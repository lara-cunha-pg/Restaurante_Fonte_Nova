import hashlib
import json

from odoo import fields
from odoo.exceptions import ValidationError

from .text_hygiene import normalize_inline_text


class ProjectDecisionsPayloadBuilder:
    PLACEHOLDER_TODO = '[PONTO POR VALIDAR]'
    ALLOWED_DECISION_STATE_VALUES = {'closed'}
    ALLOWED_IMPACT_SCOPE_VALUES = {'task_scope_item'}
    ALLOWED_DECISION_ORIGIN_VALUES = {'consultive_gate'}

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

    def _optional_text(self, value, max_chars=260):
        return normalize_inline_text(value, fallback='', max_chars=max_chars, drop_placeholders=True)

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

    def _task_domain(self, project):
        domain = [
            ('project_id', '=', project.id),
            ('active', '=', True),
            ('pg_scope_relevant', '=', True),
            ('pg_scope_track', '=', 'approved_scope'),
            ('pg_scope_state', 'not in', ('excluded', 'dropped')),
            ('pg_ai_consultive_gate_state', '=', 'ready'),
            ('pg_ai_consultive_gate_checked_by_id', '!=', False),
            ('pg_ai_consultive_gate_checked_at', '!=', False),
            ('pg_ai_recommendation_class', '!=', False),
        ]
        if 'is_template' in self.env['project.task']._fields:
            domain.append(('is_template', '=', False))
        return domain

    def _eligible_tasks(self, project):
        return self.env['project.task'].with_context(active_test=False).search(
            self._task_domain(project),
            order='pg_ai_consultive_gate_checked_at, id',
        )

    def _decision_summary(self, task):
        recommendation_label = task._get_pg_ai_recommendation_class_label() or (task.pg_ai_recommendation_class or 'Unknown')
        if task.pg_ai_recommendation_class == 'additional_module' and (task.pg_ai_recommended_module or '').strip():
            return self._normalize_text(
                f"Final recommendation closed as {recommendation_label} via module {task.pg_ai_recommended_module.strip()}."
            )
        return self._normalize_text(f"Final recommendation closed as {recommendation_label}.")

    def _decision_id(self, task):
        return f"task-{task.id}-consultive-recommendation"

    def _task_to_payload(self, task):
        return {
            'decision_id': self._decision_id(task),
            'title': self._normalize_text(task.name),
            'decision_summary': self._decision_summary(task),
            'decision_state': 'closed',
            'decided_at': fields.Datetime.to_string(task.pg_ai_consultive_gate_checked_at),
            'decided_by': self._normalize_text(task.pg_ai_consultive_gate_checked_by_id.display_name if task.pg_ai_consultive_gate_checked_by_id else ''),
            'impact_scope': 'task_scope_item',
            'source_reference': f"project.task {task.id} - {self._normalize_text(task.name)}",
            'source_task_id': task.id,
            'decision_origin': 'consultive_gate',
            'recommendation_class': task.pg_ai_recommendation_class,
            'recommended_module': self._optional_text(task.pg_ai_recommended_module, max_chars=120) or None,
            'rationale_summary': self._optional_text(task.pg_ai_recommendation_justification, max_chars=260) or None,
            'scope_state': task.pg_scope_state or None,
        }

    def build_payload(self, project, trigger_type='manual_button', trigger_model='project.project', trigger_record_id=None):
        project.ensure_one()
        sync_published_at = fields.Datetime.now()
        decisions = [self._task_to_payload(task) for task in self._eligible_tasks(project)]
        payload = {
            'schema_version': '1.0',
            'project_name': self._normalize_text(project.name),
            'project_id': project.id,
            'project_phase': project.pg_project_phase or self.PLACEHOLDER_TODO,
            'published_decision_count': len(decisions),
            'decisions': decisions,
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
        self._require_string(payload, 'schema_version', 'PG_DECISIONS_SYNC payload')
        self._require_string(payload, 'project_name', 'PG_DECISIONS_SYNC payload')
        self._require_value(payload, 'project_id', 'PG_DECISIONS_SYNC payload')

        decisions = self._require_array(payload, 'decisions', 'PG_DECISIONS_SYNC payload')
        for decision in decisions:
            if not isinstance(decision, dict):
                raise ValidationError("PG_DECISIONS_SYNC payload requires decision objects in decisions.")
            for field_name in (
                'decision_id',
                'title',
                'decision_summary',
                'decision_state',
                'decided_at',
                'decided_by',
                'impact_scope',
                'source_reference',
            ):
                self._require_string(decision, field_name, 'PG_DECISIONS_SYNC decision')
            self._validate_datetime_string(decision, 'decided_at', 'PG_DECISIONS_SYNC decision')
            if decision['decision_state'] not in self.ALLOWED_DECISION_STATE_VALUES:
                raise ValidationError("PG_DECISIONS_SYNC decision has an invalid decision_state.")
            if decision['impact_scope'] not in self.ALLOWED_IMPACT_SCOPE_VALUES:
                raise ValidationError("PG_DECISIONS_SYNC decision has an invalid impact_scope.")
            if decision.get('decision_origin') and decision['decision_origin'] not in self.ALLOWED_DECISION_ORIGIN_VALUES:
                raise ValidationError("PG_DECISIONS_SYNC decision has an invalid decision_origin.")

        source_metadata = self._require_object(payload, 'source_metadata', 'PG_DECISIONS_SYNC payload')
        for field_name in (
            'source_system',
            'source_model',
            'sync_trigger',
            'sync_published_at',
            'sync_published_by',
            'repo_branch',
        ):
            self._require_string(source_metadata, field_name, 'PG_DECISIONS_SYNC source_metadata')
        self._require_value(source_metadata, 'source_record_id', 'PG_DECISIONS_SYNC source_metadata')
        self._validate_datetime_string(source_metadata, 'sync_published_at', 'PG_DECISIONS_SYNC source_metadata')
        payload_hash = source_metadata.get('payload_hash')
        if payload_hash not in ('', None) and not isinstance(payload_hash, str):
            raise ValidationError("PG_DECISIONS_SYNC source_metadata payload_hash must be a string when provided.")
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
