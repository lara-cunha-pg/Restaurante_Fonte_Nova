from odoo.tests import TransactionCase, tagged

from .common import PgAiDevAssistantTestMixin


@tagged('post_install', '-at_install')
class TestScopeEnrichmentProjectActions(PgAiDevAssistantTestMixin, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.repository = cls.create_repository(name='scope_bulk_repo')
        cls.project = cls.create_project(cls.repository)

    def test_generate_scope_enrichment_drafts_updates_project_counters(self):
        high_confidence_task = self.create_task(
            self.project,
            name='Integracao GitHub API',
            description='<p>Sincronizar eventos GitHub com API externa.</p>',
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )
        low_confidence_task = self.create_task(
            self.project,
            name='Tarefa teste',
            description=False,
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )
        self.create_task(
            self.project,
            name='Backlog operacional ignorado',
            pg_scope_track='operational_backlog',
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )

        self.project.action_generate_scope_enrichment_drafts()

        self.assertEqual(high_confidence_task.pg_scope_enrichment_status, 'draft')
        self.assertEqual(low_confidence_task.pg_scope_enrichment_status, 'needs_review')
        self.assertTrue(self.project.pg_scope_enrichment_last_run_at)
        self.assertEqual(self.project.pg_scope_enrichment_last_run_by_id, self.env.user)
        self.assertEqual(self.project.pg_scope_enrichment_pending_count, 2)
        self.assertEqual(self.project.pg_scope_enrichment_needs_review_count, 1)
        self.assertIn('Pending assisted drafts: 2', self.project.pg_scope_enrichment_feedback)
        self.assertIn('review candidates', self.project.pg_scope_enrichment_feedback)

    def test_project_scope_feedback_uses_task_level_assisted_drafts_without_project_run(self):
        task = self.create_task(
            self.project,
            name='Tarefa teste',
            description=False,
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )

        task.action_generate_scope_enrichment_draft()
        self.project.invalidate_recordset([
            'pg_scope_enrichment_last_run_at',
            'pg_scope_enrichment_last_run_by_id',
            'pg_scope_enrichment_pending_count',
            'pg_scope_enrichment_needs_review_count',
            'pg_scope_enrichment_applied_count',
            'pg_scope_enrichment_feedback',
        ])

        self.assertFalse(self.project.pg_scope_enrichment_last_run_at)
        self.assertEqual(self.project.pg_scope_enrichment_pending_count, 1)
        self.assertEqual(self.project.pg_scope_enrichment_needs_review_count, 1)
        self.assertIn('Pending assisted drafts: 1', self.project.pg_scope_enrichment_feedback)
        self.assertIn('review candidates', self.project.pg_scope_enrichment_feedback)
        self.assertNotIn('No assisted draft has been generated', self.project.pg_scope_enrichment_feedback)

    def test_apply_scope_enrichment_drafts_applies_only_high_confidence_drafts(self):
        draft_task = self.create_task(
            self.project,
            name='Dashboard KPI operacional',
            description='<p>Gerar dashboard KPI operacional para o projeto.</p>',
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )
        review_task = self.create_task(
            self.project,
            name='Tarefa teste',
            description=False,
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )

        self.project.action_generate_scope_enrichment_drafts()
        self.project.action_apply_scope_enrichment_drafts()

        self.assertEqual(draft_task.pg_scope_enrichment_status, 'applied')
        self.assertEqual(draft_task.pg_scope_kind, 'report')
        self.assertTrue(draft_task.pg_scope_summary)
        self.assertTrue(draft_task.pg_acceptance_criteria_text)
        self.assertEqual(review_task.pg_scope_enrichment_status, 'needs_review')
        self.assertFalse(review_task.pg_scope_kind)
        self.assertGreaterEqual(self.project.pg_scope_enrichment_applied_count, 1)

    def test_view_scope_enrichment_tasks_targets_pending_drafts(self):
        task = self.create_task(
            self.project,
            name='Integracao webhook',
            description='<p>Integrar webhook com sistema externo.</p>',
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )
        self.project.action_generate_scope_enrichment_drafts()

        action = self.project.action_view_scope_enrichment_tasks()

        self.assertEqual(action['res_model'], 'project.task')
        self.assertIn(('project_id', '=', self.project.id), action['domain'])
        self.assertIn(('pg_scope_enrichment_status', 'in', ['draft', 'needs_review']), action['domain'])
        self.assertEqual(task.pg_scope_enrichment_status, 'draft')

    def test_normalize_existing_scope_enrichment_fallbacks_keeps_fallback_in_manual_review(self):
        stale_task = self.create_task(self.project, name='Fallback antigo')
        stale_task.with_context(pg_skip_scope_enrichment_reset=True).write(
            {
                'pg_scope_enrichment_source': 'llm_fallback_rule_based',
                'pg_scope_enrichment_status': 'draft',
                'pg_scope_summary_suggested': 'Resumo antigo de fallback.',
                'pg_acceptance_criteria_suggested_text': 'Criterio antigo.',
                'pg_scope_enrichment_feedback': 'Draft antigo inconsistente.',
            }
        )

        stale_task._normalize_existing_scope_enrichment_fallbacks()

        self.assertEqual(stale_task.pg_scope_enrichment_source, 'llm_fallback_rule_based')
        self.assertEqual(stale_task.pg_scope_enrichment_status, 'needs_review')
        self.assertIn('revisao manual', (stale_task.pg_scope_enrichment_feedback or '').lower())

    def test_generate_scope_enrichment_drafts_clears_stale_project_level_drafts_before_regeneration(self):
        stale_task = self.create_task(
            self.project,
            name='Draft historico restaurado',
            pg_scope_kind='requirement',
            pg_scope_summary='Resumo oficial ja aplicado.',
            pg_acceptance_criteria_text='Criterio oficial ja aplicado.',
        )
        stale_task.with_context(pg_skip_scope_enrichment_reset=True).write(
            {
                'pg_scope_enrichment_status': 'draft',
                'pg_scope_enrichment_source': 'rule_based',
                'pg_scope_summary_suggested': 'Resumo antigo trazido da base restaurada.',
                'pg_acceptance_criteria_suggested_text': 'Criterio antigo trazido da base restaurada.',
                'pg_scope_enrichment_feedback': 'Draft antigo do projeto.',
                'pg_scope_enrichment_generated_at': '2026-04-01 10:00:00',
                'pg_scope_enrichment_generated_by_id': self.env.user.id,
            }
        )
        fresh_task = self.create_task(
            self.project,
            name='Task atual por enriquecer',
            description='<p>Configurar dashboard operacional.</p>',
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )

        self.project.action_generate_scope_enrichment_drafts()

        self.assertEqual(stale_task.pg_scope_enrichment_status, 'empty')
        self.assertFalse(stale_task.pg_scope_summary_suggested)
        self.assertFalse(stale_task.pg_acceptance_criteria_suggested_text)
        self.assertFalse(stale_task.pg_scope_enrichment_generated_at)
        self.assertEqual(fresh_task.pg_scope_enrichment_status, 'draft')

        action = self.project.action_view_scope_enrichment_tasks()
        visible_tasks = self.env['project.task'].search(action['domain'])
        self.assertNotIn(stale_task, visible_tasks)
        self.assertIn(fresh_task, visible_tasks)
