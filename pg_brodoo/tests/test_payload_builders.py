from copy import deepcopy

from odoo import fields
from odoo.tests import TransactionCase, tagged

from ..services.project_budget_payload_builder import ProjectBudgetPayloadBuilder
from ..services.project_deliveries_payload_builder import ProjectDeliveriesPayloadBuilder
from ..services.project_plan_payload_builder import ProjectPlanPayloadBuilder
from ..services.project_scope_payload_builder import ProjectScopePayloadBuilder
from ..services.project_decisions_payload_builder import ProjectDecisionsPayloadBuilder
from ..services.project_requirements_payload_builder import ProjectRequirementsPayloadBuilder
from ..services.project_risks_payload_builder import ProjectRisksPayloadBuilder
from ..services.project_status_payload_builder import ProjectStatusPayloadBuilder
from .common import PgAiDevAssistantTestMixin


@tagged('post_install', '-at_install')
class TestPayloadBuilders(PgAiDevAssistantTestMixin, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.set_pg_base_url()
        cls.repository = cls.create_repository()
        cls.project = cls.create_project(cls.repository)
        cls.create_scope_line(cls.project, 'acceptance_criteria', 'O snapshot de ambito deve ser publicado.')
        cls.create_scope_line(cls.project, 'integrations', 'GitHub brodoo_v2')
        cls.scope_task = cls.create_task(cls.project, name='Tarefa em ambito')
        cls.create_task(
            cls.project,
            name='Tarefa excluida',
            pg_scope_relevant=False,
            pg_scope_state='excluded',
            pg_scope_summary='Nao deve entrar no payload.',
            pg_acceptance_criteria_text='Nao aplicavel',
        )
        cls.create_task(
            cls.project,
            name='Backlog operacional',
            pg_scope_track='operational_backlog',
            pg_scope_state='proposed',
            pg_scope_summary='Nao deve entrar no snapshot factual de scope.',
            pg_acceptance_criteria_text='Nao aplicavel',
        )
        cls.create_task(
            cls.project,
            name='Nota interna',
            pg_scope_track='internal_note',
            pg_scope_state='proposed',
            pg_scope_summary='Nao deve entrar no snapshot factual de scope.',
            pg_acceptance_criteria_text='Nao aplicavel',
        )
        cls.scope_builder = ProjectScopePayloadBuilder(cls.env)
        cls.decisions_builder = ProjectDecisionsPayloadBuilder(cls.env)
        cls.requirements_builder = ProjectRequirementsPayloadBuilder(cls.env)
        cls.risks_builder = ProjectRisksPayloadBuilder(cls.env)
        cls.deliveries_builder = ProjectDeliveriesPayloadBuilder(cls.env)
        cls.plan_builder = ProjectPlanPayloadBuilder(cls.env)
        cls.budget_builder = ProjectBudgetPayloadBuilder(cls.env)
        cls.status_builder = ProjectStatusPayloadBuilder(cls.env)

    def test_scope_payload_uses_task_trigger_url_and_filters_scope_items(self):
        payload = self.scope_builder.build_payload(
            self.project,
            trigger_type='task_write',
            trigger_model='project.task',
            trigger_record_id=self.scope_task.id,
            sync_reason=f'project.task {self.scope_task.id}',
        )

        self.assertEqual(payload['project_name'], 'Projeto Piloto')
        self.assertEqual(payload['project_phase'], 'discovery')
        self.assertEqual(payload['scope_overview']['acceptance_criteria'], ['O snapshot de ambito deve ser publicado.'])
        self.assertEqual(payload['project_lists']['integrations'], ['GitHub brodoo_v2'])
        self.assertEqual(payload['scope_summary']['active_scope_item_count'], 1)
        self.assertEqual(len(payload['scope_items']), 1)
        self.assertEqual(payload['scope_items'][0]['task_name'], 'Tarefa em ambito')
        self.assertEqual(payload['scope_items'][0]['scope_track'], 'approved_scope')
        self.assertEqual(payload['scope_items'][0]['assigned_users'], [self.env.user.display_name])
        self.assertEqual(
            payload['scope_items'][0]['source_url'],
            f'https://example.test/web#id={self.scope_task.id}&model=project.task',
        )
        self.assertEqual(
            payload['source_metadata']['source_record_url'],
            f'https://example.test/web#id={self.scope_task.id}&model=project.task',
        )

    def test_scope_payload_excludes_operational_backlog_and_internal_notes(self):
        payload = self.scope_builder.build_payload(self.project)

        task_names = {item['task_name'] for item in payload['scope_items']}

        self.assertIn('Tarefa em ambito', task_names)
        self.assertNotIn('Backlog operacional', task_names)
        self.assertNotIn('Nota interna', task_names)

    def test_scope_payload_ignores_suggested_scope_enrichment_until_applied(self):
        task = self.create_task(
            self.project,
            name='Task sem scope oficial',
            description='<p>Descricao fallback para snapshot.</p>',
            pg_scope_kind=False,
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
            pg_scope_sequence=30,
        )
        task.write(
            {
                'pg_scope_kind_suggested': 'integration',
                'pg_scope_summary_suggested': 'Resumo sugerido que nao deve entrar no payload.',
                'pg_acceptance_criteria_suggested_text': 'Criterio sugerido que nao deve entrar no payload.',
                'pg_scope_enrichment_status': 'draft',
                'pg_scope_enrichment_source': 'rule_based',
            }
        )

        payload = self.scope_builder.build_payload(self.project)
        payload_task = next(item for item in payload['scope_items'] if item['task_name'] == 'Task sem scope oficial')

        self.assertEqual(payload_task['scope_kind'], 'requirement')
        self.assertEqual(payload_task['scope_summary'], 'Descricao fallback para snapshot.')
        self.assertEqual(payload_task['acceptance_criteria'], [])

    def test_scope_payload_rejects_low_signal_official_summary_and_falls_back_to_description(self):
        task = self.create_task(
            self.project,
            name='Agendamento',
            description='<p>Agendar arranque do Odoo com a equipa comercial.</p>',
            pg_scope_summary=(
                'Bom dia Bruno, Hoje de tarde sempre passas por ca para dar seguimento ao arranque do Odoo? '
                'Com os melhores cumprimentos, Rui Ribeiro Image [7] ANCORA VIP INDUSTRY, LDA. '
                'Tel. +351 255 878 612'
            ),
            pg_scope_sequence=40,
        )

        payload = self.scope_builder.build_payload(self.project)
        payload_task = next(item for item in payload['scope_items'] if item['task_id'] == task.id)

        self.assertEqual(payload_task['scope_summary'], 'Agendar arranque do Odoo com a equipa comercial.')

    def test_scope_payload_derives_acceptance_criteria_from_description_when_official_text_is_placeholder(self):
        task = self.create_task(
            self.project,
            name='Webhook de faturacao',
            description=(
                '<p>Configurar sincronizacao do webhook de faturacao.</p>'
                '<p>O utilizador deve conseguir validar o webhook GitHub antes do go-live.</p>'
                '<p>O processo deve registar erros de integracao para analise posterior.</p>'
            ),
            pg_scope_summary='Configurar sincronizacao do webhook de faturacao.',
            pg_acceptance_criteria_text='[PONTO POR VALIDAR]',
            pg_scope_sequence=45,
        )

        payload = self.scope_builder.build_payload(self.project)
        payload_task = next(item for item in payload['scope_items'] if item['task_id'] == task.id)

        self.assertEqual(
            payload_task['acceptance_criteria'],
            [
                'O utilizador deve conseguir validar o webhook GitHub antes do go-live.',
                'O processo deve registar erros de integracao para analise posterior.',
            ],
        )

    def test_scope_payload_expands_generic_heading_into_factual_summary(self):
        task = self.create_task(
            self.project,
            name='Importacao de encomendas',
            description=(
                '<p>Desenvolvimento</p>'
                '<p>de funcionalidade para importacao de encomendas a partir de ficheiro Excel.</p>'
                '<p>O utilizador deve conseguir validar a importacao antes do go-live.</p>'
            ),
            pg_scope_summary='[PONTO POR VALIDAR]',
            pg_acceptance_criteria_text='[PONTO POR VALIDAR]',
            pg_scope_sequence=46,
        )

        payload = self.scope_builder.build_payload(self.project)
        payload_task = next(item for item in payload['scope_items'] if item['task_id'] == task.id)

        self.assertEqual(
            payload_task['scope_summary'],
            'Desenvolvimento de funcionalidade para importacao de encomendas a partir de ficheiro Excel.',
        )

    def test_scope_payload_skips_url_only_heading_and_uses_next_factual_line(self):
        task = self.create_task(
            self.project,
            name='Projeto na ref interna',
            description=(
                '<p>https://www.parametro.global/mail/message/419786 [1]</p>'
                '<p>Ao importar encomendas em curso criar o projeto com a ref. interna e confirma-la.</p>'
            ),
            pg_scope_summary='[PONTO POR VALIDAR]',
            pg_acceptance_criteria_text='[PONTO POR VALIDAR]',
            pg_scope_sequence=47,
        )

        payload = self.scope_builder.build_payload(self.project)
        payload_task = next(item for item in payload['scope_items'] if item['task_id'] == task.id)

        self.assertEqual(
            payload_task['scope_summary'],
            'Ao importar encomendas em curso criar o projeto com a ref. interna e confirma-la.',
        )

    def test_scope_payload_skips_phone_fragment_and_uses_next_factual_line(self):
        task = self.create_task(
            self.project,
            name='Lista fornecedores e clientes',
            description=(
                '<p>o +351 917 386 336</p>'
                '<p>Sincronizar lista de fornecedores e clientes com validacao deduplicada.</p>'
            ),
            pg_scope_summary='[PONTO POR VALIDAR]',
            pg_acceptance_criteria_text='[PONTO POR VALIDAR]',
            pg_scope_sequence=48,
        )

        payload = self.scope_builder.build_payload(self.project)
        payload_task = next(item for item in payload['scope_items'] if item['task_id'] == task.id)

        self.assertEqual(
            payload_task['scope_summary'],
            'Sincronizar lista de fornecedores e clientes com validacao deduplicada.',
        )

    def test_scope_payload_derives_acceptance_criteria_from_factual_secondary_line(self):
        task = self.create_task(
            self.project,
            name='Importacao de artigos',
            description=(
                '<p>Configurar importacao de artigos a partir de ficheiro Excel.</p>'
                '<p>Pre-visualizacao em grelha antes da confirmacao final pelo utilizador responsavel.</p>'
            ),
            pg_scope_summary='Configurar importacao de artigos a partir de ficheiro Excel.',
            pg_acceptance_criteria_text='[PONTO POR VALIDAR]',
            pg_scope_sequence=49,
        )

        payload = self.scope_builder.build_payload(self.project)
        payload_task = next(item for item in payload['scope_items'] if item['task_id'] == task.id)

        self.assertEqual(
            payload_task['acceptance_criteria'],
            ['Pre-visualizacao em grelha antes da confirmacao final pelo utilizador responsavel.'],
        )

    def test_scope_payload_generates_acceptance_criterion_from_factual_summary_when_needed(self):
        task = self.create_task(
            self.project,
            name='Integracao expedicao',
            description='<p>[PONTO POR VALIDAR]</p>',
            pg_scope_summary='Integrar expedicao da transportadora com confirmacao manual antes do fecho.',
            pg_acceptance_criteria_text='[PONTO POR VALIDAR]',
            pg_scope_sequence=50,
        )

        payload = self.scope_builder.build_payload(self.project)
        payload_task = next(item for item in payload['scope_items'] if item['task_id'] == task.id)

        self.assertEqual(
            payload_task['acceptance_criteria'],
            ['O ambito aprovado deve refletir integrar expedicao da transportadora com confirmacao manual antes do fecho.'],
        )

    def test_scope_payload_generates_acceptance_criterion_from_factual_task_name_when_needed(self):
        task = self.create_task(
            self.project,
            name='Importacao de contactos',
            description='<p>[PONTO POR VALIDAR]</p>',
            pg_scope_summary='Importacao de contactos',
            pg_acceptance_criteria_text='[PONTO POR VALIDAR]',
            pg_scope_sequence=50,
        )

        payload = self.scope_builder.build_payload(self.project)
        payload_task = next(item for item in payload['scope_items'] if item['task_id'] == task.id)

        self.assertEqual(
            payload_task['acceptance_criteria'],
            ['O ambito aprovado deve refletir importacao de contactos.'],
        )

    def test_scope_payload_derives_overview_acceptance_criteria_from_scope_items_when_missing_project_line(self):
        repository = self.create_repository(name='scope_overview_repo')
        project = self.create_project(repository, name='Projeto sem linha oficial')
        self.create_task(
            project,
            name='Importacao de contactos',
            description='<p>[PONTO POR VALIDAR]</p>',
            pg_scope_summary='Importacao de contactos',
            pg_acceptance_criteria_text='[PONTO POR VALIDAR]',
            pg_scope_sequence=10,
        )

        payload = self.scope_builder.build_payload(project)

        self.assertEqual(
            payload['scope_overview']['acceptance_criteria'],
            ['O ambito aprovado deve refletir importacao de contactos.'],
        )

    def test_scope_payload_keeps_acceptance_criteria_empty_when_no_factual_source_exists(self):
        task = self.create_task(
            self.project,
            name='Categorias',
            description='<p>[PONTO POR VALIDAR]</p>',
            pg_scope_summary='Categorias',
            pg_acceptance_criteria_text='[PONTO POR VALIDAR]',
            pg_scope_sequence=52,
        )

        payload = self.scope_builder.build_payload(self.project)
        payload_task = next(item for item in payload['scope_items'] if item['task_id'] == task.id)

        self.assertEqual(payload_task['acceptance_criteria'], [])

    def test_scope_hashable_payload_clears_volatile_metadata(self):
        payload = self.scope_builder.build_payload(self.project)
        hashable_payload = self.scope_builder.build_hashable_payload(payload)
        source_metadata = hashable_payload['source_metadata']

        self.assertEqual(source_metadata['sync_trigger'], '')
        self.assertEqual(source_metadata['sync_reason'], '')
        self.assertEqual(source_metadata['sync_published_at'], '')
        self.assertEqual(source_metadata['sync_published_by'], '')
        self.assertEqual(source_metadata['payload_hash'], '')

    def test_decisions_payload_maps_only_eligible_closed_consultive_decisions(self):
        ready_task = self.create_task(self.project, name='Task pronta para decisao', pg_scope_sequence=60)
        self.set_task_recommendation(ready_task, recommendation_class='additional_module')
        ready_task.write({'pg_ai_consultive_gate_notes': 'Gate fechado para publish factual.'})
        ready_task.action_mark_ai_consultive_gate_ready()

        non_ready_task = self.create_task(self.project, name='Task sem gate pronto', pg_scope_sequence=61)
        self.set_task_recommendation(non_ready_task, recommendation_class='standard')

        backlog_task = self.create_task(
            self.project,
            name='Task backlog',
            pg_scope_track='operational_backlog',
            pg_scope_sequence=62,
        )
        self.set_task_recommendation(backlog_task, recommendation_class='standard')
        backlog_task.write({'pg_ai_consultive_gate_notes': 'Gate fechado mas fora do ambito factual.'})
        backlog_task.action_mark_ai_consultive_gate_ready()

        payload = self.decisions_builder.build_payload(self.project)

        self.assertEqual(payload['project_name'], 'Projeto Piloto')
        self.assertEqual(payload['published_decision_count'], 1)
        self.assertEqual(len(payload['decisions']), 1)
        decision = payload['decisions'][0]
        self.assertEqual(decision['decision_id'], f'task-{ready_task.id}-consultive-recommendation')
        self.assertEqual(decision['title'], 'Task pronta para decisao')
        self.assertEqual(decision['decision_state'], 'closed')
        self.assertEqual(decision['impact_scope'], 'task_scope_item')
        self.assertEqual(decision['decision_origin'], 'consultive_gate')
        self.assertEqual(decision['recommendation_class'], 'additional_module')
        self.assertEqual(decision['recommended_module'], 'approvals')
        self.assertEqual(
            payload['source_metadata']['source_record_url'],
            f'https://example.test/web#id={self.project.id}&model=project.project',
        )

    def test_decisions_payload_hash_ignores_volatile_sync_metadata(self):
        task = self.create_task(self.project, name='Task hash decisions', pg_scope_sequence=63)
        self.set_task_recommendation(task, recommendation_class='standard')
        task.write({'pg_ai_consultive_gate_notes': 'Fecho pronto.'})
        task.action_mark_ai_consultive_gate_ready()

        payload = self.decisions_builder.build_payload(self.project)
        modified_payload = deepcopy(payload)
        modified_payload['source_metadata']['sync_published_at'] = '2099-12-31 23:59:59'
        modified_payload['source_metadata']['sync_published_by'] = 'Someone Else'
        modified_payload['source_metadata']['sync_trigger'] = 'scheduled'
        modified_payload['source_metadata']['payload_hash'] = 'sha256:changed'

        self.assertEqual(
            self.decisions_builder.payload_hash(payload),
            self.decisions_builder.payload_hash(modified_payload),
        )

    def test_requirements_payload_maps_only_eligible_approved_scope_requirements(self):
        eligible_requirement = self.create_task(
            self.project,
            name='Registar aprovacao de encomendas',
            pg_scope_state='validated',
            pg_scope_summary='A aplicacao deve registar e consultar aprovacoes de encomendas.',
            pg_acceptance_criteria_text='Permitir aprovar encomendas em espera\nConsultar historico de aprovacao',
            pg_requirement_status='approved',
            pg_requirement_priority='high',
            pg_requirement_traceability_refs='FIT-REQ-001\nSTEERING-APR-01',
            pg_scope_sequence=70,
        )
        deferred_requirement = self.create_task(
            self.project,
            name='Automatizar notificacoes de atraso',
            pg_scope_state='deferred',
            pg_scope_summary='A automacao de notificacoes fica registada como requisito adiado.',
            pg_requirement_status='deferred',
            pg_requirement_priority='medium',
            pg_requirement_traceability_refs='BACKLOG-REQ-009',
            pg_scope_sequence=71,
        )
        self.create_task(
            self.project,
            name='Requirement sem owner',
            pg_scope_state='validated',
            pg_requirement_owner_id=False,
            pg_scope_sequence=72,
        )
        self.create_task(
            self.project,
            name='Requirement backlog operacional',
            pg_scope_state='validated',
            pg_scope_track='operational_backlog',
            pg_scope_sequence=73,
        )

        payload = self.requirements_builder.build_payload(self.project)

        self.assertEqual(payload['project_name'], 'Projeto Piloto')
        self.assertEqual(payload['published_requirement_count'], 2)
        self.assertEqual(len(payload['requirements']), 2)

        first_requirement = payload['requirements'][0]
        self.assertEqual(first_requirement['requirement_id'], f'project-task-requirement-{eligible_requirement.id}')
        self.assertEqual(first_requirement['status'], 'approved')
        self.assertEqual(first_requirement['priority'], 'high')
        self.assertEqual(first_requirement['owner'], self.env.user.display_name)
        self.assertEqual(first_requirement['traceability_refs'], ['FIT-REQ-001', 'STEERING-APR-01'])
        self.assertEqual(first_requirement['source_task_id'], eligible_requirement.id)
        self.assertEqual(first_requirement['requirement_origin'], 'approved_scope_task')
        self.assertEqual(
            first_requirement['acceptance_criteria'],
            ['Permitir aprovar encomendas em espera', 'Consultar historico de aprovacao'],
        )

        second_requirement = next(
            item for item in payload['requirements'] if item['source_task_id'] == deferred_requirement.id
        )
        self.assertEqual(second_requirement['status'], 'deferred')
        self.assertEqual(second_requirement['scope_state'], 'deferred')
        self.assertEqual(
            payload['source_metadata']['source_record_url'],
            f'https://example.test/web#id={self.project.id}&model=project.project',
        )

    def test_requirements_payload_hash_ignores_volatile_sync_metadata(self):
        self.create_task(
            self.project,
            name='Requirement hash',
            pg_scope_state='validated',
            pg_scope_sequence=74,
        )

        payload = self.requirements_builder.build_payload(self.project)
        modified_payload = deepcopy(payload)
        modified_payload['source_metadata']['sync_published_at'] = '2099-12-31 23:59:59'
        modified_payload['source_metadata']['sync_published_by'] = 'Someone Else'
        modified_payload['source_metadata']['sync_trigger'] = 'scheduled'
        modified_payload['source_metadata']['payload_hash'] = 'sha256:changed'

        self.assertEqual(
            self.requirements_builder.payload_hash(payload),
            self.requirements_builder.payload_hash(modified_payload),
        )

    def test_risks_payload_maps_only_eligible_official_project_risks(self):
        eligible_risk = self.create_project_risk(
            self.project,
            name='Dependencia de aprovacao do cliente',
            severity='high',
            state='monitoring',
            description='A decisao final do cliente pode atrasar o arranque.',
            mitigation='Agendar follow-up semanal e escalar em caso de atraso.',
            source_reference='Steering committee',
        )
        self.create_project_risk(
            self.project,
            name='Risco fechado',
            state='closed',
        )
        self.create_project_risk(
            self.project,
            name='Risco inativo',
            active=False,
        )

        payload = self.risks_builder.build_payload(self.project)

        self.assertEqual(payload['project_name'], 'Projeto Piloto')
        self.assertEqual(payload['published_risk_count'], 1)
        self.assertEqual(len(payload['risks']), 1)
        risk = payload['risks'][0]
        self.assertEqual(risk['risk_id'], f'project-risk-{eligible_risk.id}')
        self.assertEqual(risk['title'], 'Dependencia de aprovacao do cliente')
        self.assertEqual(risk['severity'], 'high')
        self.assertEqual(risk['status'], 'monitoring')
        self.assertEqual(risk['risk_origin'], 'project_risk_register')
        self.assertEqual(risk['source_risk_id'], eligible_risk.id)
        self.assertEqual(
            payload['source_metadata']['source_record_url'],
            f'https://example.test/web#id={self.project.id}&model=project.project',
        )

    def test_risks_payload_hash_ignores_volatile_sync_metadata(self):
        self.create_project_risk(self.project, name='Risco hash')

        payload = self.risks_builder.build_payload(self.project)
        modified_payload = deepcopy(payload)
        modified_payload['source_metadata']['sync_published_at'] = '2099-12-31 23:59:59'
        modified_payload['source_metadata']['sync_published_by'] = 'Someone Else'
        modified_payload['source_metadata']['sync_trigger'] = 'scheduled'
        modified_payload['source_metadata']['payload_hash'] = 'sha256:changed'

        self.assertEqual(
            self.risks_builder.payload_hash(payload),
            self.risks_builder.payload_hash(modified_payload),
        )

    def test_deliveries_payload_maps_only_eligible_project_milestones(self):
        eligible_delivery = self.create_project_milestone(
            self.project,
            name='Go-live funcional',
            deadline=fields.Date.from_string('2026-04-20'),
            pg_delivery_state='in_progress',
            pg_acceptance_state='pending',
            pg_delivery_source_reference='Plano validado em steering',
        )
        delivered_delivery = self.create_project_milestone(
            self.project,
            name='Migracao concluida',
            deadline=fields.Date.from_string('2026-04-18'),
            pg_delivery_state='delivered',
            pg_acceptance_state='accepted',
        )
        self.create_project_milestone(
            self.project,
            name='Entrega sem owner',
            pg_delivery_owner_id=False,
        )
        self.create_project_milestone(
            self.project,
            name='Entrega sem datas',
            deadline=False,
        ).write({'is_reached': False})

        payload = self.deliveries_builder.build_payload(self.project)

        self.assertEqual(payload['project_name'], 'Projeto Piloto')
        self.assertEqual(payload['published_delivery_count'], 2)
        self.assertEqual(len(payload['deliveries']), 2)

        first_delivery = payload['deliveries'][0]
        self.assertEqual(first_delivery['delivery_id'], f'project-milestone-{delivered_delivery.id}')
        self.assertEqual(first_delivery['delivery_state'], 'delivered')
        self.assertEqual(first_delivery['acceptance_state'], 'accepted')
        self.assertEqual(first_delivery['delivery_origin'], 'project_milestone')
        self.assertEqual(first_delivery['source_milestone_id'], delivered_delivery.id)
        self.assertEqual(first_delivery['planned_date'], '2026-04-18')
        self.assertTrue(first_delivery['actual_date'])

        second_delivery = next(
            item for item in payload['deliveries'] if item['source_milestone_id'] == eligible_delivery.id
        )
        self.assertEqual(second_delivery['title'], 'Go-live funcional')
        self.assertEqual(second_delivery['delivery_state'], 'in_progress')
        self.assertEqual(second_delivery['acceptance_state'], 'pending')
        self.assertEqual(second_delivery['actual_date'], None)
        self.assertEqual(
            payload['source_metadata']['source_record_url'],
            f'https://example.test/web#id={self.project.id}&model=project.project',
        )

    def test_deliveries_payload_hash_ignores_volatile_sync_metadata(self):
        self.create_project_milestone(self.project, name='Entrega hash')

        payload = self.deliveries_builder.build_payload(self.project)
        modified_payload = deepcopy(payload)
        modified_payload['source_metadata']['sync_published_at'] = '2099-12-31 23:59:59'
        modified_payload['source_metadata']['sync_published_by'] = 'Someone Else'
        modified_payload['source_metadata']['sync_trigger'] = 'scheduled'
        modified_payload['source_metadata']['payload_hash'] = 'sha256:changed'

        self.assertEqual(
            self.deliveries_builder.payload_hash(payload),
            self.deliveries_builder.payload_hash(modified_payload),
        )

    def test_project_plan_payload_maps_only_eligible_project_milestones(self):
        eligible_plan = self.create_project_milestone(
            self.project,
            name='Preparacao de dados',
            pg_plan_start_date=fields.Date.from_string('2026-04-10'),
            deadline=fields.Date.from_string('2026-04-15'),
            pg_plan_status='in_progress',
            pg_plan_dependency_refs='REQ-001\nREQ-002',
        )
        completed_plan = self.create_project_milestone(
            self.project,
            name='Go-live',
            pg_plan_start_date=fields.Date.from_string('2026-04-16'),
            deadline=fields.Date.from_string('2026-04-20'),
            pg_plan_status='completed',
            pg_plan_dependency_refs='',
        )
        self.create_project_milestone(
            self.project,
            name='Plano sem owner',
            pg_plan_owner_id=False,
        )
        self.create_project_milestone(
            self.project,
            name='Plano sem inicio',
            pg_plan_start_date=False,
        )

        payload = self.plan_builder.build_payload(self.project)

        self.assertEqual(payload['project_name'], 'Projeto Piloto')
        self.assertEqual(payload['published_plan_item_count'], 2)
        self.assertEqual(len(payload['plan_items']), 2)
        self.assertEqual(payload['go_live_target'], None)

        first_item = payload['plan_items'][0]
        self.assertEqual(first_item['plan_item_id'], f'project-plan-milestone-{eligible_plan.id}')
        self.assertEqual(first_item['item_type'], 'milestone')
        self.assertEqual(first_item['status'], 'in_progress')
        self.assertEqual(first_item['planned_start'], '2026-04-10')
        self.assertEqual(first_item['planned_end'], '2026-04-15')
        self.assertEqual(first_item['dependency_refs'], ['REQ-001', 'REQ-002'])
        self.assertEqual(first_item['plan_origin'], 'project_milestone_baseline')

        second_item = next(item for item in payload['plan_items'] if item['source_milestone_id'] == completed_plan.id)
        self.assertEqual(second_item['status'], 'completed')
        self.assertEqual(second_item['dependency_refs'], [])
        self.assertEqual(
            payload['source_metadata']['source_record_url'],
            f'https://example.test/web#id={self.project.id}&model=project.project',
        )

    def test_project_plan_payload_hash_ignores_volatile_sync_metadata(self):
        self.create_project_milestone(self.project, name='Plano hash')

        payload = self.plan_builder.build_payload(self.project)
        modified_payload = deepcopy(payload)
        modified_payload['source_metadata']['sync_published_at'] = '2099-12-31 23:59:59'
        modified_payload['source_metadata']['sync_published_by'] = 'Someone Else'
        modified_payload['source_metadata']['sync_trigger'] = 'scheduled'
        modified_payload['source_metadata']['payload_hash'] = 'sha256:changed'

        self.assertEqual(
            self.plan_builder.payload_hash(payload),
            self.plan_builder.payload_hash(modified_payload),
        )

    def test_budget_payload_maps_only_eligible_project_budget_lines(self):
        eligible_line = self.create_project_budget_line(
            self.project,
            category='Consulting Services',
            planned_amount=2500.0,
            approved_amount=2200.0,
            consumed_amount=500.0,
            status='consuming',
            notes='Baseline aprovada em steering.',
        )
        closed_line = self.create_project_budget_line(
            self.project,
            category='Licensing',
            planned_amount=900.0,
            approved_amount=900.0,
            consumed_amount=900.0,
            status='closed',
            notes='',
        )
        other_project = self.create_project(
            self.repository,
            name='Projeto Budget Secundario',
        )
        self.create_project_budget_line(
            other_project,
            category='Outro projeto',
        )
        self.create_project_budget_line(
            self.project,
            category='Inativa',
            active=False,
        )

        payload = self.budget_builder.build_payload(self.project)

        self.assertEqual(payload['project_name'], 'Projeto Piloto')
        self.assertEqual(payload['budget_currency'], self.env.company.currency_id.name)
        self.assertEqual(payload['budget_owner'], self.env.user.display_name)
        self.assertEqual(payload['baseline_status'], 'approved')
        self.assertEqual(payload['published_budget_line_count'], 2)
        self.assertEqual(len(payload['budget_lines']), 2)

        first_line = payload['budget_lines'][0]
        self.assertEqual(first_line['budget_line_id'], f'project-budget-line-{eligible_line.id}')
        self.assertEqual(first_line['category'], 'Consulting Services')
        self.assertEqual(first_line['planned_amount'], 2500.0)
        self.assertEqual(first_line['approved_amount'], 2200.0)
        self.assertEqual(first_line['consumed_amount'], 500.0)
        self.assertEqual(first_line['status'], 'consuming')
        self.assertEqual(first_line['owner'], self.env.user.display_name)
        self.assertEqual(first_line['budget_origin'], 'project_budget_register')
        self.assertEqual(first_line['source_budget_line_id'], eligible_line.id)
        self.assertEqual(first_line['notes'], 'Baseline aprovada em steering.')

        second_line = next(item for item in payload['budget_lines'] if item['source_budget_line_id'] == closed_line.id)
        self.assertEqual(second_line['status'], 'closed')
        self.assertEqual(second_line['notes'], '')
        self.assertEqual(
            payload['source_metadata']['source_record_url'],
            f'https://example.test/web#id={self.project.id}&model=project.project',
        )

    def test_budget_payload_hash_ignores_volatile_sync_metadata(self):
        self.create_project_budget_line(self.project, category='Budget hash')

        payload = self.budget_builder.build_payload(self.project)
        modified_payload = deepcopy(payload)
        modified_payload['source_metadata']['sync_published_at'] = '2099-12-31 23:59:59'
        modified_payload['source_metadata']['sync_published_by'] = 'Someone Else'
        modified_payload['source_metadata']['sync_trigger'] = 'scheduled'
        modified_payload['source_metadata']['payload_hash'] = 'sha256:changed'

        self.assertEqual(
            self.budget_builder.payload_hash(payload),
            self.budget_builder.payload_hash(modified_payload),
        )

    def test_status_payload_maps_operational_fields(self):
        payload = self.status_builder.build_payload(
            self.project,
            trigger_type='manual_button',
            trigger_model='project.project',
            trigger_record_id=self.project.id,
        )

        self.assertEqual(payload['project_name'], 'Projeto Piloto')
        self.assertEqual(payload['phase'], 'discovery')
        self.assertEqual(payload['status_summary'], 'Projeto em validacao automatizada.')
        self.assertEqual(payload['milestones'], ['Instalacao validada', 'Upgrade validado'])
        self.assertEqual(payload['blockers'], ['Sem bloqueios'])
        self.assertEqual(payload['risks'], ['Risco controlado de regressao'])
        self.assertEqual(payload['next_steps'], ['Executar testes', 'Publicar conclusoes'])
        self.assertEqual(payload['pending_decisions'], ['Decidir status sync recorrente'])
        self.assertEqual(payload['owner'], self.env.user.display_name)
        self.assertEqual(
            payload['source_record_url'],
            f'https://example.test/web#id={self.project.id}&model=project.project',
        )

    def test_status_payload_cleans_placeholders_mojibake_and_repeated_lines(self):
        project = self.create_project(
            self.repository,
            name='Projeto Hygiene',
            pg_status_summary='IntegraÃ§Ã£o pronta para validaÃ§Ã£o.',
            pg_status_milestones_text='[PONTO POR VALIDAR]\nMarco validado\nMarco validado',
            pg_status_blockers_text='Blocked until customer approval.\nBest regards,\nPM',
            pg_status_risks_text='Risco de atraso tecnico ' * 20,
            pg_status_next_steps_text='Validar deploy em producao\nOn Tue, 2 Apr 2026 at 10:00, Customer wrote:\nAprovar deploy',
            pg_status_pending_decisions_text='[PREENCHER]\nConfirmar data de go-live',
        )

        payload = self.status_builder.build_payload(project)

        self.assertEqual(payload['status_summary'], 'IntegraÃ§Ã£o pronta para validaÃ§Ã£o.')
        self.assertEqual(payload['milestones'], ['Marco validado'])
        self.assertEqual(payload['blockers'], ['Blocked until customer approval.'])
        self.assertEqual(payload['next_steps'], ['Validar deploy em producao'])
        self.assertEqual(payload['pending_decisions'], ['Confirmar data de go-live'])
        self.assertEqual(len(payload['risks']), 1)
        self.assertLessEqual(len(payload['risks'][0]), 220)
        self.assertTrue(payload['risks'][0].endswith('...'))

    def test_status_payload_drops_workflow_and_self_referential_publication_lines(self):
        project = self.create_project(
            self.repository,
            name='Projeto Status Oficial',
            pg_status_summary=(
                'Project Projeto Status Oficial is currently in Implementation. '
                'Latest status publication status: Never. '
                'Operational status changed since the last manual publication and should be reviewed. '
                'Approved scope still needs consolidation for 3 task(s).'
            ),
            pg_status_milestones_text='No status snapshot has been published yet.\nMarco validado',
            pg_status_risks_text=(
                'The published operational status may be stale because new project updates were not published yet.\n'
                'Risco de atraso tecnico'
            ),
            pg_status_next_steps_text=(
                'Review this draft with the project manager before publishing the official status snapshot.\n'
                'Apply the draft to the operational status fields and publish manually once validated.\n'
                'Publish a fresh manual status snapshot after validating blockers, risks and next steps.\n'
                'Validar backlog operacional'
            ),
        )

        payload = self.status_builder.build_payload(project)

        self.assertNotIn('Latest status publication status: Never', payload['status_summary'])
        self.assertNotIn('Operational status changed since the last manual publication', payload['status_summary'])
        self.assertEqual(payload['milestones'], ['Marco validado'])
        self.assertEqual(payload['risks'], ['Risco de atraso tecnico'])
        self.assertEqual(payload['next_steps'], ['Validar backlog operacional'])

    def test_status_payload_hash_ignores_volatile_sync_metadata(self):
        payload = self.status_builder.build_payload(self.project)
        modified_payload = deepcopy(payload)
        modified_payload['sync_published_at'] = '2099-12-31 23:59:59'
        modified_payload['sync_published_by'] = 'Someone Else'
        modified_payload['sync_trigger'] = 'scheduled'

        self.assertEqual(
            self.status_builder.payload_hash(payload),
            self.status_builder.payload_hash(modified_payload),
        )
