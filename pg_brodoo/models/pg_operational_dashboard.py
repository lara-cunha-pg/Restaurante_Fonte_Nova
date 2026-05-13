from odoo import _, fields, models


class PgOperationalDashboard(models.TransientModel):
    _name = 'pg.operational.dashboard'
    _description = 'Dashboard Brodoo'
    _rec_name = 'name'

    name = fields.Char(
        string='Name',
        default=lambda self: _('Dashboard Brodoo'),
        readonly=True,
    )

    scope_attention_project_count = fields.Integer(
        string='Scope Attention Project Count',
        compute='_compute_dashboard_metrics',
    )
    status_attention_project_count = fields.Integer(
        string='Status Attention Project Count',
        compute='_compute_dashboard_metrics',
    )
    blocked_ai_task_count = fields.Integer(
        string='Blocked AI Task Count',
        compute='_compute_dashboard_metrics',
    )
    ready_ai_task_count = fields.Integer(
        string='AI-Ready Task Count',
        compute='_compute_dashboard_metrics',
    )
    failed_scope_run_count = fields.Integer(
        string='Failed Scope Sync Run Count',
        compute='_compute_dashboard_metrics',
    )
    failed_status_run_count = fields.Integer(
        string='Failed Status Sync Run Count',
        compute='_compute_dashboard_metrics',
    )
    brownfield_missing_scope_summary_count = fields.Integer(
        string='Brownfield Missing Scope Summary Count',
        compute='_compute_dashboard_metrics',
    )
    brownfield_missing_acceptance_criteria_count = fields.Integer(
        string='Brownfield Missing Acceptance Criteria Count',
        compute='_compute_dashboard_metrics',
    )
    brownfield_missing_scope_kind_count = fields.Integer(
        string='Brownfield Missing Scope Kind Count',
        compute='_compute_dashboard_metrics',
    )
    brownfield_needs_review_task_count = fields.Integer(
        string='Brownfield Needs Review Task Count',
        compute='_compute_dashboard_metrics',
    )
    chatter_dirty_project_count = fields.Integer(
        string='Projects With Dirty Chatter Signals',
        compute='_compute_dashboard_metrics',
    )
    chatter_dirty_task_count = fields.Integer(
        string='Tasks With Dirty Chatter Signals',
        compute='_compute_dashboard_metrics',
    )
    chatter_validated_signal_count = fields.Integer(
        string='Validated Chatter Signal Count',
        compute='_compute_dashboard_metrics',
    )
    chatter_candidate_signal_count = fields.Integer(
        string='Candidate Chatter Signal Count',
        compute='_compute_dashboard_metrics',
    )
    chatter_stale_signal_count = fields.Integer(
        string='Stale Chatter Signal Count',
        compute='_compute_dashboard_metrics',
    )
    chatter_rejected_signal_count = fields.Integer(
        string='Rejected Chatter Signal Count',
        compute='_compute_dashboard_metrics',
    )

    scope_attention_project_ids = fields.Many2many(
        'project.project',
        string='Projects With Scope Attention',
        compute='_compute_dashboard_lists',
    )
    status_attention_project_ids = fields.Many2many(
        'project.project',
        string='Projects With Status Attention',
        compute='_compute_dashboard_lists',
    )
    blocked_ai_task_ids = fields.Many2many(
        'project.task',
        string='Blocked AI Tasks',
        compute='_compute_dashboard_lists',
    )
    ready_ai_task_ids = fields.Many2many(
        'project.task',
        string='AI-Ready Tasks',
        compute='_compute_dashboard_lists',
    )
    failed_scope_run_ids = fields.Many2many(
        'pg.project.scope.sync.run',
        string='Failed Scope Sync Runs',
        compute='_compute_dashboard_lists',
    )
    failed_status_run_ids = fields.Many2many(
        'pg.project.status.sync.run',
        string='Failed Status Sync Runs',
        compute='_compute_dashboard_lists',
    )
    brownfield_missing_scope_summary_task_ids = fields.Many2many(
        'project.task',
        string='Approved Scope Tasks Missing Scope Summary',
        compute='_compute_dashboard_lists',
    )
    brownfield_missing_acceptance_criteria_task_ids = fields.Many2many(
        'project.task',
        string='Approved Scope Tasks Missing Acceptance Criteria',
        compute='_compute_dashboard_lists',
    )
    brownfield_missing_scope_kind_task_ids = fields.Many2many(
        'project.task',
        string='Approved Scope Tasks Missing Scope Kind',
        compute='_compute_dashboard_lists',
    )
    brownfield_needs_review_task_ids = fields.Many2many(
        'project.task',
        string='Scope Enrichment Tasks Needing Review',
        compute='_compute_dashboard_lists',
    )
    chatter_dirty_project_ids = fields.Many2many(
        'project.project',
        string='Projects With Chatter Refresh Pending',
        compute='_compute_dashboard_lists',
    )
    chatter_dirty_task_ids = fields.Many2many(
        'project.task',
        string='Tasks With Chatter Refresh Pending',
        compute='_compute_dashboard_lists',
    )
    chatter_validated_signal_ids = fields.Many2many(
        'pg.project.chatter.signal',
        string='Validated Chatter Signals',
        compute='_compute_dashboard_lists',
    )
    chatter_candidate_signal_ids = fields.Many2many(
        'pg.project.chatter.signal',
        string='Candidate Chatter Signals',
        compute='_compute_dashboard_lists',
    )
    chatter_stale_signal_ids = fields.Many2many(
        'pg.project.chatter.signal',
        string='Stale Chatter Signals',
        compute='_compute_dashboard_lists',
    )
    chatter_rejected_signal_ids = fields.Many2many(
        'pg.project.chatter.signal',
        string='Rejected Chatter Signals',
        compute='_compute_dashboard_lists',
    )

    def _get_scope_attention_project_domain(self):
        return [
            ('pg_scope_sync_enabled', '=', True),
            ('pg_scope_sync_last_status', 'in', ['never', 'queued', 'running', 'error']),
        ]

    def _get_status_attention_project_domain(self):
        return [
            ('pg_status_sync_enabled', '=', True),
            '|',
            ('pg_status_sync_needs_publish', '=', True),
            ('pg_status_sync_last_status', 'in', ['never', 'queued', 'running', 'error']),
        ]

    def _get_task_ai_signal_domain(self):
        return [
            ('active', '=', True),
            '|',
            '|',
            '|',
            '|',
            ('pg_ai_recommendation_class', '!=', False),
            ('pg_ai_consultive_gate_notes', '!=', False),
            ('ai_repo_id', '!=', False),
            ('ai_prompt_draft', '!=', False),
            ('ai_prompt_final', '!=', False),
        ]

    def _get_blocked_ai_task_domain(self):
        return self._get_task_ai_signal_domain() + [
            ('pg_ai_consultive_gate_state', '!=', 'ready'),
        ]

    def _get_ready_ai_task_domain(self):
        return self._get_task_ai_signal_domain() + [
            ('pg_ai_consultive_gate_state', '=', 'ready'),
        ]

    def _get_failed_scope_run_domain(self):
        return [('status', '=', 'error')]

    def _get_failed_status_run_domain(self):
        return [('status', '=', 'error')]

    def _get_brownfield_scope_task_domain(self):
        return [
            ('active', '=', True),
            ('pg_scope_relevant', '=', True),
            ('pg_scope_track', '=', 'approved_scope'),
            ('pg_scope_state', 'not in', ['excluded', 'dropped']),
        ]

    def _get_brownfield_missing_scope_summary_domain(self):
        return self._get_brownfield_scope_task_domain() + [
            ('pg_scope_summary', '=', False),
        ]

    def _get_brownfield_missing_acceptance_criteria_domain(self):
        return self._get_brownfield_scope_task_domain() + [
            ('pg_acceptance_criteria_text', '=', False),
        ]

    def _get_brownfield_missing_scope_kind_domain(self):
        return self._get_brownfield_scope_task_domain() + [
            ('pg_scope_kind', '=', False),
        ]

    def _get_brownfield_needs_review_domain(self):
        return self._get_brownfield_scope_task_domain() + [
            ('pg_scope_enrichment_status', '=', 'needs_review'),
        ]

    def _get_chatter_dirty_project_domain(self):
        return [('pg_chatter_signals_dirty', '=', True)]

    def _get_chatter_dirty_task_domain(self):
        return [('pg_chatter_signals_dirty', '=', True)]

    def _get_chatter_signal_domain(self, signal_state=False):
        domain = []
        if signal_state:
            domain.append(('signal_state', '=', signal_state))
        return domain

    def _search_record_ids(self, model_name, domain):
        return self.env[model_name].search(domain).ids

    def _get_record_action(self, action_xmlid, name, model_name, domain, list_view_xmlid, search_view_xmlid):
        action = self.env.ref(action_xmlid).read()[0]
        list_view = self.env.ref(list_view_xmlid)
        search_view = self.env.ref(search_view_xmlid)
        action.update(
            {
                'name': name,
                'domain': [('id', 'in', self._search_record_ids(model_name, domain))],
                'views': [(list_view.id, 'list'), (False, 'form')],
                'search_view_id': search_view.id,
                'context': {},
            }
        )
        return action

    def _get_projects_action(self, action_xmlid, name, domain):
        return self._get_record_action(
            action_xmlid,
            name,
            'project.project',
            domain,
            'pg_brodoo.view_pg_operational_dashboard_project_list',
            'pg_brodoo.view_pg_operational_dashboard_project_search',
        )

    def _get_tasks_action(self, action_xmlid, name, domain):
        return self._get_record_action(
            action_xmlid,
            name,
            'project.task',
            domain,
            'pg_brodoo.view_pg_operational_dashboard_task_list',
            'pg_brodoo.view_pg_operational_dashboard_task_search',
        )

    def _get_runs_action(self, xmlid, domain):
        action = self.env.ref(xmlid).read()[0]
        action['domain'] = domain
        return action

    def _get_signals_action(self, name, domain):
        action = self.env.ref('pg_brodoo.action_pg_project_chatter_signal').read()[0]
        action['name'] = name
        action['domain'] = domain
        return action

    def action_open_scope_attention_projects(self):
        return self._get_projects_action(
            'pg_brodoo.action_pg_operational_scope_attention_projects',
            'PG Projects With Scope Attention',
            self._get_scope_attention_project_domain(),
        )

    def action_open_status_attention_projects(self):
        return self._get_projects_action(
            'pg_brodoo.action_pg_operational_status_attention_projects',
            'PG Projects With Status Attention',
            self._get_status_attention_project_domain(),
        )

    def action_open_blocked_ai_tasks(self):
        return self._get_tasks_action(
            'pg_brodoo.action_pg_operational_blocked_ai_tasks',
            'PG Blocked AI Tasks',
            self._get_blocked_ai_task_domain(),
        )

    def action_open_ready_ai_tasks(self):
        return self._get_tasks_action(
            'pg_brodoo.action_pg_operational_ready_ai_tasks',
            'Tarefas Prontas — Brodoo',
            self._get_ready_ai_task_domain(),
        )

    def action_open_failed_scope_runs(self):
        return self._get_runs_action(
            'pg_brodoo.action_pg_project_scope_sync_run',
            self._get_failed_scope_run_domain(),
        )

    def action_open_failed_status_runs(self):
        return self._get_runs_action(
            'pg_brodoo.action_pg_project_status_sync_run',
            self._get_failed_status_run_domain(),
        )

    def action_open_brownfield_missing_scope_summary_tasks(self):
        return self._get_tasks_action(
            'pg_brodoo.action_pg_operational_blocked_ai_tasks',
            'PG Brownfield Consolidation Gaps - Missing Scope Summary',
            self._get_brownfield_missing_scope_summary_domain(),
        )

    def action_open_brownfield_missing_acceptance_criteria_tasks(self):
        return self._get_tasks_action(
            'pg_brodoo.action_pg_operational_blocked_ai_tasks',
            'PG Brownfield Consolidation Gaps - Missing Acceptance Criteria',
            self._get_brownfield_missing_acceptance_criteria_domain(),
        )

    def action_open_brownfield_missing_scope_kind_tasks(self):
        return self._get_tasks_action(
            'pg_brodoo.action_pg_operational_blocked_ai_tasks',
            'PG Brownfield Consolidation Gaps - Missing Scope Kind',
            self._get_brownfield_missing_scope_kind_domain(),
        )

    def action_open_brownfield_needs_review_tasks(self):
        return self._get_tasks_action(
            'pg_brodoo.action_pg_operational_blocked_ai_tasks',
            'PG Brownfield Review Candidates',
            self._get_brownfield_needs_review_domain(),
        )

    def action_open_chatter_dirty_projects(self):
        return self._get_projects_action(
            'pg_brodoo.action_pg_operational_scope_attention_projects',
            'PG Projects With Chatter Refresh Pending',
            self._get_chatter_dirty_project_domain(),
        )

    def action_open_chatter_dirty_tasks(self):
        return self._get_tasks_action(
            'pg_brodoo.action_pg_operational_blocked_ai_tasks',
            'PG Tasks With Chatter Refresh Pending',
            self._get_chatter_dirty_task_domain(),
        )

    def action_open_validated_chatter_signals(self):
        return self._get_signals_action(
            'PG Validated Chatter Signals',
            self._get_chatter_signal_domain('validated'),
        )

    def action_open_candidate_chatter_signals(self):
        return self._get_signals_action(
            'PG Candidate Chatter Signals',
            self._get_chatter_signal_domain('candidate'),
        )

    def action_open_stale_chatter_signals(self):
        return self._get_signals_action(
            'PG Stale Chatter Signals',
            self._get_chatter_signal_domain('stale'),
        )

    def action_open_rejected_chatter_signals(self):
        return self._get_signals_action(
            'PG Rejected Chatter Signals',
            self._get_chatter_signal_domain('rejected'),
        )

    def _compute_dashboard_metrics(self):
        project_model = self.env['project.project']
        task_model = self.env['project.task']
        signal_model = self.env['pg.project.chatter.signal']
        scope_run_model = self.env['pg.project.scope.sync.run']
        status_run_model = self.env['pg.project.status.sync.run']

        scope_project_count = project_model.search_count(self._get_scope_attention_project_domain())
        status_project_count = project_model.search_count(self._get_status_attention_project_domain())
        blocked_task_count = task_model.search_count(self._get_blocked_ai_task_domain())
        ready_task_count = task_model.search_count(self._get_ready_ai_task_domain())
        failed_scope_run_count = scope_run_model.search_count(self._get_failed_scope_run_domain())
        failed_status_run_count = status_run_model.search_count(self._get_failed_status_run_domain())
        brownfield_missing_scope_summary_count = task_model.search_count(
            self._get_brownfield_missing_scope_summary_domain()
        )
        brownfield_missing_acceptance_criteria_count = task_model.search_count(
            self._get_brownfield_missing_acceptance_criteria_domain()
        )
        brownfield_missing_scope_kind_count = task_model.search_count(
            self._get_brownfield_missing_scope_kind_domain()
        )
        brownfield_needs_review_count = task_model.search_count(
            self._get_brownfield_needs_review_domain()
        )
        chatter_dirty_project_count = project_model.search_count(self._get_chatter_dirty_project_domain())
        chatter_dirty_task_count = task_model.search_count(self._get_chatter_dirty_task_domain())
        chatter_validated_signal_count = signal_model.search_count(self._get_chatter_signal_domain('validated'))
        chatter_candidate_signal_count = signal_model.search_count(self._get_chatter_signal_domain('candidate'))
        chatter_stale_signal_count = signal_model.search_count(self._get_chatter_signal_domain('stale'))
        chatter_rejected_signal_count = signal_model.search_count(self._get_chatter_signal_domain('rejected'))

        for dashboard in self:
            dashboard.scope_attention_project_count = scope_project_count
            dashboard.status_attention_project_count = status_project_count
            dashboard.blocked_ai_task_count = blocked_task_count
            dashboard.ready_ai_task_count = ready_task_count
            dashboard.failed_scope_run_count = failed_scope_run_count
            dashboard.failed_status_run_count = failed_status_run_count
            dashboard.brownfield_missing_scope_summary_count = brownfield_missing_scope_summary_count
            dashboard.brownfield_missing_acceptance_criteria_count = brownfield_missing_acceptance_criteria_count
            dashboard.brownfield_missing_scope_kind_count = brownfield_missing_scope_kind_count
            dashboard.brownfield_needs_review_task_count = brownfield_needs_review_count
            dashboard.chatter_dirty_project_count = chatter_dirty_project_count
            dashboard.chatter_dirty_task_count = chatter_dirty_task_count
            dashboard.chatter_validated_signal_count = chatter_validated_signal_count
            dashboard.chatter_candidate_signal_count = chatter_candidate_signal_count
            dashboard.chatter_stale_signal_count = chatter_stale_signal_count
            dashboard.chatter_rejected_signal_count = chatter_rejected_signal_count

    def _compute_dashboard_lists(self):
        project_model = self.env['project.project']
        task_model = self.env['project.task']
        signal_model = self.env['pg.project.chatter.signal']
        scope_run_model = self.env['pg.project.scope.sync.run']
        status_run_model = self.env['pg.project.status.sync.run']

        scope_projects = project_model.search(self._get_scope_attention_project_domain(), limit=20)
        status_projects = project_model.search(self._get_status_attention_project_domain(), limit=20)
        blocked_tasks = task_model.search(self._get_blocked_ai_task_domain(), limit=20)
        ready_tasks = task_model.search(self._get_ready_ai_task_domain(), limit=20)
        failed_scope_runs = scope_run_model.search(self._get_failed_scope_run_domain(), limit=20)
        failed_status_runs = status_run_model.search(self._get_failed_status_run_domain(), limit=20)
        brownfield_missing_scope_summary_tasks = task_model.search(
            self._get_brownfield_missing_scope_summary_domain(),
            limit=20,
        )
        brownfield_missing_acceptance_criteria_tasks = task_model.search(
            self._get_brownfield_missing_acceptance_criteria_domain(),
            limit=20,
        )
        brownfield_missing_scope_kind_tasks = task_model.search(
            self._get_brownfield_missing_scope_kind_domain(),
            limit=20,
        )
        brownfield_needs_review_tasks = task_model.search(
            self._get_brownfield_needs_review_domain(),
            limit=20,
        )
        chatter_dirty_projects = project_model.search(self._get_chatter_dirty_project_domain(), limit=20)
        chatter_dirty_tasks = task_model.search(self._get_chatter_dirty_task_domain(), limit=20)
        chatter_validated_signals = signal_model.search(self._get_chatter_signal_domain('validated'), limit=20)
        chatter_candidate_signals = signal_model.search(self._get_chatter_signal_domain('candidate'), limit=20)
        chatter_stale_signals = signal_model.search(self._get_chatter_signal_domain('stale'), limit=20)
        chatter_rejected_signals = signal_model.search(self._get_chatter_signal_domain('rejected'), limit=20)

        for dashboard in self:
            dashboard.scope_attention_project_ids = scope_projects
            dashboard.status_attention_project_ids = status_projects
            dashboard.blocked_ai_task_ids = blocked_tasks
            dashboard.ready_ai_task_ids = ready_tasks
            dashboard.failed_scope_run_ids = failed_scope_runs
            dashboard.failed_status_run_ids = failed_status_runs
            dashboard.brownfield_missing_scope_summary_task_ids = brownfield_missing_scope_summary_tasks
            dashboard.brownfield_missing_acceptance_criteria_task_ids = brownfield_missing_acceptance_criteria_tasks
            dashboard.brownfield_missing_scope_kind_task_ids = brownfield_missing_scope_kind_tasks
            dashboard.brownfield_needs_review_task_ids = brownfield_needs_review_tasks
            dashboard.chatter_dirty_project_ids = chatter_dirty_projects
            dashboard.chatter_dirty_task_ids = chatter_dirty_tasks
            dashboard.chatter_validated_signal_ids = chatter_validated_signals
            dashboard.chatter_candidate_signal_ids = chatter_candidate_signals
            dashboard.chatter_stale_signal_ids = chatter_stale_signals
            dashboard.chatter_rejected_signal_ids = chatter_rejected_signals
