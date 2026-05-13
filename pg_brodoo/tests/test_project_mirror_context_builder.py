from odoo.fields import Command
from odoo.tests import TransactionCase, tagged

from ..services.project_mirror_context_builder import ProjectMirrorContextBuilder
from ..services.project_mirror_payload_builder import ProjectMirrorPayloadBuilder
from .common import PgAiDevAssistantTestMixin


@tagged('post_install', '-at_install')
class TestProjectMirrorContextBuilder(PgAiDevAssistantTestMixin, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.set_pg_base_url()
        cls.repository = cls.create_repository()
        cls.project = cls.create_project(
            cls.repository,
            partner_id=cls.env.company.partner_id.id,
        )
        cls.task = cls.create_task(
            cls.project,
            name='Corrigir template de importacao de orcamento',
            description='<p>Corrigir template de importacao usado no arranque.</p>',
            priority='3',
        )
        cls.milestone = cls.create_project_milestone(
            cls.project,
            name='Go-live comercial',
            pg_plan_dependency_refs='Aprovar template\nValidar dados',
        )
        cls.task.write({'milestone_id': cls.milestone.id})
        cls.customer_message = cls.create_chatter_message(
            'project.task',
            cls.task.id,
            '<p>Cliente validou o arranque do template.</p>',
            subtype_xmlid='mail.mt_comment',
        )
        cls.internal_note = cls.create_chatter_message(
            'project.project',
            cls.project.id,
            '<p>Nota interna sobre risco de regressao.</p>',
            subtype_xmlid='mail.mt_note',
        )
        cls.customer_partner = cls.env['res.partner'].create({'name': 'ANCORA VIP INDUSTRY LDA'})
        cls.external_internal_note = cls.create_chatter_message(
            'project.project',
            cls.project.id,
            '<p>Boa tarde Bruno. Conforme combinado envio o ficheiro excel em anexo.</p>',
            subtype_xmlid='mail.mt_note',
            author_partner=cls.customer_partner,
        )
        cls.low_signal_customer_message = cls.create_chatter_message(
            'project.task',
            cls.task.id,
            '<p>Bom dia. Obrigado pelo update.</p>',
            subtype_xmlid='mail.mt_comment',
        )
        cls.high_signal_customer_message = cls.create_chatter_message(
            'project.task',
            cls.task.id,
            '<p>Blocked until the customer confirms the final API credentials for go-live.</p>',
            subtype_xmlid='mail.mt_comment',
        )
        cls.attachment = cls.create_attachment(cls.customer_message, name='email_cliente.pdf', mimetype='application/pdf')
        cls.noisy_image_attachment = cls.create_attachment(
            cls.project,
            name='image005.png',
            mimetype='image/png',
        )
        cls.noisy_bare_image_attachment = cls.create_attachment(
            cls.project,
            name='image3',
            mimetype='image/png',
        )
        cls.customer_message.write({'attachment_ids': [Command.set([cls.attachment.id])]})
        cls.payload_builder = ProjectMirrorPayloadBuilder(cls.env)
        cls.context_builder = ProjectMirrorContextBuilder()

    def test_build_context_markdown_uses_only_mirror_payloads(self):
        project_payload = self.payload_builder.build_project_payload(self.project)
        planning_payload = self.payload_builder.build_planning_payload(self.project)
        tasks_payload = self.payload_builder.build_tasks_payload(self.project)
        chatter_payload = self.payload_builder.build_chatter_payload(self.project)
        attachments_payload = self.payload_builder.build_attachments_payload(self.project)
        history_event = self.payload_builder.build_history_event(
            self.project,
            event_type='task.updated',
            entity_model='project.task',
            entity_id=self.task.id,
            summary='Tarefa atualizada apos validacao do cliente.',
            event_data={'field': 'stage_id'},
            trigger_type='task_write',
        )

        context = self.context_builder.build_context_markdown(
            project_payload,
            planning_payload,
            tasks_payload,
            chatter_payload,
            attachments_payload,
            history_events=[history_event],
        )

        self.assertIn('# PG_CONTEXT - Contexto Global do Projeto', context)
        self.assertIn('## 1. Contexto Estrutural', context)
        self.assertIn('## 2. Planeamento', context)
        self.assertIn('## 3. Operacao Atual', context)
        self.assertIn('## 4. Comunicacoes e Historico Recente', context)
        self.assertIn('Projeto Piloto', context)
        self.assertIn('Go-live comercial', context)
        self.assertIn('Corrigir template de importacao de orcamento', context)
        self.assertIn('Cliente validou o arranque do template.', context)
        self.assertIn('Nota interna sobre risco de regressao.', context)
        self.assertIn('email_cliente.pdf', context)
        self.assertIn('task.updated', context)
        self.assertIn('Mensagens com cliente: 4', context)
        self.assertIn('Notas internas: 1', context)
        self.assertNotIn('/web/content/', context)
        self.assertNotIn('image005.png', context)
        self.assertNotIn('image3', context)

    def test_build_context_markdown_prioritizes_high_signal_messages_and_uses_compact_format(self):
        project_payload = self.payload_builder.build_project_payload(self.project)
        planning_payload = self.payload_builder.build_planning_payload(self.project)
        tasks_payload = self.payload_builder.build_tasks_payload(self.project)
        chatter_payload = self.payload_builder.build_chatter_payload(self.project)
        attachments_payload = self.payload_builder.build_attachments_payload(self.project)

        context = self.context_builder.build_context_markdown(
            project_payload,
            planning_payload,
            tasks_payload,
            chatter_payload,
            attachments_payload,
            history_events=[],
        )

        self.assertIn('Blocked until the customer confirms the final API credentials for go-live.', context)
        self.assertIn('Cliente validou o arranque do template.', context)
        self.assertIn('Boa tarde Bruno. Conforme combinado envio o ficheiro excel em anexo.', context)
        self.assertIn('email_cliente.pdf', context)
        self.assertNotIn('image005.png', context)
        self.assertNotIn('image3', context)
        self.assertNotIn('project.task:', context)
        self.assertNotIn('Bom dia. Obrigado pelo update.', context)

    def test_build_context_markdown_reapplies_conservative_scope_curation(self):
        project_payload = self.payload_builder.build_project_payload(self.project)
        project_payload['project']['included_scope'] = [
            'Criar utilizadores; Configurar permissoes; Validar acessos',
            'Fico a aguardar feedback da vossa parte.',
            'Rui Ribeiro',
            'Rua do Bairro da Boavista Freamunde',
            'Avenida Central 145 Freamunde',
            'comercial@ancoravip.pt',
            'Testar e',
            'Fiquei de lhe enviar um email informativo sobre este assunto.',
            'Arvore de categorias (Inventario)',
        ]
        planning_payload = self.payload_builder.build_planning_payload(self.project)
        tasks_payload = self.payload_builder.build_tasks_payload(self.project)
        chatter_payload = self.payload_builder.build_chatter_payload(self.project)
        attachments_payload = self.payload_builder.build_attachments_payload(self.project)

        context = self.context_builder.build_context_markdown(
            project_payload,
            planning_payload,
            tasks_payload,
            chatter_payload,
            attachments_payload,
            history_events=[],
        )

        self.assertIn('Criar utilizadores', context)
        self.assertIn('Configurar permissoes', context)
        self.assertIn('Validar acessos', context)
        self.assertNotIn('Fico a aguardar feedback da vossa parte.', context)
        self.assertNotIn('Rui Ribeiro', context)
        self.assertNotIn('Rua do Bairro da Boavista Freamunde', context)
        self.assertNotIn('Avenida Central 145 Freamunde', context)
        self.assertNotIn('comercial@ancoravip.pt', context)
        self.assertNotIn('Testar e', context)
        self.assertNotIn('Fiquei de lhe enviar um email informativo sobre este assunto.', context)
        self.assertNotIn('Arvore de categorias (Inventario)', context)

    def test_build_context_markdown_renders_factual_scope_backlog_section(self):
        project_payload = self.payload_builder.build_project_payload(self.project)
        project_payload['project']['factual_scope_backlog'] = [
            {
                'item': 'Formacao CRM',
                'reason': 'weak_nominal_item',
                'reason_label': 'Item nominal fraco',
                'source_label': 'Formacao CRM',
            },
            {
                'item': 'Incluir nome do cliente do registo do projeto Ao finalizar producao no chao de fabrica registar automaticamente a expedicao.',
                'reason': 'compound_item',
                'reason_label': 'Item composto',
                'source_label': 'Backlog composto',
            },
        ]
        project_payload['project']['scope_quality_review'] = {
            'included_scope_count': 1,
            'factual_scope_backlog_count': 2,
            'excluded_noise_count': 3,
            'curation_reason_counts': {
                'weak_nominal_item': 1,
                'compound_item': 1,
            },
        }
        planning_payload = self.payload_builder.build_planning_payload(self.project)
        tasks_payload = self.payload_builder.build_tasks_payload(self.project)
        chatter_payload = self.payload_builder.build_chatter_payload(self.project)
        attachments_payload = self.payload_builder.build_attachments_payload(self.project)

        context = self.context_builder.build_context_markdown(
            project_payload,
            planning_payload,
            tasks_payload,
            chatter_payload,
            attachments_payload,
            history_events=[],
        )

        self.assertIn('### Itens factuais a curar no Odoo', context)
        self.assertIn('Total no ambito curado: 1', context)
        self.assertIn('Total pendente de curadoria: 2', context)
        self.assertIn('Ruido excluido na curadoria: 3', context)
        self.assertIn('Motivos dominantes de curadoria pendente:', context)
        self.assertIn('Item nominal fraco: 1, Item composto: 1', context)
        self.assertIn('Formacao CRM | motivo: Item nominal fraco', context)
        self.assertIn('Backlog composto', context)
