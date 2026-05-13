from dateutil.relativedelta import relativedelta

from odoo import fields


class ProjectChatterIngestionService:
    def __init__(self, env):
        self.env = env

    def _default_since(self):
        return fields.Datetime.now() - relativedelta(days=120)

    def _search_messages(self, model_name, record_ids, since=False):
        if not record_ids:
            return self.env['mail.message']
        domain = [
            ('model', '=', model_name),
            ('res_id', 'in', record_ids),
        ]
        if since:
            domain.append(('date', '>=', since))
        return self.env['mail.message'].sudo().search(domain, order='date asc, id asc')

    def collect_project_messages(self, project, since=False):
        return self._search_messages('project.project', [project.id], since=since or self._default_since())

    def collect_task_messages(self, task, since=False):
        return self._search_messages('project.task', [task.id], since=since or self._default_since())

