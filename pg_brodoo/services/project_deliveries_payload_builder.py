import hashlib
import json

from odoo import fields
from odoo.exceptions import ValidationError

from .text_hygiene import normalize_inline_text


class ProjectDeliveriesPayloadBuilder:
    PLACEHOLDER_TODO = '[PONTO POR VALIDAR]'
    ALLOWED_DELIVERY_STATE_VALUES = {'planned', 'in_progress', 'delivered'}
    ALLOWED_ACCEPTANCE_STATE_VALUES = {'pending', 'accepted', 'rejected'}
    ALLOWED_DELIVERY_ORIGIN_VALUES = {'project_milestone'}

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

    def _delivery_domain(self, project):
        return [
            ('project_id', '=', project.id),
            ('active', '=', True),
            ('name', '!=', False),
            ('pg_delivery_state', 'in', tuple(sorted(self.ALLOWED_DELIVERY_STATE_VALUES))),
            ('pg_delivery_owner_id', '!=', False),
            ('pg_acceptance_state', 'in', tuple(sorted(self.ALLOWED_ACCEPTANCE_STATE_VALUES))),
        ]

    def _eligible_deliveries(self, project):
        deliveries = self.env['project.milestone'].search(
            self._delivery_domain(project),
            order='sequence asc, deadline asc, id asc',
        )
        return deliveries.filtered(lambda milestone: milestone.deadline or milestone.reached_date)

    def _delivery_id(self, milestone):
        return f"project-milestone-{milestone.id}"

    def _delivery_to_payload(self, milestone):
        return {
            'delivery_id': self._delivery_id(milestone),
            'title': self._normalize_text(milestone.name, max_chars=160),
            'delivery_state': milestone.pg_delivery_state,
            'planned_date': self._format_date(milestone.deadline),
            'actual_date': self._format_date(milestone.reached_date),
            'owner': self._normalize_text(
                milestone.pg_delivery_owner_id.display_name if milestone.pg_delivery_owner_id else '',
                max_chars=120,
            ),
            'acceptance_state': milestone.pg_acceptance_state,
            'source_reference': self._normalize_text(
                milestone.pg_delivery_source_reference or f"project.milestone {milestone.id} - {milestone.name}",
                max_chars=220,
            ),
            'source_milestone_id': milestone.id,
            'delivery_origin': 'project_milestone',
        }

    def build_payload(self, project, trigger_type='manual_button', trigger_model='project.project', trigger_record_id=None):
        project.ensure_one()
        sync_published_at = fields.Datetime.now()
        deliveries = [self._delivery_to_payload(milestone) for milestone in self._eligible_deliveries(project)]
        payload = {
            'schema_version': '1.0',
            'project_name': self._normalize_text(project.name),
            'project_id': project.id,
            'project_phase': project.pg_project_phase or self.PLACEHOLDER_TODO,
            'published_delivery_count': len(deliveries),
            'deliveries': deliveries,
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
        self._require_string(payload, 'schema_version', 'PG_DELIVERIES_SYNC payload')
        self._require_string(payload, 'project_name', 'PG_DELIVERIES_SYNC payload')
        self._require_value(payload, 'project_id', 'PG_DELIVERIES_SYNC payload')

        deliveries = self._require_array(payload, 'deliveries', 'PG_DELIVERIES_SYNC payload')
        for delivery in deliveries:
            if not isinstance(delivery, dict):
                raise ValidationError("PG_DELIVERIES_SYNC payload requires delivery objects in deliveries.")
            for field_name in (
                'delivery_id',
                'title',
                'delivery_state',
                'owner',
                'acceptance_state',
                'source_reference',
            ):
                self._require_string(delivery, field_name, 'PG_DELIVERIES_SYNC delivery')
            self._validate_nullable_date_string(delivery, 'planned_date', 'PG_DELIVERIES_SYNC delivery')
            self._validate_nullable_date_string(delivery, 'actual_date', 'PG_DELIVERIES_SYNC delivery')
            if delivery.get('planned_date') in (None, False, '') and delivery.get('actual_date') in (None, False, ''):
                raise ValidationError("PG_DELIVERIES_SYNC delivery requires planned_date or actual_date.")
            if delivery['delivery_state'] not in self.ALLOWED_DELIVERY_STATE_VALUES:
                raise ValidationError("PG_DELIVERIES_SYNC delivery has an invalid delivery_state.")
            if delivery['acceptance_state'] not in self.ALLOWED_ACCEPTANCE_STATE_VALUES:
                raise ValidationError("PG_DELIVERIES_SYNC delivery has an invalid acceptance_state.")
            if delivery.get('delivery_origin') and delivery['delivery_origin'] not in self.ALLOWED_DELIVERY_ORIGIN_VALUES:
                raise ValidationError("PG_DELIVERIES_SYNC delivery has an invalid delivery_origin.")

        source_metadata = self._require_object(payload, 'source_metadata', 'PG_DELIVERIES_SYNC payload')
        for field_name in (
            'source_system',
            'source_model',
            'sync_trigger',
            'sync_published_at',
            'sync_published_by',
            'repo_branch',
        ):
            self._require_string(source_metadata, field_name, 'PG_DELIVERIES_SYNC source_metadata')
        self._require_value(source_metadata, 'source_record_id', 'PG_DELIVERIES_SYNC source_metadata')
        self._validate_datetime_string(source_metadata, 'sync_published_at', 'PG_DELIVERIES_SYNC source_metadata')
        payload_hash = source_metadata.get('payload_hash')
        if payload_hash not in ('', None) and not isinstance(payload_hash, str):
            raise ValidationError("PG_DELIVERIES_SYNC source_metadata payload_hash must be a string when provided.")
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
