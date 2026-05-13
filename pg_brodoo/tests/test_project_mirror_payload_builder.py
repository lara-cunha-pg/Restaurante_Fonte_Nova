from odoo.fields import Command
from odoo.tests import TransactionCase, tagged

from ..services.project_mirror_payload_builder import ProjectMirrorPayloadBuilder
from .common import PgAiDevAssistantTestMixin


@tagged('post_install', '-at_install')
class TestProjectMirrorPayloadBuilder(PgAiDevAssistantTestMixin, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.set_pg_base_url()
        cls.repository = cls.create_repository()
        cls.project = cls.create_project(
            cls.repository,
            partner_id=cls.env.company.partner_id.id,
        )
        cls.create_scope_line(cls.project, 'integrations', 'GitHub ancoravip')
        cls.create_scope_line(cls.project, 'documents', 'Orcamento adjudicado')
        cls.create_scope_line(cls.project, 'approvals', 'Aprovacao do template pelo cliente')
        cls.task = cls.create_task(
            cls.project,
            name='Corrigir template de importacao de orcamento',
            description='<p>Corrigir o mapeamento do template de importacao de orcamento.</p>',
            priority='3',
        )
        cls.excluded_task = cls.create_task(
            cls.project,
            name='Fornecimento de hardware',
            pg_scope_summary='Hardware de postos de trabalho',
            pg_scope_state='excluded',
        )
        cls.milestone = cls.create_project_milestone(
            cls.project,
            name='Go-live comercial',
            pg_plan_dependency_refs='Aprovar template\nValidar dados',
        )
        cls.task.write({'milestone_id': cls.milestone.id})
        cls.message = cls.create_chatter_message(
            'project.task',
            cls.task.id,
            '<p>Cliente validou a necessidade de corrigir o template.</p>',
            subtype_xmlid='mail.mt_comment',
        )
        cls.note = cls.create_chatter_message(
            'project.project',
            cls.project.id,
            '<p>Nota interna sobre risco de regressao.</p>',
            subtype_xmlid='mail.mt_note',
        )
        cls.customer_partner = cls.env['res.partner'].create({'name': 'ANCORA VIP INDUSTRY LDA'})
        cls.external_internal_note = cls.create_chatter_message(
            'project.project',
            cls.project.id,
            '<p>Boa tarde Bruno. Conforme combinado envio o ficheiro para validacao.</p>',
            subtype_xmlid='mail.mt_note',
            author_partner=cls.customer_partner,
        )
        cls.noisy_notification = cls.create_chatter_message(
            'project.project',
            cls.project.id,
            '<div summary="o_mail_notification"><p>Uma nova tarefa foi criada no projeto "Projeto Piloto".</p></div>',
            message_type='notification',
            subtype_xmlid='mail.mt_comment',
        )
        cls.quoted_email = cls.create_chatter_message(
            'project.task',
            cls.task.id,
            """
                <p>Blocked until the customer shares the API credentials.</p>
                <p>Best regards,<br/>Project Manager</p>
                <p>On Tue, 2 Apr 2026 at 10:00, Customer wrote:</p>
                <blockquote><p>Approved for production.</p></blockquote>
            """,
            message_type='email',
            subtype_xmlid='mail.mt_comment',
        )
        cls.tracking_comment = cls.create_chatter_message(
            'project.task',
            cls.task.id,
            '<p>Deadline changed from 2026-04-20 to 2026-04-25.</p>',
            subtype_xmlid='mail.mt_comment',
        )
        cls.notification_wrapper_comment = cls.create_chatter_message(
            'project.task',
            cls.task.id,
            '<div class="o_mail_notification"><p>Assigned to Project Manager</p></div>',
            subtype_xmlid='mail.mt_comment',
        )
        cls.attachment = cls.create_attachment(
            cls.task,
            name='template_importacao.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        cls.message_attachment = cls.create_attachment(
            cls.message,
            name='email_cliente.pdf',
            mimetype='application/pdf',
        )
        cls.notification_attachment = cls.create_attachment(
            cls.noisy_notification,
            name='ruido_notification.pdf',
            mimetype='application/pdf',
        )
        cls.tracking_attachment = cls.create_attachment(
            cls.tracking_comment,
            name='tracking_noise.txt',
            mimetype='text/plain',
        )
        cls.wrapper_attachment = cls.create_attachment(
            cls.notification_wrapper_comment,
            name='wrapper_noise.txt',
            mimetype='text/plain',
        )
        cls.message.write({'attachment_ids': [Command.set([cls.attachment.id])]})
        cls.builder = ProjectMirrorPayloadBuilder(cls.env)

    def test_build_project_payload_matches_new_contract(self):
        payload = self.builder.build_project_payload(self.project)

        self.assertEqual(payload['schema_version'], '1.0')
        self.assertEqual(payload['project']['odoo_model'], 'project.project')
        self.assertEqual(payload['project']['name'], 'Projeto Piloto')
        self.assertEqual(payload['project']['repository_full_name'], self.repository.full_name)
        self.assertIn('Resumo funcional de teste.', payload['project']['included_scope'])
        self.assertIn('Hardware de postos de trabalho', payload['project']['included_scope'])
        self.assertEqual(payload['project']['factual_scope_backlog'], [])
        self.assertEqual(payload['project']['excluded_scope'], ['Hardware de postos de trabalho'])
        self.assertEqual(payload['project']['deliverables'], ['Go-live comercial'])
        self.assertEqual(
            payload['project']['stakeholders'],
            [self.env.company.partner_id.display_name, self.env.user.display_name],
        )
        self.assertEqual(payload['project']['project_lists']['integrations'], ['GitHub ancoravip'])
        self.assertEqual(payload['project']['project_lists']['documents'], ['Orcamento adjudicado'])
        self.assertEqual(
            payload['project']['project_lists']['approvals'],
            ['Aprovacao do template pelo cliente'],
        )
        self.assertEqual(payload['project']['governance']['standard_allowed'], 'yes')
        self.assertEqual(payload['project']['scope_quality_review']['included_scope_count'], 2)
        self.assertEqual(payload['project']['scope_quality_review']['factual_scope_backlog_count'], 0)
        self.assertEqual(payload['project']['scope_quality_review']['excluded_noise_count'], 0)
        self.assertIn(
            'Ambito curado pronto no espelho: 2 item(s).',
            payload['project']['scope_quality_review']['scope_signal_feedback'],
        )
        self.assertTrue(payload['source_metadata']['payload_hash'].startswith('sha256:'))

    def test_build_project_payload_derives_status_summary_when_manual_summary_is_missing(self):
        self.project.write({'pg_status_summary': False})

        payload = self.builder.build_project_payload(self.project)

        self.assertIn('Project currently in stage', payload['project']['status_summary'])
        self.assertIn('Open tasks:', payload['project']['status_summary'])

    def test_publishable_scope_line_drops_not_eligible_technical_noise(self):
        self.assertFalse(self.builder._publishable_scope_line('Whatsapp'))
        self.assertFalse(self.builder._publishable_scope_line('WhatsApp Business'))
        self.assertFalse(self.builder._publishable_scope_line('Template Orcamento - Odoo Import V2.2.xlsm'))
        self.assertFalse(self.builder._publishable_scope_line('Email Odoo Security'))
        self.assertFalse(
            self.builder._publishable_scope_line(
                'ANCORA VIP INDUSTRY, LDA. Unidade2 Rua do Bairro da Boavista Mail geral@ancoravip.pt'
            )
        )

    def test_build_planning_payload_includes_milestones(self):
        payload = self.builder.build_planning_payload(self.project)

        self.assertEqual(payload['planning']['milestone_count'], 1)
        self.assertEqual(payload['planning']['milestones'][0]['name'], 'Go-live comercial')
        self.assertEqual(
            payload['planning']['milestones'][0]['dependencies'],
            ['Aprovar template', 'Validar dados'],
        )
        self.assertEqual(payload['planning']['next_milestone']['odoo_id'], self.milestone.id)
        self.assertEqual(payload['planning']['planning_summary']['next_milestone_id'], self.milestone.id)
        self.assertEqual(payload['planning']['planning_summary']['open_task_count'], 2)
        self.assertEqual(payload['planning']['planning_summary']['open_tasks_for_next_milestone_count'], 1)
        self.assertEqual(
            payload['planning']['planning_summary']['open_tasks_for_next_milestone'][0]['name'],
            'Corrigir template de importacao de orcamento',
        )
        self.assertEqual(
            payload['planning']['planning_summary']['open_high_priority_tasks'][0]['name'],
            'Corrigir template de importacao de orcamento',
        )

    def test_build_planning_payload_prefers_first_unreached_milestone_when_plan_status_is_inconsistent(self):
        self.milestone.write({'is_reached': True})
        next_real_milestone = self.create_project_milestone(
            self.project,
            name='Integracao com processos produtivos',
            sequence=self.milestone.sequence + 1,
            deadline=self.milestone.deadline,
            pg_plan_status='planned',
        )

        payload = self.builder.build_planning_payload(self.project)

        self.assertEqual(payload['planning']['next_milestone']['odoo_id'], next_real_milestone.id)
        self.assertEqual(
            payload['planning']['planning_summary']['next_milestone_id'],
            next_real_milestone.id,
        )

    def test_build_planning_payload_prefers_active_milestone_with_open_tasks_over_earlier_placeholder(self):
        self.milestone.write({
            'sequence': 20,
            'deadline': '2026-04-20',
            'pg_plan_status': 'in_progress',
            'pg_delivery_state': 'in_progress',
        })
        earlier_placeholder = self.create_project_milestone(
            self.project,
            name='Kickoff administrativo',
            sequence=10,
            deadline='2026-04-10',
            pg_plan_status='planned',
            pg_delivery_state='planned',
        )

        payload = self.builder.build_planning_payload(self.project)

        self.assertEqual(payload['planning']['next_milestone']['odoo_id'], self.milestone.id)
        self.assertEqual(payload['planning']['planning_summary']['next_milestone_id'], self.milestone.id)
        self.assertNotEqual(payload['planning']['next_milestone']['odoo_id'], earlier_placeholder.id)
        self.assertEqual(payload['planning']['planning_summary']['open_tasks_for_next_milestone_count'], 1)

    def test_build_tasks_payload_includes_scope_and_assignment_fields(self):
        payload = self.builder.build_tasks_payload(self.project)

        self.assertEqual(payload['task_count'], 2)
        task_payload = next(task for task in payload['tasks'] if task['odoo_id'] == self.task.id)
        self.assertEqual(task_payload['odoo_model'], 'project.task')
        self.assertEqual(task_payload['name'], 'Corrigir template de importacao de orcamento')
        self.assertEqual(task_payload['scope_track'], 'approved_scope')
        self.assertEqual(task_payload['scope_summary'], 'Resumo funcional de teste.')
        self.assertEqual(task_payload['assignees'], [self.env.user.display_name])

    def test_build_chatter_payload_includes_all_messages_with_content(self):
        payload = self.builder.build_chatter_payload(self.project)

        message_ids_in_payload = {message['odoo_id'] for message in payload['messages']}
        self.assertIn(self.message.id, message_ids_in_payload)
        self.assertIn(self.note.id, message_ids_in_payload)
        self.assertIn(self.external_internal_note.id, message_ids_in_payload)
        self.assertIn(self.quoted_email.id, message_ids_in_payload)
        self.assertIn(self.tracking_comment.id, message_ids_in_payload)
        self.assertIn(self.notification_wrapper_comment.id, message_ids_in_payload)
        self.assertIn(self.noisy_notification.id, message_ids_in_payload)

        entry_types = {message['odoo_id']: message['entry_type'] for message in payload['messages']}
        self.assertEqual(entry_types[self.message.id], 'customer_message')
        self.assertEqual(entry_types[self.note.id], 'internal_note')
        self.assertEqual(entry_types[self.external_internal_note.id], 'customer_message')

        customer_message = next(
            message for message in payload['messages'] if message['odoo_id'] == self.message.id
        )
        self.assertEqual(customer_message['attachments'][0]['name'], 'template_importacao.xlsx')

        quoted_email = next(
            message for message in payload['messages'] if message['odoo_id'] == self.quoted_email.id
        )
        self.assertIn('Blocked until the customer shares the API credentials.', quoted_email['body'])

    def test_build_attachments_payload_includes_all_message_attachments(self):
        payload = self.builder.build_attachments_payload(self.project)

        attachment_names = [attachment['name'] for attachment in payload['attachments']]
        self.assertIn('template_importacao.xlsx', attachment_names)
        self.assertIn('email_cliente.pdf', attachment_names)
        self.assertIn('ruido_notification.pdf', attachment_names)
        self.assertIn('tracking_noise.txt', attachment_names)
        self.assertIn('wrapper_noise.txt', attachment_names)

        attachment_payload = next(
            attachment for attachment in payload['attachments']
            if attachment['name'] == 'template_importacao.xlsx'
        )
        self.assertEqual(attachment_payload['odoo_model'], 'ir.attachment')
        self.assertIn('/web/content/', attachment_payload['download_url'])
        self.assertFalse('datas' in attachment_payload)

    def test_build_history_event_produces_append_only_contract(self):
        payload = self.builder.build_history_event(
            self.project,
            event_type='task.updated',
            entity_model='project.task',
            entity_id=self.task.id,
            summary='Tarefa atualizada apos validacao do cliente.',
            event_data={'field': 'stage_id'},
            trigger_type='task_write',
        )

        self.assertEqual(payload['schema_version'], '1.0')
        self.assertEqual(payload['event_type'], 'task.updated')
        self.assertEqual(payload['entity']['odoo_model'], 'project.task')
        self.assertEqual(payload['entity']['odoo_id'], self.task.id)
        self.assertEqual(payload['event_data'], {'field': 'stage_id'})
