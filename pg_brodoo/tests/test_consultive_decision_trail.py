from unittest.mock import Mock, patch

from odoo.tests import TransactionCase, tagged

from ..services.chatgpt_service import ChatGptPromptService
from .common import PgAiDevAssistantTestMixin


@tagged('post_install', '-at_install')
class TestConsultiveDecisionTrail(PgAiDevAssistantTestMixin, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.set_pg_base_url()
        cls.repository = cls.create_repository(name='decision_trail_repo')
        cls.branch = cls.create_repository_branch(cls.repository, name='teste', is_default=True)
        cls.project = cls.create_project(cls.repository, name='Projeto Decision Trail Test')
        cls.task = cls.create_task(cls.project, name='Task com trilho consultivo')

    def _prepare_ready_gate(self):
        self.set_task_recommendation(self.task, recommendation_class='standard')
        self.task.write({'pg_ai_consultive_gate_notes': 'Analise consultiva validada para esta task.'})
        self.task.action_mark_ai_consultive_gate_ready()

    def test_mark_gate_ready_creates_consultive_decision(self):
        self._prepare_ready_gate()

        decision = self.task.pg_ai_consultive_decision_ids[:1]

        self.assertTrue(decision)
        self.assertEqual(decision.decision_type, 'gate_ready')
        self.assertEqual(decision.recommendation_class, 'standard')
        self.assertEqual(decision.gate_state, 'ready')
        self.assertEqual(decision.scope_track, 'approved_scope')
        self.assertIn('Business goal', decision.evidence_summary)
        self.assertIn('Recommendation justification', decision.evidence_summary)

    def test_generate_prompt_creates_consultive_decision_and_links_prompt_history(self):
        self._prepare_ready_gate()

        with patch.object(ChatGptPromptService, '_response_text', return_value='Prompt tecnico gerado.'):
            self.task.action_generate_prompt()

        decision = self.task.pg_ai_consultive_decision_ids.filtered(
            lambda entry: entry.decision_type == 'prompt_generated'
        )[:1]

        self.assertTrue(decision)
        self.assertEqual(decision.recommendation_class, 'standard')
        self.assertTrue(decision.ai_history_id)
        self.assertEqual(decision.ai_history_id.entry_type, 'prompt')
        self.assertIn('AI prompt generated', decision.decision_summary)

    def test_run_codex_creates_consultive_decision_linked_to_execution_history(self):
        self._prepare_ready_gate()
        self.task.write(
            {
                'ai_repo_id': self.repository.id,
                'ai_base_branch_id': self.branch.id,
                'ai_prompt_final': 'Executar alteracao controlada',
            }
        )

        history_entry = self.env['project.task.ai.history'].create(
            {
                'task_id': self.task.id,
                'entry_type': 'execution',
                'status': 'queued',
                'prompt_text': self.task.ai_prompt_final,
                'repo_full_name': self.repository.full_name,
                'branch_name': 'pg/task-com-trilho',
                'base_branch': self.branch.name,
            }
        )

        def fake_prepare(task):
            task.write(
                {
                    'ai_status': 'queued',
                    'ai_branch': history_entry.branch_name,
                    'ai_current_history_id': history_entry.id,
                }
            )

        orchestrator = Mock()
        orchestrator.prepare_codex_run.side_effect = fake_prepare

        with patch.object(type(self.task), '_ai_get_orchestrator', return_value=orchestrator), patch.object(
            type(self.task),
            '_schedule_ai_cron',
            return_value=True,
        ):
            self.task.action_run_codex()

        decision = self.task.pg_ai_consultive_decision_ids.filtered(
            lambda entry: entry.decision_type == 'codex_queued'
        )[:1]

        self.assertTrue(decision)
        self.assertEqual(decision.ai_history_id, history_entry)
        self.assertEqual(decision.ai_target_branch, 'teste')
        self.assertIn('Codex execution requested', decision.decision_summary)

    def test_ai_context_summary_includes_consultive_decision_trail(self):
        self._prepare_ready_gate()

        context_summary = self.task.build_ai_continuity_context()

        self.assertIn('Consultive decision trail:', context_summary)
        self.assertIn('Gate Ready', context_summary)
        self.assertIn('Recommendation: Standard', context_summary)
