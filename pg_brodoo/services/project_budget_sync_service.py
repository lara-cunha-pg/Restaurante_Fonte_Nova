import logging

from odoo import _, fields
from odoo.exceptions import UserError

from .github_repository_publisher import GitHubRepositoryPublisher
from .project_budget_payload_builder import ProjectBudgetPayloadBuilder
from .project_sync_quality_review_service import ProjectSyncQualityReviewService

_logger = logging.getLogger(__name__)


class ProjectBudgetSyncService:
    def __init__(self, env):
        self.env = env
        self.payload_builder = ProjectBudgetPayloadBuilder(env)
        self.publisher = GitHubRepositoryPublisher(env)
        self.quality_review_service = ProjectSyncQualityReviewService(env)

    def _update_project_status(self, project, values):
        project.sudo().write(values)

    def _append_run_log(self, run, message):
        current_log = run.log or ''
        updated_log = f"{current_log}\n{message}".strip() if current_log else message
        run.sudo().write({'log': updated_log})

    def queue_project(self, project, trigger_type='manual_button', trigger_model='project.project', trigger_record_id=None):
        project = project.exists()
        if not project or not project.pg_budget_sync_enabled:
            return False
        if not project.pg_repository_id or not (project.pg_repo_branch or '').strip():
            return False

        existing_run = self.env['pg.project.budget.sync.run'].sudo().search(
            [('project_id', '=', project.id), ('status', 'in', ('queued', 'running'))],
            order='create_date asc, id asc',
            limit=1,
        )
        if existing_run:
            return existing_run

        run = self.env['pg.project.budget.sync.run'].sudo().create(
            {
                'project_id': project.id,
                'status': 'queued',
                'trigger_type': trigger_type,
                'trigger_model': trigger_model,
                'trigger_record_id': trigger_record_id or project.id,
                'snapshot_path': '.pg/PG_BUDGET_SYNC.json',
                'message': _('Queued for project budget publication.'),
            }
        )
        self._update_project_status(
            project,
            {
                'pg_budget_sync_last_status': 'queued',
                'pg_budget_sync_last_message': _('Project budget sync queued.'),
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
            raise UserError(_("The project must define both a repository and a repository branch for budget sync."))

        run.write({'status': 'running', 'started_at': fields.Datetime.now(), 'message': _('Building payload.')})
        self._update_project_status(
            project,
            {
                'pg_budget_sync_last_status': 'running',
                'pg_budget_sync_last_message': _('Building project budget payload.'),
            },
        )

        try:
            payload = self.payload_builder.build_payload(
                project,
                trigger_type=run.trigger_type,
                trigger_model=run.trigger_model,
                trigger_record_id=run.trigger_record_id,
            )
            review = self.quality_review_service.review_budget_payload(payload)
            if review.get('feedback'):
                self._append_run_log(run, review['feedback'])
            payload_hash = self.payload_builder.payload_hash(payload)
            payload['source_metadata']['payload_hash'] = payload_hash
            self.payload_builder.validate_payload(payload)
            run.write({'payload_hash': payload_hash})

            if project.pg_budget_sync_last_payload_hash == payload_hash:
                run.write(
                    {
                        'status': 'skipped',
                        'message': _('Project budget snapshot unchanged; publication skipped.'),
                        'finished_at': fields.Datetime.now(),
                    }
                )
                self._update_project_status(
                    project,
                    {
                        'pg_budget_sync_last_status': 'skipped',
                        'pg_budget_sync_last_message': _('Project budget snapshot unchanged; nothing to publish.'),
                        'pg_budget_sync_quality_review_feedback': review.get('feedback') or False,
                    },
                )
                return run

            self._append_run_log(run, _("Publishing project budget snapshot to GitHub repository."))
            publish_result = self.publisher.publish_project_budget_snapshot(
                project.pg_repository_id,
                project.pg_repo_branch,
                payload,
            )

            run.write(
                {
                    'status': 'done',
                    'message': _('Project budget snapshot published successfully.'),
                    'published_file_sha': (publish_result.get('content') or {}).get('sha') or '',
                    'published_commit_sha': (publish_result.get('commit') or {}).get('sha') or '',
                    'finished_at': fields.Datetime.now(),
                }
            )
            self._update_project_status(
                project,
                {
                    'pg_budget_sync_last_status': 'done',
                    'pg_budget_sync_last_payload_hash': payload_hash,
                    'pg_budget_sync_last_published_at': fields.Datetime.now(),
                    'pg_budget_sync_last_message': _('Project budget snapshot published to repository.'),
                    'pg_budget_sync_quality_review_feedback': review.get('feedback') or False,
                },
            )
            return run
        except Exception as exc:
            _logger.exception("Project budget sync failed for run %s", run.id)
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
                    'pg_budget_sync_last_status': 'error',
                    'pg_budget_sync_last_message': str(exc),
                },
            )
            raise
