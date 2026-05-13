import logging
from datetime import datetime

from odoo import _, fields
from odoo.exceptions import UserError
from odoo.tools import html2plaintext

from .chatgpt_service import ChatGptPromptService
from .codex_service import CodexService
from .github_service import GitHubService

_logger = logging.getLogger(__name__)


class AiOrchestrator:
    def __init__(self, env):
        self.env = env
        self.chatgpt_service = ChatGptPromptService(env)
        self.codex_service = CodexService(env)
        self.github_service = GitHubService(env)

    def _commit(self):
        self.env['ir.cron']._commit_progress()

    def _write_task(self, task, values, commit=False):
        task.sudo().write(values)
        if commit:
            self._commit()

    def _append_task_log(self, task, message, commit=False):
        timestamp = datetime.now().strftime('%H:%M:%S')
        line = f'[{timestamp}] {message}'
        current_log = task.sudo().ai_progress_log or ''
        updated_log = f"{current_log}\n{line}".strip() if current_log else line
        task.sudo().write({'ai_progress_log': updated_log})
        if commit:
            self._commit()

    def _create_history_entry(self, task, values, commit=False):
        history_entry = self.env['project.task.ai.history'].sudo().create(
            {
                'task_id': task.id,
                **values,
            }
        )
        if commit:
            self._commit()
        return history_entry

    def _update_history_entry(self, history_entry, values, commit=False):
        history_entry = history_entry.sudo().exists()
        if not history_entry:
            return
        history_entry.write(values)
        if commit:
            self._commit()

    def prepare_codex_run(self, task):
        branch_name = self.codex_service.build_branch_name(task)
        base_branch = task.ai_base_branch_id.name or task.ai_repo_id.default_branch or 'main'
        history_entry = self._create_history_entry(
            task,
            {
                'entry_type': 'execution',
                'status': 'queued',
                'prompt_text': task.ai_prompt_final or '',
                'repo_full_name': task.ai_repo_id.full_name or '',
                'branch_name': branch_name,
                'base_branch': base_branch,
                'started_at': fields.Datetime.now(),
            },
            commit=True,
        )
        self._write_task(
            task,
            {
                'ai_status': 'queued',
                'ai_branch': branch_name,
                'ai_current_history_id': history_entry.id,
                'ai_response': False,
                'ai_progress_log': False,
                'ai_commit_sha': False,
                'ai_pr_url': False,
                'ai_error_message': False,
            },
            commit=True,
        )
        self._append_task_log(task, _("Execucao colocada em fila."), commit=True)
        return branch_name

    def _build_response_text(self, execution_result):
        lines = [
            _("Resumo:"),
            execution_result.get('summary') or '',
            '',
            _("Commit:"),
            execution_result.get('commit_message') or '',
            '',
            _("Output bruto do Codex:"),
            execution_result.get('raw_output') or '',
        ]
        return '\n'.join(lines).strip()

    def generate_prompt(self, task):
        prompt_draft = self.chatgpt_service.generate_prompt(task)
        source_text = html2plaintext(task.description or '').strip() or _('Sem descricao funcional.')
        values = {
            'ai_prompt_draft': prompt_draft,
            'ai_status': 'draft',
            'ai_error_message': False,
        }
        if not task.ai_prompt_final:
            values['ai_prompt_final'] = prompt_draft
        self._write_task(task, values)
        self._create_history_entry(
            task,
            {
                'entry_type': 'prompt',
                'status': 'done',
                'prompt_text': source_text,
                'response_text': prompt_draft,
                'summary_text': _('Prompt tecnico gerado para esta task.'),
                'finished_at': fields.Datetime.now(),
            },
        )
        return prompt_draft

    def run_codex(self, task):
        history_entry = task.ai_current_history_id.sudo().exists()
        try:
            if task.ai_status != 'queued':
                self.prepare_codex_run(task)
                history_entry = task.ai_current_history_id.sudo().exists()

            self._write_task(task, {'ai_status': 'running'}, commit=True)
            self._update_history_entry(
                history_entry,
                {
                    'status': 'running',
                    'started_at': fields.Datetime.now(),
                    'prompt_text': task.ai_prompt_final or '',
                    'repo_full_name': task.ai_repo_id.full_name or '',
                    'branch_name': task.ai_branch or '',
                    'base_branch': task.ai_base_branch_id.name or task.ai_repo_id.default_branch or '',
                },
                commit=True,
            )
            self._append_task_log(task, _("Execucao iniciada."), commit=True)

            def progress_callback(message):
                self._append_task_log(task, message, commit=True)

            execution_result = self.codex_service.execute_task(
                task,
                task.ai_prompt_final,
                progress_callback=progress_callback,
            )
            self._write_task(
                task,
                {
                    'ai_branch': execution_result['branch_name'],
                    'ai_commit_sha': execution_result['commit_sha'],
                    'ai_response': self._build_response_text(execution_result),
                    'ai_error_message': False,
                },
                commit=True,
            )
            values = {
                'ai_status': 'done',
                'ai_branch': execution_result['branch_name'],
                'ai_commit_sha': execution_result['commit_sha'],
                'ai_response': self._build_response_text(execution_result),
                'ai_error_message': False,
            }

            if self.github_service.should_create_pull_request() and not execution_result.get('skip_pr'):
                self._append_task_log(task, _("A criar pull request no GitHub."), commit=True)
                pr_data = self.github_service.create_pull_request(
                    task.ai_repo_id,
                    execution_result['branch_name'],
                    execution_result['pr_title'],
                    execution_result['pr_body'],
                    base_branch=(task.ai_base_branch_id.name or False),
                )
                values['ai_pr_url'] = pr_data.get('html_url')
                if pr_data.get('html_url'):
                    self._append_task_log(
                        task,
                        _("Pull request disponivel em %s") % pr_data.get('html_url'),
                        commit=True,
                    )

            self._write_task(task, values, commit=True)
            self._update_history_entry(
                history_entry,
                {
                    'status': 'done',
                    'response_text': self._build_response_text(execution_result),
                    'summary_text': execution_result.get('summary') or '',
                    'commit_sha': values.get('ai_commit_sha') or execution_result.get('commit_sha') or '',
                    'pr_url': values.get('ai_pr_url') or '',
                    'branch_name': execution_result.get('branch_name') or task.ai_branch or '',
                    'base_branch': execution_result.get('base_branch') or task.ai_base_branch_id.name or '',
                    'repo_full_name': task.ai_repo_id.full_name or '',
                    'error_message': False,
                    'finished_at': fields.Datetime.now(),
                },
                commit=True,
            )
            self._append_task_log(task, _("Execucao concluida com sucesso."), commit=True)
            return execution_result
        except UserError as exc:
            self._write_task(
                task,
                {
                    'ai_status': 'error',
                    'ai_error_message': str(exc),
                },
                commit=True,
            )
            self._update_history_entry(
                history_entry,
                {
                    'status': 'error',
                    'error_message': str(exc),
                    'response_text': False,
                    'summary_text': False,
                    'finished_at': fields.Datetime.now(),
                },
                commit=True,
            )
            self._append_task_log(task, _("Erro: %s") % exc, commit=True)
            raise
        except Exception as exc:
            _logger.exception("AI orchestration failed for task %s", task.id)
            self._write_task(
                task,
                {
                    'ai_status': 'error',
                    'ai_error_message': str(exc),
                },
                commit=True,
            )
            self._update_history_entry(
                history_entry,
                {
                    'status': 'error',
                    'error_message': str(exc),
                    'response_text': False,
                    'summary_text': False,
                    'finished_at': fields.Datetime.now(),
                },
                commit=True,
            )
            self._append_task_log(task, _("Erro inesperado: %s") % exc, commit=True)
            raise UserError(_("O fluxo AI falhou: %s") % exc) from exc
