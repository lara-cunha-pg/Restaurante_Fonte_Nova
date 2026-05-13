import re

from .project_chatter_grounding_service import ProjectChatterGroundingService
from .project_scope_enrichment_llm_service import ProjectScopeEnrichmentLlmService
from .text_hygiene import normalize_inline_text
from .text_hygiene import sanitize_plaintext
from .text_hygiene import split_unique_text_lines


class ProjectScopeEnrichmentService:
    KIND_KEYWORD_MAP = {
        'integration': (
            'api',
            'endpoint',
            'external',
            'github',
            'interface',
            'integrat',
            'sync',
            'webhook',
        ),
        'report': (
            'dashboard',
            'indicador',
            'kpi',
            'mapa',
            'metric',
            'pivot',
            'relat',
            'report',
        ),
        'migration': (
            'convers',
            'export',
            'import',
            'legacy',
            'legado',
            'migr',
        ),
        'data': (
            'base de dados',
            'campo',
            'data',
            'dataset',
            'modelo',
            'modelo de dados',
            'tabela',
        ),
        'training': (
            'adocao',
            'adoção',
            'formacao',
            'formação',
            'treino',
            'training',
            'workshop',
        ),
        'technical': (
            'bug',
            'ci/cd',
            'deploy',
            'infra',
            'performance',
            'refactor',
            'security',
            'seguranca',
            'segurança',
            'tecnico',
            'técnico',
            'upgrade',
        ),
        'process': (
            'approval',
            'aprov',
            'process',
            'workflow',
        ),
    }

    GENERIC_TITLE_TOKENS = {
        'task',
        'tarefa',
        'teste',
        'todo',
        'ajuste',
        'melhoria',
        'implementacao',
        'implementação',
        'validacao',
        'validação',
    }
    AGGREGATE_TITLE_HINTS = (
        'arranque',
        'email',
        'seguimento',
        'reuni',
        'kick off',
        'kickoff',
        'ponto situa',
        'documento',
        'projeto',
        'requisitos',
        'workshop',
        'sessao',
        'sessÃ£o',
    )
    AGGREGATE_SECTION_HINTS = (
        'notas:',
        'utilizadores',
        'utilizadores e perfis',
        'postos:',
        'stocks',
        'crm',
        'fases:',
        'urgente',
        'futuro',
    )
    ACCEPTANCE_LINE_PREFIXES = (
        'o utilizador deve',
        'o processo deve',
        'a lista ',
        'as melhorias ',
        'os contactos ',
        'o email ',
        'deve ser possivel',
        'deve ser possível',
    )
    OBJECTIVE_HINTS = (
        'automat',
        'atualiz',
        'calcular',
        'configur',
        'copiar',
        'colar',
        'corrig',
        'criar',
        'desenvolv',
        'garant',
        'gerar',
        'implement',
        'import',
        'investig',
        'manter',
        'monitor',
        'parar',
        'permit',
        'rever',
        'sincron',
        'valid',
        'visualiz',
    )
    FEATURE_FRAGMENT_HINTS = (
        'api',
        'armaz',
        'automat',
        'configur',
        'dashboard',
        'dados',
        'excel',
        'export',
        'github',
        'import',
        'integr',
        'interface',
        'kpi',
        'legado',
        'migr',
        'produc',
        'relat',
        'sincron',
        'stock',
        'vendas',
        'workflow',
    )
    EMAIL_GREETING_PREFIXES = (
        'bom dia',
        'boa tarde',
        'boa noite',
        'caro ',
        'cara ',
        'ola ',
        'olá ',
    )
    EMAIL_CONTEXT_HINTS = (
        'aguardo uma resposta',
        'analisa',
        'conforme conversado',
        'dar feedback',
        'dá-me feedback',
        'darmos inicio',
        'darmos início',
        'de-me feedback',
        'dê-me feedback',
        'envio em anexo',
        'fico a aguardar',
        'informacao solicitada',
        'informação solicitada',
        'penso ja ter fornecido',
        'penso já ter fornecido',
        'proxima fase',
        'próxima fase',
        'proximos passos',
        'próximos passos',
        'qualquer duvida',
        'qualquer dúvida',
    )
    EMAIL_SIGNOFF_HINTS = (
        'com os melhores cumprimentos',
        'cumprimentos',
        'obrigado',
        'obrigada',
    )

    def __init__(self, env):
        self.env = env
        self.chatter_grounding_service = ProjectChatterGroundingService(env)
        self.llm_service = ProjectScopeEnrichmentLlmService(env)

    def _normalize_text(self, value):
        return normalize_inline_text(value, fallback='')

    def _split_sentences(self, value):
        normalized = self._normalize_text(value)
        if not normalized:
            return []
        return [sentence.strip() for sentence in re.split(r'(?<=[\.\!\?])\s+', normalized) if sentence.strip()]

    def _split_lines(self, value):
        return split_unique_text_lines(value, max_items=12, max_line_chars=220)

    def _task_plaintext_description(self, task):
        return sanitize_plaintext(task.description, from_html=True, max_chars=1600, strip_email_noise=True)

    def _task_description_lines(self, task, max_items=12):
        return split_unique_text_lines(
            task.description,
            from_html=True,
            max_items=max_items,
            max_line_chars=220,
            strip_email_noise=True,
        )

    def _task_corpus(self, task, chatter_context=False):
        parts = [
            self._normalize_text(task.name),
            self._task_plaintext_description(task),
            ' '.join(task.tag_ids.mapped('name')),
        ]
        if chatter_context and chatter_context.get('hint_summaries'):
            parts.append(' '.join(chatter_context['hint_summaries']))
        return normalize_inline_text(' '.join(part for part in parts if part), fallback='', max_chars=2200)

    def _name_is_generic(self, value):
        tokens = {
            token.strip().lower()
            for token in re.split(r'[\W_]+', value or '')
            if token.strip()
        }
        return bool(tokens) and tokens.issubset(self.GENERIC_TITLE_TOKENS)

    def _title_indicates_aggregate_task(self, task):
        title = self._normalize_text(task.name).lower()
        if not title:
            return False
        if self._name_is_generic(title):
            return True
        return any(hint in title for hint in self.AGGREGATE_TITLE_HINTS)

    def _looks_like_acceptance_line(self, line):
        lowered = self._normalize_text(line).lower()
        return any(lowered.startswith(prefix) for prefix in self.ACCEPTANCE_LINE_PREFIXES)

    def _looks_like_objective_line(self, line):
        lowered = self._normalize_text(line).lower()
        if not lowered or self._looks_like_acceptance_line(lowered):
            return False
        if lowered.endswith(':'):
            return False
        return any(hint in lowered for hint in self.OBJECTIVE_HINTS)

    def _looks_like_non_testable_criteria(self, criteria_lines):
        if not criteria_lines:
            return True
        for line in criteria_lines:
            lowered = self._normalize_text(line).lower()
            if len(lowered.split()) <= 3:
                return True
            if not any(token in lowered for token in ('deve', 'permite', 'fica', 'estar', 'reflet', 'criad', 'importad', 'configur')):
                return True
        return False

    def _normalize_similarity_tokens(self, value):
        normalized = self._normalize_text(value).lower()
        normalized = re.sub(
            r'^(?:o utilizador deve conseguir|o processo deve refletir|o processo deve suportar|deve ser possivel|deve ser possível)\s+',
            '',
            normalized,
        )
        return {
            token
            for token in re.split(r'[\W_]+', normalized)
            if token and len(token) > 2
        }

    def _text_similarity_ratio(self, left, right):
        left_tokens = self._normalize_similarity_tokens(left)
        right_tokens = self._normalize_similarity_tokens(right)
        if not left_tokens or not right_tokens:
            return 0.0
        shared = len(left_tokens & right_tokens)
        return shared / float(max(len(left_tokens), len(right_tokens)))

    def _looks_like_feature_fragment(self, line):
        lowered = self._normalize_text(line).lower()
        if not lowered:
            return False
        if self._looks_like_acceptance_line(lowered):
            return False
        if self._looks_like_email_context_line(lowered):
            return False
        if lowered.endswith(':'):
            return False
        if len(lowered.split()) < 3:
            return False
        return any(hint in lowered for hint in self.FEATURE_FRAGMENT_HINTS) or self._looks_like_objective_line(lowered)

    def _criterion_from_fragment(self, fragment):
        cleaned = self._normalize_text(fragment).rstrip('.')
        if not cleaned:
            return ''
        lowered = cleaned.lower()
        if self._looks_like_acceptance_line(lowered):
            return cleaned if cleaned.endswith('.') else f"{cleaned}."
        return f"O processo deve suportar {lowered}."

    def _criteria_are_redundant(self, summary, criteria_lines, description_lines):
        if not criteria_lines:
            return False
        if len(description_lines or []) < 2:
            return False

        summary_ratio_hits = 0
        duplicate_pairs = 0
        for index, line in enumerate(criteria_lines):
            if self._text_similarity_ratio(summary, line) >= 0.8:
                summary_ratio_hits += 1
            for other in criteria_lines[index + 1:]:
                if self._text_similarity_ratio(line, other) >= 0.8:
                    duplicate_pairs += 1
        return summary_ratio_hits >= 1 or duplicate_pairs >= 1

    def _looks_like_email_context_line(self, line):
        lowered = self._normalize_text(line).lower()
        if not lowered:
            return False
        if any(lowered.startswith(prefix) for prefix in self.EMAIL_GREETING_PREFIXES):
            return True
        if any(hint in lowered for hint in self.EMAIL_CONTEXT_HINTS):
            return True
        if any(hint in lowered for hint in self.EMAIL_SIGNOFF_HINTS):
            return True
        return False

    def _summary_looks_like_email_followup(self, summary):
        lowered = self._normalize_text(summary).lower()
        if not lowered:
            return False
        if any(lowered.startswith(prefix) for prefix in self.EMAIL_GREETING_PREFIXES):
            return True
        return any(hint in lowered for hint in self.EMAIL_CONTEXT_HINTS)

    def _assess_scope_draft_quality(self, task, summary, criteria_lines):
        description_lines = self._task_description_lines(task, max_items=16)
        objective_lines = [line for line in description_lines if self._looks_like_objective_line(line)]
        email_context_hits = sum(1 for line in description_lines[:6] if self._looks_like_email_context_line(line))
        opening_email_context_hits = sum(1 for line in description_lines[:3] if self._looks_like_email_context_line(line))
        section_hits = sum(
            1
            for line in description_lines
            if any(marker in self._normalize_text(line).lower() for marker in self.AGGREGATE_SECTION_HINTS)
        )
        flags = []
        llm_eligible = True

        if self._title_indicates_aggregate_task(task):
            flags.append('A task parece ser agregada ou contextual pelo titulo e deve ficar em revisao manual.')
            llm_eligible = False
        if len(objective_lines) >= 3:
            flags.append('A descricao mistura varios objetivos fortes e nao suporta um unico scope item aplicavel.')
            llm_eligible = False
        if section_hits >= 2:
            flags.append('A descricao contem varias secoes ou listagens, sinal de contexto agregado.')
            llm_eligible = False
        if self._summary_looks_like_email_followup(summary):
            flags.append('O resumo sugerido ainda parece um email ou follow-up contextual e deve ficar em revisao manual.')
            llm_eligible = False
        if email_context_hits >= 2:
            flags.append('A descricao ainda esta dominada por linguagem de email, follow-up ou pedido de feedback.')
            llm_eligible = False
        if email_context_hits >= 1 and len(objective_lines) <= 1:
            flags.append('A task parece ser sobretudo um follow-up contextual ou email sem entrega funcional suficientemente explicita.')
            llm_eligible = False
        if opening_email_context_hits >= 1 and len(description_lines) <= 5:
            flags.append('A descricao abre como email contextual curto e nao deve ser promovida automaticamente para draft ready.')
            llm_eligible = False
        if (summary or '').endswith('...'):
            flags.append('O resumo sugerido ficou truncado e nao deve ser aplicado sem revisao.')
        if len(criteria_lines) < 2 and (len(objective_lines) >= 2 or len(description_lines) >= 5):
            flags.append('Os criterios sugeridos cobrem pouco da task e ficaram incompletos para o conteudo atual.')
        if self._looks_like_non_testable_criteria(criteria_lines):
            flags.append('Os criterios sugeridos nao estao suficientemente testaveis para draft ready.')
        if self._criteria_are_redundant(summary, criteria_lines, description_lines):
            flags.append('Os criterios sugeridos continuam demasiado proximos do resumo ou demasiado repetidos entre si.')

        return {
            'flags': flags,
            'force_review': bool(flags),
            'llm_eligible': llm_eligible,
        }

    def _collect_chatter_context(self, task):
        context = {
            'used': False,
            'stale': False,
            'hint_summaries': [],
            'signal_ids': [],
            'counts': {
                'scope_changes': 0,
                'approvals': 0,
                'decisions': 0,
            },
        }
        if getattr(task, 'pg_chatter_signals_dirty', False):
            context['stale'] = True
            return context

        grounding = self.chatter_grounding_service.build_task_grounding(task, days=30)
        seen = set()
        for bucket_name in ('scope_changes', 'approvals', 'decisions'):
            bucket_items = grounding.get(bucket_name) or []
            context['counts'][bucket_name] += len(bucket_items)
            for item in bucket_items:
                summary = self._normalize_text(item.get('summary'))
                if summary and summary not in seen:
                    seen.add(summary)
                    context['hint_summaries'].append(summary)
        context['signal_ids'] = [signal['id'] for signal in grounding.get('all_signals', [])]
        context['used'] = bool(context['hint_summaries'])
        return context

    def _build_explainability(self, chatter_context):
        if chatter_context.get('stale'):
            return {
                'pg_scope_enrichment_signal_ids': [(5, 0, 0)],
                'pg_scope_enrichment_signal_feedback': (
                    "No chatter signals were attached to this scope draft because the chatter cache is stale for the task."
                ),
            }

        if not chatter_context.get('signal_ids'):
            return {
                'pg_scope_enrichment_signal_ids': [(5, 0, 0)],
                'pg_scope_enrichment_signal_feedback': (
                    "No validated chatter signals were used when this scope draft was generated."
                ),
            }

        lines = [
            "Validated chatter signals linked to this scope draft: %s." % len(chatter_context['signal_ids']),
        ]
        for summary in chatter_context.get('hint_summaries', [])[:5]:
            lines.append("Signal: %s" % summary)
        return {
            'pg_scope_enrichment_signal_ids': [(6, 0, chatter_context['signal_ids'])],
            'pg_scope_enrichment_signal_feedback': '\n'.join(lines),
        }

    def _infer_scope_kind(self, task, chatter_context=False):
        corpus = self._task_corpus(task, chatter_context=chatter_context).lower()
        if not corpus:
            return ('requirement', [], False)

        scores = {kind: [] for kind in self.KIND_KEYWORD_MAP}
        for kind, keywords in self.KIND_KEYWORD_MAP.items():
            for keyword in keywords:
                if keyword in corpus:
                    scores[kind].append(keyword)

        best_kind = 'requirement'
        best_keywords = []
        for kind, matches in scores.items():
            if len(matches) > len(best_keywords):
                best_kind = kind
                best_keywords = matches

        return (best_kind, best_keywords, bool(best_keywords))

    def _infer_scope_summary(self, task, chatter_context=False):
        description = self._task_plaintext_description(task)
        description_sentences = self._split_sentences(description)
        if description_sentences:
            first_sentence = description_sentences[0]
            if len(first_sentence) > 220:
                first_sentence = first_sentence[:217].rstrip(' ,;:') + '...'
            return (first_sentence, 'description')

        task_name = self._normalize_text(task.name)
        if chatter_context and chatter_context.get('used') and (not task_name or self._name_is_generic(task_name)):
            return (chatter_context['hint_summaries'][0], 'chatter')
        if task_name:
            return (task_name, 'name')

        return ('', 'empty')

    def _criteria_from_description(self, task, summary, chatter_context=False):
        description_lines = split_unique_text_lines(
            task.description,
            from_html=True,
            max_items=12,
            max_line_chars=220,
            strip_email_noise=True,
        )
        normalized_summary = self._normalize_text(summary)
        extracted = []
        for line in description_lines:
            if normalized_summary and self._normalize_text(line) == normalized_summary:
                continue
            lowered = line.lower()
            if (
                'deve' in lowered
                or 'permit' in lowered
                or 'valid' in lowered
                or 'suport' in lowered
                or 'mostrar' in lowered
                or 'gerar' in lowered
                or 'sincron' in lowered
            ):
                extracted.append(line.rstrip('.'))
            if len(extracted) == 3:
                break

        if extracted:
            return (extracted, 'description')

        fragment_based = []
        for line in description_lines:
            if normalized_summary and self._text_similarity_ratio(line, normalized_summary) >= 0.95:
                continue
            if not self._looks_like_feature_fragment(line):
                continue
            criterion = self._criterion_from_fragment(line)
            if not criterion:
                continue
            if self._text_similarity_ratio(summary, criterion) >= 0.8:
                continue
            if any(self._text_similarity_ratio(criterion, existing) >= 0.8 for existing in fragment_based):
                continue
            fragment_based.append(criterion)
            if len(fragment_based) == 3:
                break

        if fragment_based:
            return (fragment_based, 'description')

        if chatter_context and chatter_context.get('used'):
            hinted = []
            for hint in chatter_context['hint_summaries'][:2]:
                normalized_hint = self._normalize_text(hint).rstrip('.')
                if normalized_hint:
                    hinted.append(f"O ambito aprovado deve refletir {normalized_hint[0].lower() + normalized_hint[1:]}.")
            if hinted:
                return (hinted, 'chatter')

        normalized_summary = self._normalize_text(summary or task.name)
        if not normalized_summary:
            return ([], 'empty')

        summary_text = normalized_summary[0].lower() + normalized_summary[1:] if len(normalized_summary) > 1 else normalized_summary.lower()
        generated = [
            f"O utilizador deve conseguir {summary_text.rstrip('.')}.",
            f"O processo deve refletir {summary_text.rstrip('.')}.",
        ]
        return (generated, 'template')

    def _compute_confidence(self, kind_source, summary_source, criteria_source, keyword_count):
        score = 40
        if kind_source:
            score += min(keyword_count * 10, 20)
        if summary_source == 'description':
            score += 20
        elif summary_source == 'chatter':
            score += 15
        elif summary_source == 'name':
            score += 8
        if criteria_source == 'description':
            score += 20
        elif criteria_source == 'chatter':
            score += 14
        elif criteria_source == 'template':
            score += 8
        return max(0, min(score, 95))

    def _build_feedback(self, kind, kind_keywords, summary_source, criteria_source, confidence, task, chatter_context=False):
        lines = []
        if kind_keywords:
            lines.append(
                "Scope Kind sugerido como %s por palavras-chave detetadas: %s."
                % (kind, ', '.join(sorted(set(kind_keywords))))
            )
        else:
            lines.append("Scope Kind sugerido como requirement por falta de sinais mais especificos.")

        summary_labels = {
            'description': 'resumo inferido a partir da descricao da task',
            'chatter': 'resumo inferido a partir de sinais validados do chatter',
            'name': 'resumo inferido a partir do nome da task',
            'empty': 'sem base suficiente para resumo automatico',
        }
        lines.append("Scope Summary: %s." % summary_labels[summary_source])

        criteria_labels = {
            'description': 'criterios inferidos a partir da descricao existente',
            'chatter': 'criterios reforcados com hints validados do chatter',
            'template': 'criterios gerados por template de fallback',
            'empty': 'sem base suficiente para criterios automaticos',
        }
        lines.append("Acceptance Criteria: %s." % criteria_labels[criteria_source])
        if chatter_context and chatter_context.get('used'):
            lines.append(
                "Sinais validados do chatter usados apenas como contexto secundario: %s scope changes, %s approvals e %s decisions."
                % (
                    chatter_context['counts']['scope_changes'],
                    chatter_context['counts']['approvals'],
                    chatter_context['counts']['decisions'],
                )
            )
            lines.append(
                "Os sinais de chatter nao alteram por si so a elegibilidade de approved scope."
            )
        elif chatter_context and chatter_context.get('stale'):
            lines.append("Os sinais do chatter nao foram usados porque o refresh esta em falta para esta task.")

        missing_official = []
        if not (task.pg_scope_kind or '').strip():
            missing_official.append('Scope Kind')
        if not (task.pg_scope_summary or '').strip():
            missing_official.append('Scope Summary')
        if not (task.pg_acceptance_criteria_text or '').strip():
            missing_official.append('Acceptance Criteria')
        if missing_official:
            lines.append("Campos oficiais ainda vazios: %s." % ', '.join(missing_official))
        else:
            lines.append("Campos oficiais ja estao preenchidos; o draft serve apenas para revisao comparativa.")

        if confidence < 70:
            lines.append("Revisao manual recomendada antes de aplicar o draft.")
        else:
            lines.append("Confianca suficiente para aplicacao assistida em campos ainda vazios.")
        return '\n'.join(lines)

    def _build_rule_based_suggestions(self, task, chatter_context):
        suggested_kind, kind_keywords, has_kind_signal = self._infer_scope_kind(task, chatter_context=chatter_context)
        suggested_summary, summary_source = self._infer_scope_summary(task, chatter_context=chatter_context)
        suggested_criteria_lines, criteria_source = self._criteria_from_description(
            task,
            suggested_summary,
            chatter_context=chatter_context,
        )
        confidence = self._compute_confidence(
            kind_source=has_kind_signal,
            summary_source=summary_source,
            criteria_source=criteria_source,
            keyword_count=len(kind_keywords),
        )
        quality_assessment = self._assess_scope_draft_quality(task, suggested_summary, suggested_criteria_lines)
        status = 'draft' if confidence >= 70 and not quality_assessment['force_review'] else 'needs_review'
        feedback = self._build_feedback(
            suggested_kind,
            kind_keywords,
            summary_source,
            criteria_source,
            confidence,
            task,
            chatter_context=chatter_context,
        )
        if quality_assessment['flags']:
            feedback = '\n'.join([feedback] + quality_assessment['flags'])
        return {
            'pg_scope_kind_suggested': suggested_kind or False,
            'pg_scope_summary_suggested': suggested_summary or False,
            'pg_acceptance_criteria_suggested_text': '\n'.join(suggested_criteria_lines) if suggested_criteria_lines else False,
            'pg_scope_enrichment_confidence': confidence,
            'pg_scope_enrichment_status': status,
            'pg_scope_enrichment_source': 'rule_based',
            'pg_scope_enrichment_feedback': feedback,
            '_kind_keywords': kind_keywords,
            '_llm_eligible': quality_assessment['llm_eligible'],
        }

    def _apply_llm_candidate(self, task, suggestions, llm_candidate):
        confidence = max(
            suggestions.get('pg_scope_enrichment_confidence') or 0,
            llm_candidate.get('confidence') or 0,
        )
        status = 'draft' if confidence >= 80 and llm_candidate.get('should_apply_without_review') else 'needs_review'
        feedback = suggestions.get('pg_scope_enrichment_feedback') or ''
        rationale = llm_candidate.get('quality_rationale')
        lines = [feedback] if feedback else []
        lines.append("LLM-assisted scope enrichment applied because the rule-based draft was weak.")
        if rationale:
            lines.append("LLM rationale: %s." % rationale.rstrip('.'))
        if status != 'draft':
            lines.append("O draft assistido por LLM continua a exigir revisao manual antes de aplicar.")
        suggestions.update(
            {
                'pg_scope_summary_suggested': llm_candidate.get('scope_summary_suggested') or suggestions.get('pg_scope_summary_suggested'),
                'pg_acceptance_criteria_suggested_text': '\n'.join(llm_candidate.get('acceptance_criteria_suggested') or []) or False,
                'pg_scope_enrichment_confidence': confidence,
                'pg_scope_enrichment_status': status,
                'pg_scope_enrichment_source': 'llm_assisted',
                'pg_scope_enrichment_feedback': '\n'.join(line for line in lines if line),
            }
        )
        return suggestions

    def _mark_llm_fallback(self, suggestions, reason=False):
        feedback = suggestions.get('pg_scope_enrichment_feedback') or ''
        lines = [feedback] if feedback else []
        lines.append("LLM-assisted scope enrichment was attempted but the system kept the rule-based fallback.")
        if reason:
            lines.append("LLM refusal reason: %s." % reason.rstrip('.'))
        lines.append("O fallback rule-based continua em revisao manual e nao deve ser promovido automaticamente para draft ready.")
        suggestions.update(
            {
                'pg_scope_enrichment_source': 'llm_fallback_rule_based',
                'pg_scope_enrichment_status': 'needs_review',
                'pg_scope_enrichment_feedback': '\n'.join(line for line in lines if line),
            }
        )
        return suggestions

    def build_suggestions(self, task):
        task.ensure_one()

        chatter_context = self._collect_chatter_context(task)
        suggestions = self._build_rule_based_suggestions(task, chatter_context)
        llm_attempted = self.llm_service.should_attempt(task, suggestions, chatter_context=chatter_context)
        if llm_attempted:
            llm_candidate = self.llm_service.build_candidate(task, suggestions, chatter_context=chatter_context)
            if llm_candidate and llm_candidate.get('decision') == 'suggest':
                suggestions = self._apply_llm_candidate(task, suggestions, llm_candidate)
            elif llm_candidate and llm_candidate.get('decision') == 'refuse':
                suggestions = self._mark_llm_fallback(suggestions, reason=llm_candidate.get('refusal_reason'))
            else:
                suggestions = self._mark_llm_fallback(suggestions)

        suggestions.pop('_kind_keywords', None)
        suggestions.pop('_llm_eligible', None)
        suggestions.update(self._build_explainability(chatter_context))
        return suggestions
