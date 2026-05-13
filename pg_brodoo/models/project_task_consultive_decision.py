from odoo import fields, models


AI_CONSULTIVE_DECISION_SELECTION = [
    ('gate_ready', 'Gate Ready'),
    ('prompt_generated', 'Prompt Generated'),
    ('codex_queued', 'Codex Queued'),
]

AI_CONSULTIVE_GATE_SELECTION = [
    ('pending', 'Pending'),
    ('ready', 'Ready'),
]

AI_RECOMMENDATION_CLASS_SELECTION = [
    ('standard', 'Standard'),
    ('additional_module', 'Modulo Adicional'),
    ('studio', 'Studio'),
    ('custom', 'Custom'),
]

PG_SCOPE_TRACK_SELECTION = [
    ('approved_scope', 'Approved Scope'),
    ('operational_backlog', 'Operational Backlog'),
    ('internal_note', 'Internal Note'),
]

PG_SCOPE_STATE_SELECTION = [
    ('proposed', 'Proposed'),
    ('validated', 'Validated'),
    ('deferred', 'Deferred'),
    ('excluded', 'Excluded'),
    ('dropped', 'Dropped'),
]


class ProjectTaskConsultiveDecision(models.Model):
    _name = 'project.task.consultive.decision'
    _description = 'Project Task Consultive Decision'
    _order = 'decided_at desc, id desc'

    task_id = fields.Many2one(
        'project.task',
        string='Task',
        required=True,
        ondelete='cascade',
        index=True,
    )
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        required=True,
        ondelete='cascade',
        index=True,
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
    )
    decided_at = fields.Datetime(
        string='Decided At',
        required=True,
        default=fields.Datetime.now,
        readonly=True,
    )
    decision_type = fields.Selection(
        AI_CONSULTIVE_DECISION_SELECTION,
        string='Decision Type',
        required=True,
        index=True,
    )
    gate_state = fields.Selection(
        AI_CONSULTIVE_GATE_SELECTION,
        string='Gate State',
    )
    recommendation_class = fields.Selection(
        AI_RECOMMENDATION_CLASS_SELECTION,
        string='Recommendation Class',
    )
    recommended_module = fields.Char(string='Recommended Odoo Module')
    scope_track = fields.Selection(
        PG_SCOPE_TRACK_SELECTION,
        string='Scope Track',
    )
    scope_state = fields.Selection(
        PG_SCOPE_STATE_SELECTION,
        string='Scope State',
    )
    decision_summary = fields.Char(string='Decision Summary', required=True)
    evidence_summary = fields.Text(string='Evidence Summary')
    gate_notes_snapshot = fields.Text(string='Consultive Gate Notes Snapshot')
    recommendation_justification_snapshot = fields.Text(string='Recommendation Justification Snapshot')
    standard_review_snapshot = fields.Text(string='Standard Review Snapshot')
    additional_module_review_snapshot = fields.Text(string='Additional Module Review Snapshot')
    studio_review_snapshot = fields.Text(string='Studio Review Snapshot')
    ai_repo_full_name = fields.Char(string='AI Repository')
    ai_target_branch = fields.Char(string='AI Target Branch')
    ai_history_id = fields.Many2one(
        'project.task.ai.history',
        string='AI History Entry',
        ondelete='set null',
    )
    source_reference = fields.Char(string='Source Reference')
