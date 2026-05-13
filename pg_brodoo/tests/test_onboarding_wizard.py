from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from ..services.github_service import GitHubService
from .common import PgAiDevAssistantTestMixin


@tagged('post_install', '-at_install')
class TestOnboardingWizard(PgAiDevAssistantTestMixin, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.set_pg_base_url()
        cls.repository = cls.create_repository(name='wizard_repo')
        cls.branch = cls.create_repository_branch(cls.repository, name='teste', is_default=True)
        cls.project = cls.create_project(
            cls.repository,
            name='Projeto Wizard Test',
            pg_repository_id=False,
            pg_repo_branch=False,
            pg_scope_sync_enabled=False,
            pg_status_sync_enabled=False,
            pg_decisions_sync_enabled=False,
            pg_risks_sync_enabled=False,
            pg_deliveries_sync_enabled=False,
            pg_requirements_sync_enabled=False,
            pg_project_plan_sync_enabled=False,
            pg_budget_sync_enabled=False,
            pg_status_owner_id=False,
        )

    def _create_wizard(self, **overrides):
        values = {
            'github_token': 'ghp_test',
            'github_default_owner': 'bruno-pinheiro-pg',
            'github_default_branch': 'teste',
            'project_id': self.project.id,
            'repository_id': self.repository.id,
            'repository_branch_id': self.branch.id,
            'scope_sync_enabled': True,
            'status_sync_enabled': True,
            'scope_sync_mode': 'event_driven',
            'client_unit': 'Operacoes',
            'odoo_version': '19.0',
            'odoo_edition': 'enterprise',
            'odoo_environment': 'odoo_sh',
            'standard_allowed': 'yes',
            'additional_modules_allowed': 'yes',
            'studio_allowed': 'no',
            'custom_allowed': 'yes',
            'trigger_text': 'Projeto adjudicado',
            'frequency_text': 'Diaria',
            'volumes_text': '350 encomendas/mes',
            'urgency': 'high',
            'project_summary': 'Resumo onboarding do projeto.',
            'project_objective': 'Garantir contexto consultavel no repositorio.',
            'scope_included_text': 'Implementacao Odoo\nIntegracao GitHub',
            'scope_excluded_text': 'Hardware',
            'deliverables_text': 'Planeamento inicial\nContexto do projeto',
            'assumptions_text': 'Cliente responde em tempo util',
            'restrictions_text': 'Sem acesso direto ao servidor do cliente',
            'stakeholders_text': 'Cliente Ancoravip\nBruno Pinheiro',
            'milestones_text': 'Kickoff\nGo-live',
        }
        values.update(overrides)
        return self.env['pg.ai.onboarding.wizard'].create(values)

    def test_import_github_account_updates_settings_and_wizard(self):
        wizard = self._create_wizard()

        with patch.object(
            GitHubService,
            'discover_configuration',
            return_value={
                'token': 'ghp_synced',
                'login': 'bruno-pinheiro-pg',
                'name': 'Bruno Pinheiro',
                'default_owner': 'bruno-pinheiro-pg',
                'suggested_default_branch': 'main',
            },
        ), patch.object(GitHubService, 'sync_user_repositories', return_value=self.repository):
            wizard.action_import_github_account()

        params = self.env['ir.config_parameter'].sudo()
        self.assertEqual(params.get_param('pg_github_token'), 'ghp_synced')
        self.assertEqual(params.get_param('pg_github_default_owner'), 'bruno-pinheiro-pg')
        self.assertEqual(wizard.github_account_login, 'bruno-pinheiro-pg')
        self.assertEqual(wizard.github_account_name, 'Bruno Pinheiro')
        self.assertEqual(wizard.last_validation_status, 'done')

    def test_validate_publish_readiness_checks_repository_branch_access(self):
        wizard = self._create_wizard()

        with patch.object(GitHubService, 'discover_configuration', return_value={'token': 'ghp_test'}), patch.object(
            GitHubService,
            'sync_repository_branches',
            return_value=self.repository.branch_ids,
        ):
            action = wizard.action_validate_publish_readiness()

        self.assertEqual(wizard.last_validation_status, 'done')
        self.assertIn('ready to receive the onboarding configuration', wizard.last_validation_message)
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'pg.ai.onboarding.wizard')
        self.assertEqual(action['res_id'], wizard.id)
        self.assertEqual(action['target'], 'new')

    def test_apply_onboarding_updates_project_configuration(self):
        wizard = self._create_wizard()

        wizard.action_apply_onboarding()

        project = self.env['project.project'].browse(self.project.id)
        params = self.env['ir.config_parameter'].sudo()

        self.assertEqual(params.get_param('pg_github_token'), 'ghp_test')
        self.assertEqual(project.pg_repository_id, self.repository)
        self.assertEqual(project.pg_repo_branch, 'teste')
        self.assertTrue(project.pg_scope_sync_enabled)
        self.assertTrue(project.pg_status_sync_enabled)
        self.assertEqual(project.pg_scope_sync_mode, 'event_driven')
        self.assertEqual(project.pg_status_owner_id, self.env.user)
        self.assertEqual(project.pg_client_unit, 'Operacoes')
        self.assertEqual(project.pg_odoo_version, '19.0')
        self.assertEqual(project.pg_odoo_edition, 'enterprise')
        self.assertEqual(project.pg_odoo_environment, 'odoo_sh')
        self.assertEqual(project.pg_standard_allowed, 'yes')
        self.assertEqual(project.pg_additional_modules_allowed, 'yes')
        self.assertEqual(project.pg_studio_allowed, 'no')
        self.assertEqual(project.pg_custom_allowed, 'yes')
        self.assertEqual(project.pg_trigger, 'Projeto adjudicado')
        self.assertEqual(project.pg_frequency, 'Diaria')
        self.assertEqual(project.pg_volumes, '350 encomendas/mes')
        self.assertEqual(project.pg_urgency, 'high')
        self.assertEqual(project.pg_repository_summary, 'Resumo onboarding do projeto.')
        self.assertEqual(project.pg_business_goal, 'Garantir contexto consultavel no repositorio.')
        self.assertEqual(project.pg_onboarding_scope_included_text, 'Implementacao Odoo\nIntegracao GitHub')
        self.assertEqual(project.pg_onboarding_scope_excluded_text, 'Hardware')
        self.assertEqual(project.pg_onboarding_deliverables_text, 'Planeamento inicial\nContexto do projeto')
        self.assertEqual(project.pg_onboarding_assumptions_text, 'Cliente responde em tempo util')
        self.assertEqual(project.pg_additional_contract_restrictions, 'Sem acesso direto ao servidor do cliente')
        self.assertEqual(project.pg_onboarding_stakeholders_text, 'Cliente Ancoravip\nBruno Pinheiro')
        self.assertEqual(project.pg_onboarding_milestones_text, 'Kickoff\nGo-live')
        self.assertTrue(project.pg_onboarding_last_applied_at)
        self.assertEqual(project.pg_onboarding_last_status, 'done')
        self.assertEqual(
            project.pg_onboarding_last_message,
            'Onboarding applied. The project is now linked to bruno-pinheiro-pg/wizard_repo on branch teste.',
        )

    def test_project_defaults_handles_missing_cached_branch(self):
        self.project.write(
            {
                'pg_client_unit': 'Consultoria',
                'pg_odoo_version': '19.0',
                'pg_odoo_edition': 'enterprise',
                'pg_odoo_environment': 'odoo_sh',
                'pg_standard_allowed': 'yes',
                'pg_additional_modules_allowed': 'yes',
                'pg_studio_allowed': 'no',
                'pg_custom_allowed': 'yes',
                'pg_trigger': 'Pedido do cliente',
                'pg_frequency': 'Semanal',
                'pg_volumes': '120 documentos/semana',
                'pg_urgency': 'medium',
                'pg_repository_summary': 'Resumo existente',
                'pg_business_goal': 'Objetivo existente',
                'pg_onboarding_scope_included_text': 'Implementacao Odoo',
                'pg_onboarding_deliverables_text': 'Go-live',
                'pg_onboarding_stakeholders_text': 'Cliente',
            }
        )
        self.project.write(
            {
                'pg_repository_id': self.repository.id,
                'pg_repo_branch': 'main',
                'pg_scope_sync_enabled': True,
                'pg_status_sync_enabled': True,
            }
        )

        wizard = self.env['pg.ai.onboarding.wizard'].new({'project_id': self.project.id})
        wizard._onchange_project_id()

        self.assertEqual(wizard.repository_id, self.repository)
        self.assertFalse(wizard.repository_branch_id)
        self.assertTrue(wizard.scope_sync_enabled)
        self.assertTrue(wizard.status_sync_enabled)
        self.assertEqual(wizard.client_unit, 'Consultoria')
        self.assertEqual(wizard.odoo_version, '19.0')
        self.assertEqual(wizard.odoo_edition, 'enterprise')
        self.assertEqual(wizard.odoo_environment, 'odoo_sh')
        self.assertEqual(wizard.standard_allowed, 'yes')
        self.assertEqual(wizard.additional_modules_allowed, 'yes')
        self.assertEqual(wizard.studio_allowed, 'no')
        self.assertEqual(wizard.custom_allowed, 'yes')
        self.assertEqual(wizard.trigger_text, 'Pedido do cliente')
        self.assertEqual(wizard.frequency_text, 'Semanal')
        self.assertEqual(wizard.volumes_text, '120 documentos/semana')
        self.assertEqual(wizard.urgency, 'medium')
        self.assertEqual(wizard.project_summary, 'Resumo existente')
        self.assertEqual(wizard.project_objective, 'Objetivo existente')
        self.assertEqual(wizard.scope_included_text, 'Implementacao Odoo')
        self.assertEqual(wizard.deliverables_text, 'Go-live')
        self.assertEqual(wizard.stakeholders_text, 'Cliente')

    def test_validate_publish_readiness_requires_context_base_fields(self):
        wizard = self._create_wizard(project_summary=False)

        with self.assertRaises(UserError):
            wizard.action_validate_publish_readiness()

    def test_validate_publish_readiness_requires_contract_fields(self):
        wizard = self._create_wizard(odoo_environment='unknown')

        with self.assertRaises(UserError):
            wizard.action_validate_publish_readiness()
