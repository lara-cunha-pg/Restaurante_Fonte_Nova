from odoo import fields, models


PG_BUDGET_LINE_STATUS_SELECTION = [
    ('draft', 'Draft'),
    ('approved', 'Approved'),
    ('consuming', 'Consuming'),
    ('closed', 'Closed'),
]


class PgProjectBudgetLine(models.Model):
    _name = 'pg.project.budget.line'
    _description = 'PG Project Budget Line'
    _order = 'sequence asc, id asc'

    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    project_id = fields.Many2one('project.project', string='Project', required=True, ondelete='cascade', index=True)
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='project_id.pg_budget_currency_id',
        store=True,
        readonly=True,
    )
    category = fields.Char(string='Category', required=True, index=True)
    planned_amount = fields.Monetary(string='Planned Amount', required=True, default=0.0, currency_field='currency_id')
    approved_amount = fields.Monetary(
        string='Approved Amount',
        required=True,
        default=0.0,
        currency_field='currency_id',
    )
    consumed_amount = fields.Monetary(
        string='Consumed Amount',
        required=True,
        default=0.0,
        currency_field='currency_id',
    )
    status = fields.Selection(
        PG_BUDGET_LINE_STATUS_SELECTION,
        string='Status',
        required=True,
        default='draft',
        index=True,
    )
    owner_id = fields.Many2one('res.users', string='Owner', required=True, index=True)
    source_reference = fields.Char(string='Source Reference')
    notes = fields.Text(string='Notes')
