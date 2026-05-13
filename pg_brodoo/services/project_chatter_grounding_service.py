from dateutil.relativedelta import relativedelta

from odoo import fields


class ProjectChatterGroundingService:
    def __init__(self, env):
        self.env = env

    def _active_states(self, include_candidates=False):
        return ['validated', 'candidate'] if include_candidates else ['validated']

    def _recent_domain(self, days=False):
        if not days:
            return []
        return [('occurred_at', '>=', fields.Datetime.now() - relativedelta(days=days))]

    def _deduplicate_signals(self, signals):
        deduplicated = self.env['pg.project.chatter.signal']
        seen = set()
        for signal in signals:
            key = (
                signal.signal_type,
                signal.content_hash or signal.summary,
            )
            if key in seen:
                continue
            seen.add(key)
            deduplicated |= signal
        return deduplicated

    def _serialize_signals(self, signals):
        return [
            {
                'id': signal.id,
                'signal_type': signal.signal_type,
                'signal_state': signal.signal_state,
                'summary': signal.summary,
                'evidence_excerpt': signal.evidence_excerpt,
                'confidence': signal.confidence,
                'occurred_at': signal.occurred_at,
                'visibility': signal.visibility,
                'source_model': signal.source_model,
                'source_record_id': signal.source_record_id,
            }
            for signal in signals
        ]

    def build_project_grounding(self, project, include_candidates=False, days=False):
        signals = self.env['pg.project.chatter.signal'].sudo().search(
            [
                ('project_id', '=', project.id),
                ('signal_state', 'in', self._active_states(include_candidates=include_candidates)),
            ]
            + self._recent_domain(days=days),
            order='occurred_at desc, id desc',
        )
        return self._group_signals(signals)

    def build_project_only_grounding(self, project, include_candidates=False, days=False):
        signals = self.env['pg.project.chatter.signal'].sudo().search(
            [
                ('project_id', '=', project.id),
                ('task_id', '=', False),
                ('signal_state', 'in', self._active_states(include_candidates=include_candidates)),
            ]
            + self._recent_domain(days=days),
            order='occurred_at desc, id desc',
        )
        return self._group_signals(signals)

    def build_task_grounding(self, task, include_project=False, include_candidates=False, days=False):
        domain = [
            ('task_id', '=', task.id),
            ('signal_state', 'in', self._active_states(include_candidates=include_candidates)),
        ] + self._recent_domain(days=days)
        signals = self.env['pg.project.chatter.signal'].sudo().search(domain, order='occurred_at desc, id desc')
        payload = self._group_signals(signals)
        if include_project and task.project_id:
            payload['project_signals'] = self.build_project_only_grounding(
                task.project_id,
                include_candidates=include_candidates,
                days=days,
            )
        return payload

    def _group_signals(self, signals):
        signals = self._deduplicate_signals(signals)
        grouped = {
            'all_signals': self._serialize_signals(signals),
            'blockers': [],
            'risks': [],
            'decisions': [],
            'approvals': [],
            'scope_changes': [],
            'next_steps': [],
            'dependencies': [],
        }
        mapping = {
            'blocker': 'blockers',
            'risk': 'risks',
            'decision': 'decisions',
            'approval': 'approvals',
            'scope_change': 'scope_changes',
            'next_step': 'next_steps',
            'dependency': 'dependencies',
        }
        for signal in signals:
            grouped[mapping[signal.signal_type]].append(
                {
                    'summary': signal.summary,
                    'confidence': signal.confidence,
                    'occurred_at': signal.occurred_at,
                    'visibility': signal.visibility,
                }
            )
        return grouped
