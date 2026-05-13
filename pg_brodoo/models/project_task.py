import re
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import html2plaintext

from ..services.ai_orchestrator import AiOrchestrator
from ..services.github_service import GitHubService
from ..services.project_chatter_grounding_service import ProjectChatterGroundingService
from ..services.project_chatter_queue_service import ProjectChatterQueueService
from ..services.project_scope_enrichment_llm_service import ProjectScopeEnrichmentLlmService
from ..services.project_scope_enrichment_service import ProjectScopeEnrichmentService
from ..services.project_scope_sync_service import ProjectScopeSyncService
from ..services.project_task_consultive_prefill_service import ProjectTaskConsultivePrefillService
from ..services.text_hygiene import is_low_signal_scope_summary
from ..services.text_hygiene import normalize_inline_text
from ..services.text_hygiene import sanitize_plaintext
from ..services.text_hygiene import split_unique_text_lines

_logger = logging.getLogger(__name__)

DEFAULT_AI_CONTEXT_HISTORY_LIMIT = 8
DEFAULT_AI_CONTEXT_EXCERPT_CHARS = 1000

AI_CONSULTIVE_GATE_SELECTION = [
    ('pending', 'Pending'),
    ('ready', 'Ready'),
]

AI_GUIDED_STEP_STATE_SELECTION = [
    ('pending', 'Pending'),
    ('ready', 'Ready'),
]

AI_CONSULTIVE_FLOW_STAGE_SELECTION = [
    ('discovery', 'Discovery'),
    ('fit_gap', 'Fit-Gap'),
    ('recommendation', 'Recommendation'),
    ('gate', 'Consultive Gate'),
    ('ready', 'Ready'),
]

AI_RECOMMENDATION_CLASS_SELECTION = [
    ('standard', 'Standard'),
    ('additional_module', 'Modulo Adicional'),
    ('studio', 'Studio'),
    ('custom', 'Custom'),
]

AI_CONSULTIVE_PREFILL_STATUS_SELECTION = [
    ('empty', 'Empty'),
    ('draft', 'Draft Ready'),
    ('needs_review', 'Needs Review'),
    ('applied', 'Applied'),
    ('dismissed', 'Dismissed'),
]

AI_CONSULTIVE_PREFILL_SOURCE_SELECTION = [
    ('rule_based', 'Rule-Based'),
]

PG_SCOPE_TRACK_SELECTION = [
    ('approved_scope', 'Oficial'),
    ('operational_backlog', 'Backlog'),
    ('internal_note', 'Nota Interna'),
]

PG_SCOPE_KIND_SELECTION = [
    ('requirement', 'Requirement'),
    ('process', 'Process'),
    ('integration', 'Integration'),
    ('report', 'Report'),
    ('data', 'Data'),
    ('migration', 'Migration'),
    ('training', 'Training'),
    ('technical', 'Technical'),
]

PG_SCOPE_ENRICHMENT_STATUS_SELECTION = [
    ('empty', 'Sem Draft'),
    ('draft', 'Draft Assistido'),
    ('needs_review', 'Candidato por Rever'),
    ('applied', 'Aplicado'),
    ('dismissed', 'Descartado'),
]

PG_SCOPE_ENRICHMENT_SOURCE_SELECTION = [
    ('rule_based', 'Rule-Based'),
    ('llm_assisted', 'LLM Assisted'),
    ('llm_fallback_rule_based', 'LLM Fallback to Rule-Based'),
]

PG_REQUIREMENT_STATUS_SELECTION = [
    ('approved', 'Approved'),
    ('deferred', 'Deferred'),
]

PG_REQUIREMENT_PRIORITY_SELECTION = [
    ('low', 'Low'),
    ('medium', 'Medium'),
    ('high', 'High'),
    ('critical', 'Critical'),
]


class ProjectTask(models.Model):
    _inherit = 'project.task'

    ai_prompt_draft = fields.Text(string='Prompt AI Draft', copy=False)
    ai_prompt_final = fields.Text(string='Prompt AI Final', copy=False)
    ai_branch = fields.Char(string='Delivery Branch', copy=False)
    ai_repo_id = fields.Many2one('pg.ai.repository', string='AI Repository', copy=False)
    ai_base_branch_id = fields.Many2one(
        'pg.ai.repository.branch',
        string='GitHub Target Branch',
        copy=False,
        domain="[('repository_id', '=', ai_repo_id)]",
    )
    ai_status = fields.Selection(
        [
            ('draft', 'Rascunho'),
            ('queued', 'Em Fila'),
            ('running', 'Em Execucao'),
            ('done', 'Concluido'),
            ('error', 'Erro'),
        ],
        string='Estado AI',
        default='draft',
        tracking=True,
        copy=False,
    )
    ai_response = fields.Text(string='Resposta AI', copy=False)
    ai_progress_log = fields.Text(string='Timeline AI', copy=False)
    ai_commit_sha = fields.Char(string='Commit SHA', copy=False)
    ai_pr_url = fields.Char(string='Pull Request URL', copy=False)
    ai_error_message = fields.Text(string='Erro AI', copy=False)
    ai_history_ids = fields.One2many('project.task.ai.history', 'task_id', string='AI History', copy=False)
    ai_current_history_id = fields.Many2one('project.task.ai.history', string='Current AI Run', copy=False)
    pg_ai_consultive_decision_ids = fields.One2many(
        'project.task.consultive.decision',
        'task_id',
        string='Consultive Decision Trail',
        copy=False,
    )
    pg_ai_consultive_flow_stage = fields.Selection(
        AI_CONSULTIVE_FLOW_STAGE_SELECTION,
        string='Guided Consultive Flow',
        compute='_compute_pg_ai_consultive_flow_stage',
    )
    pg_ai_consultive_flow_feedback = fields.Text(
        string='Guided Consultive Flow Feedback',
        compute='_compute_pg_ai_consultive_flow_feedback',
    )
    pg_ai_discovery_step_state = fields.Selection(
        AI_GUIDED_STEP_STATE_SELECTION,
        string='Discovery Step',
        compute='_compute_pg_ai_consultive_step_states',
    )
    pg_ai_fit_gap_step_state = fields.Selection(
        AI_GUIDED_STEP_STATE_SELECTION,
        string='Fit-Gap Step',
        compute='_compute_pg_ai_consultive_step_states',
    )
    pg_ai_recommendation_step_state = fields.Selection(
        AI_GUIDED_STEP_STATE_SELECTION,
        string='Recommendation Step',
        compute='_compute_pg_ai_consultive_step_states',
    )
    pg_ai_gate_step_state = fields.Selection(
        AI_GUIDED_STEP_STATE_SELECTION,
        string='Gate Step',
        compute='_compute_pg_ai_consultive_step_states',
    )
    ai_context_summary = fields.Text(string='AI Context Memory', compute='_compute_ai_context_summary')
    pg_ai_consultive_gate_state = fields.Selection(
        AI_CONSULTIVE_GATE_SELECTION,
        string='Consultive Gate',
        default='pending',
        copy=False,
        tracking=True,
    )
    pg_ai_consultive_gate_notes = fields.Text(string='Consultive Gate Notes', copy=False)
    pg_ai_consultive_gate_checked_by_id = fields.Many2one(
        'res.users',
        string='Consultive Gate Checked By',
        copy=False,
        readonly=True,
    )
    pg_ai_consultive_gate_checked_at = fields.Datetime(
        string='Consultive Gate Checked At',
        copy=False,
        readonly=True,
    )
    pg_ai_consultive_gate_feedback = fields.Text(
        string='Consultive Gate Feedback',
        compute='_compute_pg_ai_consultive_gate_feedback',
    )
    pg_ai_recommendation_class = fields.Selection(
        AI_RECOMMENDATION_CLASS_SELECTION,
        string='Recommendation Class',
        copy=False,
        tracking=True,
    )
    pg_ai_recommended_module = fields.Char(string='Recommended Odoo Module', copy=False)
    pg_ai_standard_review = fields.Text(string='Standard Review', copy=False)
    pg_ai_additional_module_review = fields.Text(string='Additional Module Review', copy=False)
    pg_ai_studio_review = fields.Text(string='Studio Review', copy=False)
    pg_ai_recommendation_justification = fields.Text(string='Recommendation Justification', copy=False)
    pg_ai_recommendation_feedback = fields.Text(
        string='Recommendation Feedback',
        compute='_compute_pg_ai_recommendation_feedback',
    )
    pg_ai_recommendation_class_suggested = fields.Selection(
        AI_RECOMMENDATION_CLASS_SELECTION,
        string='Suggested Recommendation Class',
        copy=False,
        readonly=True,
    )
    pg_ai_recommended_module_suggested = fields.Char(
        string='Suggested Odoo Module',
        copy=False,
        readonly=True,
    )
    pg_ai_standard_review_suggested = fields.Text(
        string='Suggested Standard Review',
        copy=False,
        readonly=True,
    )
    pg_ai_additional_module_review_suggested = fields.Text(
        string='Suggested Additional Module Review',
        copy=False,
        readonly=True,
    )
    pg_ai_studio_review_suggested = fields.Text(
        string='Suggested Studio Review',
        copy=False,
        readonly=True,
    )
    pg_ai_recommendation_justification_suggested = fields.Text(
        string='Suggested Recommendation Justification',
        copy=False,
        readonly=True,
    )
    pg_ai_consultive_prefill_confidence = fields.Integer(
        string='Consultive Prefill Confidence',
        copy=False,
        readonly=True,
    )
    pg_ai_consultive_prefill_status = fields.Selection(
        AI_CONSULTIVE_PREFILL_STATUS_SELECTION,
        string='Consultive Prefill Draft',
        default='empty',
        copy=False,
        tracking=True,
    )
    pg_ai_consultive_prefill_source = fields.Selection(
        AI_CONSULTIVE_PREFILL_SOURCE_SELECTION,
        string='Consultive Prefill Source',
        copy=False,
        readonly=True,
    )
    pg_ai_consultive_prefill_generated_at = fields.Datetime(
        string='Consultive Prefill Generated At',
        copy=False,
        readonly=True,
    )
    pg_ai_consultive_prefill_generated_by_id = fields.Many2one(
        'res.users',
        string='Consultive Prefill Generated By',
        copy=False,
        readonly=True,
    )
    pg_ai_consultive_prefill_feedback = fields.Text(
        string='Consultive Prefill Feedback',
        copy=False,
        readonly=True,
    )
    pg_ai_consultive_prefill_signal_ids = fields.Many2many(
        'pg.project.chatter.signal',
        'pg_task_consultive_prefill_signal_rel',
        'task_id',
        'signal_id',
        string='Consultive Prefill Chatter Signals',
        copy=False,
        readonly=True,
    )
    pg_ai_consultive_prefill_signal_feedback = fields.Text(
        string='Consultive Prefill Chatter Explainability',
        copy=False,
        readonly=True,
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
        'task_id',
        string='Task Chatter Signals',
        copy=False,
    )
    pg_chatter_signal_total_count = fields.Integer(
        string='Task Chatter Signal Count',
        compute='_compute_pg_chatter_signal_counts',
    )
    pg_chatter_signal_validated_count = fields.Integer(
        string='Validated Task Chatter Signals',
        compute='_compute_pg_chatter_signal_counts',
    )
    pg_chatter_signal_candidate_count = fields.Integer(
        string='Candidate Task Chatter Signals',
        compute='_compute_pg_chatter_signal_counts',
    )
    pg_chatter_signal_feedback = fields.Text(
        string='Task Chatter Signal Feedback',
        compute='_compute_pg_chatter_signal_feedback',
    )
    pg_scope_track = fields.Selection(
        PG_SCOPE_TRACK_SELECTION,
        string='Camada Brownfield',
        required=True,
        default='approved_scope',
        copy=False,
        tracking=True,
    )
    pg_scope_relevant = fields.Boolean(string='Scope Relevant', default=True, copy=False)
    pg_scope_state = fields.Selection(
        [
            ('proposed', 'Proposed'),
            ('validated', 'Validated'),
            ('deferred', 'Deferred'),
            ('excluded', 'Excluded'),
            ('dropped', 'Dropped'),
        ],
        string='Scope State',
        required=True,
        default='proposed',
        copy=False,
    )
    pg_scope_kind = fields.Selection(
        PG_SCOPE_KIND_SELECTION,
        string='Scope Kind',
        copy=False,
    )
    pg_scope_summary = fields.Text(string='Scope Summary', copy=False)
    pg_acceptance_criteria_text = fields.Text(string='Acceptance Criteria', copy=False)
    pg_requirement_status = fields.Selection(
        PG_REQUIREMENT_STATUS_SELECTION,
        string='Requirement Status',
        copy=False,
    )
    pg_requirement_priority = fields.Selection(
        PG_REQUIREMENT_PRIORITY_SELECTION,
        string='Requirement Priority',
        copy=False,
    )
    pg_requirement_owner_id = fields.Many2one(
        'res.users',
        string='Requirement Owner',
        copy=False,
    )
    pg_requirement_traceability_refs = fields.Text(string='Requirement Traceability Refs', copy=False)
    pg_out_of_scope_reason = fields.Text(string='Out Of Scope Reason', copy=False)
    pg_scope_sequence = fields.Integer(string='Scope Sequence', default=10, copy=False)
    pg_scope_kind_suggested = fields.Selection(
        PG_SCOPE_KIND_SELECTION,
        string='Suggested Scope Kind',
        copy=False,
        readonly=True,
    )
    pg_scope_summary_suggested = fields.Text(string='Suggested Scope Summary', copy=False, readonly=True)
    pg_acceptance_criteria_suggested_text = fields.Text(
        string='Suggested Acceptance Criteria',
        copy=False,
        readonly=True,
    )
    pg_scope_enrichment_confidence = fields.Integer(
        string='Scope Enrichment Confidence',
        copy=False,
        readonly=True,
    )
    pg_scope_enrichment_status = fields.Selection(
        PG_SCOPE_ENRICHMENT_STATUS_SELECTION,
        string='Draft Assistido',
        default='empty',
        copy=False,
        tracking=True,
    )
    pg_scope_enrichment_source = fields.Selection(
        PG_SCOPE_ENRICHMENT_SOURCE_SELECTION,
        string='Origem do Draft Assistido',
        copy=False,
        readonly=True,
    )
    pg_scope_enrichment_generated_at = fields.Datetime(
        string='Scope Enrichment Generated At',
        copy=False,
        readonly=True,
    )
    pg_scope_enrichment_generated_by_id = fields.Many2one(
        'res.users',
        string='Scope Enrichment Generated By',
        copy=False,
        readonly=True,
    )
    pg_scope_enrichment_feedback = fields.Text(
        string='Scope Enrichment Feedback',
        copy=False,
        readonly=True,
    )
    pg_scope_curation_feedback = fields.Text(
        string='Scope Curation Feedback',
        compute='_compute_pg_scope_curation_feedback',
        store=True,
        readonly=True,
        copy=False,
    )
    pg_mirror_task_eligibility_status = fields.Selection(
        [
            ('eligible', 'Eligible'),
            ('eligible_with_warnings', 'Eligible With Warnings'),
            ('not_eligible', 'Not Eligible'),
        ],
        string='Mirror Task Eligibility',
        compute='_compute_pg_mirror_task_eligibility',
        readonly=True,
    )
    pg_mirror_task_eligibility_warning_count = fields.Integer(
        string='Mirror Task Eligibility Warning Count',
        compute='_compute_pg_mirror_task_eligibility',
        readonly=True,
    )
    pg_mirror_task_eligibility_feedback = fields.Text(
        string='Mirror Task Eligibility Feedback',
        compute='_compute_pg_mirror_task_eligibility',
        readonly=True,
    )
    pg_scope_enrichment_signal_ids = fields.Many2many(
        'pg.project.chatter.signal',
        'pg_task_scope_enrichment_signal_rel',
        'task_id',
        'signal_id',
        string='Scope Enrichment Chatter Signals',
        copy=False,
        readonly=True,
    )
    pg_scope_enrichment_signal_feedback = fields.Text(
        string='Scope Enrichment Chatter Explainability',
        copy=False,
        readonly=True,
    )

    def _ai_get_orchestrator(self):
        return AiOrchestrator(self.env)

    @api.depends('pg_chatter_signal_ids', 'pg_chatter_signal_ids.signal_state', 'pg_chatter_signals_dirty')
    def _compute_pg_chatter_signal_counts(self):
        signal_model = self.env['pg.project.chatter.signal']
        for task in self:
            domain = [('task_id', '=', task.id)]
            task.pg_chatter_signal_total_count = signal_model.search_count(domain)
            task.pg_chatter_signal_validated_count = signal_model.search_count(
                domain + [('signal_state', '=', 'validated')]
            )
            task.pg_chatter_signal_candidate_count = signal_model.search_count(
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
        for task in self:
            if task.pg_chatter_signals_dirty:
                task.pg_chatter_signal_feedback = _(
                    "Task chatter signals are stale and should be refreshed before grounding a draft from chatter."
                )
                continue
            if not task.pg_chatter_signal_total_count:
                task.pg_chatter_signal_feedback = _(
                    "No validated chatter signals were captured yet for this task."
                )
                continue
            task.pg_chatter_signal_feedback = _(
                "Task signals captured: %(total)s total, %(validated)s validated, %(candidate)s candidate."
            ) % {
                'total': task.pg_chatter_signal_total_count,
                'validated': task.pg_chatter_signal_validated_count,
                'candidate': task.pg_chatter_signal_candidate_count,
            }

    def _get_pg_scope_sync_service(self):
        return ProjectScopeSyncService(self.env)

    def _get_pg_chatter_queue_service(self):
        return ProjectChatterQueueService(self.env)

    def _get_pg_chatter_grounding_service(self):
        return ProjectChatterGroundingService(self.env)

    def _get_pg_scope_enrichment_service(self):
        return ProjectScopeEnrichmentService(self.env)

    def _get_pg_scope_enrichment_llm_service(self):
        return ProjectScopeEnrichmentLlmService(self.env)

    def _get_pg_ai_consultive_prefill_service(self):
        return ProjectTaskConsultivePrefillService(self.env)

    def _pg_scope_sync_relevant_fields(self):
        return {
            'name',
            'description',
            'project_id',
            'stage_id',
            'priority',
            'date_assign',
            'date_deadline',
            'allocated_hours',
            'effective_hours',
            'progress',
            'milestone_id',
            'parent_id',
            'tag_ids',
            'user_ids',
            'active',
            'pg_scope_relevant',
            'pg_scope_track',
            'pg_scope_state',
            'pg_scope_kind',
            'pg_scope_summary',
            'pg_acceptance_criteria_text',
            'pg_scope_sequence',
        }

    def _pg_scope_official_fields(self):
        return {
            'pg_scope_kind',
            'pg_scope_summary',
            'pg_acceptance_criteria_text',
        }

    @api.depends(
        'active',
        'pg_scope_relevant',
        'pg_scope_track',
        'pg_scope_state',
        'pg_scope_kind',
        'pg_scope_summary',
        'pg_acceptance_criteria_text',
        'pg_scope_enrichment_status',
        'pg_scope_enrichment_generated_at',
        'pg_scope_enrichment_source',
        'pg_scope_kind_suggested',
        'pg_scope_summary_suggested',
        'pg_acceptance_criteria_suggested_text',
        'pg_chatter_signals_dirty',
        'pg_chatter_signal_validated_count',
        'pg_chatter_signal_candidate_count',
    )
    def _compute_pg_scope_curation_feedback(self):
        field_labels = {
            'pg_scope_kind': _('Scope Kind'),
            'pg_scope_summary': _('Scope Summary'),
            'pg_acceptance_criteria_text': _('Acceptance Criteria'),
        }
        for task in self:
            lines = []
            if not task.active:
                task.pg_scope_curation_feedback = _(
                    "This task is archived. It does not participate in official scope curation or publication."
                )
                continue
            if not task.pg_scope_relevant:
                task.pg_scope_curation_feedback = _(
                    "This task is marked as not scope relevant. It stays outside the official scope curation path."
                )
                continue
            if (task.pg_scope_track or 'approved_scope') != 'approved_scope':
                task.pg_scope_curation_feedback = _(
                    "This task is currently outside the official layer. It stays in backlog or note mode until it is manually reclassified."
                )
                continue
            if task.pg_scope_state in {'excluded', 'dropped'}:
                task.pg_scope_curation_feedback = _(
                    "This task is marked as %(state)s and is excluded from official scope publication."
                ) % {'state': dict(task._fields['pg_scope_state'].selection).get(task.pg_scope_state, task.pg_scope_state)}
                continue
            if task.pg_scope_enrichment_status == 'empty':
                task.pg_scope_curation_feedback = _(
                    "No assisted draft is available yet. Only the official scope fields feed scope and requirement publications."
                )
                continue

            if task.pg_chatter_signals_dirty:
                lines.append(_(
                    "Validated chatter grounding is stale. Refresh chatter signals before trusting this draft as evidence."
                ))
            elif task.pg_chatter_signal_candidate_count and not task.pg_chatter_signal_validated_count:
                lines.append(_(
                    "Only candidate chatter signals exist for this task. They do not ground official scope until manually validated."
                ))

            if task.pg_scope_enrichment_status == 'needs_review':
                lines.append(_(
                    "This assisted draft still sits in the review-candidate queue. Project-level bulk apply ignores candidates that remain pending review."
                ))
            elif task.pg_scope_enrichment_status == 'applied':
                lines.append(_(
                    "This assisted draft was already applied. Only the official scope fields now feed publications."
                ))
                task.pg_scope_curation_feedback = '\n'.join(lines)
                continue
            elif task.pg_scope_enrichment_status == 'dismissed':
                lines.append(_(
                    "This assisted draft was dismissed and no longer participates in official scope curation."
                ))
                task.pg_scope_curation_feedback = '\n'.join(lines)
                continue

            missing_fields = []
            for field_name in task._pg_scope_official_fields():
                if getattr(task, field_name):
                    continue
                suggested_value = getattr(
                    task,
                    {
                        'pg_scope_kind': 'pg_scope_kind_suggested',
                        'pg_scope_summary': 'pg_scope_summary_suggested',
                        'pg_acceptance_criteria_text': 'pg_acceptance_criteria_suggested_text',
                    }[field_name],
                )
                if suggested_value:
                    missing_fields.append(field_labels[field_name])

            if missing_fields:
                lines.append(_(
                    "Apply will only fill consolidation gaps from this assisted draft: %s."
                ) % ', '.join(missing_fields))
            else:
                lines.append(_(
                    "The official scope fields are already filled. Applying this assisted draft would not change the official scope unless those fields are cleared manually first."
                ))

            lines.append(_(
                "Assisted drafts, raw chatter and backlog stay outside the official scope until a user explicitly applies curated values."
            ))
            task.pg_scope_curation_feedback = '\n'.join(lines)

    def _pg_is_in_official_mirror_scope(self):
        self.ensure_one()
        return bool(
            self.active
            and self.pg_scope_relevant
            and (self.pg_scope_track or 'approved_scope') == 'approved_scope'
            and self.pg_scope_state not in {'excluded', 'dropped'}
        )

    def _pg_mirror_task_eligibility_review(self):
        self.ensure_one()
        if not self._pg_is_in_official_mirror_scope():
            return {
                'applies': False,
                'status': 'eligible',
                'findings': [],
                'feedback': _(
                    "This task does not currently feed the official mirror path, so the minimum mirror eligibility checks do not apply."
                ),
            }

        enrichment_service = self._get_pg_scope_enrichment_service()
        findings = []

        normalized_name = normalize_inline_text(self.name, fallback='', max_chars=220, drop_placeholders=True)
        normalized_name_lower = normalized_name.lower()
        normalized_name_tokens = [
            token.strip()
            for token in re.split(r'[\W_]+', normalized_name_lower)
            if token.strip()
        ]
        if (
            not normalized_name
            or enrichment_service._name_is_generic(normalized_name)
            or is_low_signal_scope_summary(self.name, normalized_name)
            or (
                len(normalized_name_tokens) == 1
                and not any(
                    hint in normalized_name_lower
                    for hint in enrichment_service.OBJECTIVE_HINTS
                )
            )
        ):
            findings.append(
                {
                    'bucket': 'weak_name',
                    'message': _(
                        "Task name is still too weak or generic for mirror publication."
                    ),
                    'evidence': normalized_name or '[empty]',
                }
            )

        normalized_description = sanitize_plaintext(
            self.description,
            from_html=True,
            max_chars=1200,
            strip_email_noise=True,
        )
        if not normalized_description:
            findings.append(
                {
                    'bucket': 'missing_description',
                    'message': _(
                        "Task description is empty or collapses after hygiene filtering."
                    ),
                    'evidence': '[empty]',
                }
            )

        summary = normalize_inline_text(
            self.pg_scope_summary or normalized_description or self.name,
            fallback='',
            max_chars=220,
            drop_placeholders=True,
        )
        criteria_lines = split_unique_text_lines(
            self.pg_acceptance_criteria_text,
            max_items=6,
            max_line_chars=220,
        )
        quality_assessment = enrichment_service._assess_scope_draft_quality(self, summary, criteria_lines)
        if quality_assessment.get('force_review'):
            findings.append(
                {
                    'bucket': 'compound_item',
                    'message': _(
                        "Task still looks aggregate or contextual and should be split or curated before relying on it for the mirror."
                    ),
                    'evidence': (quality_assessment.get('flags') or ['[aggregate]'])[0],
                }
            )

        if self.milestone_id and not self.milestone_id.pg_plan_owner_id:
            findings.append(
                {
                    'bucket': 'milestone_owner_missing',
                    'message': _(
                        "Linked milestone still has no owner."
                    ),
                    'evidence': self.milestone_id.name or '[missing milestone name]',
                }
            )

        warning_buckets = {finding['bucket'] for finding in findings}
        status = 'eligible'
        if 'missing_description' in warning_buckets and (
            'weak_name' in warning_buckets or 'compound_item' in warning_buckets
        ):
            status = 'not_eligible'
        elif findings:
            status = 'eligible_with_warnings'

        if not findings:
            feedback = _(
                "Task is currently eligible for the mirror minimum contract."
            )
        else:
            lines = [
                _(
                    "Mirror task eligibility status: %(status)s. Warning signals: %(count)s."
                )
                % {'status': status, 'count': len(findings)}
            ]
            for finding in findings:
                lines.append(
                    "- %(bucket)s: %(message)s Evidence: %(evidence)s."
                    % {
                        'bucket': finding['bucket'],
                        'message': finding['message'],
                        'evidence': finding['evidence'],
                    }
                )
            feedback = '\n'.join(lines)

        return {
            'applies': True,
            'status': status,
            'findings': findings,
            'feedback': feedback,
        }

    @api.depends(
        'active',
        'pg_scope_relevant',
        'pg_scope_track',
        'pg_scope_state',
        'name',
        'description',
        'pg_scope_summary',
        'pg_acceptance_criteria_text',
        'milestone_id',
        'milestone_id.pg_plan_owner_id',
    )
    def _compute_pg_mirror_task_eligibility(self):
        for task in self:
            review = task._pg_mirror_task_eligibility_review()
            task.pg_mirror_task_eligibility_status = review['status']
            task.pg_mirror_task_eligibility_warning_count = len(review['findings'])
            task.pg_mirror_task_eligibility_feedback = review['feedback']

    def _pg_scope_enrichment_field_values(self, overrides=None):
        values = {
            'pg_scope_kind_suggested': False,
            'pg_scope_summary_suggested': False,
            'pg_acceptance_criteria_suggested_text': False,
            'pg_scope_enrichment_confidence': 0,
            'pg_scope_enrichment_status': 'empty',
            'pg_scope_enrichment_source': False,
            'pg_scope_enrichment_generated_at': False,
            'pg_scope_enrichment_generated_by_id': False,
            'pg_scope_enrichment_feedback': False,
            'pg_scope_enrichment_signal_ids': [(5, 0, 0)],
            'pg_scope_enrichment_signal_feedback': False,
        }
        if overrides:
            values.update(overrides)
        return values

    def _normalize_scope_enrichment_guard_text(self, value):
        return ' '.join((value or '').strip().lower().split())

    def _scope_enrichment_requires_manual_review(self, vals):
        source = vals.get('pg_scope_enrichment_source')
        status = vals.get('pg_scope_enrichment_status')
        if source != 'rule_based' or status != 'draft':
            return False

        summary = self._normalize_scope_enrichment_guard_text(vals.get('pg_scope_summary_suggested'))
        criteria = self._normalize_scope_enrichment_guard_text(vals.get('pg_acceptance_criteria_suggested_text'))
        name = ''
        description = ''
        if len(self) == 1:
            name = self._normalize_scope_enrichment_guard_text(self.name)
            description = self._normalize_scope_enrichment_guard_text(html2plaintext(self.description or ''))

        combined = ' '.join(part for part in (name, summary, criteria, description) if part)
        if not combined:
            return False

        if any(combined.startswith(prefix) for prefix in ProjectScopeEnrichmentService.EMAIL_GREETING_PREFIXES):
            return True
        if any(hint in combined for hint in ProjectScopeEnrichmentService.EMAIL_CONTEXT_HINTS):
            return True
        if any(hint in combined for hint in ProjectScopeEnrichmentService.EMAIL_SIGNOFF_HINTS):
            return True
        if name and any(hint in name for hint in ('email', 'seguimento', 'ponto situa')):
            return True
        return False

    def _normalize_scope_enrichment_state_values(self, vals):
        source = vals.get('pg_scope_enrichment_source')
        status = vals.get('pg_scope_enrichment_status')
        if source == 'llm_fallback_rule_based' and status != 'needs_review':
            vals = dict(vals)
            vals['pg_scope_enrichment_status'] = 'needs_review'
        elif self._scope_enrichment_requires_manual_review(vals):
            vals = dict(vals)
            feedback = vals.get('pg_scope_enrichment_feedback') or ''
            feedback_line = _(
                "O draft rule-based ainda parece email, follow-up ou contexto operacional e fica em revisao manual."
            )
            vals['pg_scope_enrichment_status'] = 'needs_review'
            if feedback_line not in feedback:
                vals['pg_scope_enrichment_feedback'] = ("%s\n%s" % (feedback, feedback_line)).strip()
        return vals

    def _normalize_existing_scope_enrichment_fallbacks(self):
        feedback_line = _(
            "O fallback rule-based continua em revisao manual e nao deve ser promovido automaticamente para draft ready."
        )
        stale_tasks = self.filtered(
            lambda task: task.pg_scope_enrichment_source == 'llm_fallback_rule_based'
            and (
                (task.pg_scope_enrichment_status or 'empty') != 'needs_review'
                or feedback_line not in (task.pg_scope_enrichment_feedback or '')
            )
        )
        for task in stale_tasks:
            feedback = task.pg_scope_enrichment_feedback or ''
            if feedback_line not in feedback:
                feedback = ("%s\n%s" % (feedback, feedback_line)).strip()
            task.with_context(
                pg_skip_scope_enrichment_reset=True,
                pg_skip_scope_sync_enqueue=True,
            ).write(
                {
                    'pg_scope_enrichment_status': 'needs_review',
                    'pg_scope_enrichment_feedback': feedback,
                }
            )
        return stale_tasks

    def _reset_existing_scope_enrichment_drafts(self):
        stale_tasks = self.filtered(
            lambda task: (task.pg_scope_enrichment_status or 'empty') in {'draft', 'needs_review', 'dismissed'}
        )
        if stale_tasks:
            stale_tasks.with_context(
                pg_skip_scope_enrichment_reset=True,
                pg_skip_scope_sync_enqueue=True,
            ).write(stale_tasks._pg_scope_enrichment_field_values())
        return stale_tasks

    def _pg_ai_consultive_prefill_official_fields(self):
        return {
            'pg_ai_recommendation_class',
            'pg_ai_recommended_module',
            'pg_ai_standard_review',
            'pg_ai_additional_module_review',
            'pg_ai_studio_review',
            'pg_ai_recommendation_justification',
        }

    def _pg_ai_consultive_prefill_field_values(self, overrides=None):
        values = {
            'pg_ai_recommendation_class_suggested': False,
            'pg_ai_recommended_module_suggested': False,
            'pg_ai_standard_review_suggested': False,
            'pg_ai_additional_module_review_suggested': False,
            'pg_ai_studio_review_suggested': False,
            'pg_ai_recommendation_justification_suggested': False,
            'pg_ai_consultive_prefill_confidence': 0,
            'pg_ai_consultive_prefill_status': 'empty',
            'pg_ai_consultive_prefill_source': False,
            'pg_ai_consultive_prefill_generated_at': False,
            'pg_ai_consultive_prefill_generated_by_id': False,
            'pg_ai_consultive_prefill_feedback': False,
            'pg_ai_consultive_prefill_signal_ids': [(5, 0, 0)],
            'pg_ai_consultive_prefill_signal_feedback': False,
        }
        if overrides:
            values.update(overrides)
        return values

    def _ensure_scope_enrichment_allowed(self):
        self.ensure_one()
        if not self.active:
            raise UserError(_("Reactivate the task before generating a scope enrichment draft."))
        if not self.pg_scope_relevant:
            raise UserError(_("Mark the task as Scope Relevant before generating a scope enrichment draft."))
        if (self.pg_scope_track or 'approved_scope') != 'approved_scope':
            raise UserError(_("Scope enrichment drafts are only available for tasks in Approved Scope."))
        if self.pg_scope_state in {'excluded', 'dropped'}:
            raise UserError(_("This task is currently outside the published scope and cannot generate a scope draft."))

    def _get_scope_enrichment_apply_values(self):
        self.ensure_one()

        values = {}
        applied_fields = []
        if not (self.pg_scope_kind or '').strip() and self.pg_scope_kind_suggested:
            values['pg_scope_kind'] = self.pg_scope_kind_suggested
            applied_fields.append(_('Scope Kind'))
        if not (self.pg_scope_summary or '').strip() and (self.pg_scope_summary_suggested or '').strip():
            values['pg_scope_summary'] = self.pg_scope_summary_suggested
            applied_fields.append(_('Scope Summary'))
        if not (self.pg_acceptance_criteria_text or '').strip() and (self.pg_acceptance_criteria_suggested_text or '').strip():
            values['pg_acceptance_criteria_text'] = self.pg_acceptance_criteria_suggested_text
            applied_fields.append(_('Acceptance Criteria'))
        return values, applied_fields

    def _get_pg_ai_consultive_prefill_apply_values(self):
        self.ensure_one()

        values = {}
        applied_fields = []
        suggested_class = self.pg_ai_recommendation_class_suggested or False
        final_class = self.pg_ai_recommendation_class or suggested_class

        if not self.pg_ai_recommendation_class and suggested_class:
            values['pg_ai_recommendation_class'] = suggested_class
            applied_fields.append(_('Recommendation Class'))

        if not (self.pg_ai_standard_review or '').strip() and (self.pg_ai_standard_review_suggested or '').strip():
            values['pg_ai_standard_review'] = self.pg_ai_standard_review_suggested
            applied_fields.append(_('Standard Review'))

        if (
            final_class in {'additional_module', 'studio', 'custom'}
            and not (self.pg_ai_additional_module_review or '').strip()
            and (self.pg_ai_additional_module_review_suggested or '').strip()
        ):
            values['pg_ai_additional_module_review'] = self.pg_ai_additional_module_review_suggested
            applied_fields.append(_('Additional Module Review'))

        if (
            final_class in {'studio', 'custom'}
            and not (self.pg_ai_studio_review or '').strip()
            and (self.pg_ai_studio_review_suggested or '').strip()
        ):
            values['pg_ai_studio_review'] = self.pg_ai_studio_review_suggested
            applied_fields.append(_('Studio Review'))

        if (
            final_class == 'additional_module'
            and not (self.pg_ai_recommended_module or '').strip()
            and (self.pg_ai_recommended_module_suggested or '').strip()
        ):
            values['pg_ai_recommended_module'] = self.pg_ai_recommended_module_suggested
            applied_fields.append(_('Recommended Odoo Module'))

        if (
            not (self.pg_ai_recommendation_justification or '').strip()
            and (self.pg_ai_recommendation_justification_suggested or '').strip()
        ):
            values['pg_ai_recommendation_justification'] = self.pg_ai_recommendation_justification_suggested
            applied_fields.append(_('Recommendation Justification'))

        return values, applied_fields

    def _pg_ai_consultive_gate_relevant_fields(self):
        return {
            'name',
            'description',
            'project_id',
            'pg_scope_relevant',
            'pg_scope_track',
            'pg_scope_state',
            'pg_scope_kind',
            'pg_scope_summary',
            'pg_acceptance_criteria_text',
            'pg_ai_recommendation_class',
            'pg_ai_recommended_module',
            'pg_ai_standard_review',
            'pg_ai_additional_module_review',
            'pg_ai_studio_review',
            'pg_ai_recommendation_justification',
        }

    def _queue_scope_sync_for_projects(self, projects, trigger_type):
        for project in projects.exists():
            self._get_pg_scope_sync_service().queue_project(
                project,
                trigger_type=trigger_type,
                trigger_model='project.task',
                trigger_record_id=self[:1].id if self else False,
            )

    def _queue_mirror_sync_for_projects(self, projects, trigger_type):
        for project in projects.exists():
            project._get_pg_mirror_sync_service().queue_project(
                project,
                trigger_type=trigger_type,
                trigger_model='project.task',
                trigger_record_id=self[:1].id if self else False,
            )

    def _get_boolean_param(self, key, default='True'):
        value = self.env['ir.config_parameter'].sudo().get_param(key, default)
        return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}

    def _get_positive_int_param(self, key, default):
        value = self.env['ir.config_parameter'].sudo().get_param(key, default)
        try:
            return max(int(value), 1)
        except (TypeError, ValueError):
            return default

    def _get_ai_context_history_limit(self):
        return self._get_positive_int_param('pg_ai_task_context_history_limit', DEFAULT_AI_CONTEXT_HISTORY_LIMIT)

    def _get_ai_context_excerpt_chars(self):
        return self._get_positive_int_param('pg_ai_task_context_excerpt_chars', DEFAULT_AI_CONTEXT_EXCERPT_CHARS)

    def _get_pg_ai_consultive_gate_missing_items(self, include_notes=False):
        self.ensure_one()

        missing = []
        project = self.project_id
        task_description = html2plaintext(self.description or '').strip()

        if not project:
            missing.append(_("Associate the task with a project."))
            return missing

        if not (self.name or '').strip():
            missing.append(_("Define a task name."))

        if not task_description and not (self.pg_scope_summary or '').strip() and not (self.pg_acceptance_criteria_text or '').strip():
            missing.append(_("Provide a functional description, scope summary or acceptance criteria on the task."))

        if not (project.pg_business_goal or '').strip():
            missing.append(_("Fill Project > PG Scope Sync > Business Goal."))

        if not (project.pg_current_request or '').strip():
            missing.append(_("Fill Project > PG Scope Sync > Current Request."))

        if not project.pg_project_phase:
            missing.append(_("Fill Project > PG Scope Sync > Project Phase."))

        if not (project.pg_odoo_version or '').strip():
            missing.append(_("Fill Project > PG Scope Sync > Odoo Version."))

        if not project.pg_odoo_edition or project.pg_odoo_edition == 'unknown':
            missing.append(_("Fill Project > PG Scope Sync > Odoo Edition."))

        if not project.pg_odoo_environment or project.pg_odoo_environment == 'unknown':
            missing.append(_("Fill Project > PG Scope Sync > Odoo Environment."))

        if include_notes and not (self.pg_ai_consultive_gate_notes or '').strip():
            missing.append(_("Fill Consultive Gate Notes on the task before marking the gate as ready."))

        missing.extend(self._get_pg_ai_recommendation_missing_items())
        return missing

    def _get_pg_ai_discovery_missing_items(self):
        self.ensure_one()

        missing = []
        project = self.project_id
        task_description = html2plaintext(self.description or '').strip()

        if not project:
            missing.append(_("Associate the task with a project."))
            return missing

        if not (self.name or '').strip():
            missing.append(_("Define a task name."))

        if not task_description and not (self.pg_scope_summary or '').strip() and not (self.pg_acceptance_criteria_text or '').strip():
            missing.append(_("Provide a functional description, scope summary or acceptance criteria on the task."))

        if not (project.pg_business_goal or '').strip():
            missing.append(_("Fill Project > PG Scope Sync > Business Goal."))

        if not (project.pg_current_request or '').strip():
            missing.append(_("Fill Project > PG Scope Sync > Current Request."))

        if not project.pg_project_phase:
            missing.append(_("Fill Project > PG Scope Sync > Project Phase."))

        if not (project.pg_odoo_version or '').strip():
            missing.append(_("Fill Project > PG Scope Sync > Odoo Version."))

        if not project.pg_odoo_edition or project.pg_odoo_edition == 'unknown':
            missing.append(_("Fill Project > PG Scope Sync > Odoo Edition."))

        if not project.pg_odoo_environment or project.pg_odoo_environment == 'unknown':
            missing.append(_("Fill Project > PG Scope Sync > Odoo Environment."))

        return missing

    def _get_pg_ai_fit_gap_missing_items(self):
        self.ensure_one()

        missing = []
        if self._get_pg_ai_discovery_missing_items():
            return missing

        if not (self.pg_ai_standard_review or '').strip():
            missing.append(_("Fill Standard Review on the task."))
        return missing

    def _get_pg_ai_consultive_flow_status(self):
        self.ensure_one()

        discovery_missing = self._get_pg_ai_discovery_missing_items()
        fit_gap_missing = self._get_pg_ai_fit_gap_missing_items()
        recommendation_missing = self._get_pg_ai_recommendation_missing_items()
        gate_missing = self._get_pg_ai_consultive_gate_missing_items(include_notes=True)

        discovery_ready = not discovery_missing
        fit_gap_ready = discovery_ready and not fit_gap_missing
        recommendation_ready = fit_gap_ready and not recommendation_missing
        gate_ready = self.pg_ai_consultive_gate_state == 'ready' and recommendation_ready and not gate_missing

        if gate_ready:
            stage = 'ready'
            current_missing = []
        elif recommendation_ready:
            stage = 'gate'
            current_missing = gate_missing or [_("Mark the consultive gate as ready on the task before continuing.")]
        elif fit_gap_ready:
            stage = 'recommendation'
            current_missing = recommendation_missing
        elif discovery_ready:
            stage = 'fit_gap'
            current_missing = fit_gap_missing
        else:
            stage = 'discovery'
            current_missing = discovery_missing

        return {
            'stage': stage,
            'discovery_ready': discovery_ready,
            'fit_gap_ready': fit_gap_ready,
            'recommendation_ready': recommendation_ready,
            'gate_ready': gate_ready,
            'current_missing': current_missing,
        }

    def _get_pg_ai_recommendation_class_label(self):
        self.ensure_one()
        return dict(AI_RECOMMENDATION_CLASS_SELECTION).get(
            self.pg_ai_recommendation_class or '',
            self.pg_ai_recommendation_class or '',
        )

    def _get_pg_ai_recommendation_missing_items(self):
        self.ensure_one()

        project = self.project_id
        recommendation_class = self.pg_ai_recommendation_class
        missing = []

        if not recommendation_class:
            missing.append(_("Select the final recommendation class on the task."))
            return missing

        if not (self.pg_ai_standard_review or '').strip():
            missing.append(_("Fill Standard Review on the task."))

        if recommendation_class in {'additional_module', 'studio', 'custom'}:
            if not (self.pg_ai_additional_module_review or '').strip():
                missing.append(_("Fill Additional Module Review on the task."))

        if recommendation_class in {'studio', 'custom'}:
            if not (self.pg_ai_studio_review or '').strip():
                missing.append(_("Fill Studio Review on the task."))

        if recommendation_class == 'additional_module' and not (self.pg_ai_recommended_module or '').strip():
            missing.append(_("Fill Recommended Odoo Module on the task."))

        if not (self.pg_ai_recommendation_justification or '').strip():
            missing.append(_("Fill Recommendation Justification on the task."))

        if not project:
            missing.append(_("Associate the task with a project before validating the final recommendation."))
            return missing

        project_restriction_map = {
            'standard': ('pg_standard_allowed', _("Project > PG Scope Sync > Standard Allowed")),
            'additional_module': (
                'pg_additional_modules_allowed',
                _("Project > PG Scope Sync > Additional Modules Allowed"),
            ),
            'studio': ('pg_studio_allowed', _("Project > PG Scope Sync > Studio Allowed")),
            'custom': ('pg_custom_allowed', _("Project > PG Scope Sync > Custom Allowed")),
        }
        restriction_field, restriction_label = project_restriction_map[recommendation_class]
        restriction_value = getattr(project, restriction_field)
        if restriction_value == 'unknown':
            missing.append(_("Confirm %s before using this recommendation class.") % restriction_label)
        elif restriction_value == 'no':
            missing.append(_("The project restrictions mark %s as not allowed.") % restriction_label)

        return missing

    def _build_pg_ai_consultive_gate_error(self, action_label, include_notes=False):
        self.ensure_one()

        missing = self._get_pg_ai_consultive_gate_missing_items(include_notes=include_notes)
        if not missing and self.pg_ai_consultive_gate_state != 'ready':
            missing.append(_("Mark the consultive gate as ready on the task before continuing."))

        lines = [
            _("Consultive gate not ready for %s.") % action_label,
            "",
            _("Complete the following before continuing:"),
        ]
        lines.extend("- %s" % item for item in missing)
        return '\n'.join(lines)

    def _ensure_pg_ai_consultive_gate_ready(self, action_label):
        self.ensure_one()
        if self.pg_ai_consultive_gate_state == 'ready':
            return True
        raise UserError(self._build_pg_ai_consultive_gate_error(action_label, include_notes=True))

    def _reopen_pg_ai_consultive_gate(self):
        tasks = self.filtered(lambda task: task.pg_ai_consultive_gate_state == 'ready')
        if not tasks:
            return

        tasks.with_context(pg_skip_ai_consultive_gate_reset=True).write(
            {
                'pg_ai_consultive_gate_state': 'pending',
                'pg_ai_consultive_gate_checked_by_id': False,
                'pg_ai_consultive_gate_checked_at': False,
            }
        )

    def _get_pg_ai_consultive_decision_type_label(self, decision_type):
        self.ensure_one()
        return dict(
            self.env['project.task.consultive.decision']._fields['decision_type'].selection
        ).get(decision_type or '', decision_type or '')

    def _get_pg_ai_consultive_decision_entries(self, limit=3):
        self.ensure_one()
        search_limit = limit if limit else None
        return self.env['project.task.consultive.decision'].search(
            [('task_id', '=', self.id)],
            order='decided_at desc, id desc',
            limit=search_limit,
        )

    def _format_pg_ai_consultive_decision_for_context(self, decision):
        self.ensure_one()
        timestamp = fields.Datetime.to_string(decision.decided_at or decision.create_date or fields.Datetime.now())
        decision_type_label = self._get_pg_ai_consultive_decision_type_label(decision.decision_type)
        user_name = decision.user_id.display_name or _('Unknown')
        lines = ["[%s] %s | %s" % (timestamp, decision_type_label, user_name)]
        if decision.recommendation_class:
            lines.append(
                _("Recommendation: %s")
                % dict(AI_RECOMMENDATION_CLASS_SELECTION).get(
                    decision.recommendation_class,
                    decision.recommendation_class,
                )
            )
        if decision.recommended_module:
            lines.append(_("Recommended Odoo module: %s") % decision.recommended_module)
        if decision.ai_target_branch:
            lines.append(_("AI target branch: %s") % decision.ai_target_branch)
        if decision.decision_summary:
            lines.append(_("Summary: %s") % self._clip_ai_context_text(decision.decision_summary))
        return '\n'.join(lines)

    def _build_pg_ai_consultive_decision_evidence_summary(self):
        self.ensure_one()
        project = self.project_id
        lines = []
        if project and project.pg_business_goal:
            lines.append(_("Business goal: %s") % self._clip_ai_context_text(project.pg_business_goal))
        if project and project.pg_current_request:
            lines.append(_("Current request: %s") % self._clip_ai_context_text(project.pg_current_request))
        if self.pg_scope_summary:
            lines.append(_("Scope summary: %s") % self._clip_ai_context_text(self.pg_scope_summary))
        if self.pg_acceptance_criteria_text:
            lines.append(_("Acceptance criteria: %s") % self._clip_ai_context_text(self.pg_acceptance_criteria_text))
        if self.pg_ai_consultive_gate_notes:
            lines.append(_("Consultive gate notes: %s") % self._clip_ai_context_text(self.pg_ai_consultive_gate_notes))
        if self.pg_ai_standard_review:
            lines.append(_("Standard review: %s") % self._clip_ai_context_text(self.pg_ai_standard_review))
        if self.pg_ai_additional_module_review:
            lines.append(
                _("Additional module review: %s")
                % self._clip_ai_context_text(self.pg_ai_additional_module_review)
            )
        if self.pg_ai_studio_review:
            lines.append(_("Studio review: %s") % self._clip_ai_context_text(self.pg_ai_studio_review))
        if self.pg_ai_recommendation_justification:
            lines.append(
                _("Recommendation justification: %s")
                % self._clip_ai_context_text(self.pg_ai_recommendation_justification)
            )
        return '\n'.join(lines).strip()

    def _build_pg_ai_consultive_decision_summary(self, decision_type):
        self.ensure_one()
        recommendation_label = self._get_pg_ai_recommendation_class_label() or _('Unclassified')
        if decision_type == 'gate_ready':
            return _("Consultive gate marked ready with final recommendation %s.") % recommendation_label
        if decision_type == 'prompt_generated':
            return _("AI prompt generated after consultive validation with recommendation %s.") % recommendation_label
        if decision_type == 'codex_queued':
            branch_name = self.ai_base_branch_id.name or self.ai_repo_id.default_branch or _('Unknown branch')
            return _("Codex execution requested for branch %s with recommendation %s.") % (
                branch_name,
                recommendation_label,
            )
        return _("Consultive decision captured for %s.") % recommendation_label

    def _capture_pg_ai_consultive_decision(self, decision_type, ai_history_entry=False):
        self.ensure_one()
        project = self.project_id
        if not project:
            return False

        history_entry = ai_history_entry.sudo().exists() if ai_history_entry else self.env['project.task.ai.history']
        return self.env['project.task.consultive.decision'].create(
            {
                'task_id': self.id,
                'project_id': project.id,
                'user_id': self.env.user.id,
                'decision_type': decision_type,
                'gate_state': self.pg_ai_consultive_gate_state or 'pending',
                'recommendation_class': self.pg_ai_recommendation_class,
                'recommended_module': self.pg_ai_recommended_module or False,
                'scope_track': self.pg_scope_track or 'approved_scope',
                'scope_state': self.pg_scope_state or False,
                'decision_summary': self._build_pg_ai_consultive_decision_summary(decision_type),
                'evidence_summary': self._build_pg_ai_consultive_decision_evidence_summary(),
                'gate_notes_snapshot': self.pg_ai_consultive_gate_notes or False,
                'recommendation_justification_snapshot': self.pg_ai_recommendation_justification or False,
                'standard_review_snapshot': self.pg_ai_standard_review or False,
                'additional_module_review_snapshot': self.pg_ai_additional_module_review or False,
                'studio_review_snapshot': self.pg_ai_studio_review or False,
                'ai_repo_full_name': self.ai_repo_id.full_name or False,
                'ai_target_branch': self.ai_base_branch_id.name or self.ai_repo_id.default_branch or False,
                'ai_history_id': history_entry.id if history_entry else False,
                'source_reference': f'project.task {self.id} - {self.name or ""}'.strip(),
            }
        )

    def _clip_ai_context_text(self, text, limit=None):
        normalized_text = ' '.join((text or '').split())
        excerpt_limit = limit or self._get_ai_context_excerpt_chars()
        if len(normalized_text) <= excerpt_limit:
            return normalized_text
        return normalized_text[:excerpt_limit].rstrip() + '...'

    def _get_ai_history_context_entries(self, limit=None, exclude_current_run=False):
        self.ensure_one()
        entries = self.ai_history_ids
        if exclude_current_run and self.ai_current_history_id:
            entries -= self.ai_current_history_id
        entries = entries.sorted(
            key=lambda entry: (
                entry.started_at or entry.create_date or fields.Datetime.now(),
                entry.id,
            )
        )
        history_limit = limit or self._get_ai_context_history_limit()
        if history_limit and len(entries) > history_limit:
            entries = entries[-history_limit:]
        return entries

    def _format_ai_history_entry_for_context(self, entry):
        entry_labels = {
            'prompt': _('Prompt'),
            'execution': _('Execution'),
        }
        status_labels = {
            'draft': _('Draft'),
            'queued': _('Queued'),
            'running': _('Running'),
            'done': _('Done'),
            'error': _('Error'),
        }
        timestamp = fields.Datetime.to_string(entry.started_at or entry.create_date or fields.Datetime.now())
        lines = [
            "[%s] %s | %s"
            % (
                timestamp,
                entry_labels.get(entry.entry_type, entry.entry_type or _('Unknown')),
                status_labels.get(entry.status, entry.status or _('Unknown')),
            )
        ]
        if entry.repo_full_name:
            lines.append(_("Repository: %s") % entry.repo_full_name)
        if entry.base_branch:
            lines.append(_("Target branch: %s") % entry.base_branch)
        if entry.branch_name:
            lines.append(_("Delivery branch: %s") % entry.branch_name)
        if entry.commit_sha:
            lines.append(_("Commit: %s") % entry.commit_sha)
        if entry.prompt_text:
            lines.append(_("Prompt: %s") % self._clip_ai_context_text(entry.prompt_text))
        if entry.summary_text:
            lines.append(_("Summary: %s") % self._clip_ai_context_text(entry.summary_text))
        elif entry.response_text:
            lines.append(_("Response: %s") % self._clip_ai_context_text(entry.response_text))
        if entry.error_message:
            lines.append(_("Error: %s") % self._clip_ai_context_text(entry.error_message))
        return '\n'.join(lines)

    def build_ai_continuity_context(self, limit=None, exclude_current_run=False):
        self.ensure_one()
        lines = []
        task_description = html2plaintext(self.description or '').strip()
        if task_description:
            lines.append(_("Functional description: %s") % self._clip_ai_context_text(task_description))
        if self.pg_ai_consultive_gate_notes:
            lines.append(_("Consultive gate notes: %s") % self._clip_ai_context_text(self.pg_ai_consultive_gate_notes))
        if self.pg_ai_recommendation_class:
            lines.append(_("Final recommendation class: %s") % self._get_pg_ai_recommendation_class_label())
        if self.pg_ai_recommended_module:
            lines.append(_("Recommended Odoo module: %s") % self.pg_ai_recommended_module)
        if self.pg_ai_standard_review:
            lines.append(_("Standard review: %s") % self._clip_ai_context_text(self.pg_ai_standard_review))
        if self.pg_ai_additional_module_review:
            lines.append(_("Additional module review: %s") % self._clip_ai_context_text(self.pg_ai_additional_module_review))
        if self.pg_ai_studio_review:
            lines.append(_("Studio review: %s") % self._clip_ai_context_text(self.pg_ai_studio_review))
        if self.pg_ai_recommendation_justification:
            lines.append(
                _("Recommendation justification: %s")
                % self._clip_ai_context_text(self.pg_ai_recommendation_justification)
            )
        if self.ai_repo_id:
            lines.append(_("Repository selected: %s") % (self.ai_repo_id.full_name or ''))
        if self.ai_base_branch_id:
            lines.append(_("Current target branch: %s") % (self.ai_base_branch_id.name or ''))
        if self.ai_branch:
            lines.append(_("Current delivery branch: %s") % self.ai_branch)
        if self.ai_commit_sha:
            lines.append(_("Latest AI commit: %s") % self.ai_commit_sha)

        history_entries = self._get_ai_history_context_entries(limit=limit, exclude_current_run=exclude_current_run)
        if history_entries:
            lines.append(_("Task AI history:"))
            for index, entry in enumerate(history_entries, start=1):
                lines.append("%s. %s" % (index, self._format_ai_history_entry_for_context(entry)))

        decision_entries = self._get_pg_ai_consultive_decision_entries(limit=3)
        if decision_entries:
            lines.append(_("Consultive decision trail:"))
            for index, decision in enumerate(decision_entries, start=1):
                lines.append("%s. %s" % (index, self._format_pg_ai_consultive_decision_for_context(decision)))
        return '\n\n'.join(filter(None, lines)).strip()

    @api.depends(
        'description',
        'pg_ai_consultive_gate_notes',
        'pg_ai_recommendation_class',
        'pg_ai_recommended_module',
        'pg_ai_standard_review',
        'pg_ai_additional_module_review',
        'pg_ai_studio_review',
        'pg_ai_recommendation_justification',
        'ai_repo_id.full_name',
        'ai_base_branch_id.name',
        'ai_branch',
        'ai_commit_sha',
        'ai_history_ids.entry_type',
        'ai_history_ids.status',
        'ai_history_ids.prompt_text',
        'ai_history_ids.response_text',
        'ai_history_ids.summary_text',
        'ai_history_ids.error_message',
        'ai_history_ids.branch_name',
        'ai_history_ids.base_branch',
        'ai_history_ids.commit_sha',
        'ai_history_ids.repo_full_name',
        'ai_history_ids.started_at',
        'ai_history_ids.create_date',
        'pg_ai_consultive_decision_ids.decision_type',
        'pg_ai_consultive_decision_ids.decision_summary',
        'pg_ai_consultive_decision_ids.recommendation_class',
        'pg_ai_consultive_decision_ids.recommended_module',
        'pg_ai_consultive_decision_ids.ai_target_branch',
        'pg_ai_consultive_decision_ids.user_id',
        'pg_ai_consultive_decision_ids.decided_at',
    )
    def _compute_ai_context_summary(self):
        for task in self:
            task.ai_context_summary = task.build_ai_continuity_context() if task.id else False

    @api.depends(
        'name',
        'description',
        'pg_scope_summary',
        'pg_acceptance_criteria_text',
        'pg_ai_consultive_gate_state',
        'pg_ai_consultive_gate_notes',
        'project_id',
        'project_id.pg_business_goal',
        'project_id.pg_current_request',
        'project_id.pg_project_phase',
        'project_id.pg_odoo_version',
        'project_id.pg_odoo_edition',
        'project_id.pg_odoo_environment',
        'project_id.pg_standard_allowed',
        'project_id.pg_additional_modules_allowed',
        'project_id.pg_studio_allowed',
        'project_id.pg_custom_allowed',
        'pg_ai_recommendation_class',
        'pg_ai_recommended_module',
        'pg_ai_standard_review',
        'pg_ai_additional_module_review',
        'pg_ai_studio_review',
        'pg_ai_recommendation_justification',
    )
    def _compute_pg_ai_consultive_flow_stage(self):
        for task in self:
            task.pg_ai_consultive_flow_stage = task._get_pg_ai_consultive_flow_status()['stage']

    @api.depends(
        'name',
        'description',
        'pg_scope_summary',
        'pg_acceptance_criteria_text',
        'pg_ai_consultive_gate_state',
        'pg_ai_consultive_gate_notes',
        'project_id',
        'project_id.pg_business_goal',
        'project_id.pg_current_request',
        'project_id.pg_project_phase',
        'project_id.pg_odoo_version',
        'project_id.pg_odoo_edition',
        'project_id.pg_odoo_environment',
        'project_id.pg_standard_allowed',
        'project_id.pg_additional_modules_allowed',
        'project_id.pg_studio_allowed',
        'project_id.pg_custom_allowed',
        'pg_ai_recommendation_class',
        'pg_ai_recommended_module',
        'pg_ai_standard_review',
        'pg_ai_additional_module_review',
        'pg_ai_studio_review',
        'pg_ai_recommendation_justification',
    )
    def _compute_pg_ai_consultive_step_states(self):
        for task in self:
            status = task._get_pg_ai_consultive_flow_status()
            task.pg_ai_discovery_step_state = 'ready' if status['discovery_ready'] else 'pending'
            task.pg_ai_fit_gap_step_state = 'ready' if status['fit_gap_ready'] else 'pending'
            task.pg_ai_recommendation_step_state = 'ready' if status['recommendation_ready'] else 'pending'
            task.pg_ai_gate_step_state = 'ready' if status['gate_ready'] else 'pending'

    @api.depends(
        'pg_ai_consultive_flow_stage',
        'name',
        'description',
        'pg_scope_summary',
        'pg_acceptance_criteria_text',
        'pg_ai_consultive_gate_state',
        'pg_ai_consultive_gate_notes',
        'project_id',
        'project_id.pg_business_goal',
        'project_id.pg_current_request',
        'project_id.pg_project_phase',
        'project_id.pg_odoo_version',
        'project_id.pg_odoo_edition',
        'project_id.pg_odoo_environment',
        'project_id.pg_standard_allowed',
        'project_id.pg_additional_modules_allowed',
        'project_id.pg_studio_allowed',
        'project_id.pg_custom_allowed',
        'pg_ai_recommendation_class',
        'pg_ai_recommended_module',
        'pg_ai_standard_review',
        'pg_ai_additional_module_review',
        'pg_ai_studio_review',
        'pg_ai_recommendation_justification',
    )
    def _compute_pg_ai_consultive_flow_feedback(self):
        stage_labels = dict(AI_CONSULTIVE_FLOW_STAGE_SELECTION)
        for task in self:
            status = task._get_pg_ai_consultive_flow_status()
            if status['stage'] == 'ready':
                task.pg_ai_consultive_flow_feedback = _(
                    "Guided consultive flow complete. AI can be used because discovery, fit-gap, final recommendation and the consultive gate are all ready."
                )
                continue

            lines = [
                _("Current guided step: %s.") % stage_labels[status['stage']],
                _("Complete the following before moving to the next step:"),
            ]
            lines.extend("- %s" % item for item in status['current_missing'])
            task.pg_ai_consultive_flow_feedback = '\n'.join(lines)

    @api.depends(
        'name',
        'description',
        'pg_scope_summary',
        'pg_acceptance_criteria_text',
        'pg_ai_consultive_gate_state',
        'pg_ai_consultive_gate_notes',
        'pg_ai_consultive_gate_checked_by_id',
        'pg_ai_consultive_gate_checked_at',
        'project_id',
        'project_id.pg_business_goal',
        'project_id.pg_current_request',
        'project_id.pg_project_phase',
        'project_id.pg_odoo_version',
        'project_id.pg_odoo_edition',
        'project_id.pg_odoo_environment',
        'project_id.pg_standard_allowed',
        'project_id.pg_additional_modules_allowed',
        'project_id.pg_studio_allowed',
        'project_id.pg_custom_allowed',
        'pg_ai_recommendation_class',
        'pg_ai_recommended_module',
        'pg_ai_standard_review',
        'pg_ai_additional_module_review',
        'pg_ai_studio_review',
        'pg_ai_recommendation_justification',
    )
    def _compute_pg_ai_consultive_gate_feedback(self):
        for task in self:
            missing = task._get_pg_ai_consultive_gate_missing_items(include_notes=(task.pg_ai_consultive_gate_state != 'ready'))
            if task.pg_ai_consultive_gate_state == 'ready' and not missing:
                checked_by = task.pg_ai_consultive_gate_checked_by_id.display_name or _('Unknown')
                checked_at = fields.Datetime.to_string(task.pg_ai_consultive_gate_checked_at) if task.pg_ai_consultive_gate_checked_at else _('Unknown')
                task.pg_ai_consultive_gate_feedback = _(
                    "Consultive gate ready. Last checked by %s at %s."
                ) % (checked_by, checked_at)
                continue

            lines = [_("Before using AI, complete the following:")]
            lines.extend("- %s" % item for item in missing)
            task.pg_ai_consultive_gate_feedback = '\n'.join(lines)

    @api.depends(
        'pg_ai_recommendation_class',
        'pg_ai_recommended_module',
        'pg_ai_standard_review',
        'pg_ai_additional_module_review',
        'pg_ai_studio_review',
        'pg_ai_recommendation_justification',
        'project_id',
        'project_id.pg_standard_allowed',
        'project_id.pg_additional_modules_allowed',
        'project_id.pg_studio_allowed',
        'project_id.pg_custom_allowed',
    )
    def _compute_pg_ai_recommendation_feedback(self):
        for task in self:
            missing = task._get_pg_ai_recommendation_missing_items()
            if not missing and task.pg_ai_recommendation_class:
                lines = [
                    _("Final recommendation classified as: %s.") % task._get_pg_ai_recommendation_class_label(),
                ]
                if task.pg_ai_recommended_module:
                    lines.append(_("Recommended Odoo module: %s") % task.pg_ai_recommended_module)
                task.pg_ai_recommendation_feedback = '\n'.join(lines)
                continue

            lines = [_("Before using AI, complete the final recommendation classification:")]
            lines.extend("- %s" % item for item in missing or [_("Select the final recommendation class on the task.")])
            task.pg_ai_recommendation_feedback = '\n'.join(lines)

    @api.onchange('ai_repo_id')
    def _onchange_ai_repo_id(self):
        self.ai_base_branch_id = False
        if not self.ai_repo_id:
            return {'domain': {'ai_base_branch_id': []}}

        if self._get_boolean_param('pg_ai_autosync_branches_on_repo_change', 'True'):
            self.ai_repo_id.sync_branches()
        default_branch = self.ai_repo_id.get_default_branch_record()
        if default_branch and self._get_boolean_param('pg_ai_auto_select_default_branch', 'True'):
            self.ai_base_branch_id = default_branch
        return {'domain': {'ai_base_branch_id': [('repository_id', '=', self.ai_repo_id.id)]}}

    def _ensure_base_branch(self):
        self.ensure_one()
        if self.ai_base_branch_id:
            return self.ai_base_branch_id
        if not self.ai_repo_id:
            return False
        self.ai_repo_id.sync_branches()
        default_branch = self.ai_repo_id.get_default_branch_record()
        if default_branch:
            self.write({'ai_base_branch_id': default_branch.id})
            return default_branch
        return False

    def action_sync_ai_repositories(self):
        GitHubService(self.env).sync_user_repositories()
        if self.ai_repo_id:
            self.ai_repo_id.sync_branches()
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_sync_ai_branches(self):
        self.ensure_one()
        if not self.ai_repo_id:
            raise UserError(_("Select an AI repository before synchronizing branches."))
        self.ai_repo_id.sync_branches()
        default_branch = self.ai_repo_id.get_default_branch_record()
        values = {}
        if default_branch:
            values['ai_base_branch_id'] = default_branch.id
        if values:
            self.write(values)
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_generate_scope_enrichment_draft(self):
        for task in self:
            task._ensure_scope_enrichment_allowed()
            suggestions = task._get_pg_scope_enrichment_service().build_suggestions(task)
            suggestions.update(
                {
                    'pg_scope_enrichment_generated_at': fields.Datetime.now(),
                    'pg_scope_enrichment_generated_by_id': self.env.user.id,
                }
            )
            task.with_context(pg_skip_scope_enrichment_reset=True).write(suggestions)
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_apply_scope_enrichment_draft(self):
        self.ensure_one()

        if self.pg_scope_enrichment_status not in {'draft', 'needs_review'}:
            raise UserError(_("Generate a scope enrichment draft before applying it."))

        values, applied_fields = self._get_scope_enrichment_apply_values()

        if not values:
            raise UserError(
                _("The official scope fields are already filled. Clear them manually if you want to replace them with the draft.")
            )

        values.update(
            {
                'pg_scope_enrichment_status': 'applied',
                'pg_scope_enrichment_feedback': _(
                    "Scope enrichment draft applied to: %s."
                ) % ', '.join(applied_fields),
            }
        )
        self.with_context(pg_skip_scope_enrichment_reset=True).write(values)
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_discard_scope_enrichment_draft(self):
        self.ensure_one()
        self.with_context(pg_skip_scope_enrichment_reset=True).write(
            self._pg_scope_enrichment_field_values(
                {
                    'pg_scope_enrichment_status': 'dismissed',
                    'pg_scope_enrichment_feedback': _(
                        "Scope enrichment draft discarded by %s."
                    ) % (self.env.user.display_name or _('Unknown')),
                }
            )
        )
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_generate_consultive_prefill(self):
        for task in self:
            if not task.project_id:
                raise UserError(_("Associate the task with a project before generating a consultive prefill draft."))
            suggestions = task._get_pg_ai_consultive_prefill_service().build_suggestions(task)
            suggestions.update(
                {
                    'pg_ai_consultive_prefill_generated_at': fields.Datetime.now(),
                    'pg_ai_consultive_prefill_generated_by_id': self.env.user.id,
                }
            )
            task.with_context(pg_skip_ai_consultive_prefill_reset=True).write(suggestions)
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_apply_consultive_prefill(self):
        self.ensure_one()

        if self.pg_ai_consultive_prefill_status not in {'draft', 'needs_review'}:
            raise UserError(_("Generate a consultive prefill draft before applying it."))

        values, applied_fields = self._get_pg_ai_consultive_prefill_apply_values()

        if not values:
            raise UserError(
                _("The official consultive fields are already filled. Clear them manually if you want to replace them with the draft.")
            )

        values.update(
            {
                'pg_ai_consultive_prefill_status': 'applied',
                'pg_ai_consultive_prefill_feedback': _(
                    "Consultive prefill draft applied to: %s."
                ) % ', '.join(applied_fields),
            }
        )
        self.with_context(pg_skip_ai_consultive_prefill_reset=True).write(values)
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_discard_consultive_prefill(self):
        self.ensure_one()
        self.with_context(pg_skip_ai_consultive_prefill_reset=True).write(
            self._pg_ai_consultive_prefill_field_values(
                {
                    'pg_ai_consultive_prefill_status': 'dismissed',
                    'pg_ai_consultive_prefill_feedback': _(
                        "Consultive prefill draft discarded by %s."
                    ) % (self.env.user.display_name or _('Unknown')),
                }
            )
        )
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_refresh_chatter_signals(self):
        for task in self:
            task._get_pg_chatter_queue_service().refresh_task(task)
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_view_chatter_signals(self):
        self.ensure_one()
        action = self.env.ref('pg_brodoo.action_pg_project_chatter_signal').read()[0]
        action['domain'] = [('task_id', '=', self.id)]
        action['context'] = {'default_task_id': self.id, 'default_project_id': self.project_id.id}
        return action

    def action_generate_prompt(self):
        self.ensure_one()
        self._ensure_pg_ai_consultive_gate_ready(_("generating the AI prompt"))
        if not self.name:
            raise UserError(_("The task must have a name before generating the AI prompt."))

        self._ai_get_orchestrator().generate_prompt(self)
        history_entry = self.env['project.task.ai.history'].search(
            [('task_id', '=', self.id), ('entry_type', '=', 'prompt')],
            order='create_date desc, id desc',
            limit=1,
        )
        self._capture_pg_ai_consultive_decision('prompt_generated', ai_history_entry=history_entry)
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_mark_ai_consultive_gate_ready(self):
        self.ensure_one()

        missing = self._get_pg_ai_consultive_gate_missing_items(include_notes=True)
        if missing:
            raise UserError(self._build_pg_ai_consultive_gate_error(_("marking the consultive gate as ready"), include_notes=True))

        self.with_context(pg_skip_ai_consultive_gate_reset=True).write(
            {
                'pg_ai_consultive_gate_state': 'ready',
                'pg_ai_consultive_gate_checked_by_id': self.env.user.id,
                'pg_ai_consultive_gate_checked_at': fields.Datetime.now(),
            }
        )
        self._capture_pg_ai_consultive_decision('gate_ready')
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_reopen_ai_consultive_gate(self):
        self.ensure_one()
        self._reopen_pg_ai_consultive_gate()
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    @api.model_create_multi
    def create(self, vals_list):
        tasks = super().create(vals_list)
        if not self.env.context.get('pg_skip_scope_sync_enqueue'):
            tasks._queue_scope_sync_for_projects(tasks.mapped('project_id'), 'task_create')
        if not self.env.context.get('pg_skip_mirror_sync_enqueue'):
            tasks._queue_mirror_sync_for_projects(tasks.mapped('project_id'), 'task_create')
        return tasks

    def write(self, vals):
        vals = self._normalize_scope_enrichment_state_values(vals)
        old_projects = self.mapped('project_id')
        ready_gate_tasks = self.browse()
        tasks_with_scope_enrichment = self.browse()
        tasks_with_consultive_prefill = self.browse()
        should_enqueue = (
            not self.env.context.get('pg_skip_scope_sync_enqueue')
            and bool(set(vals) & self._pg_scope_sync_relevant_fields())
        )
        should_enqueue_mirror = (
            not self.env.context.get('pg_skip_mirror_sync_enqueue')
            and bool(set(vals) & self._pg_scope_sync_relevant_fields())
        )
        should_reopen_gate = (
            not self.env.context.get('pg_skip_ai_consultive_gate_reset')
            and 'pg_ai_consultive_gate_state' not in vals
            and 'pg_ai_consultive_gate_checked_by_id' not in vals
            and 'pg_ai_consultive_gate_checked_at' not in vals
            and bool(set(vals) & self._pg_ai_consultive_gate_relevant_fields())
        )
        should_reset_scope_enrichment = (
            not self.env.context.get('pg_skip_scope_enrichment_reset')
            and bool(
                set(vals)
                & (
                    self._pg_scope_official_fields()
                    | {'name', 'description', 'pg_scope_relevant', 'pg_scope_track', 'pg_scope_state'}
                )
            )
        )
        should_reset_consultive_prefill = (
            not self.env.context.get('pg_skip_ai_consultive_prefill_reset')
            and bool(
                set(vals)
                & (
                    self._pg_ai_consultive_prefill_official_fields()
                    | {'name', 'description', 'project_id', 'pg_scope_kind', 'pg_scope_summary', 'pg_acceptance_criteria_text'}
                )
            )
        )
        if should_reopen_gate:
            ready_gate_tasks = self.filtered(lambda task: task.pg_ai_consultive_gate_state == 'ready')
        if should_reset_scope_enrichment:
            tasks_with_scope_enrichment = self.filtered(
                lambda task: (task.pg_scope_enrichment_status or 'empty') != 'empty'
            )
        if should_reset_consultive_prefill:
            tasks_with_consultive_prefill = self.filtered(
                lambda task: (task.pg_ai_consultive_prefill_status or 'empty') != 'empty'
            )
        result = super().write(vals)
        if should_enqueue:
            self._queue_scope_sync_for_projects(old_projects | self.mapped('project_id'), 'task_write')
        if should_enqueue_mirror:
            self._queue_mirror_sync_for_projects(old_projects | self.mapped('project_id'), 'task_write')
        if should_reopen_gate:
            ready_gate_tasks._reopen_pg_ai_consultive_gate()
        if should_reset_scope_enrichment:
            tasks_with_scope_enrichment.with_context(pg_skip_scope_enrichment_reset=True).write(
                tasks_with_scope_enrichment._pg_scope_enrichment_field_values()
            )
        if should_reset_consultive_prefill:
            tasks_with_consultive_prefill.with_context(pg_skip_ai_consultive_prefill_reset=True).write(
                tasks_with_consultive_prefill._pg_ai_consultive_prefill_field_values()
            )
        if 'project_id' in vals:
            for task in self:
                task.pg_chatter_signal_ids.sudo().write({'project_id': task.project_id.id or False})
        return result

    def unlink(self):
        old_projects = self.mapped('project_id')
        trigger_record_id = self[:1].id if self else False
        result = super().unlink()
        if not self.env.context.get('pg_skip_scope_sync_enqueue'):
            scope_sync_service = ProjectScopeSyncService(self.env)
            for project in old_projects:
                scope_sync_service.queue_project(
                    project,
                    trigger_type='task_unlink',
                    trigger_model='project.task',
                    trigger_record_id=trigger_record_id,
                )
        if not self.env.context.get('pg_skip_mirror_sync_enqueue'):
            for project in old_projects:
                project._get_pg_mirror_sync_service().queue_project(
                    project,
                    trigger_type='task_unlink',
                    trigger_model='project.task',
                    trigger_record_id=trigger_record_id,
                )
        return result

    def _schedule_ai_cron(self):
        self.ensure_one()
        cron = self.env['ir.cron'].sudo().create(
            {
                'name': f'Brodoo Task {self.id}',
                'model_id': self.env['ir.model']._get('project.task').id,
                'state': 'code',
                'code': f'model._cron_run_ai_task({self.id})',
                'user_id': self.env.user.id,
                'interval_number': 1,
                'interval_type': 'months',
                'nextcall': fields.Datetime.now(),
                'priority': 0,
                'active': True,
            }
        )
        cron._trigger()
        return cron

    @api.model
    def _cron_run_ai_task(self, task_id):
        task = self.sudo().browse(task_id).exists()
        try:
            if task:
                task._ai_get_orchestrator().run_codex(task)
            else:
                _logger.warning("AI cron skipped because task %s no longer exists", task_id)
        except Exception:
            _logger.exception("Background AI execution failed for task %s", task_id)
        finally:
            self.env['ir.cron']._commit_progress(processed=1, remaining=0, deactivate=True)

    def action_run_codex(self):
        self.ensure_one()
        self._ensure_pg_ai_consultive_gate_ready(_("executing Codex"))
        if not self.ai_repo_id:
            raise UserError(_("Select an AI repository before executing Codex."))
        if not self.ai_prompt_final:
            raise UserError(_("Generate or fill the final AI prompt before executing Codex."))
        if not self._ensure_base_branch():
            raise UserError(_("Select a GitHub target branch before executing Codex."))
        if self.ai_status in {'queued', 'running'}:
            raise UserError(_("Codex is already processing this task."))

        self._ai_get_orchestrator().prepare_codex_run(self)
        self._capture_pg_ai_consultive_decision('codex_queued', ai_history_entry=self.ai_current_history_id)
        self._schedule_ai_cron()
        return {'type': 'ir.actions.client', 'tag': 'reload'}
