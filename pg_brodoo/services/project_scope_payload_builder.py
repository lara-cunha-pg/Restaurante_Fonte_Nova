import json
import re
import unicodedata
from copy import deepcopy

from odoo import fields

from .text_hygiene import is_low_signal_scope_summary
from .text_hygiene import is_non_factual_scope_summary
from .text_hygiene import is_technical_noise_scope_summary
from .text_hygiene import is_weak_scope_heading
from .text_hygiene import normalize_inline_text
from .text_hygiene import sanitize_scope_publication_candidate
from .text_hygiene import strip_inline_email_noise
from .text_hygiene import split_unique_text_lines


class ProjectScopePayloadBuilder:
    ACCEPTANCE_HINT_RE = re.compile(
        r'\b(?:deve|valid\w*|permit\w*|suport\w*|mostrar\w*|ger\w*|cri\w*|integr\w*|sincron\w*|'
        r'import\w*|export\w*|regist\w*|atualiz\w*|corrig\w*|test\w*|configur\w*|calcul\w*|'
        r'associ\w*|preench\w*|instal\w*|investig\w*|garant\w*|troc\w*|elimin\w*|possibilit\w*|'
        r'verific\w*|suger\w*)\b',
        re.IGNORECASE,
    )
    LINE_TYPES = (
        'acceptance_criteria',
        'users_and_roles',
        'known_exceptions',
        'approvals',
        'documents',
        'integrations',
        'reporting_needs',
        'standard_attempted_or_validated',
        'why_standard_was_insufficient',
    )
    PLACEHOLDER_TODO = '[PONTO POR VALIDAR]'

    def __init__(self, env):
        self.env = env
        self.params = env['ir.config_parameter'].sudo()

    def _get_base_url(self):
        return (self.params.get_param('web.base.url') or '').strip().rstrip('/')

    def _normalize_text(self, value, fallback=None):
        normalized = normalize_inline_text(value, fallback='', max_chars=500, drop_placeholders=True)
        if normalized:
            return normalized
        return fallback if fallback is not None else self.PLACEHOLDER_TODO

    def _normalize_optional_text(self, value, max_chars=False):
        return normalize_inline_text(value, fallback='', max_chars=max_chars, drop_placeholders=True)

    def _fold_scope_text(self, value):
        normalized = self._normalize_optional_text(value, max_chars=False)
        folded = unicodedata.normalize('NFKD', normalized)
        return ''.join(char for char in folded if not unicodedata.combining(char)).lower()

    def _split_text_lines(self, value):
        return split_unique_text_lines(
            value,
            max_items=20,
            max_line_chars=220,
            strip_email_noise=True,
        )

    def _project_lines_map(self, project):
        result = {line_type: [] for line_type in self.LINE_TYPES}
        active_lines = project.pg_scope_line_ids.filtered(lambda line: line.active).sorted(
            key=lambda line: (line.line_type or '', line.sequence, line.id)
        )
        for line_type in self.LINE_TYPES:
            values = []
            for line in active_lines.filtered(lambda record: record.line_type == line_type):
                normalized = self._normalize_optional_text(line.text, max_chars=220)
                if normalized:
                    values.append(normalized)
            result[line_type] = values
        return result

    def _task_domain(self, project):
        domain = [('project_id', '=', project.id)]
        if 'is_template' in self.env['project.task']._fields:
            domain.append(('is_template', '=', False))
        return domain

    def _task_description_lines(self, task, max_items=12, max_line_chars=220):
        return split_unique_text_lines(
            task.description,
            from_html=True,
            max_items=max_items,
            max_line_chars=max_line_chars,
            strip_email_noise=True,
        )

    def _is_url_only_scope_summary(self, value):
        normalized = self._normalize_optional_text(value, max_chars=False)
        if not normalized:
            return True
        lowered = normalized.lower()
        if lowered.startswith('http://') or lowered.startswith('https://') or lowered.startswith('www.'):
            return True
        return False

    def _scope_summary_needs_expansion(self, value):
        normalized = self._normalize_optional_text(value, max_chars=False)
        if not normalized:
            return True
        if self._is_url_only_scope_summary(normalized):
            return True

        folded = self._fold_scope_text(normalized)
        tokens = [token for token in re.split(r'[\W_]+', folded) if token]
        if not tokens:
            return True
        if normalized.endswith(':'):
            return True
        if is_weak_scope_heading(value, normalized):
            return True
        return False

    def _expanded_scope_summary(self, lines, start_index):
        parts = []
        for line in lines[start_index:start_index + 3]:
            cleaned = strip_inline_email_noise(line, max_chars=False)
            cleaned = self._normalize_optional_text(cleaned, max_chars=False)
            if not cleaned or self._is_url_only_scope_summary(cleaned):
                continue
            if is_non_factual_scope_summary(line, cleaned):
                continue
            if is_technical_noise_scope_summary(line, cleaned) and not is_weak_scope_heading(line, cleaned):
                continue
            parts.append(cleaned.strip(' ;:'))
            candidate = sanitize_scope_publication_candidate(' '.join(parts), max_chars=260)
            if not candidate:
                continue
            if self._scope_summary_needs_expansion(candidate):
                continue
            return candidate

        return sanitize_scope_publication_candidate(' '.join(parts), max_chars=260)

    def _task_description_summary(self, task):
        lines = self._task_description_lines(task, max_items=8, max_line_chars=260)
        for index, line in enumerate(lines):
            cleaned = strip_inline_email_noise(line, max_chars=260)
            cleaned = self._normalize_optional_text(cleaned, max_chars=260)
            if not cleaned or self._is_url_only_scope_summary(cleaned):
                continue
            if is_non_factual_scope_summary(line, cleaned):
                continue
            if is_technical_noise_scope_summary(line, cleaned) and not is_weak_scope_heading(line, cleaned):
                continue
            if self._scope_summary_needs_expansion(cleaned):
                expanded = self._expanded_scope_summary(lines, index)
                if expanded:
                    return expanded
                continue
            candidate = sanitize_scope_publication_candidate(line, max_chars=260)
            if candidate:
                return candidate
        return ''

    def _normalized_comparable(self, value):
        return self._normalize_optional_text(value, max_chars=220).lower().strip(' .,:;!?')

    def _is_meaningful_acceptance_criterion(self, value, summary='', task_name=''):
        normalized = self._normalize_optional_text(value, max_chars=220)
        if not normalized:
            return False

        comparable = normalized.lower().strip(' .,:;!?')
        if comparable == self._normalized_comparable(summary):
            return False
        if comparable == self._normalized_comparable(task_name):
            return False
        if is_low_signal_scope_summary(value, normalized):
            return False
        if self.ACCEPTANCE_HINT_RE.search(normalized):
            return True
        return len(normalized.split()) >= 6

    def _is_factual_acceptance_fallback(self, value, summary='', task_name=''):
        normalized = self._normalize_optional_text(value, max_chars=220)
        if not normalized:
            return False

        comparable = normalized.lower().strip(' .,:;!?')
        if comparable == self._normalized_comparable(summary):
            return False
        if comparable == self._normalized_comparable(task_name):
            return False
        if is_low_signal_scope_summary(value, normalized):
            return False
        return len(normalized.split()) >= 8

    def _generated_acceptance_criterion_from_text(self, value):
        normalized_value = self._normalize_optional_text(value, max_chars=180)
        if not normalized_value:
            return False
        if is_low_signal_scope_summary(value, normalized_value):
            return False
        if len(normalized_value.split()) < 3:
            return False
        if not self.ACCEPTANCE_HINT_RE.search(normalized_value) and not normalized_value.lower().startswith('ao '):
            return False
        criterion_source = normalized_value.rstrip('.')
        if not criterion_source:
            return False
        generated = "O ambito aprovado deve refletir %s." % (
            criterion_source[0].lower() + criterion_source[1:] if len(criterion_source) > 1 else criterion_source.lower()
        )
        return self._normalize_optional_text(generated, max_chars=220)

    def _overview_acceptance_criteria(self, project_lines, scope_items_payload):
        if project_lines['acceptance_criteria']:
            return project_lines['acceptance_criteria']

        derived = []
        seen = set()
        for item in scope_items_payload:
            for criterion in item['acceptance_criteria']:
                comparable = self._normalized_comparable(criterion)
                if not comparable or comparable in seen:
                    continue
                seen.add(comparable)
                derived.append(self._normalize_optional_text(criterion, max_chars=220))
                if len(derived) >= 8:
                    return derived

        return derived

    def _task_scope_summary(self, task):
        if task.pg_scope_summary:
            official_summary = sanitize_scope_publication_candidate(task.pg_scope_summary, max_chars=260)
            if official_summary:
                return self._normalize_text(official_summary)
        description_summary = self._task_description_summary(task)
        if description_summary:
            return self._normalize_text(description_summary)
        fallback_name = sanitize_scope_publication_candidate(task.name, max_chars=220)
        if not fallback_name:
            return ''
        if self._scope_summary_needs_expansion(fallback_name):
            return ''
        return self._normalize_text(fallback_name)

    def _task_acceptance_criteria(self, task, scope_summary):
        criteria = [
            item
            for item in self._split_text_lines(task.pg_acceptance_criteria_text)
            if self._is_meaningful_acceptance_criterion(item, summary=scope_summary, task_name=task.name)
        ]
        if criteria:
            return criteria

        derived = []
        seen = set()
        for line in self._task_description_lines(task):
            if not self._is_meaningful_acceptance_criterion(line, summary=scope_summary, task_name=task.name):
                continue
            comparable = self._normalized_comparable(line)
            if comparable in seen:
                continue
            seen.add(comparable)
            derived.append(self._normalize_optional_text(line, max_chars=220))
            if len(derived) >= 3:
                break
        if derived:
            return derived

        fallback_lines = []
        for line in self._task_description_lines(task):
            if not self._is_factual_acceptance_fallback(line, summary=scope_summary, task_name=task.name):
                continue
            comparable = self._normalized_comparable(line)
            if comparable in seen:
                continue
            seen.add(comparable)
            fallback_lines.append(self._normalize_optional_text(line, max_chars=220))
            if len(fallback_lines) >= 2:
                break
        if fallback_lines:
            return fallback_lines

        if task.pg_scope_summary:
            official_summary = strip_inline_email_noise(task.pg_scope_summary, max_chars=180)
            official_summary = self._normalize_optional_text(official_summary, max_chars=180)
            if official_summary and not is_low_signal_scope_summary(task.pg_scope_summary, official_summary):
                generated = self._generated_acceptance_criterion_from_text(official_summary)
                if generated:
                    return [generated]

        generated = self._generated_acceptance_criterion_from_text(task.name)
        if generated:
            return [generated]
        return derived

    def _build_task_source_url(self, task):
        return self._build_record_url('project.task', task.id)

    def _task_to_payload(self, task):
        assigned_users = sorted({user.display_name for user in task.user_ids})
        task_tags = sorted({tag.name for tag in task.tag_ids})
        scope_summary = self._task_scope_summary(task)
        return {
            'task_id': task.id,
            'task_name': self._normalize_text(task.name),
            'task_stage': self._normalize_text(task.stage_id.display_name if task.stage_id else '', fallback=''),
            'task_priority': str(task.priority or ''),
            'task_tags': task_tags,
            'scope_track': task.pg_scope_track or 'approved_scope',
            'scope_state': task.pg_scope_state,
            'scope_kind': task.pg_scope_kind or 'requirement',
            'scope_sequence': task.pg_scope_sequence or 0,
            'scope_summary': scope_summary,
            'acceptance_criteria': self._task_acceptance_criteria(task, scope_summary),
            'assigned_users': assigned_users,
            'last_task_update_at': fields.Datetime.to_string(task.write_date or task.create_date or fields.Datetime.now()),
            'source_url': self._build_task_source_url(task),
        }

    def _scope_tasks(self, project):
        tasks = self.env['project.task'].with_context(active_test=False).search(
            self._task_domain(project),
            order='pg_scope_sequence, priority desc, id',
        )
        return tasks.filtered(
            lambda task: task.active
            and task.pg_scope_relevant
            and (task.pg_scope_track or 'approved_scope') == 'approved_scope'
            and task.pg_scope_state not in ('excluded', 'dropped')
        )

    def _project_source_url(self, project):
        return self._build_record_url('project.project', project.id)

    def _build_record_url(self, model_name, record_id):
        base_url = self._get_base_url()
        if not base_url or not model_name or not record_id:
            return False
        return f"{base_url}/web#id={record_id}&model={model_name}"

    def _source_record_url(self, project, trigger_model, trigger_record_id):
        if trigger_model and trigger_record_id:
            source_url = self._build_record_url(trigger_model, trigger_record_id)
            if source_url:
                return source_url
        return self._project_source_url(project)

    def _build_scope_summary(self, tasks):
        states = [task.pg_scope_state for task in tasks]
        timestamps = [task.write_date or task.create_date for task in tasks if (task.write_date or task.create_date)]
        return {
            'active_scope_item_count': len(tasks),
            'validated_scope_item_count': len([state for state in states if state == 'validated']),
            'proposed_scope_item_count': len([state for state in states if state == 'proposed']),
            'deferred_scope_item_count': len([state for state in states if state == 'deferred']),
            'last_scope_change_at': fields.Datetime.to_string(max(timestamps)) if timestamps else False,
        }

    def build_payload(self, project, trigger_type='manual', trigger_model='project.project', trigger_record_id=None, sync_reason=None):
        project.ensure_one()
        project_lines = self._project_lines_map(project)
        tasks = self._scope_tasks(project)
        sync_published_at = fields.Datetime.now()
        scope_items_payload = [self._task_to_payload(task) for task in tasks]
        payload = {
            'schema_version': '1.0',
            'project_name': self._normalize_text(project.name),
            'project_id': project.id,
            'client_unit': self._normalize_text(project.pg_client_unit, fallback=''),
            'repository_summary': self._normalize_text(project.pg_repository_summary, fallback=''),
            'project_phase': project.pg_project_phase or self.PLACEHOLDER_TODO,
            'odoo_version': self._normalize_text(project.pg_odoo_version, fallback=''),
            'odoo_edition': project.pg_odoo_edition or 'unknown',
            'odoo_environment': project.pg_odoo_environment or 'unknown',
            'restrictions': {
                'standard_allowed': project.pg_standard_allowed or 'unknown',
                'additional_modules_allowed': project.pg_additional_modules_allowed or 'unknown',
                'studio_allowed': project.pg_studio_allowed or 'unknown',
                'custom_allowed': project.pg_custom_allowed or 'unknown',
                'additional_contract_restrictions': self._split_text_lines(project.pg_additional_contract_restrictions),
            },
            'scope_overview': {
                'business_goal': self._normalize_text(project.pg_business_goal),
                'current_request': self._normalize_text(project.pg_current_request),
                'current_process': self._normalize_text(project.pg_current_process),
                'problem_or_need': self._normalize_text(project.pg_problem_or_need),
                'business_impact': self._normalize_text(project.pg_business_impact),
                'trigger': self._normalize_text(project.pg_trigger),
                'frequency': self._normalize_text(project.pg_frequency),
                'volumes': self._normalize_text(project.pg_volumes),
                'urgency': project.pg_urgency or 'unknown',
                'acceptance_criteria': self._overview_acceptance_criteria(project_lines, scope_items_payload),
            },
            'project_lists': {line_type: project_lines[line_type] for line_type in self.LINE_TYPES if line_type != 'acceptance_criteria'},
            'scope_items': scope_items_payload,
            'scope_summary': self._build_scope_summary(tasks),
            'source_metadata': {
                'source_system': 'odoo_parametro_global',
                'source_model': trigger_model or 'project.project',
                'source_record_id': trigger_record_id or project.id,
                'source_record_url': self._source_record_url(project, trigger_model, trigger_record_id or project.id),
                'sync_trigger': trigger_type or 'manual',
                'sync_reason': sync_reason or '',
                'sync_published_at': fields.Datetime.to_string(sync_published_at),
                'sync_published_by': self.env.user.display_name or 'Odoo',
                'repo_branch': (project.pg_repo_branch or '').strip(),
                'payload_hash': '',
            },
        }
        return payload

    def build_hashable_payload(self, payload):
        hashable_payload = deepcopy(payload)
        source_metadata = hashable_payload.get('source_metadata') or {}
        for key in ('sync_trigger', 'sync_reason', 'sync_published_at', 'sync_published_by', 'payload_hash'):
            source_metadata[key] = ''
        hashable_payload['source_metadata'] = source_metadata
        return hashable_payload

    def serialize_payload(self, payload):
        return json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + '\n'
