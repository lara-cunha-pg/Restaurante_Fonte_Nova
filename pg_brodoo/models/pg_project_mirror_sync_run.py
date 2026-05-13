import logging

from odoo import _, api, fields, models

from ..services.project_mirror_sync_service import ProjectMirrorSyncService

_logger = logging.getLogger(__name__)


class PgProjectMirrorSyncRun(models.Model):
    _name = 'pg.project.mirror.sync.run'
    _description = 'PG Project Mirror Sync Run'
    _order = 'create_date desc, id desc'

    project_id = fields.Many2one('project.project', string='Project', required=True, ondelete='cascade', index=True)
    status = fields.Selection(
        [
            ('queued', 'Queued'),
            ('running', 'Running'),
            ('done', 'Done'),
            ('skipped', 'Skipped'),
            ('error', 'Error'),
        ],
        string='Status',
        required=True,
        default='queued',
        index=True,
    )
    trigger_type = fields.Selection(
        [
            ('manual', 'Manual'),
            ('task_create', 'Task Create'),
            ('task_write', 'Task Write'),
            ('task_unlink', 'Task Unlink'),
            ('message_create', 'Message Create'),
            ('message_write', 'Message Write'),
            ('message_unlink', 'Message Unlink'),
            ('attachment_create', 'Attachment Create'),
            ('attachment_write', 'Attachment Write'),
            ('attachment_unlink', 'Attachment Unlink'),
            ('project_write', 'Project Write'),
            ('legacy_migration', 'Legacy Migration'),
            ('milestone_create', 'Milestone Create'),
            ('milestone_write', 'Milestone Write'),
            ('milestone_unlink', 'Milestone Unlink'),
            ('scheduled_rebuild', 'Scheduled Rebuild'),
        ],
        string='Trigger Type',
        required=True,
        default='manual',
    )
    trigger_model = fields.Char(string='Trigger Model')
    trigger_record_id = fields.Integer(string='Trigger Record ID')
    payload_hash = fields.Char(string='Payload Hash', copy=False)
    published_project_file_sha = fields.Char(string='Published Project File SHA', copy=False)
    published_planning_file_sha = fields.Char(string='Published Planning File SHA', copy=False)
    published_tasks_file_sha = fields.Char(string='Published Tasks File SHA', copy=False)
    published_chatter_file_sha = fields.Char(string='Published Chatter File SHA', copy=False)
    published_attachments_file_sha = fields.Char(string='Published Attachments File SHA', copy=False)
    published_history_file_sha = fields.Char(string='Published History File SHA', copy=False)
    published_context_file_sha = fields.Char(string='Published PG_CONTEXT SHA', copy=False)
    published_commit_sha = fields.Char(string='Published Commit SHA', copy=False)
    quality_review_status = fields.Selection(
        [
            ('ok', 'OK'),
            ('warning', 'Warning'),
            ('blocking', 'Blocking'),
        ],
        string='Quality Review Status',
        copy=False,
    )
    quality_review_warning_count = fields.Integer(string='Quality Review Warning Count', copy=False)
    quality_review_blocking_count = fields.Integer(string='Quality Review Blocking Count', copy=False)
    quality_review_feedback = fields.Text(string='Quality Review Feedback', copy=False)
    included_scope_count = fields.Integer(string='Included Scope Count', copy=False)
    factual_scope_backlog_count = fields.Integer(string='Factual Scope Backlog Count', copy=False)
    factual_scope_backlog_reason_summary = fields.Char(string='Factual Scope Backlog Reasons', copy=False)
    factual_scope_backlog_feedback = fields.Text(string='Factual Scope Backlog Feedback', copy=False)
    excluded_noise_count = fields.Integer(string='Excluded Noise Count', copy=False)
    excluded_noise_reason_summary = fields.Char(string='Excluded Noise Reasons', copy=False)
    excluded_noise_feedback = fields.Text(string='Excluded Noise Feedback', copy=False)
    scope_signal_feedback = fields.Text(string='Scope Signal Feedback', copy=False)
    message = fields.Text(string='Message', copy=False)
    log = fields.Text(string='Log', copy=False)
    started_at = fields.Datetime(string='Started At', copy=False)
    finished_at = fields.Datetime(string='Finished At', copy=False)

    def _get_mirror_sync_service(self):
        return ProjectMirrorSyncService(self.env)

    def action_process_now(self):
        for run in self:
            self._get_mirror_sync_service().process_run(run)
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    @api.model
    def _cron_process_mirror_sync_queue(self, limit=5):
        runs = self.search([('status', '=', 'queued')], order='create_date asc, id asc', limit=limit)
        for run in runs:
            try:
                self._get_mirror_sync_service().process_run(run)
            except Exception:
                _logger.exception("Mirror sync queue failed for run %s", run.id)
        return len(runs)
