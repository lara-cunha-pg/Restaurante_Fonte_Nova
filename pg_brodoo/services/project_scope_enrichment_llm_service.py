import json
import logging

from odoo import _
from odoo.exceptions import UserError

from .chatgpt_service import ChatGptPromptService
from .text_hygiene import is_low_signal_scope_summary
from .text_hygiene import is_placeholder_text
from .text_hygiene import normalize_inline_text
from .text_hygiene import sanitize_plaintext
from .text_hygiene import split_unique_text_lines

_logger = logging.getLogger(__name__)


LLM_SCOPE_ENRICHMENT_INSTRUCTIONS = """Review one weak Odoo scope enrichment draft.

Rules:
- Return strict JSON only.
- Use only facts explicitly present in the input.
- Never invent requirements, integrations, fields, reports, workflows or acceptance criteria.
- Refuse when the task is not atomic, mixes multiple deliveries, is just a meeting/kickoff/context note, or does not support one reliable scope item.
- Keep the summary factual, compact, in Portuguese and suitable for one scope draft.
- Acceptance criteria must be testable and grounded in the input.
- Return at most 3 acceptance criteria.
- Return an empty acceptance_criteria_suggested array when you refuse.
- Never return placeholders, workflow text or implementation guidance.
- Never return meta-work text such as "analyze the email", "provide feedback", or similar.

JSON schema:
{
  "decision": "suggest|refuse",
  "is_atomic": true,
  "should_apply_without_review": false,
  "scope_summary_suggested": "string",
  "acceptance_criteria_suggested": ["string"],
  "quality_rationale": "string",
  "confidence": 0,
  "refusal_reason": "string"
}
"""


class ProjectScopeEnrichmentLlmService:
    def __init__(self, env):
        self.env = env
        self.prompt_service = ChatGptPromptService(env)

    def _is_enabled(self):
        return bool((self.prompt_service._get_param('pg_openai_api_key') or '').strip())

    def _json_schema_format(self):
        return {
            'type': 'json_schema',
            'name': 'scope_enrichment_draft',
            'strict': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'decision': {
                        'type': 'string',
                        'enum': ['suggest', 'refuse'],
                    },
                    'is_atomic': {'type': 'boolean'},
                    'should_apply_without_review': {'type': 'boolean'},
                    'scope_summary_suggested': {'type': 'string'},
                    'acceptance_criteria_suggested': {
                        'type': 'array',
                        'items': {'type': 'string'},
                    },
                    'quality_rationale': {'type': 'string'},
                    'confidence': {'type': 'integer'},
                    'refusal_reason': {'type': 'string'},
                },
                'required': [
                    'decision',
                    'is_atomic',
                    'should_apply_without_review',
                    'scope_summary_suggested',
                    'acceptance_criteria_suggested',
                    'quality_rationale',
                    'confidence',
                    'refusal_reason',
                ],
                'additionalProperties': False,
            },
        }

    def _task_description(self, task):
        return sanitize_plaintext(task.description, from_html=True, max_chars=1400, strip_email_noise=True)

    def _normalized_criteria_lines(self, value):
        return split_unique_text_lines(
            value,
            from_html=False,
            max_items=3,
            max_line_chars=180,
            strip_email_noise=True,
        )

    def _task_name_supports_llm(self, task_name):
        normalized = normalize_inline_text(task_name, fallback='', max_chars=120, drop_placeholders=True)
        if not normalized or is_low_signal_scope_summary(normalized):
            return False
        tokens = [token for token in normalized.split(' ') if token]
        return len(tokens) >= 2

    def _has_minimum_input(self, task, chatter_context=False):
        task_name = normalize_inline_text(task.name, fallback='', max_chars=120, drop_placeholders=True)
        description = self._task_description(task)
        hints = chatter_context.get('hint_summaries') if chatter_context else []
        return bool(description or self._task_name_supports_llm(task_name) or hints)

    def should_attempt(self, task, rule_based_suggestions, chatter_context=False):
        if not self._is_enabled():
            return False
        if not self._has_minimum_input(task, chatter_context=chatter_context or {}):
            return False
        if not rule_based_suggestions.get('_llm_eligible', True):
            return False

        status = (rule_based_suggestions.get('pg_scope_enrichment_status') or '').strip()
        summary = rule_based_suggestions.get('pg_scope_summary_suggested')
        criteria = rule_based_suggestions.get('pg_acceptance_criteria_suggested_text')

        if status == 'needs_review':
            return True
        if is_low_signal_scope_summary(summary):
            return True
        if not self._normalized_criteria_lines(criteria):
            return True
        return False

    def _build_input_text(self, task, rule_based_suggestions, chatter_context=False):
        task_name = normalize_inline_text(task.name, fallback='', max_chars=120, drop_placeholders=True)
        description = self._task_description(task)
        summary = normalize_inline_text(
            rule_based_suggestions.get('pg_scope_summary_suggested'),
            fallback='',
            max_chars=220,
            drop_placeholders=True,
        )
        criteria_lines = self._normalized_criteria_lines(rule_based_suggestions.get('pg_acceptance_criteria_suggested_text'))
        chatter_lines = []
        if chatter_context and chatter_context.get('hint_summaries'):
            for hint in chatter_context['hint_summaries'][:3]:
                normalized_hint = normalize_inline_text(hint, fallback='', max_chars=180, drop_placeholders=True)
                if normalized_hint:
                    chatter_lines.append(normalized_hint)

        return (
            "Task name: %s\n"
            "Task description:\n%s\n\n"
            "Rule-based scope summary: %s\n"
            "Rule-based acceptance criteria:\n- %s\n\n"
            "Validated chatter hints:\n- %s\n\n"
            "Return a stronger suggestion only if the input supports it."
        ) % (
            task_name or '(empty)',
            description or '(empty)',
            summary or '(empty)',
            '\n- '.join(criteria_lines) if criteria_lines else '(empty)',
            '\n- '.join(chatter_lines) if chatter_lines else '(empty)',
        )

    def _normalize_confidence(self, value):
        try:
            return max(0, min(int(value), 100))
        except (TypeError, ValueError):
            return 0

    def _contains_meta_work_text(self, value):
        lowered = normalize_inline_text(value, fallback='', max_chars=False, drop_placeholders=True).lower()
        if not lowered:
            return False
        meta_needles = (
            'analyze the attached email',
            'analyse the attached email',
            'provide feedback',
            'feedback is provided',
            'email is analyzed',
            'review the attached',
            'review the email',
            'analisar o email',
            'dar feedback',
        )
        return any(needle in lowered for needle in meta_needles)

    def _normalize_payload(self, payload):
        if not isinstance(payload, dict):
            raise UserError(_("A OpenAI devolveu um payload de scope enrichment fora do schema esperado."))

        decision = (payload.get('decision') or '').strip()
        if decision not in ('suggest', 'refuse'):
            raise UserError(_("A OpenAI devolveu uma decisao invalida para scope enrichment."))

        rationale = normalize_inline_text(
            payload.get('quality_rationale'),
            fallback='',
            max_chars=220,
            drop_placeholders=True,
        )
        refusal_reason = normalize_inline_text(
            payload.get('refusal_reason'),
            fallback='',
            max_chars=220,
            drop_placeholders=True,
        )
        confidence = self._normalize_confidence(payload.get('confidence'))
        is_atomic = bool(payload.get('is_atomic'))
        should_apply_without_review = bool(payload.get('should_apply_without_review'))

        if decision == 'refuse' or not is_atomic:
            return {
                'decision': 'refuse',
                'refusal_reason': refusal_reason or rationale or False,
                'quality_rationale': rationale or False,
                'confidence': confidence,
                'is_atomic': is_atomic,
                'should_apply_without_review': False,
            }

        summary = normalize_inline_text(
            payload.get('scope_summary_suggested'),
            fallback='',
            max_chars=220,
            drop_placeholders=True,
        )
        if not summary or is_placeholder_text(summary) or self._contains_meta_work_text(summary):
            raise UserError(_("A OpenAI devolveu um scope summary invalido para scope enrichment."))

        criteria = []
        raw_criteria = payload.get('acceptance_criteria_suggested') or []
        if not isinstance(raw_criteria, list):
            raise UserError(_("A OpenAI devolveu acceptance criteria fora do schema esperado."))
        for criterion in raw_criteria[:3]:
            normalized = normalize_inline_text(criterion, fallback='', max_chars=180, drop_placeholders=True)
            if not normalized or is_placeholder_text(normalized) or self._contains_meta_work_text(normalized):
                continue
            if normalized == summary or normalized in criteria:
                continue
            criteria.append(normalized.rstrip('.'))
        if not criteria:
            raise UserError(_("A OpenAI devolveu um draft de scope enrichment sem criterios testaveis suficientes."))

        return {
            'decision': 'suggest',
            'scope_summary_suggested': summary,
            'acceptance_criteria_suggested': criteria,
            'quality_rationale': rationale or False,
            'confidence': confidence,
            'refusal_reason': False,
            'is_atomic': True,
            'should_apply_without_review': should_apply_without_review,
        }

    def _request_llm_payload(self, task, rule_based_suggestions, chatter_context=False):
        response_text = self.prompt_service._response_text(
            self.prompt_service._get_prompt_model(),
            LLM_SCOPE_ENRICHMENT_INSTRUCTIONS,
            self._build_input_text(task, rule_based_suggestions, chatter_context=chatter_context or {}),
            _("Falha ao gerar draft assistido de scope enrichment com OpenAI: %s"),
            text_format=self._json_schema_format(),
        )
        try:
            payload = json.loads(response_text)
        except ValueError as exc:
            raise UserError(_("A OpenAI devolveu um payload invalido para scope enrichment.")) from exc
        return self._normalize_payload(payload)

    def build_candidate(self, task, rule_based_suggestions, chatter_context=False):
        if not self.should_attempt(task, rule_based_suggestions, chatter_context=chatter_context or {}):
            return False
        try:
            return self._request_llm_payload(task, rule_based_suggestions, chatter_context=chatter_context or {})
        except UserError:
            _logger.exception("LLM scope enrichment candidate generation failed")
            return False
