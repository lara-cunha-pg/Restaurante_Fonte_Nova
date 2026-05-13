import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import html2plaintext

from ..services.project_chatter_grounding_service import ProjectChatterGroundingService
from ..services.project_chatter_queue_service import ProjectChatterQueueService
from ..services.project_budget_sync_service import ProjectBudgetSyncService
from ..services.project_deliveries_sync_service import ProjectDeliveriesSyncService
from ..services.project_decisions_sync_service import ProjectDecisionsSyncService
from ..services.project_mirror_sync_service import ProjectMirrorSyncService
from ..services.project_mirror_migration_service import ProjectMirrorMigrationService
from ..services.project_plan_sync_service import ProjectPlanSyncService
from ..services.project_requirements_sync_service import ProjectRequirementsSyncService
from ..services.project_risks_sync_service import ProjectRisksSyncService
from ..services.project_scope_sync_service import ProjectScopeSyncService
from ..services.project_status_draft_service import ProjectStatusDraftService
from ..services.project_status_sync_service import ProjectStatusSyncService
from ..services.project_sync_quality_review_service import ProjectSyncQualityReviewService

_logger = logging.getLogger(__name__)


YES_NO_UNKNOWN_SELECTION = [
    ('yes', 'Yes'),
    ('no', 'No'),
    ('unknown', 'Unknown'),
]

ODOO_EDITION_SELECTION = [
    ('community', 'Community'),
    ('enterprise', 'Enterprise'),
    ('unknown', 'Unknown'),
]

ODOO_ENVIRONMENT_SELECTION = [
    ('saas', 'SaaS'),
    ('odoo_sh', 'Odoo.sh'),
    ('on_premise', 'On-Premise'),
    ('unknown', 'Unknown'),
]

PROJECT_PHASE_SELECTION = [
    ('discovery', 'Discovery'),
    ('fit_gap', 'Fit-Gap'),
    ('solution_design', 'Solution Design'),
    ('implementation', 'Implementation'),
    ('uat', 'UAT'),
    ('go_live', 'Go-Live'),
    ('hypercare', 'Hypercare'),
    ('support', 'Support'),
]

SCOPE_SYNC_MODE_SELECTION = [
    ('manual', 'Manual'),
    ('event_driven', 'Event Driven'),
]

SCOPE_SYNC_STATUS_SELECTION = [
    ('never', 'Never'),
    ('queued', 'Queued'),
    ('running', 'Running'),
    ('done', 'Done'),
    ('skipped', 'Skipped'),
    ('error', 'Error'),
]

STATUS_DRAFT_SOURCE_SELECTION = [
    ('deterministic', 'Deterministic'),
    ('llm_assisted', 'LLM Assisted'),
    ('llm_fallback_deterministic', 'LLM Fallback to Deterministic'),
]

PG_BUDGET_BASELINE_STATUS_SELECTION = [
    ('draft', 'Draft'),
    ('approved', 'Approved'),
    ('consuming', 'Consuming'),
    ('closed', 'Closed'),
]

PG_ONBOARDING_STATUS_SELECTION = [
    ('never', 'Never'),
    ('done', 'Done'),
    ('error', 'Error'),
]


class ProjectProject(models.Model):
    _inherit = 'project.project'

    pg_project_plan_milestone_ids = fields.One2many(
        'project.milestone',
        'project_id',
        string='Project Plan Milestones',
    )
    pg_repository_id = fields.Many2one('pg.ai.repository', string='PG Repository', copy=False)
    pg_repo_branch = fields.Char(string='PG Repo Branch', copy=False)
    pg_scope_sync_enabled = fields.Boolean(string='Scope Sync Enabled', copy=False)
    pg_status_sync_enabled = fields.Boolean(string='Status Sync Enabled', copy=False)
    pg_decisions_sync_enabled = fields.Boolean(string='Decisions Sync Enabled', copy=False)
    pg_risks_sync_enabled = fields.Boolean(string='Risks Sync Enabled', copy=False)
    pg_deliveries_sync_enabled = fields.Boolean(string='Deliveries Sync Enabled', copy=False)
    pg_requirements_sync_enabled = fields.Boolean(string='Requirements Sync Enabled', copy=False)
    pg_project_plan_sync_enabled = fields.Boolean(string='Project Plan Sync Enabled', copy=False)
    pg_budget_sync_enabled = fields.Boolean(string='Budget Sync Enabled', copy=False)
    pg_scope_sync_mode = fields.Selection(
        SCOPE_SYNC_MODE_SELECTION,
        string='Scope Sync Mode',
        required=True,
        default='event_driven',
        copy=False,
    )
    pg_scope_sync_last_status = fields.Selection(
        SCOPE_SYNC_STATUS_SELECTION,
        string='Last Scope Sync Status',
        default='never',
        readonly=True,
        copy=False,
    )
    pg_scope_sync_last_payload_hash = fields.Char(string='Last Scope Payload Hash', readonly=True, copy=False)
    pg_scope_sync_last_published_at = fields.Datetime(string='Last Scope Published At', readonly=True, copy=False)
    pg_scope_sync_last_message = fields.Text(string='Last Scope Sync Message', readonly=True, copy=False)
    pg_mirror_sync_last_status = fields.Selection(
        SCOPE_SYNC_STATUS_SELECTION,
        string='Last Mirror Sync Status',
        default='never',
        readonly=True,
        copy=False,
    )
    pg_mirror_sync_last_payload_hash = fields.Char(string='Last Mirror Payload Hash', readonly=True, copy=False)
    pg_mirror_sync_last_published_at = fields.Datetime(string='Last Mirror Published At', readonly=True, copy=False)
    pg_mirror_sync_last_message = fields.Text(string='Last Mirror Sync Message', readonly=True, copy=False)
    pg_mirror_sync_quality_review_status = fields.Selection(
        [
            ('ok', 'OK'),
            ('warning', 'Warning'),
            ('blocking', 'Blocking'),
        ],
        string='Mirror Quality Review Status',
        readonly=True,
        copy=False,
    )
    pg_mirror_sync_quality_review_feedback = fields.Text(
        string='Mirror Quality Review Feedback',
        readonly=True,
        copy=False,
    )
    pg_mirror_sync_quality_warning_count = fields.Integer(
        string='Mirror Quality Warning Count',
        readonly=True,
        copy=False,
    )
    pg_mirror_sync_quality_blocking_count = fields.Integer(
        string='Mirror Quality Blocking Count',
        readonly=True,
        copy=False,
    )
    pg_mirror_included_scope_count = fields.Integer(
        string='Mirror Included Scope Count',
        readonly=True,
        copy=False,
    )
    pg_mirror_scope_backlog_count = fields.Integer(
        string='Mirror Factual Scope Backlog Count',
        readonly=True,
        copy=False,
    )
    pg_mirror_scope_backlog_reason_summary = fields.Char(
        string='Mirror Factual Scope Backlog Reasons',
        readonly=True,
        copy=False,
    )
    pg_mirror_scope_backlog_feedback = fields.Text(
        string='Mirror Factual Scope Backlog Feedback',
        readonly=True,
        copy=False,
    )
    pg_mirror_excluded_noise_count = fields.Integer(
        string='Mirror Excluded Noise Count',
        readonly=True,
        copy=False,
    )
    pg_mirror_excluded_noise_reason_summary = fields.Char(
        string='Mirror Excluded Noise Reasons',
        readonly=True,
        copy=False,
    )
    pg_mirror_excluded_noise_feedback = fields.Text(
        string='Mirror Excluded Noise Feedback',
        readonly=True,
        copy=False,
    )
    pg_mirror_scope_signal_feedback = fields.Text(
        string='Mirror Scope Signal Feedback',
        readonly=True,
        copy=False,
    )
    pg_mirror_operational_eligibility_status = fields.Selection(
        [
            ('eligible', 'Eligible'),
            ('eligible_with_warnings', 'Eligible With Warnings'),
            ('not_eligible', 'Not Eligible'),
        ],
        string='Mirror Operational Eligibility',
        compute='_compute_pg_mirror_operational_eligibility',
        readonly=True,
    )
    pg_mirror_operational_eligibility_warning_count = fields.Integer(
        string='Mirror Operational Eligibility Warning Count',
        compute='_compute_pg_mirror_operational_eligibility',
        readonly=True,
    )
    pg_mirror_operational_eligibility_not_eligible_count = fields.Integer(
        string='Mirror Operational Not Eligible Count',
        compute='_compute_pg_mirror_operational_eligibility',
        readonly=True,
    )
    pg_mirror_operational_eligibility_feedback = fields.Text(
        string='Mirror Operational Eligibility Feedback',
        compute='_compute_pg_mirror_operational_eligibility',
        readonly=True,
    )
    pg_scope_sync_quality_review_feedback = fields.Text(
        string='Scope Quality Review Feedback',
        readonly=True,
        copy=False,
    )
    pg_status_sync_last_status = fields.Selection(
        SCOPE_SYNC_STATUS_SELECTION,
        string='Last Status Sync Status',
        default='never',
        readonly=True,
        copy=False,
    )
    pg_status_sync_last_payload_hash = fields.Char(string='Last Status Sync Payload Hash', readonly=True, copy=False)
    pg_status_sync_last_published_at = fields.Datetime(string='Last Status Published At', readonly=True, copy=False)
    pg_status_sync_last_message = fields.Text(string='Last Status Sync Message', readonly=True, copy=False)
    pg_status_sync_needs_publish = fields.Boolean(
        string='Status Sync Needs Publish',
        default=False,
        readonly=True,
        copy=False,
    )
    pg_status_sync_review_feedback = fields.Text(
        string='Status Sync Review Feedback',
        compute='_compute_pg_status_sync_review_feedback',
    )
    pg_status_sync_quality_review_feedback = fields.Text(
        string='Status Quality Review Feedback',
        readonly=True,
        copy=False,
    )
    pg_decisions_sync_last_status = fields.Selection(
        SCOPE_SYNC_STATUS_SELECTION,
        string='Last Decisions Sync Status',
        default='never',
        readonly=True,
        copy=False,
    )
    pg_decisions_sync_last_payload_hash = fields.Char(string='Last Decisions Payload Hash', readonly=True, copy=False)
    pg_decisions_sync_last_published_at = fields.Datetime(string='Last Decisions Published At', readonly=True, copy=False)
    pg_decisions_sync_last_message = fields.Text(string='Last Decisions Sync Message', readonly=True, copy=False)
    pg_decisions_sync_quality_review_feedback = fields.Text(
        string='Decisions Quality Review Feedback',
        readonly=True,
        copy=False,
    )
    pg_risks_sync_last_status = fields.Selection(
        SCOPE_SYNC_STATUS_SELECTION,
        string='Last Risks Sync Status',
        default='never',
        readonly=True,
        copy=False,
    )
    pg_risks_sync_last_payload_hash = fields.Char(string='Last Risks Payload Hash', readonly=True, copy=False)
    pg_risks_sync_last_published_at = fields.Datetime(string='Last Risks Published At', readonly=True, copy=False)
    pg_risks_sync_last_message = fields.Text(string='Last Risks Sync Message', readonly=True, copy=False)
    pg_risks_sync_quality_review_feedback = fields.Text(
        string='Risks Quality Review Feedback',
        readonly=True,
        copy=False,
    )
    pg_deliveries_sync_last_status = fields.Selection(
        SCOPE_SYNC_STATUS_SELECTION,
        string='Last Deliveries Sync Status',
        default='never',
        readonly=True,
        copy=False,
    )
    pg_deliveries_sync_last_payload_hash = fields.Char(
        string='Last Deliveries Payload Hash',
        readonly=True,
        copy=False,
    )
    pg_deliveries_sync_last_published_at = fields.Datetime(
        string='Last Deliveries Published At',
        readonly=True,
        copy=False,
    )
    pg_deliveries_sync_last_message = fields.Text(string='Last Deliveries Sync Message', readonly=True, copy=False)
    pg_deliveries_sync_quality_review_feedback = fields.Text(
        string='Deliveries Quality Review Feedback',
        readonly=True,
        copy=False,
    )
    pg_requirements_sync_last_status = fields.Selection(
        SCOPE_SYNC_STATUS_SELECTION,
        string='Last Requirements Sync Status',
        default='never',
        readonly=True,
        copy=False,
    )
    pg_requirements_sync_last_payload_hash = fields.Char(
        string='Last Requirements Payload Hash',
        readonly=True,
        copy=False,
    )
    pg_requirements_sync_last_published_at = fields.Datetime(
        string='Last Requirements Published At',
        readonly=True,
        copy=False,
    )
    pg_requirements_sync_last_message = fields.Text(
        string='Last Requirements Sync Message',
        readonly=True,
        copy=False,
    )
    pg_requirements_sync_quality_review_feedback = fields.Text(
        string='Requirements Quality Review Feedback',
        readonly=True,
        copy=False,
    )
    pg_project_plan_sync_last_status = fields.Selection(
        SCOPE_SYNC_STATUS_SELECTION,
        string='Last Project Plan Sync Status',
        default='never',
        readonly=True,
        copy=False,
    )
    pg_project_plan_sync_last_payload_hash = fields.Char(
        string='Last Project Plan Payload Hash',
        readonly=True,
        copy=False,
    )
    pg_project_plan_sync_last_published_at = fields.Datetime(
        string='Last Project Plan Published At',
        readonly=True,
        copy=False,
    )
    pg_project_plan_sync_last_message = fields.Text(
        string='Last Project Plan Sync Message',
        readonly=True,
        copy=False,
    )
    pg_project_plan_sync_quality_review_feedback = fields.Text(
        string='Project Plan Quality Review Feedback',
        readonly=True,
        copy=False,
    )
    pg_budget_sync_last_status = fields.Selection(
        SCOPE_SYNC_STATUS_SELECTION,
        string='Last Budget Sync Status',
        default='never',
        readonly=True,
        copy=False,
    )
    pg_budget_sync_last_payload_hash = fields.Char(
        string='Last Budget Payload Hash',
        readonly=True,
        copy=False,
    )
    pg_budget_sync_last_published_at = fields.Datetime(
        string='Last Budget Published At',
        readonly=True,
        copy=False,
    )
    pg_budget_sync_last_message = fields.Text(
        string='Last Budget Sync Message',
        readonly=True,
        copy=False,
    )
    pg_budget_sync_quality_review_feedback = fields.Text(
        string='Budget Quality Review Feedback',
        readonly=True,
        copy=False,
    )
    pg_status_draft_generated_at = fields.Datetime(string='Status Draft Generated At', readonly=True, copy=False)
    pg_status_draft_generated_by_id = fields.Many2one(
        'res.users',
        string='Status Draft Generated By',
        readonly=True,
        copy=False,
    )
    pg_status_draft_summary = fields.Text(string='Status Draft Summary', readonly=True, copy=False)
    pg_status_draft_milestones_text = fields.Text(string='Status Draft Milestones', readonly=True, copy=False)
    pg_status_draft_blockers_text = fields.Text(string='Status Draft Blockers', readonly=True, copy=False)
    pg_status_draft_risks_text = fields.Text(string='Status Draft Risks', readonly=True, copy=False)
    pg_status_draft_next_steps_text = fields.Text(string='Status Draft Next Steps', readonly=True, copy=False)
    pg_status_draft_pending_decisions_text = fields.Text(
        string='Status Draft Pending Decisions',
        readonly=True,
        copy=False,
    )
    pg_status_draft_source = fields.Selection(
        STATUS_DRAFT_SOURCE_SELECTION,
        string='Status Draft Source',
        readonly=True,
        copy=False,
    )
    pg_status_draft_confidence = fields.Integer(
        string='Status Draft Confidence',
        readonly=True,
        copy=False,
    )
    pg_status_draft_quality_rationale = fields.Text(
        string='Status Draft Quality Rationale',
        readonly=True,
        copy=False,
    )
    pg_status_draft_feedback = fields.Text(
        string='Status Draft Feedback',
        compute='_compute_pg_status_draft_feedback',
    )
    pg_status_draft_signal_ids = fields.Many2many(
        'pg.project.chatter.signal',
        'pg_project_status_draft_signal_rel',
        'project_id',
        'signal_id',
        string='Status Draft Chatter Signals',
        copy=False,
        readonly=True,
    )
    pg_status_draft_signal_feedback = fields.Text(
        string='Status Draft Chatter Explainability',
        readonly=True,
        copy=False,
    )
    pg_scope_enrichment_last_run_at = fields.Datetime(
        string='Ultimo Draft Assistido em',
        readonly=True,
        copy=False,
    )
    pg_scope_enrichment_last_run_by_id = fields.Many2one(
        'res.users',
        string='Ultimo Draft Assistido por',
        readonly=True,
        copy=False,
    )
    pg_scope_enrichment_pending_count = fields.Integer(
        string='Drafts Assistidos Pendentes',
        compute='_compute_pg_scope_enrichment_counts',
    )
    pg_scope_enrichment_needs_review_count = fields.Integer(
        string='Candidatos por Rever',
        compute='_compute_pg_scope_enrichment_counts',
    )
    pg_scope_enrichment_applied_count = fields.Integer(
        string='Drafts Assistidos Aplicados',
        compute='_compute_pg_scope_enrichment_counts',
    )
    pg_scope_enrichment_feedback = fields.Text(
        string='Feedback Brownfield',
        compute='_compute_pg_scope_enrichment_feedback',
    )
    pg_chatter_signals_dirty = fields.Boolean(
        string='Chatter Signals Dirty',
        default=False,
        readonly=True,
        copy=False,
    )
    pg_chatter_last_scanned_at = fields.Datetime(
        string='Chatter Signals Last Scanned At',
        readonly=True,
        copy=False,
    )
    pg_chatter_signal_ids = fields.One2many(
        'pg.project.chatter.signal',
        'project_id',
        string='Chatter Signals',
        copy=False,
    )
    pg_chatter_signal_total_count = fields.Integer(
        string='Chatter Signal Count',
        compute='_compute_pg_chatter_signal_counts',
    )
    pg_chatter_signal_validated_count = fields.Integer(
        string='Validated Chatter Signals',
        compute='_compute_pg_chatter_signal_counts',
    )
    pg_chatter_signal_candidate_count = fields.Integer(
        string='Candidate Chatter Signals',
        compute='_compute_pg_chatter_signal_counts',
    )
    pg_chatter_signal_feedback = fields.Text(
        string='Chatter Signal Feedback',
        compute='_compute_pg_chatter_signal_feedback',
    )

    pg_client_unit = fields.Char(string='Client Unit')
    pg_repository_summary = fields.Text(string='Repository Summary')
    pg_project_phase = fields.Selection(PROJECT_PHASE_SELECTION, string='Project Phase')
    pg_odoo_version = fields.Char(string='Odoo Version')
    pg_odoo_edition = fields.Selection(ODOO_EDITION_SELECTION, string='Odoo Edition', default='unknown', required=True)
    pg_odoo_environment = fields.Selection(
        ODOO_ENVIRONMENT_SELECTION,
        string='Odoo Environment',
        default='unknown',
        required=True,
    )
    pg_standard_allowed = fields.Selection(
        YES_NO_UNKNOWN_SELECTION,
        string='Standard Allowed',
        default='unknown',
        required=True,
    )
    pg_additional_modules_allowed = fields.Selection(
        YES_NO_UNKNOWN_SELECTION,
        string='Additional Modules Allowed',
        default='unknown',
        required=True,
    )
    pg_studio_allowed = fields.Selection(
        YES_NO_UNKNOWN_SELECTION,
        string='Studio Allowed',
        default='unknown',
        required=True,
    )
    pg_custom_allowed = fields.Selection(
        YES_NO_UNKNOWN_SELECTION,
        string='Custom Allowed',
        default='unknown',
        required=True,
    )
    pg_additional_contract_restrictions = fields.Text(string='Additional Contract Restrictions')
    pg_business_goal = fields.Text(string='Business Goal')
    pg_current_request = fields.Text(string='Current Request')
    pg_current_process = fields.Text(string='Current Process')
    pg_problem_or_need = fields.Text(string='Problem Or Need')
    pg_business_impact = fields.Text(string='Business Impact')
    pg_onboarding_scope_included_text = fields.Text(string='Onboarding Scope Included')
    pg_onboarding_scope_excluded_text = fields.Text(string='Onboarding Scope Excluded')
    pg_onboarding_deliverables_text = fields.Text(string='Onboarding Deliverables')
    pg_onboarding_assumptions_text = fields.Text(string='Onboarding Assumptions')
    pg_onboarding_stakeholders_text = fields.Text(string='Onboarding Stakeholders')
    pg_onboarding_milestones_text = fields.Text(string='Onboarding Milestones')
    pg_onboarding_last_applied_at = fields.Datetime(
        string='Last Onboarding Applied At',
        readonly=True,
        copy=False,
    )
    pg_onboarding_last_status = fields.Selection(
        PG_ONBOARDING_STATUS_SELECTION,
        string='Last Onboarding Status',
        default='never',
        readonly=True,
        copy=False,
    )
    pg_onboarding_last_message = fields.Text(
        string='Last Onboarding Message',
        readonly=True,
        copy=False,
    )
    pg_mirror_migration_last_at = fields.Datetime(
        string='Last Mirror Migration At',
        readonly=True,
        copy=False,
    )
    pg_mirror_migration_last_status = fields.Selection(
        PG_ONBOARDING_STATUS_SELECTION,
        string='Last Mirror Migration Status',
        default='never',
        readonly=True,
        copy=False,
    )
    pg_mirror_migration_last_message = fields.Text(
        string='Last Mirror Migration Message',
        readonly=True,
        copy=False,
    )
    pg_mirror_migration_needed = fields.Boolean(
        string='Mirror Migration Needed',
        compute='_compute_pg_mirror_migration_needed',
    )
    pg_trigger = fields.Char(string='Trigger')
    pg_frequency = fields.Char(string='Frequency')
    pg_volumes = fields.Char(string='Volumes')
    pg_urgency = fields.Selection(
        [
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical'),
            ('unknown', 'Unknown'),
        ],
        string='Urgency',
        default='unknown',
        required=True,
    )
    pg_status_last_update_at = fields.Datetime(
        string='Status Last Updated At',
        default=fields.Datetime.now,
        copy=False,
        readonly=True,
    )
    pg_status_summary = fields.Text(string='Status Summary')
    pg_status_milestones_text = fields.Text(string='Status Milestones')
    pg_status_blockers_text = fields.Text(string='Blockers')
    pg_status_risks_text = fields.Text(string='Risks')
    pg_status_next_steps_text = fields.Text(string='Next Steps')
    pg_status_pending_decisions_text = fields.Text(string='Pending Decisions')
    pg_status_go_live_target = fields.Date(string='Go-Live Target')
    pg_status_owner_id = fields.Many2one('res.users', string='Status Owner')
    pg_budget_currency_id = fields.Many2one('res.currency', string='Budget Currency')
    pg_budget_owner_id = fields.Many2one('res.users', string='Budget Owner')
    pg_budget_baseline_status = fields.Selection(
        PG_BUDGET_BASELINE_STATUS_SELECTION,
        string='Budget Baseline Status',
    )
    pg_budget_materiality_threshold = fields.Monetary(
        string='Budget Materiality Threshold',
        currency_field='pg_budget_currency_id',
        copy=False,
    )
    pg_budget_line_ids = fields.One2many(
        'pg.project.budget.line',
        'project_id',
        string='PG Budget Lines',
        copy=False,
    )
    pg_risk_ids = fields.One2many('pg.project.risk', 'project_id', string='PG Risks', copy=False)

    pg_scope_line_ids = fields.One2many('pg.project.scope.line', 'project_id', string='PG Scope Lines', copy=False)
    pg_scope_sync_run_ids = fields.One2many('pg.project.scope.sync.run', 'project_id', string='PG Scope Sync Runs', copy=False)
    pg_scope_sync_run_count = fields.Integer(string='Scope Sync Runs', compute='_compute_pg_scope_sync_run_count')
    pg_mirror_sync_run_ids = fields.One2many(
        'pg.project.mirror.sync.run',
        'project_id',
        string='PG Mirror Sync Runs',
        copy=False,
    )
    pg_mirror_sync_run_count = fields.Integer(string='Mirror Sync Runs', compute='_compute_pg_mirror_sync_run_count')
    pg_status_sync_run_ids = fields.One2many(
        'pg.project.status.sync.run',
        'project_id',
        string='PG Status Sync Runs',
        copy=False,
    )
    pg_status_sync_run_count = fields.Integer(string='Status Sync Runs', compute='_compute_pg_status_sync_run_count')
    pg_decisions_sync_run_ids = fields.One2many(
        'pg.project.decisions.sync.run',
        'project_id',
        string='PG Decisions Sync Runs',
        copy=False,
    )
    pg_decisions_sync_run_count = fields.Integer(string='Decisions Sync Runs', compute='_compute_pg_decisions_sync_run_count')
    pg_risks_sync_run_ids = fields.One2many(
        'pg.project.risks.sync.run',
        'project_id',
        string='PG Risks Sync Runs',
        copy=False,
    )
    pg_risks_sync_run_count = fields.Integer(string='Risks Sync Runs', compute='_compute_pg_risks_sync_run_count')
    pg_deliveries_sync_run_ids = fields.One2many(
        'pg.project.deliveries.sync.run',
        'project_id',
        string='PG Deliveries Sync Runs',
        copy=False,
    )
    pg_deliveries_sync_run_count = fields.Integer(
        string='Deliveries Sync Runs',
        compute='_compute_pg_deliveries_sync_run_count',
    )
    pg_project_plan_sync_run_ids = fields.One2many(
        'pg.project.plan.sync.run',
        'project_id',
        string='PG Project Plan Sync Runs',
        copy=False,
    )
    pg_project_plan_sync_run_count = fields.Integer(
        string='Project Plan Sync Runs',
        compute='_compute_pg_project_plan_sync_run_count',
    )
    pg_requirements_sync_run_ids = fields.One2many(
        'pg.project.requirements.sync.run',
        'project_id',
        string='PG Requirements Sync Runs',
        copy=False,
    )
    pg_requirements_sync_run_count = fields.Integer(
        string='Requirements Sync Runs',
        compute='_compute_pg_requirements_sync_run_count',
    )
    pg_budget_sync_run_ids = fields.One2many(
        'pg.project.budget.sync.run',
        'project_id',
        string='PG Budget Sync Runs',
        copy=False,
    )
    pg_budget_sync_run_count = fields.Integer(
        string='Budget Sync Runs',
        compute='_compute_pg_budget_sync_run_count',
    )

    @api.depends('pg_scope_sync_run_ids')
    def _compute_pg_scope_sync_run_count(self):
        for project in self:
            project.pg_scope_sync_run_count = len(project.pg_scope_sync_run_ids)

    @api.depends('pg_mirror_sync_run_ids')
    def _compute_pg_mirror_sync_run_count(self):
        for project in self:
            project.pg_mirror_sync_run_count = len(project.pg_mirror_sync_run_ids)

    @api.depends(
        'pg_repository_id',
        'pg_repo_branch',
        'pg_onboarding_last_status',
        'pg_mirror_sync_run_ids',
    )
    def _compute_pg_mirror_migration_needed(self):
        migration_service = self._get_pg_mirror_migration_service()
        for project in self:
            project.pg_mirror_migration_needed = migration_service.project_needs_migration(project)

    @api.depends('pg_status_sync_run_ids')
    def _compute_pg_status_sync_run_count(self):
        for project in self:
            project.pg_status_sync_run_count = len(project.pg_status_sync_run_ids)

    @api.depends('pg_decisions_sync_run_ids')
    def _compute_pg_decisions_sync_run_count(self):
        for project in self:
            project.pg_decisions_sync_run_count = len(project.pg_decisions_sync_run_ids)

    @api.depends('pg_risks_sync_run_ids')
    def _compute_pg_risks_sync_run_count(self):
        for project in self:
            project.pg_risks_sync_run_count = len(project.pg_risks_sync_run_ids)

    @api.depends('pg_deliveries_sync_run_ids')
    def _compute_pg_deliveries_sync_run_count(self):
        for project in self:
            project.pg_deliveries_sync_run_count = len(project.pg_deliveries_sync_run_ids)

    @api.depends('pg_project_plan_sync_run_ids')
    def _compute_pg_project_plan_sync_run_count(self):
        for project in self:
            project.pg_project_plan_sync_run_count = len(project.pg_project_plan_sync_run_ids)

    @api.depends('pg_requirements_sync_run_ids')
    def _compute_pg_requirements_sync_run_count(self):
        for project in self:
            project.pg_requirements_sync_run_count = len(project.pg_requirements_sync_run_ids)

    @api.depends('pg_budget_sync_run_ids')
    def _compute_pg_budget_sync_run_count(self):
        for project in self:
            project.pg_budget_sync_run_count = len(project.pg_budget_sync_run_ids)

    @api.depends('pg_chatter_signal_ids', 'pg_chatter_signal_ids.signal_state', 'pg_chatter_signals_dirty')
    def _compute_pg_chatter_signal_counts(self):
        signal_model = self.env['pg.project.chatter.signal']
        for project in self:
            domain = [('project_id', '=', project.id)]
            project.pg_chatter_signal_total_count = signal_model.search_count(domain)
            project.pg_chatter_signal_validated_count = signal_model.search_count(
                domain + [('signal_state', '=', 'validated')]
            )
            project.pg_chatter_signal_candidate_count = signal_model.search_count(
                domain + [('signal_state', '=', 'candidate')]
            )

    @api.depends(
        'pg_chatter_signals_dirty',
        'pg_chatter_last_scanned_at',
        'pg_chatter_signal_total_count',
        'pg_chatter_signal_validated_count',
        'pg_chatter_signal_candidate_count',
    )
    def _compute_pg_chatter_signal_feedback(self):
        for project in self:
            if project.pg_chatter_signals_dirty:
                project.pg_chatter_signal_feedback = _(
                    "Chatter signals are stale and should be refreshed before using them in draft grounding."
                )
                continue
            if not project.pg_chatter_signal_total_count:
                project.pg_chatter_signal_feedback = _(
                    "No validated chatter signals were captured yet for this project."
                )
                continue
            project.pg_chatter_signal_feedback = _(
                "Signals captured: %(total)s total, %(validated)s validated, %(candidate)s candidate."
            ) % {
                'total': project.pg_chatter_signal_total_count,
                'validated': project.pg_chatter_signal_validated_count,
                'candidate': project.pg_chatter_signal_candidate_count,
            }

    @api.depends(
        'task_ids.pg_scope_relevant',
        'task_ids.pg_scope_track',
        'task_ids.pg_scope_state',
        'task_ids.pg_scope_enrichment_status',
    )
    def _compute_pg_scope_enrichment_counts(self):
        for project in self:
            relevant_tasks = project._pg_scope_enrichment_target_tasks()
            project.pg_scope_enrichment_pending_count = len(
                relevant_tasks.filtered(lambda task: task.pg_scope_enrichment_status in {'draft', 'needs_review'})
            )
            project.pg_scope_enrichment_needs_review_count = len(
                relevant_tasks.filtered(lambda task: task.pg_scope_enrichment_status == 'needs_review')
            )
            project.pg_scope_enrichment_applied_count = len(
                relevant_tasks.filtered(lambda task: task.pg_scope_enrichment_status == 'applied')
            )

    @api.depends(
        'pg_scope_enrichment_last_run_at',
        'pg_scope_enrichment_last_run_by_id',
        'pg_scope_enrichment_pending_count',
        'pg_scope_enrichment_needs_review_count',
        'pg_scope_enrichment_applied_count',
        'task_ids.pg_scope_relevant',
        'task_ids.pg_scope_track',
        'task_ids.pg_scope_state',
        'task_ids.pg_scope_enrichment_status',
        'task_ids.pg_scope_enrichment_generated_at',
        'task_ids.pg_scope_enrichment_generated_by_id',
    )
    def _compute_pg_scope_enrichment_feedback(self):
        for project in self:
            relevant_tasks = project._pg_scope_enrichment_target_tasks()
            generated_tasks = relevant_tasks.filtered(lambda task: task.pg_scope_enrichment_generated_at)
            latest_generated_task = generated_tasks.sorted(
                key=lambda task: task.pg_scope_enrichment_generated_at or fields.Datetime.from_string('1970-01-01 00:00:00'),
                reverse=True,
            )[:1]

            run_at_value = project.pg_scope_enrichment_last_run_at or latest_generated_task.pg_scope_enrichment_generated_at
            run_by = project.pg_scope_enrichment_last_run_by_id or latest_generated_task.pg_scope_enrichment_generated_by_id
            run_prefix = ""
            if run_at_value:
                run_prefix = _("Assisted drafts last generated at %s") % fields.Datetime.to_string(run_at_value)
                if run_by:
                    run_prefix = _("%s by %s") % (run_prefix, run_by.name)
                run_prefix += "."

            if not run_at_value and not (
                project.pg_scope_enrichment_pending_count
                or project.pg_scope_enrichment_needs_review_count
                or project.pg_scope_enrichment_applied_count
            ):
                project.pg_scope_enrichment_feedback = _(
                    "No assisted draft has been generated for this project yet."
                )
                continue

            if project.pg_scope_enrichment_pending_count:
                lines = []
                if run_prefix:
                    lines.append(run_prefix)
                else:
                    lines.append(_("Assisted drafts already exist on this project."))
                lines.append(_(
                    "Pending assisted drafts: %s, of which %s remain as review candidates."
                ) % (
                    project.pg_scope_enrichment_pending_count,
                    project.pg_scope_enrichment_needs_review_count,
                ))
                if project.pg_scope_enrichment_applied_count:
                    lines.append(_(
                        "Previously applied assisted drafts still visible in the official layer: %s."
                    ) % project.pg_scope_enrichment_applied_count)
                project.pg_scope_enrichment_feedback = ' '.join(lines)
                continue

            if run_prefix:
                project.pg_scope_enrichment_feedback = _(
                    "%s All current assisted drafts are either applied or absent."
                ) % run_prefix
            else:
                project.pg_scope_enrichment_feedback = _(
                    "No pending assisted drafts remain on this project."
                )

    @api.depends(
        'allow_milestones',
        'task_ids.active',
        'task_ids.pg_scope_relevant',
        'task_ids.pg_scope_track',
        'task_ids.pg_scope_state',
        'task_ids.name',
        'task_ids.description',
        'task_ids.pg_scope_summary',
        'task_ids.pg_acceptance_criteria_text',
        'task_ids.milestone_id',
        'task_ids.milestone_id.pg_plan_owner_id',
        'milestone_ids.active',
        'milestone_ids.pg_plan_status',
        'milestone_ids.pg_plan_owner_id',
    )
    def _pg_mirror_task_eligibility_review_safe(self, task):
        review_method = getattr(type(task), '_pg_mirror_task_eligibility_review', None)
        if callable(review_method):
            return review_method(task)

        findings = []
        if not task.active or not task.pg_scope_relevant or (task.pg_scope_track or 'approved_scope') != 'approved_scope':
            return {
                'applies': False,
                'status': 'eligible',
                'findings': [],
                'feedback': _(
                    "Task does not currently apply to mirror operational eligibility."
                ),
            }

        task_name = (task.name or '').strip()
        description = (html2plaintext(task.description or '') or '').strip()
        scope_summary = (task.pg_scope_summary or '').strip()
        if len(task_name.split()) <= 2:
            findings.append(
                {
                    'bucket': 'weak_name',
                    'message': _(
                        "Task name is too weak to support a robust mirror review."
                    ),
                    'evidence': task_name or '[empty]',
                }
            )
        if not description and not scope_summary:
            findings.append(
                {
                    'bucket': 'missing_description',
                    'message': _(
                        "Task still has no usable description or official scope summary."
                    ),
                    'evidence': task_name or '[empty]',
                }
            )
        if self.allow_milestones and task.milestone_id and not task.milestone_id.pg_plan_owner_id:
            findings.append(
                {
                    'bucket': 'milestone_owner_missing',
                    'message': _(
                        "Linked milestone still has no owner."
                    ),
                    'evidence': task.milestone_id.name or '[missing milestone name]',
                }
            )

        warning_buckets = {finding['bucket'] for finding in findings}
        status = 'eligible'
        if 'missing_description' in warning_buckets and 'weak_name' in warning_buckets:
            status = 'not_eligible'
        elif findings:
            status = 'eligible_with_warnings'

        feedback = _(
            "Mirror task eligibility fallback applied because the task review helper is unavailable in the current build."
        )
        return {
            'applies': True,
            'status': status,
            'findings': findings,
            'feedback': feedback,
        }

    def _compute_pg_mirror_operational_eligibility(self):
        for project in self:
            weak_name_count = 0
            missing_description_count = 0
            compound_item_count = 0
            task_not_eligible_count = 0

            for task in project._pg_scope_enrichment_target_tasks():
                review = project._pg_mirror_task_eligibility_review_safe(task)
                if not review.get('applies'):
                    continue
                buckets = {finding['bucket'] for finding in review.get('findings') or []}
                weak_name_count += int('weak_name' in buckets)
                missing_description_count += int('missing_description' in buckets)
                compound_item_count += int('compound_item' in buckets)
                task_not_eligible_count += int(review.get('status') == 'not_eligible')

            milestone_owner_gap_count = len(
                project.milestone_ids.filtered(
                    lambda milestone: milestone.active
                    and (milestone.pg_plan_status or 'planned') != 'completed'
                    and not milestone.pg_plan_owner_id
                )
            ) if project.allow_milestones else 0

            total_warning_count = (
                weak_name_count
                + missing_description_count
                + compound_item_count
                + milestone_owner_gap_count
            )

            if task_not_eligible_count:
                status = 'not_eligible'
            elif total_warning_count:
                status = 'eligible_with_warnings'
            else:
                status = 'eligible'

            if not total_warning_count:
                feedback = _(
                    "Operational mirror eligibility is currently clean for the official project layer."
                )
            else:
                lines = [
                    _(
                        "Operational mirror eligibility status: %(status)s."
                    ) % {'status': status},
                    _(
                        "Official tasks reviewed: %(tasks)s. Not eligible tasks: %(not_eligible)s. Warning signals: %(warnings)s."
                    ) % {
                        'tasks': len(project._pg_scope_enrichment_target_tasks()),
                        'not_eligible': task_not_eligible_count,
                        'warnings': total_warning_count,
                    },
                ]
                if weak_name_count:
                    lines.append(_("- Weak task names detected: %s.") % weak_name_count)
                if missing_description_count:
                    lines.append(_("- Tasks with missing description after hygiene: %s.") % missing_description_count)
                if compound_item_count:
                    lines.append(_("- Aggregate or contextual tasks still needing split/curation: %s.") % compound_item_count)
                if milestone_owner_gap_count:
                    lines.append(_("- Open milestones without owner: %s.") % milestone_owner_gap_count)
                feedback = '\n'.join(lines)

            project.pg_mirror_operational_eligibility_status = status
            project.pg_mirror_operational_eligibility_warning_count = total_warning_count
            project.pg_mirror_operational_eligibility_not_eligible_count = task_not_eligible_count
            project.pg_mirror_operational_eligibility_feedback = feedback

    @api.depends(
        'pg_status_sync_enabled',
        'pg_status_sync_needs_publish',
        'pg_status_sync_last_status',
        'pg_status_sync_last_published_at',
        'pg_status_last_update_at',
    )
    def _compute_pg_status_sync_review_feedback(self):
        for project in self:
            if not project.pg_status_sync_enabled:
                project.pg_status_sync_review_feedback = _(
                    "Status sync is disabled on this project."
                )
                continue

            if project.pg_status_sync_last_status == 'running':
                project.pg_status_sync_review_feedback = _(
                    "A manual status publication is currently running."
                )
                continue

            if project.pg_status_sync_last_status == 'queued':
                project.pg_status_sync_review_feedback = _(
                    "A manual status publication is queued and waiting to run."
                )
                continue

            if project.pg_status_sync_last_status == 'error':
                project.pg_status_sync_review_feedback = _(
                    "The last manual status publication failed. Review the message and publish again."
                )
                continue

            if project.pg_status_sync_needs_publish:
                if project.pg_status_sync_last_published_at:
                    updated_at = (
                        fields.Datetime.to_string(project.pg_status_last_update_at)
                        if project.pg_status_last_update_at
                        else _('Unknown')
                    )
                    published_at = fields.Datetime.to_string(project.pg_status_sync_last_published_at)
                    project.pg_status_sync_review_feedback = _(
                        "Operational status changed at %s after the last manual publication at %s. Review and publish a new status snapshot."
                    ) % (updated_at, published_at)
                else:
                    project.pg_status_sync_review_feedback = _(
                        "Operational status was edited but no manual status snapshot has been published yet."
                    )
                continue

            if project.pg_status_sync_last_published_at:
                published_at = fields.Datetime.to_string(project.pg_status_sync_last_published_at)
                project.pg_status_sync_review_feedback = _(
                    "Operational status is aligned with the last manual publication at %s."
                ) % published_at
                continue

            project.pg_status_sync_review_feedback = _(
                "Status sync is enabled but no manual publication has been performed yet."
            )

    @api.depends(
        'pg_status_draft_generated_at',
        'pg_status_last_update_at',
        'pg_chatter_signals_dirty',
        'pg_chatter_signal_validated_count',
        'pg_chatter_signal_candidate_count',
        'pg_status_summary',
        'pg_status_milestones_text',
        'pg_status_blockers_text',
        'pg_status_risks_text',
        'pg_status_next_steps_text',
        'pg_status_pending_decisions_text',
        'pg_status_draft_summary',
        'pg_status_draft_milestones_text',
        'pg_status_draft_blockers_text',
        'pg_status_draft_risks_text',
        'pg_status_draft_next_steps_text',
        'pg_status_draft_pending_decisions_text',
        'pg_status_draft_source',
        'pg_status_draft_confidence',
        'pg_status_draft_quality_rationale',
        'task_ids.pg_scope_relevant',
        'task_ids.pg_scope_track',
        'task_ids.pg_scope_state',
        'task_ids.pg_scope_kind',
        'task_ids.pg_scope_summary',
        'task_ids.pg_acceptance_criteria_text',
        'task_ids.pg_scope_enrichment_status',
    )
    def _compute_pg_status_draft_feedback(self):
        for project in self:
            source_lines = []
            if not project.pg_status_draft_generated_at:
                project.pg_status_draft_feedback = _(
                    "No auto-generated status draft is available yet."
                )
                continue

            if project.pg_status_draft_source == 'llm_assisted':
                line = _("LLM-assisted redraft generated")
                if project.pg_status_draft_confidence:
                    line += _(" with confidence %s%%") % project.pg_status_draft_confidence
                source_lines.append("%s." % line)
                if project.pg_status_draft_quality_rationale:
                    source_lines.append(_("LLM rationale: %s.") % project.pg_status_draft_quality_rationale.rstrip('.'))
            elif project.pg_status_draft_source == 'llm_fallback_deterministic':
                source_lines.append(_("LLM redraft was attempted, but the deterministic draft was kept."))
                if project.pg_status_draft_quality_rationale:
                    source_lines.append(_("LLM fallback reason: %s.") % project.pg_status_draft_quality_rationale.rstrip('.'))

            if project.pg_chatter_signals_dirty:
                source_lines.append(_(
                    "Validated chatter grounding is stale. Refresh project chatter signals before trusting this draft as evidence."
                ))
            elif project.pg_chatter_signal_candidate_count and not project.pg_chatter_signal_validated_count:
                source_lines.append(_(
                    "Only candidate chatter signals are currently available. They do not ground the official status until manually validated."
                ))

            if project._pg_status_draft_matches_official_status():
                source_lines.append(_(
                    "Draft already applied to the official status fields. Review and publish manually when ready. Manual publication still reads only the official status fields."
                ))
                project.pg_status_draft_feedback = '\n'.join(source_lines)
                continue

            if (
                project.pg_status_last_update_at
                and project.pg_status_draft_generated_at
                and project.pg_status_last_update_at > project.pg_status_draft_generated_at
            ):
                source_lines.append(_(
                    "Operational status fields changed after this draft was generated. Refresh the draft before applying or publishing. Manual publication still reads only the official status fields."
                ))
                project.pg_status_draft_feedback = '\n'.join(source_lines)
                continue

            missing_scope_fields_count = len(project._pg_scope_enrichment_tasks_missing_official_fields())
            needs_review_count = len(
                project._pg_scope_enrichment_target_tasks().filtered(
                    lambda task: task.pg_scope_enrichment_status == 'needs_review'
                )
            )
            operational_backlog_count = len(project._pg_operational_backlog_tasks())
            if missing_scope_fields_count or needs_review_count or operational_backlog_count:
                source_lines.append(_(
                    "Draft ready for review, but brownfield consolidation is still incomplete: %s official tasks still have consolidation gaps, %s assisted drafts remain in the review-candidate queue and %s backlog items still need classification."
                ) % (
                    missing_scope_fields_count,
                    needs_review_count,
                    operational_backlog_count,
                ))
                source_lines.append(_(
                    "Tasks, assisted drafts, backlog and chatter evidence do not feed the official status directly. Apply the curated draft to the official status fields only after review."
                ))
                project.pg_status_draft_feedback = '\n'.join(source_lines)
                continue

            source_lines.append(_(
                "Draft ready for review. Apply it to the official status fields before manual publication. Tasks, assisted drafts, backlog and chatter evidence stay outside the published status until then."
            ))
            project.pg_status_draft_feedback = '\n'.join(source_lines)

    def _pg_status_draft_matches_official_status(self):
        self.ensure_one()
        comparisons = (
            ('pg_status_summary', 'pg_status_draft_summary'),
            ('pg_status_milestones_text', 'pg_status_draft_milestones_text'),
            ('pg_status_blockers_text', 'pg_status_draft_blockers_text'),
            ('pg_status_risks_text', 'pg_status_draft_risks_text'),
            ('pg_status_next_steps_text', 'pg_status_draft_next_steps_text'),
            ('pg_status_pending_decisions_text', 'pg_status_draft_pending_decisions_text'),
        )
        has_draft_payload = False
        for official_field, draft_field in comparisons:
            official_value = ' '.join((getattr(self, official_field) or '').split()).strip()
            draft_value = ' '.join((getattr(self, draft_field) or '').split()).strip()
            has_draft_payload = has_draft_payload or bool(draft_value)
            if official_value != draft_value:
                return False
        return has_draft_payload

    def _get_pg_scope_sync_service(self):
        return ProjectScopeSyncService(self.env)

    def _get_pg_mirror_sync_service(self):
        return ProjectMirrorSyncService(self.env)

    def _get_pg_mirror_migration_service(self):
        return ProjectMirrorMigrationService(self.env)

    def _get_pg_status_draft_service(self):
        return ProjectStatusDraftService(self.env)

    def _get_pg_status_sync_service(self):
        return ProjectStatusSyncService(self.env)

    def _get_pg_decisions_sync_service(self):
        return ProjectDecisionsSyncService(self.env)

    def _get_pg_risks_sync_service(self):
        return ProjectRisksSyncService(self.env)

    def _get_pg_deliveries_sync_service(self):
        return ProjectDeliveriesSyncService(self.env)

    def _get_pg_project_plan_sync_service(self):
        return ProjectPlanSyncService(self.env)

    def _get_pg_requirements_sync_service(self):
        return ProjectRequirementsSyncService(self.env)

    def _get_pg_budget_sync_service(self):
        return ProjectBudgetSyncService(self.env)

    def _get_pg_sync_quality_review_service(self):
        return ProjectSyncQualityReviewService(self.env)

    def _get_pg_chatter_queue_service(self):
        return ProjectChatterQueueService(self.env)

    def _get_pg_chatter_grounding_service(self):
        return ProjectChatterGroundingService(self.env)

    def _pg_scope_enrichment_target_tasks(self):
        self.ensure_one()
        return self.task_ids.filtered(
            lambda task: task.active
            and task.pg_scope_relevant
            and (task.pg_scope_track or 'approved_scope') == 'approved_scope'
            and task.pg_scope_state not in {'excluded', 'dropped'}
        )

    def _is_pg_mirror_sync_enabled(self):
        self.ensure_one()
        return bool(
            self.pg_repository_id
            and (self.pg_repo_branch or '').strip()
            and (self.pg_scope_sync_enabled or self.pg_status_sync_enabled)
        )

    def _pg_mirror_sync_relevant_fields(self):
        return {
            'name',
            'partner_id',
            'user_id',
            'stage_id',
            'tag_ids',
            'date_start',
            'date',
            'allocated_hours',
            'progress',
            'allow_milestones',
            'pg_repository_id',
            'pg_repo_branch',
            'pg_scope_sync_enabled',
            'pg_status_sync_enabled',
            'pg_scope_sync_mode',
            'pg_client_unit',
            'pg_repository_summary',
            'pg_project_phase',
            'pg_business_goal',
            'pg_current_request',
            'pg_current_process',
            'pg_problem_or_need',
            'pg_business_impact',
            'pg_trigger',
            'pg_frequency',
            'pg_volumes',
            'pg_urgency',
            'pg_standard_allowed',
            'pg_additional_modules_allowed',
            'pg_studio_allowed',
            'pg_custom_allowed',
            'pg_additional_contract_restrictions',
            'pg_onboarding_scope_included_text',
            'pg_onboarding_scope_excluded_text',
            'pg_onboarding_deliverables_text',
            'pg_onboarding_assumptions_text',
            'pg_onboarding_stakeholders_text',
            'pg_onboarding_milestones_text',
            'pg_status_summary',
            'pg_status_milestones_text',
            'pg_status_blockers_text',
            'pg_status_risks_text',
            'pg_status_next_steps_text',
            'pg_status_pending_decisions_text',
            'pg_status_go_live_target',
        }

    def _pg_scope_enrichment_tasks_missing_official_fields(self):
        self.ensure_one()
        return self._pg_scope_enrichment_target_tasks().filtered(
            lambda task: not (task.pg_scope_kind or '').strip()
            or not (task.pg_scope_summary or '').strip()
            or not (task.pg_acceptance_criteria_text or '').strip()
        )

    def _pg_operational_backlog_tasks(self):
        self.ensure_one()
        return self.task_ids.filtered(
            lambda task: task.active
            and task.pg_scope_relevant
            and (task.pg_scope_track or 'approved_scope') == 'operational_backlog'
            and task.pg_scope_state not in {'excluded', 'dropped'}
        )

    def _pg_scope_sync_relevant_fields(self):
        return {
            'pg_repository_id',
            'pg_repo_branch',
            'pg_scope_sync_enabled',
            'pg_scope_sync_mode',
            'pg_client_unit',
            'pg_repository_summary',
            'pg_project_phase',
            'pg_odoo_version',
            'pg_odoo_edition',
            'pg_odoo_environment',
            'pg_standard_allowed',
            'pg_additional_modules_allowed',
            'pg_studio_allowed',
            'pg_custom_allowed',
            'pg_additional_contract_restrictions',
            'pg_business_goal',
            'pg_current_request',
            'pg_current_process',
            'pg_problem_or_need',
            'pg_business_impact',
            'pg_trigger',
            'pg_frequency',
            'pg_volumes',
            'pg_urgency',
        }

    def _pg_status_sync_relevant_fields(self):
        return {
            'pg_project_phase',
            'pg_status_summary',
            'pg_status_milestones_text',
            'pg_status_blockers_text',
            'pg_status_risks_text',
            'pg_status_next_steps_text',
            'pg_status_pending_decisions_text',
            'pg_status_go_live_target',
            'pg_status_owner_id',
        }

    def _pg_ai_consultive_gate_relevant_fields(self):
        return {
            'pg_project_phase',
            'pg_odoo_version',
            'pg_odoo_edition',
            'pg_odoo_environment',
            'pg_business_goal',
            'pg_current_request',
            'pg_current_process',
            'pg_problem_or_need',
            'pg_business_impact',
            'pg_trigger',
            'pg_frequency',
            'pg_volumes',
            'pg_urgency',
            'pg_standard_allowed',
            'pg_additional_modules_allowed',
            'pg_studio_allowed',
            'pg_custom_allowed',
            'pg_additional_contract_restrictions',
        }

    @api.constrains('pg_repo_branch', 'pg_odoo_environment')
    def _check_pg_repo_branch_not_main_on_odoo_sh(self):
        for project in self:
            if (
                project.pg_odoo_environment == 'odoo_sh'
                and (project.pg_repo_branch or '').strip().lower() == 'main'
            ):
                raise ValidationError(
                    _("A branch 'main' não pode ser utilizada em projetos com ambiente Odoo.sh. "
                      "Em Odoo.sh a branch 'main' é a branch de produção. "
                      "Configure uma branch de desenvolvimento (ex: dev, staging).")
                )

    @api.onchange('pg_repo_branch', 'pg_odoo_environment')
    def _onchange_pg_repo_branch_odoo_sh_warning(self):
        if (
            self.pg_odoo_environment == 'odoo_sh'
            and (self.pg_repo_branch or '').strip().lower() == 'main'
        ):
            return {
                'warning': {
                    'title': _("Branch 'main' não permitida em Odoo.sh"),
                    'message': _(
                        "Em Odoo.sh a branch 'main' corresponde ao ambiente de produção. "
                        "Utilize uma branch de desenvolvimento ou staging."
                    ),
                }
            }

    @api.constrains('pg_scope_sync_enabled', 'pg_repository_id', 'pg_repo_branch')
    def _check_pg_scope_sync_configuration(self):
        for project in self:
            if project.pg_scope_sync_enabled and (not project.pg_repository_id or not (project.pg_repo_branch or '').strip()):
                raise ValidationError(
                    _("Scope sync requires both a GitHub repository and a repository branch on the project.")
                )

    @api.constrains('pg_status_sync_enabled', 'pg_repository_id', 'pg_repo_branch')
    def _check_pg_status_sync_configuration(self):
        for project in self:
            if project.pg_status_sync_enabled and (not project.pg_repository_id or not (project.pg_repo_branch or '').strip()):
                raise ValidationError(
                    _("Status sync requires both a GitHub repository and a repository branch on the project.")
                )

    @api.constrains('pg_decisions_sync_enabled', 'pg_repository_id', 'pg_repo_branch')
    def _check_pg_decisions_sync_configuration(self):
        for project in self:
            if project.pg_decisions_sync_enabled and (not project.pg_repository_id or not (project.pg_repo_branch or '').strip()):
                raise ValidationError(
                    _("Decisions sync requires both a GitHub repository and a repository branch on the project.")
                )

    @api.constrains('pg_risks_sync_enabled', 'pg_repository_id', 'pg_repo_branch')
    def _check_pg_risks_sync_configuration(self):
        for project in self:
            if project.pg_risks_sync_enabled and (not project.pg_repository_id or not (project.pg_repo_branch or '').strip()):
                raise ValidationError(
                    _("Risks sync requires both a GitHub repository and a repository branch on the project.")
                )

    @api.constrains('pg_deliveries_sync_enabled', 'pg_repository_id', 'pg_repo_branch', 'allow_milestones')
    def _check_pg_deliveries_sync_configuration(self):
        for project in self:
            if project.pg_deliveries_sync_enabled and (not project.pg_repository_id or not (project.pg_repo_branch or '').strip()):
                raise ValidationError(
                    _("Deliveries sync requires both a GitHub repository and a repository branch on the project.")
                )
            if project.pg_deliveries_sync_enabled and not project.allow_milestones:
                raise ValidationError(
                    _("Deliveries sync requires milestones to be enabled on the project.")
                )

    @api.constrains('pg_requirements_sync_enabled', 'pg_repository_id', 'pg_repo_branch')
    def _check_pg_requirements_sync_configuration(self):
        for project in self:
            if project.pg_requirements_sync_enabled and (not project.pg_repository_id or not (project.pg_repo_branch or '').strip()):
                raise ValidationError(
                    _("Requirements sync requires both a GitHub repository and a repository branch on the project.")
                )

    @api.constrains('pg_project_plan_sync_enabled', 'pg_repository_id', 'pg_repo_branch', 'allow_milestones')
    def _check_pg_project_plan_sync_configuration(self):
        for project in self:
            if project.pg_project_plan_sync_enabled and (not project.pg_repository_id or not (project.pg_repo_branch or '').strip()):
                raise ValidationError(
                    _("Project plan sync requires both a GitHub repository and a repository branch on the project.")
                )
            if project.pg_project_plan_sync_enabled and not project.allow_milestones:
                raise ValidationError(
                    _("Project plan sync requires milestones to be enabled on the project.")
                )

    @api.constrains('pg_budget_sync_enabled', 'pg_repository_id', 'pg_repo_branch', 'pg_budget_currency_id')
    def _check_pg_budget_sync_configuration(self):
        for project in self:
            if project.pg_budget_sync_enabled and (not project.pg_repository_id or not (project.pg_repo_branch or '').strip()):
                raise ValidationError(
                    _("Budget sync requires both a GitHub repository and a repository branch on the project.")
                )
            if project.pg_budget_sync_enabled and not project.pg_budget_currency_id:
                raise ValidationError(
                    _("Budget sync requires a budget currency on the project.")
                )

    def action_publish_scope_to_repository(self):
        for project in self:
            run = project._get_pg_scope_sync_service().queue_project(
                project,
                trigger_type='manual',
                trigger_model='project.project',
                trigger_record_id=project.id,
            )
            if run and run.status == 'queued':
                project._get_pg_scope_sync_service().process_run(run)
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_open_pg_onboarding(self):
        self.ensure_one()
        action = self.env.ref('pg_brodoo.action_pg_ai_onboarding_wizard').sudo().read()[0]
        context = dict(self.env.context)
        context.update(
            {
                'active_model': 'project.project',
                'active_id': self.id,
                'default_project_id': self.id,
            }
        )
        action['context'] = context
        return action

    def action_sync_project_mirror_now(self):
        for project in self:
            run = project._get_pg_mirror_sync_service().queue_project(
                project,
                trigger_type='manual',
                trigger_model='project.project',
                trigger_record_id=project.id,
            )
            if run and run.status == 'queued':
                project._get_pg_mirror_sync_service().process_run(run)
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_migrate_legacy_project_mirror(self):
        for project in self:
            project._get_pg_mirror_migration_service().migrate_project(project, process_run=True)
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_rebuild_project_context(self):
        for project in self:
            run = project._get_pg_mirror_sync_service().queue_project(
                project,
                trigger_type='scheduled_rebuild',
                trigger_model='project.project',
                trigger_record_id=project.id,
            )
            if run and run.status == 'queued':
                project._get_pg_mirror_sync_service().process_run(run)
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_view_mirror_sync_runs(self):
        self.ensure_one()
        action = self.env.ref('pg_brodoo.action_pg_project_mirror_sync_run').sudo().read()[0]
        action['domain'] = [('project_id', '=', self.id)]
        action['context'] = {'default_project_id': self.id}
        return action

    def action_generate_scope_enrichment_drafts(self):
        for project in self:
            project._pg_scope_enrichment_target_tasks()._reset_existing_scope_enrichment_drafts()
            tasks = project._pg_scope_enrichment_tasks_missing_official_fields()
            if not tasks:
                raise ValidationError(
                    _("No approved scope tasks with missing official scope fields were found on this project.")
                )
            tasks.action_generate_scope_enrichment_draft()
            project._pg_scope_enrichment_target_tasks()._normalize_existing_scope_enrichment_fallbacks()
            project.with_context(pg_skip_status_sync_touch=True).write(
                {
                    'pg_scope_enrichment_last_run_at': fields.Datetime.now(),
                    'pg_scope_enrichment_last_run_by_id': self.env.user.id,
                }
            )
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_apply_scope_enrichment_drafts(self):
        scope_sync_service = self._get_pg_scope_sync_service()
        for project in self:
            tasks = project._pg_scope_enrichment_target_tasks().filtered(
                lambda task: task.pg_scope_enrichment_status == 'draft'
            )
            if not tasks:
                raise ValidationError(
                    _("No high-confidence scope enrichment drafts are ready to be applied on this project.")
                )

            applied_any = False
            for task in tasks:
                values, applied_fields = task._get_scope_enrichment_apply_values()
                if not values:
                    continue
                values.update(
                    {
                        'pg_scope_enrichment_status': 'applied',
                        'pg_scope_enrichment_feedback': _(
                            "Scope enrichment draft applied to: %s."
                        ) % ', '.join(applied_fields),
                    }
                )
                task.with_context(pg_skip_scope_sync_enqueue=True, pg_skip_scope_enrichment_reset=True).write(values)
                applied_any = True

            if not applied_any:
                raise ValidationError(
                    _("The available drafts could not be applied because the official scope fields are already filled.")
                )

            scope_sync_service.queue_project(
                project,
                trigger_type='project_write',
                trigger_model='project.project',
                trigger_record_id=project.id,
            )
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_view_scope_enrichment_tasks(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Scope Enrichment Tasks'),
            'res_model': 'project.task',
            'view_mode': 'list,form,kanban',
            'domain': [
                ('project_id', '=', self.id),
                ('active', '=', True),
                ('pg_scope_relevant', '=', True),
                ('pg_scope_track', '=', 'approved_scope'),
                ('pg_scope_state', 'not in', ['excluded', 'dropped']),
                ('pg_scope_enrichment_status', 'in', ['draft', 'needs_review']),
            ],
            'context': {'default_project_id': self.id},
        }

    def action_refresh_chatter_signals(self):
        for project in self:
            project._get_pg_chatter_queue_service().refresh_project(project)
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_view_chatter_signals(self):
        self.ensure_one()
        action = self.env.ref('pg_brodoo.action_pg_project_chatter_signal').read()[0]
        action['domain'] = [('project_id', '=', self.id)]
        action['context'] = {'default_project_id': self.id}
        return action

    def action_publish_status_to_repository(self):
        for project in self:
            run = project._get_pg_status_sync_service().queue_project(
                project,
                trigger_type='manual_button',
                trigger_model='project.project',
                trigger_record_id=project.id,
            )
            if run and run.status == 'queued':
                project._get_pg_status_sync_service().process_run(run)
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_publish_decisions_to_repository(self):
        for project in self:
            run = project._get_pg_decisions_sync_service().queue_project(
                project,
                trigger_type='manual_button',
                trigger_model='project.project',
                trigger_record_id=project.id,
            )
            if run and run.status == 'queued':
                project._get_pg_decisions_sync_service().process_run(run)
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_publish_risks_to_repository(self):
        for project in self:
            run = project._get_pg_risks_sync_service().queue_project(
                project,
                trigger_type='manual_button',
                trigger_model='project.project',
                trigger_record_id=project.id,
            )
            if run and run.status == 'queued':
                project._get_pg_risks_sync_service().process_run(run)
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_publish_deliveries_to_repository(self):
        for project in self:
            run = project._get_pg_deliveries_sync_service().queue_project(
                project,
                trigger_type='manual_button',
                trigger_model='project.project',
                trigger_record_id=project.id,
            )
            if run and run.status == 'queued':
                project._get_pg_deliveries_sync_service().process_run(run)
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_publish_requirements_to_repository(self):
        for project in self:
            run = project._get_pg_requirements_sync_service().queue_project(
                project,
                trigger_type='manual_button',
                trigger_model='project.project',
                trigger_record_id=project.id,
            )
            if run and run.status == 'queued':
                project._get_pg_requirements_sync_service().process_run(run)
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_publish_project_plan_to_repository(self):
        for project in self:
            run = project._get_pg_project_plan_sync_service().queue_project(
                project,
                trigger_type='manual_button',
                trigger_model='project.project',
                trigger_record_id=project.id,
            )
            if run and run.status == 'queued':
                project._get_pg_project_plan_sync_service().process_run(run)
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_publish_budget_to_repository(self):
        for project in self:
            run = project._get_pg_budget_sync_service().queue_project(
                project,
                trigger_type='manual_button',
                trigger_model='project.project',
                trigger_record_id=project.id,
            )
            if run and run.status == 'queued':
                project._get_pg_budget_sync_service().process_run(run)
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_generate_status_draft(self):
        for project in self:
            draft_values = project._get_pg_status_draft_service().build_draft_values(project)
            project.with_context(pg_skip_status_sync_touch=True).write(draft_values)
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_apply_status_draft(self):
        for project in self:
            if not project.pg_status_draft_generated_at:
                raise ValidationError(
                    _("Generate a status draft before applying it to the official status fields.")
                )
            project.write(
                {
                    'pg_status_summary': project.pg_status_draft_summary or False,
                    'pg_status_milestones_text': project.pg_status_draft_milestones_text or False,
                    'pg_status_blockers_text': project.pg_status_draft_blockers_text or False,
                    'pg_status_risks_text': project.pg_status_draft_risks_text or False,
                    'pg_status_next_steps_text': project.pg_status_draft_next_steps_text or False,
                    'pg_status_pending_decisions_text': project.pg_status_draft_pending_decisions_text or False,
                }
            )
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_view_scope_sync_runs(self):
        self.ensure_one()
        action = self.env.ref('pg_brodoo.action_pg_project_scope_sync_run').read()[0]
        action['domain'] = [('project_id', '=', self.id)]
        action['context'] = {'default_project_id': self.id}
        return action

    def action_view_status_sync_runs(self):
        self.ensure_one()
        action = self.env.ref('pg_brodoo.action_pg_project_status_sync_run').read()[0]
        action['domain'] = [('project_id', '=', self.id)]
        action['context'] = {'default_project_id': self.id}
        return action

    def action_view_decisions_sync_runs(self):
        self.ensure_one()
        action = self.env.ref('pg_brodoo.action_pg_project_decisions_sync_run').read()[0]
        action['domain'] = [('project_id', '=', self.id)]
        action['context'] = {'default_project_id': self.id}
        return action

    def action_view_risks_sync_runs(self):
        self.ensure_one()
        action = self.env.ref('pg_brodoo.action_pg_project_risks_sync_run').read()[0]
        action['domain'] = [('project_id', '=', self.id)]
        action['context'] = {'default_project_id': self.id}
        return action

    def action_view_deliveries_sync_runs(self):
        self.ensure_one()
        action = self.env.ref('pg_brodoo.action_pg_project_deliveries_sync_run').read()[0]
        action['domain'] = [('project_id', '=', self.id)]
        action['context'] = {'default_project_id': self.id}
        return action

    def action_view_requirements_sync_runs(self):
        self.ensure_one()
        action = self.env.ref('pg_brodoo.action_pg_project_requirements_sync_run').read()[0]
        action['domain'] = [('project_id', '=', self.id)]
        action['context'] = {'default_project_id': self.id}
        return action

    def action_view_project_plan_sync_runs(self):
        self.ensure_one()
        action = self.env.ref('pg_brodoo.action_pg_project_plan_sync_run').read()[0]
        action['domain'] = [('project_id', '=', self.id)]
        action['context'] = {'default_project_id': self.id}
        return action

    def action_view_budget_sync_runs(self):
        self.ensure_one()
        action = self.env.ref('pg_brodoo.action_pg_project_budget_sync_run').read()[0]
        action['domain'] = [('project_id', '=', self.id)]
        action['context'] = {'default_project_id': self.id}
        return action

    @api.model
    def _cron_refresh_pg_chatter_signals(self):
        processed = self._get_pg_chatter_queue_service().process_pending(limit=50)
        if getattr(self.env.registry, '_assertion_report', None) is None:
            self.env['ir.cron']._commit_progress(processed=processed, remaining=0)
        return processed

    def write(self, vals):
        ready_gate_tasks = self.env['project.task']
        should_enqueue_mirror = (
            not self.env.context.get('pg_skip_mirror_sync_enqueue')
            and bool(set(vals) & self._pg_mirror_sync_relevant_fields())
        )
        if (
            not self.env.context.get('pg_skip_status_sync_touch')
            and bool(set(vals) & self._pg_status_sync_relevant_fields())
            and 'pg_status_last_update_at' not in vals
        ):
            vals = dict(
                vals,
                pg_status_last_update_at=fields.Datetime.now(),
                pg_status_sync_needs_publish=True,
            )
        should_enqueue = (
            not self.env.context.get('pg_skip_scope_sync_enqueue')
            and bool(set(vals) & self._pg_scope_sync_relevant_fields())
        )
        should_reopen_gate = (
            not self.env.context.get('pg_skip_ai_consultive_gate_reset')
            and bool(set(vals) & self._pg_ai_consultive_gate_relevant_fields())
        )
        if should_reopen_gate:
            ready_gate_tasks = self.mapped('task_ids').filtered(lambda task: task.pg_ai_consultive_gate_state == 'ready')
        result = super().write(vals)
        if should_enqueue_mirror:
            for project in self:
                project._get_pg_mirror_sync_service().queue_project(
                    project,
                    trigger_type='project_write',
                    trigger_model='project.project',
                    trigger_record_id=project.id,
                )
        if should_enqueue:
            for project in self:
                project._get_pg_scope_sync_service().queue_project(
                    project,
                    trigger_type='project_write',
                    trigger_model='project.project',
                    trigger_record_id=project.id,
                )
        if should_reopen_gate:
            ready_gate_tasks._reopen_pg_ai_consultive_gate()
        return result
