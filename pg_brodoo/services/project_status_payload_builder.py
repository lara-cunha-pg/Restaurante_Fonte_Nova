import hashlib
import json

from odoo import fields

from .text_hygiene import filter_status_workflow_lines
from .text_hygiene import normalize_inline_text
from .text_hygiene import sanitize_status_summary
from .text_hygiene import split_unique_text_lines


class ProjectStatusPayloadBuilder:
    PLACEHOLDER_TODO = '[PONTO POR VALIDAR]'

    def __init__(self, env):
        self.env = env
        self.params = env['ir.config_parameter'].sudo()

    def _get_base_url(self):
        return (self.params.get_param('web.base.url') or '').strip().rstrip('/')

    def _normalize_text(self, value, fallback=None):
        normalized = normalize_inline_text(value, fallback='', max_chars=260, drop_placeholders=True)
        if normalized:
            return normalized
        return fallback if fallback is not None else self.PLACEHOLDER_TODO

    def _split_text_lines(self, value):
        return filter_status_workflow_lines(
            split_unique_text_lines(
                value,
                max_items=20,
                max_line_chars=220,
                strip_email_noise=True,
            )
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

    def _status_owner_name(self, project):
        owner = project.pg_status_owner_id or project.user_id
        return self._normalize_text(owner.display_name if owner else '', fallback='')

    def build_payload(self, project, trigger_type='manual_button', trigger_model='project.project', trigger_record_id=None):
        project.ensure_one()
        sync_published_at = fields.Datetime.now()
        return {
            'schema_version': '1.0',
            'project_name': self._normalize_text(project.name),
            'last_update_at': fields.Datetime.to_string(
                project.pg_status_last_update_at or project.write_date or sync_published_at
            ),
            'phase': project.pg_project_phase or self.PLACEHOLDER_TODO,
            'status_summary': sanitize_status_summary(project.pg_status_summary, max_chars=260) or self.PLACEHOLDER_TODO,
            'milestones': self._split_text_lines(project.pg_status_milestones_text),
            'blockers': self._split_text_lines(project.pg_status_blockers_text),
            'risks': self._split_text_lines(project.pg_status_risks_text),
            'next_steps': self._split_text_lines(project.pg_status_next_steps_text),
            'pending_decisions': self._split_text_lines(project.pg_status_pending_decisions_text),
            'go_live_target': fields.Date.to_string(project.pg_status_go_live_target) if project.pg_status_go_live_target else None,
            'owner': self._status_owner_name(project),
            'source_reference': f"project.project {project.id} - {project.display_name}",
            'source_system': 'odoo_parametro_global',
            'source_model': trigger_model or 'project.project',
            'source_record_id': str(trigger_record_id or project.id),
            'source_record_url': self._source_record_url(project, trigger_model, trigger_record_id or project.id),
            'sync_published_at': fields.Datetime.to_string(sync_published_at),
            'sync_published_by': self.env.user.display_name or 'Odoo',
            'sync_trigger': trigger_type or 'manual_button',
            'repo_branch': (project.pg_repo_branch or '').strip(),
        }

    def build_hashable_payload(self, payload):
        hashable_payload = dict(payload)
        for key in ('sync_published_at', 'sync_published_by', 'sync_trigger'):
            hashable_payload[key] = ''
        return hashable_payload

    def serialize_payload(self, payload):
        return json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + '\n'

    def payload_hash(self, payload):
        serialized = self.serialize_payload(self.build_hashable_payload(payload))
        return f"sha256:{hashlib.sha256(serialized.encode('utf-8')).hexdigest()}"
