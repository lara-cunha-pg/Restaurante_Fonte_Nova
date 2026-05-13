from unittest.mock import patch

from odoo.tests import TransactionCase, tagged

from ..services.project_status_draft_llm_service import ProjectStatusDraftLlmService
from .common import PgAiDevAssistantTestMixin


@tagged('post_install', '-at_install')
class TestStatusDraftLlmService(PgAiDevAssistantTestMixin, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.repository = cls.create_repository(name='status_llm_repo')
        cls.project = cls.create_project(cls.repository, name='Projeto Status LLM')
        cls.llm_service = ProjectStatusDraftLlmService(cls.env)
        cls.deterministic_values = {
            'pg_status_draft_summary': 'Projeto Status LLM em validacao assistida.',
            'pg_status_draft_milestones_text': 'Ambito aprovado consolidado',
            'pg_status_draft_blockers_text': 'Sem bloqueios atuais',
            'pg_status_draft_risks_text': 'Persistem riscos editoriais em casos ambiguos',
            'pg_status_draft_next_steps_text': 'Rever o draft e publicar manualmente',
            'pg_status_draft_pending_decisions_text': 'Confirmar quando publicar o proximo status',
            'pg_status_draft_signal_feedback': 'Validated chatter signals linked to this status draft: 2.',
        }

    def test_should_attempt_requires_explicit_status_redraft_flag(self):
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('pg_openai_api_key', 'sk-test')
        params.set_param('pg_status_draft_llm_redraft_enabled', 'False')

        self.assertFalse(self.llm_service.should_attempt(self.project, self.deterministic_values))

        params.set_param('pg_status_draft_llm_redraft_enabled', 'True')

        self.assertTrue(self.llm_service.should_attempt(self.project, self.deterministic_values))

    def test_build_candidate_normalizes_valid_json_payload(self):
        response_text = """
        {
          "decision": "redraft",
          "status_summary": "Projeto Status LLM segue em validacao assistida com ambito consolidado.",
          "milestones": [
            "Ambito aprovado consolidado",
            "Snapshot operacional pronto para revisao manual"
          ],
          "blockers": [],
          "risks": [
            "Persistem riscos editoriais nos casos contextuais"
          ],
          "next_steps": [
            "Publicar um novo snapshot operacional apos revisao humana"
          ],
          "pending_decisions": [
            "Confirmar o momento da proxima publicacao"
          ],
          "quality_rationale": "O redraft melhora legibilidade sem adicionar factos.",
          "confidence": 82,
          "refusal_reason": ""
        }
        """

        with patch.object(ProjectStatusDraftLlmService, '_is_enabled', return_value=True), patch.object(
            self.llm_service.prompt_service,
            '_response_text',
            return_value=response_text,
        ):
            candidate = self.llm_service.build_candidate(self.project, self.deterministic_values)

        self.assertEqual(candidate['decision'], 'redraft')
        self.assertEqual(candidate['confidence'], 82)
        self.assertEqual(
            candidate['status_summary'],
            'Projeto Status LLM segue em validacao assistida com ambito consolidado.',
        )
        self.assertEqual(candidate['blockers'], [])
        self.assertTrue(candidate['quality_rationale'])

    def test_build_candidate_returns_refusal_payload_when_llm_refuses(self):
        response_text = """
        {
          "decision": "refuse",
          "status_summary": "",
          "milestones": [],
          "blockers": [],
          "risks": [],
          "next_steps": [],
          "pending_decisions": [],
          "quality_rationale": "O input nao melhora o suficiente face ao draft deterministico.",
          "confidence": 18,
          "refusal_reason": "O redraft nao acrescenta valor suficiente."
        }
        """

        with patch.object(ProjectStatusDraftLlmService, '_is_enabled', return_value=True), patch.object(
            self.llm_service.prompt_service,
            '_response_text',
            return_value=response_text,
        ):
            candidate = self.llm_service.build_candidate(self.project, self.deterministic_values)

        self.assertEqual(candidate['decision'], 'refuse')
        self.assertEqual(candidate['confidence'], 18)
        self.assertIn('acrescenta valor', candidate['refusal_reason'])

    def test_build_candidate_returns_false_on_invalid_payload(self):
        with patch.object(ProjectStatusDraftLlmService, '_is_enabled', return_value=True), patch.object(
            self.llm_service.prompt_service,
            '_response_text',
            return_value='not-json',
        ):
            self.assertFalse(self.llm_service.build_candidate(self.project, self.deterministic_values))
