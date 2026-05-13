from unittest.mock import Mock, patch

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from .common import PgAiDevAssistantTestMixin


@tagged('post_install', '-at_install')
class TestConsultiveGate(PgAiDevAssistantTestMixin, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.set_pg_base_url()
        cls.repository = cls.create_repository(name='gate_repo')
        cls.branch = cls.create_repository_branch(cls.repository, name='teste', is_default=True)
        cls.project = cls.create_project(cls.repository, name='Projeto Gate Test')
        cls.task = cls.create_task(cls.project, name='Task com gate')

    def test_mark_gate_ready_requires_notes(self):
        self.set_task_recommendation(self.task, recommendation_class='standard')

        with self.assertRaises(UserError):
            self.task.action_mark_ai_consultive_gate_ready()

        self.assertEqual(self.task.pg_ai_consultive_gate_state, 'pending')

    def test_generate_prompt_requires_ready_gate(self):
        with self.assertRaises(UserError) as exc:
            self.task.action_generate_prompt()

        self.assertIn('Consultive gate not ready', str(exc.exception))

    def test_run_codex_requires_ready_gate(self):
        self.task.write(
            {
                'ai_repo_id': self.repository.id,
                'ai_base_branch_id': self.branch.id,
                'ai_prompt_final': 'Executar teste controlado',
            }
        )

        with self.assertRaises(UserError) as exc:
            self.task.action_run_codex()

        self.assertIn('Consultive gate not ready', str(exc.exception))

    def test_ready_gate_allows_prompt_generation(self):
        self.set_task_recommendation(self.task, recommendation_class='standard')
        self.task.write({'pg_ai_consultive_gate_notes': 'Análise mínima revista para esta task.'})
        self.task.action_mark_ai_consultive_gate_ready()

        orchestrator = Mock()
        with patch.object(type(self.task), '_ai_get_orchestrator', return_value=orchestrator):
            result = self.task.action_generate_prompt()

        orchestrator.generate_prompt.assert_called_once_with(self.task)
        self.assertEqual(result['tag'], 'reload')
        self.assertEqual(self.task.pg_ai_consultive_gate_state, 'ready')
        self.assertEqual(self.task.pg_ai_consultive_gate_checked_by_id, self.env.user)
        self.assertTrue(self.task.pg_ai_consultive_gate_checked_at)

    def test_task_change_reopens_ready_gate(self):
        self.set_task_recommendation(self.task, recommendation_class='standard')
        self.task.write({'pg_ai_consultive_gate_notes': 'Gate pronto para esta task.'})
        self.task.action_mark_ai_consultive_gate_ready()

        self.task.write({'pg_scope_summary': 'Resumo alterado depois da validacao.'})

        self.assertEqual(self.task.pg_ai_consultive_gate_state, 'pending')
        self.assertFalse(self.task.pg_ai_consultive_gate_checked_by_id)
        self.assertFalse(self.task.pg_ai_consultive_gate_checked_at)

    def test_project_change_reopens_ready_gate(self):
        self.set_task_recommendation(self.task, recommendation_class='standard')
        self.task.write({'pg_ai_consultive_gate_notes': 'Gate pronto para esta task.'})
        self.task.action_mark_ai_consultive_gate_ready()

        self.project.write({'pg_current_request': 'Pedido consultivo alterado.'})

        self.assertEqual(self.task.pg_ai_consultive_gate_state, 'pending')
        self.assertFalse(self.task.pg_ai_consultive_gate_checked_by_id)
        self.assertFalse(self.task.pg_ai_consultive_gate_checked_at)
