import logging

from odoo import api, fields, models

from ..services.project_status_sync_service import ProjectStatusSyncService

_logger = logging.getLogger(__name__)


class PgProjectStatusSyncRun(models.Model):
    _name = 'pg.project.status.sync.run'
    _description = 'PG Project Status Sync Run'
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
            ('manual_button', 'Manual Button'),
            ('project_write', 'Project Write'),
        ],
        string='Trigger Type',
        required=True,
        default='manual_button',
    )
    trigger_model = fields.Char(string='Trigger Model')
    trigger_record_id = fields.Integer(string='Trigger Record ID')
    payload_hash = fields.Char(string='Payload Hash', copy=False)
    published_file_sha = fields.Char(string='Published File SHA', copy=False)
    published_commit_sha = fields.Char(string='Published Commit SHA', copy=False)
    snapshot_path = fields.Char(string='Snapshot Path', required=True, default='.pg/PG_PROJECT_STATUS_SYNC.json')
    message = fields.Text(string='Message', copy=False)
    log = fields.Text(string='Log', copy=False)
    started_at = fields.Datetime(string='Started At', copy=False)
    finished_at = fields.Datetime(string='Finished At', copy=False)

    def _get_status_sync_service(self):
        return ProjectStatusSyncService(self.env)

    def action_process_now(self):
        for run in self:
            self._get_status_sync_service().process_run(run)
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    @api.model
    def _cron_process_status_sync_queue(self, limit=5):
        runs = self.search([('status', '=', 'queued')], order='create_date asc, id asc', limit=limit)
        for run in runs:
            try:
                self._get_status_sync_service().process_run(run)
            except Exception:
                _logger.exception("Status sync queue failed for run %s", run.id)
        return len(runs)
