from odoo.tests import TransactionCase, tagged

from .common import PgAiDevAssistantTestMixin


@tagged('post_install', '-at_install')
class TestChatterSignalPipeline(PgAiDevAssistantTestMixin, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.repository = cls.create_repository(name='chatter_signal_repo')
        cls.project = cls.create_project(cls.repository, name='Projeto Chatter')
        cls.task = cls.create_task(
            cls.project,
            name='Task Chatter',
            description='<p>Integracao com GitHub.</p>',
        )
        cls.note_subtype = cls.env.ref('mail.mt_note')

    @classmethod
    def _create_message(cls, model_name, record_id, body):
        return cls.env['mail.message'].create(
            {
                'model': model_name,
                'res_id': record_id,
                'body': body,
                'message_type': 'comment',
                'subtype_id': cls.note_subtype.id,
                'author_id': cls.env.user.partner_id.id,
            }
        )

    def test_relevant_human_messages_become_structured_signals(self):
        self._create_message(
            'project.project',
            self.project.id,
            '<p>Blocked until the customer shares the production API credentials. Waiting for cliente approval.</p>',
        )
        self._create_message(
            'project.task',
            self.task.id,
            '<p>Approved for production by the cliente. Next step is to configure the GitHub webhook and validate the integration flow.</p>',
        )

        self.project.action_refresh_chatter_signals()

        project_signals = self.env['pg.project.chatter.signal'].search(
            [('project_id', '=', self.project.id), ('source_model', '=', 'project.project')]
        )
        task_signals = self.env['pg.project.chatter.signal'].search(
            [('task_id', '=', self.task.id), ('source_model', '=', 'project.task')]
        )

        self.assertTrue(project_signals.filtered(lambda signal: signal.signal_type == 'blocker'))
        self.assertTrue(task_signals.filtered(lambda signal: signal.signal_type == 'approval'))
        self.assertTrue(task_signals.filtered(lambda signal: signal.signal_type == 'next_step'))
        self.assertTrue(all(signal.signal_state == 'validated' for signal in project_signals | task_signals))

    def test_tracking_noise_is_excluded(self):
        self._create_message('project.task', self.task.id, '<p>Task created</p>')
        self._create_message('project.task', self.task.id, '<p>Stage changed</p>')
        self._create_message('project.task', self.task.id, '<p>Deadline changed from 2026-04-20 to 2026-04-25.</p>')
        self._create_message(
            'project.task',
            self.task.id,
            '<div class="o_mail_notification"><p>Assigned to Project Manager</p></div>',
        )

        self.task.action_refresh_chatter_signals()

        signals = self.env['pg.project.chatter.signal'].search([('task_id', '=', self.task.id)])
        self.assertFalse(signals)

    def test_quoted_replies_and_signatures_are_removed_before_signal_detection(self):
        self._create_message(
            'project.task',
            self.task.id,
            """
                <p>Blocked until the customer shares the production API credentials.</p>
                <p>Best regards,<br/>Project Manager</p>
                <p>On Tue, 2 Apr 2026 at 10:00, Customer wrote:</p>
                <blockquote><p>Approved for production by the customer.</p></blockquote>
            """,
        )

        self.task.action_refresh_chatter_signals()

        signals = self.env['pg.project.chatter.signal'].search([('task_id', '=', self.task.id)])
        blocker = signals.filtered(lambda signal: signal.signal_type == 'blocker')

        self.assertEqual(len(blocker), 1)
        self.assertIn('Blocked until the customer shares the production API credentials.', blocker.summary)
        self.assertNotIn('Best regards', blocker.evidence_excerpt)
        self.assertNotIn('wrote:', blocker.evidence_excerpt)
        self.assertFalse(signals.filtered(lambda signal: signal.signal_type == 'approval'))

    def test_duplicates_and_deleted_messages_become_stale_and_grounding_ignores_them(self):
        message_a = self._create_message(
            'project.task',
            self.task.id,
            '<p>Blocked until the external API credentials are provided by the customer.</p>',
        )
        message_b = self._create_message(
            'project.task',
            self.task.id,
            '<p>Blocked until the external API credentials are provided by the customer.</p>',
        )

        self.task.action_refresh_chatter_signals()

        signals = self.env['pg.project.chatter.signal'].search(
            [('task_id', '=', self.task.id)],
            order='id asc',
        )
        self.assertEqual(len(signals), 2)
        self.assertEqual(len(signals.filtered(lambda signal: signal.signal_state == 'validated')), 1)
        self.assertEqual(len(signals.filtered(lambda signal: signal.signal_state == 'stale')), 1)

        (message_a | message_b).unlink()
        self.task.action_refresh_chatter_signals()

        signals.invalidate_recordset()
        self.assertTrue(all(signal.signal_state == 'stale' for signal in signals))
        grounding = self.task._get_pg_chatter_grounding_service().build_task_grounding(self.task)
        self.assertFalse(grounding['blockers'])

    def test_project_and_task_actions_open_filtered_signal_views(self):
        project_action = self.project.action_view_chatter_signals()
        task_action = self.task.action_view_chatter_signals()

        self.assertEqual(project_action['res_model'], 'pg.project.chatter.signal')
        self.assertIn(('project_id', '=', self.project.id), project_action['domain'])
        self.assertEqual(task_action['res_model'], 'pg.project.chatter.signal')
        self.assertIn(('task_id', '=', self.task.id), task_action['domain'])

    def test_cron_processes_dirty_targets_and_clears_flags(self):
        self._create_message(
            'project.project',
            self.project.id,
            '<p>Decision final: agreed to keep the scope publication on the current branch.</p>',
        )
        self._create_message(
            'project.task',
            self.task.id,
            '<p>Dependency detected: depends on customer validation of the GitHub application.</p>',
        )

        self.assertTrue(self.project.pg_chatter_signals_dirty)
        self.assertTrue(self.task.pg_chatter_signals_dirty)

        self.env['project.project']._cron_refresh_pg_chatter_signals()

        self.project.invalidate_recordset()
        self.task.invalidate_recordset()
        self.assertFalse(self.project.pg_chatter_signals_dirty)
        self.assertFalse(self.task.pg_chatter_signals_dirty)
        self.assertTrue(self.project.pg_chatter_last_scanned_at)
        self.assertTrue(self.task.pg_chatter_last_scanned_at)
        self.assertTrue(
            self.env['pg.project.chatter.signal'].search_count([('project_id', '=', self.project.id)]) >= 2
        )
