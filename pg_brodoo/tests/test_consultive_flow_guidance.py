from odoo.tests import TransactionCase, tagged

from .common import PgAiDevAssistantTestMixin


@tagged('post_install', '-at_install')
class TestConsultiveFlowGuidance(PgAiDevAssistantTestMixin, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.set_pg_base_url()
        cls.repository = cls.create_repository(name='guided_flow_repo')
        cls.branch = cls.create_repository_branch(cls.repository, name='teste', is_default=True)
        cls.project = cls.create_project(cls.repository, name='Projeto Guided Flow Test')
        cls.task = cls.create_task(cls.project, name='Task com fluxo guiado')

    def test_guided_flow_starts_in_discovery_when_project_context_is_missing(self):
        project = self.create_project(
            self.repository,
            name='Projeto Discovery em Falta',
            pg_business_goal=False,
        )
        task = self.create_task(project, name='Task em discovery')

        self.assertEqual(task.pg_ai_consultive_flow_stage, 'discovery')
        self.assertEqual(task.pg_ai_discovery_step_state, 'pending')
        self.assertIn('Current guided step: Discovery.', task.pg_ai_consultive_flow_feedback)
        self.assertIn('Business Goal', task.pg_ai_consultive_flow_feedback)

    def test_guided_flow_moves_to_fit_gap_after_discovery_is_ready(self):
        self.assertEqual(self.task.pg_ai_consultive_flow_stage, 'fit_gap')
        self.assertEqual(self.task.pg_ai_discovery_step_state, 'ready')
        self.assertEqual(self.task.pg_ai_fit_gap_step_state, 'pending')
        self.assertIn('Current guided step: Fit-Gap.', self.task.pg_ai_consultive_flow_feedback)
        self.assertIn('Standard Review', self.task.pg_ai_consultive_flow_feedback)

    def test_guided_flow_moves_to_recommendation_after_fit_gap_review(self):
        self.task.write({'pg_ai_standard_review': 'Standard revisto no projeto.'})

        self.assertEqual(self.task.pg_ai_consultive_flow_stage, 'recommendation')
        self.assertEqual(self.task.pg_ai_fit_gap_step_state, 'ready')
        self.assertEqual(self.task.pg_ai_recommendation_step_state, 'pending')
        self.assertIn('Current guided step: Recommendation.', self.task.pg_ai_consultive_flow_feedback)
        self.assertIn('recommendation class', self.task.pg_ai_consultive_flow_feedback.lower())

    def test_guided_flow_moves_to_gate_after_recommendation_is_classified(self):
        self.set_task_recommendation(self.task, recommendation_class='standard')

        self.assertEqual(self.task.pg_ai_consultive_flow_stage, 'gate')
        self.assertEqual(self.task.pg_ai_recommendation_step_state, 'ready')
        self.assertEqual(self.task.pg_ai_gate_step_state, 'pending')
        self.assertIn('Current guided step: Consultive Gate.', self.task.pg_ai_consultive_flow_feedback)
        self.assertIn('Consultive Gate Notes', self.task.pg_ai_consultive_flow_feedback)

    def test_guided_flow_becomes_ready_after_gate_is_marked_ready(self):
        self.set_task_recommendation(self.task, recommendation_class='standard')
        self.task.write({'pg_ai_consultive_gate_notes': 'Analise consultiva concluida para esta task.'})
        self.task.action_mark_ai_consultive_gate_ready()

        self.assertEqual(self.task.pg_ai_consultive_flow_stage, 'ready')
        self.assertEqual(self.task.pg_ai_gate_step_state, 'ready')
        self.assertIn('Guided consultive flow complete', self.task.pg_ai_consultive_flow_feedback)
