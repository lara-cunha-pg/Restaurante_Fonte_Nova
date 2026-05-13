import json
import logging

from odoo import _
from odoo.exceptions import UserError

from .chatgpt_service import ChatGptPromptService
from .text_hygiene import filter_status_workflow_lines
from .text_hygiene import normalize_inline_text
from .text_hygiene import sanitize_plaintext
from .text_hygiene import sanitize_status_summary

_logger = logging.getLogger(__name__)


FORBIDDEN_STATUS_NEEDLES = (
    'latest status publication status',
    'no status snapshot has been published yet',
    'review this draft',
    'apply the draft',
    'manual publication',
    'publish a new status snapshot',
)

LLM_STATUS_REDRAFT_INSTRUCTIONS = """Redraft one Odoo operational status draft.

Rules:
- Return strict JSON only.
- Use only facts explicitly present in the input.
- Never invent blockers, approvals, timelines, risks, dependencies, milestones or next steps.
- Keep the language factual, compact and suitable for a publishable operational status draft.
- Remove workflow/meta wording about draft review, publication mechanics or sync internals.
- Avoid repeating the same idea across sections.
- Return at most 5 lines per list section.
- Return an empty array for any section that is not supported by the input.

JSON schema:
{
  "decision": "redraft|refuse",
  "status_summary": "string",
  "milestones": ["string"],
  "blockers": ["string"],
  "risks": ["string"],
  "next_steps": ["string"],
  "pending_decisions": ["string"],
  "quality_rationale": "string",
  "confidence": 0,
  "refusal_reason": "string"
}
"""


class ProjectStatusDraftLlmService:
    def __init__(self, env):
        self.env = env
        self.prompt_service = ChatGptPromptService(env)

    def _param_is_true(self, key):
        value = (self.prompt_service._get_param(key) or '').strip().lower()
        return value in {'1', 'true', 'yes', 'on'}

    def _selection_label(self, record, field_name):
        field = record._fields.get(field_name)
        if not field:
            return ''
        return dict(field.selection).get(getattr(record, field_name), '')

    def _is_opted_in(self):
        return self._param_is_true('pg_status_draft_llm_redraft_enabled')

    def _is_enabled(self):
        return bool((self.prompt_service._get_param('pg_openai_api_key') or '').strip()) and self._is_opted_in()

    def _json_schema_format(self):
        return {
            'type': 'json_schema',
            'name': 'status_draft_redraft',
            'strict': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'decision': {
                        'type': 'string',
                        'enum': ['redraft', 'refuse'],
                    },
                    'status_summary': {'type': 'string'},
                    'milestones': {'type': 'array', 'items': {'type': 'string'}},
                    'blockers': {'type': 'array', 'items': {'type': 'string'}},
                    'risks': {'type': 'array', 'items': {'type': 'string'}},
                    'next_steps': {'type': 'array', 'items': {'type': 'string'}},
                    'pending_decisions': {'type': 'array', 'items': {'type': 'string'}},
                    'quality_rationale': {'type': 'string'},
                    'confidence': {'type': 'integer'},
                    'refusal_reason': {'type': 'string'},
                },
                'required': [
                    'decision',
                    'status_summary',
                    'milestones',
                    'blockers',
                    'risks',
                    'next_steps',
                    'pending_decisions',
                    'quality_rationale',
                    'confidence',
                    'refusal_reason',
                ],
                'additionalProperties': False,
            },
        }

    def _normalize_confidence(self, value):
        try:
            return max(0, min(int(value), 100))
        except (TypeError, ValueError):
            return 0

    def _contains_forbidden_text(self, value):
        normalized = normalize_inline_text(value, fallback='', max_chars=False, drop_placeholders=True).lower()
        if not normalized:
            return False
        return any(needle in normalized for needle in FORBIDDEN_STATUS_NEEDLES)

    def _normalize_lines(self, values):
        if not isinstance(values, list):
            raise UserError(_("A OpenAI devolveu uma secao de status fora do schema esperado."))

        lines = []
        for value in values[:5]:
            normalized = normalize_inline_text(value, fallback='', max_chars=220, drop_placeholders=True)
            if not normalized or normalized in lines:
                continue
            if self._contains_forbidden_text(normalized):
                continue
            lines.append(normalized)
        return filter_status_workflow_lines(lines)

    def should_attempt(self, project, deterministic_values):
        if not self._is_enabled():
            return False
        return bool(
            deterministic_values.get('pg_status_draft_summary')
            or deterministic_values.get('pg_status_draft_milestones_text')
            or deterministic_values.get('pg_status_draft_blockers_text')
            or deterministic_values.get('pg_status_draft_risks_text')
            or deterministic_values.get('pg_status_draft_next_steps_text')
            or deterministic_values.get('pg_status_draft_pending_decisions_text')
        )

    def _build_input_text(self, project, deterministic_values):
        return (
            "Project: %s\n"
            "Phase: %s\n"
            "Deterministic status summary:\n%s\n\n"
            "Deterministic milestones:\n%s\n\n"
            "Deterministic blockers:\n%s\n\n"
            "Deterministic risks:\n%s\n\n"
            "Deterministic next steps:\n%s\n\n"
            "Deterministic pending decisions:\n%s\n\n"
            "Validated chatter explainability:\n%s"
        ) % (
            project.display_name,
            self._selection_label(project, 'pg_project_phase') or '(empty)',
            deterministic_values.get('pg_status_draft_summary') or '(empty)',
            deterministic_values.get('pg_status_draft_milestones_text') or '(empty)',
            deterministic_values.get('pg_status_draft_blockers_text') or '(empty)',
            deterministic_values.get('pg_status_draft_risks_text') or '(empty)',
            deterministic_values.get('pg_status_draft_next_steps_text') or '(empty)',
            deterministic_values.get('pg_status_draft_pending_decisions_text') or '(empty)',
            deterministic_values.get('pg_status_draft_signal_feedback') or '(empty)',
        )

    def _normalize_payload(self, payload):
        if not isinstance(payload, dict):
            raise UserError(_("A OpenAI devolveu um payload de status draft fora do schema esperado."))

        decision = (payload.get('decision') or '').strip()
        if decision not in {'redraft', 'refuse'}:
            raise UserError(_("A OpenAI devolveu uma decisao invalida para status draft."))

        quality_rationale = sanitize_plaintext(payload.get('quality_rationale'), max_chars=220)
        refusal_reason = sanitize_plaintext(payload.get('refusal_reason'), max_chars=220)
        confidence = self._normalize_confidence(payload.get('confidence'))

        if decision == 'refuse':
            return {
                'decision': 'refuse',
                'quality_rationale': quality_rationale or False,
                'refusal_reason': refusal_reason or quality_rationale or False,
                'confidence': confidence,
            }

        status_summary = sanitize_status_summary(payload.get('status_summary'), max_chars=420)
        if not status_summary or self._contains_forbidden_text(status_summary):
            raise UserError(_("A OpenAI devolveu um status summary invalido para status draft."))

        milestones = self._normalize_lines(payload.get('milestones') or [])
        blockers = self._normalize_lines(payload.get('blockers') or [])
        risks = self._normalize_lines(payload.get('risks') or [])
        next_steps = self._normalize_lines(payload.get('next_steps') or [])
        pending_decisions = self._normalize_lines(payload.get('pending_decisions') or [])

        return {
            'decision': 'redraft',
            'status_summary': status_summary,
            'milestones': milestones,
            'blockers': blockers,
            'risks': risks,
            'next_steps': next_steps,
            'pending_decisions': pending_decisions,
            'quality_rationale': quality_rationale or False,
            'refusal_reason': False,
            'confidence': confidence,
        }

    def _request_llm_payload(self, project, deterministic_values):
        response_text = self.prompt_service._response_text(
            self.prompt_service._get_prompt_model(),
            LLM_STATUS_REDRAFT_INSTRUCTIONS,
            self._build_input_text(project, deterministic_values),
            _("Falha ao gerar redraft assistido de status com OpenAI: %s"),
            text_format=self._json_schema_format(),
        )
        try:
            payload = json.loads(response_text)
        except ValueError as exc:
            raise UserError(_("A OpenAI devolveu um payload invalido para status draft.")) from exc
        return self._normalize_payload(payload)

    def build_candidate(self, project, deterministic_values):
        if not self.should_attempt(project, deterministic_values):
            return False
        try:
            return self._request_llm_payload(project, deterministic_values)
        except UserError:
            _logger.exception("LLM status draft redraft failed")
            return False
