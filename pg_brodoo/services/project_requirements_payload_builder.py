import hashlib
import json

from odoo import fields
from odoo.exceptions import ValidationError

from .text_hygiene import normalize_inline_text, split_unique_text_lines


class ProjectRequirementsPayloadBuilder:
    PLACEHOLDER_TODO = '[PONTO POR VALIDAR]'
    ALLOWED_REQUIREMENT_STATUS_VALUES = {'approved', 'deferred'}
    ALLOWED_REQUIREMENT_PRIORITY_VALUES = {'low', 'medium', 'high', 'critical'}
    ALLOWED_REQUIREMENT_ORIGIN_VALUES = {'approved_scope_task'}
    ALLOWED_SCOPE_STATE_VALUES = {'validated', 'deferred'}

    def __init__(self, env):
        self.env = env
        self.params = env['ir.config_parameter'].sudo()

    def _get_base_url(self):
        return (self.params.get_param('web.base.url') or '').strip().rstrip('/')

    def _normalize_text(self, value, fallback=None, max_chars=260):
        normalized = normalize_inline_text(value, fallback='', max_chars=max_chars, drop_placeholders=True)
        if normalized:
            return normalized
        return fallback if fallback is not None else self.PLACEHOLDER_TODO

    def _normalize_text_lines(self, value, max_items=12, max_line_chars=220):
        return split_unique_text_lines(
            value,
            from_html=False,
            max_items=max_items,
            max_line_chars=max_line_chars,
            strip_email_noise=True,
        )

    def _build_record_url(self, model_name, record_id):
        base_url = self._get_base_url()
        if not base_url or not model_name or not record_id:
            return None
        return f"{base_url}/web#id={record_id}&model={model_name}"

    def _source_record_url(self, project, trigger_model, trigger_record_id):
        if trigger_model and trigger_record_id:
            source_url = self._build_record_url(trigger_model, trigger_record_id)
            if source_url:
                return source_url
        return self._build_record_url('project.project', project.id)

    def _requirement_domain(self, project):
        return [
            ('project_id', '=', project.id),
            ('active', '=', True),
            ('name', '!=', False),
            ('pg_scope_relevant', '=', True),
            ('pg_scope_track', '=', 'approved_scope'),
            ('pg_scope_kind', '=', 'requirement'),
            ('pg_scope_state', 'in', tuple(sorted(self.ALLOWED_SCOPE_STATE_VALUES))),
            ('pg_scope_summary', '!=', False),
            ('pg_requirement_status', 'in', tuple(sorted(self.ALLOWED_REQUIREMENT_STATUS_VALUES))),
            ('pg_requirement_priority', 'in', tuple(sorted(self.ALLOWED_REQUIREMENT_PRIORITY_VALUES))),
            ('pg_requirement_owner_id', '!=', False),
            ('pg_requirement_traceability_refs', '!=', False),
        ]

    def _eligible_requirements(self, project):
        tasks = self.env['project.task'].with_context(active_test=False).search(
            self._requirement_domain(project),
            order='pg_scope_sequence asc, id asc',
        )
        return tasks.filtered(lambda task: bool(self._normalize_text_lines(task.pg_requirement_traceability_refs)))

    def _requirement_id(self, task):
        return f"project-task-requirement-{task.id}"

    def _requirement_to_payload(self, task):
        return {
            'requirement_id': self._requirement_id(task),
            'title': self._normalize_text(task.name, max_chars=160),
            'summary': self._normalize_text(task.pg_scope_summary, max_chars=420),
            'status': task.pg_requirement_status,
            'priority': task.pg_requirement_priority,
            'owner': self._normalize_text(
                task.pg_requirement_owner_id.display_name if task.pg_requirement_owner_id else '',
                max_chars=120,
            ),
            'traceability_refs': self._normalize_text_lines(task.pg_requirement_traceability_refs),
            'source_task_id': task.id,
            'requirement_origin': 'approved_scope_task',
            'scope_state': task.pg_scope_state,
            'acceptance_criteria': self._normalize_text_lines(
                task.pg_acceptance_criteria_text,
                max_items=12,
                max_line_chars=260,
            ),
        }

    def build_payload(self, project, trigger_type='manual_button', trigger_model='project.project', trigger_record_id=None):
        project.ensure_one()
        sync_published_at = fields.Datetime.now()
        requirements = [self._requirement_to_payload(task) for task in self._eligible_requirements(project)]
        payload = {
            'schema_version': '1.0',
            'project_name': self._normalize_text(project.name),
            'project_id': project.id,
            'project_phase': project.pg_project_phase or self.PLACEHOLDER_TODO,
            'published_requirement_count': len(requirements),
            'requirements': requirements,
            'source_metadata': {
                'source_system': 'odoo_parametro_global',
                'source_model': trigger_model or 'project.project',
                'source_record_id': trigger_record_id or project.id,
                'source_record_url': self._source_record_url(project, trigger_model, trigger_record_id or project.id),
                'sync_trigger': trigger_type or 'manual_button',
                'sync_published_at': fields.Datetime.to_string(sync_published_at),
                'sync_published_by': self.env.user.display_name or 'Odoo',
                'repo_branch': (project.pg_repo_branch or '').strip(),
                'payload_hash': '',
            },
        }
        self.validate_payload(payload)
        return payload

    def _require_string(self, data, field_name, label):
        value = data.get(field_name)
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(f"{label} requires a non-empty string: {field_name}")

    def _require_value(self, data, field_name, label):
        value = data.get(field_name)
        if value in (None, False, ''):
            raise ValidationError(f"{label} requires a value: {field_name}")

    def _require_array(self, data, field_name, label):
        value = data.get(field_name)
        if not isinstance(value, list):
            raise ValidationError(f"{label} requires an array: {field_name}")
        return value

    def _require_string_array(self, data, field_name, label, allow_empty=False):
        values = self._require_array(data, field_name, label)
        if not allow_empty and not values:
            raise ValidationError(f"{label} requires at least one item: {field_name}")
        for value in values:
            if not isinstance(value, str) or not value.strip():
                raise ValidationError(f"{label} requires non-empty string items: {field_name}")
        return values

    def _require_object(self, data, field_name, label):
        value = data.get(field_name)
        if not isinstance(value, dict):
            raise ValidationError(f"{label} requires an object: {field_name}")
        return value

    def _validate_datetime_string(self, data, field_name, label):
        self._require_string(data, field_name, label)
        try:
            fields.Datetime.from_string(data[field_name])
        except Exception as exc:
            raise ValidationError(f"{label} requires a valid datetime string: {field_name}") from exc

    def validate_payload(self, payload):
        self._require_string(payload, 'schema_version', 'PG_REQUIREMENTS_SYNC payload')
        self._require_string(payload, 'project_name', 'PG_REQUIREMENTS_SYNC payload')
        self._require_value(payload, 'project_id', 'PG_REQUIREMENTS_SYNC payload')

        requirements = self._require_array(payload, 'requirements', 'PG_REQUIREMENTS_SYNC payload')
        for requirement in requirements:
            if not isinstance(requirement, dict):
                raise ValidationError("PG_REQUIREMENTS_SYNC payload requires requirement objects in requirements.")
            for field_name in (
                'requirement_id',
                'title',
                'summary',
                'status',
                'priority',
                'owner',
            ):
                self._require_string(requirement, field_name, 'PG_REQUIREMENTS_SYNC requirement')
            self._require_string_array(
                requirement,
                'traceability_refs',
                'PG_REQUIREMENTS_SYNC requirement',
            )
            if 'acceptance_criteria' in requirement:
                self._require_string_array(
                    requirement,
                    'acceptance_criteria',
                    'PG_REQUIREMENTS_SYNC requirement',
                    allow_empty=True,
                )
            if requirement['status'] not in self.ALLOWED_REQUIREMENT_STATUS_VALUES:
                raise ValidationError("PG_REQUIREMENTS_SYNC requirement has an invalid status.")
            if requirement['priority'] not in self.ALLOWED_REQUIREMENT_PRIORITY_VALUES:
                raise ValidationError("PG_REQUIREMENTS_SYNC requirement has an invalid priority.")
            if requirement.get('requirement_origin') and requirement['requirement_origin'] not in self.ALLOWED_REQUIREMENT_ORIGIN_VALUES:
                raise ValidationError("PG_REQUIREMENTS_SYNC requirement has an invalid requirement_origin.")
            if requirement.get('scope_state') and requirement['scope_state'] not in self.ALLOWED_SCOPE_STATE_VALUES:
                raise ValidationError("PG_REQUIREMENTS_SYNC requirement has an invalid scope_state.")

        source_metadata = self._require_object(payload, 'source_metadata', 'PG_REQUIREMENTS_SYNC payload')
        for field_name in (
            'source_system',
            'source_model',
            'sync_trigger',
            'sync_published_at',
            'sync_published_by',
            'repo_branch',
        ):
            self._require_string(source_metadata, field_name, 'PG_REQUIREMENTS_SYNC source_metadata')
        self._require_value(source_metadata, 'source_record_id', 'PG_REQUIREMENTS_SYNC source_metadata')
        self._validate_datetime_string(source_metadata, 'sync_published_at', 'PG_REQUIREMENTS_SYNC source_metadata')
        payload_hash = source_metadata.get('payload_hash')
        if payload_hash not in ('', None) and not isinstance(payload_hash, str):
            raise ValidationError("PG_REQUIREMENTS_SYNC source_metadata payload_hash must be a string when provided.")
        return payload

    def build_hashable_payload(self, payload):
        hashable_payload = json.loads(json.dumps(payload))
        source_metadata = hashable_payload.get('source_metadata') or {}
        for key in ('sync_trigger', 'sync_published_at', 'sync_published_by', 'payload_hash'):
            source_metadata[key] = ''
        hashable_payload['source_metadata'] = source_metadata
        return hashable_payload

    def serialize_payload(self, payload):
        return json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + '\n'

    def payload_hash(self, payload):
        self.validate_payload(payload)
        serialized = self.serialize_payload(self.build_hashable_payload(payload))
        return f"sha256:{hashlib.sha256(serialized.encode('utf-8')).hexdigest()}"
