import hashlib
import json

from odoo import fields
from odoo.exceptions import ValidationError

from .text_hygiene import normalize_inline_text


class ProjectBudgetPayloadBuilder:
    PLACEHOLDER_TODO = '[PONTO POR VALIDAR]'
    ALLOWED_LINE_STATUS_VALUES = {'draft', 'approved', 'consuming', 'closed'}
    ALLOWED_BUDGET_ORIGIN_VALUES = {'project_budget_register'}

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

    def _float_or_none(self, value):
        if value is None or value is False:
            return None
        return float(value)

    def _budget_domain(self, project):
        return [
            ('project_id', '=', project.id),
            ('active', '=', True),
            ('category', '!=', False),
            ('status', 'in', tuple(sorted(self.ALLOWED_LINE_STATUS_VALUES))),
            ('owner_id', '!=', False),
        ]

    def _eligible_budget_lines(self, project):
        return self.env['pg.project.budget.line'].search(
            self._budget_domain(project),
            order='sequence asc, id asc',
        )

    def _budget_line_id(self, line):
        return f"project-budget-line-{line.id}"

    def _budget_line_to_payload(self, line):
        return {
            'budget_line_id': self._budget_line_id(line),
            'category': self._normalize_text(line.category, max_chars=120),
            'planned_amount': self._float_or_none(line.planned_amount),
            'approved_amount': self._float_or_none(line.approved_amount),
            'consumed_amount': self._float_or_none(line.consumed_amount),
            'status': line.status,
            'owner': self._normalize_text(line.owner_id.display_name if line.owner_id else '', max_chars=120),
            'sequence': line.sequence,
            'source_budget_line_id': line.id,
            'budget_origin': 'project_budget_register',
            'notes': self._normalize_text(line.notes, fallback='', max_chars=260),
        }

    def build_payload(self, project, trigger_type='manual_button', trigger_model='project.project', trigger_record_id=None):
        project.ensure_one()
        if not project.pg_budget_currency_id:
            raise ValidationError("PG_BUDGET_SYNC payload requires a project budget currency before publication.")

        sync_published_at = fields.Datetime.now()
        budget_lines = [self._budget_line_to_payload(line) for line in self._eligible_budget_lines(project)]
        payload = {
            'schema_version': '1.0',
            'project_name': self._normalize_text(project.name),
            'project_id': project.id,
            'budget_currency': self._normalize_text(project.pg_budget_currency_id.name, max_chars=20),
            'budget_owner': self._normalize_text(
                project.pg_budget_owner_id.display_name if project.pg_budget_owner_id else '',
                fallback='',
                max_chars=120,
            ),
            'baseline_status': project.pg_budget_baseline_status or None,
            'published_budget_line_count': len(budget_lines),
            'materiality_threshold': self._float_or_none(project.pg_budget_materiality_threshold),
            'budget_lines': budget_lines,
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

    def _require_numeric(self, data, field_name, label):
        value = data.get(field_name)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValidationError(f"{label} requires a numeric value: {field_name}")

    def _validate_datetime_string(self, data, field_name, label):
        self._require_string(data, field_name, label)
        try:
            fields.Datetime.from_string(data[field_name])
        except Exception as exc:
            raise ValidationError(f"{label} requires a valid datetime string: {field_name}") from exc

    def validate_payload(self, payload):
        self._require_string(payload, 'schema_version', 'PG_BUDGET_SYNC payload')
        self._require_string(payload, 'project_name', 'PG_BUDGET_SYNC payload')
        self._require_value(payload, 'project_id', 'PG_BUDGET_SYNC payload')
        self._require_string(payload, 'budget_currency', 'PG_BUDGET_SYNC payload')

        baseline_status = payload.get('baseline_status')
        if baseline_status not in (None, False, '') and baseline_status not in self.ALLOWED_LINE_STATUS_VALUES:
            raise ValidationError("PG_BUDGET_SYNC payload has an invalid baseline_status.")
        materiality_threshold = payload.get('materiality_threshold')
        if materiality_threshold not in (None, False, '') and (
            isinstance(materiality_threshold, bool) or not isinstance(materiality_threshold, (int, float))
        ):
            raise ValidationError("PG_BUDGET_SYNC payload requires materiality_threshold to be numeric when provided.")

        budget_lines = self._require_array(payload, 'budget_lines', 'PG_BUDGET_SYNC payload')
        for budget_line in budget_lines:
            if not isinstance(budget_line, dict):
                raise ValidationError("PG_BUDGET_SYNC payload requires budget line objects in budget_lines.")
            for field_name in ('budget_line_id', 'category', 'status', 'owner'):
                self._require_string(budget_line, field_name, 'PG_BUDGET_SYNC budget_line')
            for field_name in ('planned_amount', 'approved_amount', 'consumed_amount'):
                self._require_numeric(budget_line, field_name, 'PG_BUDGET_SYNC budget_line')
            if budget_line['status'] not in self.ALLOWED_LINE_STATUS_VALUES:
                raise ValidationError("PG_BUDGET_SYNC budget_line has an invalid status.")
            if budget_line.get('budget_origin') and budget_line['budget_origin'] not in self.ALLOWED_BUDGET_ORIGIN_VALUES:
                raise ValidationError("PG_BUDGET_SYNC budget_line has an invalid budget_origin.")

        source_metadata = self._require_object(payload, 'source_metadata', 'PG_BUDGET_SYNC payload')
        for field_name in (
            'source_system',
            'source_model',
            'sync_trigger',
            'sync_published_at',
            'sync_published_by',
            'repo_branch',
        ):
            self._require_string(source_metadata, field_name, 'PG_BUDGET_SYNC source_metadata')
        self._require_value(source_metadata, 'source_record_id', 'PG_BUDGET_SYNC source_metadata')
        self._validate_datetime_string(source_metadata, 'sync_published_at', 'PG_BUDGET_SYNC source_metadata')
        payload_hash = source_metadata.get('payload_hash')
        if payload_hash not in ('', None) and not isinstance(payload_hash, str):
            raise ValidationError("PG_BUDGET_SYNC source_metadata payload_hash must be a string when provided.")
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
