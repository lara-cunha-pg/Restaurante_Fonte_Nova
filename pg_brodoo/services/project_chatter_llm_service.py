import json
import logging
import re

from odoo import _
from odoo.exceptions import UserError

from .chatgpt_service import ChatGptPromptService
from .project_chatter_signal_service import SIGNAL_RULES

_logger = logging.getLogger(__name__)


LLM_AMBIGUOUS_HINT_PATTERNS = (
    r'\bmove forward\b',
    r'\bproceed\b',
    r'\bready to start\b',
    r'\bready to continue\b',
    r'\bconfirmed\b',
    r'\bconfirmou\b',
    r'\baligned\b',
    r'\balinhad[oa]s?\b',
    r'\bnext (monday|tuesday|wednesday|thursday|friday|week)\b',
    r'\bproxima semana\b',
    r'\bnext sprint\b',
    r'\breview closes\b',
    r'\bafter review\b',
    r'\bfinance\b',
    r'\bsecurity\b',
    r'\blegal\b',
    r'\bvendor\b',
)

LLM_CLASSIFIER_INSTRUCTIONS = """Classify one ambiguous Odoo project chatter message.

Rules:
- Return strict JSON only.
- Use only facts that are explicitly present in the message.
- Never invent blockers, approvals, decisions, dependencies, risks or next steps.
- A signal is allowed only when the message clearly supports it.
- Evidence keywords must be exact substrings copied from the message.
- Return an empty signals array when the message is not reliable enough.
- Allowed signal types are: blocker, risk, decision, approval, scope_change, next_step, dependency.
- Return at most 3 signals.

JSON schema:
{
  "signals": [
    {
      "signal_type": "blocker|risk|decision|approval|scope_change|next_step|dependency",
      "confidence": 0-100,
      "rationale": "short justification grounded in the message",
      "evidence_keywords": ["exact substring", "exact substring"]
    }
  ]
}
"""


class ProjectChatterLlmService:
    def __init__(self, env):
        self.env = env
        self.prompt_service = ChatGptPromptService(env)

    def _is_enabled(self):
        return bool((self.prompt_service._get_param('pg_openai_api_key') or '').strip())

    def _extract_summary(self, text):
        parts = re.split(r'(?<=[\.\!\?])\s+|\n+', text or '')
        for part in parts:
            summary = (part or '').strip()
            if len(summary) >= 12:
                return summary[:180]
        return (text or '').strip()[:180]

    def _build_excerpt(self, text):
        return (text or '').strip()[:300]

    def should_attempt(self, filtered_message, rule_candidates):
        if rule_candidates or not self._is_enabled():
            return False
        normalized_text = (filtered_message.get('normalized_text') or '').strip()
        if len(normalized_text) < 50:
            return False
        return any(re.search(pattern, normalized_text, re.IGNORECASE) for pattern in LLM_AMBIGUOUS_HINT_PATTERNS)

    def _build_input_text(self, filtered_message):
        normalized_text = (filtered_message.get('normalized_text') or '').strip()
        allowed_types = ', '.join(SIGNAL_RULES.keys())
        return (
            "Source model: %s\n"
            "Visibility: %s\n"
            "Allowed signal types: %s\n"
            "Message:\n%s"
        ) % (
            filtered_message.get('source_model') or '',
            filtered_message.get('visibility') or 'internal',
            allowed_types,
            normalized_text,
        )

    def _request_llm_payload(self, filtered_message):
        response_text = self.prompt_service._response_text(
            self.prompt_service._get_prompt_model(),
            LLM_CLASSIFIER_INSTRUCTIONS,
            self._build_input_text(filtered_message),
            _("Falha ao classificar mensagens ambiguas do chatter com OpenAI: %s"),
        )
        try:
            payload = json.loads(response_text)
        except ValueError as exc:
            raise UserError(_("A OpenAI devolveu um payload invalido para a classificacao de chatter.")) from exc
        if not isinstance(payload, dict):
            raise UserError(_("A OpenAI devolveu um payload de chatter fora do schema esperado."))
        return payload

    def _normalize_confidence(self, value):
        try:
            return max(0, min(int(value), 100))
        except (TypeError, ValueError):
            return 0

    def classify_ambiguous_message(self, filtered_message):
        try:
            payload = self._request_llm_payload(filtered_message)
        except UserError:
            _logger.exception("LLM chatter classification failed")
            return []

        raw_signals = payload.get('signals') or []
        if not isinstance(raw_signals, list):
            return []

        normalized_text = filtered_message.get('normalized_text') or ''
        summary = self._extract_summary(normalized_text)
        excerpt = self._build_excerpt(normalized_text)
        content_hash = filtered_message.get('content_hash')
        seen_types = set()
        candidates = []

        for raw_signal in raw_signals[:3]:
            if not isinstance(raw_signal, dict):
                continue
            signal_type = (raw_signal.get('signal_type') or '').strip()
            if not signal_type or signal_type in seen_types:
                continue
            candidates.append(
                {
                    'signal_type': signal_type,
                    'summary': summary,
                    'evidence_excerpt': excerpt,
                    'confidence': self._normalize_confidence(raw_signal.get('confidence')),
                    'author_id': filtered_message.get('author_id'),
                    'occurred_at': filtered_message.get('occurred_at'),
                    'visibility': filtered_message.get('visibility') or 'internal',
                    'engine': 'llm_hybrid',
                    'content_hash': content_hash,
                    'llm_rationale': (raw_signal.get('rationale') or '').strip(),
                    'llm_evidence_keywords': raw_signal.get('evidence_keywords') or [],
                }
            )
            seen_types.add(signal_type)
        return candidates
