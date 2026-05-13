import base64
import logging
import os
from collections import Counter
from urllib.parse import quote

import requests

from odoo import _
from odoo.exceptions import UserError
from odoo.fields import Datetime

_logger = logging.getLogger(__name__)


REPOSITORY_SORT_OPTIONS = {'updated', 'full_name', 'created', 'pushed'}


class GitHubService:
    API_URL = 'https://api.github.com'
    DEFAULT_TIMEOUT = 60
    API_VERSION = '2026-03-10'
    PAGE_SIZE = 100
    DEFAULT_REPOSITORY_SORT = 'updated'
    DEFAULT_BRANCH = 'main'

    def __init__(self, env):
        self.env = env
        self.params = env['ir.config_parameter'].sudo()

    def _get_param(self, key, default=None):
        return self.params.get_param(key, default)

    def _get_timeout(self):
        value = self._get_param('pg_github_timeout', self.DEFAULT_TIMEOUT)
        try:
            return max(int(value), 1)
        except (TypeError, ValueError):
            return self.DEFAULT_TIMEOUT

    def _get_repository_sort(self):
        repository_sort = (
            self._get_param('pg_github_repository_sort', self.DEFAULT_REPOSITORY_SORT)
            or self.DEFAULT_REPOSITORY_SORT
        ).strip()
        if repository_sort not in REPOSITORY_SORT_OPTIONS:
            return self.DEFAULT_REPOSITORY_SORT
        return repository_sort

    def _get_default_branch(self):
        return (self._get_param('pg_github_default_branch', self.DEFAULT_BRANCH) or self.DEFAULT_BRANCH).strip()

    def should_autosync_on_search(self):
        value = self._get_param('pg_github_autosync_on_search', 'True')
        return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}

    def should_push_directly_to_selected_branch(self):
        value = self._get_param('pg_ai_push_direct_to_selected_branch', 'True')
        return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}

    def _get_environment_token(self):
        for key in ('PG_GITHUB_TOKEN', 'GITHUB_TOKEN', 'GH_TOKEN'):
            value = (os.environ.get(key) or '').strip()
            if value:
                return value
        return ''

    def _get_resolved_token(self, token=None):
        resolved_token = (
            (token or '').strip()
            or (self._get_param('pg_github_token') or '').strip()
            or self._get_environment_token()
        )
        if not resolved_token:
            raise UserError(_("Configuracao em falta: GitHub Token."))
        return resolved_token

    def _build_headers(self, token=None):
        resolved_token = self._get_resolved_token(token)
        return {
            'Accept': 'application/vnd.github+json',
            'Authorization': f'Bearer {resolved_token}',
            'X-GitHub-Api-Version': self.API_VERSION,
        }

    def _request(self, method, endpoint, token=None, allow_not_found=False, **kwargs):
        try:
            response = requests.request(
                method,
                f'{self.API_URL}{endpoint}',
                headers=self._build_headers(token=token),
                timeout=self._get_timeout(),
                **kwargs,
            )
            if response.status_code == 404 and allow_not_found:
                return False
            if response.status_code >= 400:
                details = response.text
                try:
                    details = response.json().get('message') or details
                except ValueError:
                    pass
                raise UserError(_("GitHub API devolveu erro em %s: %s") % (endpoint, details))
            if response.content:
                return response.json()
            return {}
        except requests.exceptions.RequestException as exc:
            _logger.exception("GitHub request failed: %s %s", method, endpoint)
            raise UserError(_("Falha na comunicacao com GitHub: %s") % exc) from exc

    def _paginate(self, endpoint, token=None, params=None):
        current_page = 1
        records = []
        params = dict(params or {})
        while True:
            payload = self._request(
                'GET',
                endpoint,
                token=token,
                params={**params, 'per_page': self.PAGE_SIZE, 'page': current_page},
            )
            if not payload:
                break
            records.extend(payload)
            if len(payload) < self.PAGE_SIZE:
                break
            current_page += 1
        return records

    def discover_configuration(self, token=None):
        resolved_token = self._get_resolved_token(token)
        user_data = self._request('GET', '/user', token=resolved_token)
        repos = self._paginate('/user/repos', token=resolved_token, params={'sort': self._get_repository_sort()})
        branch_counter = Counter(
            repo.get('default_branch')
            for repo in repos
            if (repo.get('default_branch') or '').strip()
        )
        suggested_default_branch = ''
        if branch_counter:
            suggested_default_branch = branch_counter.most_common(1)[0][0]

        return {
            'token': resolved_token,
            'login': (user_data.get('login') or '').strip(),
            'name': (user_data.get('name') or '').strip(),
            'default_owner': (user_data.get('login') or '').strip(),
            'suggested_default_branch': suggested_default_branch,
            'public_repos': user_data.get('public_repos') or 0,
            'private_repos': user_data.get('total_private_repos') or 0,
        }

    def list_user_repositories(self, token=None):
        return self._paginate('/user/repos', token=token, params={'sort': self._get_repository_sort()})

    def list_repository_branches(self, repository, token=None):
        return self._paginate(f'/repos/{repository.github_owner}/{repository.github_repo}/branches', token=token)

    def sync_user_repositories(self, token=None):
        repositories = self.list_user_repositories(token=token)
        repository_model = self.env['pg.ai.repository'].sudo()
        synced_records = repository_model.browse()
        existing_by_github_id = {
            record.github_id: record
            for record in repository_model.search([('github_id', '!=', False)])
        }
        existing_by_full_name = {
            record.full_name: record
            for record in repository_model.search([('full_name', '!=', False)])
        }
        sync_time = Datetime.now()

        for repo_data in repositories:
            owner_data = repo_data.get('owner') or {}
            full_name = (repo_data.get('full_name') or '').strip()
            values = {
                'name': (repo_data.get('name') or '').strip(),
                'github_id': repo_data.get('id'),
                'full_name': full_name,
                'github_owner': (owner_data.get('login') or '').strip(),
                'github_repo': (repo_data.get('name') or '').strip(),
                'default_branch': (repo_data.get('default_branch') or '').strip() or self._get_default_branch(),
                'visibility': (repo_data.get('visibility') or 'private').strip(),
                'is_private': bool(repo_data.get('private')),
                'last_sync_at': sync_time,
                'active': True,
            }
            record = existing_by_github_id.get(values['github_id']) or existing_by_full_name.get(full_name)
            if record:
                record.write(values)
            else:
                record = repository_model.create(values)
            synced_records |= record

        return synced_records.sorted(key=lambda repo: (repo.github_owner.lower(), repo.github_repo.lower()))

    def sync_repository_branches(self, repository, token=None):
        branch_model = self.env['pg.ai.repository.branch'].sudo()
        branches = self.list_repository_branches(repository, token=token)
        existing = {branch.name: branch for branch in repository.branch_ids}
        current_names = set()
        sync_time = Datetime.now()
        synced_branches = branch_model.browse()

        for branch_data in branches:
            branch_name = (branch_data.get('name') or '').strip()
            if not branch_name:
                continue
            current_names.add(branch_name)
            values = {
                'repository_id': repository.id,
                'name': branch_name,
                'is_default': branch_name == repository.default_branch,
                'last_sync_at': sync_time,
            }
            branch_record = existing.get(branch_name)
            if branch_record:
                branch_record.write(values)
            else:
                branch_record = branch_model.create(values)
            synced_branches |= branch_record

        stale_branches = repository.branch_ids.filtered(lambda branch: branch.name not in current_names)
        if stale_branches:
            stale_branches.unlink()

        if repository.default_branch and not synced_branches.filtered(lambda branch: branch.name == repository.default_branch):
            synced_branches |= branch_model.create(
                {
                    'repository_id': repository.id,
                    'name': repository.default_branch,
                    'is_default': True,
                    'last_sync_at': sync_time,
                }
            )

        return synced_branches.sorted(key=lambda branch: (not branch.is_default, branch.name.lower()))

    def get_repository_file(self, repository, path, branch=None, token=None):
        owner, repo, resolved_branch = self._get_repository_coordinates(repository, base_branch=branch)
        quoted_path = quote((path or '').lstrip('/'), safe='')
        return self._request(
            'GET',
            f'/repos/{owner}/{repo}/contents/{quoted_path}',
            token=token,
            allow_not_found=True,
            params={'ref': resolved_branch},
        )

    def get_repository_file_text(self, repository, path, branch=None, token=None):
        file_data = self.get_repository_file(repository, path, branch=branch, token=token)
        if not file_data:
            return ''
        if (file_data.get('type') or '').strip() != 'file':
            return ''

        content = file_data.get('content') or ''
        encoding = (file_data.get('encoding') or 'base64').strip().lower()
        if not content:
            return ''
        if encoding == 'base64':
            normalized_content = ''.join(str(content).splitlines())
            return base64.b64decode(normalized_content).decode('utf-8')
        return str(content)

    def upsert_repository_file(self, repository, path, content, message, branch=None, token=None):
        owner, repo, resolved_branch = self._get_repository_coordinates(repository, base_branch=branch)
        existing_file = self.get_repository_file(repository, path, branch=resolved_branch, token=token)
        payload = {
            'message': message,
            'content': base64.b64encode((content or '').encode('utf-8')).decode('ascii'),
            'branch': resolved_branch,
        }
        if existing_file and existing_file.get('sha'):
            payload['sha'] = existing_file['sha']

        quoted_path = quote((path or '').lstrip('/'), safe='')
        return self._request('PUT', f'/repos/{owner}/{repo}/contents/{quoted_path}', token=token, json=payload)

    def _get_repository_coordinates(self, repository, base_branch=None):
        owner = (repository.github_owner or self._get_param('pg_github_default_owner') or '').strip()
        repo = (repository.github_repo or '').strip()
        resolved_base_branch = (base_branch or repository.default_branch or self._get_default_branch()).strip()
        if not owner or not repo:
            raise UserError(_("O repositorio AI tem de ter owner e repository GitHub configurados."))
        return owner, repo, resolved_base_branch

    def should_create_pull_request(self):
        if self.should_push_directly_to_selected_branch():
            return False
        value = self._get_param('pg_github_create_pr_by_default', 'True')
        return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}

    def get_branch_sha(self, repository, branch_name):
        owner, repo, _base_branch = self._get_repository_coordinates(repository)
        ref_data = self._request('GET', f'/repos/{owner}/{repo}/git/ref/heads/{branch_name}')
        return ref_data.get('object', {}).get('sha')

    def create_branch(self, repository, branch_name, base_branch=None):
        owner, repo, default_branch = self._get_repository_coordinates(repository, base_branch=base_branch)
        source_branch = (base_branch or default_branch).strip()
        sha = self.get_branch_sha(repository, source_branch)
        if not sha:
            raise UserError(_("Nao foi possivel obter o SHA da branch base %s.") % source_branch)
        payload = {'ref': f'refs/heads/{branch_name}', 'sha': sha}
        return self._request('POST', f'/repos/{owner}/{repo}/git/refs', json=payload)

    def create_commit(self, repository, message, tree_sha, parent_shas):
        owner, repo, _base_branch = self._get_repository_coordinates(repository)
        payload = {
            'message': message,
            'tree': tree_sha,
            'parents': parent_shas,
        }
        return self._request('POST', f'/repos/{owner}/{repo}/git/commits', json=payload)

    def find_open_pull_request(self, repository, branch_name):
        owner, repo, _base_branch = self._get_repository_coordinates(repository)
        payload = self._request(
            'GET',
            f'/repos/{owner}/{repo}/pulls?state=open&head={owner}:{branch_name}',
        )
        return payload[0] if payload else False

    def create_pull_request(self, repository, branch_name, title, body, base_branch=None):
        owner, repo, resolved_base_branch = self._get_repository_coordinates(repository, base_branch=base_branch)
        payload = {
            'title': title,
            'head': branch_name,
            'base': resolved_base_branch,
            'body': body,
            'maintainer_can_modify': True,
        }

        try:
            return self._request('POST', f'/repos/{owner}/{repo}/pulls', json=payload)
        except UserError as exc:
            if 'A pull request already exists' not in str(exc):
                raise
            existing_pr = self.find_open_pull_request(repository, branch_name)
            if existing_pr:
                return existing_pr
            raise
