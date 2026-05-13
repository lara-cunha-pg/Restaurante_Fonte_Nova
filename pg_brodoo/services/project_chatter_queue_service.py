from odoo import fields

from .project_chatter_filter_service import ProjectChatterFilterService
from .project_chatter_ingestion_service import ProjectChatterIngestionService
from .project_chatter_llm_service import ProjectChatterLlmService
from .project_chatter_signal_service import ProjectChatterSignalService
from .project_chatter_validation_service import ProjectChatterValidationService


class ProjectChatterQueueService:
    def __init__(self, env):
        self.env = env
        self.filter_service = ProjectChatterFilterService(env)
        self.ingestion_service = ProjectChatterIngestionService(env)
        self.llm_service = ProjectChatterLlmService(env)
        self.signal_service = ProjectChatterSignalService(env)
        self.validation_service = ProjectChatterValidationService(env)

    def mark_dirty_from_refs(self, refs):
        project_ids = set()
        task_ids = set()
        for model_name, record_id in refs:
            if not record_id:
                continue
            if model_name == 'project.project':
                project_ids.add(record_id)
            elif model_name == 'project.task':
                task_ids.add(record_id)

        project_model = self.env['project.project'].sudo()
        task_model = self.env['project.task'].sudo()
        tasks = task_model.browse(list(task_ids)).exists()
        projects = project_model.browse(list(project_ids)).exists() | tasks.mapped('project_id')

        if tasks:
            tasks.with_context(
                pg_skip_scope_sync_enqueue=True,
                pg_skip_scope_enrichment_reset=True,
                pg_skip_ai_consultive_prefill_reset=True,
            ).write({'pg_chatter_signals_dirty': True})
        if projects:
            projects.with_context(
                pg_skip_scope_sync_enqueue=True,
                pg_skip_status_sync_touch=True,
            ).write({'pg_chatter_signals_dirty': True})

    def refresh_project(self, project):
        project = project.sudo()
        now = fields.Datetime.now()
        project_messages = self.ingestion_service.collect_project_messages(project)
        self._sync_signals(
            source_model='project.project',
            source_record_id=project.id,
            project=project,
            task=False,
            filtered_messages=self.filter_service.filter_messages(project_messages),
        )

        tasks = self.env['project.task'].sudo().with_context(active_test=False).search([('project_id', '=', project.id)])
        for task in tasks:
            task_messages = self.ingestion_service.collect_task_messages(task)
            self._sync_signals(
                source_model='project.task',
                source_record_id=task.id,
                project=project,
                task=task,
                filtered_messages=self.filter_service.filter_messages(task_messages),
            )

        if tasks:
            tasks.with_context(
                pg_skip_scope_sync_enqueue=True,
                pg_skip_scope_enrichment_reset=True,
                pg_skip_ai_consultive_prefill_reset=True,
            ).write(
                {
                    'pg_chatter_signals_dirty': False,
                    'pg_chatter_last_scanned_at': now,
                }
            )
        project.with_context(
            pg_skip_scope_sync_enqueue=True,
            pg_skip_status_sync_touch=True,
        ).write(
            {
                'pg_chatter_signals_dirty': False,
                'pg_chatter_last_scanned_at': now,
            }
        )
        return True

    def refresh_task(self, task):
        task = task.sudo()
        task_messages = self.ingestion_service.collect_task_messages(task)
        self._sync_signals(
            source_model='project.task',
            source_record_id=task.id,
            project=task.project_id.sudo() if task.project_id else False,
            task=task,
            filtered_messages=self.filter_service.filter_messages(task_messages),
        )
        task.with_context(
            pg_skip_scope_sync_enqueue=True,
            pg_skip_scope_enrichment_reset=True,
            pg_skip_ai_consultive_prefill_reset=True,
        ).write(
            {
                'pg_chatter_signals_dirty': False,
                'pg_chatter_last_scanned_at': fields.Datetime.now(),
            }
        )
        return True

    def process_pending(self, limit=25):
        projects = self.env['project.project'].sudo().search([('pg_chatter_signals_dirty', '=', True)], limit=limit)
        for project in projects:
            self.refresh_project(project)

        remaining = max(limit - len(projects), 0)
        if not remaining:
            return len(projects)

        tasks = self.env['project.task'].sudo().search(
            [('pg_chatter_signals_dirty', '=', True)],
            limit=remaining,
        )
        for task in tasks:
            self.refresh_task(task)
        return len(projects) + len(tasks)

    def _sync_signals(self, source_model, source_record_id, project, task, filtered_messages):
        signal_model = self.env['pg.project.chatter.signal'].sudo()
        existing_signals = signal_model.search(
            [
                ('source_model', '=', source_model),
                ('source_record_id', '=', source_record_id),
            ]
        )
        existing_by_key = {
            (signal.source_message_id, signal.signal_type, signal.content_hash): signal
            for signal in existing_signals
        }
        latest_keys = set()
        seen_content_pairs = set()

        for filtered_message in filtered_messages:
            candidates = list(self.signal_service.build_signal_candidates(filtered_message))
            if self.llm_service.should_attempt(filtered_message, candidates):
                candidates.extend(self.llm_service.classify_ambiguous_message(filtered_message))
            for candidate in candidates:
                key = (
                    filtered_message['message_id'],
                    candidate['signal_type'],
                    candidate['content_hash'],
                )
                latest_keys.add(key)
                state_values = self.validation_service.validate_signal(
                    candidate,
                    source_text=filtered_message.get('normalized_text') or '',
                )
                values = {
                    'message_id': filtered_message['message_id'],
                    'source_message_id': filtered_message['message_id'],
                    'source_model': source_model,
                    'source_record_id': source_record_id,
                    'project_id': project.id if project else False,
                    'task_id': task.id if task else False,
                    'signal_type': candidate['signal_type'],
                    'summary': candidate['summary'],
                    'evidence_excerpt': candidate['evidence_excerpt'],
                    'confidence': candidate['confidence'],
                    'author_id': candidate['author_id'],
                    'occurred_at': candidate['occurred_at'],
                    'visibility': candidate['visibility'],
                    'engine': candidate['engine'],
                    'content_hash': candidate['content_hash'],
                    'signal_state': state_values['signal_state'],
                    'validation_feedback': state_values['validation_feedback'],
                }
                duplicate_key = (candidate['signal_type'], candidate['content_hash'])
                if duplicate_key in seen_content_pairs:
                    values.update(
                        {
                            'signal_state': 'stale',
                            'validation_feedback': 'Stale duplicate excluded from the latest grounding refresh.',
                        }
                    )
                else:
                    seen_content_pairs.add(duplicate_key)

                signal = existing_by_key.get(key)
                if signal:
                    signal.write(values)
                else:
                    signal_model.create(values)

        stale_signals = existing_signals.filtered(
            lambda signal: (signal.source_message_id, signal.signal_type, signal.content_hash) not in latest_keys
        )
        if stale_signals:
            stale_signals.write(
                {
                    'signal_state': 'stale',
                    'validation_feedback': 'Stale because the source message was removed or no longer produces this signal.',
                }
            )
