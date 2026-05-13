from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from ..services.github_service import GitHubService


class PgAiRepository(models.Model):
    _name = 'pg.ai.repository'
    _description = 'AI Repository'
    _order = 'github_owner, github_repo'

    name = fields.Char(string='Name', required=True)
    full_name = fields.Char(string='GitHub Full Name', required=True, index=True)
    github_id = fields.Integer(string='GitHub ID', index=True)
    github_owner = fields.Char(string='GitHub Owner', required=True, index=True)
    github_repo = fields.Char(string='GitHub Repository', required=True, index=True)
    default_branch = fields.Char(
        string='Default Branch',
        required=True,
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param('pg_github_default_branch', 'main'),
    )
    visibility = fields.Selection(
        [('public', 'Public'), ('private', 'Private'), ('internal', 'Internal')],
        string='Visibility',
        default='private',
    )
    is_private = fields.Boolean(string='Private')
    active = fields.Boolean(default=True)
    last_sync_at = fields.Datetime(string='Last Sync')
    branch_ids = fields.One2many('pg.ai.repository.branch', 'repository_id', string='Branches')
    branch_count = fields.Integer(string='Branch Count', compute='_compute_branch_count')

    _pg_ai_repository_unique_repo = models.Constraint(
        'unique(github_owner, github_repo)',
        'The GitHub repository is already configured.',
    )
    _pg_ai_repository_unique_github_id = models.Constraint(
        'unique(github_id)',
        'The GitHub repository is already synchronized.',
    )

    @api.depends('branch_ids')
    def _compute_branch_count(self):
        for record in self:
            record.branch_count = len(record.branch_ids)

    def name_get(self):
        return [(record.id, record.full_name or f"{record.github_owner}/{record.github_repo}") for record in self]

    def _normalize_git_value(self, value):
        return (value or '').strip().strip('/')

    def _github_service(self):
        return GitHubService(self.env)

    def get_default_branch_record(self):
        self.ensure_one()
        default_branch = self.branch_ids.filtered(lambda branch: branch.is_default)[:1]
        if default_branch:
            return default_branch
        if self.default_branch:
            return self.branch_ids.filtered(lambda branch: branch.name == self.default_branch)[:1]
        return self.branch_ids[:1]

    def sync_branches(self):
        for record in self:
            record._github_service().sync_repository_branches(record)
        return True

    def action_sync_branches(self):
        self.sync_branches()
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    @api.model
    def action_sync_from_github(self):
        self._github_service().sync_user_repositories()
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    @api.model
    def name_search(self, name='', domain=None, operator='ilike', limit=100):
        domain = list(domain or [])
        records = self.search(domain, limit=limit)
        if name:
            records = self.search(
                ['|', ('full_name', operator, name), ('name', operator, name)] + domain,
                limit=limit,
            )
        if records:
            return records.name_get()

        if not self._github_service().should_autosync_on_search():
            return super().name_search(name=name, domain=domain, operator=operator, limit=limit)

        try:
            self._github_service().sync_user_repositories()
        except ValidationError:
            raise
        except Exception:
            return super().name_search(name=name, domain=domain, operator=operator, limit=limit)

        records = self.search(
            ['|', ('full_name', operator, name), ('name', operator, name)] + domain,
            limit=limit,
        )
        return records.name_get()

    @api.constrains('github_owner', 'github_repo', 'default_branch')
    def _check_repository_values(self):
        for record in self:
            owner = record._normalize_git_value(record.github_owner)
            repo = record._normalize_git_value(record.github_repo)
            if '/' in owner or not owner:
                raise ValidationError(_("GitHub owner must contain a single account or organization name."))
            if '/' in repo or not repo:
                raise ValidationError(_("GitHub repository must contain only the repository name."))
            if not record.default_branch or not record.default_branch.strip():
                raise ValidationError(_("Default branch is required."))

    @api.model_create_multi
    def create(self, vals_list):
        normalized_vals_list = []
        for vals in vals_list:
            normalized_vals = dict(vals)
            if 'github_owner' in normalized_vals:
                normalized_vals['github_owner'] = self._normalize_git_value(normalized_vals['github_owner'])
            if 'github_repo' in normalized_vals:
                normalized_vals['github_repo'] = self._normalize_git_value(normalized_vals['github_repo'])
            if 'full_name' not in normalized_vals and normalized_vals.get('github_owner') and normalized_vals.get('github_repo'):
                normalized_vals['full_name'] = f"{normalized_vals['github_owner']}/{normalized_vals['github_repo']}"
            if 'default_branch' in normalized_vals:
                normalized_vals['default_branch'] = (normalized_vals['default_branch'] or '').strip()
            normalized_vals_list.append(normalized_vals)
        return super().create(normalized_vals_list)

    def write(self, vals):
        normalized_vals = dict(vals)
        if 'github_owner' in normalized_vals:
            normalized_vals['github_owner'] = self._normalize_git_value(normalized_vals['github_owner'])
        if 'github_repo' in normalized_vals:
            normalized_vals['github_repo'] = self._normalize_git_value(normalized_vals['github_repo'])
        owner = normalized_vals.get('github_owner') or self.github_owner
        repo = normalized_vals.get('github_repo') or self.github_repo
        if owner and repo:
            normalized_vals['full_name'] = f"{owner}/{repo}"
        if 'default_branch' in normalized_vals:
            normalized_vals['default_branch'] = (normalized_vals['default_branch'] or '').strip()
        return super().write(normalized_vals)


class PgAiRepositoryBranch(models.Model):
    _name = 'pg.ai.repository.branch'
    _description = 'AI Repository Branch'
    _order = 'is_default desc, name'

    repository_id = fields.Many2one('pg.ai.repository', string='Repository', required=True, ondelete='cascade', index=True)
    name = fields.Char(string='Branch', required=True, index=True)
    is_default = fields.Boolean(string='Default')
    last_sync_at = fields.Datetime(string='Last Sync')

    _pg_ai_repository_branch_unique_name = models.Constraint(
        'unique(repository_id, name)',
        'The branch is already synchronized for this repository.',
    )

    def name_get(self):
        return [(record.id, record.name) for record in self]

    @api.model
    def name_search(self, name='', domain=None, operator='ilike', limit=100):
        domain = list(domain or [])
        records = self.search([('name', operator, name)] + domain, limit=limit)
        if records:
            return records.name_get()

        repository_id = self.env.context.get('pg_ai_repository_id')
        if repository_id:
            autosync_enabled = str(
                self.env['ir.config_parameter'].sudo().get_param('pg_github_autosync_on_search', 'True')
            ).strip().lower() in {'1', 'true', 'yes', 'on'}
            if not autosync_enabled:
                return super().name_search(name=name, domain=domain, operator=operator, limit=limit)
            repository = self.env['pg.ai.repository'].browse(repository_id).exists()
            if repository:
                repository.sync_branches()
                records = self.search([('name', operator, name)] + domain, limit=limit)
                if records:
                    return records.name_get()
        return super().name_search(name=name, domain=domain, operator=operator, limit=limit)
