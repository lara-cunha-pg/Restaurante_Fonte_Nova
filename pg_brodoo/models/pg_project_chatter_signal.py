from odoo import fields, models


PG_CHATTER_SIGNAL_TYPE_SELECTION = [
    ('blocker', 'Blocker'),
    ('risk', 'Risk'),
    ('decision', 'Decision'),
    ('approval', 'Approval'),
    ('scope_change', 'Scope Change'),
    ('next_step', 'Next Step'),
    ('dependency', 'Dependency'),
]

PG_CHATTER_SIGNAL_STATE_SELECTION = [
    ('candidate', 'Candidate'),
    ('validated', 'Validated'),
    ('stale', 'Stale'),
    ('rejected', 'Rejected'),
]

PG_CHATTER_SIGNAL_VISIBILITY_SELECTION = [
    ('internal', 'Internal'),
    ('external', 'External'),
]

PG_CHATTER_SIGNAL_ENGINE_SELECTION = [
    ('rule_based', 'Rule-Based'),
    ('llm_hybrid', 'LLM Hybrid'),
]


class PgProjectChatterSignal(models.Model):
    _name = 'pg.project.chatter.signal'
    _description = 'PG Project Chatter Signal'
    _order = 'occurred_at desc, id desc'

    message_id = fields.Many2one('mail.message', string='Source Message', ondelete='set null', readonly=True)
    source_message_id = fields.Integer(string='Source Message ID', readonly=True, index=True)
    source_model = fields.Char(string='Source Model', required=True, readonly=True, index=True)
    source_record_id = fields.Integer(string='Source Record ID', required=True, readonly=True, index=True)
    project_id = fields.Many2one('project.project', string='Project', ondelete='cascade', index=True, readonly=True)
    task_id = fields.Many2one('project.task', string='Task', ondelete='cascade', index=True, readonly=True)
    signal_type = fields.Selection(
        PG_CHATTER_SIGNAL_TYPE_SELECTION,
        string='Signal Type',
        required=True,
        readonly=True,
        index=True,
    )
    signal_state = fields.Selection(
        PG_CHATTER_SIGNAL_STATE_SELECTION,
        string='Signal State',
        required=True,
        default='candidate',
        readonly=True,
        index=True,
    )
    summary = fields.Char(string='Summary', required=True, readonly=True)
    evidence_excerpt = fields.Text(string='Evidence Excerpt', readonly=True)
    confidence = fields.Integer(string='Confidence', readonly=True)
    author_id = fields.Many2one('res.partner', string='Author', ondelete='set null', readonly=True)
    occurred_at = fields.Datetime(string='Occurred At', readonly=True, index=True)
    visibility = fields.Selection(
        PG_CHATTER_SIGNAL_VISIBILITY_SELECTION,
        string='Visibility',
        default='internal',
        readonly=True,
    )
    engine = fields.Selection(
        PG_CHATTER_SIGNAL_ENGINE_SELECTION,
        string='Engine',
        default='rule_based',
        readonly=True,
    )
    content_hash = fields.Char(string='Content Hash', readonly=True, index=True)
    validation_feedback = fields.Text(string='Validation Feedback', readonly=True)

