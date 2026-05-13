from unittest.mock import Mock

from odoo.tests import TransactionCase, tagged

from ..services.project_scope_sync_service import ProjectScopeSyncService
from ..services.project_status_sync_service import ProjectStatusSyncService
from ..services.project_decisions_sync_service import ProjectDecisionsSyncService
from ..services.project_plan_sync_service import ProjectPlanSyncService
from ..services.project_budget_sync_service import ProjectBudgetSyncService
from ..services.project_sync_quality_review_service import ProjectSyncQualityReviewService
from .common import PgAiDevAssistantTestMixin


@tagged('post_install', '-at_install')
class TestSyncQualityReviewService(PgAiDevAssistantTestMixin, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.set_pg_base_url()
        cls.repository = cls.create_repository(name='quality_review_repo')
        cls.project = cls.create_project(cls.repository, name='Projeto Quality Review')
        cls.task = cls.create_task(cls.project, name='Task Quality Review')

    def setUp(self):
        super().setUp()
        self.env['ir.config_parameter'].sudo().set_param('pg_sync_quality_review_enabled', '1')

    def test_status_review_detects_placeholder_and_workflow_text(self):
        service = ProjectSyncQualityReviewService(self.env)

        review = service.review_status_payload(
            {
                'status_summary': 'Curto demais',
                'milestones': ['Latest status publication status: Never'],
                'blockers': [],
                'risks': [],
                'next_steps': [],
                'pending_decisions': ['[PONTO POR VALIDAR]'],
            }
        )

        buckets = {warning['bucket'] for warning in review['warnings']}
        self.assertIn('low_signal_summary', buckets)
        self.assertIn('workflow_text_detected', buckets)
        self.assertIn('placeholder_residual', buckets)
        self.assertIn('latest status payload', review['feedback'])

    def test_scope_review_flags_weak_acceptance_criteria(self):
        service = ProjectSyncQualityReviewService(self.env)

        review = service.review_scope_payload(
            {
                'scope_overview': {
                    'business_goal': 'Validar qualidade.',
                    'acceptance_criteria': [],
                },
                'scope_items': [
                    {
                        'title': 'Inventario',
                        'scope_summary': 'Inventario',
                        'acceptance_criteria': [],
                    }
                ],
            }
        )

        buckets = {warning['bucket'] for warning in review['warnings']}
        self.assertIn('weak_acceptance_criteria', buckets)

    def test_scope_review_aggregates_repeated_placeholder_warnings(self):
        service = ProjectSyncQualityReviewService(self.env)

        review = service.review_scope_payload(
            {
                'scope_overview': {
                    'business_goal': '[PONTO POR VALIDAR]',
                    'business_process': '[PONTO POR VALIDAR]',
                    'out_of_scope': '[PONTO POR VALIDAR]',
                },
                'scope_items': [],
            }
        )

        placeholder_warnings = [warning for warning in review['warnings'] if warning['bucket'] == 'placeholder_residual']
        self.assertEqual(len(placeholder_warnings), 1)
        self.assertEqual(placeholder_warnings[0]['occurrence_count'], 3)
        self.assertEqual(review['warning_occurrence_count'], 4)
        self.assertEqual(review['warning_group_count'], 2)
        self.assertIn('warning occurrence(s) across', review['feedback'])
        self.assertIn('placeholder_residual (x3)', review['feedback'])

    def test_mirror_review_returns_structured_warning_output(self):
        service = ProjectSyncQualityReviewService(self.env)

        review = service.review_mirror_payload(
            {
                'project': {
                    'repository_summary': 'Repositorio factual do projeto.',
                    'objective': 'Melhorar a disciplina de publish.',
                    'current_request': 'Publicar espelho do projeto.',
                    'current_process': 'Execucao e validacao.',
                    'problem_or_need': 'Ruido semantico residual.',
                    'business_impact': 'Melhorar legibilidade.',
                    'included_scope': ['Email Odoo Security'],
                    'deliverables': ['Go Live'],
                }
            },
            {
                'planning': {
                    'planning_summary': {
                        'next_milestone_name': 'Go Live',
                        'next_milestone_target_date': '2026-04-01',
                        'next_milestone_owner': '',
                        'open_tasks_for_next_milestone_count': 0,
                    }
                }
            },
            {'tasks': []},
            {'messages': []},
            {'attachments': []},
        )

        self.assertTrue(review['enabled'])
        self.assertEqual(review['summary_status'], 'warning')
        self.assertEqual(review['publishability'], 'eligible_with_warnings')
        self.assertFalse(review['blocking_findings'])
        warning_buckets = {finding['bucket'] for finding in review['warning_findings']}
        self.assertIn('included_scope_not_eligible', warning_buckets)
        self.assertIn('next_milestone_target_in_past', warning_buckets)
        self.assertIn('next_milestone_owner_missing', warning_buckets)
        self.assertIn('next_milestone_without_open_tasks', warning_buckets)
        self.assertTrue(review['bucket_reviews'])
        self.assertIn('Mirror quality review status: warning.', review['feedback'])

    def test_mirror_review_reports_factual_scope_backlog_without_degrading_publishability(self):
        service = ProjectSyncQualityReviewService(self.env)

        review = service.review_mirror_payload(
            {
                'project': {
                    'repository_summary': 'Repositorio factual do projeto.',
                    'objective': 'Publicar espelho factual.',
                    'current_request': 'Publicar mirror.',
                    'current_process': 'Validacao.',
                    'problem_or_need': 'Preservar factos brownfield.',
                    'business_impact': 'Evitar perda factual.',
                    'included_scope': ['Resumo funcional de teste.'],
                    'factual_scope_backlog': [
                        {'item': 'Formacao CRM', 'reason': 'weak_nominal_item'},
                        {
                            'item': 'Incluir nome do cliente do registo do projeto Ao finalizar producao no chao de fabrica registar automaticamente a expedicao.',
                            'reason': 'compound_item',
                        },
                    ],
                    'scope_quality_review': {
                        'included_scope_count': 1,
                        'factual_scope_backlog_count': 2,
                        'curation_reason_counts': {
                            'weak_nominal_item': 1,
                            'compound_item': 1,
                        },
                    },
                    'deliverables': ['Go Live'],
                }
            },
            {'planning': {'planning_summary': {}}},
            {'tasks': []},
            {'messages': []},
            {'attachments': []},
        )

        self.assertEqual(review['summary_status'], 'ok')
        self.assertEqual(review['publishability'], 'eligible')
        self.assertEqual(review['included_scope_count'], 1)
        self.assertEqual(review['factual_scope_backlog_count'], 2)
        self.assertEqual(review['factual_scope_backlog_reason_counts']['weak_nominal_item'], 1)
        self.assertEqual(review['factual_scope_backlog_reason_counts']['compound_item'], 1)
        self.assertIn(
            'Curated scope snapshot: included 1 item(s), backlog 2 item(s), excluded noise 0 item(s).',
            review['feedback'],
        )
        self.assertIn('Factual scope backlog pending curation: 2 item(s).', review['feedback'])

    def test_mirror_review_keeps_observation_only_payload_publishable(self):
        service = ProjectSyncQualityReviewService(self.env)

        review = service.review_mirror_payload(
            {
                'project': {
                    'repository_summary': 'Repositorio factual do projeto.',
                    'objective': 'Publicar espelho factual.',
                    'current_request': 'Regerar mirror.',
                    'current_process': 'Validacao.',
                    'problem_or_need': 'Melhorar rastreabilidade.',
                    'business_impact': 'Dar contexto fiavel ao repo.',
                    'included_scope': ['Resumo funcional de teste.'],
                    'deliverables': ['Go Live'],
                }
            },
            {'planning': {'planning_summary': {}}},
            {'tasks': []},
            {'messages': []},
            {'attachments': []},
        )

        self.assertEqual(review['summary_status'], 'ok')
        self.assertEqual(review['publishability'], 'eligible')
        self.assertFalse(review['blocking_findings'])
        self.assertFalse(review['warning_findings'])
        self.assertEqual(review['observation_count'], 1)
        self.assertEqual(review['observations'][0]['severity'], 'observacao')
        self.assertEqual(review['observations'][0]['bucket'], 'next_milestone_missing')
        self.assertIn('Mirror quality review status: ok.', review['feedback'])

    def test_mirror_review_blocks_when_essential_context_is_missing(self):
        service = ProjectSyncQualityReviewService(self.env)

        review = service.review_mirror_payload(
            {
                'project': {
                    'repository_summary': '',
                    'objective': '',
                    'current_request': '',
                    'current_process': '',
                    'problem_or_need': '',
                    'business_impact': '',
                    'included_scope': [],
                    'deliverables': [],
                }
            },
            {'planning': {'planning_summary': {}}},
            {'tasks': []},
            {'messages': []},
            {'attachments': []},
        )

        self.assertEqual(review['summary_status'], 'blocking')
        self.assertEqual(review['publishability'], 'not_eligible')
        self.assertEqual(review['blocking_count'], 1)
        self.assertEqual(review['blocking_findings'][0]['bucket'], 'essential_project_context_missing')
        self.assertIn('Mirror quality review status: blocking.', review['feedback'])

    def test_mirror_review_keeps_sparse_operational_payload_publishable(self):
        service = ProjectSyncQualityReviewService(self.env)

        review = service.review_mirror_payload(
            {
                'project': {
                    'repository_summary': '',
                    'objective': '',
                    'current_request': '',
                    'current_process': '',
                    'problem_or_need': '',
                    'business_impact': '',
                    'included_scope': [],
                    'deliverables': [],
                }
            },
            {
                'planning': {
                    'milestones': [],
                    'planning_summary': {
                        'next_milestone_name': '',
                        'open_task_count': 1,
                        'open_tasks_for_next_milestone_count': 0,
                    },
                }
            },
            {
                'tasks': [
                    {
                        'name': 'Levantar requisitos do projeto',
                        'is_closed': False,
                        'is_cancelled': False,
                    }
                ]
            },
            {'messages': []},
            {'attachments': []},
        )

        self.assertEqual(review['summary_status'], 'warning')
        self.assertEqual(review['publishability'], 'eligible_with_warnings')
        self.assertFalse(review['blocking_findings'])
        warning_buckets = {finding['bucket'] for finding in review['warning_findings']}
        self.assertIn('minimum_required_bucket_empty', warning_buckets)

    def test_mirror_review_warns_when_included_scope_is_empty(self):
        service = ProjectSyncQualityReviewService(self.env)

        review = service.review_mirror_payload(
            {
                'project': {
                    'repository_summary': 'Repositorio factual do projeto.',
                    'objective': 'Melhorar a disciplina de publish.',
                    'current_request': 'Publicar espelho.',
                    'current_process': 'Execucao.',
                    'problem_or_need': 'Ruido residual.',
                    'business_impact': 'Melhorar legibilidade.',
                    'included_scope': [],
                    'deliverables': ['Go Live'],
                }
            },
            {'planning': {'planning_summary': {}}},
            {'tasks': []},
            {'messages': []},
            {'attachments': []},
        )

        warning_buckets = {finding['bucket'] for finding in review['warning_findings']}
        self.assertIn('minimum_required_bucket_empty', warning_buckets)

    def test_mirror_review_marks_contact_metadata_scope_as_not_eligible(self):
        service = ProjectSyncQualityReviewService(self.env)

        review = service.review_mirror_payload(
            {
                'project': {
                    'repository_summary': 'Repositorio factual do projeto.',
                    'objective': 'Publicar espelho factual.',
                    'current_request': 'Publicar mirror.',
                    'current_process': 'Validacao.',
                    'problem_or_need': 'Reduzir ruído.',
                    'business_impact': 'Melhorar leitura operacional.',
                    'included_scope': ['Cliente X Unidade1 Unidade2 Tel. +351 255 878 612'],
                    'deliverables': ['Go Live'],
                }
            },
            {'planning': {'planning_summary': {}}},
            {'tasks': []},
            {'messages': []},
            {'attachments': []},
        )

        warning_buckets = {finding['bucket'] for finding in review['warning_findings']}
        self.assertIn('included_scope_not_eligible', warning_buckets)
        finding = next(
            finding for finding in review['warning_findings'] if finding['bucket'] == 'included_scope_not_eligible'
        )
        self.assertEqual(finding['severity'], 'warning')
        self.assertEqual(finding['publishability'], 'not_eligible')

    def test_mirror_review_flags_contact_metadata_scope_as_not_eligible(self):
        service = ProjectSyncQualityReviewService(self.env)

        review = service.review_mirror_payload(
            {
                'project': {
                    'repository_summary': 'Repositorio factual do projeto.',
                    'objective': 'Publicar espelho factual.',
                    'current_request': 'Publicar mirror.',
                    'current_process': 'Validacao.',
                    'problem_or_need': 'Reduzir ruido.',
                    'business_impact': 'Melhorar leitura operacional.',
                    'included_scope': [
                        'ANCORA VIP INDUSTRY, LDA. Unidade2 Rua do Bairro da Boavista Mail geral@ancoravip.pt '
                        'Tel. +351 255 878 612'
                    ],
                    'deliverables': ['Go Live'],
                }
            },
            {'planning': {'planning_summary': {}}},
            {'tasks': []},
            {'messages': []},
            {'attachments': []},
        )

        warning_buckets = {finding['bucket'] for finding in review['warning_findings']}
        self.assertIn('included_scope_not_eligible', warning_buckets)
        finding = next(
            finding for finding in review['warning_findings'] if finding['bucket'] == 'included_scope_not_eligible'
        )
        self.assertEqual(finding['severity'], 'warning')
        self.assertEqual(finding['publishability'], 'not_eligible')

    def test_mirror_review_flags_scope_item_that_still_needs_hygiene_normalization(self):
        service = ProjectSyncQualityReviewService(self.env)

        review = service.review_mirror_payload(
            {
                'project': {
                    'repository_summary': 'Repositorio factual do projeto.',
                    'objective': 'Publicar espelho factual.',
                    'current_request': 'Publicar mirror.',
                    'current_process': 'Validacao.',
                    'problem_or_need': 'Reduzir ruido.',
                    'business_impact': 'Melhorar leitura operacional.',
                    'included_scope': ['Whatsapp Criar campo "Registo Verificado"'],
                    'deliverables': ['Go Live'],
                }
            },
            {'planning': {'planning_summary': {}}},
            {'tasks': []},
            {'messages': []},
            {'attachments': []},
        )

        warning_buckets = {finding['bucket'] for finding in review['warning_findings']}
        self.assertIn('included_scope_needs_hygiene', warning_buckets)
        hygiene_finding = next(
            finding for finding in review['warning_findings'] if finding['bucket'] == 'included_scope_needs_hygiene'
        )
        self.assertEqual(hygiene_finding['severity'], 'warning')
        self.assertEqual(hygiene_finding['publishability'], 'eligible_with_warnings')

    def test_mirror_review_flags_conversational_follow_up_scope_as_not_eligible(self):
        service = ProjectSyncQualityReviewService(self.env)

        review = service.review_mirror_payload(
            {
                'project': {
                    'repository_summary': 'Repositorio factual do projeto.',
                    'objective': 'Publicar espelho factual.',
                    'current_request': 'Publicar mirror.',
                    'current_process': 'Validacao.',
                    'problem_or_need': 'Reduzir ruido.',
                    'business_impact': 'Melhorar leitura operacional.',
                    'included_scope': ['Fico a aguardar feedback da vossa parte.'],
                    'deliverables': ['Go Live'],
                }
            },
            {'planning': {'planning_summary': {}}},
            {'tasks': []},
            {'messages': []},
            {'attachments': []},
        )

        warning_buckets = {finding['bucket'] for finding in review['warning_findings']}
        self.assertIn('included_scope_conversational_follow_up', warning_buckets)

    def test_mirror_review_flags_unsafe_compound_scope_as_not_eligible(self):
        service = ProjectSyncQualityReviewService(self.env)

        review = service.review_mirror_payload(
            {
                'project': {
                    'repository_summary': 'Repositorio factual do projeto.',
                    'objective': 'Publicar espelho factual.',
                    'current_request': 'Publicar mirror.',
                    'current_process': 'Validacao.',
                    'problem_or_need': 'Reduzir ruido.',
                    'business_impact': 'Melhorar leitura operacional.',
                    'included_scope': [
                        'testar e corrigir importacao de encomendas em curso alterar arrastar tarefa para producao '
                        'alterar campo de mapeamento de secao para mapeamento obrigatorio'
                    ],
                    'deliverables': ['Go Live'],
                }
            },
            {'planning': {'planning_summary': {}}},
            {'tasks': []},
            {'messages': []},
            {'attachments': []},
        )

        warning_buckets = {finding['bucket'] for finding in review['warning_findings']}
        self.assertIn('included_scope_split_not_safe', warning_buckets)

    def test_mirror_review_flags_safe_compound_scope_as_warning(self):
        service = ProjectSyncQualityReviewService(self.env)

        review = service.review_mirror_payload(
            {
                'project': {
                    'repository_summary': 'Repositorio factual do projeto.',
                    'objective': 'Publicar espelho factual.',
                    'current_request': 'Publicar mirror.',
                    'current_process': 'Validacao.',
                    'problem_or_need': 'Reduzir ruido.',
                    'business_impact': 'Melhorar leitura operacional.',
                    'included_scope': ['Criar utilizadores; Configurar permissoes; Validar acessos'],
                    'deliverables': ['Go Live'],
                }
            },
            {'planning': {'planning_summary': {}}},
            {'tasks': []},
            {'messages': []},
            {'attachments': []},
        )

        warning_buckets = {finding['bucket'] for finding in review['warning_findings']}
        self.assertIn('included_scope_compound_item', warning_buckets)

    def test_project_plan_review_flags_overdue_items_and_missing_owner(self):
        service = ProjectSyncQualityReviewService(self.env)

        review = service.review_project_plan_payload(
            {
                'plan_items': [
                    {
                        'title': 'Go Live',
                        'planned_end': '2026-04-01',
                        'status': 'in_progress',
                        'owner': '[PONTO POR VALIDAR]',
                    }
                ]
            }
        )

        warning_buckets = {warning['bucket'] for warning in review['warnings']}
        self.assertIn('plan_item_target_in_past', warning_buckets)
        self.assertIn('plan_item_owner_missing', warning_buckets)
        self.assertIn('latest project plan payload', review['feedback'])

    def test_status_sync_persists_quality_review_feedback(self):
        self.project.write({'pg_status_summary': 'Curto demais'})
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
        processed_run = service.process_run(run)

        self.assertEqual(processed_run.status, 'done')
        self.assertIn('Pre-publication quality review found', self.project.pg_status_sync_quality_review_feedback)
        self.assertIn('low_signal_summary', self.project.pg_status_sync_quality_review_feedback)

    def test_scope_sync_persists_quality_review_feedback(self):
        project = self.create_project(
            self.repository,
            name='Projeto Scope Quality Review',
            pg_business_goal=False,
        )
        self.create_task(project, name='Task Scope Quality Review')
        service = ProjectScopeSyncService(self.env)
        service.publisher.publish_project_scope_snapshot = Mock(
            return_value={
                'content': {'sha': 'scope-file-sha'},
                'commit': {'sha': 'scope-commit-sha'},
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
        self.assertIn('Pre-publication quality review found', project.pg_scope_sync_quality_review_feedback)
        self.assertIn('placeholder_residual', project.pg_scope_sync_quality_review_feedback)

    def test_decisions_sync_persists_quality_review_feedback(self):
        project = self.create_project(
            self.repository,
            name='Projeto Decisions Quality Review',
            pg_decisions_sync_enabled=True,
        )
        service = ProjectDecisionsSyncService(self.env)
        service.publisher.publish_project_decisions_snapshot = Mock(
            return_value={
                'content': {'sha': 'decisions-file-sha'},
                'commit': {'sha': 'decisions-commit-sha'},
            }
        )

        run = service.queue_project(
            project,
            trigger_type='manual_button',
            trigger_model='project.project',
            trigger_record_id=project.id,
        )
        processed_run = service.process_run(run)

        self.assertEqual(processed_run.status, 'done')
        self.assertIn('Pre-publication quality review found', project.pg_decisions_sync_quality_review_feedback)
        self.assertIn('empty_publishable_payload', project.pg_decisions_sync_quality_review_feedback)

    def test_budget_sync_persists_quality_review_feedback(self):
        project = self.create_project(
            self.repository,
            name='Projeto Budget Quality Review',
            pg_budget_sync_enabled=True,
        )
        self.create_project_budget_line(project)
        service = ProjectBudgetSyncService(self.env)
        service.publisher.publish_project_budget_snapshot = Mock(
            return_value={
                'content': {'sha': 'budget-file-sha'},
                'commit': {'sha': 'budget-commit-sha'},
            }
        )

        run = service.queue_project(
            project,
            trigger_type='manual_button',
            trigger_model='project.project',
            trigger_record_id=project.id,
        )
        processed_run = service.process_run(run)

        self.assertEqual(processed_run.status, 'done')
        self.assertIn('Pre-publication quality review found no warnings', project.pg_budget_sync_quality_review_feedback)

    def test_project_plan_sync_persists_specific_quality_review_feedback(self):
        project = self.create_project(
            self.repository,
            name='Projeto Plan Quality Review',
            allow_milestones=True,
            pg_project_plan_sync_enabled=True,
        )
        self.create_project_milestone(
            project,
            name='Go Live atrasado',
            pg_plan_start_date='2026-03-20',
            deadline='2026-04-01',
            pg_plan_status='in_progress',
        )
        service = ProjectPlanSyncService(self.env)
        service.publisher.publish_project_plan_snapshot = Mock(
            return_value={
                'content': {'sha': 'project-plan-file-sha'},
                'commit': {'sha': 'project-plan-commit-sha'},
            }
        )

        run = service.queue_project(
            project,
            trigger_type='manual_button',
            trigger_model='project.project',
            trigger_record_id=project.id,
        )
        processed_run = service.process_run(run)

        self.assertEqual(processed_run.status, 'done')
        self.assertIn('plan_item_target_in_past', project.pg_project_plan_sync_quality_review_feedback)
