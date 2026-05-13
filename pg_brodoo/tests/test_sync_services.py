from unittest.mock import Mock, patch

from odoo.tests import TransactionCase, tagged

from ..services.project_budget_sync_service import ProjectBudgetSyncService
from ..services.project_deliveries_sync_service import ProjectDeliveriesSyncService
from ..services.project_plan_sync_service import ProjectPlanSyncService
from ..services.project_scope_sync_service import ProjectScopeSyncService
from ..services.project_decisions_sync_service import ProjectDecisionsSyncService
from ..services.project_mirror_sync_service import ProjectMirrorSyncService
from ..services.project_requirements_sync_service import ProjectRequirementsSyncService
from ..services.project_risks_sync_service import ProjectRisksSyncService
from ..services.project_status_sync_service import ProjectStatusSyncService
from ..services.project_sync_quality_review_service import ProjectSyncQualityReviewService
from .common import PgAiDevAssistantTestMixin


@tagged('post_install', '-at_install')
class TestSyncServices(PgAiDevAssistantTestMixin, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.set_pg_base_url()
        cls.repository = cls.create_repository(name='service_repo')
        cls.project = cls.create_project(
            cls.repository,
            name='Projeto Service Test',
            allow_milestones=True,
            pg_decisions_sync_enabled=True,
            pg_requirements_sync_enabled=True,
            pg_risks_sync_enabled=True,
            pg_deliveries_sync_enabled=True,
            pg_project_plan_sync_enabled=True,
            pg_budget_sync_enabled=True,
        )
        cls.create_scope_line(cls.project, 'acceptance_criteria', 'Publicar snapshot tecnico.')
        cls.task = cls.create_task(cls.project, name='Tarefa service')

    def setUp(self):
        super().setUp()
        self.env['ir.config_parameter'].sudo().set_param('pg_sync_quality_review_enabled', '1')

    def test_scope_service_processes_and_skips_unchanged_payload(self):
        service = ProjectScopeSyncService(self.env)
        service.publisher.publish_project_scope_snapshot = Mock(
            return_value={
                'content': {'sha': 'scope-file-sha'},
                'commit': {'sha': 'scope-commit-sha'},
            }
        )

        run = service.queue_project(
            self.project,
            trigger_type='task_write',
            trigger_model='project.task',
            trigger_record_id=self.task.id,
        )
        self.assertTrue(run)
        self.assertEqual(run.status, 'queued')

        processed_run = service.process_run(run)
        self.assertEqual(processed_run.status, 'done')
        self.assertEqual(processed_run.published_commit_sha, 'scope-commit-sha')
        self.assertEqual(self.project.pg_scope_sync_last_status, 'done')
        service.publisher.publish_project_scope_snapshot.assert_called_once()

        service.publisher.publish_project_scope_snapshot.reset_mock()
        second_run = service.queue_project(
            self.project,
            trigger_type='task_write',
            trigger_model='project.task',
            trigger_record_id=self.task.id,
        )
        processed_second_run = service.process_run(second_run)
        self.assertEqual(processed_second_run.status, 'skipped')
        service.publisher.publish_project_scope_snapshot.assert_not_called()

    def test_mirror_service_processes_and_skips_unchanged_payload(self):
        service = ProjectMirrorSyncService(self.env)
        service.publisher.publish_project_mirror_payload = Mock(
            return_value={
                'content': {'sha': 'mirror-project-file-sha'},
                'commit': {'sha': 'mirror-project-commit-sha'},
            }
        )
        service.publisher.publish_planning_mirror_payload = Mock(
            return_value={
                'content': {'sha': 'mirror-planning-file-sha'},
                'commit': {'sha': 'mirror-planning-commit-sha'},
            }
        )
        service.publisher.publish_tasks_mirror_payload = Mock(
            return_value={
                'content': {'sha': 'mirror-tasks-file-sha'},
                'commit': {'sha': 'mirror-tasks-commit-sha'},
            }
        )
        service.publisher.publish_chatter_mirror_payload = Mock(
            return_value={
                'content': {'sha': 'mirror-chatter-file-sha'},
                'commit': {'sha': 'mirror-chatter-commit-sha'},
            }
        )
        service.publisher.publish_attachments_mirror_payload = Mock(
            return_value={
                'content': {'sha': 'mirror-attachments-file-sha'},
                'commit': {'sha': 'mirror-attachments-commit-sha'},
            }
        )
        service.publisher.publish_project_context = Mock(
            return_value={
                'content': {'sha': 'mirror-context-file-sha'},
                'commit': {'sha': 'mirror-context-commit-sha'},
            }
        )
        service.publisher.github_service.get_repository_file_text = Mock(return_value='')
        service.publisher.append_project_mirror_history_event = Mock(
            return_value={
                'content': {'sha': 'mirror-history-file-sha'},
                'commit': {'sha': 'mirror-history-commit-sha'},
            }
        )

        run = service.queue_project(
            self.project,
            trigger_type='project_write',
            trigger_model='project.project',
            trigger_record_id=self.project.id,
        )
        self.assertTrue(run)
        self.assertEqual(run.status, 'queued')

        processed_run = service.process_run(run)
        self.assertEqual(processed_run.status, 'done')
        self.assertEqual(processed_run.published_commit_sha, 'mirror-context-commit-sha')
        self.assertEqual(self.project.pg_mirror_sync_last_status, 'done')
        self.assertTrue(self.project.pg_mirror_sync_last_payload_hash)
        service.publisher.publish_project_mirror_payload.assert_called_once()
        service.publisher.publish_planning_mirror_payload.assert_called_once()
        service.publisher.publish_tasks_mirror_payload.assert_called_once()
        service.publisher.publish_chatter_mirror_payload.assert_called_once()
        service.publisher.publish_attachments_mirror_payload.assert_called_once()
        service.publisher.append_project_mirror_history_event.assert_called_once()
        service.publisher.publish_project_context.assert_called_once()

        service.publisher.publish_project_mirror_payload.reset_mock()
        service.publisher.publish_planning_mirror_payload.reset_mock()
        service.publisher.publish_tasks_mirror_payload.reset_mock()
        service.publisher.publish_chatter_mirror_payload.reset_mock()
        service.publisher.publish_attachments_mirror_payload.reset_mock()
        service.publisher.append_project_mirror_history_event.reset_mock()
        service.publisher.publish_project_context.reset_mock()
        second_run = service.queue_project(
            self.project,
            trigger_type='project_write',
            trigger_model='project.project',
            trigger_record_id=self.project.id,
        )
        processed_second_run = service.process_run(second_run)
        self.assertEqual(processed_second_run.status, 'skipped')
        service.publisher.publish_project_mirror_payload.assert_not_called()
        service.publisher.publish_planning_mirror_payload.assert_not_called()
        service.publisher.publish_tasks_mirror_payload.assert_not_called()
        service.publisher.publish_chatter_mirror_payload.assert_not_called()
        service.publisher.publish_attachments_mirror_payload.assert_not_called()
        service.publisher.append_project_mirror_history_event.assert_not_called()
        service.publisher.publish_project_context.assert_not_called()

    def test_mirror_service_rebuilds_context_when_snapshot_is_unchanged(self):
        service = ProjectMirrorSyncService(self.env)
        service.publisher.publish_project_mirror_payload = Mock(
            return_value={
                'content': {'sha': 'mirror-project-file-sha'},
                'commit': {'sha': 'mirror-project-commit-sha'},
            }
        )
        service.publisher.publish_planning_mirror_payload = Mock(
            return_value={
                'content': {'sha': 'mirror-planning-file-sha'},
                'commit': {'sha': 'mirror-planning-commit-sha'},
            }
        )
        service.publisher.publish_tasks_mirror_payload = Mock(
            return_value={
                'content': {'sha': 'mirror-tasks-file-sha'},
                'commit': {'sha': 'mirror-tasks-commit-sha'},
            }
        )
        service.publisher.publish_chatter_mirror_payload = Mock(
            return_value={
                'content': {'sha': 'mirror-chatter-file-sha'},
                'commit': {'sha': 'mirror-chatter-commit-sha'},
            }
        )
        service.publisher.publish_attachments_mirror_payload = Mock(
            return_value={
                'content': {'sha': 'mirror-attachments-file-sha'},
                'commit': {'sha': 'mirror-attachments-commit-sha'},
            }
        )
        service.publisher.publish_project_context = Mock(
            return_value={
                'content': {'sha': 'mirror-context-file-sha'},
                'commit': {'sha': 'mirror-context-commit-sha'},
            }
        )
        service.publisher.github_service.get_repository_file_text = Mock(return_value='')
        service.publisher.append_project_mirror_history_event = Mock(
            return_value={
                'content': {'sha': 'mirror-history-file-sha'},
                'commit': {'sha': 'mirror-history-commit-sha'},
            }
        )

        initial_run = service.queue_project(
            self.project,
            trigger_type='manual',
            trigger_model='project.project',
            trigger_record_id=self.project.id,
        )
        service.process_run(initial_run)

        service.publisher.publish_project_mirror_payload.reset_mock()
        service.publisher.publish_planning_mirror_payload.reset_mock()
        service.publisher.publish_tasks_mirror_payload.reset_mock()
        service.publisher.publish_chatter_mirror_payload.reset_mock()
        service.publisher.publish_attachments_mirror_payload.reset_mock()
        service.publisher.append_project_mirror_history_event.reset_mock()
        service.publisher.publish_project_context.reset_mock()

        rebuild_run = service.queue_project(
            self.project,
            trigger_type='scheduled_rebuild',
            trigger_model='project.project',
            trigger_record_id=self.project.id,
        )
        processed_rebuild_run = service.process_run(rebuild_run)

        self.assertEqual(processed_rebuild_run.status, 'done')
        self.assertEqual(processed_rebuild_run.message, 'Project context regenerated successfully.')
        service.publisher.publish_project_mirror_payload.assert_not_called()
        service.publisher.publish_planning_mirror_payload.assert_not_called()
        service.publisher.publish_tasks_mirror_payload.assert_not_called()
        service.publisher.publish_chatter_mirror_payload.assert_not_called()
        service.publisher.publish_attachments_mirror_payload.assert_not_called()
        service.publisher.append_project_mirror_history_event.assert_not_called()
        service.publisher.publish_project_context.assert_called_once()

    def test_mirror_service_persists_quality_warnings_without_blocking_publish(self):
        milestone = self.create_project_milestone(
            self.project,
            name='Go Live warning',
            deadline='2026-04-01',
            pg_plan_owner_id=False,
            sequence=1,
        )
        self.assertTrue(milestone)

        service = ProjectMirrorSyncService(self.env)
        service.publisher.publish_project_mirror_payload = Mock(
            return_value={
                'content': {'sha': 'mirror-project-file-sha'},
                'commit': {'sha': 'mirror-project-commit-sha'},
            }
        )
        service.publisher.publish_planning_mirror_payload = Mock(
            return_value={
                'content': {'sha': 'mirror-planning-file-sha'},
                'commit': {'sha': 'mirror-planning-commit-sha'},
            }
        )
        service.publisher.publish_tasks_mirror_payload = Mock(
            return_value={
                'content': {'sha': 'mirror-tasks-file-sha'},
                'commit': {'sha': 'mirror-tasks-commit-sha'},
            }
        )
        service.publisher.publish_chatter_mirror_payload = Mock(
            return_value={
                'content': {'sha': 'mirror-chatter-file-sha'},
                'commit': {'sha': 'mirror-chatter-commit-sha'},
            }
        )
        service.publisher.publish_attachments_mirror_payload = Mock(
            return_value={
                'content': {'sha': 'mirror-attachments-file-sha'},
                'commit': {'sha': 'mirror-attachments-commit-sha'},
            }
        )
        service.publisher.publish_project_context = Mock(
            return_value={
                'content': {'sha': 'mirror-context-file-sha'},
                'commit': {'sha': 'mirror-context-commit-sha'},
            }
        )
        service.publisher.github_service.get_repository_file_text = Mock(return_value='')
        service.publisher.append_project_mirror_history_event = Mock(
            return_value={
                'content': {'sha': 'mirror-history-file-sha'},
                'commit': {'sha': 'mirror-history-commit-sha'},
            }
        )

        run = service.queue_project(
            self.project,
            trigger_type='manual',
            trigger_model='project.project',
            trigger_record_id=self.project.id,
        )
        processed_run = service.process_run(run)

        self.assertEqual(processed_run.status, 'done')
        self.assertEqual(processed_run.quality_review_status, 'warning')
        self.assertEqual(processed_run.quality_review_warning_count, 3)
        self.assertIn('Mirror quality review status: warning.', processed_run.quality_review_feedback)
        self.assertEqual(self.project.pg_mirror_sync_quality_review_status, 'warning')
        self.assertEqual(self.project.pg_mirror_sync_quality_warning_count, 3)
        self.assertIn('next_milestone_target_in_past', self.project.pg_mirror_sync_quality_review_feedback)
        self.assertIn('quality warnings', processed_run.message)
        service.publisher.publish_project_mirror_payload.assert_called_once()

    def test_mirror_service_mirrors_all_tasks_in_included_scope(self):
        self.create_task(
            self.project,
            name='Formacao CRM',
            description=False,
            pg_scope_summary=False,
        )
        self.create_task(
            self.project,
            name='Kick Off',
            description='<p>Fico a aguardar feedback da vossa parte.</p>',
            pg_scope_summary=False,
        )

        service = ProjectMirrorSyncService(self.env)
        service.publisher.publish_project_mirror_payload = Mock(
            return_value={
                'content': {'sha': 'mirror-project-file-sha'},
                'commit': {'sha': 'mirror-project-commit-sha'},
            }
        )
        service.publisher.publish_planning_mirror_payload = Mock(
            return_value={
                'content': {'sha': 'mirror-planning-file-sha'},
                'commit': {'sha': 'mirror-planning-commit-sha'},
            }
        )
        service.publisher.publish_tasks_mirror_payload = Mock(
            return_value={
                'content': {'sha': 'mirror-tasks-file-sha'},
                'commit': {'sha': 'mirror-tasks-commit-sha'},
            }
        )
        service.publisher.publish_chatter_mirror_payload = Mock(
            return_value={
                'content': {'sha': 'mirror-chatter-file-sha'},
                'commit': {'sha': 'mirror-chatter-commit-sha'},
            }
        )
        service.publisher.publish_attachments_mirror_payload = Mock(
            return_value={
                'content': {'sha': 'mirror-attachments-file-sha'},
                'commit': {'sha': 'mirror-attachments-commit-sha'},
            }
        )
        service.publisher.publish_project_context = Mock(
            return_value={
                'content': {'sha': 'mirror-context-file-sha'},
                'commit': {'sha': 'mirror-context-commit-sha'},
            }
        )
        service.publisher.github_service.get_repository_file_text = Mock(return_value='')
        service.publisher.append_project_mirror_history_event = Mock(
            return_value={
                'content': {'sha': 'mirror-history-file-sha'},
                'commit': {'sha': 'mirror-history-commit-sha'},
            }
        )

        run = service.queue_project(
            self.project,
            trigger_type='manual',
            trigger_model='project.project',
            trigger_record_id=self.project.id,
        )
        processed_run = service.process_run(run)
        published_payload = service.publisher.publish_project_mirror_payload.call_args.args[2]

        self.assertEqual(processed_run.status, 'done')
        self.assertEqual(processed_run.included_scope_count, 3)
        self.assertEqual(processed_run.factual_scope_backlog_count, 0)
        self.assertEqual(processed_run.excluded_noise_count, 0)
        self.assertIn('Ambito curado pronto no espelho: 3 item(s).', processed_run.scope_signal_feedback)
        self.assertEqual(self.project.pg_mirror_included_scope_count, 3)
        self.assertEqual(self.project.pg_mirror_scope_backlog_count, 0)
        self.assertEqual(self.project.pg_mirror_excluded_noise_count, 0)
        self.assertIn('Resumo funcional de teste.', published_payload['project']['included_scope'])
        self.assertIn('Formacao CRM', published_payload['project']['included_scope'])
        service.publisher.publish_project_mirror_payload.assert_called_once()

    def test_mirror_service_always_publishes_despite_blocking_quality_review(self):
        service = ProjectMirrorSyncService(self.env)
        service.publisher.publish_project_mirror_payload = Mock(
            return_value={
                'content': {'sha': 'mirror-project-file-sha'},
                'commit': {'sha': 'mirror-project-commit-sha'},
            }
        )
        service.publisher.publish_planning_mirror_payload = Mock(
            return_value={
                'content': {'sha': 'mirror-planning-file-sha'},
                'commit': {'sha': 'mirror-planning-commit-sha'},
            }
        )
        service.publisher.publish_tasks_mirror_payload = Mock(
            return_value={
                'content': {'sha': 'mirror-tasks-file-sha'},
                'commit': {'sha': 'mirror-tasks-commit-sha'},
            }
        )
        service.publisher.publish_chatter_mirror_payload = Mock(
            return_value={
                'content': {'sha': 'mirror-chatter-file-sha'},
                'commit': {'sha': 'mirror-chatter-commit-sha'},
            }
        )
        service.publisher.publish_attachments_mirror_payload = Mock(
            return_value={
                'content': {'sha': 'mirror-attachments-file-sha'},
                'commit': {'sha': 'mirror-attachments-commit-sha'},
            }
        )
        service.publisher.publish_project_context = Mock(
            return_value={
                'content': {'sha': 'mirror-context-file-sha'},
                'commit': {'sha': 'mirror-context-commit-sha'},
            }
        )
        service.publisher.github_service.get_repository_file_text = Mock(return_value='')
        service.publisher.append_project_mirror_history_event = Mock(
            return_value={
                'content': {'sha': 'mirror-history-file-sha'},
                'commit': {'sha': 'mirror-history-commit-sha'},
            }
        )

        blocking_review = {
            'enabled': True,
            'summary_status': 'blocking',
            'publishability': 'not_eligible',
            'blocking_findings': [
                {
                    'bucket': 'essential_project_context_missing',
                    'severity': 'blocking',
                    'publishability': 'not_eligible',
                    'message': 'Mirror payload is missing the minimum factual project context required for publication.',
                    'evidence': '[project core is empty]',
                }
            ],
            'warning_findings': [],
            'observations': [],
            'bucket_reviews': [],
            'quality_score': 0,
            'feedback': 'Mirror quality review status: blocking.',
        }

        run = service.queue_project(
            self.project,
            trigger_type='manual',
            trigger_model='project.project',
            trigger_record_id=self.project.id,
        )
        with patch.object(
            ProjectSyncQualityReviewService,
            'review_mirror_payload',
            autospec=True,
            return_value=blocking_review,
        ):
            processed_run = service.process_run(run)

        self.assertEqual(processed_run.status, 'done')
        self.assertEqual(processed_run.quality_review_status, 'blocking')
        self.assertEqual(processed_run.quality_review_blocking_count, 1)
        self.assertEqual(processed_run.quality_review_feedback, 'Mirror quality review status: blocking.')
        self.assertEqual(self.project.pg_mirror_sync_last_status, 'done')
        self.assertEqual(self.project.pg_mirror_sync_quality_review_status, 'blocking')
        self.assertEqual(self.project.pg_mirror_sync_quality_review_feedback, 'Mirror quality review status: blocking.')
        service.publisher.publish_project_mirror_payload.assert_called_once()

    def test_mirror_service_processes_sparse_brownfield_project_without_curated_project_core(self):
        project = self.create_project(
            self.repository,
            name='Projeto Brownfield Mirror',
            pg_business_goal=False,
            pg_repository_summary=False,
            pg_current_request=False,
            pg_current_process=False,
            pg_problem_or_need=False,
            pg_business_impact=False,
            pg_status_summary=False,
        )
        self.create_task(
            project,
            name='Levantar requisitos do projeto',
            description='<p>Levantar requisitos atuais com a equipa do cliente.</p>',
            pg_scope_track='operational_backlog',
            pg_scope_summary=False,
        )

        service = ProjectMirrorSyncService(self.env)
        service.publisher.publish_project_mirror_payload = Mock(
            return_value={
                'content': {'sha': 'mirror-project-file-sha'},
                'commit': {'sha': 'mirror-project-commit-sha'},
            }
        )
        service.publisher.publish_planning_mirror_payload = Mock(
            return_value={
                'content': {'sha': 'mirror-planning-file-sha'},
                'commit': {'sha': 'mirror-planning-commit-sha'},
            }
        )
        service.publisher.publish_tasks_mirror_payload = Mock(
            return_value={
                'content': {'sha': 'mirror-tasks-file-sha'},
                'commit': {'sha': 'mirror-tasks-commit-sha'},
            }
        )
        service.publisher.publish_chatter_mirror_payload = Mock(
            return_value={
                'content': {'sha': 'mirror-chatter-file-sha'},
                'commit': {'sha': 'mirror-chatter-commit-sha'},
            }
        )
        service.publisher.publish_attachments_mirror_payload = Mock(
            return_value={
                'content': {'sha': 'mirror-attachments-file-sha'},
                'commit': {'sha': 'mirror-attachments-commit-sha'},
            }
        )
        service.publisher.publish_project_context = Mock(
            return_value={
                'content': {'sha': 'mirror-context-file-sha'},
                'commit': {'sha': 'mirror-context-commit-sha'},
            }
        )
        service.publisher.github_service.get_repository_file_text = Mock(return_value='')
        service.publisher.append_project_mirror_history_event = Mock(
            return_value={
                'content': {'sha': 'mirror-history-file-sha'},
                'commit': {'sha': 'mirror-history-commit-sha'},
            }
        )

        run = service.queue_project(
            project,
            trigger_type='manual',
            trigger_model='project.project',
            trigger_record_id=project.id,
        )
        processed_run = service.process_run(run)

        self.assertEqual(processed_run.status, 'done')
        self.assertEqual(processed_run.quality_review_status, 'ok')
        self.assertEqual(processed_run.quality_review_blocking_count, 0)
        self.assertIn('Mirror quality review status: ok', processed_run.quality_review_feedback)
        self.assertEqual(project.pg_mirror_sync_last_status, 'done')
        service.publisher.publish_project_mirror_payload.assert_called_once()

    def test_task_write_queues_project_mirror_sync_run(self):
        self.task.write({'name': 'Tarefa service atualizada'})

        run = self.env['pg.project.mirror.sync.run'].search(
            [('project_id', '=', self.project.id)],
            order='create_date desc, id desc',
            limit=1,
        )
        self.assertTrue(run)
        self.assertEqual(run.status, 'queued')
        self.assertEqual(run.trigger_type, 'task_write')
        self.assertEqual(run.trigger_model, 'project.task')
        self.assertEqual(run.trigger_record_id, self.task.id)

    def test_milestone_write_queues_project_mirror_sync_run(self):
        milestone = self.create_project_milestone(
            self.project,
            name='Marco do espelho',
            pg_plan_status='planned',
        )
        self.env['pg.project.mirror.sync.run'].search([('project_id', '=', self.project.id)]).unlink()

        milestone.write({'pg_plan_dependency_refs': 'Aprovar template'})

        run = self.env['pg.project.mirror.sync.run'].search(
            [('project_id', '=', self.project.id)],
            order='create_date desc, id desc',
            limit=1,
        )
        self.assertTrue(run)
        self.assertEqual(run.status, 'queued')
        self.assertEqual(run.trigger_type, 'milestone_write')
        self.assertEqual(run.trigger_model, 'project.milestone')
        self.assertEqual(run.trigger_record_id, milestone.id)

    def test_message_write_queues_project_mirror_sync_run(self):
        message = self.create_chatter_message(
            'project.task',
            self.task.id,
            '<p>Mensagem inicial para o mirror.</p>',
            subtype_xmlid='mail.mt_comment',
        )
        self.env['pg.project.mirror.sync.run'].search([('project_id', '=', self.project.id)]).unlink()

        message.write({'body': '<p>Mensagem atualizada para o mirror.</p>'})

        run = self.env['pg.project.mirror.sync.run'].search(
            [('project_id', '=', self.project.id)],
            order='create_date desc, id desc',
            limit=1,
        )
        self.assertTrue(run)
        self.assertEqual(run.status, 'queued')
        self.assertEqual(run.trigger_type, 'message_write')
        self.assertEqual(run.trigger_model, 'mail.message')

    def test_attachment_write_queues_project_mirror_sync_run(self):
        attachment = self.create_attachment(self.task, name='mirror_sync.txt')
        self.env['pg.project.mirror.sync.run'].search([('project_id', '=', self.project.id)]).unlink()

        attachment.write({'name': 'mirror_sync_v2.txt'})

        run = self.env['pg.project.mirror.sync.run'].search(
            [('project_id', '=', self.project.id)],
            order='create_date desc, id desc',
            limit=1,
        )
        self.assertTrue(run)
        self.assertEqual(run.status, 'queued')
        self.assertEqual(run.trigger_type, 'attachment_write')
        self.assertEqual(run.trigger_model, 'ir.attachment')

    def test_action_open_pg_onboarding_targets_current_project(self):
        action = self.project.action_open_pg_onboarding()

        self.assertEqual(action['res_model'], 'pg.ai.onboarding.wizard')
        self.assertEqual(action['target'], 'new')
        self.assertEqual(action['context']['active_model'], 'project.project')
        self.assertEqual(action['context']['active_id'], self.project.id)
        self.assertEqual(action['context']['default_project_id'], self.project.id)

    def test_action_view_mirror_sync_runs_filters_current_project(self):
        action = self.project.action_view_mirror_sync_runs()

        self.assertEqual(action['res_model'], 'pg.project.mirror.sync.run')
        self.assertEqual(action['domain'], [('project_id', '=', self.project.id)])
        self.assertEqual(action['context']['default_project_id'], self.project.id)

    def test_action_sync_project_mirror_now_uses_manual_trigger(self):
        run = self.env['pg.project.mirror.sync.run'].create(
            {
                'project_id': self.project.id,
                'status': 'queued',
                'trigger_type': 'manual',
                'trigger_model': 'project.project',
                'trigger_record_id': self.project.id,
            }
        )
        with patch.object(ProjectMirrorSyncService, 'queue_project', autospec=True, return_value=run) as queue_mock:
            with patch.object(ProjectMirrorSyncService, 'process_run', autospec=True, return_value=run) as process_mock:
                self.project.action_sync_project_mirror_now()

        self.assertEqual(queue_mock.call_args.kwargs['trigger_type'], 'manual')
        self.assertEqual(queue_mock.call_args.kwargs['trigger_model'], 'project.project')
        self.assertEqual(queue_mock.call_args.kwargs['trigger_record_id'], self.project.id)
        process_mock.assert_called_once()

    def test_action_rebuild_project_context_uses_rebuild_trigger(self):
        run = self.env['pg.project.mirror.sync.run'].create(
            {
                'project_id': self.project.id,
                'status': 'queued',
                'trigger_type': 'scheduled_rebuild',
                'trigger_model': 'project.project',
                'trigger_record_id': self.project.id,
            }
        )
        with patch.object(ProjectMirrorSyncService, 'queue_project', autospec=True, return_value=run) as queue_mock:
            with patch.object(ProjectMirrorSyncService, 'process_run', autospec=True, return_value=run) as process_mock:
                self.project.action_rebuild_project_context()

        self.assertEqual(queue_mock.call_args.kwargs['trigger_type'], 'scheduled_rebuild')
        self.assertEqual(queue_mock.call_args.kwargs['trigger_model'], 'project.project')
        self.assertEqual(queue_mock.call_args.kwargs['trigger_record_id'], self.project.id)
        process_mock.assert_called_once()

    def test_legacy_project_migration_bootstraps_new_mirror_model(self):
        partner = self.env['res.partner'].create({'name': 'Cliente Legacy'})
        legacy_project = self.create_project(
            self.repository,
            name='Projeto Legacy',
            partner_id=partner.id,
            description='<p>Projeto legacy para migracao do espelho.</p>',
            pg_scope_sync_enabled=False,
            pg_status_sync_enabled=False,
            pg_decisions_sync_enabled=True,
            pg_repository_summary=False,
            pg_business_goal=False,
            pg_onboarding_scope_included_text=False,
            pg_onboarding_scope_excluded_text=False,
            pg_onboarding_deliverables_text=False,
            pg_onboarding_assumptions_text=False,
            pg_onboarding_stakeholders_text=False,
            pg_onboarding_milestones_text=False,
            pg_onboarding_last_status='never',
        )
        self.create_project_milestone(legacy_project, name='Go Live Legacy')
        self.create_task(
            legacy_project,
            name='Importar configuracao legacy',
            pg_scope_summary='Importar configuracao do template legado.',
        )
        self.create_task(
            legacy_project,
            name='Agendamento',
            description='<p>Agendar arranque do Odoo com a equipa comercial.</p>',
            pg_scope_summary=(
                'Bom dia Bruno, Hoje de tarde sempre passas por ca para dar seguimento ao arranque do Odoo? '
                'Com os melhores cumprimentos, Rui Ribeiro Image [7] ANCORA VIP INDUSTRY, LDA. '
                'Tel. +351 255 878 612'
            ),
        )
        self.create_task(
            legacy_project,
            name='Categorias',
            description='<p>[PONTO POR VALIDAR]</p>',
            pg_scope_summary='[PONTO POR VALIDAR]',
        )
        self.create_task(
            legacy_project,
            name='Kick Off',
            description='<p>Agendar reuniao de arranque com o cliente e recolher dados iniciais.</p>',
            pg_scope_summary=(
                'Conforme conversado na reuniao na AncoraVip envio em anexo a informacao solicitada '
                'para darmos inicio ao arranque da implementacao do Odoo.'
            ),
        )
        self.create_task(
            legacy_project,
            name='Importacao de contactos',
            description='<p>Importar contactos de clientes e fornecedores para preparar a operacao inicial.</p>',
            pg_scope_summary=(
                'Rui Ribeiro Image ANCORA VIP INDUSTRY, LDA. Unidade2 Rua do Bairro da Boavista Freamunde '
                '( Mail None geral@ancoravip.pt None None Image None Image None Image Image '
                'mailto:geral@ancoravip.pt'
            ),
        )
        self.create_task(
            legacy_project,
            name='Acessos iniciais',
            description='<p>Criar utilizadores; Configurar permissoes; Validar acessos</p>',
            pg_scope_summary=False,
        )
        self.create_task(
            legacy_project,
            name='Backlog composto',
            description=(
                '<p>Testar e Corrigir importacao de encomendas em curso Alterar arrastar tarefa para producao '
                'Alterar campo de mapeamento de secao para mapeamento obrigatorio</p>'
            ),
            pg_scope_summary=False,
        )
        self.create_task(
            legacy_project,
            name='Rui Ribeiro',
            description='<p>Fico a aguardar feedback da vossa parte.</p>',
            pg_scope_summary=False,
        )
        self.create_task(
            legacy_project,
            name='Fora de ambito legacy',
            pg_scope_state='excluded',
            pg_scope_summary='Aquisição de hardware fora de âmbito.',
        )

        run = self.env['pg.project.mirror.sync.run'].create(
            {
                'project_id': legacy_project.id,
                'status': 'queued',
                'trigger_type': 'legacy_migration',
                'trigger_model': 'project.project',
                'trigger_record_id': legacy_project.id,
            }
        )
        with patch.object(ProjectMirrorSyncService, 'queue_project', autospec=True, return_value=run) as queue_mock:
            with patch.object(ProjectMirrorSyncService, 'process_run', autospec=True, return_value=run) as process_mock:
                legacy_project.action_migrate_legacy_project_mirror()

        migrated_project = self.env['project.project'].browse(legacy_project.id)
        self.assertTrue(migrated_project.pg_scope_sync_enabled)
        self.assertEqual(migrated_project.pg_onboarding_last_status, 'done')
        self.assertEqual(migrated_project.pg_mirror_migration_last_status, 'done')
        self.assertIn('Importar configuracao do template legado.', migrated_project.pg_onboarding_scope_included_text)
        self.assertIn('Agendar arranque do Odoo com a equipa comercial.', migrated_project.pg_onboarding_scope_included_text)
        self.assertIn('Agendar reuniao de arranque com o cliente e recolher dados iniciais.', migrated_project.pg_onboarding_scope_included_text)
        self.assertIn('Importar contactos de clientes e fornecedores para preparar a operacao inicial.', migrated_project.pg_onboarding_scope_included_text)
        self.assertIn('Criar utilizadores', migrated_project.pg_onboarding_scope_included_text)
        self.assertIn('Configurar permissoes', migrated_project.pg_onboarding_scope_included_text)
        self.assertIn('Validar acessos', migrated_project.pg_onboarding_scope_included_text)
        self.assertNotIn('Categorias', migrated_project.pg_onboarding_scope_included_text)
        self.assertNotIn('Bom dia Bruno', migrated_project.pg_onboarding_scope_included_text)
        self.assertNotIn('Conforme conversado', migrated_project.pg_onboarding_scope_included_text)
        self.assertNotIn('Mail None', migrated_project.pg_onboarding_scope_included_text)
        self.assertNotIn('Testar e Corrigir importacao de encomendas em curso', migrated_project.pg_onboarding_scope_included_text)
        self.assertNotIn('Fico a aguardar feedback', migrated_project.pg_onboarding_scope_included_text)
        self.assertNotIn('Rui Ribeiro', migrated_project.pg_onboarding_scope_included_text)
        self.assertIn('Aquisição de hardware fora de âmbito.', migrated_project.pg_onboarding_scope_excluded_text)
        self.assertIn('Go Live Legacy', migrated_project.pg_onboarding_deliverables_text)
        self.assertIn('Cliente Legacy', migrated_project.pg_onboarding_stakeholders_text)
        self.assertEqual(queue_mock.call_args.kwargs['trigger_type'], 'legacy_migration')
        self.assertEqual(queue_mock.call_args.kwargs['trigger_model'], 'project.project')
        self.assertEqual(queue_mock.call_args.kwargs['trigger_record_id'], legacy_project.id)
        process_mock.assert_called_once()

    def test_legacy_project_migration_curates_existing_onboarding_scope_seed(self):
        legacy_project = self.create_project(
            self.repository,
            name='Projeto Legacy Seed',
            pg_scope_sync_enabled=False,
            pg_status_sync_enabled=False,
            pg_decisions_sync_enabled=True,
            pg_onboarding_scope_included_text='\n'.join(
                [
                    'Importar contactos de clientes e fornecedores',
                    'Template Orcamento - Odoo Import V2.2.xlsm',
                    '> Criar campo "Registo Verificado"',
                    'Criar utilizadores; Configurar permissoes; Validar acessos',
                    'Fico a aguardar resposta o mais breve possivel.',
                    'Go-Live',
                    'Conforme conversado na reuniao na AncoraVip envio em anexo a informacao solicitada.',
                    'Whatsapp',
                ]
            ),
            pg_onboarding_last_status='never',
        )

        run = self.env['pg.project.mirror.sync.run'].create(
            {
                'project_id': legacy_project.id,
                'status': 'queued',
                'trigger_type': 'legacy_migration',
                'trigger_model': 'project.project',
                'trigger_record_id': legacy_project.id,
            }
        )
        with patch.object(ProjectMirrorSyncService, 'queue_project', autospec=True, return_value=run):
            with patch.object(ProjectMirrorSyncService, 'process_run', autospec=True, return_value=run):
                legacy_project.action_migrate_legacy_project_mirror()

        migrated_project = self.env['project.project'].browse(legacy_project.id)
        self.assertIn('Importar contactos de clientes e fornecedores', migrated_project.pg_onboarding_scope_included_text)
        self.assertIn('Criar campo "Registo Verificado"', migrated_project.pg_onboarding_scope_included_text)
        self.assertIn('Criar utilizadores', migrated_project.pg_onboarding_scope_included_text)
        self.assertIn('Configurar permissoes', migrated_project.pg_onboarding_scope_included_text)
        self.assertIn('Validar acessos', migrated_project.pg_onboarding_scope_included_text)
        self.assertNotIn('Template Orcamento - Odoo Import V2.2.xlsm', migrated_project.pg_onboarding_scope_included_text)
        self.assertNotIn('Conforme conversado', migrated_project.pg_onboarding_scope_included_text)
        self.assertNotIn('Whatsapp', migrated_project.pg_onboarding_scope_included_text)
        self.assertNotIn('Fico a aguardar resposta', migrated_project.pg_onboarding_scope_included_text)
        self.assertNotIn('Go-Live', migrated_project.pg_onboarding_scope_included_text)

    def test_mirror_migration_needed_flag_clears_after_onboarding_and_first_run(self):
        project = self.create_project(
            self.repository,
            name='Projeto a Migrar',
            pg_onboarding_last_status='never',
        )
        self.assertTrue(project.pg_mirror_migration_needed)

        project.with_context(
            pg_skip_scope_sync_enqueue=True,
            pg_skip_mirror_sync_enqueue=True,
            pg_skip_status_sync_touch=True,
        ).write({'pg_onboarding_last_status': 'done'})
        self.env['pg.project.mirror.sync.run'].create(
            {
                'project_id': project.id,
                'status': 'done',
                'trigger_type': 'manual',
                'trigger_model': 'project.project',
                'trigger_record_id': project.id,
            }
        )
        project = self.env['project.project'].browse(project.id)

        self.assertFalse(project.pg_mirror_migration_needed)

    def test_status_service_processes_and_skips_unchanged_payload(self):
        service = ProjectStatusSyncService(self.env)
        service.publisher.publish_project_status_snapshot = Mock(
            return_value={
                'content': {'sha': 'status-file-sha'},
                'commit': {'sha': 'status-commit-sha'},
            }
        )

        run = service.queue_project(
            self.project,
            trigger_type='manual_button',
            trigger_model='project.project',
            trigger_record_id=self.project.id,
        )
        self.assertTrue(run)
        self.assertEqual(run.status, 'queued')

        processed_run = service.process_run(run)
        self.assertEqual(processed_run.status, 'done')
        self.assertEqual(processed_run.published_commit_sha, 'status-commit-sha')
        self.assertEqual(self.project.pg_status_sync_last_status, 'done')
        self.assertFalse(self.project.pg_status_sync_needs_publish)
        service.publisher.publish_project_status_snapshot.assert_called_once()

        service.publisher.publish_project_status_snapshot.reset_mock()
        second_run = service.queue_project(
            self.project,
            trigger_type='manual_button',
            trigger_model='project.project',
            trigger_record_id=self.project.id,
        )
        processed_second_run = service.process_run(second_run)
        self.assertEqual(processed_second_run.status, 'skipped')
        self.assertFalse(self.project.pg_status_sync_needs_publish)
        service.publisher.publish_project_status_snapshot.assert_not_called()

    def test_status_change_marks_project_for_manual_publish_review(self):
        service = ProjectStatusSyncService(self.env)
        service.publisher.publish_project_status_snapshot = Mock(
            return_value={
                'content': {'sha': 'status-file-sha'},
                'commit': {'sha': 'status-commit-sha'},
            }
        )

        run = service.queue_project(
            self.project,
            trigger_type='manual_button',
            trigger_model='project.project',
            trigger_record_id=self.project.id,
        )
        service.process_run(run)

        project = self.env['project.project'].browse(self.project.id)
        project.write({'pg_status_next_steps_text': 'Publicar novo estado validado'})

        self.assertTrue(project.pg_status_sync_needs_publish)
        self.assertIn('after the last manual publication', project.pg_status_sync_review_feedback)

    def test_decisions_service_processes_and_skips_unchanged_payload(self):
        task = self.create_task(self.project, name='Task decisions service', pg_scope_sequence=70)
        self.set_task_recommendation(task, recommendation_class='standard')
        task.write({'pg_ai_consultive_gate_notes': 'Decisao pronta para publish.'})
        task.action_mark_ai_consultive_gate_ready()

        service = ProjectDecisionsSyncService(self.env)
        service.publisher.publish_project_decisions_snapshot = Mock(
            return_value={
                'content': {'sha': 'decisions-file-sha'},
                'commit': {'sha': 'decisions-commit-sha'},
            }
        )

        run = service.queue_project(
            self.project,
            trigger_type='manual_button',
            trigger_model='project.project',
            trigger_record_id=self.project.id,
        )
        self.assertTrue(run)
        self.assertEqual(run.status, 'queued')

        processed_run = service.process_run(run)
        self.assertEqual(processed_run.status, 'done')
        self.assertEqual(processed_run.published_commit_sha, 'decisions-commit-sha')
        self.assertEqual(self.project.pg_decisions_sync_last_status, 'done')
        service.publisher.publish_project_decisions_snapshot.assert_called_once()

        service.publisher.publish_project_decisions_snapshot.reset_mock()
        second_run = service.queue_project(
            self.project,
            trigger_type='manual_button',
            trigger_model='project.project',
            trigger_record_id=self.project.id,
        )
        processed_second_run = service.process_run(second_run)
        self.assertEqual(processed_second_run.status, 'skipped')
        service.publisher.publish_project_decisions_snapshot.assert_not_called()

    def test_requirements_service_processes_and_skips_unchanged_payload(self):
        self.create_task(
            self.project,
            name='Task requirements service',
            pg_scope_state='validated',
            pg_scope_sequence=71,
        )

        service = ProjectRequirementsSyncService(self.env)
        service.publisher.publish_project_requirements_snapshot = Mock(
            return_value={
                'content': {'sha': 'requirements-file-sha'},
                'commit': {'sha': 'requirements-commit-sha'},
            }
        )

        run = service.queue_project(
            self.project,
            trigger_type='manual_button',
            trigger_model='project.project',
            trigger_record_id=self.project.id,
        )
        self.assertTrue(run)
        self.assertEqual(run.status, 'queued')

        processed_run = service.process_run(run)
        self.assertEqual(processed_run.status, 'done')
        self.assertEqual(processed_run.published_commit_sha, 'requirements-commit-sha')
        self.assertEqual(self.project.pg_requirements_sync_last_status, 'done')
        service.publisher.publish_project_requirements_snapshot.assert_called_once()

        service.publisher.publish_project_requirements_snapshot.reset_mock()
        second_run = service.queue_project(
            self.project,
            trigger_type='manual_button',
            trigger_model='project.project',
            trigger_record_id=self.project.id,
        )
        processed_second_run = service.process_run(second_run)
        self.assertEqual(processed_second_run.status, 'skipped')
        service.publisher.publish_project_requirements_snapshot.assert_not_called()

    def test_risks_service_processes_and_skips_unchanged_payload(self):
        self.create_project_risk(
            self.project,
            name='Risco de governance',
            description='O backlog pode crescer sem validacao formal.',
            mitigation='Rever backlog quinzenalmente com o PM.',
            severity='medium',
            state='open',
        )

        service = ProjectRisksSyncService(self.env)
        service.publisher.publish_project_risks_snapshot = Mock(
            return_value={
                'content': {'sha': 'risks-file-sha'},
                'commit': {'sha': 'risks-commit-sha'},
            }
        )

        run = service.queue_project(
            self.project,
            trigger_type='manual_button',
            trigger_model='project.project',
            trigger_record_id=self.project.id,
        )
        self.assertTrue(run)
        self.assertEqual(run.status, 'queued')

        processed_run = service.process_run(run)
        self.assertEqual(processed_run.status, 'done')
        self.assertEqual(processed_run.published_commit_sha, 'risks-commit-sha')
        self.assertEqual(self.project.pg_risks_sync_last_status, 'done')
        service.publisher.publish_project_risks_snapshot.assert_called_once()

        service.publisher.publish_project_risks_snapshot.reset_mock()
        second_run = service.queue_project(
            self.project,
            trigger_type='manual_button',
            trigger_model='project.project',
            trigger_record_id=self.project.id,
        )
        processed_second_run = service.process_run(second_run)
        self.assertEqual(processed_second_run.status, 'skipped')
        service.publisher.publish_project_risks_snapshot.assert_not_called()

    def test_deliveries_service_processes_and_skips_unchanged_payload(self):
        self.create_project_milestone(
            self.project,
            name='Entrega service',
            pg_delivery_state='in_progress',
            pg_acceptance_state='pending',
        )

        service = ProjectDeliveriesSyncService(self.env)
        service.publisher.publish_project_deliveries_snapshot = Mock(
            return_value={
                'content': {'sha': 'deliveries-file-sha'},
                'commit': {'sha': 'deliveries-commit-sha'},
            }
        )

        run = service.queue_project(
            self.project,
            trigger_type='manual_button',
            trigger_model='project.project',
            trigger_record_id=self.project.id,
        )
        self.assertTrue(run)
        self.assertEqual(run.status, 'queued')

        processed_run = service.process_run(run)
        self.assertEqual(processed_run.status, 'done')
        self.assertEqual(processed_run.published_commit_sha, 'deliveries-commit-sha')
        self.assertEqual(self.project.pg_deliveries_sync_last_status, 'done')
        service.publisher.publish_project_deliveries_snapshot.assert_called_once()

        service.publisher.publish_project_deliveries_snapshot.reset_mock()
        second_run = service.queue_project(
            self.project,
            trigger_type='manual_button',
            trigger_model='project.project',
            trigger_record_id=self.project.id,
        )
        processed_second_run = service.process_run(second_run)
        self.assertEqual(processed_second_run.status, 'skipped')
        service.publisher.publish_project_deliveries_snapshot.assert_not_called()

    def test_project_plan_service_processes_and_skips_unchanged_payload(self):
        self.create_project_milestone(
            self.project,
            name='Plano service',
            pg_plan_start_date='2026-04-10',
            deadline='2026-04-15',
            pg_plan_status='planned',
            pg_plan_dependency_refs='REQ-001',
        )

        service = ProjectPlanSyncService(self.env)
        service.publisher.publish_project_plan_snapshot = Mock(
            return_value={
                'content': {'sha': 'project-plan-file-sha'},
                'commit': {'sha': 'project-plan-commit-sha'},
            }
        )

        run = service.queue_project(
            self.project,
            trigger_type='manual_button',
            trigger_model='project.project',
            trigger_record_id=self.project.id,
        )
        self.assertTrue(run)
        self.assertEqual(run.status, 'queued')

        processed_run = service.process_run(run)
        self.assertEqual(processed_run.status, 'done')
        self.assertEqual(processed_run.published_commit_sha, 'project-plan-commit-sha')
        self.assertEqual(self.project.pg_project_plan_sync_last_status, 'done')
        service.publisher.publish_project_plan_snapshot.assert_called_once()

        service.publisher.publish_project_plan_snapshot.reset_mock()
        second_run = service.queue_project(
            self.project,
            trigger_type='manual_button',
            trigger_model='project.project',
            trigger_record_id=self.project.id,
        )
        processed_second_run = service.process_run(second_run)
        self.assertEqual(processed_second_run.status, 'skipped')
        service.publisher.publish_project_plan_snapshot.assert_not_called()

    def test_budget_service_processes_and_skips_unchanged_payload(self):
        self.create_project_budget_line(
            self.project,
            category='Budget service',
            planned_amount=1800.0,
            approved_amount=1500.0,
            consumed_amount=250.0,
            status='consuming',
        )

        service = ProjectBudgetSyncService(self.env)
        service.publisher.publish_project_budget_snapshot = Mock(
            return_value={
                'content': {'sha': 'budget-file-sha'},
                'commit': {'sha': 'budget-commit-sha'},
            }
        )

        run = service.queue_project(
            self.project,
            trigger_type='manual_button',
            trigger_model='project.project',
            trigger_record_id=self.project.id,
        )
        self.assertTrue(run)
        self.assertEqual(run.status, 'queued')

        processed_run = service.process_run(run)
        self.assertEqual(processed_run.status, 'done')
        self.assertEqual(processed_run.published_commit_sha, 'budget-commit-sha')
        self.assertEqual(self.project.pg_budget_sync_last_status, 'done')
        service.publisher.publish_project_budget_snapshot.assert_called_once()

        service.publisher.publish_project_budget_snapshot.reset_mock()
        second_run = service.queue_project(
            self.project,
            trigger_type='manual_button',
            trigger_model='project.project',
            trigger_record_id=self.project.id,
        )
        processed_second_run = service.process_run(second_run)
        self.assertEqual(processed_second_run.status, 'skipped')
        service.publisher.publish_project_budget_snapshot.assert_not_called()
