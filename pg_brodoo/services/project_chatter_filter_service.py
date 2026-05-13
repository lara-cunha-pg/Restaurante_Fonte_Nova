import hashlib
import re

from .text_hygiene import has_suspicious_mojibake
from .text_hygiene import sanitize_message_body


NOISE_PATTERNS = [
    r'^a new task has been created\b',
    r'^a new project has been created\b',
    r'^task created\b',
    r'^project created\b',
    r'^stage changed\b',
    r'^assigned to\b',
    r'^deadline changed\b',
    r'^seguidores?:?\b',
    r'^follower\b',
    r'^atividade\b',
    r'^tarefa criada\b',
    r'^projeto criado\b',
    r'^etapa alterada\b',
    r'^atribu[ií]do a\b',
    r'^prazo alterado\b',
]
TRACKING_NOISE_PATTERNS = [
    r'^(?:deadline|prazo)\b.+\b(?:changed|updated|set to|alterad[oa]|atualizad[oa]|definid[oa])\b',
    r'^(?:stage|status|state|etapa|estado)\b.+\b(?:changed|updated|set to|alterad[oa]|atualizad[oa]|definid[oa])\b',
    r'^(?:priority|prioridade)\b.+\b(?:changed|updated|set to|alterad[oa]|atualizad[oa]|definid[oa])\b',
    r'^(?:assigned to|unassigned from|atribu[iÃ­]do a|removido de)\b',
    r'^(?:milestone|marco)\b.+\b(?:changed|updated|set to|alterad[oa]|atualizad[oa]|definid[oa])\b',
    r'^(?:field|fields|campo|campos)\b.+\b(?:changed|updated|alterad[oa]s?|atualizad[oa]s?)\b',
    r'\b(?:old value|new value|valor anterior|novo valor)\b',
]
SYSTEM_BODY_MARKERS = (
    'o_mail_notification',
    'o_thread_message_notification',
    'mail_tracking_value',
    'o_field_widget',
)

class ProjectChatterFilterService:
    def __init__(self, env):
        self.env = env

    def _normalize_text(self, body):
        return sanitize_message_body(body, max_chars=1200)

    def _looks_like_noise(self, text):
        if not text or len(text) < 12:
            return True
        if has_suspicious_mojibake(text):
            return True
        lowered = text.lower()
        return any(re.search(pattern, lowered) for pattern in NOISE_PATTERNS)

    def _looks_like_tracking_noise(self, message, text):
        lowered = (text or '').lower()
        if any(re.search(pattern, lowered) for pattern in TRACKING_NOISE_PATTERNS):
            return True
        if getattr(message, 'tracking_value_ids', False) and len(lowered.split()) <= 40:
            return True
        return False

    def _has_system_wrapper_noise(self, message):
        raw_body = (message.body or '').lower()
        return any(marker in raw_body for marker in SYSTEM_BODY_MARKERS)

    def _is_human_message(self, message):
        if message.message_type == 'notification':
            return False
        if not message.author_id and not message.email_from:
            return False
        return True

    def _visibility_for_message(self, message):
        if message.subtype_id and message.subtype_id.internal and self._is_internal_message_author(message):
            return 'internal'
        if message.message_type == 'email':
            return 'external'
        return 'internal'

    def _is_internal_message_author(self, message):
        author = message.author_id
        if not author:
            return False
        if author.user_ids:
            return True
        company_partner = self.env.company.partner_id.commercial_partner_id
        return author.commercial_partner_id == company_partner

    def filter_message(self, message):
        if message.model not in {'project.project', 'project.task'}:
            return False
        if message.message_type not in {'comment', 'email'}:
            return False
        if not self._is_human_message(message):
            return False
        if self._has_system_wrapper_noise(message):
            return False

        normalized_text = self._normalize_text(message.body)
        if self._looks_like_noise(normalized_text):
            return False
        if self._looks_like_tracking_noise(message, normalized_text):
            return False

        content_hash = hashlib.sha1(normalized_text.encode('utf-8')).hexdigest()
        return {
            'message_id': message.id,
            'source_model': message.model,
            'source_record_id': message.res_id,
            'author_id': message.author_id.id or False,
            'occurred_at': message.date,
            'visibility': self._visibility_for_message(message),
            'normalized_text': normalized_text,
            'content_hash': content_hash,
        }

    def filter_messages(self, messages):
        filtered = []
        for message in messages:
            payload = self.filter_message(message)
            if payload:
                filtered.append(payload)
        return filtered
