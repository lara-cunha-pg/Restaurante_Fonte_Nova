import base64
import json
import logging
import os
import queue
import re
import shlex
import shutil
import subprocess
import tempfile
import threading
import time
from datetime import datetime

import requests

from odoo import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


DEFAULT_EXECUTION_MODE = 'cli'
MAX_CHANGE_REQUEST_ATTEMPTS = 2
MAX_ERROR_OUTPUT_CHARS = 2000
MAX_PROGRESS_MESSAGE_CHARS = 220
DEFAULT_FILE_SELECTION_INSTRUCTIONS = (
    'Seleciona apenas os ficheiros mais relevantes para implementar a tarefa e responde so com JSON.'
)
DEFAULT_CHANGE_REQUEST_INSTRUCTIONS = (
    'Implementa a tarefa no repositorio e responde apenas com JSON de alteracoes.'
)
DEFAULT_CLI_INSTRUCTIONS = (
    'Implementa a tarefa editando diretamente o repositorio atual, sem criar commits nem fazer push, '
    'e no fim devolve apenas o JSON final pedido.'
)
DEFAULT_COMMIT_MESSAGE_TEMPLATE = '[AI] {task_name}'
DEFAULT_PR_TITLE_TEMPLATE = '[AI] {task_name}'
DEFAULT_PR_BODY_TEMPLATE = (
    '## Contexto\n{task_name}\n\n'
    '## Branch\n{branch_name}\n\n'
    '## Branch Base\n{base_branch}\n\n'
    '## Repositorio\n{repo_full_name}\n\n'
    '## Origem\nAlteracoes geradas automaticamente pelo fluxo AI Dev Assistant.'
)


class CodexService:
    RESPONSES_API_URL = 'https://api.openai.com/v1/responses'
    DEFAULT_TIMEOUT = 1800
    DEFAULT_WORKDIR_NAME = 'odoo_codex_repos'
    DEFAULT_MODEL = 'gpt-5.3-codex'
    DEFAULT_TREE_FILE_LIMIT = 600
    DEFAULT_SELECTED_FILE_LIMIT = 12
    DEFAULT_FILE_CHAR_LIMIT = 16000
    DEFAULT_BRANCH_PREFIX = 'ai/task'
    DEFAULT_CLI_COMMAND = 'npx'
    DEFAULT_CLI_ARGS = '@openai/codex'
    DEFAULT_CLI_RUNTIME_PROFILE = 'dangerous'
    DEFAULT_FALLBACK_PRIORITY_FILENAMES = (
        '__manifest__.py',
        'README.md',
        'README.rst',
        'requirements.txt',
        'pyproject.toml',
        '__init__.py',
    )
    DEFAULT_FALLBACK_EXTENSIONS = ('.py', '.xml', '.js', '.csv', '.md', '.rst')

    def __init__(self, env):
        self.env = env
        self.params = env['ir.config_parameter'].sudo()

    def _get_param(self, key, default=None):
        return self.params.get_param(key, default)

    def _get_positive_int(self, key, default):
        value = self._get_param(key, default)
        try:
            return max(int(value), 1)
        except (TypeError, ValueError):
            return default

    def _get_timeout(self):
        return self._get_positive_int('codex_timeout', self.DEFAULT_TIMEOUT)

    def should_cleanup_local_workspace(self):
        value = self._get_param('pg_ai_cleanup_local_workspace', 'True')
        return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}

    def _get_execution_mode(self):
        execution_mode = (self._get_param('codex_execution_mode', DEFAULT_EXECUTION_MODE) or DEFAULT_EXECUTION_MODE).strip()
        if execution_mode not in {'service', 'cli'}:
            return DEFAULT_EXECUTION_MODE
        return execution_mode

    def _get_model(self):
        return (self._get_param('codex_execution_model', self.DEFAULT_MODEL) or self.DEFAULT_MODEL).strip()

    def _split_command_string(self, raw_value):
        return shlex.split((raw_value or '').strip(), posix=(os.name != 'nt'))

    def _get_cli_command_parts(self):
        command = (self._get_param('codex_cli_command', self.DEFAULT_CLI_COMMAND) or self.DEFAULT_CLI_COMMAND).strip()
        args = (self._get_param('codex_cli_args', self.DEFAULT_CLI_ARGS) or self.DEFAULT_CLI_ARGS).strip()
        if command == 'npx' and args == 'codex':
            args = self.DEFAULT_CLI_ARGS
        parts = []
        parts.extend(self._split_command_string(command))
        parts.extend(self._split_command_string(args))
        return parts or [self.DEFAULT_CLI_COMMAND, self.DEFAULT_CLI_ARGS]

    def _get_cli_runtime_profile(self):
        return self.DEFAULT_CLI_RUNTIME_PROFILE

    def _get_cli_extra_args(self):
        return self._split_command_string(self._get_param('codex_cli_extra_args'))

    def _is_dangerous_cli_runtime(self, runtime_profile=None):
        return (runtime_profile or self._get_cli_runtime_profile()) == 'dangerous'

    def _join_command_parts(self, parts):
        return ' '.join(part for part in (parts or []) if part)

    def _cli_candidate_commands(self):
        candidates = []
        configured_parts = self._get_cli_command_parts()
        if configured_parts:
            candidates.append(configured_parts)
        candidates.extend([
            ['codex'],
            ['npx', '@openai/codex'],
        ])

        unique_candidates = []
        seen = set()
        for candidate in candidates:
            normalized = tuple(candidate)
            if not normalized or normalized in seen:
                continue
            unique_candidates.append(list(candidate))
            seen.add(normalized)
        return unique_candidates

    def _probe_codex_cli(self, command_parts):
        version_result = self._run_process([*command_parts, '--version'], timeout=30, allow_failure=True)
        exec_help_result = self._run_process([*command_parts, 'exec', '--help'], timeout=30, allow_failure=True)
        if version_result.returncode != 0 or exec_help_result.returncode != 0:
            return False
        version_output = (version_result.stdout or version_result.stderr or '').strip()
        help_output = (exec_help_result.stdout or exec_help_result.stderr or '').strip()
        if 'codex' not in version_output.lower():
            return False
        if 'Run Codex non-interactively' not in help_output and 'codex exec' not in help_output.lower():
            return False
        return {
            'command_parts': command_parts,
            'version': version_output,
            'supports_exec': True,
        }

    def discover_cli_configuration(self):
        last_error = ''
        for candidate in self._cli_candidate_commands():
            try:
                result = self._probe_codex_cli(candidate)
            except UserError as exc:
                last_error = str(exc)
                continue
            if not result:
                continue

            command = candidate[0]
            args = self._join_command_parts(candidate[1:])
            return {
                'available': True,
                'command': command,
                'args': args,
                'display_command': self._join_command_parts(candidate),
                'version': result.get('version') or '',
                'supports_exec': True,
                'runtime_profile': self.DEFAULT_CLI_RUNTIME_PROFILE,
            }

        error_message = _("Nao foi possivel detetar um launcher Codex CLI funcional neste servidor.")
        if last_error:
            error_message = "%s\n%s" % (error_message, last_error)
        raise UserError(error_message)

    def _get_working_dir(self):
        configured_path = (self._get_param('codex_working_dir') or '').strip()
        if configured_path:
            return configured_path
        return os.path.join(tempfile.gettempdir(), self.DEFAULT_WORKDIR_NAME)

    def get_default_working_dir(self):
        return os.path.join(tempfile.gettempdir(), self.DEFAULT_WORKDIR_NAME)

    def _get_branch_prefix(self):
        return (self._get_param('codex_branch_prefix', self.DEFAULT_BRANCH_PREFIX) or self.DEFAULT_BRANCH_PREFIX).strip().strip('/')

    def should_push_directly_to_selected_branch(self):
        value = self._get_param('pg_ai_push_direct_to_selected_branch', 'True')
        return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}

    def _get_git_user_name(self):
        return (self._get_param('codex_git_user_name') or self.env.user.name or 'Odoo AI Bot').strip()

    def _get_git_user_email(self):
        return (self._get_param('codex_git_user_email') or self.env.user.email or 'odoo-ai@example.invalid').strip()

    def _get_repo_tree_file_limit(self):
        return self._get_positive_int('codex_repo_tree_file_limit', self.DEFAULT_TREE_FILE_LIMIT)

    def _get_selected_file_limit(self):
        return self._get_positive_int('codex_selected_file_limit', self.DEFAULT_SELECTED_FILE_LIMIT)

    def _get_file_content_char_limit(self):
        return self._get_positive_int('codex_file_content_char_limit', self.DEFAULT_FILE_CHAR_LIMIT)

    def _parse_text_list(self, raw_value, default_values):
        values = []
        for part in (raw_value or '').replace('\r', '\n').replace(',', '\n').split('\n'):
            item = part.strip()
            if item and item not in values:
                values.append(item)
        if values:
            return values
        return list(default_values)

    def _get_fallback_priority_filenames(self):
        return self._parse_text_list(
            self._get_param('codex_fallback_priority_filenames'),
            self.DEFAULT_FALLBACK_PRIORITY_FILENAMES,
        )

    def _get_fallback_extensions(self):
        raw_extensions = self._parse_text_list(
            self._get_param('codex_fallback_extensions'),
            self.DEFAULT_FALLBACK_EXTENSIONS,
        )
        normalized = []
        for extension in raw_extensions:
            normalized_extension = extension if extension.startswith('.') else f'.{extension}'
            if normalized_extension not in normalized:
                normalized.append(normalized_extension)
        return tuple(normalized)

    def _get_file_selection_instructions(self):
        return (
            self._get_param('codex_file_selection_instructions', DEFAULT_FILE_SELECTION_INSTRUCTIONS)
            or DEFAULT_FILE_SELECTION_INSTRUCTIONS
        )

    def _get_change_request_instructions(self):
        return (
            self._get_param('codex_change_request_instructions', DEFAULT_CHANGE_REQUEST_INSTRUCTIONS)
            or DEFAULT_CHANGE_REQUEST_INSTRUCTIONS
        )

    def _get_cli_instructions(self):
        return self._get_param('codex_cli_instructions', DEFAULT_CLI_INSTRUCTIONS) or DEFAULT_CLI_INSTRUCTIONS

    def _get_commit_message_template(self):
        return self._get_param('codex_commit_message_template', DEFAULT_COMMIT_MESSAGE_TEMPLATE) or DEFAULT_COMMIT_MESSAGE_TEMPLATE

    def _get_pr_title_template(self):
        return self._get_param('codex_pr_title_template', DEFAULT_PR_TITLE_TEMPLATE) or DEFAULT_PR_TITLE_TEMPLATE

    def _get_pr_body_template(self):
        return self._get_param('codex_pr_body_template', DEFAULT_PR_BODY_TEMPLATE) or DEFAULT_PR_BODY_TEMPLATE

    def _render_template(self, template, **values):
        try:
            return (template or '').format(**values).strip()
        except Exception:
            _logger.exception("Failed to render configurable template")
            return (template or '').strip()

    def _get_openai_api_key(self):
        api_key = (self._get_param('pg_openai_api_key') or '').strip()
        if not api_key:
            raise UserError(_("Configuracao em falta: OpenAI API Key."))
        return api_key

    def _openai_headers(self):
        return {
            'Authorization': f'Bearer {self._get_openai_api_key()}',
            'Content-Type': 'application/json',
        }

    def _extract_output_text(self, payload):
        output_text = (payload or {}).get('output_text')
        if output_text:
            return output_text.strip()

        chunks = []
        for output in (payload or {}).get('output', []):
            for content in output.get('content', []):
                text = content.get('text') or content.get('value')
                if text and content.get('type') in {'output_text', 'text'}:
                    chunks.append(text.strip())
        return '\n\n'.join(filter(None, chunks)).strip()

    def _response_text(self, instructions, input_text, failure_message, text_format=None):
        payload = {
            'model': self._get_model(),
            'instructions': instructions,
            'input': input_text,
            'text': {'format': text_format or {'type': 'text'}},
        }
        try:
            response = requests.post(
                self.RESPONSES_API_URL,
                headers=self._openai_headers(),
                json=payload,
                timeout=self._get_timeout(),
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            _logger.exception("Codex cloud request failed")
            raise UserError(failure_message % exc) from exc

        result = self._extract_output_text(response.json())
        if not result:
            raise UserError(_("O Codex cloud nao devolveu texto utilizavel."))
        return result

    def _json_schema_format(self, name, schema):
        return {
            'type': 'json_schema',
            'name': name,
            'strict': True,
            'schema': schema,
        }

    def _report_progress(self, progress_callback, message):
        if callable(progress_callback):
            progress_callback(message)

    def _slugify(self, value):
        slug = re.sub(r'[^a-z0-9]+', '-', (value or '').lower()).strip('-')
        return slug or 'task'

    def build_branch_name(self, task):
        if self.should_push_directly_to_selected_branch():
            selected_branch = (
                task.ai_base_branch_id.name
                or task.ai_repo_id.default_branch
                or self._get_param('pg_github_default_branch', 'main')
                or 'main'
            ).strip()
            return selected_branch or 'main'
        if task.ai_branch:
            return task.ai_branch
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        prefix = self._get_branch_prefix() or self.DEFAULT_BRANCH_PREFIX
        return f"{prefix}-{task.id}-{self._slugify(task.name)[:40]}-{timestamp}"

    def _github_token(self):
        token = (self._get_param('pg_github_token') or '').strip()
        if not token:
            raise UserError(_("Configuracao em falta: GitHub Token."))
        return token

    def _git_auth_header(self):
        credentials = f"x-access-token:{self._github_token()}".encode()
        encoded = base64.b64encode(credentials).decode()
        return f'AUTHORIZATION: basic {encoded}'

    def _run_process(self, command, cwd=None, timeout=None, failure_message=None, allow_failure=False):
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError as exc:
            raise UserError(_("Executavel nao encontrado: %s") % command[0]) from exc
        except subprocess.TimeoutExpired as exc:
            raise UserError(_("O comando excedeu o timeout configurado.")) from exc

        if result.returncode != 0 and not allow_failure:
            error_output = (result.stderr or result.stdout or '').strip()
            if failure_message:
                raise UserError("%s\n%s" % (failure_message, error_output))
            raise UserError(error_output or _("O comando devolveu um codigo de erro."))
        return result

    def _git(self, repo_path, *args, failure_message=None, allow_failure=False):
        command = ['git', '-c', f'http.extraHeader={self._git_auth_header()}', *args]
        return self._run_process(
            command,
            cwd=repo_path,
            timeout=self._get_timeout(),
            failure_message=failure_message,
            allow_failure=allow_failure,
        )

    def _clone_repository(self, repository, repo_path):
        os.makedirs(os.path.dirname(repo_path), exist_ok=True)
        remote_url = f'https://github.com/{repository.github_owner}/{repository.github_repo}.git'
        command = [
            'git',
            '-c',
            f'http.extraHeader={self._git_auth_header()}',
            'clone',
            remote_url,
            repo_path,
        ]
        self._run_process(command, timeout=self._get_timeout(), failure_message=_("Falha ao clonar o repositorio GitHub."))

    def _ensure_clean_worktree(self, repo_path):
        status = self._git(repo_path, 'status', '--porcelain')
        if status.stdout.strip():
            raise UserError(
                _("O repositorio local %s tem alteracoes pendentes. Limpe a working tree antes de reutilizar a pasta.")
                % repo_path
            )

    def _ensure_git_identity(self, repo_path):
        name = self._git(repo_path, 'config', '--get', 'user.name', allow_failure=True).stdout.strip()
        email = self._git(repo_path, 'config', '--get', 'user.email', allow_failure=True).stdout.strip()
        if not name:
            self._git(repo_path, 'config', 'user.name', self._get_git_user_name())
        if not email:
            self._git(repo_path, 'config', 'user.email', self._get_git_user_email())

    def _create_temporary_repo_workspace(self, repository):
        workspace_root = self._get_working_dir()
        os.makedirs(workspace_root, exist_ok=True)
        workspace_prefix = f"{self._slugify(repository.github_owner)}__{self._slugify(repository.github_repo)}__"
        return tempfile.mkdtemp(prefix=workspace_prefix, dir=workspace_root)

    def _cleanup_repo_workspace(self, repo_path):
        if not repo_path or not os.path.isdir(repo_path):
            return
        shutil.rmtree(repo_path, ignore_errors=True)

    def _prepare_repository(self, repository, branch_name, base_branch):
        repo_path = self._create_temporary_repo_workspace(repository)
        try:
            self._clone_repository(repository, repo_path)
        except Exception:
            self._cleanup_repo_workspace(repo_path)
            raise

        source_branch = (base_branch or repository.default_branch or self._get_param('pg_github_default_branch', 'main') or 'main').strip()
        self._git(repo_path, 'fetch', 'origin', failure_message=_("Falha ao atualizar o repositorio local."))
        self._git(repo_path, 'checkout', source_branch, failure_message=_("Falha ao mudar para a branch base."))
        self._git(
            repo_path,
            'pull',
            '--ff-only',
            'origin',
            source_branch,
            failure_message=_("Falha ao atualizar a branch base."),
        )

        remote_branch_exists = self._git(
            repo_path,
            'ls-remote',
            '--heads',
            'origin',
            branch_name,
            failure_message=_("Falha ao validar a branch remota."),
        ).stdout.strip()
        target_ref = f'origin/{branch_name}' if remote_branch_exists else f'origin/{source_branch}'
        self._git(
            repo_path,
            'checkout',
            '-B',
            branch_name,
            target_ref,
            failure_message=_("Falha ao preparar a branch de trabalho."),
        )
        self._ensure_git_identity(repo_path)
        return repo_path

    def _list_repo_files(self, repo_path):
        result = self._git(repo_path, 'ls-files', failure_message=_("Falha ao listar ficheiros do repositorio."))
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def _fallback_file_selection(self, files):
        selected = []
        priority_names = tuple(self._get_fallback_priority_filenames())
        allowed_extensions = self._get_fallback_extensions()
        selected_file_limit = self._get_selected_file_limit()

        for preferred_name in priority_names:
            for file_path in files:
                if file_path.endswith(preferred_name) and file_path not in selected:
                    selected.append(file_path)

        for file_path in files:
            if len(selected) >= selected_file_limit:
                break
            if file_path in selected:
                continue
            if file_path.endswith(allowed_extensions):
                selected.append(file_path)
        return selected[:selected_file_limit]

    def _file_selection_schema(self):
        return self._json_schema_format(
            'file_selection',
            {
                'type': 'object',
                'properties': {
                    'files_to_read': {
                        'type': 'array',
                        'items': {'type': 'string'},
                    },
                },
                'required': ['files_to_read'],
                'additionalProperties': False,
            },
        )

    def _select_files_for_task(self, repo_path, task, prompt):
        files = self._list_repo_files(repo_path)
        if not files:
            raise UserError(_("O repositorio nao contem ficheiros versionados."))

        tree_limit = self._get_repo_tree_file_limit()
        selected_file_limit = self._get_selected_file_limit()
        tree_lines = files[:tree_limit]
        truncated_note = ''
        if len(files) > tree_limit:
            truncated_note = f"\nNota: a arvore foi truncada para os primeiros {tree_limit} ficheiros."
        selection_prompt = (
            f"Task: {task.name}\n"
            f"Prompt tecnico:\n{prompt.strip()}\n\n"
            "Arvore do repositorio:\n"
            f"{chr(10).join(tree_lines)}"
            f"{truncated_note}\n\n"
            "Responde apenas com JSON valido no formato:\n"
            '{"files_to_read": ["path/one.py", "path/two.xml"]}\n'
            f"Seleciona no maximo {selected_file_limit} ficheiros existentes que precisas de ler para implementar a task."
        )
        raw_output = self._response_text(
            self._get_file_selection_instructions(),
            selection_prompt,
            _("Falha ao selecionar ficheiros com Codex cloud: %s"),
            text_format=self._file_selection_schema(),
        )
        payload = self._extract_json_payload(raw_output)
        selected_files = payload.get('files_to_read') or payload.get('files') or []
        if not isinstance(selected_files, list):
            selected_files = []

        existing_files = set(files)
        filtered_paths = []
        for file_path in selected_files:
            normalized_path = self._normalize_relative_path(file_path)
            if normalized_path and normalized_path in existing_files and normalized_path not in filtered_paths:
                filtered_paths.append(normalized_path)

        if filtered_paths:
            return filtered_paths[:selected_file_limit], files
        return self._fallback_file_selection(files), files

    def _read_file_snapshots(self, repo_path, file_paths):
        snapshots = []
        char_limit = self._get_file_content_char_limit()
        for file_path in file_paths:
            absolute_path = os.path.join(repo_path, file_path)
            try:
                with open(absolute_path, 'r', encoding='utf-8') as handle:
                    content = handle.read()
            except UnicodeDecodeError:
                with open(absolute_path, 'r', encoding='utf-8', errors='ignore') as handle:
                    content = handle.read()
            except OSError:
                continue

            if len(content) > char_limit:
                content = content[:char_limit] + '\n...[truncated]...'
            snapshots.append((file_path, content))
        return snapshots

    def _normalize_relative_path(self, file_path):
        normalized_path = os.path.normpath((file_path or '').strip()).replace('\\', '/')
        if not normalized_path or normalized_path == '.':
            return ''
        if normalized_path.startswith('../') or normalized_path.startswith('/') or os.path.isabs(normalized_path):
            raise UserError(_("O Codex tentou escrever fora do repositorio: %s") % file_path)
        return normalized_path

    def _build_change_request(self, repo_path, task, prompt):
        selected_files, all_files = self._select_files_for_task(repo_path, task, prompt)
        snapshots = self._read_file_snapshots(repo_path, selected_files)
        repo_tree = '\n'.join(all_files[: self._get_repo_tree_file_limit()])
        inspected_files = []
        for file_path, content in snapshots:
            inspected_files.append(f"FILE: {file_path}\n-----\n{content}")

        base_branch = task.ai_base_branch_id.name or task.ai_repo_id.default_branch or 'main'
        concrete_change_rule = (
            "A tarefa e de implementacao. Devolve alteracoes concretas quando houver trabalho para fazer.\n"
            "Nao devolvas ficheiros inalterados em changes.\n"
            "Cada item em changes tem de criar, apagar ou modificar efetivamente o repositorio.\n"
        )
        request_text = (
            f"Task: {task.name}\n"
            f"Repositorio: {task.ai_repo_id.full_name}\n"
            f"Branch base: {base_branch}\n\n"
            f"Prompt tecnico:\n{prompt.strip()}\n\n"
            "Arvore do repositorio:\n"
            f"{repo_tree}\n\n"
            "Conteudo dos ficheiros lidos:\n"
            f"{chr(10).join(inspected_files)}\n\n"
            "Responde apenas com JSON valido no formato:\n"
            '{'
            '"summary": "resumo curto",'
            '"commit_message": "mensagem de commit",'
            '"pr_title": "titulo do PR",'
            '"pr_body": "descricao do PR",'
            '"changes": ['
            '{"path": "relative/path.py", "content": "conteudo completo do ficheiro"}'
            ']'
            '}\n'
            "Regras:\n"
            "- Podes criar ficheiros novos.\n"
            '- Para apagar ficheiros usa {"path": "x", "delete": true}.\n'
            "- So podes alterar ficheiros dentro do repositorio.\n"
            "- Para ficheiros existentes devolve o conteudo completo final.\n"
            "- Nao uses markdown nem code fences.\n"
            "- Se nao for necessario alterar nada, devolve changes como lista vazia.\n"
            f"{concrete_change_rule}"
        )
        raw_output = self._response_text(
            self._get_change_request_instructions(),
            request_text,
            _("Falha ao gerar alteracoes com Codex cloud: %s"),
            text_format=self._json_schema_format(
                'codex_change_request',
                {
                    'type': 'object',
                    'properties': {
                        'summary': {'type': 'string'},
                        'commit_message': {'type': 'string'},
                        'pr_title': {'type': 'string'},
                        'pr_body': {'type': 'string'},
                        'changes': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'path': {'type': 'string'},
                                    'content': {'type': 'string'},
                                    'delete': {'type': 'boolean'},
                                },
                                'required': ['path', 'content', 'delete'],
                                'additionalProperties': False,
                            },
                        },
                    },
                    'required': ['summary', 'commit_message', 'pr_title', 'pr_body', 'changes'],
                    'additionalProperties': False,
                },
            ),
        )
        payload = self._extract_json_payload(raw_output)
        if not payload:
            raise UserError(_("O Codex cloud nao devolveu um objeto JSON valido com alteracoes."))
        payload['_raw_output'] = raw_output
        return payload

    def _read_current_file_content(self, absolute_path):
        try:
            with open(absolute_path, 'r', encoding='utf-8') as handle:
                return handle.read()
        except UnicodeDecodeError:
            with open(absolute_path, 'r', encoding='utf-8', errors='ignore') as handle:
                return handle.read()
        except OSError:
            return None

    def _has_effective_changes(self, repo_path, changes):
        if not isinstance(changes, list):
            raise UserError(_("O Codex cloud devolveu alteracoes invalidas."))

        for change in changes:
            if not isinstance(change, dict):
                continue
            relative_path = self._normalize_relative_path(change.get('path'))
            if not relative_path:
                continue

            absolute_path = os.path.join(repo_path, relative_path)
            if change.get('delete'):
                if os.path.exists(absolute_path):
                    return True
                continue

            if 'content' not in change:
                continue
            new_content = change.get('content') or ''
            if not os.path.exists(absolute_path):
                return True

            current_content = self._read_current_file_content(absolute_path)
            if current_content != new_content:
                return True
        return False

    def _get_noop_change_paths(self, repo_path, changes):
        noop_paths = []
        if not isinstance(changes, list):
            return noop_paths

        for change in changes:
            if not isinstance(change, dict):
                continue
            relative_path = self._normalize_relative_path(change.get('path'))
            if not relative_path:
                continue

            absolute_path = os.path.join(repo_path, relative_path)
            if change.get('delete'):
                if not os.path.exists(absolute_path):
                    noop_paths.append(relative_path)
                continue

            if 'content' not in change or not os.path.exists(absolute_path):
                continue

            current_content = self._read_current_file_content(absolute_path)
            if current_content == (change.get('content') or ''):
                noop_paths.append(relative_path)
        return noop_paths

    def _get_change_paths(self, changes):
        paths = []
        if not isinstance(changes, list):
            return paths

        for change in changes:
            if not isinstance(change, dict):
                continue
            relative_path = self._normalize_relative_path(change.get('path'))
            if relative_path and relative_path not in paths:
                paths.append(relative_path)
        return paths

    def _shorten_output(self, output):
        shortened_output = (output or '').strip()
        if len(shortened_output) <= MAX_ERROR_OUTPUT_CHARS:
            return shortened_output
        return shortened_output[:MAX_ERROR_OUTPUT_CHARS].rstrip() + '\n...[truncated]...'

    def _shorten_progress_message(self, text):
        message = re.sub(r'\s+', ' ', (text or '').strip())
        if len(message) <= MAX_PROGRESS_MESSAGE_CHARS:
            return message
        return message[:MAX_PROGRESS_MESSAGE_CHARS].rstrip() + '...'

    def _build_continuity_enriched_prompt(self, task, prompt):
        base_prompt = (prompt or '').strip()
        continuity_context = task.build_ai_continuity_context(exclude_current_run=True)
        if not continuity_context:
            return base_prompt
        return (
            f"{base_prompt}\n\n"
            "Contexto acumulado da task:\n"
            f"{continuity_context}\n\n"
            "Regras de continuidade:\n"
            "- Preserva o trabalho anterior desta task.\n"
            "- Se o novo pedido complementar o anterior, continua a partir do estado atual.\n"
            "- Nao voltes atras nem removas alteracoes anteriores sem instrucao explicita.\n"
        ).strip()

    def _build_change_request_with_retry(self, repo_path, task, prompt, progress_callback=None):
        previous_output = ''
        last_payload = {}
        for attempt in range(1, MAX_CHANGE_REQUEST_ATTEMPTS + 1):
            if attempt == 1:
                self._report_progress(progress_callback, _("A pedir alteracoes ao Codex Cloud."))
            else:
                self._report_progress(progress_callback, _("Nova tentativa com instrucoes reforcadas para obter alteracoes efetivas."))
            retry_note = ''
            if previous_output:
                retry_note = (
                    "\nTentativa anterior sem alteracoes efetivas no repositorio.\n"
                    "Output anterior resumido:\n"
                    f"{self._shorten_output(previous_output)}\n\n"
                    "Corrige isso agora. Devolve pelo menos uma alteracao efetiva e nao repitas ficheiros sem diff.\n"
                )
            payload = self._build_change_request(repo_path, task, prompt + retry_note)
            last_payload = payload
            if self._has_effective_changes(repo_path, payload.get('changes') or []):
                return payload
            previous_output = payload.get('_raw_output') or ''
        last_payload['_no_effective_changes'] = True
        return last_payload

    def _apply_changes(self, repo_path, changes):
        if not isinstance(changes, list):
            raise UserError(_("O Codex cloud devolveu alteracoes invalidas."))

        for change in changes:
            if not isinstance(change, dict):
                continue
            relative_path = self._normalize_relative_path(change.get('path'))
            if not relative_path:
                continue
            absolute_path = os.path.join(repo_path, relative_path)

            if change.get('delete'):
                if os.path.exists(absolute_path):
                    os.remove(absolute_path)
                continue

            if 'content' not in change:
                continue
            parent_dir = os.path.dirname(absolute_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            with open(absolute_path, 'w', encoding='utf-8', newline='') as handle:
                handle.write(change.get('content') or '')

    def _extract_json_payload(self, output):
        decoder = json.JSONDecoder()
        parsed_payload = {}
        for index, char in enumerate(output or ''):
            if char != '{':
                continue
            try:
                payload, _end = decoder.raw_decode(output[index:])
            except ValueError:
                continue
            if isinstance(payload, dict):
                parsed_payload = payload
        return parsed_payload

    def _codex_cli_output_schema(self):
        return {
            'type': 'object',
            'properties': {
                'summary': {'type': 'string'},
                'commit_message': {'type': 'string'},
                'pr_title': {'type': 'string'},
                'pr_body': {'type': 'string'},
            },
            'required': ['summary', 'commit_message', 'pr_title', 'pr_body'],
            'additionalProperties': False,
        }

    def _build_cli_exec_prompt(self, task, prompt, branch_name, base_branch):
        cli_instructions = self._get_cli_instructions().strip()
        return (
            f"Repositorio: {task.ai_repo_id.full_name}\n"
            f"Branch de trabalho: {branch_name}\n"
            f"Branch base: {base_branch}\n\n"
            "Objetivo tecnico da task:\n"
            f"{prompt.strip()}\n\n"
            "Regras obrigatorias:\n"
            "- Trabalha apenas dentro do repositorio Git atual.\n"
            "- Implementa as alteracoes diretamente na working tree local.\n"
            "- Nao cries commits, nao facas push e nao abras PR; isso sera tratado pelo Odoo.\n"
            "- Podes correr comandos locais para inspecao e validacao dentro do repositorio.\n"
            "- No fim responde apenas com JSON valido que respeite o schema fornecido.\n"
            "- Se concluires que nao ha nada a alterar, explica isso no summary.\n\n"
            "Instrucoes adicionais configuradas:\n"
            f"{cli_instructions}\n"
        )

    def _relative_repo_path(self, repo_path, file_path):
        if not file_path:
            return ''
        try:
            relative_path = os.path.relpath(file_path, repo_path)
        except ValueError:
            return file_path
        normalized_path = relative_path.replace('\\', '/')
        if normalized_path.startswith('../'):
            return file_path
        return normalized_path

    def _build_codex_cli_command(self, repo_path, prompt, schema_path, output_path, runtime_profile=None):
        command = [*self._get_cli_command_parts(), 'exec', '--json', '--output-schema', schema_path, '--output-last-message', output_path]
        model = self._get_model()
        if model:
            command.extend(['-m', model])

        if self._is_dangerous_cli_runtime(runtime_profile):
            command.append('--dangerously-bypass-approvals-and-sandbox')
        else:
            command.append('--full-auto')

        command.extend(['-C', repo_path])
        command.extend(self._get_cli_extra_args())
        command.append(prompt)
        return command

    def _cli_output_indicates_sandbox_issue(self, output):
        haystack = (output or '').lower()
        sandbox_markers = (
            'sandbox(denied',
            'bwrap:',
            'operation not permitted',
            'exec_command failed',
            'createprocess { message:',
        )
        return any(marker in haystack for marker in sandbox_markers)

    def _handle_codex_cli_event(self, repo_path, raw_line, progress_callback):
        line = (raw_line or '').strip()
        if not line:
            return
        try:
            event = json.loads(line)
        except ValueError:
            if line and 'shell_snapshot' not in line:
                self._report_progress(progress_callback, _("Codex CLI: %s") % self._shorten_progress_message(line))
            return

        event_type = event.get('type')
        if event_type == 'thread.started':
            self._report_progress(progress_callback, _("Sessao Codex CLI iniciada."))
            return

        item = event.get('item') or {}
        item_type = item.get('type')

        if event_type == 'item.started' and item_type == 'command_execution':
            self._report_progress(
                progress_callback,
                _("Codex a executar: %s") % self._shorten_progress_message(item.get('command') or ''),
            )
            return

        if event_type == 'item.completed' and item_type == 'command_execution':
            if item.get('exit_code') not in (None, 0):
                self._report_progress(
                    progress_callback,
                    _("Comando Codex terminou com exit code %s.") % item.get('exit_code'),
                )
            return

        if event_type == 'item.completed' and item_type == 'file_change':
            changed_paths = []
            for change in item.get('changes') or []:
                relative_path = self._relative_repo_path(repo_path, change.get('path') or '')
                if relative_path and relative_path not in changed_paths:
                    changed_paths.append(relative_path)
            if changed_paths:
                preview = ', '.join(changed_paths[:6])
                if len(changed_paths) > 6:
                    preview += ', ...'
                self._report_progress(progress_callback, _("Codex alterou ficheiros: %s") % preview)
            return

        if event_type == 'item.completed' and item_type == 'agent_message':
            text = (item.get('text') or '').strip()
            if text and not text.startswith('{'):
                self._report_progress(progress_callback, _("Codex: %s") % self._shorten_progress_message(text))

    def _run_streaming_process(self, command, cwd=None, timeout=None, failure_message=None, progress_line_callback=None):
        try:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except FileNotFoundError as exc:
            raise UserError(_("Executavel nao encontrado: %s") % command[0]) from exc

        line_queue = queue.Queue()
        output_lines = []

        def _reader():
            try:
                for line in iter(process.stdout.readline, ''):
                    line_queue.put(line)
            finally:
                if process.stdout:
                    process.stdout.close()
                line_queue.put(None)

        reader_thread = threading.Thread(target=_reader, daemon=True)
        reader_thread.start()

        deadline = time.monotonic() + (timeout or self._get_timeout())
        reader_finished = False
        while not reader_finished:
            if time.monotonic() > deadline:
                process.kill()
                reader_thread.join(timeout=2)
                raise UserError(_("O comando excedeu o timeout configurado."))
            try:
                line = line_queue.get(timeout=0.5)
            except queue.Empty:
                if process.poll() is not None and not reader_thread.is_alive():
                    break
                continue

            if line is None:
                reader_finished = True
                continue

            output_lines.append(line)
            if callable(progress_line_callback):
                progress_line_callback(line)

        reader_thread.join(timeout=2)
        return_code = process.wait(timeout=5)
        output_text = ''.join(output_lines).strip()
        if return_code != 0:
            if failure_message:
                raise UserError("%s\n%s" % (failure_message, output_text))
            raise UserError(output_text or _("O comando devolveu um codigo de erro."))
        return {'returncode': return_code, 'stdout': output_text}

    def _run_codex_cli(self, repo_path, task, prompt, branch_name, base_branch, progress_callback=None, runtime_profile=None):
        work_dir = tempfile.mkdtemp(prefix='pg_ai_codex_cli_')
        schema_path = os.path.join(work_dir, 'output_schema.json')
        output_path = os.path.join(work_dir, 'last_message.json')

        try:
            with open(schema_path, 'w', encoding='utf-8', newline='\n') as schema_file:
                json.dump(self._codex_cli_output_schema(), schema_file, ensure_ascii=True, indent=2)

            command = self._build_codex_cli_command(
                repo_path,
                self._build_cli_exec_prompt(task, prompt, branch_name, base_branch),
                schema_path,
                output_path,
                runtime_profile=runtime_profile,
            )
            if self._is_dangerous_cli_runtime(runtime_profile):
                self._report_progress(progress_callback, _("A executar Codex CLI local sem sandbox."))
            else:
                self._report_progress(progress_callback, _("A executar Codex CLI local."))
            try:
                process_result = self._run_streaming_process(
                    command,
                    cwd=repo_path,
                    timeout=self._get_timeout(),
                    failure_message=_("Falha ao executar o Codex CLI local."),
                    progress_line_callback=lambda line: self._handle_codex_cli_event(repo_path, line, progress_callback),
                )
            except UserError as exc:
                if not self._is_dangerous_cli_runtime(runtime_profile) and self._cli_output_indicates_sandbox_issue(str(exc)):
                    self._report_progress(
                        progress_callback,
                        _("Falha de sandbox no Codex CLI; vou repetir sem sandbox."),
                    )
                    return self._run_codex_cli(
                        repo_path,
                        task,
                        prompt,
                        branch_name,
                        base_branch,
                        progress_callback=progress_callback,
                        runtime_profile='dangerous',
                    )
                raise

            final_message = ''
            if os.path.exists(output_path):
                with open(output_path, 'r', encoding='utf-8', errors='ignore') as output_file:
                    final_message = output_file.read().strip()

            payload = self._extract_json_payload(final_message)
            if not payload:
                payload = {
                    'summary': final_message or _("Execucao concluida sem metadados estruturados."),
                    'commit_message': '',
                    'pr_title': '',
                    'pr_body': '',
                }
            raw_output = final_message or process_result.get('stdout') or ''
            payload['_raw_output'] = raw_output
            payload['_cli_runtime_profile'] = runtime_profile or self._get_cli_runtime_profile()
            payload['_cli_sandbox_issue'] = self._cli_output_indicates_sandbox_issue(process_result.get('stdout') or raw_output)
            return payload
        finally:
            for temp_path in (schema_path, output_path):
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass
            try:
                os.rmdir(work_dir)
            except OSError:
                pass

    def _default_commit_message(self, task, branch_name, base_branch):
        return self._render_template(
            self._get_commit_message_template(),
            task_name=task.name or '',
            branch_name=branch_name,
            base_branch=base_branch,
            repo_full_name=task.ai_repo_id.full_name or '',
        ) or f"[AI] {task.name}"

    def _default_pr_title(self, task, branch_name, base_branch):
        return self._render_template(
            self._get_pr_title_template(),
            task_name=task.name or '',
            branch_name=branch_name,
            base_branch=base_branch,
            repo_full_name=task.ai_repo_id.full_name or '',
        ) or f"[AI] {task.name}"

    def _default_pr_body(self, task, branch_name, base_branch):
        return self._render_template(
            self._get_pr_body_template(),
            task_name=task.name or '',
            branch_name=branch_name,
            base_branch=base_branch,
            repo_full_name=task.ai_repo_id.full_name or '',
        )

    def _get_head_commit_sha(self, repo_path):
        return self._git(repo_path, 'rev-parse', 'HEAD').stdout.strip()

    def _get_head_commit_message(self, repo_path):
        return self._git(repo_path, 'log', '-1', '--pretty=%s').stdout.strip()

    def _get_branch_diff_against_base(self, repo_path, base_branch):
        diff_result = self._git(
            repo_path,
            'diff',
            '--name-only',
            f'origin/{base_branch}...HEAD',
            failure_message=_("Falha ao comparar a branch AI com a branch base."),
        )
        return [line.strip() for line in diff_result.stdout.splitlines() if line.strip()]

    def _build_existing_branch_result(self, task, repo_path, branch_name, base_branch, payload, changed_files):
        raw_summary = (payload.get('summary') or payload.get('_raw_output') or '').strip()
        changed_files_preview = ', '.join(changed_files[:8])
        if len(changed_files) > 8:
            changed_files_preview += ', ...'

        summary_lines = [
            _("A branch de entrega ja continha alteracoes relativamente a %s.") % base_branch,
            _("Nao foi necessario criar um novo commit para esta execucao."),
        ]
        if changed_files_preview:
            summary_lines.append(_("Ficheiros ja alterados na branch de entrega: %s") % changed_files_preview)
        if raw_summary:
            summary_lines.extend(['', raw_summary])

        return {
            'branch_name': branch_name,
            'base_branch': base_branch,
            'commit_sha': self._get_head_commit_sha(repo_path),
            'summary': '\n'.join(summary_lines).strip(),
            'pr_title': (payload.get('pr_title') or self._default_pr_title(task, branch_name, base_branch)).strip(),
            'pr_body': (payload.get('pr_body') or self._default_pr_body(task, branch_name, base_branch)).strip(),
            'commit_message': self._get_head_commit_message(repo_path),
            'raw_output': (payload.get('_raw_output') or '').strip(),
            'repo_path': repo_path,
            'skip_pr': False,
        }

    def _build_noop_result(self, task, repo_path, branch_name, base_branch, payload, noop_paths):
        preview = ', '.join(noop_paths[:8])
        if len(noop_paths) > 8:
            preview += ', ...'

        summary_lines = [
            _("O conteudo proposto pelo Codex ja correspondia ao estado atual do repositorio."),
            _("Nao foi necessario criar commit nem push porque nao existia diff efetivo."),
        ]
        if preview:
            summary_lines.append(_("Ficheiros sem diferencas face ao proposto: %s") % preview)
        raw_summary = (payload.get('summary') or '').strip()
        if raw_summary:
            summary_lines.extend(['', raw_summary])

        return {
            'branch_name': branch_name,
            'base_branch': base_branch,
            'commit_sha': self._get_head_commit_sha(repo_path),
            'summary': '\n'.join(summary_lines).strip(),
            'pr_title': (payload.get('pr_title') or self._default_pr_title(task, branch_name, base_branch)).strip(),
            'pr_body': (payload.get('pr_body') or self._default_pr_body(task, branch_name, base_branch)).strip(),
            'commit_message': self._get_head_commit_message(repo_path),
            'raw_output': (payload.get('_raw_output') or '').strip(),
            'repo_path': repo_path,
            'skip_pr': True,
        }

    def execute_task(self, task, prompt, progress_callback=None):
        execution_mode = self._get_execution_mode()
        branch_name = self.build_branch_name(task)
        base_branch = task.ai_base_branch_id.name or task.ai_repo_id.default_branch or 'main'
        effective_prompt = self._build_continuity_enriched_prompt(task, prompt)
        repo_path = ''
        cleanup_workspace = self.should_cleanup_local_workspace()
        self._report_progress(progress_callback, _("A preparar repositorio Git local."))
        try:
            repo_path = self._prepare_repository(task.ai_repo_id, branch_name, base_branch)
            if execution_mode == 'service':
                self._report_progress(progress_callback, _("Repositorio preparado. A analisar contexto e ficheiros relevantes."))
                payload = self._build_change_request_with_retry(repo_path, task, effective_prompt, progress_callback=progress_callback)
                self._report_progress(progress_callback, _("A aplicar alteracoes propostas no repositorio local."))
                self._apply_changes(repo_path, payload.get('changes') or [])
            else:
                self._report_progress(progress_callback, _("Repositorio preparado. A iniciar sessao com Codex CLI."))
                payload = self._run_codex_cli(
                    repo_path,
                    task,
                    effective_prompt,
                    branch_name,
                    base_branch,
                    progress_callback=progress_callback,
                )

            status = self._git(repo_path, 'status', '--porcelain', failure_message=_("Falha ao validar alteracoes do repositorio."))
            if not status.stdout.strip():
                if (
                    execution_mode == 'cli'
                    and payload.get('_cli_sandbox_issue')
                    and not self._is_dangerous_cli_runtime(payload.get('_cli_runtime_profile'))
                ):
                    self._report_progress(
                        progress_callback,
                        _("O sandbox do Codex bloqueou comandos locais; vou repetir sem sandbox."),
                    )
                    payload = self._run_codex_cli(
                        repo_path,
                        task,
                        effective_prompt,
                        branch_name,
                        base_branch,
                        progress_callback=progress_callback,
                        runtime_profile='dangerous',
                    )
                    status = self._git(repo_path, 'status', '--porcelain', failure_message=_("Falha ao validar alteracoes do repositorio."))

            if not status.stdout.strip():
                changed_files = self._get_branch_diff_against_base(repo_path, base_branch)
                if changed_files:
                    self._report_progress(progress_callback, _("A branch selecionada ja continha alteracoes relativamente a %s; vou reutilizar essa branch.") % base_branch)
                    return self._build_existing_branch_result(task, repo_path, branch_name, base_branch, payload, changed_files)
                noop_paths = self._get_noop_change_paths(repo_path, payload.get('changes') or [])
                if not noop_paths:
                    noop_paths = self._get_change_paths(payload.get('changes') or [])
                if noop_paths:
                    self._report_progress(progress_callback, _("Sem diff local: o conteudo proposto pelo Codex ja existe no repositorio."))
                    return self._build_noop_result(task, repo_path, branch_name, base_branch, payload, noop_paths)
                if execution_mode == 'cli':
                    self._report_progress(progress_callback, _("O Codex CLI terminou sem diff local nesta execucao."))
                    return self._build_noop_result(task, repo_path, branch_name, base_branch, payload, [])
                raise UserError(
                    _("O Codex %s terminou sem produzir alteracoes no repositorio.\nOutput bruto do Codex:\n%s")
                    % ('CLI local' if execution_mode == 'cli' else 'cloud', self._shorten_output(payload.get('_raw_output') or ''))
                )
            commit_message = (payload.get('commit_message') or self._default_commit_message(task, branch_name, base_branch)).strip()
            pr_title = (payload.get('pr_title') or self._default_pr_title(task, branch_name, base_branch)).strip()
            pr_body = (payload.get('pr_body') or self._default_pr_body(task, branch_name, base_branch)).strip()
            summary = (payload.get('summary') or payload.get('_raw_output') or '').strip()

            self._report_progress(progress_callback, _("A criar commit Git local."))
            self._git(repo_path, 'add', '-A', failure_message=_("Falha ao adicionar alteracoes ao commit."))
            self._git(repo_path, 'commit', '-m', commit_message, failure_message=_("Falha ao criar o commit Git."))
            self._report_progress(progress_callback, _("Commit criado. A fazer push para GitHub."))
            self._git(
                repo_path,
                'push',
                '--set-upstream',
                'origin',
                branch_name,
                failure_message=_("Falha ao fazer push da branch para o GitHub."),
            )
            self._report_progress(progress_callback, _("Push concluido para a branch %s.") % branch_name)
            commit_sha = self._get_head_commit_sha(repo_path)

            return {
                'branch_name': branch_name,
                'base_branch': base_branch,
                'commit_sha': commit_sha,
                'summary': summary,
                'pr_title': pr_title,
                'pr_body': pr_body,
                'commit_message': commit_message,
                'raw_output': (payload.get('_raw_output') or '').strip(),
                'repo_path': repo_path,
            }
        finally:
            if repo_path and cleanup_workspace:
                self._cleanup_repo_workspace(repo_path)
