from .project_chatter_grounding_service import ProjectChatterGroundingService
from .text_hygiene import normalize_inline_text
from .text_hygiene import sanitize_plaintext


class ProjectTaskConsultivePrefillService:
    MODULE_KEYWORD_MAP = {
        'approvals': ('approval', 'approv', 'aprov'),
        'documents': ('document', 'assinatura', 'signature'),
        'helpdesk': ('helpdesk', 'ticket', 'sla', 'suporte'),
        'knowledge': ('knowledge', 'wiki', 'base de conhecimento'),
        'purchase': ('purchase', 'compra', 'fornecedor', 'vendor'),
        'sale': ('sale', 'venda', 'quotation', 'orcamento'),
        'stock': ('armaz', 'inventario', 'stock', 'warehouse'),
        'account': ('account', 'fatura', 'invoice', 'payment', 'pagamento'),
        'crm': ('crm', 'lead', 'oportunidade'),
        'project': ('project', 'task', 'timesheet'),
    }

    CUSTOM_KEYWORDS = (
        'api',
        'ci/cd',
        'codex',
        'cron',
        'deploy',
        'endpoint',
        'external',
        'externo',
        'github',
        'integrat',
        'legado',
        'legacy',
        'migr',
        'script',
        'security',
        'seguranca',
        'sync',
        'tecnico',
        'technical',
        'webhook',
    )

    STANDARD_KEYWORDS = (
        'configur',
        'formacao',
        'nativo',
        'parametr',
        'processo standard',
        'setup',
        'standard',
        'treino',
        'training',
        'workflow existente',
    )

    STUDIO_KEYWORDS = (
        'approval',
        'aprov',
        'automation',
        'automacao',
        'botao',
        'campo',
        'dashboard',
        'field',
        'form',
        'kanban',
        'layout',
        'report',
        'view',
    )

    SCOPE_KIND_HINT_MAP = {
        'integration': 'custom',
        'migration': 'custom',
        'technical': 'custom',
        'data': 'custom',
        'report': 'studio',
        'process': 'standard',
        'training': 'standard',
    }

    def __init__(self, env):
        self.env = env
        self.chatter_grounding_service = ProjectChatterGroundingService(env)

    def _normalize_text(self, value):
        return normalize_inline_text(value, fallback='')

    def _task_plaintext_description(self, task):
        return sanitize_plaintext(task.description, from_html=True, max_chars=1200, strip_email_noise=True)

    def _task_corpus(self, task, chatter_context=False):
        project = task.project_id
        parts = [
            self._normalize_text(task.name),
            self._task_plaintext_description(task),
            self._normalize_text(task.pg_scope_summary),
            self._normalize_text(task.pg_acceptance_criteria_text),
            self._normalize_text(task.pg_scope_kind),
            ' '.join(task.tag_ids.mapped('name')),
            self._normalize_text(project.pg_business_goal if project else False),
            self._normalize_text(project.pg_current_request if project else False),
        ]
        if chatter_context and chatter_context.get('signals_used'):
            parts.append(' '.join(chatter_context['signals_used']))
        return normalize_inline_text(' '.join(part for part in parts if part), fallback='', max_chars=2000)

    def _task_label(self, task):
        return (
            self._normalize_text(task.pg_scope_summary)
            or self._normalize_text(task.name)
            or 'this task'
        )

    def _match_keywords(self, corpus, keywords):
        lowered = corpus.lower()
        return [keyword for keyword in keywords if keyword in lowered]

    def _empty_chatter_context(self):
        return {
            'task_grounding': {},
            'project_grounding': {},
            'signals_used': [],
            'counts': {
                'decisions': 0,
                'approvals': 0,
                'dependencies': 0,
                'scope_changes': 0,
            },
            'used': False,
            'stale_sources': [],
        }

    def _collect_chatter_context(self, task):
        context = self._empty_chatter_context()
        relevant_buckets = ('decisions', 'approvals', 'dependencies', 'scope_changes')
        seen = set()

        if getattr(task, 'pg_chatter_signals_dirty', False):
            context['stale_sources'].append('task')
        else:
            context['task_grounding'] = self.chatter_grounding_service.build_task_grounding(task, days=90)

        if task.project_id:
            if getattr(task.project_id, 'pg_chatter_signals_dirty', False):
                context['stale_sources'].append('project')
            else:
                context['project_grounding'] = self.chatter_grounding_service.build_project_only_grounding(
                    task.project_id,
                    days=90,
                )

        for grounding in (context['task_grounding'], context['project_grounding']):
            for bucket_name in relevant_buckets:
                bucket_items = grounding.get(bucket_name) or []
                context['counts'][bucket_name] += len(bucket_items)
                for item in bucket_items:
                    summary = self._normalize_text(item.get('summary'))
                    if summary and summary not in seen:
                        seen.add(summary)
                        context['signals_used'].append(summary)

        context['used'] = bool(context['signals_used'])
        return context

    def _build_chatter_feedback_line(self, chatter_context):
        if chatter_context.get('used'):
            counts = chatter_context['counts']
            return (
                "Validated chatter signals were used from task/project discussions: %s decisions, %s approvals, %s dependencies and %s scope changes."
                % (
                    counts['decisions'],
                    counts['approvals'],
                    counts['dependencies'],
                    counts['scope_changes'],
                )
            )
        if chatter_context.get('stale_sources'):
            return (
                "Chatter signals were not used because the current cache is stale for: %s."
                % ', '.join(chatter_context['stale_sources'])
            )
        return False

    def _build_explainability(self, chatter_context):
        if chatter_context.get('stale_sources'):
            return {
                'pg_ai_consultive_prefill_signal_ids': [(5, 0, 0)],
                'pg_ai_consultive_prefill_signal_feedback': (
                    "No chatter signals were attached to this consultive draft because the cache is stale for: %s."
                    % ', '.join(chatter_context['stale_sources'])
                ),
            }

        signal_ids = []
        for grounding in (chatter_context.get('task_grounding') or {}, chatter_context.get('project_grounding') or {}):
            for signal in grounding.get('all_signals', []):
                if signal['id'] not in signal_ids:
                    signal_ids.append(signal['id'])

        if not signal_ids:
            return {
                'pg_ai_consultive_prefill_signal_ids': [(5, 0, 0)],
                'pg_ai_consultive_prefill_signal_feedback': (
                    "No validated chatter signals were used when this consultive draft was generated."
                ),
            }

        lines = [
            "Validated chatter signals linked to this consultive draft: %s." % len(signal_ids),
        ]
        for summary in chatter_context.get('signals_used', [])[:5]:
            lines.append("Signal: %s" % summary)

        return {
            'pg_ai_consultive_prefill_signal_ids': [(6, 0, signal_ids)],
            'pg_ai_consultive_prefill_signal_feedback': '\n'.join(lines),
        }

    def _infer_module(self, corpus):
        best_module = False
        best_keywords = []
        for module_name, keywords in self.MODULE_KEYWORD_MAP.items():
            matches = self._match_keywords(corpus, keywords)
            if len(matches) > len(best_keywords):
                best_module = module_name
                best_keywords = matches
        return best_module, best_keywords

    def _project_restriction_value(self, project, recommendation_class):
        restriction_map = {
            'standard': 'pg_standard_allowed',
            'additional_module': 'pg_additional_modules_allowed',
            'studio': 'pg_studio_allowed',
            'custom': 'pg_custom_allowed',
        }
        return getattr(project, restriction_map[recommendation_class], 'unknown')

    def _project_restriction_map(self, project):
        if not project:
            return {}
        return {
            'standard': self._project_restriction_value(project, 'standard'),
            'additional_module': self._project_restriction_value(project, 'additional_module'),
            'studio': self._project_restriction_value(project, 'studio'),
            'custom': self._project_restriction_value(project, 'custom'),
        }

    def _candidate_scores(
        self,
        task,
        scope_hint,
        module_name,
        module_keywords,
        custom_keywords,
        standard_keywords,
        studio_keywords,
    ):
        scores = {
            'standard': 0,
            'additional_module': 0,
            'studio': 0,
            'custom': 0,
        }

        if scope_hint == 'custom':
            scores['custom'] += 40
        if custom_keywords:
            scores['custom'] += min(len(custom_keywords) * 8, 28)

        if module_name:
            scores['additional_module'] += 36 + min(len(module_keywords) * 6, 18)

        if scope_hint == 'standard':
            scores['standard'] += 36
        if standard_keywords:
            scores['standard'] += min(len(standard_keywords) * 7, 21)

        if scope_hint == 'studio':
            scores['studio'] += 34
        if studio_keywords:
            scores['studio'] += min(len(studio_keywords) * 7, 21)
        if (task.pg_scope_kind or '') in {'report', 'requirement'}:
            scores['studio'] += 16

        return scores

    def _best_allowed_fallback(self, candidate_scores, project, excluded_class=False):
        if not project:
            return False

        restrictions = self._project_restriction_map(project)
        candidates = [
            recommendation_class
            for recommendation_class, score in candidate_scores.items()
            if recommendation_class != excluded_class and score >= 30 and restrictions.get(recommendation_class) != 'no'
        ]
        if not candidates:
            return False

        return max(
            candidates,
            key=lambda recommendation_class: (
                candidate_scores[recommendation_class],
                1 if restrictions.get(recommendation_class) == 'yes' else 0,
            ),
        )

    def _resolve_recommendation_restrictions(
        self,
        task,
        recommendation_class,
        candidate_scores,
        recommended_module,
    ):
        if not recommendation_class or not task.project_id:
            return {
                'recommendation_class': recommendation_class,
                'recommended_module': recommended_module,
                'restriction_value': 'unknown',
                'restriction_warning': False,
                'restriction_resolution': False,
                'blocked_by_restrictions': False,
                'restriction_adjusted': False,
            }

        restriction_value = self._project_restriction_value(task.project_id, recommendation_class)
        if restriction_value == 'yes':
            return {
                'recommendation_class': recommendation_class,
                'recommended_module': recommended_module,
                'restriction_value': restriction_value,
                'restriction_warning': False,
                'restriction_resolution': False,
                'blocked_by_restrictions': False,
                'restriction_adjusted': False,
            }

        if restriction_value == 'unknown':
            return {
                'recommendation_class': recommendation_class,
                'recommended_module': recommended_module,
                'restriction_value': restriction_value,
                'restriction_warning': (
                    "Project restrictions for %s are still unknown."
                    % recommendation_class.replace('_', ' ')
                ),
                'restriction_resolution': False,
                'blocked_by_restrictions': False,
                'restriction_adjusted': False,
            }

        fallback_class = self._best_allowed_fallback(
            candidate_scores,
            task.project_id,
            excluded_class=recommendation_class,
        )
        if fallback_class:
            return {
                'recommendation_class': fallback_class,
                'recommended_module': recommended_module if fallback_class == 'additional_module' else False,
                'restriction_value': self._project_restriction_value(task.project_id, fallback_class),
                'restriction_warning': (
                    "Project restrictions mark %s as not allowed."
                    % recommendation_class.replace('_', ' ')
                ),
                'restriction_resolution': (
                    "The draft falls back to %s because it is the strongest currently allowed class."
                    % fallback_class.replace('_', ' ')
                ),
                'blocked_by_restrictions': False,
                'restriction_adjusted': True,
            }

        return {
            'recommendation_class': False,
            'recommended_module': False,
            'restriction_value': 'no',
            'restriction_warning': (
                "Project restrictions mark %s as not allowed."
                % recommendation_class.replace('_', ' ')
            ),
            'restriction_resolution': (
                "No automatic Recommendation Class is proposed because the strongest signals only support classes currently blocked by project restrictions."
            ),
            'blocked_by_restrictions': True,
            'restriction_adjusted': True,
        }

    def _infer_recommendation(self, task, chatter_context=False):
        corpus = self._task_corpus(task, chatter_context=chatter_context)
        module_name, module_keywords = self._infer_module(corpus)
        custom_keywords = self._match_keywords(corpus, self.CUSTOM_KEYWORDS)
        standard_keywords = self._match_keywords(corpus, self.STANDARD_KEYWORDS)
        studio_keywords = self._match_keywords(corpus, self.STUDIO_KEYWORDS)
        scope_hint = self.SCOPE_KIND_HINT_MAP.get(task.pg_scope_kind or '')
        candidate_scores = self._candidate_scores(
            task,
            scope_hint,
            module_name,
            module_keywords,
            custom_keywords,
            standard_keywords,
            studio_keywords,
        )

        reasons = []
        if scope_hint == 'custom' or len(custom_keywords) >= 2:
            recommendation_class = 'custom'
            reasons.append(
                "Strong custom signal detected from technical/integration indicators: %s."
                % ', '.join(sorted(set(custom_keywords)) or [task.pg_scope_kind or 'scope kind'])
            )
        elif module_name:
            recommendation_class = 'additional_module'
            reasons.append(
                "Standard module candidate detected: %s (%s)."
                % (module_name, ', '.join(sorted(set(module_keywords))))
            )
        elif scope_hint == 'standard' or len(standard_keywords) >= 2:
            recommendation_class = 'standard'
            reasons.append(
                "Standard-fit signal detected: %s."
                % ', '.join(sorted(set(standard_keywords)) or [task.pg_scope_kind or 'scope kind'])
            )
        elif studio_keywords or (task.pg_scope_kind or '') in {'report', 'requirement'}:
            recommendation_class = 'studio'
            reasons.append(
                "Studio-fit signal detected: %s."
                % ', '.join(sorted(set(studio_keywords)) or [task.pg_scope_kind or 'scope kind'])
            )
        else:
            recommendation_class = 'custom' if (task.pg_scope_kind or '') in {'data', 'integration', 'migration', 'technical'} else 'standard'
            reasons.append("Signals are weak, so the recommendation draft should be reviewed manually.")

        confidence = 45
        if task.pg_scope_kind:
            confidence += 10
        if task.pg_scope_summary:
            confidence += 10
        elif task.name:
            confidence += 5
        if task.description:
            confidence += 10
        if module_name and recommendation_class == 'additional_module':
            confidence += 18
        if recommendation_class == 'custom':
            confidence += min(len(custom_keywords) * 8, 20)
        elif recommendation_class == 'standard':
            confidence += min(len(standard_keywords) * 8, 18)
        elif recommendation_class == 'studio':
            confidence += min(len(studio_keywords) * 8, 18)
        if scope_hint and recommendation_class == scope_hint:
            confidence += 8
        if chatter_context and chatter_context.get('used'):
            confidence += min(len(chatter_context['signals_used']) * 4, 12)
            reasons.append(self._build_chatter_feedback_line(chatter_context))

        restriction_resolution = self._resolve_recommendation_restrictions(
            task,
            recommendation_class,
            candidate_scores,
            module_name if recommendation_class == 'additional_module' else False,
        )
        recommendation_class = restriction_resolution['recommendation_class']
        recommended_module = restriction_resolution['recommended_module']
        restriction_value = restriction_resolution['restriction_value']
        restriction_warning = restriction_resolution['restriction_warning']
        restriction_feedback = restriction_resolution['restriction_resolution']

        if restriction_value == 'unknown':
            confidence -= 10
        elif restriction_value == 'no':
            confidence = 38
        elif restriction_feedback:
            confidence -= 18

        if restriction_feedback:
            reasons.append(restriction_feedback)

        return {
            'recommendation_class': recommendation_class,
            'recommended_module': recommended_module if recommendation_class == 'additional_module' else False,
            'confidence': max(35, min(confidence, 92)),
            'module_keywords': module_keywords,
            'custom_keywords': custom_keywords,
            'standard_keywords': standard_keywords,
            'studio_keywords': studio_keywords,
            'scope_hint': scope_hint,
            'reasons': reasons,
            'restriction_warning': restriction_warning,
            'restriction_value': restriction_value,
            'blocked_by_restrictions': restriction_resolution['blocked_by_restrictions'],
            'restriction_adjusted': restriction_resolution['restriction_adjusted'],
        }

    def _build_standard_review(self, task, recommendation_class):
        label = self._task_label(task)
        if not recommendation_class:
            return (
                "Standard Odoo and the existing project setup were reviewed for %s. "
                "Current signals are not strong enough to recommend an allowed delivery class without manual consultive review."
            ) % label
        if recommendation_class == 'standard':
            return (
                "Standard Odoo and the existing project setup were reviewed for %s. "
                "Current signals suggest that the need can likely be covered with standard configuration and existing flows."
            ) % label
        return (
            "Standard Odoo and the existing project setup were reviewed for %s. "
            "Current signals do not show enough standard coverage to close the requirement without an additional option."
        ) % label

    def _build_additional_module_review(self, task, recommendation_class, suggested_module):
        label = self._task_label(task)
        if not recommendation_class:
            return False
        if recommendation_class == 'additional_module' and suggested_module:
            return (
                "Standard additional modules were reviewed for %s. The strongest current candidate is module %s, which should be validated functionally before confirming delivery."
            ) % (label, suggested_module)
        if recommendation_class in {'studio', 'custom'}:
            return (
                "Standard additional modules were reviewed for %s, but no module candidate currently looks strong enough to cover the requirement end-to-end."
            ) % label
        return False

    def _build_studio_review(self, task, recommendation_class):
        label = self._task_label(task)
        if not recommendation_class:
            return False
        if recommendation_class == 'studio':
            return (
                "Studio was reviewed for %s. Current signals suggest that fields, views and simple automations may be enough without moving to custom code."
            ) % label
        if recommendation_class == 'custom':
            return (
                "Studio was reviewed for %s, but current signals point to integration, migration or technical complexity above a safe Studio-only approach."
            ) % label
        return False

    def _build_justification(self, task, recommendation_class, suggested_module):
        label = self._task_label(task)
        if not recommendation_class:
            return (
                "No automatic recommendation class is suggested for %s because the strongest current signals conflict with project restrictions and require manual consultive review."
            ) % label
        if recommendation_class == 'standard':
            return (
                "The current recommendation is standard because %s appears to fit the existing Odoo setup without needing extra modules, Studio or custom development."
            ) % label
        if recommendation_class == 'additional_module':
            module_text = suggested_module or 'an additional Odoo module'
            return (
                "The current recommendation is additional module because %s appears closer to %s than to a pure standard, Studio or custom path."
            ) % (label, module_text)
        if recommendation_class == 'studio':
            return (
                "The current recommendation is Studio because %s appears to be mainly a matter of fields, views or light automation rather than deep custom logic."
            ) % label
        return (
            "The current recommendation is custom because %s appears to require integration, migration, technical behavior or cross-cutting logic beyond standard, additional modules or Studio."
        ) % label

    def _build_feedback(self, task, suggestion, chatter_context=False):
        if suggestion['recommendation_class']:
            lines = [
                "Suggested Recommendation Class: %s." % suggestion['recommendation_class'].replace('_', ' '),
            ]
        else:
            lines = [
                "Suggested Recommendation Class: none.",
            ]
        if suggestion['recommended_module']:
            lines.append("Suggested Odoo module: %s." % suggestion['recommended_module'])
        lines.extend(suggestion['reasons'])
        chatter_feedback = self._build_chatter_feedback_line(chatter_context or {})
        if chatter_feedback and chatter_feedback not in lines:
            lines.append(chatter_feedback)
        if chatter_context and chatter_context.get('signals_used'):
            lines.append(
                "Chatter evidence used: %s."
                % ' | '.join(chatter_context['signals_used'][:3])
            )
        if suggestion['restriction_warning']:
            lines.append(suggestion['restriction_warning'])

        missing_official = []
        if not task.pg_ai_recommendation_class:
            missing_official.append('Recommendation Class')
        if not (task.pg_ai_standard_review or '').strip():
            missing_official.append('Standard Review')
        if not (task.pg_ai_recommendation_justification or '').strip():
            missing_official.append('Recommendation Justification')
        if suggestion['recommendation_class'] in {'additional_module', 'studio', 'custom'} and not (task.pg_ai_additional_module_review or '').strip():
            missing_official.append('Additional Module Review')
        if suggestion['recommendation_class'] in {'studio', 'custom'} and not (task.pg_ai_studio_review or '').strip():
            missing_official.append('Studio Review')
        if suggestion['recommendation_class'] == 'additional_module' and not (task.pg_ai_recommended_module or '').strip():
            missing_official.append('Recommended Odoo Module')

        if missing_official:
            lines.append("Official consultive fields still empty: %s." % ', '.join(missing_official))
        else:
            lines.append("Official consultive fields are already filled; this draft is only for comparison.")

        if suggestion['blocked_by_restrictions']:
            lines.append("Manual review is required because project restrictions block the strongest automatic recommendation path.")
        elif (
            suggestion['confidence'] < 70
            or suggestion['restriction_value'] != 'yes'
            or suggestion['restriction_adjusted']
        ):
            lines.append("Manual review is recommended before applying this consultive draft.")
        else:
            lines.append("Confidence is high enough to apply this consultive draft to empty official fields.")
        return '\n'.join(lines)

    def build_suggestions(self, task):
        task.ensure_one()

        chatter_context = self._collect_chatter_context(task)
        suggestion = self._infer_recommendation(task, chatter_context=chatter_context)
        recommendation_class = suggestion['recommendation_class']
        recommended_module = suggestion['recommended_module']
        confidence = suggestion['confidence']
        status = (
            'draft'
            if confidence >= 70 and suggestion['restriction_value'] == 'yes' and not suggestion['restriction_adjusted']
            else 'needs_review'
        )
        return {
            'pg_ai_recommendation_class_suggested': recommendation_class,
            'pg_ai_recommended_module_suggested': recommended_module or False,
            'pg_ai_standard_review_suggested': self._build_standard_review(task, recommendation_class),
            'pg_ai_additional_module_review_suggested': self._build_additional_module_review(
                task,
                recommendation_class,
                recommended_module,
            ),
            'pg_ai_studio_review_suggested': self._build_studio_review(task, recommendation_class),
            'pg_ai_recommendation_justification_suggested': self._build_justification(
                task,
                recommendation_class,
                recommended_module,
            ),
            'pg_ai_consultive_prefill_confidence': confidence,
            'pg_ai_consultive_prefill_status': status,
            'pg_ai_consultive_prefill_source': 'rule_based',
            'pg_ai_consultive_prefill_feedback': self._build_feedback(
                task,
                suggestion,
                chatter_context=chatter_context,
            ),
            **self._build_explainability(chatter_context),
        }
