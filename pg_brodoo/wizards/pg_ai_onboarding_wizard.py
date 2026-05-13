from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..services.github_service import GitHubService


class PgAiOnboardingWizard(models.TransientModel):
    _name = 'pg.ai.onboarding.wizard'
    _description = 'Brodoo Onboarding Wizard'

    github_token = fields.Char(string='GitHub Token')
    github_default_owner = fields.Char(string='GitHub Default Owner')
    github_default_branch = fields.Char(string='GitHub Default Branch')
    github_account_login = fields.Char(string='GitHub Account', readonly=True)
    github_account_name = fields.Char(string='GitHub Name', readonly=True)
    github_repo_count = fields.Integer(string='GitHub Repositories', compute='_compute_github_repo_count')

    project_id = fields.Many2one('project.project', string='Project')
    repository_id = fields.Many2one('pg.ai.repository', string='Repository')
    repository_branch_id = fields.Many2one(
        'pg.ai.repository.branch',
        string='Repository Branch',
        domain="[('repository_id', '=', repository_id)]",
    )
    scope_sync_enabled = fields.Boolean(string='Enable Scope Sync', default=True)
    status_sync_enabled = fields.Boolean(string='Enable Status Sync', default=True)
    scope_sync_mode = fields.Selection(
        selection=lambda self: self.env['project.project']._fields['pg_scope_sync_mode'].selection,
        string='Scope Sync Mode',
        default='event_driven',
        required=True,
    )
    client_unit = fields.Char(string='Unidade do Cliente')
    odoo_version = fields.Char(string='Versão Odoo')
    odoo_edition = fields.Selection(
        selection=lambda self: self.env['project.project']._fields['pg_odoo_edition'].selection,
        string='Edição Odoo',
        default='unknown',
        required=True,
    )
    odoo_environment = fields.Selection(
        selection=lambda self: self.env['project.project']._fields['pg_odoo_environment'].selection,
        string='Alojamento',
        default='unknown',
        required=True,
    )
    standard_allowed = fields.Selection(
        selection=lambda self: self.env['project.project']._fields['pg_standard_allowed'].selection,
        string='Standard Permitido',
        default='unknown',
        required=True,
    )
    additional_modules_allowed = fields.Selection(
        selection=lambda self: self.env['project.project']._fields['pg_additional_modules_allowed'].selection,
        string='Módulos Adicionais Permitidos',
        default='unknown',
        required=True,
    )
    studio_allowed = fields.Selection(
        selection=lambda self: self.env['project.project']._fields['pg_studio_allowed'].selection,
        string='Studio Permitido',
        default='unknown',
        required=True,
    )
    custom_allowed = fields.Selection(
        selection=lambda self: self.env['project.project']._fields['pg_custom_allowed'].selection,
        string='Desenvolvimento Custom Permitido',
        default='unknown',
        required=True,
    )
    trigger_text = fields.Char(string='Desencadeador')
    frequency_text = fields.Char(string='Frequência')
    volumes_text = fields.Char(string='Volumes')
    urgency = fields.Selection(
        selection=lambda self: self.env['project.project']._fields['pg_urgency'].selection,
        string='Urgência',
        default='unknown',
        required=True,
    )
    project_summary = fields.Text(string='Resumo do Projeto')
    project_objective = fields.Text(string='Objetivo do Projeto')
    scope_included_text = fields.Text(string='Âmbito Incluído')
    scope_excluded_text = fields.Text(string='Âmbito Excluído')
    deliverables_text = fields.Text(string='Entregáveis Principais')
    assumptions_text = fields.Text(string='Pressupostos')
    restrictions_text = fields.Text(string='Restrições')
    stakeholders_text = fields.Text(string='Stakeholders Principais')
    milestones_text = fields.Text(string='Marcos Principais')

    setup_feedback = fields.Text(string='Setup Feedback', compute='_compute_setup_feedback')
    last_validation_status = fields.Selection(
        [('idle', 'Idle'), ('done', 'Done'), ('error', 'Error')],
        string='Last Validation Status',
        default='idle',
        readonly=True,
    )
    last_validation_message = fields.Text(string='Last Validation Message', readonly=True)

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        params = self.env['ir.config_parameter'].sudo()
        values.setdefault('github_token', params.get_param('pg_github_token') or '')
        values.setdefault('github_default_owner', params.get_param('pg_github_default_owner') or '')
        values.setdefault('github_default_branch', params.get_param('pg_github_default_branch', 'main') or 'main')
        values.setdefault('github_account_login', params.get_param('pg_github_account_login') or '')
        values.setdefault('github_account_name', params.get_param('pg_github_account_name') or '')

        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        if active_model == 'project.project' and active_id:
            project = self.env['project.project'].browse(active_id).exists()
            if project:
                values.update(self._project_defaults(project))
        return values

    @api.depends()
    def _compute_github_repo_count(self):
        repo_count = self.env['pg.ai.repository'].sudo().search_count([])
        for wizard in self:
            wizard.github_repo_count = repo_count

    @api.depends(
        'github_token',
        'project_id',
        'repository_id',
        'repository_branch_id',
        'scope_sync_enabled',
        'status_sync_enabled',
        'client_unit',
        'odoo_version',
        'odoo_edition',
        'odoo_environment',
        'standard_allowed',
        'additional_modules_allowed',
        'studio_allowed',
        'custom_allowed',
        'trigger_text',
        'frequency_text',
        'volumes_text',
        'urgency',
        'project_summary',
        'project_objective',
        'scope_included_text',
        'scope_excluded_text',
        'deliverables_text',
        'assumptions_text',
        'restrictions_text',
        'stakeholders_text',
        'milestones_text',
        'last_validation_status',
        'last_validation_message',
    )
    def _compute_setup_feedback(self):
        for wizard in self:
            messages = []
            if not wizard.project_id:
                messages.append(_("Select the target project to configure."))
            if not wizard.repository_id:
                messages.append(_("Select a synchronized repository for the project."))
            if wizard.repository_id and not wizard.repository_branch_id:
                messages.append(_("Sync branches and choose the target repository branch."))
            if not wizard.scope_sync_enabled and not wizard.status_sync_enabled:
                messages.append(_("Enable at least one factual sync flow on the project."))
            if not (wizard.odoo_version or '').strip():
                messages.append(_("Define the Odoo version used by the project."))
            if (wizard.odoo_edition or 'unknown') == 'unknown':
                messages.append(_("Define the Odoo edition used by the project."))
            if (wizard.odoo_environment or 'unknown') == 'unknown':
                messages.append(_("Define where the project is hosted."))
            if (wizard.standard_allowed or 'unknown') == 'unknown':
                messages.append(_("Clarify whether standard Odoo is allowed for this project."))
            if (wizard.additional_modules_allowed or 'unknown') == 'unknown':
                messages.append(_("Clarify whether additional modules are allowed for this project."))
            if (wizard.studio_allowed or 'unknown') == 'unknown':
                messages.append(_("Clarify whether Odoo Studio is allowed for this project."))
            if (wizard.custom_allowed or 'unknown') == 'unknown':
                messages.append(_("Clarify whether custom development is allowed for this project."))
            if not (wizard.project_summary or '').strip():
                messages.append(_("Add a short summary so the repository starts with useful project context."))
            if not (wizard.project_objective or '').strip():
                messages.append(_("Add the project objective to support scope and decision questions."))
            if not (wizard.scope_included_text or '').strip():
                messages.append(_("Describe what is included in scope."))
            if not (wizard.deliverables_text or '').strip():
                messages.append(_("List the main deliverables expected for this project."))
            if not (wizard.stakeholders_text or '').strip():
                messages.append(_("List the main stakeholders involved in the project."))

            if not messages:
                base_feedback = _(
                    "Wizard ready: validate GitHub access and apply the onboarding configuration to the project."
                )
            else:
                base_feedback = '\n'.join(messages)

            if wizard.last_validation_message:
                wizard.setup_feedback = "%s\n\n%s" % (base_feedback, wizard.last_validation_message)
            else:
                wizard.setup_feedback = base_feedback

    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self.project_id:
            defaults = self._project_defaults(self.project_id)
            self.repository_id = defaults.get('repository_id') or self.repository_id
            self.scope_sync_enabled = defaults.get('scope_sync_enabled', self.scope_sync_enabled)
            self.status_sync_enabled = defaults.get('status_sync_enabled', self.status_sync_enabled)
            self.scope_sync_mode = defaults.get('scope_sync_mode') or self.scope_sync_mode
            self.client_unit = defaults.get('client_unit') or self.client_unit
            self.odoo_version = defaults.get('odoo_version') or self.odoo_version
            self.odoo_edition = defaults.get('odoo_edition') or self.odoo_edition
            self.odoo_environment = defaults.get('odoo_environment') or self.odoo_environment
            self.standard_allowed = defaults.get('standard_allowed') or self.standard_allowed
            self.additional_modules_allowed = defaults.get('additional_modules_allowed') or self.additional_modules_allowed
            self.studio_allowed = defaults.get('studio_allowed') or self.studio_allowed
            self.custom_allowed = defaults.get('custom_allowed') or self.custom_allowed
            self.trigger_text = defaults.get('trigger_text') or self.trigger_text
            self.frequency_text = defaults.get('frequency_text') or self.frequency_text
            self.volumes_text = defaults.get('volumes_text') or self.volumes_text
            self.urgency = defaults.get('urgency') or self.urgency
            self.project_summary = defaults.get('project_summary') or self.project_summary
            self.project_objective = defaults.get('project_objective') or self.project_objective
            self.scope_included_text = defaults.get('scope_included_text') or self.scope_included_text
            self.scope_excluded_text = defaults.get('scope_excluded_text') or self.scope_excluded_text
            self.deliverables_text = defaults.get('deliverables_text') or self.deliverables_text
            self.assumptions_text = defaults.get('assumptions_text') or self.assumptions_text
            self.restrictions_text = defaults.get('restrictions_text') or self.restrictions_text
            self.stakeholders_text = defaults.get('stakeholders_text') or self.stakeholders_text
            self.milestones_text = defaults.get('milestones_text') or self.milestones_text
            branch_id = defaults.get('repository_branch_id')
            if branch_id:
                self.repository_branch_id = branch_id

    @api.onchange('repository_id')
    def _onchange_repository_id(self):
        if self.repository_id:
            if not self.github_default_owner:
                self.github_default_owner = self.repository_id.github_owner
            self.repository_branch_id = self.repository_id.get_default_branch_record()
        else:
            self.repository_branch_id = False

    def _project_defaults(self, project):
        branch_record = False
        if project.pg_repository_id and project.pg_repo_branch:
            branch_record = project.pg_repository_id.branch_ids.filtered(
                lambda branch: branch.name == project.pg_repo_branch
            )[:1]
        milestone_lines = '\n'.join(project.pg_project_plan_milestone_ids.sorted(key=lambda milestone: (milestone.sequence, milestone.id)).mapped('name'))
        stakeholder_lines = '\n'.join(
            [value for value in [project.partner_id.display_name if project.partner_id else '', project.user_id.display_name if project.user_id else ''] if value]
        )
        return {
            'project_id': project.id,
            'repository_id': project.pg_repository_id.id or False,
            'repository_branch_id': branch_record.id if branch_record else False,
            'scope_sync_enabled': project.pg_scope_sync_enabled,
            'status_sync_enabled': project.pg_status_sync_enabled,
            'scope_sync_mode': project.pg_scope_sync_mode or 'event_driven',
            'client_unit': project.pg_client_unit or False,
            'odoo_version': project.pg_odoo_version or False,
            'odoo_edition': project.pg_odoo_edition or 'unknown',
            'odoo_environment': project.pg_odoo_environment or 'unknown',
            'standard_allowed': project.pg_standard_allowed or 'unknown',
            'additional_modules_allowed': project.pg_additional_modules_allowed or 'unknown',
            'studio_allowed': project.pg_studio_allowed or 'unknown',
            'custom_allowed': project.pg_custom_allowed or 'unknown',
            'trigger_text': project.pg_trigger or False,
            'frequency_text': project.pg_frequency or False,
            'volumes_text': project.pg_volumes or False,
            'urgency': project.pg_urgency or 'unknown',
            'project_summary': project.pg_repository_summary or False,
            'project_objective': project.pg_business_goal or False,
            'scope_included_text': project.pg_onboarding_scope_included_text or False,
            'scope_excluded_text': project.pg_onboarding_scope_excluded_text or False,
            'deliverables_text': project.pg_onboarding_deliverables_text or False,
            'assumptions_text': project.pg_onboarding_assumptions_text or False,
            'restrictions_text': project.pg_additional_contract_restrictions or False,
            'stakeholders_text': project.pg_onboarding_stakeholders_text or stakeholder_lines or False,
            'milestones_text': project.pg_onboarding_milestones_text or milestone_lines or False,
        }

    def _github_service(self):
        return GitHubService(self.env)

    def _set_param(self, key, value):
        stored_value = value
        if isinstance(value, bool):
            stored_value = 'True' if value else 'False'
        elif value in (None, False):
            stored_value = ''
        self.env['ir.config_parameter'].sudo().set_param(key, stored_value)

    def _store_global_settings(self):
        self._set_param('pg_github_token', self.github_token or '')
        self._set_param('pg_github_default_owner', self.github_default_owner or '')
        self._set_param('pg_github_default_branch', self.github_default_branch or 'main')
        self._set_param('pg_github_account_login', self.github_account_login or '')
        self._set_param('pg_github_account_name', self.github_account_name or '')

    def _set_validation_feedback(self, status, message):
        self.write(
            {
                'last_validation_status': status,
                'last_validation_message': message,
            }
        )

    def _reload_action(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Brodoo Onboarding'),
            'res_model': 'pg.ai.onboarding.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_import_github_account(self):
        self.ensure_one()
        github_service = self._github_service()
        details = github_service.discover_configuration(token=self.github_token)
        github_service.sync_user_repositories(token=details.get('token'))

        self.write(
            {
                'github_token': details.get('token') or self.github_token,
                'github_default_owner': details.get('default_owner') or '',
                'github_default_branch': details.get('suggested_default_branch') or self.github_default_branch or 'main',
                'github_account_login': details.get('login') or '',
                'github_account_name': details.get('name') or '',
            }
        )
        self._store_global_settings()
        self._set_validation_feedback('done', _("GitHub account imported and repositories synchronized successfully."))
        return self._reload_action()

    def action_sync_repository_branches(self):
        self.ensure_one()
        if not self.repository_id:
            raise UserError(_("Select a repository before synchronizing branches."))

        self._github_service().sync_repository_branches(self.repository_id, token=self.github_token)
        self.repository_branch_id = self.repository_id.get_default_branch_record()
        self._set_validation_feedback('done', _("Repository branches synchronized successfully."))
        return self._reload_action()

    def _validate_required_onboarding_fields(self):
        self.ensure_one()
        if not self.project_id:
            raise UserError(_("Select the project that should receive the onboarding configuration."))
        if not self.repository_id:
            raise UserError(_("Select the GitHub repository that should be linked to the project."))
        if not self.repository_branch_id:
            raise UserError(_("Select the repository branch that should be linked to the project."))
        if (
            self.odoo_environment == 'odoo_sh'
            and (self.repository_branch_id.name or '').strip().lower() == 'main'
        ):
            raise UserError(
                _("A branch 'main' não pode ser utilizada em projetos com ambiente Odoo.sh. "
                  "Em Odoo.sh a branch 'main' é a branch de produção. "
                  "Configure uma branch de desenvolvimento (ex: dev, staging).")
            )
        if not self.scope_sync_enabled and not self.status_sync_enabled:
            raise UserError(_("Enable at least one sync flow before applying the onboarding configuration."))
        for field_name, label, empty_value in (
            ('odoo_version', _('Odoo version'), ''),
            ('odoo_edition', _('Odoo edition'), 'unknown'),
            ('odoo_environment', _('hosting model'), 'unknown'),
            ('standard_allowed', _('standard allowance'), 'unknown'),
            ('additional_modules_allowed', _('additional modules allowance'), 'unknown'),
            ('studio_allowed', _('Studio allowance'), 'unknown'),
            ('custom_allowed', _('custom development allowance'), 'unknown'),
        ):
            value = getattr(self, field_name)
            if value == empty_value or not value:
                raise UserError(_("The onboarding requires %s before applying the configuration.") % label)
        for field_name, label in (
            ('project_summary', _('project summary')),
            ('project_objective', _('project objective')),
            ('scope_included_text', _('included scope')),
            ('deliverables_text', _('main deliverables')),
            ('stakeholders_text', _('main stakeholders')),
        ):
            if not (getattr(self, field_name) or '').strip():
                raise UserError(_("The onboarding requires %s before applying the configuration.") % label)

    def action_validate_publish_readiness(self):
        self.ensure_one()
        self._validate_required_onboarding_fields()

        github_service = self._github_service()
        github_service.discover_configuration(token=self.github_token)
        synced_branches = github_service.sync_repository_branches(self.repository_id, token=self.github_token)
        if not synced_branches.filtered(lambda branch: branch.id == self.repository_branch_id.id):
            raise UserError(_("The selected repository branch is not available after synchronization."))

        self._set_validation_feedback(
            'done',
            _("GitHub access validated. Project %s is ready to receive the onboarding configuration.")
            % self.project_id.display_name,
        )
        return self._reload_action()

    def action_apply_onboarding(self):
        self.ensure_one()
        self._validate_required_onboarding_fields()
        self._store_global_settings()
        onboarding_message = _(
            "Onboarding applied. The project is now linked to %s on branch %s."
        ) % (self.repository_id.full_name, self.repository_branch_id.name)

        project_values = {
            'pg_repository_id': self.repository_id.id,
            'pg_repo_branch': self.repository_branch_id.name,
            'pg_scope_sync_enabled': self.scope_sync_enabled,
            'pg_status_sync_enabled': self.status_sync_enabled,
            'pg_scope_sync_mode': self.scope_sync_mode,
            'pg_client_unit': self.client_unit or False,
            'pg_odoo_version': self.odoo_version or False,
            'pg_odoo_edition': self.odoo_edition,
            'pg_odoo_environment': self.odoo_environment,
            'pg_standard_allowed': self.standard_allowed,
            'pg_additional_modules_allowed': self.additional_modules_allowed,
            'pg_studio_allowed': self.studio_allowed,
            'pg_custom_allowed': self.custom_allowed,
            'pg_trigger': self.trigger_text or False,
            'pg_frequency': self.frequency_text or False,
            'pg_volumes': self.volumes_text or False,
            'pg_urgency': self.urgency,
            'pg_repository_summary': self.project_summary or False,
            'pg_business_goal': self.project_objective or False,
            'pg_onboarding_scope_included_text': self.scope_included_text or False,
            'pg_onboarding_scope_excluded_text': self.scope_excluded_text or False,
            'pg_onboarding_deliverables_text': self.deliverables_text or False,
            'pg_onboarding_assumptions_text': self.assumptions_text or False,
            'pg_additional_contract_restrictions': self.restrictions_text or False,
            'pg_onboarding_stakeholders_text': self.stakeholders_text or False,
            'pg_onboarding_milestones_text': self.milestones_text or False,
            'pg_onboarding_last_applied_at': fields.Datetime.now(),
            'pg_onboarding_last_status': 'done',
            'pg_onboarding_last_message': onboarding_message,
        }
        if self.status_sync_enabled and not self.project_id.pg_status_owner_id:
            project_values['pg_status_owner_id'] = self.env.user.id

        self.project_id.with_context(
            pg_skip_scope_sync_enqueue=True,
            pg_skip_status_sync_touch=True,
            pg_skip_ai_consultive_gate_reset=True,
        ).write(project_values)

        self._set_validation_feedback(
            'done',
            onboarding_message,
        )
        return {'type': 'ir.actions.act_window_close'}
