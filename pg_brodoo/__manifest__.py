{
    'name': 'Brodoo',
    'version': '19.0.1.0.0',
    'category': 'Services/Project',
    'summary': 'Espelho factual de projectos Odoo para repositórios GitHub com suporte a agentes AI',
    'description': """
        Adds two complementary flows to Project:
        - Publish project scope snapshots from Odoo to GitHub repositories
        - Publish project status snapshots from Odoo to GitHub repositories
        - Publish project decisions snapshots from Odoo to GitHub repositories
        - Publish project risks snapshots from Odoo to GitHub repositories
        - Publish project deliveries snapshots from Odoo to GitHub repositories
        - Publish project requirements snapshots from Odoo to GitHub repositories
        - Publish project plan snapshots from Odoo to GitHub repositories
        - Publish project budget snapshots from Odoo to GitHub repositories
        - Generate technical prompts with ChatGPT
        - Execute Codex against a GitHub repository
        - Commit and push changes automatically
        - Open a Pull Request from the task
    """,
    'author': 'Parametro',
    'depends': ['project'],
    'assets': {
        'web.assets_backend': [
            'pg_brodoo/static/src/js/task_form_autorefresh.js',
            'pg_brodoo/static/src/scss/pg_brodoo.scss',
        ],
        'web.assets_web_dark': [
            'pg_brodoo/static/src/scss/pg_brodoo.dark.scss',
        ],
    },
    'data': [
        'security/ir.model.access.csv',
        'data/pg_chatter_signal_cron.xml',
        'data/pg_mirror_sync_cron.xml',
        'data/pg_scope_sync_cron.xml',
        'views/pg_ai_repository_views.xml',
        'views/pg_ai_onboarding_wizard_views.xml',
        'views/pg_project_batch_onboarding_wizard_views.xml',
        'views/pg_operational_dashboard_views.xml',
        'views/pg_project_chatter_signal_views.xml',
        'views/pg_project_scope_sync_run_views.xml',
        'views/pg_project_deliveries_sync_run_views.xml',
        'views/pg_project_budget_sync_run_views.xml',
        'views/pg_project_decisions_sync_run_views.xml',
        'views/pg_project_mirror_sync_run_views.xml',
        'views/pg_project_plan_sync_run_views.xml',
        'views/pg_project_requirements_sync_run_views.xml',
        'views/pg_project_risks_sync_run_views.xml',
        'views/pg_project_status_sync_run_views.xml',
        'views/project_project_views.xml',
        'views/project_task_scope_views.xml',
        'views/project_task_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'OPL-1',
}
