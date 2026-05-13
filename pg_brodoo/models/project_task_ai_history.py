from odoo import fields, models


class ProjectTaskAiHistory(models.Model):
    _name = 'project.task.ai.history'
    _description = 'Project Task AI History'
    _order = 'create_date desc, id desc'

    task_id = fields.Many2one(
        'project.task',
        string='Task',
        required=True,
        ondelete='cascade',
        index=True,
    )
    entry_type = fields.Selection(
        [
            ('prompt', 'Prompt'),
            ('execution', 'Execution'),
        ],
        string='Entry Type',
        required=True,
        default='execution',
    )
    status = fields.Selection(
        [
            ('draft', 'Draft'),
            ('queued', 'Queued'),
            ('running', 'Running'),
            ('done', 'Done'),
            ('error', 'Error'),
        ],
        string='Status',
        required=True,
        default='done',
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        default=lambda self: self.env.user,
        readonly=True,
    )
    prompt_text = fields.Text(string='Prompt')
    response_text = fields.Text(string='Response')
    summary_text = fields.Text(string='Summary')
    error_message = fields.Text(string='Error')
    repo_full_name = fields.Char(string='Repository')
    branch_name = fields.Char(string='AI Branch')
    base_branch = fields.Char(string='Base Branch')
    commit_sha = fields.Char(string='Commit SHA')
    pr_url = fields.Char(string='Pull Request URL')
    started_at = fields.Datetime(string='Started At', default=fields.Datetime.now)
    finished_at = fields.Datetime(string='Finished At')
