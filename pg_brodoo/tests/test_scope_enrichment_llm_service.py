from unittest.mock import patch

from odoo.tests import TransactionCase, tagged

from ..services.project_scope_enrichment_llm_service import ProjectScopeEnrichmentLlmService
from ..services.project_scope_enrichment_service import ProjectScopeEnrichmentService
from .common import PgAiDevAssistantTestMixin


@tagged('post_install', '-at_install')
class TestScopeEnrichmentLlmService(PgAiDevAssistantTestMixin, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.repository = cls.create_repository(name='scope_llm_repo')
        cls.project = cls.create_project(cls.repository, name='Projeto Scope LLM')
        cls.rule_service = ProjectScopeEnrichmentService(cls.env)
        cls.llm_service = ProjectScopeEnrichmentLlmService(cls.env)

    def test_should_attempt_when_rule_based_result_is_weak(self):
        task = self.create_task(
            self.project,
            name='ConfiguraÃ§Ã£o',
            description='<p>Configurar regras de expediÃ§Ã£o por armazÃ©m e transportadora.</p>',
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )
        suggestions = self.rule_service.build_suggestions(task)
        suggestions['pg_scope_enrichment_status'] = 'needs_review'
        suggestions['_llm_eligible'] = True

        with patch.object(ProjectScopeEnrichmentLlmService, '_is_enabled', return_value=True):
            self.assertTrue(self.llm_service.should_attempt(task, suggestions, chatter_context={}))

    def test_should_not_attempt_without_minimum_input(self):
        task = self.create_task(
            self.project,
            name='Teste',
            description=False,
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )
        suggestions = self.rule_service.build_suggestions(task)

        with patch.object(ProjectScopeEnrichmentLlmService, '_is_enabled', return_value=True):
            self.assertFalse(self.llm_service.should_attempt(task, suggestions, chatter_context={}))

    def test_should_not_attempt_for_rule_based_tasks_marked_as_not_llm_eligible(self):
        task = self.create_task(
            self.project,
            name='ReuniÃ£o kick off',
            description='<p>Importar vendas.</p><p>Configurar CRM.</p><p>Rever stocks.</p>',
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )
        suggestions = self.rule_service.build_suggestions(task)
        suggestions['_llm_eligible'] = False

        with patch.object(ProjectScopeEnrichmentLlmService, '_is_enabled', return_value=True):
            self.assertFalse(self.llm_service.should_attempt(task, suggestions, chatter_context={}))

    def test_build_candidate_normalizes_valid_json_payload(self):
        task = self.create_task(
            self.project,
            name='ConfiguraÃ§Ã£o',
            description='<p>Configurar regras de expediÃ§Ã£o por armazÃ©m e transportadora.</p>',
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )
        suggestions = self.rule_service.build_suggestions(task)
        suggestions['pg_scope_enrichment_status'] = 'needs_review'
        suggestions['_llm_eligible'] = True

        response_text = """
        {
          "decision": "suggest",
          "is_atomic": true,
          "should_apply_without_review": true,
          "scope_summary_suggested": "Configurar regras de expediÃ§Ã£o por armazÃ©m e transportadora.",
          "acceptance_criteria_suggested": [
            "Permitir definir a transportadora por armazÃ©m",
            "Aplicar a regra correta no fluxo de expediÃ§Ã£o",
            "Permitir rever a configuraÃ§Ã£o em projeto",
            "Item extra que deve ser ignorado"
          ],
          "quality_rationale": "A descriÃ§Ã£o jÃ¡ suporta um resumo e critÃ©rios testÃ¡veis.",
          "confidence": 84,
          "refusal_reason": ""
        }
        """

        with patch.object(ProjectScopeEnrichmentLlmService, '_is_enabled', return_value=True), patch.object(
            self.llm_service.prompt_service,
            '_response_text',
            return_value=response_text,
        ):
            candidate = self.llm_service.build_candidate(task, suggestions, chatter_context={})

        self.assertEqual(
            candidate['scope_summary_suggested'],
            'Configurar regras de expediÃ§Ã£o por armazÃ©m e transportadora.',
        )
        self.assertEqual(candidate['decision'], 'suggest')
        self.assertEqual(len(candidate['acceptance_criteria_suggested']), 3)
        self.assertEqual(candidate['confidence'], 84)
        self.assertTrue(candidate['should_apply_without_review'])
        self.assertTrue(candidate['quality_rationale'])

    def test_build_candidate_returns_refusal_payload_when_llm_refuses(self):
        task = self.create_task(
            self.project,
            name='Kick Off',
            description='<p>CRM</p><p>Importar encomendas</p><p>Shop floor</p>',
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )
        suggestions = self.rule_service.build_suggestions(task)
        suggestions['pg_scope_enrichment_status'] = 'needs_review'
        suggestions['_llm_eligible'] = True

        response_text = """
        {
          "decision": "refuse",
          "is_atomic": false,
          "should_apply_without_review": false,
          "scope_summary_suggested": "",
          "acceptance_criteria_suggested": [],
          "quality_rationale": "A task mistura vÃ¡rios temas e nÃ£o suporta um Ãºnico scope item.",
          "confidence": 18,
          "refusal_reason": "A task agrega vÃ¡rios temas e deve ficar em revisÃ£o manual."
        }
        """

        with patch.object(ProjectScopeEnrichmentLlmService, '_is_enabled', return_value=True), patch.object(
            self.llm_service.prompt_service,
            '_response_text',
            return_value=response_text,
        ):
            candidate = self.llm_service.build_candidate(task, suggestions, chatter_context={})

        self.assertEqual(candidate['decision'], 'refuse')
        self.assertFalse(candidate['is_atomic'])
        self.assertIn('vÃ¡rios temas', candidate['refusal_reason'])

    def test_build_candidate_returns_false_on_invalid_payload(self):
        task = self.create_task(
            self.project,
            name='ConfiguraÃ§Ã£o',
            description='<p>Configurar regras de expediÃ§Ã£o por armazÃ©m e transportadora.</p>',
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )
        suggestions = self.rule_service.build_suggestions(task)
        suggestions['pg_scope_enrichment_status'] = 'needs_review'
        suggestions['_llm_eligible'] = True

        with patch.object(ProjectScopeEnrichmentLlmService, '_is_enabled', return_value=True), patch.object(
            self.llm_service.prompt_service,
            '_response_text',
            return_value='not-json',
        ):
            self.assertFalse(self.llm_service.build_candidate(task, suggestions, chatter_context={}))
