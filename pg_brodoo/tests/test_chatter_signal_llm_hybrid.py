from unittest.mock import patch

from odoo.tests import TransactionCase, tagged

from ..services.project_chatter_llm_service import ProjectChatterLlmService
from .common import PgAiDevAssistantTestMixin


@tagged('post_install', '-at_install')
class TestChatterSignalLlmHybrid(PgAiDevAssistantTestMixin, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.repository = cls.create_repository(name='chatter_llm_repo')
        cls.project = cls.create_project(cls.repository, name='Projeto Chatter LLM')
        cls.task = cls.create_task(
            cls.project,
            name='Task Chatter LLM',
            description='<p>Integracao com GitHub.</p>',
        )
        cls.note_subtype = cls.env.ref('mail.mt_note')

    @classmethod
    def _create_message(cls, body):
        return cls.env['mail.message'].create(
            {
                'model': 'project.task',
                'res_id': cls.task.id,
                'body': body,
                'message_type': 'comment',
                'subtype_id': cls.note_subtype.id,
                'author_id': cls.env.user.partner_id.id,
            }
        )

    def test_clear_rule_based_message_skips_llm_hybrid_classification(self):
        self._create_message('<p>Blocked until the customer shares the production credentials.</p>')

        with patch.object(ProjectChatterLlmService, '_is_enabled', return_value=True), patch.object(
            ProjectChatterLlmService,
            '_request_llm_payload',
            side_effect=AssertionError('LLM path should not run for explicit rule-based chatter signals.'),
        ):
            self.task.action_refresh_chatter_signals()

        signal = self.env['pg.project.chatter.signal'].search([('task_id', '=', self.task.id)], limit=1)
        self.assertEqual(signal.engine, 'rule_based')
        self.assertEqual(signal.signal_type, 'blocker')
        self.assertEqual(signal.signal_state, 'validated')

    def test_ambiguous_message_can_be_promoted_by_llm_hybrid(self):
        self._create_message('<p>We can move forward next Tuesday once finance closes the review.</p>')

        payload = {
            'signals': [
                {
                    'signal_type': 'next_step',
                    'confidence': 78,
                    'rationale': 'The message commits to a concrete next move after a review milestone.',
                    'evidence_keywords': ['move forward', 'next Tuesday', 'review'],
                }
            ]
        }

        with patch.object(ProjectChatterLlmService, '_is_enabled', return_value=True), patch.object(
            ProjectChatterLlmService,
            '_request_llm_payload',
            return_value=payload,
        ):
            self.task.action_refresh_chatter_signals()

        signal = self.env['pg.project.chatter.signal'].search(
            [('task_id', '=', self.task.id), ('signal_type', '=', 'next_step')],
            limit=1,
        )
        self.assertTrue(signal)
        self.assertEqual(signal.engine, 'llm_hybrid')
        self.assertEqual(signal.signal_state, 'validated')
        self.assertIn('move forward', signal.validation_feedback)

    def test_invalid_llm_output_is_rejected_and_excluded_from_grounding(self):
        self._create_message('<p>We can move forward next Tuesday once finance closes the review.</p>')

        payload = {
            'signals': [
                {
                    'signal_type': 'next_step',
                    'confidence': 82,
                    'rationale': 'The message implies a next step.',
                    'evidence_keywords': ['production API credentials'],
                }
            ]
        }

        with patch.object(ProjectChatterLlmService, '_is_enabled', return_value=True), patch.object(
            ProjectChatterLlmService,
            '_request_llm_payload',
            return_value=payload,
        ):
            self.task.action_refresh_chatter_signals()

        signal = self.env['pg.project.chatter.signal'].search(
            [('task_id', '=', self.task.id), ('signal_type', '=', 'next_step')],
            limit=1,
        )
        self.assertTrue(signal)
        self.assertEqual(signal.engine, 'llm_hybrid')
        self.assertEqual(signal.signal_state, 'rejected')

        grounding = self.task._get_pg_chatter_grounding_service().build_task_grounding(self.task, include_candidates=True)
        self.assertFalse(grounding['next_steps'])
