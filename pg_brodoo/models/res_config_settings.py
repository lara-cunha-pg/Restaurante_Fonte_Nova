from odoo import fields, models

from ..services.chatgpt_service import (
    DEFAULT_BASE_PROMPT,
    DEFAULT_CODEX_MODEL,
    DEFAULT_PROMPT_MODEL,
    DEFAULT_PROMPT_INSTRUCTIONS,
    ChatGptPromptService,
)
from ..services.codex_service import (
    DEFAULT_CHANGE_REQUEST_INSTRUCTIONS,
    DEFAULT_CLI_INSTRUCTIONS,
    DEFAULT_COMMIT_MESSAGE_TEMPLATE,
    DEFAULT_FILE_SELECTION_INSTRUCTIONS,
    DEFAULT_PR_BODY_TEMPLATE,
    DEFAULT_PR_TITLE_TEMPLATE,
    CodexService,
)
from ..services.github_service import GitHubService


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    _GITHUB_REPOSITORY_SORT_SELECTION = [
        ('updated', 'Updated'),
        ('full_name', 'Full Name'),
        ('created', 'Created'),
        ('pushed', 'Pushed'),
    ]
    _SELECTION_PARAM_FIELDS = {
        'pg_openai_model': ('pg_openai_model', DEFAULT_PROMPT_MODEL),
        'codex_execution_mode': ('codex_execution_mode', 'cli'),
        'codex_execution_model': ('codex_execution_model', DEFAULT_CODEX_MODEL),
        'codex_cli_runtime_profile': ('codex_cli_runtime_profile', 'dangerous'),
        'pg_github_repository_sort': ('pg_github_repository_sort', 'updated'),
    }
    _TEXT_PARAM_FIELDS = {
        'pg_openai_prompt_template': ('pg_openai_prompt_template', DEFAULT_BASE_PROMPT),
        'pg_openai_prompt_instructions': ('pg_openai_prompt_instructions', DEFAULT_PROMPT_INSTRUCTIONS),
        'pg_openai_fallback_models': (
            'pg_openai_fallback_models',
            'gpt-4.1-mini\ngpt-5.4\ngpt-5.3-codex\ngpt-5.2-codex',
        ),
        'codex_fallback_priority_filenames': (
            'codex_fallback_priority_filenames',
            '__manifest__.py\nREADME.md\nREADME.rst\nrequirements.txt\npyproject.toml\n__init__.py',
        ),
        'codex_file_selection_instructions': (
            'codex_file_selection_instructions',
            DEFAULT_FILE_SELECTION_INSTRUCTIONS,
        ),
        'codex_change_request_instructions': (
            'codex_change_request_instructions',
            DEFAULT_CHANGE_REQUEST_INSTRUCTIONS,
        ),
        'codex_cli_instructions': (
            'codex_cli_instructions',
            DEFAULT_CLI_INSTRUCTIONS,
        ),
        'codex_commit_message_template': (
            'codex_commit_message_template',
            DEFAULT_COMMIT_MESSAGE_TEMPLATE,
        ),
        'codex_pr_title_template': (
            'codex_pr_title_template',
            DEFAULT_PR_TITLE_TEMPLATE,
        ),
        'codex_pr_body_template': (
            'codex_pr_body_template',
            DEFAULT_PR_BODY_TEMPLATE,
        ),
    }

    pg_openai_api_key = fields.Char(
        string='OpenAI API Key',
        config_parameter='pg_openai_api_key',
    )
    pg_openai_model = fields.Selection(
        selection='_selection_pg_openai_model',
        string='GPT Prompt Model',
        default='gpt-4.1-mini',
    )
    pg_openai_timeout = fields.Integer(
        string='OpenAI Timeout (s)',
        config_parameter='pg_openai_timeout',
        default=120,
    )
    pg_status_draft_llm_redraft_enabled = fields.Boolean(
        string='Enable LLM Status Draft Redraft',
        config_parameter='pg_status_draft_llm_redraft_enabled',
        default=False,
    )
    pg_sync_quality_review_enabled = fields.Boolean(
        string='Enable Pre-Publication Quality Review',
        config_parameter='pg_sync_quality_review_enabled',
        default=False,
    )
    pg_ai_task_context_history_limit = fields.Integer(
        string='Task Memory Entries',
        config_parameter='pg_ai_task_context_history_limit',
        default=8,
    )
    pg_ai_task_context_excerpt_chars = fields.Integer(
        string='Task Memory Excerpt Chars',
        config_parameter='pg_ai_task_context_excerpt_chars',
        default=1000,
    )
    pg_odoo_version = fields.Char(
        string='Odoo Version',
        config_parameter='pg_odoo_version',
        default='19',
    )
    pg_openai_prompt_template = fields.Text(
        string='Prompt Template',
    )
    pg_openai_prompt_instructions = fields.Text(
        string='Prompt Instructions',
    )
    pg_openai_fallback_models = fields.Text(
        string='Fallback Models',
        help='Comma or line-separated list of fallback GPT models.',
    )

    codex_execution_mode = fields.Selection(
        [('cli', 'CLI Local'), ('service', 'Cloud API')],
        string='Codex Execution Mode',
        default='cli',
    )
    codex_execution_model = fields.Selection(
        selection='_selection_codex_execution_model',
        string='Codex Model',
        default='gpt-5.3-codex',
    )
    codex_cli_command = fields.Char(
        string='Codex CLI Command',
        config_parameter='codex_cli_command',
        default='npx',
    )
    codex_cli_args = fields.Char(
        string='Codex CLI Base Args',
        config_parameter='codex_cli_args',
        default='@openai/codex',
    )
    codex_cli_runtime_profile = fields.Selection(
        [('dangerous', 'No Sandbox')],
        string='Codex CLI Runtime Profile',
        default='dangerous',
    )
    codex_cli_extra_args = fields.Char(
        string='Codex CLI Extra Args',
        config_parameter='codex_cli_extra_args',
        help='Extra command-line flags appended after the standard Codex exec arguments.',
    )
    codex_cli_detected_command = fields.Char(
        string='Detected CLI Launcher',
        config_parameter='codex_cli_detected_command',
        readonly=True,
    )
    codex_cli_detected_version = fields.Char(
        string='Detected CLI Version',
        config_parameter='codex_cli_detected_version',
        readonly=True,
    )
    codex_working_dir = fields.Char(
        string='Git Working Directory',
        config_parameter='codex_working_dir',
    )
    codex_timeout = fields.Integer(
        string='Codex Timeout (s)',
        config_parameter='codex_timeout',
        default=1800,
    )
    pg_ai_cleanup_local_workspace = fields.Boolean(
        string='Cleanup Local Workspace After Each Run',
        config_parameter='pg_ai_cleanup_local_workspace',
        default=True,
    )
    codex_branch_prefix = fields.Char(
        string='Branch Prefix',
        config_parameter='codex_branch_prefix',
        default='ai/task',
    )
    codex_git_user_name = fields.Char(
        string='Git User Name',
        config_parameter='codex_git_user_name',
    )
    codex_git_user_email = fields.Char(
        string='Git User Email',
        config_parameter='codex_git_user_email',
    )
    codex_repo_tree_file_limit = fields.Integer(
        string='Repo Tree File Limit',
        config_parameter='codex_repo_tree_file_limit',
        default=600,
    )
    codex_selected_file_limit = fields.Integer(
        string='Selected File Limit',
        config_parameter='codex_selected_file_limit',
        default=12,
    )
    codex_file_content_char_limit = fields.Integer(
        string='File Content Char Limit',
        config_parameter='codex_file_content_char_limit',
        default=16000,
    )
    codex_fallback_priority_filenames = fields.Text(
        string='Fallback Priority Filenames',
        help='Comma or line-separated filenames used when Codex file selection is unavailable.',
    )
    codex_fallback_extensions = fields.Char(
        string='Fallback Extensions',
        config_parameter='codex_fallback_extensions',
        help='Comma-separated extensions used in fallback file selection.',
    )
    codex_file_selection_instructions = fields.Text(
        string='File Selection Instructions',
    )
    codex_change_request_instructions = fields.Text(
        string='Change Request Instructions',
    )
    codex_cli_instructions = fields.Text(
        string='CLI Run Instructions',
    )
    codex_commit_message_template = fields.Text(
        string='Commit Message Template',
    )
    codex_pr_title_template = fields.Text(
        string='PR Title Template',
    )
    codex_pr_body_template = fields.Text(
        string='PR Body Template',
    )

    pg_github_token = fields.Char(
        string='GitHub Token',
        config_parameter='pg_github_token',
    )
    pg_github_default_owner = fields.Char(
        string='GitHub Default Owner',
        config_parameter='pg_github_default_owner',
    )
    pg_github_default_branch = fields.Char(
        string='GitHub Default Branch',
        config_parameter='pg_github_default_branch',
        default='main',
    )
    pg_github_timeout = fields.Integer(
        string='GitHub Timeout (s)',
        config_parameter='pg_github_timeout',
        default=60,
    )
    pg_github_repository_sort = fields.Selection(
        _GITHUB_REPOSITORY_SORT_SELECTION,
        string='Repository Sort',
        default='updated',
    )
    pg_ai_push_direct_to_selected_branch = fields.Boolean(
        string='Push Directly To Selected Branch',
        config_parameter='pg_ai_push_direct_to_selected_branch',
        default=True,
    )
    pg_github_create_pr_by_default = fields.Boolean(
        string='Create Pull Request by Default',
        config_parameter='pg_github_create_pr_by_default',
        default=True,
    )
    pg_github_autosync_on_search = fields.Boolean(
        string='Auto Sync Repositories On Search',
        config_parameter='pg_github_autosync_on_search',
        default=True,
    )
    pg_ai_autosync_branches_on_repo_change = fields.Boolean(
        string='Auto Sync Branches On Repo Change',
        config_parameter='pg_ai_autosync_branches_on_repo_change',
        default=True,
    )
    pg_ai_auto_select_default_branch = fields.Boolean(
        string='Auto Select Default Branch',
        config_parameter='pg_ai_auto_select_default_branch',
        default=True,
    )
    pg_github_account_login = fields.Char(
        string='GitHub Account',
        config_parameter='pg_github_account_login',
        readonly=True,
    )
    pg_github_account_name = fields.Char(
        string='GitHub Name',
        config_parameter='pg_github_account_name',
        readonly=True,
    )
    pg_github_repo_count = fields.Integer(string='GitHub Repositories', compute='_compute_github_repo_count')

    def _compute_github_repo_count(self):
        repository_count = self.env['pg.ai.repository'].sudo().search_count([])
        for record in self:
            record.pg_github_repo_count = repository_count

    def _selection_pg_openai_model(self):
        options = ChatGptPromptService(self.env).get_available_models_for_selection()
        current_value = (self.env['ir.config_parameter'].sudo().get_param('pg_openai_model') or '').strip()
        if current_value and current_value not in dict(options):
            options.append((current_value, current_value))
        return options

    def _selection_codex_execution_model(self):
        options = ChatGptPromptService(self.env).get_available_models_for_selection(codex_only=True)
        current_value = (self.env['ir.config_parameter'].sudo().get_param('codex_execution_model') or '').strip()
        if current_value and current_value not in dict(options):
            options.append((current_value, current_value))
        return options

    def _normalize_selection_value(self, field_name, value, default_value):
        normalized_value = (value or '').strip() or default_value

        if field_name == 'pg_github_repository_sort':
            allowed_values = {item[0] for item in self._GITHUB_REPOSITORY_SORT_SELECTION}
            if normalized_value not in allowed_values:
                return default_value

        if field_name == 'codex_execution_mode' and normalized_value not in {'service', 'cli'}:
            return default_value

        if field_name == 'codex_cli_runtime_profile':
            return 'dangerous'

        return normalized_value

    def _normalize_cli_args_value(self, command, args):
        normalized_command = (command or '').strip()
        normalized_args = (args or '').strip()
        if normalized_command == 'npx' and normalized_args == 'codex':
            return '@openai/codex'
        return normalized_args

    def get_values(self):
        res = super().get_values()
        params = self.env['ir.config_parameter'].sudo()
        for field_name, (param_key, default_value) in self._SELECTION_PARAM_FIELDS.items():
            res[field_name] = self._normalize_selection_value(field_name, params.get_param(param_key), default_value)
        for field_name, (param_key, default_value) in self._TEXT_PARAM_FIELDS.items():
            res[field_name] = params.get_param(param_key, default_value) or default_value
        res['codex_cli_args'] = self._normalize_cli_args_value(res.get('codex_cli_command'), res.get('codex_cli_args'))
        return res

    def _store_config_values(self, values):
        params = self.env['ir.config_parameter'].sudo()
        for key, value in values.items():
            stored_value = value
            if isinstance(value, bool):
                stored_value = 'True' if value else 'False'
            elif value in (None, False):
                stored_value = ''
            params.set_param(key, stored_value)

    def set_values(self):
        super().set_values()
        params = self.env['ir.config_parameter'].sudo()
        for field_name, (param_key, default_value) in self._SELECTION_PARAM_FIELDS.items():
            params.set_param(param_key, self._normalize_selection_value(field_name, getattr(self, field_name), default_value))
        for field_name, (param_key, _default_value) in self._TEXT_PARAM_FIELDS.items():
            params.set_param(param_key, getattr(self, field_name) or '')

    def _reload_settings(self):
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_refresh_gpt_models(self):
        self.ensure_one()
        prompt_service = ChatGptPromptService(self.env)
        prompt_models = prompt_service.refresh_available_models()
        codex_models = prompt_service.get_available_models(codex_only=True)
        values = {}
        if prompt_models and not self.pg_openai_model:
            values['pg_openai_model'] = prompt_models[0]['id']
        if codex_models and not self.codex_execution_model:
            values['codex_execution_model'] = codex_models[0]['id']
        if values:
            self._store_config_values(values)
        return self._reload_settings()

    def action_import_codex_configuration(self):
        self.ensure_one()
        details = CodexService(self.env).discover_cli_configuration()
        values = {
            'codex_execution_mode': 'cli',
            'codex_cli_command': details.get('command') or 'npx',
            'codex_cli_args': details.get('args') or '@openai/codex',
            'codex_cli_runtime_profile': 'dangerous',
            'codex_cli_detected_command': details.get('display_command') or '',
            'codex_cli_detected_version': details.get('version') or '',
        }
        self._store_config_values(values)
        return self._reload_settings()

    def action_import_github_configuration(self):
        self.ensure_one()
        github_service = GitHubService(self.env)
        details = github_service.discover_configuration(token=self.pg_github_token)
        github_service.sync_user_repositories(token=details.get('token'))
        values = {
            'pg_github_token': details.get('token') or '',
            'pg_github_default_owner': details.get('default_owner') or '',
            'pg_github_account_login': details.get('login') or '',
            'pg_github_account_name': details.get('name') or '',
        }
        if details.get('suggested_default_branch'):
            values['pg_github_default_branch'] = details['suggested_default_branch']

        self._store_config_values(values)
        return self._reload_settings()

    def action_sync_github_repositories(self):
        self.ensure_one()
        GitHubService(self.env).sync_user_repositories(token=self.pg_github_token)
        return self._reload_settings()

    def action_open_pg_ai_onboarding_wizard(self):
        self.ensure_one()
        action = self.env.ref('pg_brodoo.action_pg_ai_onboarding_wizard').read()[0]
        action.update({'target': 'new'})
        return action
