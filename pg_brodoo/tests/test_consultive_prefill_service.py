from odoo.tests import TransactionCase, tagged

from .common import PgAiDevAssistantTestMixin


@tagged('post_install', '-at_install')
class TestConsultivePrefillService(PgAiDevAssistantTestMixin, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.repository = cls.create_repository(name='consultive_prefill_repo')
        cls.project = cls.create_project(cls.repository, name='Projeto Consultive Prefill')

    def test_generate_consultive_prefill_suggests_custom_for_integration_task(self):
        task = self.create_task(
            self.project,
            name='Integracao GitHub com API externa',
            description='<p>Sincronizar eventos do GitHub com API externa e reprocessar erros de webhook.</p>',
        )

        task.action_generate_consultive_prefill()

        self.assertEqual(task.pg_ai_recommendation_class_suggested, 'custom')
        self.assertGreaterEqual(task.pg_ai_consultive_prefill_confidence, 70)
        self.assertEqual(task.pg_ai_consultive_prefill_status, 'draft')
        self.assertIn('do not show enough standard coverage', task.pg_ai_standard_review_suggested)
        self.assertIn('Studio was reviewed', task.pg_ai_studio_review_suggested)
        self.assertIn('current recommendation is custom', task.pg_ai_recommendation_justification_suggested.lower())

    def test_generate_consultive_prefill_suggests_additional_module_candidate(self):
        task = self.create_task(
            self.project,
            name='Fluxo de aprovacao de despesas',
            description='<p>Gerir aprovacoes multi-etapa para despesas com historico de aprovacao.</p>',
        )

        task.action_generate_consultive_prefill()

        self.assertEqual(task.pg_ai_recommendation_class_suggested, 'additional_module')
        self.assertEqual(task.pg_ai_recommended_module_suggested, 'approvals')
        self.assertEqual(task.pg_ai_consultive_prefill_status, 'draft')
        self.assertIn('module approvals', task.pg_ai_additional_module_review_suggested.lower())

    def test_generate_consultive_prefill_marks_low_confidence_tasks_for_review(self):
        task = self.create_task(
            self.project,
            name='Tarefa teste',
            description=False,
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )

        task.action_generate_consultive_prefill()

        self.assertLess(task.pg_ai_consultive_prefill_confidence, 70)
        self.assertEqual(task.pg_ai_consultive_prefill_status, 'needs_review')
        self.assertIn('Manual review is recommended', task.pg_ai_consultive_prefill_feedback)

    def test_apply_consultive_prefill_fills_only_missing_official_fields(self):
        task = self.create_task(
            self.project,
            name='Fluxo de aprovacao de despesas',
            description='<p>Gerir aprovacoes multi-etapa para despesas com historico de aprovacao.</p>',
            pg_ai_recommendation_justification='Justificacao manual ja existente.',
        )

        task.action_generate_consultive_prefill()
        task.action_apply_consultive_prefill()

        self.assertEqual(task.pg_ai_recommendation_class, 'additional_module')
        self.assertEqual(task.pg_ai_recommended_module, 'approvals')
        self.assertTrue(task.pg_ai_standard_review)
        self.assertTrue(task.pg_ai_additional_module_review)
        self.assertFalse(task.pg_ai_studio_review)
        self.assertEqual(task.pg_ai_recommendation_justification, 'Justificacao manual ja existente.')
        self.assertEqual(task.pg_ai_consultive_prefill_status, 'applied')

    def test_manual_consultive_change_clears_stale_prefill(self):
        task = self.create_task(
            self.project,
            name='Fluxo de aprovacao de despesas',
            description='<p>Gerir aprovacoes multi-etapa para despesas com historico de aprovacao.</p>',
        )

        task.action_generate_consultive_prefill()
        task.write({'pg_ai_standard_review': 'Revisao manual atualizada depois do draft.'})

        self.assertEqual(task.pg_ai_consultive_prefill_status, 'empty')
        self.assertFalse(task.pg_ai_recommendation_class_suggested)
        self.assertFalse(task.pg_ai_recommended_module_suggested)
        self.assertFalse(task.pg_ai_standard_review_suggested)

    def test_generate_consultive_prefill_uses_validated_chatter_grounding(self):
        task = self.create_task(
            self.project,
            name='Ajuste processo',
            description=False,
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )
        self.create_chatter_message(
            'project.task',
            task.id,
            '<p>Final decision: approved scope change to integrate the GitHub webhook with an external API.</p>',
        )

        task.action_refresh_chatter_signals()
        task.action_generate_consultive_prefill()

        self.assertEqual(task.pg_ai_recommendation_class_suggested, 'custom')
        self.assertGreaterEqual(task.pg_ai_consultive_prefill_confidence, 70)
        self.assertEqual(task.pg_ai_consultive_prefill_status, 'draft')
        self.assertIn('Validated chatter signals were used', task.pg_ai_consultive_prefill_feedback)

    def test_generate_consultive_prefill_never_suggests_disallowed_class(self):
        self.project.write({'pg_custom_allowed': 'no'})
        task = self.create_task(
            self.project,
            name='Integracao GitHub com API externa',
            description='<p>Sincronizar eventos do GitHub com API externa e reprocessar erros de webhook.</p>',
        )

        task.action_generate_consultive_prefill()

        self.assertFalse(task.pg_ai_recommendation_class_suggested)
        self.assertFalse(task.pg_ai_recommended_module_suggested)
        self.assertEqual(task.pg_ai_consultive_prefill_status, 'needs_review')
        self.assertIn('Suggested Recommendation Class: none.', task.pg_ai_consultive_prefill_feedback)
        self.assertIn('project restrictions block the strongest automatic recommendation path', task.pg_ai_consultive_prefill_feedback.lower())

    def test_generate_consultive_prefill_falls_back_to_allowed_class_when_supported(self):
        self.project.write({'pg_additional_modules_allowed': 'no'})
        task = self.create_task(
            self.project,
            name='Configurar processo standard de aprovacao',
            description='<p>Configurar processo standard com aprovacoes simples e parametrizacao base.</p>',
            pg_scope_kind='process',
        )

        task.action_generate_consultive_prefill()

        self.assertEqual(task.pg_ai_recommendation_class_suggested, 'standard')
        self.assertFalse(task.pg_ai_recommended_module_suggested)
        self.assertEqual(task.pg_ai_consultive_prefill_status, 'needs_review')
        self.assertIn('falls back to standard', task.pg_ai_consultive_prefill_feedback)

    def test_generate_consultive_prefill_keeps_unknown_restrictions_in_manual_review(self):
        self.project.write({'pg_custom_allowed': 'unknown'})
        task = self.create_task(
            self.project,
            name='Integracao GitHub com API externa',
            description='<p>Sincronizar eventos do GitHub com API externa e reprocessar erros de webhook.</p>',
        )

        task.action_generate_consultive_prefill()

        self.assertEqual(task.pg_ai_recommendation_class_suggested, 'custom')
        self.assertEqual(task.pg_ai_consultive_prefill_status, 'needs_review')
        self.assertIn('restrictions for custom are still unknown', task.pg_ai_consultive_prefill_feedback.lower())
        self.assertIn('Manual review is recommended', task.pg_ai_consultive_prefill_feedback)
