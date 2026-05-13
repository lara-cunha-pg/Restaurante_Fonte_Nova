from odoo import fields
from odoo.tests import TransactionCase, tagged

from .common import PgAiDevAssistantTestMixin


@tagged('post_install', '-at_install')
class TestOperationalDashboard(PgAiDevAssistantTestMixin, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.set_pg_base_url()
        cls.repository = cls.create_repository(name='dashboard_repo')
        cls.branch = cls.create_repository_branch(cls.repository, name='teste', is_default=True)

        cls.project_scope_attention = cls.create_project(
            cls.repository,
            name='Projeto Scope Attention',
            pg_status_sync_enabled=False,
        )
        cls.project_status_attention = cls.create_project(
            cls.repository,
            name='Projeto Status Attention',
            pg_scope_sync_enabled=False,
            pg_status_sync_last_status='done',
            pg_status_sync_needs_publish=True,
            pg_status_sync_last_published_at=fields.Datetime.now(),
        )
        cls.project_clean = cls.create_project(
            cls.repository,
            name='Projeto Limpo',
            pg_scope_sync_last_status='done',
            pg_scope_sync_last_published_at=fields.Datetime.now(),
            pg_status_sync_last_status='done',
            pg_status_sync_needs_publish=False,
            pg_status_sync_last_published_at=fields.Datetime.now(),
        )

        cls.blocked_task = cls.create_task(cls.project_clean, name='Task bloqueada dashboard')
        cls.set_task_recommendation(cls.blocked_task, recommendation_class='standard')

        cls.ready_task = cls.create_task(cls.project_clean, name='Task ready dashboard')
        cls.set_task_recommendation(cls.ready_task, recommendation_class='standard')
        cls.ready_task.write({'pg_ai_consultive_gate_notes': 'Notas consultivas completas para dashboard.'})
        cls.ready_task.action_mark_ai_consultive_gate_ready()

        cls.missing_summary_task = cls.create_task(
            cls.project_clean,
            name='Task sem resumo',
            pg_scope_summary=False,
        )
        cls.missing_criteria_task = cls.create_task(
            cls.project_clean,
            name='Task sem criterios',
            pg_acceptance_criteria_text=False,
        )
        cls.missing_kind_task = cls.create_task(
            cls.project_clean,
            name='Task sem kind',
            pg_scope_kind=False,
        )
        cls.needs_review_task = cls.create_task(
            cls.project_clean,
            name='Task brownfield sem base',
            description=False,
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )
        cls.needs_review_task.action_generate_scope_enrichment_draft()

        cls.failed_scope_run = cls.env['pg.project.scope.sync.run'].create(
            {
                'project_id': cls.project_scope_attention.id,
                'status': 'error',
                'trigger_type': 'manual',
                'message': 'Falha de scope para dashboard',
            }
        )
        cls.failed_status_run = cls.env['pg.project.status.sync.run'].create(
            {
                'project_id': cls.project_status_attention.id,
                'status': 'error',
                'trigger_type': 'manual_button',
                'message': 'Falha de status para dashboard',
            }
        )

        cls.dashboard_chatter_task = cls.create_task(
            cls.project_clean,
            name='Task chatter dashboard',
            description=False,
        )
        cls.create_chatter_message(
            'project.project',
            cls.project_clean.id,
            '<p>Blocked until the customer shares the production API credentials.</p>',
        )
        cls.create_chatter_message(
            'project.task',
            cls.dashboard_chatter_task.id,
            '<p>We may delay the rollout if customer data is late.</p>',
        )
        cls.create_chatter_message(
            'project.task',
            cls.dashboard_chatter_task.id,
            '<p>Approved for production by the customer.</p>',
        )
        cls.create_chatter_message(
            'project.task',
            cls.dashboard_chatter_task.id,
            '<p>Approved for production by the customer.</p>',
        )
        cls.project_clean.action_refresh_chatter_signals()

        cls.dirty_chatter_task = cls.create_task(
            cls.project_clean,
            name='Task dirty chatter dashboard',
            description=False,
        )
        cls.create_chatter_message(
            'project.task',
            cls.dirty_chatter_task.id,
            '<p>Decision final: agreed to review the firewall settings.</p>',
        )

    def test_dashboard_collects_operational_signals(self):
        dashboard = self.env['pg.operational.dashboard'].create({})

        self.assertEqual(dashboard.display_name, 'Dashboard Brodoo')
        self.assertIn(self.project_scope_attention, dashboard.scope_attention_project_ids)
        self.assertNotIn(self.project_clean, dashboard.scope_attention_project_ids)
        self.assertIn(self.project_status_attention, dashboard.status_attention_project_ids)
        self.assertNotIn(self.project_clean, dashboard.status_attention_project_ids)
        self.assertIn(self.blocked_task, dashboard.blocked_ai_task_ids)
        self.assertIn(self.ready_task, dashboard.ready_ai_task_ids)
        self.assertIn(self.failed_scope_run, dashboard.failed_scope_run_ids)
        self.assertIn(self.failed_status_run, dashboard.failed_status_run_ids)
        self.assertIn(self.missing_summary_task, dashboard.brownfield_missing_scope_summary_task_ids)
        self.assertIn(self.missing_criteria_task, dashboard.brownfield_missing_acceptance_criteria_task_ids)
        self.assertIn(self.missing_kind_task, dashboard.brownfield_missing_scope_kind_task_ids)
        self.assertIn(self.needs_review_task, dashboard.brownfield_needs_review_task_ids)
        self.assertGreaterEqual(dashboard.scope_attention_project_count, 1)
        self.assertGreaterEqual(dashboard.status_attention_project_count, 1)
        self.assertGreaterEqual(dashboard.blocked_ai_task_count, 1)
        self.assertGreaterEqual(dashboard.ready_ai_task_count, 1)
        self.assertGreaterEqual(dashboard.failed_scope_run_count, 1)
        self.assertGreaterEqual(dashboard.failed_status_run_count, 1)
        self.assertGreaterEqual(dashboard.brownfield_missing_scope_summary_count, 1)
        self.assertGreaterEqual(dashboard.brownfield_missing_acceptance_criteria_count, 1)
        self.assertGreaterEqual(dashboard.brownfield_missing_scope_kind_count, 1)
        self.assertGreaterEqual(dashboard.brownfield_needs_review_task_count, 1)
        self.assertGreaterEqual(dashboard.chatter_dirty_project_count, 1)
        self.assertGreaterEqual(dashboard.chatter_dirty_task_count, 1)
        self.assertGreaterEqual(dashboard.chatter_validated_signal_count, 1)
        self.assertGreaterEqual(dashboard.chatter_candidate_signal_count, 1)
        self.assertGreaterEqual(dashboard.chatter_stale_signal_count, 1)
        self.assertIn(self.project_clean, dashboard.chatter_dirty_project_ids)
        self.assertIn(self.dirty_chatter_task, dashboard.chatter_dirty_task_ids)
        self.assertTrue(dashboard.chatter_validated_signal_ids)
        self.assertTrue(dashboard.chatter_candidate_signal_ids)
        self.assertTrue(dashboard.chatter_stale_signal_ids)

    def test_dashboard_actions_target_expected_models(self):
        dashboard = self.env['pg.operational.dashboard'].create({})

        scope_action = dashboard.action_open_scope_attention_projects()
        task_action = dashboard.action_open_blocked_ai_tasks()
        scope_run_action = dashboard.action_open_failed_scope_runs()
        brownfield_action = dashboard.action_open_brownfield_needs_review_tasks()
        dirty_project_action = dashboard.action_open_chatter_dirty_projects()
        candidate_signal_action = dashboard.action_open_candidate_chatter_signals()
        stale_signal_action = dashboard.action_open_stale_chatter_signals()

        self.assertEqual(scope_action['res_model'], 'project.project')
        self.assertEqual(task_action['res_model'], 'project.task')
        self.assertEqual(scope_run_action['res_model'], 'pg.project.scope.sync.run')
        self.assertEqual(brownfield_action['res_model'], 'project.task')
        self.assertEqual(dirty_project_action['res_model'], 'project.project')
        self.assertEqual(candidate_signal_action['res_model'], 'pg.project.chatter.signal')
        self.assertEqual(stale_signal_action['res_model'], 'pg.project.chatter.signal')
        self.assertEqual(
            scope_action['id'],
            self.env.ref('pg_brodoo.action_pg_operational_scope_attention_projects').id,
        )
        self.assertEqual(
            task_action['id'],
            self.env.ref('pg_brodoo.action_pg_operational_blocked_ai_tasks').id,
        )
        self.assertEqual(
            scope_action['domain'],
            [('id', 'in', self.env['project.project'].search(dashboard._get_scope_attention_project_domain()).ids)],
        )
        self.assertEqual(
            task_action['domain'],
            [('id', 'in', self.env['project.task'].search(dashboard._get_blocked_ai_task_domain()).ids)],
        )
        self.assertEqual(
            scope_action['views'],
            [(self.env.ref('pg_brodoo.view_pg_operational_dashboard_project_list').id, 'list'), (False, 'form')],
        )
        self.assertEqual(
            task_action['views'],
            [(self.env.ref('pg_brodoo.view_pg_operational_dashboard_task_list').id, 'list'), (False, 'form')],
        )
        self.assertEqual(
            scope_action['search_view_id'],
            self.env.ref('pg_brodoo.view_pg_operational_dashboard_project_search').id,
        )
        self.assertEqual(
            task_action['search_view_id'],
            self.env.ref('pg_brodoo.view_pg_operational_dashboard_task_search').id,
        )
        self.assertEqual(scope_action['context'], {})
        self.assertEqual(task_action['context'], {})
        self.assertIn(('status', '=', 'error'), scope_run_action['domain'])
        self.assertEqual(
            brownfield_action['domain'],
            [('id', 'in', self.env['project.task'].search(dashboard._get_brownfield_needs_review_domain()).ids)],
        )
        self.assertEqual(
            dirty_project_action['domain'],
            [('id', 'in', self.env['project.project'].search(dashboard._get_chatter_dirty_project_domain()).ids)],
        )
        self.assertIn(('signal_state', '=', 'candidate'), candidate_signal_action['domain'])
        self.assertIn(('signal_state', '=', 'stale'), stale_signal_action['domain'])
