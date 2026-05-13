from odoo import _, fields
from odoo.exceptions import UserError

from .project_scope_payload_builder import ProjectScopePayloadBuilder
from .text_hygiene import SCOPE_ITEM_INCLUDED
from .text_hygiene import classify_scope_item
from .text_hygiene import curate_scope_publication_lines
from .text_hygiene import is_low_signal_scope_summary
from .text_hygiene import normalize_inline_text
from .text_hygiene import sanitize_scope_publication_candidate
from .text_hygiene import split_scope_publication_candidates
from .text_hygiene import split_unique_text_lines


class ProjectMirrorMigrationService:
    def __init__(self, env):
        self.env = env
        self.scope_payload_builder = ProjectScopePayloadBuilder(env)

    def _normalize_text(self, value, fallback='', max_chars=500):
        return normalize_inline_text(
            value,
            fallback=fallback,
            max_chars=max_chars,
            drop_placeholders=True,
        )

    def _normalize_lines(self, value, max_items=20, max_line_chars=240):
        return split_unique_text_lines(
            value,
            from_html=True,
            max_items=max_items,
            max_line_chars=max_line_chars,
            strip_email_noise=False,
        )

    def _join_lines(self, values):
        cleaned = []
        for value in values:
            normalized = self._normalize_text(value, max_chars=240)
            if normalized and normalized not in cleaned:
                cleaned.append(normalized)
        return '\n'.join(cleaned) or False

    def _publishable_scope_line(self, raw_value, normalized_value=''):
        return sanitize_scope_publication_candidate(normalized_value or raw_value, max_chars=240)

    def _publishable_scope_lines(self, raw_value):
        classification = classify_scope_item(raw_value, max_chars=240)
        if classification.get('state') != SCOPE_ITEM_INCLUDED:
            return []
        return (classification.get('publication_candidates') or [])[:6]

    def _join_included_scope_lines(self, values):
        cleaned = curate_scope_publication_lines(values, max_chars=240)
        return '\n'.join(cleaned) or False

    def _scope_line_texts(self, project, line_types):
        lines = project.pg_scope_line_ids.filtered(
            lambda line: line.active and line.line_type in set(line_types)
        ).sorted(key=lambda line: (line.sequence, line.id))
        return [line.text for line in lines]

    def _task_scope_texts(self, project, states=None, exclude_states=None):
        values = []
        tasks = project.task_ids.filtered(lambda task: task.active).sorted(key=lambda task: (task.priority or '', task.id))
        for task in tasks:
            state = task.pg_scope_state or False
            if states and state not in states:
                continue
            if exclude_states and state in exclude_states:
                continue
            if (task.pg_scope_track or 'approved_scope') != 'approved_scope':
                continue
            summary = self.scope_payload_builder._task_scope_summary(task)
            normalized_task_name = self._normalize_text(task.name, max_chars=240)
            normalized_summary = self._normalize_text(summary, max_chars=240)
            summary_lines = self._publishable_scope_lines(normalized_summary)
            if not summary_lines:
                continue
            if len(summary_lines) == 1 and summary_lines[0] == normalized_task_name:
                if is_low_signal_scope_summary(task.name, summary_lines[0]):
                    continue
                if self.scope_payload_builder._scope_summary_needs_expansion(summary_lines[0]):
                    continue
            for summary_line in summary_lines:
                if summary_line:
                    values.append(summary_line)
        return values

    def _planning_names(self, project):
        milestones = project.pg_project_plan_milestone_ids.sorted(key=lambda milestone: (milestone.sequence, milestone.id))
        if not milestones:
            milestones = project.milestone_ids.sorted(key=lambda milestone: (milestone.sequence, milestone.id))
        return milestones.mapped('name')

    def _stakeholder_names(self, project):
        values = []
        for value in (
            project.partner_id.display_name if project.partner_id else '',
            project.user_id.display_name if project.user_id else '',
            project.pg_status_owner_id.display_name if project.pg_status_owner_id else '',
        ):
            normalized = self._normalize_text(value, max_chars=160)
            if normalized and normalized not in values:
                values.append(normalized)
        return values

    def _legacy_sync_signals(self, project):
        return bool(
            project.pg_decisions_sync_enabled
            or project.pg_risks_sync_enabled
            or project.pg_deliveries_sync_enabled
            or project.pg_requirements_sync_enabled
            or project.pg_project_plan_sync_enabled
            or project.pg_budget_sync_enabled
            or project.pg_scope_sync_last_published_at
            or project.pg_status_sync_last_published_at
            or project.pg_decisions_sync_last_published_at
            or project.pg_risks_sync_last_published_at
            or project.pg_deliveries_sync_last_published_at
            or project.pg_requirements_sync_last_published_at
            or project.pg_project_plan_sync_last_published_at
            or project.pg_budget_sync_last_published_at
        )

    def project_needs_migration(self, project):
        project.ensure_one()
        if not project.pg_repository_id or not (project.pg_repo_branch or '').strip():
            return False
        if project.pg_onboarding_last_status != 'done':
            return True
        if not project.pg_mirror_sync_run_count:
            return True
        return False

    def _migration_values(self, project):
        project.ensure_one()
        summary = project.pg_repository_summary or project.description or _(
            "Project mirrored from Odoo for repository-first AI context."
        )
        objective = project.pg_business_goal or project.pg_current_request or project.pg_problem_or_need or summary
        included_scope_source = (
            self._normalize_lines(project.pg_onboarding_scope_included_text)
            if project.pg_onboarding_scope_included_text
            else (
                self._task_scope_texts(project, exclude_states={'excluded', 'dropped'})
                + self._scope_line_texts(
                    project,
                    (
                        'acceptance_criteria',
                        'users_and_roles',
                        'integrations',
                        'reporting_needs',
                        'documents',
                    ),
                )
            )
        )
        included_scope = self._join_included_scope_lines(included_scope_source)
        excluded_scope = (
            project.pg_onboarding_scope_excluded_text
            or self._join_lines(self._task_scope_texts(project, states={'excluded', 'dropped'}))
        )
        deliverables = (
            project.pg_onboarding_deliverables_text
            or self._join_lines(self._planning_names(project) + self._normalize_lines(project.pg_status_milestones_text))
        )
        assumptions = (
            project.pg_onboarding_assumptions_text
            or self._join_lines(self._scope_line_texts(project, ('known_exceptions', 'standard_attempted_or_validated')))
        )
        stakeholders = (
            project.pg_onboarding_stakeholders_text
            or self._join_lines(self._stakeholder_names(project))
        )
        milestones = (
            project.pg_onboarding_milestones_text
            or self._join_lines(self._planning_names(project))
        )
        values = {
            'pg_repository_summary': self._normalize_text(summary, max_chars=500) or False,
            'pg_business_goal': self._normalize_text(objective, max_chars=500) or False,
            'pg_onboarding_scope_included_text': included_scope or False,
            'pg_onboarding_scope_excluded_text': excluded_scope or False,
            'pg_onboarding_deliverables_text': deliverables or False,
            'pg_onboarding_assumptions_text': assumptions or False,
            'pg_onboarding_stakeholders_text': stakeholders or False,
            'pg_onboarding_milestones_text': milestones or False,
            'pg_onboarding_last_applied_at': fields.Datetime.now(),
            'pg_onboarding_last_status': 'done',
            'pg_onboarding_last_message': _(
                "Legacy project configuration migrated to the V1 onboarding and mirror model."
            ),
            'pg_mirror_migration_last_at': fields.Datetime.now(),
            'pg_mirror_migration_last_status': 'done',
            'pg_mirror_migration_last_message': _(
                "Legacy project context migrated and ready for mirror synchronization."
            ),
        }
        if not (project.pg_scope_sync_enabled or project.pg_status_sync_enabled) and self._legacy_sync_signals(project):
            values['pg_scope_sync_enabled'] = True
            values['pg_scope_sync_mode'] = 'event_driven'
        return values

    def migrate_project(self, project, process_run=True):
        project.ensure_one()
        if not project.pg_repository_id or not (project.pg_repo_branch or '').strip():
            raise UserError(_("Define the repository and branch before migrating a legacy project to the V1 mirror."))

        values = self._migration_values(project)
        project.with_context(
            pg_skip_scope_sync_enqueue=True,
            pg_skip_mirror_sync_enqueue=True,
            pg_skip_status_sync_touch=True,
        ).sudo().write(values)
        project = self.env['project.project'].sudo().browse(project.id)

        run = False
        if project._is_pg_mirror_sync_enabled():
            run = project._get_pg_mirror_sync_service().queue_project(
                project,
                trigger_type='legacy_migration',
                trigger_model='project.project',
                trigger_record_id=project.id,
            )
            if run and process_run:
                project._get_pg_mirror_sync_service().process_run(run)
        elif not (project.pg_scope_sync_enabled or project.pg_status_sync_enabled):
            project.sudo().write(
                {
                    'pg_mirror_migration_last_status': 'error',
                    'pg_mirror_migration_last_message': _(
                        "Migration completed, but no mirror sync flow is enabled yet for this project."
                    ),
                }
            )
        return run
