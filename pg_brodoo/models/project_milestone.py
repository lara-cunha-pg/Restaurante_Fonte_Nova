from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


PG_DELIVERY_STATE_SELECTION = [
    ('planned', 'Planned'),
    ('in_progress', 'In Progress'),
    ('delivered', 'Delivered'),
]

PG_ACCEPTANCE_STATE_SELECTION = [
    ('pending', 'Pending'),
    ('accepted', 'Accepted'),
    ('rejected', 'Rejected'),
]

PG_PLAN_STATUS_SELECTION = [
    ('planned', 'Planned'),
    ('in_progress', 'In Progress'),
    ('completed', 'Completed'),
]


class ProjectMilestone(models.Model):
    _inherit = 'project.milestone'

    active = fields.Boolean(string='Active', default=True)
    pg_delivery_state = fields.Selection(
        PG_DELIVERY_STATE_SELECTION,
        string='Delivery State',
        required=True,
        default='planned',
        tracking=True,
        index=True,
    )
    pg_delivery_owner_id = fields.Many2one(
        'res.users',
        string='Delivery Owner',
        tracking=True,
        index=True,
    )
    pg_acceptance_state = fields.Selection(
        PG_ACCEPTANCE_STATE_SELECTION,
        string='Acceptance State',
        required=True,
        default='pending',
        tracking=True,
        index=True,
    )
    pg_delivery_source_reference = fields.Char(string='Delivery Source Reference', tracking=True)
    pg_delivery_notes = fields.Text(string='Delivery Notes')
    pg_plan_start_date = fields.Date(string='Plan Start Date', tracking=True, index=True)
    pg_plan_status = fields.Selection(
        PG_PLAN_STATUS_SELECTION,
        string='Plan Status',
        tracking=True,
        index=True,
    )
    pg_plan_owner_id = fields.Many2one(
        'res.users',
        string='Plan Owner',
        tracking=True,
        index=True,
    )
    pg_plan_dependency_refs = fields.Text(string='Plan Dependency Refs', tracking=True)

    @api.model
    def _normalize_pg_delivery_values(self, values, milestone=None):
        normalized = dict(values)
        if 'pg_delivery_state' in normalized:
            normalized['is_reached'] = normalized['pg_delivery_state'] == 'delivered'
        elif 'is_reached' in normalized:
            if normalized['is_reached']:
                normalized['pg_delivery_state'] = 'delivered'
            elif milestone and milestone.pg_delivery_state == 'delivered':
                normalized['pg_delivery_state'] = 'planned'
        return normalized

    @api.model_create_multi
    def create(self, vals_list):
        normalized_vals_list = [self._normalize_pg_delivery_values(values) for values in vals_list]
        milestones = super().create(normalized_vals_list)
        if not self.env.context.get('pg_skip_mirror_sync_enqueue'):
            for project in milestones.mapped('project_id').exists():
                project._get_pg_mirror_sync_service().queue_project(
                    project,
                    trigger_type='milestone_create',
                    trigger_model='project.milestone',
                    trigger_record_id=milestones[:1].id if milestones else False,
                )
        return milestones

    def write(self, vals):
        old_projects = self.mapped('project_id')
        if 'pg_delivery_state' not in vals and 'is_reached' not in vals:
            result = super().write(vals)
        else:
            for milestone in self:
                super(ProjectMilestone, milestone).write(self._normalize_pg_delivery_values(vals, milestone))
            result = True

        if not self.env.context.get('pg_skip_mirror_sync_enqueue'):
            for project in (old_projects | self.mapped('project_id')).exists():
                project._get_pg_mirror_sync_service().queue_project(
                    project,
                    trigger_type='milestone_write',
                    trigger_model='project.milestone',
                    trigger_record_id=self[:1].id if self else False,
                )
        return result

    def unlink(self):
        old_projects = self.mapped('project_id')
        trigger_record_id = self[:1].id if self else False
        result = super().unlink()
        if not self.env.context.get('pg_skip_mirror_sync_enqueue'):
            for project in old_projects.exists():
                project._get_pg_mirror_sync_service().queue_project(
                    project,
                    trigger_type='milestone_unlink',
                    trigger_model='project.milestone',
                    trigger_record_id=trigger_record_id,
                )
        return result

    @api.constrains('pg_delivery_state', 'is_reached')
    def _check_pg_delivery_state_consistency(self):
        for milestone in self:
            if milestone.pg_delivery_state == 'delivered' and not milestone.is_reached:
                raise ValidationError(_("Delivered milestones must also be marked as reached."))
            if milestone.pg_delivery_state != 'delivered' and milestone.is_reached:
                raise ValidationError(_("Only delivered milestones can be marked as reached."))

    @api.constrains('pg_delivery_state', 'pg_acceptance_state')
    def _check_pg_acceptance_state_consistency(self):
        for milestone in self:
            if milestone.pg_acceptance_state in {'accepted', 'rejected'} and milestone.pg_delivery_state != 'delivered':
                raise ValidationError(_("Accepted or rejected deliveries must first be marked as delivered."))
