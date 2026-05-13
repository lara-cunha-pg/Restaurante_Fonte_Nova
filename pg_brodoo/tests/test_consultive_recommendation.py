from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from .common import PgAiDevAssistantTestMixin


@tagged('post_install', '-at_install')
class TestConsultiveRecommendation(PgAiDevAssistantTestMixin, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.set_pg_base_url()
        cls.repository = cls.create_repository(name='recommendation_repo')
        cls.branch = cls.create_repository_branch(cls.repository, name='teste', is_default=True)
        cls.project = cls.create_project(cls.repository, name='Projeto Recommendation Test')
        cls.task = cls.create_task(cls.project, name='Task com classificacao')

    def test_mark_gate_ready_requires_recommendation_class(self):
        self.task.write({'pg_ai_consultive_gate_notes': 'Notas minimas registadas.'})

        with self.assertRaises(UserError) as exc:
            self.task.action_mark_ai_consultive_gate_ready()

        self.assertIn('Select the final recommendation class', str(exc.exception))

    def test_additional_module_requires_module_name(self):
        self.set_task_recommendation(
            self.task,
            recommendation_class='additional_module',
            pg_ai_recommended_module=False,
        )
        self.task.write({'pg_ai_consultive_gate_notes': 'Notas minimas registadas.'})

        with self.assertRaises(UserError) as exc:
            self.task.action_mark_ai_consultive_gate_ready()

        self.assertIn('Recommended Odoo Module', str(exc.exception))

    def test_custom_requires_studio_review(self):
        self.set_task_recommendation(
            self.task,
            recommendation_class='custom',
            pg_ai_studio_review=False,
        )
        self.task.write({'pg_ai_consultive_gate_notes': 'Notas minimas registadas.'})

        with self.assertRaises(UserError) as exc:
            self.task.action_mark_ai_consultive_gate_ready()

        self.assertIn('Studio Review', str(exc.exception))

    def test_project_restriction_blocks_disallowed_classification(self):
        self.project.write({'pg_custom_allowed': 'no'})
        self.set_task_recommendation(self.task, recommendation_class='custom')
        self.task.write({'pg_ai_consultive_gate_notes': 'Notas minimas registadas.'})

        with self.assertRaises(UserError) as exc:
            self.task.action_mark_ai_consultive_gate_ready()

        self.assertIn('Custom Allowed', str(exc.exception))
        self.assertIn('not allowed', str(exc.exception))

    def test_recommendation_change_reopens_ready_gate(self):
        self.set_task_recommendation(self.task, recommendation_class='standard')
        self.task.write({'pg_ai_consultive_gate_notes': 'Notas minimas registadas.'})
        self.task.action_mark_ai_consultive_gate_ready()

        self.task.write({'pg_ai_recommendation_justification': 'Justificacao final alterada depois da validacao.'})

        self.assertEqual(self.task.pg_ai_consultive_gate_state, 'pending')
        self.assertFalse(self.task.pg_ai_consultive_gate_checked_by_id)
        self.assertFalse(self.task.pg_ai_consultive_gate_checked_at)
