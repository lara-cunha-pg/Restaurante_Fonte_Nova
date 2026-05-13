from odoo.tests import TransactionCase, tagged

from .common import PgAiDevAssistantTestMixin


@tagged('post_install', '-at_install')
class TestMirrorOperationalEligibility(PgAiDevAssistantTestMixin, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.set_pg_base_url()
        cls.repository = cls.create_repository(name='mirror_operational_eligibility_repo')

    def test_task_marks_weak_name_and_missing_description_as_not_eligible(self):
        project = self.create_project(self.repository, name='Projeto Task Eligibility')
        task = self.create_task(
            project,
            name='Agendamento',
            description='<p> </p>',
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )

        self.assertEqual(task.pg_mirror_task_eligibility_status, 'not_eligible')
        self.assertGreaterEqual(task.pg_mirror_task_eligibility_warning_count, 2)
        self.assertIn('weak_name', task.pg_mirror_task_eligibility_feedback)
        self.assertIn('missing_description', task.pg_mirror_task_eligibility_feedback)

    def test_task_marks_compound_item_as_eligible_with_warnings(self):
        project = self.create_project(self.repository, name='Projeto Compound Eligibility')
        task = self.create_task(
            project,
            name='Automatizar expedicao total',
            description=(
                '<p>Corrigir importacao de encomendas em curso.</p>'
                '<p>Alterar arrastar tarefa para producao quando a rota nao esta definida.</p>'
                '<p>Alterar campo de mapeamento de seccao para obrigatorio.</p>'
            ),
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )

        self.assertEqual(task.pg_mirror_task_eligibility_status, 'eligible_with_warnings')
        self.assertGreaterEqual(task.pg_mirror_task_eligibility_warning_count, 1)
        self.assertIn('compound_item', task.pg_mirror_task_eligibility_feedback)

    def test_project_aggregates_task_and_milestone_operational_eligibility_signals(self):
        project = self.create_project(
            self.repository,
            name='Projeto Operational Eligibility',
            allow_milestones=True,
        )
        milestone = self.create_project_milestone(
            project,
            name='Go Live sem owner',
            pg_plan_owner_id=False,
            pg_plan_status='in_progress',
        )
        task = self.create_task(
            project,
            name='Agendamento',
            description='<p> </p>',
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )
        task.with_context(
            pg_skip_scope_sync_enqueue=True,
            pg_skip_mirror_sync_enqueue=True,
        ).write({'milestone_id': milestone.id})
        project = self.env['project.project'].browse(project.id)

        self.assertEqual(project.pg_mirror_operational_eligibility_status, 'not_eligible')
        self.assertGreaterEqual(project.pg_mirror_operational_eligibility_not_eligible_count, 1)
        self.assertGreaterEqual(project.pg_mirror_operational_eligibility_warning_count, 3)
        self.assertIn('Not eligible tasks', project.pg_mirror_operational_eligibility_feedback)
        self.assertIn('Open milestones without owner', project.pg_mirror_operational_eligibility_feedback)

    def test_project_operational_eligibility_has_safe_fallback_when_task_helper_is_missing(self):
        project = self.create_project(
            self.repository,
            name='Projeto Eligibility Fallback',
            allow_milestones=True,
        )
        self.create_task(
            project,
            name='Kick Off',
            description='<p> </p>',
            pg_scope_summary=False,
            pg_acceptance_criteria_text=False,
        )

        task_model = type(project.task_ids[:1])
        had_local_helper = '_pg_mirror_task_eligibility_review' in task_model.__dict__
        original_helper = task_model.__dict__.get('_pg_mirror_task_eligibility_review')
        setattr(task_model, '_pg_mirror_task_eligibility_review', None)
        try:
            project = self.env['project.project'].browse(project.id)
            self.assertEqual(project.pg_mirror_operational_eligibility_status, 'not_eligible')
            self.assertIn('Not eligible tasks', project.pg_mirror_operational_eligibility_feedback)
        finally:
            if had_local_helper:
                setattr(task_model, '_pg_mirror_task_eligibility_review', original_helper)
            else:
                delattr(task_model, '_pg_mirror_task_eligibility_review')
