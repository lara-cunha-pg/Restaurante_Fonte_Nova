import hashlib
import json

from odoo import fields
from odoo.exceptions import ValidationError

from .text_hygiene import normalize_inline_text


class ProjectRisksPayloadBuilder:
    PLACEHOLDER_TODO = '[PONTO POR VALIDAR]'
    ALLOWED_SEVERITY_VALUES = {'low', 'medium', 'high', 'critical'}
    ALLOWED_STATUS_VALUES = {'open', 'monitoring', 'mitigated'}
    ALLOWED_RISK_ORIGIN_VALUES = {'project_risk_register'}

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

    def _risk_domain(self, project):
        return [
            ('project_id', '=', project.id),
            ('active', '=', True),
            ('name', '!=', False),
            ('description', '!=', False),
            ('severity', 'in', tuple(sorted(self.ALLOWED_SEVERITY_VALUES))),
            ('state', 'in', tuple(sorted(self.ALLOWED_STATUS_VALUES))),
            ('mitigation', '!=', False),
            ('owner_id', '!=', False),
            ('last_review_at', '!=', False),
        ]

    def _eligible_risks(self, project):
        return self.env['pg.project.risk'].with_context(active_test=False).search(
            self._risk_domain(project),
            order='sequence asc, id asc',
        )

    def _risk_id(self, risk):
        return f"project-risk-{risk.id}"

    def _risk_to_payload(self, risk):
        return {
            'risk_id': self._risk_id(risk),
            'title': self._normalize_text(risk.name, max_chars=160),
            'description': self._normalize_text(risk.description, max_chars=420),
            'severity': risk.severity,
            'status': risk.state,
            'mitigation': self._normalize_text(risk.mitigation, max_chars=420),
            'owner': self._normalize_text(risk.owner_id.display_name if risk.owner_id else '', max_chars=120),
            'last_review_at': fields.Datetime.to_string(risk.last_review_at),
            'source_reference': self._normalize_text(
                risk.source_reference or f"pg.project.risk {risk.id} - {risk.name}",
                max_chars=220,
            ),
            'source_risk_id': risk.id,
            'risk_origin': 'project_risk_register',
        }

    def build_payload(self, project, trigger_type='manual_button', trigger_model='project.project', trigger_record_id=None):
        project.ensure_one()
        sync_published_at = fields.Datetime.now()
        risks = [self._risk_to_payload(risk) for risk in self._eligible_risks(project)]
        payload = {
            'schema_version': '1.0',
            'project_name': self._normalize_text(project.name),
            'project_id': project.id,
            'project_phase': project.pg_project_phase or self.PLACEHOLDER_TODO,
            'published_risk_count': len(risks),
            'risks': risks,
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
        self._require_string(payload, 'schema_version', 'PG_RISKS_SYNC payload')
        self._require_string(payload, 'project_name', 'PG_RISKS_SYNC payload')
        self._require_value(payload, 'project_id', 'PG_RISKS_SYNC payload')

        risks = self._require_array(payload, 'risks', 'PG_RISKS_SYNC payload')
        for risk in risks:
            if not isinstance(risk, dict):
                raise ValidationError("PG_RISKS_SYNC payload requires risk objects in risks.")
            for field_name in (
                'risk_id',
                'title',
                'description',
                'severity',
                'status',
                'mitigation',
                'owner',
                'last_review_at',
                'source_reference',
            ):
                self._require_string(risk, field_name, 'PG_RISKS_SYNC risk')
            self._validate_datetime_string(risk, 'last_review_at', 'PG_RISKS_SYNC risk')
            if risk['severity'] not in self.ALLOWED_SEVERITY_VALUES:
                raise ValidationError("PG_RISKS_SYNC risk has an invalid severity.")
            if risk['status'] not in self.ALLOWED_STATUS_VALUES:
                raise ValidationError("PG_RISKS_SYNC risk has an invalid status.")
            if risk.get('risk_origin') and risk['risk_origin'] not in self.ALLOWED_RISK_ORIGIN_VALUES:
                raise ValidationError("PG_RISKS_SYNC risk has an invalid risk_origin.")

        source_metadata = self._require_object(payload, 'source_metadata', 'PG_RISKS_SYNC payload')
        for field_name in (
            'source_system',
            'source_model',
            'sync_trigger',
            'sync_published_at',
            'sync_published_by',
            'repo_branch',
        ):
            self._require_string(source_metadata, field_name, 'PG_RISKS_SYNC source_metadata')
        self._require_value(source_metadata, 'source_record_id', 'PG_RISKS_SYNC source_metadata')
        self._validate_datetime_string(source_metadata, 'sync_published_at', 'PG_RISKS_SYNC source_metadata')
        payload_hash = source_metadata.get('payload_hash')
        if payload_hash not in ('', None) and not isinstance(payload_hash, str):
            raise ValidationError("PG_RISKS_SYNC source_metadata payload_hash must be a string when provided.")
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

