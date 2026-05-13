from odoo import api, fields, models

from ..services.project_scope_sync_service import ProjectScopeSyncService


class PgProjectScopeLine(models.Model):
    _name = 'pg.project.scope.line'
    _description = 'PG Project Scope Line'
    _order = 'line_type, sequence, id'

    project_id = fields.Many2one('project.project', string='Project', required=True, ondelete='cascade', index=True)
    line_type = fields.Selection(
        [
            ('acceptance_criteria', 'Acceptance Criteria'),
            ('users_and_roles', 'Users And Roles'),
            ('known_exceptions', 'Known Exceptions'),
            ('approvals', 'Approvals'),
            ('documents', 'Documents'),
            ('integrations', 'Integrations'),
            ('reporting_needs', 'Reporting Needs'),
            ('standard_attempted_or_validated', 'Standard Attempted Or Validated'),
            ('why_standard_was_insufficient', 'Why Standard Was Insufficient'),
        ],
        string='Line Type',
        required=True,
        index=True,
    )
    sequence = fields.Integer(default=10)
    text = fields.Text(string='Text', required=True)
    active = fields.Boolean(default=True)

    def _get_scope_sync_service(self):
        return ProjectScopeSyncService(self.env)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get('pg_skip_scope_sync_enqueue'):
            for project in records.mapped('project_id'):
                self._get_scope_sync_service().queue_project(
                    project,
                    trigger_type='project_write',
                    trigger_model='pg.project.scope.line',
                    trigger_record_id=records[:1].id if records else False,
                )
        return records

    def write(self, vals):
        projects = self.mapped('project_id')
        result = super().write(vals)
        if not self.env.context.get('pg_skip_scope_sync_enqueue'):
            for project in projects | self.mapped('project_id'):
                self._get_scope_sync_service().queue_project(
                    project,
                    trigger_type='project_write',
                    trigger_model='pg.project.scope.line',
                    trigger_record_id=self[:1].id if self else False,
                )
        return result

    def unlink(self):
        projects = self.mapped('project_id')
        trigger_record_id = self[:1].id if self else False
        result = super().unlink()
        if not self.env.context.get('pg_skip_scope_sync_enqueue'):
            for project in projects:
                self._get_scope_sync_service().queue_project(
                    project,
                    trigger_type='project_write',
                    trigger_model='pg.project.scope.line',
                    trigger_record_id=trigger_record_id,
                )
        return result
