import hashlib
import json
import logging

from odoo import _, fields
from odoo.exceptions import UserError

from .github_repository_publisher import GitHubRepositoryPublisher
from .project_mirror_context_builder import ProjectMirrorContextBuilder
from .project_mirror_payload_builder import ProjectMirrorPayloadBuilder
from .project_sync_quality_review_service import ProjectSyncQualityReviewService
from .text_hygiene import build_scope_quality_feedback

_logger = logging.getLogger(__name__)


class ProjectMirrorSyncService:
    def __init__(self, env):
        self.env = env
        self.payload_builder = ProjectMirrorPayloadBuilder(env)
        self.context_builder = ProjectMirrorContextBuilder()
        self.publisher = GitHubRepositoryPublisher(env)

    def _update_project_status(self, project, values):
        project.with_context(pg_skip_mirror_sync_enqueue=True).sudo().write(values)

    def _append_run_log(self, run, message):
        current_log = run.log or ''
        updated_log = f"{current_log}\n{message}".strip() if current_log else message
        run.sudo().write({'log': updated_log})

    def _is_event_driven_allowed(self, project, trigger_type):
        if trigger_type in {'manual', 'scheduled_rebuild'}:
            return True
        return project.pg_scope_sync_mode == 'event_driven'

    def _build_compound_hash(self, *payloads):
        payload_hashes = [payload['source_metadata']['payload_hash'] for payload in payloads]
        serialized = json.dumps(payload_hashes, ensure_ascii=True, sort_keys=True)
        return f"sha256:{hashlib.sha256(serialized.encode('utf-8')).hexdigest()}"

    def _persist_quality_review(self, project, run, review):
        quality_status = review.get('summary_status') or 'ok'
        if quality_status == ProjectSyncQualityReviewService.SEVERITY_OBSERVATION:
            quality_status = 'ok'
        warning_count = len(review.get('warning_findings') or [])
        blocking_count = len(review.get('blocking_findings') or [])
        feedback = review.get('feedback') or False
        included_scope_count = int(review.get('included_scope_count') or 0)
        factual_scope_backlog_count = int(review.get('factual_scope_backlog_count') or 0)
        factual_scope_backlog_reason_counts = review.get('factual_scope_backlog_reason_counts') or {}
        excluded_noise_count = int(review.get('excluded_noise_count') or 0)
        excluded_noise_reason_counts = review.get('excluded_noise_reason_counts') or {}
        scope_feedback = build_scope_quality_feedback(
            included_scope_count,
            factual_scope_backlog_count,
            factual_scope_backlog_reason_counts,
            excluded_noise_count,
            excluded_noise_reason_counts,
        )
        factual_scope_backlog_reason_summary = scope_feedback['factual_scope_backlog_reason_summary']
        factual_scope_backlog_feedback = scope_feedback['factual_scope_backlog_feedback']
        excluded_noise_reason_summary = scope_feedback['excluded_noise_reason_summary']
        excluded_noise_feedback = scope_feedback['excluded_noise_feedback']
        scope_signal_feedback = scope_feedback['scope_signal_feedback']
        run.sudo().write(
            {
                'quality_review_status': quality_status,
                'quality_review_warning_count': warning_count,
                'quality_review_blocking_count': blocking_count,
                'quality_review_feedback': feedback,
                'included_scope_count': included_scope_count,
                'factual_scope_backlog_count': factual_scope_backlog_count,
                'factual_scope_backlog_reason_summary': factual_scope_backlog_reason_summary,
                'factual_scope_backlog_feedback': factual_scope_backlog_feedback,
                'excluded_noise_count': excluded_noise_count,
                'excluded_noise_reason_summary': excluded_noise_reason_summary,
                'excluded_noise_feedback': excluded_noise_feedback,
                'scope_signal_feedback': scope_signal_feedback,
            }
        )
        self._update_project_status(
            project,
            {
                'pg_mirror_sync_quality_review_status': quality_status,
                'pg_mirror_sync_quality_review_feedback': feedback,
                'pg_mirror_sync_quality_warning_count': warning_count,
                'pg_mirror_sync_quality_blocking_count': blocking_count,
                'pg_mirror_included_scope_count': included_scope_count,
                'pg_mirror_scope_backlog_count': factual_scope_backlog_count,
                'pg_mirror_scope_backlog_reason_summary': factual_scope_backlog_reason_summary,
                'pg_mirror_scope_backlog_feedback': factual_scope_backlog_feedback,
                'pg_mirror_excluded_noise_count': excluded_noise_count,
                'pg_mirror_excluded_noise_reason_summary': excluded_noise_reason_summary,
                'pg_mirror_excluded_noise_feedback': excluded_noise_feedback,
                'pg_mirror_scope_signal_feedback': scope_signal_feedback,
            },
        )

    def _review_mirror_payloads(self, project, run, project_payload, planning_payload, tasks_payload, chatter_payload, attachments_payload):
        review = project._get_pg_sync_quality_review_service().review_mirror_payload(
            project_payload,
            planning_payload,
            tasks_payload,
            chatter_payload,
            attachments_payload,
        )
        self._persist_quality_review(project, run, review)
        feedback = review.get('feedback')
        if feedback:
            self._append_run_log(run, feedback)
        return review

    def _history_event_type(self, trigger_type):
        mapping = {
            'task_create': 'task.created',
            'task_write': 'task.updated',
            'task_unlink': 'task.deleted',
            'message_create': 'chatter.message_created',
            'message_write': 'chatter.message_updated',
            'message_unlink': 'chatter.message_deleted',
            'attachment_create': 'attachment.created',
            'attachment_write': 'attachment.updated',
            'attachment_unlink': 'attachment.deleted',
            'project_write': 'project.updated',
            'legacy_migration': 'project.legacy_migrated',
            'milestone_create': 'planning.milestone_created',
            'milestone_write': 'planning.updated',
            'milestone_unlink': 'planning.milestone_deleted',
            'scheduled_rebuild': 'project.snapshot_refreshed',
            'manual': 'project.snapshot_refreshed',
        }
        return mapping.get(trigger_type or 'manual', 'project.snapshot_refreshed')

    def _history_summary(self, project, trigger_type, trigger_model, trigger_record_id):
        labels = {
            'task_create': _("Task created and mirrored to the repository context."),
            'task_write': _("Task updated and mirrored to the repository context."),
            'task_unlink': _("Task removed and repository context refreshed."),
            'message_create': _("Chatter message created and mirrored to the repository context."),
            'message_write': _("Chatter message updated and mirrored to the repository context."),
            'message_unlink': _("Chatter message removed and repository context refreshed."),
            'attachment_create': _("Attachment metadata created and mirrored to the repository context."),
            'attachment_write': _("Attachment metadata updated and mirrored to the repository context."),
            'attachment_unlink': _("Attachment metadata removed and repository context refreshed."),
            'project_write': _("Project context updated and mirrored to the repository."),
            'legacy_migration': _("Legacy project configuration migrated and mirrored to the repository."),
            'milestone_create': _("Planning milestone created and mirrored to the repository."),
            'milestone_write': _("Planning milestone updated and mirrored to the repository."),
            'milestone_unlink': _("Planning milestone removed and repository context refreshed."),
            'scheduled_rebuild': _("Project repository context rebuilt from Odoo."),
            'manual': _("Project repository context synchronized manually."),
        }
        if trigger_model and trigger_record_id:
            return "%s [%s:%s]" % (
                labels.get(trigger_type or 'manual', _("Project repository context synchronized.")),
                trigger_model,
                trigger_record_id,
            )
        return labels.get(trigger_type or 'manual', _("Project repository context synchronized."))

    def _publish_context_only(self, project, run, project_payload, planning_payload, tasks_payload, chatter_payload, attachments_payload, payload_hash):
        self._append_run_log(run, _("Project mirror snapshot unchanged; rebuilding PG_CONTEXT.md only."))
        existing_history_text = self.publisher.github_service.get_repository_file_text(
            project.pg_repository_id,
            self.publisher.MIRROR_HISTORY_PATH,
            branch=project.pg_repo_branch,
        )
        history_events = self.context_builder.parse_history_events_text(existing_history_text)
        context_markdown = self.context_builder.build_context_markdown(
            project_payload,
            planning_payload,
            tasks_payload,
            chatter_payload,
            attachments_payload,
            history_events=history_events,
        )
        context_result = self.publisher.publish_project_context(
            project.pg_repository_id,
            project.pg_repo_branch,
            context_markdown,
        )
        now = fields.Datetime.now()
        run.write(
            {
                'status': 'done',
                'message': _('Project context regenerated successfully.'),
                'published_context_file_sha': (context_result.get('content') or {}).get('sha') or '',
                'published_commit_sha': (context_result.get('commit') or {}).get('sha') or '',
                'finished_at': now,
            }
        )
        self._update_project_status(
            project,
            {
                'pg_mirror_sync_last_status': 'done',
                'pg_mirror_sync_last_payload_hash': payload_hash,
                'pg_mirror_sync_last_published_at': now,
                'pg_mirror_sync_last_message': _('Project context regenerated in repository.'),
            },
        )
        return run

    def queue_project(self, project, trigger_type='manual', trigger_model='project.project', trigger_record_id=None):
        project = project.exists()
        if not project or not project._is_pg_mirror_sync_enabled():
            return False
        if not self._is_event_driven_allowed(project, trigger_type):
            return False

        existing_run = self.env['pg.project.mirror.sync.run'].sudo().search(
            [('project_id', '=', project.id), ('status', 'in', ('queued', 'running'))],
            order='create_date asc, id asc',
            limit=1,
        )
        if existing_run:
            return existing_run

        run = self.env['pg.project.mirror.sync.run'].sudo().create(
            {
                'project_id': project.id,
                'status': 'queued',
                'trigger_type': trigger_type,
                'trigger_model': trigger_model,
                'trigger_record_id': trigger_record_id or project.id,
                'message': _('Queued for project mirror synchronization.'),
            }
        )
        self._update_project_status(
            project,
            {
                'pg_mirror_sync_last_status': 'queued',
                'pg_mirror_sync_last_message': _('Project mirror sync queued.'),
            },
        )
        return run

    def queue_from_refs(self, refs, trigger_type, trigger_model, trigger_record_id=None):
        project_ids = set()
        task_ids = set()
        for model_name, record_id in refs:
            if not record_id:
                continue
            if model_name == 'project.project':
                project_ids.add(record_id)
            elif model_name == 'project.task':
                task_ids.add(record_id)

        projects = self.env['project.project'].sudo().browse(list(project_ids)).exists()
        tasks = self.env['project.task'].sudo().browse(list(task_ids)).exists()
        projects |= tasks.mapped('project_id')
        runs = self.env['pg.project.mirror.sync.run']
        for project in projects:
            runs |= self.queue_project(
                project,
                trigger_type=trigger_type,
                trigger_model=trigger_model,
                trigger_record_id=trigger_record_id,
            ) or self.env['pg.project.mirror.sync.run']
        return runs

    def process_run(self, run):
        run = run.sudo().exists()
        if not run:
            return False

        project = run.project_id.sudo().exists()
        if not project:
            run.write(
                {
                    'status': 'error',
                    'message': _('Project no longer exists.'),
                    'finished_at': fields.Datetime.now(),
                }
            )
            return False

        if not project._is_pg_mirror_sync_enabled():
            run.write(
                {
                    'status': 'skipped',
                    'message': _('Project mirror sync is disabled for this project.'),
                    'finished_at': fields.Datetime.now(),
                }
            )
            return run

        if not project.pg_repository_id or not (project.pg_repo_branch or '').strip():
            raise UserError(_("The project must define both a repository and a repository branch for mirror sync."))

        run.write({'status': 'running', 'started_at': fields.Datetime.now(), 'message': _('Building mirror payloads.')})
        self._update_project_status(
            project,
            {
                'pg_mirror_sync_last_status': 'running',
                'pg_mirror_sync_last_message': _('Building project mirror payloads.'),
            },
        )

        try:
            project_payload = self.payload_builder.build_project_payload(
                project,
                trigger_type=run.trigger_type,
                trigger_model=run.trigger_model,
                trigger_record_id=run.trigger_record_id,
            )
            planning_payload = self.payload_builder.build_planning_payload(
                project,
                trigger_type=run.trigger_type,
                trigger_model=run.trigger_model,
                trigger_record_id=run.trigger_record_id,
            )
            tasks_payload = self.payload_builder.build_tasks_payload(
                project,
                trigger_type=run.trigger_type,
                trigger_model=run.trigger_model,
                trigger_record_id=run.trigger_record_id,
            )
            chatter_payload = self.payload_builder.build_chatter_payload(
                project,
                trigger_type=run.trigger_type,
                trigger_model=run.trigger_model,
                trigger_record_id=run.trigger_record_id,
            )
            attachments_payload = self.payload_builder.build_attachments_payload(
                project,
                trigger_type=run.trigger_type,
                trigger_model=run.trigger_model,
                trigger_record_id=run.trigger_record_id,
            )
            payload_hash = self._build_compound_hash(
                project_payload,
                planning_payload,
                tasks_payload,
                chatter_payload,
                attachments_payload,
            )
            run.write({'payload_hash': payload_hash})
            mirror_review = self._review_mirror_payloads(
                project,
                run,
                project_payload,
                planning_payload,
                tasks_payload,
                chatter_payload,
                attachments_payload,
            )
            if project.pg_mirror_sync_last_payload_hash == payload_hash:
                if run.trigger_type == 'scheduled_rebuild':
                    return self._publish_context_only(
                        project,
                        run,
                        project_payload,
                        planning_payload,
                        tasks_payload,
                        chatter_payload,
                        attachments_payload,
                        payload_hash,
                    )
                run.write(
                    {
                        'status': 'skipped',
                        'message': _('Project mirror snapshot unchanged; synchronization skipped.'),
                        'finished_at': fields.Datetime.now(),
                    }
                )
                self._update_project_status(
                    project,
                    {
                        'pg_mirror_sync_last_status': 'skipped',
                        'pg_mirror_sync_last_message': _('Project mirror snapshot unchanged; nothing to publish.'),
                    },
                )
                return run

            self._append_run_log(run, _("Publishing project mirror artifacts to GitHub."))
            project_result = self.publisher.publish_project_mirror_payload(
                project.pg_repository_id,
                project.pg_repo_branch,
                project_payload,
            )
            planning_result = self.publisher.publish_planning_mirror_payload(
                project.pg_repository_id,
                project.pg_repo_branch,
                planning_payload,
            )
            tasks_result = self.publisher.publish_tasks_mirror_payload(
                project.pg_repository_id,
                project.pg_repo_branch,
                tasks_payload,
            )
            chatter_result = self.publisher.publish_chatter_mirror_payload(
                project.pg_repository_id,
                project.pg_repo_branch,
                chatter_payload,
            )
            attachments_result = self.publisher.publish_attachments_mirror_payload(
                project.pg_repository_id,
                project.pg_repo_branch,
                attachments_payload,
            )
            history_event = self.payload_builder.build_history_event(
                project,
                event_type=self._history_event_type(run.trigger_type),
                entity_model=run.trigger_model or 'project.project',
                entity_id=run.trigger_record_id or project.id,
                summary=self._history_summary(project, run.trigger_type, run.trigger_model, run.trigger_record_id),
                event_data={
                    'payload_hash': payload_hash,
                    'artifacts': [
                        self.publisher.MIRROR_PROJECT_PATH,
                        self.publisher.MIRROR_PLANNING_PATH,
                        self.publisher.MIRROR_TASKS_PATH,
                        self.publisher.MIRROR_CHATTER_PATH,
                        self.publisher.MIRROR_ATTACHMENTS_PATH,
                        self.publisher.PROJECT_CONTEXT_PATH,
                    ],
                },
                trigger_type=run.trigger_type,
            )
            existing_history_text = self.publisher.github_service.get_repository_file_text(
                project.pg_repository_id,
                self.publisher.MIRROR_HISTORY_PATH,
                branch=project.pg_repo_branch,
            )
            history_events = self.context_builder.parse_history_events_text(existing_history_text)
            history_events.insert(0, history_event)
            context_markdown = self.context_builder.build_context_markdown(
                project_payload,
                planning_payload,
                tasks_payload,
                chatter_payload,
                attachments_payload,
                history_events=history_events,
            )
            history_result = self.publisher.append_project_mirror_history_event(
                project.pg_repository_id,
                project.pg_repo_branch,
                history_event,
            )
            context_result = self.publisher.publish_project_context(
                project.pg_repository_id,
                project.pg_repo_branch,
                context_markdown,
            )

            run.write(
                {
                    'status': 'done',
                    'message': _(
                        'Project mirror synchronized successfully with quality warnings.'
                    )
                    if mirror_review.get('summary_status') == ProjectSyncQualityReviewService.SEVERITY_WARNING
                    else _('Project mirror synchronized successfully.'),
                    'published_project_file_sha': (project_result.get('content') or {}).get('sha') or '',
                    'published_planning_file_sha': (planning_result.get('content') or {}).get('sha') or '',
                    'published_tasks_file_sha': (tasks_result.get('content') or {}).get('sha') or '',
                    'published_chatter_file_sha': (chatter_result.get('content') or {}).get('sha') or '',
                    'published_attachments_file_sha': (attachments_result.get('content') or {}).get('sha') or '',
                    'published_history_file_sha': (history_result.get('content') or {}).get('sha') or '',
                    'published_context_file_sha': (context_result.get('content') or {}).get('sha') or '',
                    'published_commit_sha': (context_result.get('commit') or {}).get('sha')
                    or (history_result.get('commit') or {}).get('sha')
                    or (attachments_result.get('commit') or {}).get('sha')
                    or (chatter_result.get('commit') or {}).get('sha')
                    or (tasks_result.get('commit') or {}).get('sha')
                    or (planning_result.get('commit') or {}).get('sha')
                    or (project_result.get('commit') or {}).get('sha')
                    or '',
                    'finished_at': fields.Datetime.now(),
                }
            )
            self._update_project_status(
                project,
                {
                    'pg_mirror_sync_last_status': 'done',
                    'pg_mirror_sync_last_payload_hash': payload_hash,
                    'pg_mirror_sync_last_published_at': fields.Datetime.now(),
                    'pg_mirror_sync_last_message': _(
                        'Project mirror synchronized to repository with quality warnings.'
                    )
                    if mirror_review.get('summary_status') == ProjectSyncQualityReviewService.SEVERITY_WARNING
                    else _('Project mirror synchronized to repository.'),
                },
            )
            return run
        except Exception as exc:
            _logger.exception("Project mirror sync failed for run %s", run.id)
            run.write(
                {
                    'status': 'error',
                    'message': str(exc),
                    'finished_at': fields.Datetime.now(),
                }
            )
            self._update_project_status(
                project,
                {
                    'pg_mirror_sync_last_status': 'error',
                    'pg_mirror_sync_last_message': str(exc),
                },
            )
            raise
