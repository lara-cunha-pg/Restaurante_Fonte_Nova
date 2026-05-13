from unittest.mock import patch

from odoo.tests import TransactionCase, tagged

from ..services.project_status_draft_llm_service import ProjectStatusDraftLlmService
from .common import PgAiDevAssistantTestMixin


@tagged('post_install', '-at_install')
class TestStatusDraftService(PgAiDevAssistantTestMixin, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.set_pg_base_url()
        cls.repository = cls.create_repository(name='draft_repo')
        cls.project = cls.create_project(cls.repository, name='Projeto Draft Test')
        cls.create_scope_line(cls.project, 'acceptance_criteria', 'Validar draft operacional.')
        cls.create_task(cls.project, name='Tarefa draft')

    def test_generate_status_draft_populates_reviewable_fields(self):
        project = self.env['project.project'].browse(self.project.id)

        project.action_generate_status_draft()

        self.assertTrue(project.pg_status_draft_generated_at)
        self.assertEqual(project.pg_status_draft_generated_by_id, self.env.user)
        self.assertIn('Projeto Draft Test', project.pg_status_draft_summary)
        self.assertIn('Approved scope items currently tracked: 1.', project.pg_status_draft_milestones_text)
        self.assertIn(
            'Confirm which approved scope items can move from proposed to validated.',
            project.pg_status_draft_pending_decisions_text,
        )
        self.assertNotIn('Latest status publication status', project.pg_status_draft_summary)
        self.assertNotIn('No status snapshot has been published yet.', project.pg_status_draft_milestones_text)
        self.assertNotIn('Review this draft', project.pg_status_draft_next_steps_text)
        self.assertNotIn('Apply the draft', project.pg_status_draft_next_steps_text)
        self.assertIn('Draft ready for review', project.pg_status_draft_feedback)
        self.assertIn(
            'Tasks, assisted drafts, backlog and chatter evidence stay outside the published status until then',
            project.pg_status_draft_feedback,
        )
        self.assertEqual(project.pg_status_draft_source, 'deterministic')

    def test_apply_status_draft_copies_values_to_official_status(self):
        project = self.env['project.project'].browse(self.project.id)
        project.action_generate_status_draft()

        project.action_apply_status_draft()

        self.assertEqual(project.pg_status_summary, project.pg_status_draft_summary)
        self.assertEqual(project.pg_status_milestones_text, project.pg_status_draft_milestones_text)
        self.assertEqual(project.pg_status_blockers_text, project.pg_status_draft_blockers_text)
        self.assertEqual(project.pg_status_risks_text, project.pg_status_draft_risks_text)
        self.assertEqual(project.pg_status_next_steps_text, project.pg_status_draft_next_steps_text)
        self.assertEqual(
            project.pg_status_pending_decisions_text,
            project.pg_status_draft_pending_decisions_text,
        )
        self.assertTrue(project.pg_status_sync_needs_publish)
        self.assertIn('Draft already applied', project.pg_status_draft_feedback)
        self.assertIn('Manual publication still reads only the official status fields', project.pg_status_draft_feedback)

    def test_generate_status_draft_uses_brownfield_consolidation_signals(self):
        repository = self.create_repository(name='draft_brownfield_repo')
        project = self.create_project(
            repository,
            name='Projeto Brownfield',
            pg_status_owner_id=False,
            pg_status_go_live_target=False,
            pg_scope_sync_last_status='error',
            pg_status_sync_last_status='error',
            pg_status_sync_needs_publish=True,
        )
        approved_scope_task = self.create_task(
            project,
            name='Tarefa legado',
            description=False,
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )
        self.create_task(
            project,
            name='Backlog operacional',
            pg_scope_track='operational_backlog',
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )

        approved_scope_task.action_generate_scope_enrichment_draft()
        project.action_generate_status_draft()

        self.assertIn(
            'Operational backlog items currently tracked outside approved scope: 1.',
            project.pg_status_draft_summary,
        )
        self.assertIn(
            'Approved scope still needs consolidation for 1 task(s) with incomplete scope fields.',
            project.pg_status_draft_summary,
        )
        self.assertIn(
            'Low-confidence scope drafts still need manual review for 1 task(s).',
            project.pg_status_draft_summary,
        )
        self.assertIn(
            'Approved scope tasks still missing official scope fields: 1.',
            project.pg_status_draft_milestones_text,
        )
        self.assertIn(
            'Latest scope sync failed and should be reviewed before the next publication.',
            project.pg_status_draft_blockers_text,
        )
        self.assertIn(
            'Latest status sync failed and should be reviewed before the next publication.',
            project.pg_status_draft_blockers_text,
        )
        self.assertIn(
            'Low-confidence scope drafts still need manual review before the approved scope can be trusted.',
            project.pg_status_draft_blockers_text,
        )
        self.assertIn(
            'Approved scope still contains 1 task(s) with incomplete scope definition.',
            project.pg_status_draft_risks_text,
        )
        self.assertIn(
            'Generate or apply scope enrichment drafts for approved scope tasks still missing official scope fields.',
            project.pg_status_draft_next_steps_text,
        )
        self.assertIn(
            'Review operational backlog items and confirm which ones should move into approved scope.',
            project.pg_status_draft_next_steps_text,
        )
        self.assertIn(
            'Confirm whether the current operational backlog items should remain outside scope or move into approved scope.',
            project.pg_status_draft_pending_decisions_text,
        )
        self.assertIn(
            'brownfield consolidation is still incomplete',
            project.pg_status_draft_feedback,
        )
        self.assertIn(
            'do not feed the official status directly',
            project.pg_status_draft_feedback,
        )

    def test_generate_status_draft_warns_when_chatter_grounding_is_stale(self):
        repository = self.create_repository(name='draft_stale_chatter_repo')
        project = self.create_project(repository, name='Projeto Chatter Stale')

        project.write({'pg_chatter_signals_dirty': True})
        project.action_generate_status_draft()

        self.assertIn('Validated chatter grounding is stale', project.pg_status_draft_feedback)

    def test_generate_status_draft_stays_available_when_status_sync_is_disabled(self):
        repository = self.create_repository(name='draft_disabled_repo')
        project = self.create_project(
            repository,
            name='Projeto Sem Status Sync',
            pg_status_sync_enabled=False,
        )

        project.action_generate_status_draft()

        self.assertTrue(project.pg_status_draft_generated_at)
        self.assertIn('Projeto Sem Status Sync', project.pg_status_draft_summary)

    def test_generate_status_draft_enriches_output_with_validated_chatter_signals(self):
        repository = self.create_repository(name='draft_chatter_repo')
        project = self.create_project(repository, name='Projeto Draft Chatter')
        task = self.create_task(project, name='Task chatter status')

        self.create_chatter_message(
            'project.project',
            project.id,
            '<p>Blocked until the customer shares the production API credentials.</p>',
        )
        self.create_chatter_message(
            'project.task',
            task.id,
            '<p>Approved for production by the customer.</p>',
        )
        self.create_chatter_message(
            'project.task',
            task.id,
            '<p>Next step is to configure the GitHub webhook and validate the integration flow.</p>',
        )
        self.create_chatter_message(
            'project.task',
            task.id,
            '<p>Depende do cliente validar as firewall rules antes do go-live.</p>',
        )

        project.action_refresh_chatter_signals()
        project.action_generate_status_draft()

        self.assertIn('Validated chatter signals currently grounding this draft', project.pg_status_draft_summary)
        self.assertIn('Validated chatter approval:', project.pg_status_draft_milestones_text)
        self.assertIn('Validated chatter blocker:', project.pg_status_draft_blockers_text)
        self.assertIn('Validated chatter dependency:', project.pg_status_draft_risks_text)
        self.assertIn('Validated chatter next step:', project.pg_status_draft_next_steps_text)
        self.assertTrue(project.pg_status_draft_signal_ids)
        self.assertIn('Validated chatter signals linked to this status draft', project.pg_status_draft_signal_feedback)

    def test_generate_status_draft_keeps_deterministic_path_when_llm_is_not_attempted(self):
        project = self.env['project.project'].browse(self.project.id)

        with patch.object(ProjectStatusDraftLlmService, 'should_attempt', return_value=False), patch.object(
            ProjectStatusDraftLlmService,
            'build_candidate',
            side_effect=AssertionError('LLM candidate path should not run when status redraft is not attempted.'),
        ):
            project.action_generate_status_draft()

        self.assertEqual(project.pg_status_draft_source, 'deterministic')
        self.assertFalse(project.pg_status_draft_confidence)

    def test_generate_status_draft_can_use_llm_assisted_redraft(self):
        project = self.env['project.project'].browse(self.project.id)
        llm_candidate = {
            'decision': 'redraft',
            'status_summary': 'Projeto Draft Test segue em validacao assistida com ambito aprovado consolidado.',
            'milestones': [
                'Ambito aprovado consolidado em 1 item',
                'Draft operacional preparado para publicacao manual',
            ],
            'blockers': [],
            'risks': ['Persistem riscos editoriais em casos contextuais.'],
            'next_steps': ['Publicar um novo snapshot operacional apos revisao humana.'],
            'pending_decisions': ['Confirmar quando publicar o proximo ponto de situacao.'],
            'quality_rationale': 'O draft deterministico era factual, mas podia ficar mais publicavel.',
            'confidence': 86,
        }

        with patch.object(ProjectStatusDraftLlmService, 'should_attempt', return_value=True), patch.object(
            ProjectStatusDraftLlmService,
            'build_candidate',
            return_value=llm_candidate,
        ):
            project.action_generate_status_draft()

        self.assertEqual(project.pg_status_draft_source, 'llm_assisted')
        self.assertEqual(project.pg_status_draft_confidence, 86)
        self.assertEqual(
            project.pg_status_draft_summary,
            'Projeto Draft Test segue em validacao assistida com ambito aprovado consolidado.',
        )
        self.assertIn('LLM-assisted redraft generated', project.pg_status_draft_feedback)
        self.assertIn('LLM rationale', project.pg_status_draft_feedback)

    def test_generate_status_draft_marks_llm_fallback_when_candidate_fails(self):
        project = self.env['project.project'].browse(self.project.id)

        with patch.object(ProjectStatusDraftLlmService, 'should_attempt', return_value=True), patch.object(
            ProjectStatusDraftLlmService,
            'build_candidate',
            return_value=False,
        ):
            project.action_generate_status_draft()

        self.assertEqual(project.pg_status_draft_source, 'llm_fallback_deterministic')
        self.assertFalse(project.pg_status_draft_confidence)
        self.assertIn('deterministic draft was kept', project.pg_status_draft_feedback)
