import re

from ..models.pg_project_chatter_signal import PG_CHATTER_SIGNAL_TYPE_SELECTION


LLM_SIGNAL_NEGATION_PATTERNS = {
    'approval': (r'\bnot approved\b', r'\brejected\b', r'\bdeclined\b', r'\bnao aprovad'),
    'decision': (r'\bno decision\b', r'\bsem decis'),
    'blocker': (r'\bno blockers?\b', r'\bsem bloque'),
    'risk': (r'\bno risk\b', r'\bsem risco'),
    'scope_change': (r'\bno scope change\b', r'\bsem altera'),
    'next_step': (r'\bno next step\b', r'\bsem proxim'),
    'dependency': (r'\bno dependenc', r'\bsem depend'),
}


class ProjectChatterValidationService:
    def __init__(self, env):
        self.env = env

    def _allowed_signal_types(self):
        return {value for value, _label in PG_CHATTER_SIGNAL_TYPE_SELECTION}

    def _validate_rule_based_signal(self, signal_values):
        summary = (signal_values.get('summary') or '').strip()
        if not summary:
            return {
                'signal_state': 'rejected',
                'validation_feedback': 'Rejected because the signal summary is empty.',
            }

        if (signal_values.get('confidence') or 0) >= 70:
            return {
                'signal_state': 'validated',
                'validation_feedback': 'Validated automatically from a high-confidence rule-based match.',
            }

        return {
            'signal_state': 'candidate',
            'validation_feedback': 'Candidate signal kept for review because confidence is below the validation threshold.',
        }

    def _validate_llm_signal(self, signal_values, source_text):
        signal_type = (signal_values.get('signal_type') or '').strip()
        summary = (signal_values.get('summary') or '').strip()
        rationale = (signal_values.get('llm_rationale') or '').strip()
        evidence_keywords = signal_values.get('llm_evidence_keywords') or []
        normalized_source_text = (source_text or '').strip().lower()

        if signal_type not in self._allowed_signal_types():
            return {
                'signal_state': 'rejected',
                'validation_feedback': 'Rejected because the LLM returned an unknown chatter signal type.',
            }

        if not summary:
            return {
                'signal_state': 'rejected',
                'validation_feedback': 'Rejected because the signal summary is empty.',
            }

        if not rationale:
            return {
                'signal_state': 'rejected',
                'validation_feedback': 'Rejected because the LLM classification is missing a rationale.',
            }

        if not isinstance(evidence_keywords, list) or not evidence_keywords:
            return {
                'signal_state': 'rejected',
                'validation_feedback': 'Rejected because the LLM classification is missing evidence keywords.',
            }

        cleaned_keywords = []
        for keyword in evidence_keywords[:3]:
            cleaned_keyword = (keyword or '').strip()
            if not cleaned_keyword:
                continue
            if cleaned_keyword.lower() not in normalized_source_text:
                return {
                    'signal_state': 'rejected',
                    'validation_feedback': 'Rejected because the LLM evidence keywords are not present in the source message.',
                }
            cleaned_keywords.append(cleaned_keyword)

        if not cleaned_keywords:
            return {
                'signal_state': 'rejected',
                'validation_feedback': 'Rejected because the LLM evidence keywords are empty after normalization.',
            }

        for pattern in LLM_SIGNAL_NEGATION_PATTERNS.get(signal_type, ()):
            if re.search(pattern, normalized_source_text, re.IGNORECASE):
                return {
                    'signal_state': 'rejected',
                    'validation_feedback': 'Rejected because the source message contradicts the LLM signal classification.',
                }

        if (signal_values.get('confidence') or 0) >= 70:
            return {
                'signal_state': 'validated',
                'validation_feedback': (
                    "Validated from an LLM-assisted ambiguous chatter classification. Evidence keywords: %s. Rationale: %s"
                    % (', '.join(cleaned_keywords), rationale)
                ),
            }

        return {
            'signal_state': 'candidate',
            'validation_feedback': (
                "Candidate LLM-assisted chatter signal kept for review. Evidence keywords: %s. Rationale: %s"
                % (', '.join(cleaned_keywords), rationale)
            ),
        }

    def validate_signal(self, signal_values, source_text=''):
        if signal_values.get('engine') == 'llm_hybrid':
            return self._validate_llm_signal(signal_values, source_text)
        return self._validate_rule_based_signal(signal_values)
