from odoo import fields, models


PG_PROJECT_RISK_SEVERITY_SELECTION = [
    ('low', 'Low'),
    ('medium', 'Medium'),
    ('high', 'High'),
    ('critical', 'Critical'),
]

PG_PROJECT_RISK_STATE_SELECTION = [
    ('open', 'Open'),
    ('monitoring', 'Monitoring'),
    ('mitigated', 'Mitigated'),
    ('closed', 'Closed'),
]


class PgProjectRisk(models.Model):
    _name = 'pg.project.risk'
    _description = 'PG Project Risk'
    _order = 'sequence asc, id asc'

    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    project_id = fields.Many2one('project.project', string='Project', required=True, ondelete='cascade', index=True)
    name = fields.Char(string='Title', required=True)
    description = fields.Text(string='Description', required=True)
    severity = fields.Selection(
        PG_PROJECT_RISK_SEVERITY_SELECTION,
        string='Severity',
        required=True,
        default='medium',
        index=True,
    )
    state = fields.Selection(
        PG_PROJECT_RISK_STATE_SELECTION,
        string='Status',
        required=True,
        default='open',
        index=True,
    )
    mitigation = fields.Text(string='Mitigation', required=True)
    owner_id = fields.Many2one('res.users', string='Owner', required=True, index=True)
    last_review_at = fields.Datetime(string='Last Review At', required=True, default=fields.Datetime.now, index=True)
    source_reference = fields.Char(string='Source Reference')
    notes = fields.Text(string='Notes')

