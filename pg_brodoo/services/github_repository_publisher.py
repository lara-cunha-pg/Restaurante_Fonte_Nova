import json

from .github_service import GitHubService


class GitHubRepositoryPublisher:
    SCOPE_SNAPSHOT_PATH = '.pg/PG_SCOPE_SYNC.json'
    STATUS_SNAPSHOT_PATH = '.pg/PG_PROJECT_STATUS_SYNC.json'
    DECISIONS_SNAPSHOT_PATH = '.pg/PG_DECISIONS_SYNC.json'
    RISKS_SNAPSHOT_PATH = '.pg/PG_RISKS_SYNC.json'
    DELIVERIES_SNAPSHOT_PATH = '.pg/PG_DELIVERIES_SYNC.json'
    REQUIREMENTS_SNAPSHOT_PATH = '.pg/PG_REQUIREMENTS_SYNC.json'
    PROJECT_PLAN_SNAPSHOT_PATH = '.pg/PG_PROJECT_PLAN_SYNC.json'
    BUDGET_SNAPSHOT_PATH = '.pg/PG_BUDGET_SYNC.json'
    MIRROR_PROJECT_PATH = '.pg/project/project.json'
    MIRROR_PLANNING_PATH = '.pg/planning/planning.json'
    MIRROR_TASKS_PATH = '.pg/tasks/tasks.json'
    MIRROR_CHATTER_PATH = '.pg/chatter/chatter.json'
    MIRROR_ATTACHMENTS_PATH = '.pg/attachments/attachments.json'
    MIRROR_HISTORY_PATH = '.pg/history/events.jsonl'
    PROJECT_CONTEXT_PATH = 'PG_CONTEXT.md'

    def __init__(self, env):
        self.env = env
        self.github_service = GitHubService(env)

    def _publish_snapshot(self, repository, snapshot_path, branch_name, payload, commit_message):
        content = json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + '\n'
        return self.github_service.upsert_repository_file(
            repository,
            snapshot_path,
            content,
            commit_message,
            branch=branch_name,
        )

    def _publish_text_file(self, repository, snapshot_path, branch_name, content, commit_message):
        return self.github_service.upsert_repository_file(
            repository,
            snapshot_path,
            content,
            commit_message,
            branch=branch_name,
        )

    def publish_project_scope_snapshot(self, repository, branch_name, payload):
        return self._publish_snapshot(
            repository,
            self.SCOPE_SNAPSHOT_PATH,
            branch_name,
            payload,
            'chore(pg-sync): refresh project scope from odoo',
        )

    def publish_project_status_snapshot(self, repository, branch_name, payload):
        return self._publish_snapshot(
            repository,
            self.STATUS_SNAPSHOT_PATH,
            branch_name,
            payload,
            'chore(pg-sync): refresh project status from odoo',
        )

    def publish_project_decisions_snapshot(self, repository, branch_name, payload):
        return self._publish_snapshot(
            repository,
            self.DECISIONS_SNAPSHOT_PATH,
            branch_name,
            payload,
            'chore(pg-sync): refresh project decisions from odoo',
        )

    def publish_project_risks_snapshot(self, repository, branch_name, payload):
        return self._publish_snapshot(
            repository,
            self.RISKS_SNAPSHOT_PATH,
            branch_name,
            payload,
            'chore(pg-sync): refresh project risks from odoo',
        )

    def publish_project_deliveries_snapshot(self, repository, branch_name, payload):
        return self._publish_snapshot(
            repository,
            self.DELIVERIES_SNAPSHOT_PATH,
            branch_name,
            payload,
            'chore(pg-sync): refresh project deliveries from odoo',
        )

    def publish_project_requirements_snapshot(self, repository, branch_name, payload):
        return self._publish_snapshot(
            repository,
            self.REQUIREMENTS_SNAPSHOT_PATH,
            branch_name,
            payload,
            'chore(pg-sync): refresh project requirements from odoo',
        )

    def publish_project_plan_snapshot(self, repository, branch_name, payload):
        return self._publish_snapshot(
            repository,
            self.PROJECT_PLAN_SNAPSHOT_PATH,
            branch_name,
            payload,
            'chore(pg-sync): refresh project plan from odoo',
        )

    def publish_project_budget_snapshot(self, repository, branch_name, payload):
        return self._publish_snapshot(
            repository,
            self.BUDGET_SNAPSHOT_PATH,
            branch_name,
            payload,
            'chore(pg-sync): refresh project budget from odoo',
        )

    def publish_project_mirror_payload(self, repository, branch_name, payload):
        return self._publish_snapshot(
            repository,
            self.MIRROR_PROJECT_PATH,
            branch_name,
            payload,
            'chore(pg-mirror): refresh project context from odoo',
        )

    def publish_planning_mirror_payload(self, repository, branch_name, payload):
        return self._publish_snapshot(
            repository,
            self.MIRROR_PLANNING_PATH,
            branch_name,
            payload,
            'chore(pg-mirror): refresh planning context from odoo',
        )

    def publish_tasks_mirror_payload(self, repository, branch_name, payload):
        return self._publish_snapshot(
            repository,
            self.MIRROR_TASKS_PATH,
            branch_name,
            payload,
            'chore(pg-mirror): refresh task context from odoo',
        )

    def publish_chatter_mirror_payload(self, repository, branch_name, payload):
        return self._publish_snapshot(
            repository,
            self.MIRROR_CHATTER_PATH,
            branch_name,
            payload,
            'chore(pg-mirror): refresh chatter context from odoo',
        )

    def publish_attachments_mirror_payload(self, repository, branch_name, payload):
        return self._publish_snapshot(
            repository,
            self.MIRROR_ATTACHMENTS_PATH,
            branch_name,
            payload,
            'chore(pg-mirror): refresh attachment metadata from odoo',
        )

    def append_project_mirror_history_event(self, repository, branch_name, payload):
        existing_content = self.github_service.get_repository_file_text(
            repository,
            self.MIRROR_HISTORY_PATH,
            branch=branch_name,
        )
        event_line = json.dumps(payload, ensure_ascii=True, sort_keys=True) + '\n'
        if existing_content:
            content = existing_content
            if not content.endswith('\n'):
                content += '\n'
            content += event_line
        else:
            content = event_line
        return self._publish_text_file(
            repository,
            self.MIRROR_HISTORY_PATH,
            branch_name,
            content,
            'chore(pg-mirror): append project history event from odoo',
        )

    def publish_project_context(self, repository, branch_name, content):
        return self._publish_text_file(
            repository,
            self.PROJECT_CONTEXT_PATH,
            branch_name,
            content,
            'chore(pg-mirror): refresh PG_CONTEXT from mirror artifacts',
        )
