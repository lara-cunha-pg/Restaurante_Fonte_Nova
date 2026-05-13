from unittest.mock import patch

from odoo.tests import TransactionCase, tagged

from ..services.project_scope_enrichment_llm_service import ProjectScopeEnrichmentLlmService
from .common import PgAiDevAssistantTestMixin


@tagged('post_install', '-at_install')
class TestScopeEnrichmentService(PgAiDevAssistantTestMixin, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.repository = cls.create_repository()
        cls.project = cls.create_project(cls.repository)

    def test_generate_scope_enrichment_draft_for_integration_task(self):
        task = self.create_task(
            self.project,
            name='Integracao GitHub com API externa',
            description="""
                <p>Sincronizar o projeto com uma API externa para refletir eventos do GitHub.</p>
                <ul>
                    <li>O utilizador deve conseguir consultar o estado da sincronizacao.</li>
                    <li>O processo deve permitir reprocessar eventos com erro.</li>
                </ul>
            """,
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )

        task.action_generate_scope_enrichment_draft()

        self.assertEqual(task.pg_scope_kind_suggested, 'integration')
        self.assertEqual(task.pg_scope_enrichment_source, 'rule_based')
        self.assertIn('Sincronizar o projeto com uma API externa', task.pg_scope_summary_suggested)
        self.assertIn('O utilizador deve conseguir consultar o estado da sincronizacao', task.pg_acceptance_criteria_suggested_text)
        self.assertGreaterEqual(task.pg_scope_enrichment_confidence, 70)
        self.assertEqual(task.pg_scope_enrichment_status, 'draft')
        self.assertEqual(task.pg_scope_enrichment_generated_by_id, self.env.user)

    def test_generate_scope_enrichment_draft_keeps_rule_based_path_for_strong_task(self):
        task = self.create_task(
            self.project,
            name='Integracao GitHub com API externa',
            description="""
                <p>Sincronizar o projeto com uma API externa para refletir eventos do GitHub.</p>
                <ul>
                    <li>O utilizador deve conseguir consultar o estado da sincronizacao.</li>
                    <li>O processo deve permitir reprocessar eventos com erro.</li>
                </ul>
            """,
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )

        with patch.object(ProjectScopeEnrichmentLlmService, 'should_attempt', return_value=False), patch.object(
            ProjectScopeEnrichmentLlmService,
            'build_candidate',
            side_effect=AssertionError('LLM candidate path should not run for strong rule-based scope drafts.'),
        ):
            task.action_generate_scope_enrichment_draft()

        self.assertEqual(task.pg_scope_enrichment_source, 'rule_based')
        self.assertEqual(task.pg_scope_enrichment_status, 'draft')
        self.assertIn('Sincronizar o projeto com uma API externa', task.pg_scope_summary_suggested)

    def test_generate_scope_enrichment_draft_marks_low_confidence_tasks_for_review(self):
        task = self.create_task(
            self.project,
            name='Tarefa teste',
            description=False,
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )

        task.action_generate_scope_enrichment_draft()

        self.assertEqual(task.pg_scope_kind_suggested, 'requirement')
        self.assertEqual(task.pg_scope_summary_suggested, 'Tarefa teste')
        self.assertIn('O utilizador deve conseguir', task.pg_acceptance_criteria_suggested_text)
        self.assertLess(task.pg_scope_enrichment_confidence, 70)
        self.assertEqual(task.pg_scope_enrichment_status, 'needs_review')
        self.assertIn('review-candidate queue', task.pg_scope_curation_feedback)
        self.assertIn('outside the official scope until a user explicitly applies curated values', task.pg_scope_curation_feedback)

    def test_generate_scope_enrichment_draft_marks_aggregate_rule_based_tasks_for_review(self):
        task = self.create_task(
            self.project,
            name='Kick Off',
            description="""
                <p>CRM</p>
                <p>Importar encomendas de excel</p>
                <p>Shop floor</p>
                <p>Projeto com fases: Gab Tecnico, Compras, ProduÃ§Ã£o, ExpediÃ§Ã£o</p>
            """,
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )

        task.action_generate_scope_enrichment_draft()

        self.assertEqual(task.pg_scope_enrichment_source, 'rule_based')
        self.assertEqual(task.pg_scope_enrichment_status, 'needs_review')
        self.assertIn('agregada', task.pg_scope_enrichment_feedback.lower())

    def test_generate_scope_enrichment_draft_marks_email_followup_task_for_review(self):
        task = self.create_task(
            self.project,
            name='Email Odoo Security',
            description="""
                <p>Boa tarde Bruno</p>
                <p>Recebi o email que anexo, não sei do que se trata.</p>
                <p>Por favor, analisa e dá-me feedback.</p>
                <p>Obrigado</p>
            """,
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )

        with patch.object(ProjectScopeEnrichmentLlmService, 'should_attempt', return_value=False):
            task.action_generate_scope_enrichment_draft()

        self.assertEqual(task.pg_scope_enrichment_source, 'rule_based')
        self.assertEqual(task.pg_scope_enrichment_status, 'needs_review')
        self.assertIn('email', task.pg_scope_enrichment_feedback.lower())

    def test_generate_scope_enrichment_draft_marks_contextual_status_followup_for_review(self):
        task = self.create_task(
            self.project,
            name='Ponto Situação',
            description="""
                <p>Boa tarde Bruno,</p>
                <p>penso já te ter fornecido todos os elementos pendentes da minha parte.</p>
                <p>preciso de perceber quais são os próximos passos e quando pensas começar a testar o processo?</p>
                <p>necessito também do template para a parte comercial.</p>
                <p>Aguardo uma resposta breve da tua parte.</p>
            """,
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )

        with patch.object(ProjectScopeEnrichmentLlmService, 'should_attempt', return_value=False):
            task.action_generate_scope_enrichment_draft()

        self.assertEqual(task.pg_scope_enrichment_source, 'rule_based')
        self.assertEqual(task.pg_scope_enrichment_status, 'needs_review')
        self.assertIn('follow-up', task.pg_scope_enrichment_feedback.lower())

    def test_generate_scope_enrichment_draft_cleans_markup_and_derives_distinct_criteria_from_feature_lines(self):
        task = self.create_task(
            self.project,
            name='InventÃ¡rio',
            description="""
                <p>*ImportaÃ§Ã£o de ficheiro mestre de artigos* via Excel</p>
                <p>ConfiguraÃ§Ã£o e gestÃ£o de 2 armazÃ©ns fÃ­sicos</p>
                <p>IntegraÃ§Ã£o total com Vendas, Compras e ProduÃ§Ã£o</p>
            """,
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )

        with patch.object(ProjectScopeEnrichmentLlmService, 'should_attempt', return_value=False):
            task.action_generate_scope_enrichment_draft()

        self.assertEqual(task.pg_scope_enrichment_source, 'rule_based')
        self.assertEqual(task.pg_scope_enrichment_status, 'draft')
        self.assertNotIn('*', task.pg_scope_summary_suggested)
        self.assertIn('ImportaÃ§Ã£o de ficheiro mestre de artigos via Excel', task.pg_scope_summary_suggested)
        criteria_text = task.pg_acceptance_criteria_suggested_text.lower()
        self.assertIn('o processo deve suportar', criteria_text)
        self.assertIn('configura', criteria_text)
        self.assertIn('armaz', criteria_text)
        self.assertIn('integra', criteria_text)
        self.assertIn('vendas', criteria_text)

    def test_apply_scope_enrichment_draft_fills_only_missing_official_fields(self):
        task = self.create_task(
            self.project,
            name='Relatorio operacional',
            description="""
                <p>Gerar um relatorio operacional para o projeto.</p>
                <p>O utilizador deve conseguir exportar o relatorio em XLSX.</p>
            """,
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )

        task.action_generate_scope_enrichment_draft()
        task.action_apply_scope_enrichment_draft()

        self.assertEqual(task.pg_scope_kind, 'report')
        self.assertIn('Gerar um relatorio operacional', task.pg_scope_summary)
        self.assertIn('O utilizador deve conseguir exportar o relatorio em XLSX', task.pg_acceptance_criteria_text)
        self.assertEqual(task.pg_scope_enrichment_status, 'applied')
        self.assertIn('Scope Kind', task.pg_scope_enrichment_feedback)
        self.assertIn('already applied', task.pg_scope_curation_feedback)

    def test_scope_curation_feedback_warns_when_task_is_outside_approved_scope(self):
        task = self.create_task(
            self.project,
            name='Backlog operacional',
            pg_scope_track='operational_backlog',
        )

        self.assertIn('outside the official layer', task.pg_scope_curation_feedback)

    def test_manual_scope_change_clears_stale_scope_enrichment_draft(self):
        task = self.create_task(
            self.project,
            name='Migracao legado',
            description='<p>Migrar dados legados para o novo modelo.</p>',
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )

        task.action_generate_scope_enrichment_draft()
        task.write({'pg_scope_summary': 'Resumo validado manualmente.'})

        self.assertEqual(task.pg_scope_enrichment_status, 'empty')
        self.assertFalse(task.pg_scope_kind_suggested)
        self.assertFalse(task.pg_scope_summary_suggested)
        self.assertFalse(task.pg_acceptance_criteria_suggested_text)

    def test_generate_scope_enrichment_draft_uses_validated_chatter_hints_as_secondary_context(self):
        task = self.create_task(
            self.project,
            name='Tarefa teste',
            description=False,
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )
        self.create_chatter_message(
            'project.task',
            task.id,
            '<p>Approved scope change: add finance dashboard KPI for weekly operations review.</p>',
        )

        task.action_refresh_chatter_signals()
        task.action_generate_scope_enrichment_draft()

        self.assertEqual(task.pg_scope_kind_suggested, 'report')
        self.assertIn('Approved scope change: add finance dashboard KPI', task.pg_scope_summary_suggested)
        self.assertIn('O ambito aprovado deve refletir', task.pg_acceptance_criteria_suggested_text)
        self.assertIn('Sinais validados do chatter usados apenas como contexto secundario', task.pg_scope_enrichment_feedback)

    def test_generate_scope_enrichment_draft_can_use_llm_assisted_fallback_for_weak_rule_based_result(self):
        task = self.create_task(
            self.project,
            name='ConfiguraÃ§Ã£o',
            description='<p>Configurar regras de expediÃ§Ã£o por armazÃ©m e transportadora.</p>',
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )

        llm_candidate = {
            'decision': 'suggest',
            'scope_summary_suggested': 'Configurar regras de expediÃ§Ã£o por armazÃ©m e transportadora.',
            'acceptance_criteria_suggested': [
                'Permitir definir a transportadora por armazÃ©m',
                'Aplicar a regra correta no fluxo de expediÃ§Ã£o',
            ],
            'quality_rationale': 'A descriÃ§Ã£o suporta um resumo factual mais forte.',
            'confidence': 84,
            'should_apply_without_review': True,
        }

        with patch.object(ProjectScopeEnrichmentLlmService, 'should_attempt', return_value=True), patch.object(
            ProjectScopeEnrichmentLlmService,
            'build_candidate',
            return_value=llm_candidate,
        ):
            task.action_generate_scope_enrichment_draft()

        self.assertEqual(task.pg_scope_enrichment_source, 'llm_assisted')
        self.assertEqual(task.pg_scope_enrichment_status, 'draft')
        self.assertEqual(
            task.pg_scope_summary_suggested,
            'Configurar regras de expediÃ§Ã£o por armazÃ©m e transportadora.',
        )
        self.assertIn('Permitir definir a transportadora por armazÃ©m', task.pg_acceptance_criteria_suggested_text)
        self.assertIn('LLM-assisted scope enrichment applied', task.pg_scope_enrichment_feedback)

    def test_generate_scope_enrichment_draft_marks_rule_based_result_as_llm_fallback_when_candidate_fails(self):
        task = self.create_task(
            self.project,
            name='ConfiguraÃ§Ã£o',
            description='<p>Configurar regras de expediÃ§Ã£o por armazÃ©m e transportadora.</p>',
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )

        with patch.object(ProjectScopeEnrichmentLlmService, 'should_attempt', return_value=True), patch.object(
            ProjectScopeEnrichmentLlmService,
            'build_candidate',
            return_value=False,
        ):
            task.action_generate_scope_enrichment_draft()

        self.assertEqual(task.pg_scope_enrichment_source, 'llm_fallback_rule_based')
        self.assertEqual(task.pg_scope_enrichment_status, 'needs_review')
        self.assertIn('LLM-assisted scope enrichment was attempted', task.pg_scope_enrichment_feedback)
        self.assertIn('revisao manual', task.pg_scope_enrichment_feedback.lower())
        self.assertTrue(task.pg_scope_summary_suggested)

    def test_generate_scope_enrichment_draft_keeps_fallback_when_llm_refuses(self):
        task = self.create_task(
            self.project,
            name='ConfiguraÃ§Ã£o',
            description='<p>Configurar regras de expediÃ§Ã£o por armazÃ©m e transportadora.</p>',
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )

        llm_candidate = {
            'decision': 'refuse',
            'refusal_reason': 'A task agrega vÃ¡rios temas e precisa de revisÃ£o manual.',
            'quality_rationale': 'NÃ£o hÃ¡ atomicidade suficiente.',
            'confidence': 12,
            'is_atomic': False,
            'should_apply_without_review': False,
        }

        with patch.object(ProjectScopeEnrichmentLlmService, 'should_attempt', return_value=True), patch.object(
            ProjectScopeEnrichmentLlmService,
            'build_candidate',
            return_value=llm_candidate,
        ):
            task.action_generate_scope_enrichment_draft()

        self.assertEqual(task.pg_scope_enrichment_source, 'llm_fallback_rule_based')
        self.assertIn('LLM refusal reason', task.pg_scope_enrichment_feedback)
        self.assertEqual(task.pg_scope_enrichment_status, 'needs_review')

    def test_write_normalizes_llm_fallback_to_needs_review(self):
        task = self.create_task(self.project, name='Configuracao fallback')

        task.with_context(pg_skip_scope_enrichment_reset=True).write(
            {
                'pg_scope_enrichment_source': 'llm_fallback_rule_based',
                'pg_scope_enrichment_status': 'draft',
            }
        )

        self.assertEqual(task.pg_scope_enrichment_source, 'llm_fallback_rule_based')
        self.assertEqual(task.pg_scope_enrichment_status, 'needs_review')

    def test_apply_scope_enrichment_draft_accepts_llm_assisted_suggestions(self):
        task = self.create_task(
            self.project,
            name='ConfiguraÃ§Ã£o',
            description='<p>Configurar regras de expediÃ§Ã£o por armazÃ©m e transportadora.</p>',
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )

        llm_candidate = {
            'decision': 'suggest',
            'scope_summary_suggested': 'Configurar regras de expediÃ§Ã£o por armazÃ©m e transportadora.',
            'acceptance_criteria_suggested': [
                'Permitir definir a transportadora por armazÃ©m',
                'Aplicar a regra correta no fluxo de expediÃ§Ã£o',
            ],
            'quality_rationale': 'A descriÃ§Ã£o suporta critÃ©rios factuais aplicÃ¡veis.',
            'confidence': 84,
            'should_apply_without_review': True,
        }

        with patch.object(ProjectScopeEnrichmentLlmService, 'should_attempt', return_value=True), patch.object(
            ProjectScopeEnrichmentLlmService,
            'build_candidate',
            return_value=llm_candidate,
        ):
            task.action_generate_scope_enrichment_draft()

        task.action_apply_scope_enrichment_draft()

        self.assertEqual(task.pg_scope_enrichment_status, 'applied')
        self.assertEqual(task.pg_scope_summary, 'Configurar regras de expediÃ§Ã£o por armazÃ©m e transportadora.')
        self.assertIn('Permitir definir a transportadora por armazÃ©m', task.pg_acceptance_criteria_text)
