import hashlib
import logging

from odoo import _, fields
from odoo.exceptions import UserError

from .github_repository_publisher import GitHubRepositoryPublisher
from .project_scope_payload_builder import ProjectScopePayloadBuilder
from .project_sync_quality_review_service import ProjectSyncQualityReviewService

_logger = logging.getLogger(__name__)


class ProjectScopeSyncService:
    def __init__(self, env):
        self.env = env
        self.payload_builder = ProjectScopePayloadBuilder(env)
        self.publisher = GitHubRepositoryPublisher(env)
        self.quality_review_service = ProjectSyncQualityReviewService(env)

    def _update_project_status(self, project, values):
        project.with_context(pg_skip_scope_sync_enqueue=True).sudo().write(values)

    def _append_run_log(self, run, message):
        current_log = run.log or ''
        updated_log = f"{current_log}\n{message}".strip() if current_log else message
        run.sudo().write({'log': updated_log})

    def _is_event_driven_allowed(self, project, trigger_type):
        if trigger_type == 'manual':
            return True
        return project.pg_scope_sync_mode == 'event_driven'

    def queue_project(self, project, trigger_type='manual', trigger_model='project.project', trigger_record_id=None):
        project = project.exists()
        if not project or not project.pg_scope_sync_enabled:
            return False
        if not self._is_event_driven_allowed(project, trigger_type):
            return False
        if not project.pg_repository_id or not (project.pg_repo_branch or '').strip():
            return False

        existing_run = self.env['pg.project.scope.sync.run'].sudo().search(
            [('project_id', '=', project.id), ('status', 'in', ('queued', 'running'))],
            order='create_date asc, id asc',
            limit=1,
        )
        if existing_run:
            return existing_run

        run = self.env['pg.project.scope.sync.run'].sudo().create(
            {
                'project_id': project.id,
                'status': 'queued',
                'trigger_type': trigger_type,
                'trigger_model': trigger_model,
                'trigger_record_id': trigger_record_id or project.id,
                'snapshot_path': '.pg/PG_SCOPE_SYNC.json',
                'message': _('Queued for scope publication.'),
            }
        )
        self._update_project_status(
            project,
            {
                'pg_scope_sync_last_status': 'queued',
                'pg_scope_sync_last_message': _('Scope sync queued.'),
            },
        )
        return run

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

        if not project.pg_repository_id or not (project.pg_repo_branch or '').strip():
            raise UserError(_("The project must define both a repository and a repository branch for scope sync."))

        run.write({'status': 'running', 'started_at': fields.Datetime.now(), 'message': _('Building payload.')})
        self._update_project_status(
            project,
            {
                'pg_scope_sync_last_status': 'running',
                'pg_scope_sync_last_message': _('Building project scope payload.'),
            },
        )

        try:
            payload = self.payload_builder.build_payload(
                project,
                trigger_type=run.trigger_type,
                trigger_model=run.trigger_model,
                trigger_record_id=run.trigger_record_id,
                sync_reason=f"{run.trigger_model or 'project.project'} {run.trigger_record_id or project.id}",
            )
            review = self.quality_review_service.review_scope_payload(payload)
            if review.get('feedback'):
                self._append_run_log(run, review['feedback'])
            hashable_payload = self.payload_builder.build_hashable_payload(payload)
            payload_hash = hashlib.sha256(self.payload_builder.serialize_payload(hashable_payload).encode('utf-8')).hexdigest()
            payload['source_metadata']['payload_hash'] = f"sha256:{payload_hash}"
            run.write({'payload_hash': payload['source_metadata']['payload_hash']})

            if project.pg_scope_sync_last_payload_hash == payload['source_metadata']['payload_hash']:
                run.write(
                    {
                        'status': 'skipped',
                        'message': _('Scope snapshot unchanged; publication skipped.'),
                        'finished_at': fields.Datetime.now(),
                    }
                )
                self._update_project_status(
                    project,
                    {
                        'pg_scope_sync_last_status': 'skipped',
                        'pg_scope_sync_last_message': _('Scope snapshot unchanged; nothing to publish.'),
                        'pg_scope_sync_quality_review_feedback': review.get('feedback') or False,
                    },
                )
                return run

            self._append_run_log(run, _("Publishing scope snapshot to GitHub repository."))
            publish_result = self.publisher.publish_project_scope_snapshot(
                project.pg_repository_id,
                project.pg_repo_branch,
                payload,
            )

            run.write(
                {
                    'status': 'done',
                    'message': _('Scope snapshot published successfully.'),
                    'published_file_sha': (publish_result.get('content') or {}).get('sha') or '',
                    'published_commit_sha': (publish_result.get('commit') or {}).get('sha') or '',
                    'finished_at': fields.Datetime.now(),
                }
            )
            self._update_project_status(
                project,
                {
                    'pg_scope_sync_last_status': 'done',
                    'pg_scope_sync_last_payload_hash': payload['source_metadata']['payload_hash'],
                    'pg_scope_sync_last_published_at': fields.Datetime.now(),
                    'pg_scope_sync_last_message': _('Scope snapshot published to repository.'),
                    'pg_scope_sync_quality_review_feedback': review.get('feedback') or False,
                },
            )
            return run
        except Exception as exc:
            _logger.exception("Project scope sync failed for run %s", run.id)
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
                    'pg_scope_sync_last_status': 'error',
                    'pg_scope_sync_last_message': str(exc),
                },
            )
            raise
