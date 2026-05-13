from odoo import _, fields

from .project_chatter_grounding_service import ProjectChatterGroundingService
from .project_scope_payload_builder import ProjectScopePayloadBuilder
from .project_status_draft_llm_service import ProjectStatusDraftLlmService
from .text_hygiene import normalize_inline_text


class ProjectStatusDraftService:
    def __init__(self, env):
        self.env = env
        self.chatter_grounding_service = ProjectChatterGroundingService(env)
        self.llm_service = ProjectStatusDraftLlmService(env)
        self.scope_payload_builder = ProjectScopePayloadBuilder(env)

    def _selection_label(self, record, field_name):
        field = record._fields.get(field_name)
        if not field:
            return ''
        return dict(field.selection).get(getattr(record, field_name), '')

    def _normalize_text(self, value):
        return normalize_inline_text(value, fallback='')

    def _append_unique(self, target, value):
        normalized = self._normalize_text(value)
        if normalized and normalized not in target:
            target.append(normalized)

    def _join_lines(self, items):
        return '\n'.join(items) or False

    def _strip_terminal_punctuation(self, value):
        return self._normalize_text(value).rstrip('.!?;:')

    def _recent_chatter_grounding(self, project):
        if getattr(project, 'pg_chatter_signals_dirty', False):
            return {}
        grounding = self.chatter_grounding_service.build_project_grounding(project, days=30)
        return grounding if grounding.get('all_signals') else {}

    def _format_chatter_signal(self, signal, label):
        summary = self._strip_terminal_punctuation(signal.get('summary'))
        if not summary:
            return False
        return _("Validated chatter %(label)s: %(summary)s (confidence %(confidence)s%%).") % {
            'label': label,
            'summary': summary,
            'confidence': signal.get('confidence') or 0,
        }

    def _append_chatter_bucket(self, target, chatter_grounding, bucket_name, label, limit=2):
        for signal in (chatter_grounding or {}).get(bucket_name, [])[:limit]:
            self._append_unique(target, self._format_chatter_signal(signal, label))

    def _build_chatter_explainability(self, project, chatter_grounding):
        if getattr(project, 'pg_chatter_signals_dirty', False):
            return {
                'pg_status_draft_signal_ids': [(5, 0, 0)],
                'pg_status_draft_signal_feedback': _(
                    "No chatter signals were attached to this status draft because the chatter cache is stale. Refresh chatter signals and regenerate the draft."
                ),
            }

        signal_entries = (chatter_grounding or {}).get('all_signals') or []
        if not signal_entries:
            return {
                'pg_status_draft_signal_ids': [(5, 0, 0)],
                'pg_status_draft_signal_feedback': _(
                    "No validated chatter signals were used when this status draft was generated."
                ),
            }

        lines = [
            _("Validated chatter signals linked to this status draft: %s.") % len(signal_entries),
        ]
        for signal in signal_entries[:5]:
            lines.append(
                _("%(type)s: %(summary)s")
                % {
                    'type': signal['signal_type'].replace('_', ' ').title(),
                    'summary': signal['summary'],
                }
            )
        return {
            'pg_status_draft_signal_ids': [(6, 0, [signal['id'] for signal in signal_entries])],
            'pg_status_draft_signal_feedback': '\n'.join(lines),
        }

    def _scope_tasks(self, project):
        return self.scope_payload_builder._scope_tasks(project)

    def _operational_backlog_tasks(self, project):
        return project._pg_operational_backlog_tasks()

    def _scope_consolidation_signals(self, project, scope_tasks):
        approved_scope_tasks = project._pg_scope_enrichment_target_tasks() if hasattr(project, '_pg_scope_enrichment_target_tasks') else scope_tasks
        missing_scope_tasks = (
            project._pg_scope_enrichment_tasks_missing_official_fields()
            if hasattr(project, '_pg_scope_enrichment_tasks_missing_official_fields')
            else approved_scope_tasks.filtered(
                lambda task: not (task.pg_scope_kind or '').strip()
                or not (task.pg_scope_summary or '').strip()
                or not (task.pg_acceptance_criteria_text or '').strip()
            )
        )
        needs_review_tasks = approved_scope_tasks.filtered(
            lambda task: task.pg_scope_enrichment_status == 'needs_review'
        )
        operational_backlog_tasks = self._operational_backlog_tasks(project)
        return {
            'approved_scope_count': len(scope_tasks),
            'validated_scope_count': len(scope_tasks.filtered(lambda task: task.pg_scope_state == 'validated')),
            'proposed_scope_count': len(scope_tasks.filtered(lambda task: task.pg_scope_state == 'proposed')),
            'deferred_scope_count': len(scope_tasks.filtered(lambda task: task.pg_scope_state == 'deferred')),
            'operational_backlog_count': len(operational_backlog_tasks),
            'missing_scope_fields_count': len(missing_scope_tasks),
            'missing_scope_summary_count': len(
                missing_scope_tasks.filtered(lambda task: not (task.pg_scope_summary or '').strip())
            ),
            'missing_acceptance_criteria_count': len(
                missing_scope_tasks.filtered(lambda task: not (task.pg_acceptance_criteria_text or '').strip())
            ),
            'missing_scope_kind_count': len(
                missing_scope_tasks.filtered(lambda task: not (task.pg_scope_kind or '').strip())
            ),
            'needs_review_count': len(needs_review_tasks),
        }

    def _draft_summary(self, project, scope_tasks, chatter_grounding=False):
        phase_label = self._selection_label(project, 'pg_project_phase') or _('Unknown')
        signals = self._scope_consolidation_signals(project, scope_tasks)
        summary_parts = [
            _("Project %s is currently in %s.") % (project.display_name, phase_label),
            _("Approved scope items currently tracked: %s.") % signals['approved_scope_count'],
        ]
        if signals['operational_backlog_count']:
            summary_parts.append(
                _("Operational backlog items currently tracked outside approved scope: %s.")
                % signals['operational_backlog_count']
            )
        if signals['missing_scope_fields_count']:
            summary_parts.append(
                _("Approved scope still needs consolidation for %s task(s) with incomplete scope fields.")
                % signals['missing_scope_fields_count']
            )
        if signals['needs_review_count']:
            summary_parts.append(
                _("Low-confidence scope drafts still need manual review for %s task(s).")
                % signals['needs_review_count']
            )
        if chatter_grounding:
            summary_parts.append(
                _("Validated chatter signals currently grounding this draft: %s.")
                % len(chatter_grounding['all_signals'])
            )
            if chatter_grounding['blockers'] or chatter_grounding['risks'] or chatter_grounding['dependencies'] or chatter_grounding['next_steps']:
                summary_parts.append(
                    _("Recent chatter highlights %(blockers)s blocker(s), %(risks)s risk(s), %(dependencies)s dependenc%(dependency_suffix)s and %(next_steps)s next step(s).")
                    % {
                        'blockers': len(chatter_grounding['blockers']),
                        'risks': len(chatter_grounding['risks']),
                        'dependencies': len(chatter_grounding['dependencies']),
                        'dependency_suffix': 'ies' if len(chatter_grounding['dependencies']) != 1 else 'y',
                        'next_steps': len(chatter_grounding['next_steps']),
                    }
                )
            if chatter_grounding['approvals'] or chatter_grounding['decisions']:
                summary_parts.append(
                    _("Recent chatter also records %(approvals)s approval(s) and %(decisions)s decision(s).")
                    % {
                        'approvals': len(chatter_grounding['approvals']),
                        'decisions': len(chatter_grounding['decisions']),
                    }
                )
        return ' '.join(summary_parts)

    def _draft_milestones(self, project, scope_tasks, chatter_grounding=False):
        signals = self._scope_consolidation_signals(project, scope_tasks)
        milestones = []
        phase_label = self._selection_label(project, 'pg_project_phase')
        if phase_label:
            milestones.append(_("Project phase currently recorded: %s.") % phase_label)
        milestones.append(_("Approved scope items currently tracked: %s.") % signals['approved_scope_count'])
        milestones.append(_("Approved scope items already validated: %s.") % signals['validated_scope_count'])
        milestones.append(_("Approved scope items still proposed: %s.") % signals['proposed_scope_count'])
        if signals['operational_backlog_count']:
            milestones.append(
                _("Operational backlog items currently tracked outside approved scope: %s.")
                % signals['operational_backlog_count']
            )
        if signals['missing_scope_fields_count']:
            milestones.append(
                _("Approved scope tasks still missing official scope fields: %s.")
                % signals['missing_scope_fields_count']
            )
        if chatter_grounding:
            milestones.append(
                _("Validated chatter signals used for this draft: %s.")
                % len(chatter_grounding['all_signals'])
            )
            self._append_chatter_bucket(milestones, chatter_grounding, 'approvals', 'approval')
            self._append_chatter_bucket(milestones, chatter_grounding, 'decisions', 'decision')
        return milestones

    def _draft_blockers(self, project, scope_tasks, chatter_grounding=False):
        signals = self._scope_consolidation_signals(project, scope_tasks)
        blockers = []
        if not project.pg_repository_id:
            self._append_unique(blockers, _("Project repository is not configured yet."))
        if not (project.pg_repo_branch or '').strip():
            self._append_unique(blockers, _("Project repository branch is not configured yet."))
        if project.pg_scope_sync_last_status == 'error':
            self._append_unique(
                blockers,
                _("Latest scope sync failed and should be reviewed before the next publication."),
            )
        if project.pg_status_sync_last_status == 'error':
            self._append_unique(
                blockers,
                _("Latest status sync failed and should be reviewed before the next publication."),
            )
        if not scope_tasks and signals['operational_backlog_count']:
            self._append_unique(
                blockers,
                _("There are operational backlog items but no approved scope item currently confirmed for publication."),
            )
        if signals['needs_review_count']:
            self._append_unique(
                blockers,
                _("Low-confidence scope drafts still need manual review before the approved scope can be trusted."),
            )
        self._append_chatter_bucket(blockers, chatter_grounding, 'blockers', 'blocker')
        return blockers

    def _draft_risks(self, project, scope_tasks, chatter_grounding=False):
        signals = self._scope_consolidation_signals(project, scope_tasks)
        risks = []
        if not scope_tasks:
            self._append_unique(risks, _("There is no approved scope item currently tracked for this project."))
        if signals['missing_scope_fields_count']:
            self._append_unique(
                risks,
                _("Approved scope still contains %s task(s) with incomplete scope definition.")
                % signals['missing_scope_fields_count'],
            )
        if signals['missing_scope_summary_count']:
            self._append_unique(
                risks,
                _("Some approved scope tasks still miss Scope Summary, reducing clarity of the published scope."),
            )
        if signals['missing_acceptance_criteria_count']:
            self._append_unique(
                risks,
                _("Some approved scope tasks still miss Acceptance Criteria, reducing confidence in the published scope."),
            )
        if signals['missing_scope_kind_count']:
            self._append_unique(
                risks,
                _("Some approved scope tasks still miss Scope Kind, reducing quality of scope categorization."),
            )
        if signals['needs_review_count']:
            self._append_unique(
                risks,
                _("Some scope enrichment drafts are still marked as needs review, so brownfield consolidation is not finished."),
            )
        self._append_chatter_bucket(risks, chatter_grounding, 'risks', 'risk')
        self._append_chatter_bucket(risks, chatter_grounding, 'dependencies', 'dependency')
        return risks

    def _draft_next_steps(self, project, scope_tasks, chatter_grounding=False):
        signals = self._scope_consolidation_signals(project, scope_tasks)
        next_steps = []
        if not project.pg_scope_sync_last_published_at:
            self._append_unique(
                next_steps,
                _("Publish a scope snapshot so the operational draft references the latest approved scope."),
            )
        if signals['proposed_scope_count']:
            self._append_unique(
                next_steps,
                _("Review proposed approved-scope items and validate which ones can move forward."),
            )
        if signals['operational_backlog_count']:
            self._append_unique(
                next_steps,
                _("Review operational backlog items and confirm which ones should move into approved scope."),
            )
        if signals['missing_scope_fields_count']:
            self._append_unique(
                next_steps,
                _("Generate or apply scope enrichment drafts for approved scope tasks still missing official scope fields."),
            )
        if signals['needs_review_count']:
            self._append_unique(
                next_steps,
                _("Review low-confidence scope enrichment drafts before trusting the approved scope in the next publication."),
            )
        if not next_steps:
            self._append_unique(
                next_steps,
                _("Validate project progress with the project owner and confirm the next operational milestone."),
            )
        self._append_chatter_bucket(next_steps, chatter_grounding, 'next_steps', 'next step')
        return next_steps

    def _draft_pending_decisions(self, project, scope_tasks):
        signals = self._scope_consolidation_signals(project, scope_tasks)
        decisions = []
        if signals['proposed_scope_count']:
            self._append_unique(
                decisions,
                _("Confirm which approved scope items can move from proposed to validated."),
            )
        if not project.pg_status_owner_id:
            self._append_unique(decisions, _("Assign a project owner for the operational status publication."))
        if not project.pg_status_go_live_target:
            self._append_unique(decisions, _("Confirm whether a go-live target date should already be recorded."))
        if signals['operational_backlog_count']:
            self._append_unique(
                decisions,
                _("Confirm whether the current operational backlog items should remain outside scope or move into approved scope."),
            )
        return decisions

    def _apply_llm_candidate(self, values, llm_candidate):
        values.update(
            {
                'pg_status_draft_summary': llm_candidate.get('status_summary') or values.get('pg_status_draft_summary'),
                'pg_status_draft_milestones_text': self._join_lines(llm_candidate.get('milestones')),
                'pg_status_draft_blockers_text': self._join_lines(llm_candidate.get('blockers')),
                'pg_status_draft_risks_text': self._join_lines(llm_candidate.get('risks')),
                'pg_status_draft_next_steps_text': self._join_lines(llm_candidate.get('next_steps')),
                'pg_status_draft_pending_decisions_text': self._join_lines(llm_candidate.get('pending_decisions')),
                'pg_status_draft_source': 'llm_assisted',
                'pg_status_draft_confidence': llm_candidate.get('confidence') or 0,
                'pg_status_draft_quality_rationale': llm_candidate.get('quality_rationale') or False,
            }
        )
        return values

    def _mark_llm_fallback(self, values, reason=False):
        values.update(
            {
                'pg_status_draft_source': 'llm_fallback_deterministic',
                'pg_status_draft_confidence': 0,
                'pg_status_draft_quality_rationale': reason or False,
            }
        )
        return values

    def build_draft_values(self, project):
        project.ensure_one()
        scope_tasks = self._scope_tasks(project)
        chatter_grounding = self._recent_chatter_grounding(project)
        draft_generated_at = fields.Datetime.now()
        values = {
            'pg_status_draft_generated_at': draft_generated_at,
            'pg_status_draft_generated_by_id': self.env.user.id,
            'pg_status_draft_summary': self._draft_summary(project, scope_tasks, chatter_grounding=chatter_grounding),
            'pg_status_draft_milestones_text': self._join_lines(
                self._draft_milestones(project, scope_tasks, chatter_grounding=chatter_grounding)
            ),
            'pg_status_draft_blockers_text': self._join_lines(
                self._draft_blockers(project, scope_tasks, chatter_grounding=chatter_grounding)
            ),
            'pg_status_draft_risks_text': self._join_lines(
                self._draft_risks(project, scope_tasks, chatter_grounding=chatter_grounding)
            ),
            'pg_status_draft_next_steps_text': self._join_lines(
                self._draft_next_steps(project, scope_tasks, chatter_grounding=chatter_grounding)
            ),
            'pg_status_draft_pending_decisions_text': self._join_lines(
                self._draft_pending_decisions(project, scope_tasks)
            ),
            'pg_status_draft_source': 'deterministic',
            'pg_status_draft_confidence': 0,
            'pg_status_draft_quality_rationale': False,
        }
        values.update(self._build_chatter_explainability(project, chatter_grounding))
        llm_attempted = self.llm_service.should_attempt(project, values)
        if llm_attempted:
            llm_candidate = self.llm_service.build_candidate(project, values)
            if llm_candidate and llm_candidate.get('decision') == 'redraft':
                values = self._apply_llm_candidate(values, llm_candidate)
            elif llm_candidate and llm_candidate.get('decision') == 'refuse':
                values = self._mark_llm_fallback(values, reason=llm_candidate.get('refusal_reason'))
            else:
                values = self._mark_llm_fallback(values)
        return values
