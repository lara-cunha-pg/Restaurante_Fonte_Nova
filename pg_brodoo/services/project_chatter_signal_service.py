import re


SIGNAL_RULES = {
    'blocker': {
        'patterns': [
            r'\bblocked?\b',
            r'\bblocker\b',
            r'\bbloquead[oa]s?\b',
            r'\bimpediment[oa]s?\b',
            r'\bwaiting for\b',
            r'\baguardamos\b',
        ],
        'strong_patterns': [r'\bblocked until\b', r'\bbloquead[oa] at[eé]\b'],
    },
    'risk': {
        'patterns': [
            r'\brisk\b',
            r'\brisco\b',
            r'\bconcern\b',
            r'\bpreocup',
            r'\bmay delay\b',
            r'\batras',
        ],
        'strong_patterns': [r'\bhigh risk\b', r'\brisco alto\b'],
    },
    'decision': {
        'patterns': [
            r'\bdecid',
            r'\bficou decidido\b',
            r'\bagreed\b',
            r'\bacordad[oa]s?\b',
            r'\boptamos\b',
        ],
        'strong_patterns': [r'\bfinal decision\b', r'\bdecis[aã]o final\b'],
    },
    'approval': {
        'patterns': [
            r'\bapproved?\b',
            r'\bapproval\b',
            r'\baprovad[oa]s?\b',
            r'\bvalidad[oa]s?\b',
            r'\bsign[- ]off\b',
            r'\bgreen light\b',
        ],
        'strong_patterns': [r'\bapproved for production\b', r'\baprovado para produ'],
        'exclude_patterns': [
            r'\bwaiting for\b.*\bapproval\b',
            r'\bawaiting\b.*\bapproval\b',
            r'\bpending\b.*\bapproval\b',
            r'\ba aguardar\b.*\baprova',
            r'\baguarda\b.*\baprova',
            r'\bpendente\b.*\baprova',
        ],
    },
    'scope_change': {
        'patterns': [
            r'\bscope change\b',
            r'\bchange request\b',
            r'\baltera[cç][aã]o de [aâ]mbito\b',
            r'\bfora do [aâ]mbito\b',
            r'\bout of scope\b',
            r'\bextra scope\b',
        ],
        'strong_patterns': [r'\bapproved scope change\b', r'\baltera[cç][aã]o de [aâ]mbito aprovada\b'],
    },
    'next_step': {
        'patterns': [
            r'\bnext step[s]?\b',
            r'\bpr[oó]ximos passos\b',
            r'\bfollow[- ]up\b',
            r'\baction item[s]?\b',
        ],
        'strong_patterns': [r'\bnext step is\b', r'\bo pr[oó]ximo passo\b'],
    },
    'dependency': {
        'patterns': [
            r'\bdepends on\b',
            r'\bdepends on customer\b',
            r'\bdependency\b',
            r'\bdepend[eê]ncia\b',
            r'\bdepende de\b',
            r'\bdepende do cliente\b',
            r'\bthird[- ]party\b',
            r'\bfornecedor\b',
        ],
        'strong_patterns': [r'\bblocked by customer\b', r'\bdepende do cliente\b'],
    },
}


class ProjectChatterSignalService:
    def __init__(self, env):
        self.env = env

    def _has_excluded_context(self, text, rules):
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in rules.get('exclude_patterns', []))

    def _extract_summary(self, text):
        parts = re.split(r'(?<=[\.\!\?])\s+|\n+', text or '')
        for part in parts:
            summary = (part or '').strip()
            if len(summary) >= 12:
                return summary[:180]
        return (text or '').strip()[:180]

    def _build_excerpt(self, text):
        return (text or '').strip()[:300]

    def _compute_confidence(self, filtered_message, match_count, has_strong_match):
        confidence = 48
        confidence += min(20, match_count * 6)
        if filtered_message.get('visibility') == 'internal':
            confidence += 8
        if len(filtered_message.get('normalized_text') or '') >= 60:
            confidence += 6
        if has_strong_match:
            confidence += 10
        return min(confidence, 95)

    def build_signal_candidates(self, filtered_message):
        text = filtered_message.get('normalized_text') or ''
        signals = []
        for signal_type, rules in SIGNAL_RULES.items():
            if self._has_excluded_context(text, rules):
                continue
            matches = [pattern for pattern in rules['patterns'] if re.search(pattern, text, re.IGNORECASE)]
            if not matches:
                continue
            has_strong_match = any(
                re.search(pattern, text, re.IGNORECASE) for pattern in rules.get('strong_patterns', [])
            )
            signals.append(
                {
                    'signal_type': signal_type,
                    'summary': self._extract_summary(text),
                    'evidence_excerpt': self._build_excerpt(text),
                    'confidence': self._compute_confidence(filtered_message, len(matches), has_strong_match),
                    'author_id': filtered_message.get('author_id'),
                    'occurred_at': filtered_message.get('occurred_at'),
                    'visibility': filtered_message.get('visibility') or 'internal',
                    'engine': 'rule_based',
                    'content_hash': filtered_message.get('content_hash'),
                }
            )
        return signals
