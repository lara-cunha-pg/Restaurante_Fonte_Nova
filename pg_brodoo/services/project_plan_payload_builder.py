import hashlib
import json

from odoo import fields
from odoo.exceptions import ValidationError

from .text_hygiene import normalize_inline_text, split_unique_text_lines


class ProjectPlanPayloadBuilder:
    PLACEHOLDER_TODO = '[PONTO POR VALIDAR]'
    ALLOWED_PLAN_STATUS_VALUES = {'planned', 'in_progress', 'completed'}
    ALLOWED_PLAN_ITEM_TYPE_VALUES = {'milestone'}
    ALLOWED_PLAN_ORIGIN_VALUES = {'project_milestone_baseline'}

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

    def _normalize_text_lines(self, value, max_items=12, max_line_chars=120):
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

    def _format_date(self, value):
        return fields.Date.to_string(value) if value else None

    def _plan_domain(self, project):
        return [
            ('project_id', '=', project.id),
            ('active', '=', True),
            ('name', '!=', False),
            ('sequence', '!=', False),
            ('deadline', '!=', False),
            ('pg_plan_start_date', '!=', False),
            ('pg_plan_status', 'in', tuple(sorted(self.ALLOWED_PLAN_STATUS_VALUES))),
            ('pg_plan_owner_id', '!=', False),
        ]

    def _eligible_plan_items(self, project):
        return self.env['project.milestone'].search(
            self._plan_domain(project),
            order='sequence asc, deadline asc, id asc',
        )

    def _plan_item_id(self, milestone):
        return f"project-plan-milestone-{milestone.id}"

    def _plan_item_to_payload(self, milestone):
        return {
            'plan_item_id': self._plan_item_id(milestone),
            'title': self._normalize_text(milestone.name, max_chars=160),
            'item_type': 'milestone',
            'status': milestone.pg_plan_status,
            'planned_start': self._format_date(milestone.pg_plan_start_date),
            'planned_end': self._format_date(milestone.deadline),
            'owner': self._normalize_text(
                milestone.pg_plan_owner_id.display_name if milestone.pg_plan_owner_id else '',
                max_chars=120,
            ),
            'dependency_refs': self._normalize_text_lines(milestone.pg_plan_dependency_refs),
            'sequence': milestone.sequence,
            'source_milestone_id': milestone.id,
            'plan_origin': 'project_milestone_baseline',
        }

    def build_payload(self, project, trigger_type='manual_button', trigger_model='project.project', trigger_record_id=None):
        project.ensure_one()
        sync_published_at = fields.Datetime.now()
        plan_items = [self._plan_item_to_payload(milestone) for milestone in self._eligible_plan_items(project)]
        payload = {
            'schema_version': '1.0',
            'project_name': self._normalize_text(project.name),
            'project_id': project.id,
            'project_phase': project.pg_project_phase or self.PLACEHOLDER_TODO,
            'go_live_target': self._format_date(project.pg_status_go_live_target),
            'published_plan_item_count': len(plan_items),
            'plan_items': plan_items,
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

    def _validate_nullable_date_string(self, data, field_name, label):
        if field_name not in data:
            raise ValidationError(f"{label} requires the date field to exist: {field_name}")
        value = data.get(field_name)
        if value in (None, False, ''):
            return
        if not isinstance(value, str):
            raise ValidationError(f"{label} requires a valid date string when provided: {field_name}")
        try:
            fields.Date.from_string(value)
        except Exception as exc:
            raise ValidationError(f"{label} requires a valid date string when provided: {field_name}") from exc

    def validate_payload(self, payload):
        self._require_string(payload, 'schema_version', 'PG_PROJECT_PLAN_SYNC payload')
        self._require_string(payload, 'project_name', 'PG_PROJECT_PLAN_SYNC payload')
        self._require_value(payload, 'project_id', 'PG_PROJECT_PLAN_SYNC payload')
        self._validate_nullable_date_string(payload, 'go_live_target', 'PG_PROJECT_PLAN_SYNC payload')

        plan_items = self._require_array(payload, 'plan_items', 'PG_PROJECT_PLAN_SYNC payload')
        for plan_item in plan_items:
            if not isinstance(plan_item, dict):
                raise ValidationError("PG_PROJECT_PLAN_SYNC payload requires plan item objects in plan_items.")
            for field_name in (
                'plan_item_id',
                'title',
                'item_type',
                'status',
                'owner',
            ):
                self._require_string(plan_item, field_name, 'PG_PROJECT_PLAN_SYNC plan_item')
            self._validate_nullable_date_string(plan_item, 'planned_start', 'PG_PROJECT_PLAN_SYNC plan_item')
            self._validate_nullable_date_string(plan_item, 'planned_end', 'PG_PROJECT_PLAN_SYNC plan_item')
            if plan_item.get('planned_start') in (None, False, '') or plan_item.get('planned_end') in (None, False, ''):
                raise ValidationError("PG_PROJECT_PLAN_SYNC plan_item requires planned_start and planned_end.")
            self._require_string_array(
                plan_item,
                'dependency_refs',
                'PG_PROJECT_PLAN_SYNC plan_item',
                allow_empty=True,
            )
            if plan_item['status'] not in self.ALLOWED_PLAN_STATUS_VALUES:
                raise ValidationError("PG_PROJECT_PLAN_SYNC plan_item has an invalid status.")
            if plan_item['item_type'] not in self.ALLOWED_PLAN_ITEM_TYPE_VALUES:
                raise ValidationError("PG_PROJECT_PLAN_SYNC plan_item has an invalid item_type.")
            if plan_item.get('plan_origin') and plan_item['plan_origin'] not in self.ALLOWED_PLAN_ORIGIN_VALUES:
                raise ValidationError("PG_PROJECT_PLAN_SYNC plan_item has an invalid plan_origin.")

        source_metadata = self._require_object(payload, 'source_metadata', 'PG_PROJECT_PLAN_SYNC payload')
        for field_name in (
            'source_system',
            'source_model',
            'sync_trigger',
            'sync_published_at',
            'sync_published_by',
            'repo_branch',
        ):
            self._require_string(source_metadata, field_name, 'PG_PROJECT_PLAN_SYNC source_metadata')
        self._require_value(source_metadata, 'source_record_id', 'PG_PROJECT_PLAN_SYNC source_metadata')
        self._validate_datetime_string(source_metadata, 'sync_published_at', 'PG_PROJECT_PLAN_SYNC source_metadata')
        payload_hash = source_metadata.get('payload_hash')
        if payload_hash not in ('', None) and not isinstance(payload_hash, str):
            raise ValidationError("PG_PROJECT_PLAN_SYNC source_metadata payload_hash must be a string when provided.")
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
