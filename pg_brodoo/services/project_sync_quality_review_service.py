from odoo import fields

from .text_hygiene import SCOPE_ITEM_EXCLUDED_NOISE
from .text_hygiene import SCOPE_ITEM_FACTUAL_BUT_NEEDS_CURATION
from .text_hygiene import SCOPE_ITEM_INCLUDED
from .text_hygiene import STATUS_WORKFLOW_PREFIXES
from .text_hygiene import classify_scope_item
from .text_hygiene import is_low_signal_scope_summary
from .text_hygiene import is_non_factual_scope_summary
from .text_hygiene import is_placeholder_text
from .text_hygiene import normalize_inline_text
from .text_hygiene import sanitize_scope_publication_candidate
from .text_hygiene import sanitize_status_summary
from .text_hygiene import format_scope_reason_summary


class ProjectSyncQualityReviewService:
    PUBLISHABILITY_ELIGIBLE = 'eligible'
    PUBLISHABILITY_ELIGIBLE_WITH_WARNINGS = 'eligible_with_warnings'
    PUBLISHABILITY_NOT_ELIGIBLE = 'not_eligible'

    SEVERITY_BLOCKING = 'blocking'
    SEVERITY_WARNING = 'warning'
    SEVERITY_OBSERVATION = 'observacao'

    def __init__(self, env):
        self.env = env
        self.params = env['ir.config_parameter'].sudo()

    def _param_is_true(self, key):
        value = (self.params.get_param(key) or '').strip().lower()
        return value in {'1', 'true', 'yes', 'on'}

    def is_enabled(self):
        return self._param_is_true('pg_sync_quality_review_enabled')

    def _normalize(self, value, max_chars=False):
        return normalize_inline_text(value, fallback='', max_chars=max_chars, drop_placeholders=False)

    def _flatten_strings(self, value):
        if isinstance(value, str):
            normalized = self._normalize(value, max_chars=False)
            return [normalized] if normalized else []
        if isinstance(value, dict):
            result = []
            for nested in value.values():
                result.extend(self._flatten_strings(nested))
            return result
        if isinstance(value, (list, tuple)):
            result = []
            for nested in value:
                result.extend(self._flatten_strings(nested))
            return result
        return []

    def _workflow_hits(self, payload):
        hits = []
        for line in self._flatten_strings(payload):
            lowered = self._normalize(line, max_chars=False).lower()
            if any(lowered.startswith(prefix) for prefix in STATUS_WORKFLOW_PREFIXES):
                hits.append(line)
        return hits

    def _placeholder_hits(self, payload):
        hits = []
        for line in self._flatten_strings(payload):
            if '[PONTO POR VALIDAR]' in line or is_placeholder_text(line):
                hits.append(line)
        return hits

    def _deduplicated_lines(self, lines):
        seen = set()
        result = []
        for line in lines:
            normalized = self._normalize(line, max_chars=False).lower().strip(' .,:;!?')
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            result.append(normalized)
        return result

    def _duplicate_hits(self, payload, keys):
        all_lines = []
        for key in keys:
            all_lines.extend(self._flatten_strings(payload.get(key)))
        normalized_lines = [
            self._normalize(line, max_chars=False).lower().strip(' .,:;!?')
            for line in all_lines
            if self._normalize(line, max_chars=False)
        ]
        seen = set()
        duplicates = []
        for line in normalized_lines:
            if not line:
                continue
            if line in seen and line not in duplicates:
                duplicates.append(line)
            seen.add(line)
        return duplicates

    def _warning_key(self, warning):
        return (
            self._normalize(warning.get('severity'), max_chars=False).lower(),
            self._normalize(warning.get('publishability'), max_chars=False).lower(),
            self._normalize(warning.get('bucket'), max_chars=False).lower(),
            self._normalize(warning.get('message'), max_chars=False).lower(),
            self._normalize(warning.get('evidence'), max_chars=False).lower().strip(' .,:;!?'),
        )

    def _aggregate_warnings(self, warnings):
        aggregated = []
        grouped_indexes = {}
        for warning in warnings:
            key = self._warning_key(warning)
            occurrence_count = max(1, int(warning.get('occurrence_count') or 1))
            if key not in grouped_indexes:
                item = dict(warning)
                item['occurrence_count'] = occurrence_count
                aggregated.append(item)
                grouped_indexes[key] = len(aggregated) - 1
                continue
            aggregated[grouped_indexes[key]]['occurrence_count'] += occurrence_count
        return aggregated

    def _status_low_signal_warning(self, payload):
        summary = sanitize_status_summary(payload.get('status_summary'), max_chars=260)
        if not summary:
            return {
                'bucket': 'low_signal_summary',
                'message': 'Status summary is empty or collapses after hygiene filtering.',
                'evidence': '[empty]',
            }
        tokens = [token for token in summary.lower().split() if token]
        if len(tokens) < 8:
            return {
                'bucket': 'low_signal_summary',
                'message': 'Status summary is too short to support a strong publication.',
                'evidence': summary,
            }
        return False

    def _scope_acceptance_warnings(self, payload):
        warnings = []
        for item in payload.get('scope_items') or []:
            criteria = self._deduplicated_lines(item.get('acceptance_criteria') or [])
            if criteria:
                continue
            warnings.append(
                {
                    'bucket': 'weak_acceptance_criteria',
                    'message': 'Scope item still lacks strong acceptance criteria in the publishable payload.',
                    'evidence': self._normalize(item.get('title') or item.get('scope_summary') or '[unknown]', max_chars=180),
                }
            )
        return warnings

    def _scope_low_signal_warnings(self, payload):
        warnings = []
        for item in payload.get('scope_items') or []:
            summary = self._normalize(item.get('scope_summary'), max_chars=220)
            if not summary or is_placeholder_text(summary) or is_low_signal_scope_summary(summary):
                warnings.append(
                    {
                        'bucket': 'low_signal_summary',
                        'message': 'Scope item summary remains too weak for a strong factual snapshot.',
                        'evidence': self._normalize(item.get('title') or '[unknown]', max_chars=180),
                    }
                )
        return warnings

    def _build_feedback(self, label, warnings, warning_occurrence_count=None):
        if not warnings:
            return "Pre-publication quality review found no warnings in the latest %s payload." % label

        total_occurrences = warning_occurrence_count if warning_occurrence_count is not None else sum(
            max(1, int(warning.get('occurrence_count') or 1)) for warning in warnings
        )
        lines = [
            "Pre-publication quality review found %s warning occurrence(s) across %s unique warning(s) in the latest %s payload."
            % (total_occurrences, len(warnings), label),
        ]
        for warning in warnings[:8]:
            occurrence_count = max(1, int(warning.get('occurrence_count') or 1))
            suffix = " (x%s)" % occurrence_count if occurrence_count > 1 else ""
            occurrence_note = " Occurrences: %s." % occurrence_count if occurrence_count > 1 else ""
            lines.append(
                "- %(bucket)s%(suffix)s: %(message)s Evidence: %(evidence)s.%(occurrence_note)s"
                % {
                    'bucket': warning['bucket'],
                    'suffix': suffix,
                    'message': warning['message'],
                    'evidence': warning['evidence'] or '[none]',
                    'occurrence_note': occurrence_note,
                }
            )
        return '\n'.join(lines)

    def _empty_collection_warning(self, payload, collection_key, item_label):
        items = payload.get(collection_key)
        if items is None:
            return False
        if isinstance(items, (list, tuple)) and len(items) == 0:
            return {
                'bucket': 'empty_publishable_payload',
                'message': 'No %s items are currently eligible in the publishable payload.' % item_label,
                'evidence': '[empty]',
            }
        return False

    def _score(self, warnings):
        if isinstance(warnings, int):
            warning_count = warnings
        else:
            warning_count = len(warnings or [])
        return max(0, 100 - (warning_count * 15))

    def _mirror_score(self, blocking_count, warning_count, observation_count):
        return max(0, 100 - (blocking_count * 40) - (warning_count * 15) - (observation_count * 5))

    def _finding(self, bucket, severity, publishability, message, evidence, occurrence_count=1):
        return {
            'bucket': bucket,
            'severity': severity,
            'publishability': publishability,
            'message': message,
            'evidence': self._normalize(evidence, max_chars=220) or '[none]',
            'occurrence_count': max(1, int(occurrence_count or 1)),
        }

    def _mirror_summary_status(self, blocking_findings, warning_findings):
        if blocking_findings:
            return self.SEVERITY_BLOCKING
        if warning_findings:
            return self.SEVERITY_WARNING
        return 'ok'

    def _mirror_publishability(self, blocking_findings, warning_findings):
        if blocking_findings:
            return self.PUBLISHABILITY_NOT_ELIGIBLE
        if warning_findings:
            return self.PUBLISHABILITY_ELIGIBLE_WITH_WARNINGS
        return self.PUBLISHABILITY_ELIGIBLE

    def _build_mirror_feedback(self, review):
        if not review.get('enabled'):
            return False

        blocking_findings = review.get('blocking_findings') or []
        warning_findings = review.get('warning_findings') or []
        observations = review.get('observations') or []
        status = review.get('summary_status') or 'ok'
        included_scope_count = int(review.get('included_scope_count') or 0)
        factual_scope_backlog_count = int(review.get('factual_scope_backlog_count') or 0)
        excluded_noise_count = int(review.get('excluded_noise_count') or 0)
        factual_scope_backlog_reason_counts = review.get('factual_scope_backlog_reason_counts') or {}
        excluded_noise_reason_counts = review.get('excluded_noise_reason_counts') or {}
        lines = [
            "Mirror quality review status: %s. Blocking findings: %s. Warning findings: %s. Observations: %s."
            % (status, len(blocking_findings), len(warning_findings), len(observations))
        ]
        lines.append(
            "Curated scope snapshot: included %s item(s), backlog %s item(s), excluded noise %s item(s)."
            % (included_scope_count, factual_scope_backlog_count, excluded_noise_count)
        )
        if factual_scope_backlog_count:
            lines.append(
                "Factual scope backlog pending curation: %s item(s). Dominant reasons: %s."
                % (
                    factual_scope_backlog_count,
                    format_scope_reason_summary(factual_scope_backlog_reason_counts) or 'n/a',
                )
            )
        if excluded_noise_count:
            lines.append(
                "Excluded noise detected during scope curation: %s item(s). Dominant reasons: %s."
                % (
                    excluded_noise_count,
                    format_scope_reason_summary(excluded_noise_reason_counts) or 'n/a',
                )
            )

        for label, findings in (
            ('Blocking', blocking_findings),
            ('Warning', warning_findings),
            ('Observation', observations),
        ):
            for finding in findings[:6]:
                occurrence_count = max(1, int(finding.get('occurrence_count') or 1))
                suffix = " (x%s)" % occurrence_count if occurrence_count > 1 else ""
                lines.append(
                    "- %(label)s %(bucket)s%(suffix)s: %(message)s Evidence: %(evidence)s."
                    % {
                        'label': label,
                        'bucket': finding.get('bucket') or 'unknown',
                        'suffix': suffix,
                        'message': finding.get('message') or '[no message]',
                        'evidence': finding.get('evidence') or '[none]',
                    }
                )
        return '\n'.join(lines)

    def _review_factual_scope_backlog(self, factual_scope_backlog, scope_quality_review):
        reason_counts = {}
        for item in factual_scope_backlog or []:
            if not isinstance(item, dict):
                continue
            reason = self._normalize(item.get('reason'), max_chars=False) or 'needs_manual_scope_curation'
            reason_counts[reason] = int(reason_counts.get(reason) or 0) + 1
        if reason_counts:
            return reason_counts
        persisted_counts = (scope_quality_review or {}).get('curation_reason_counts') or {}
        normalized_counts = {}
        for reason, count in persisted_counts.items():
            normalized_reason = self._normalize(reason, max_chars=False)
            if not normalized_reason:
                continue
            normalized_counts[normalized_reason] = int(count or 0)
        return normalized_counts

    def _review_excluded_noise(self, scope_quality_review):
        persisted_counts = (scope_quality_review or {}).get('excluded_noise_reason_counts') or {}
        normalized_counts = {}
        for reason, count in persisted_counts.items():
            normalized_reason = self._normalize(reason, max_chars=False)
            if not normalized_reason:
                continue
            normalized_counts[normalized_reason] = int(count or 0)
        return normalized_counts

    def _review_included_scope_item(self, item):
        normalized = self._normalize(item, max_chars=False)
        if not normalized:
            return self._finding(
                'minimum_required_bucket_empty',
                self.SEVERITY_WARNING,
                self.PUBLISHABILITY_NOT_ELIGIBLE,
                'Included scope contains an empty or collapsed line after normalization.',
                '[empty]',
            )

        classification = classify_scope_item(item, max_chars=220)
        if classification.get('state') == SCOPE_ITEM_INCLUDED:
            publication_candidates = classification.get('publication_candidates') or []
            if len(publication_candidates) > 1:
                return self._finding(
                    'included_scope_compound_item',
                    self.SEVERITY_WARNING,
                    self.PUBLISHABILITY_ELIGIBLE_WITH_WARNINGS,
                    'Included scope still contains a compound item that should be segmented conservatively.',
                    normalized,
                )
            if classification.get('needs_hygiene'):
                return self._finding(
                    'included_scope_needs_hygiene',
                    self.SEVERITY_WARNING,
                    self.PUBLISHABILITY_ELIGIBLE_WITH_WARNINGS,
                    'Included scope still needs hygiene normalization before it is considered clean.',
                    normalized,
                )
            return False

        if classification.get('state') == SCOPE_ITEM_FACTUAL_BUT_NEEDS_CURATION:
            if classification.get('reason') == 'compound_item':
                return self._finding(
                    'included_scope_split_not_safe',
                    self.SEVERITY_WARNING,
                    self.PUBLISHABILITY_NOT_ELIGIBLE,
                    'Included scope still contains a compound item that cannot be split safely.',
                    normalized,
                )
            if classification.get('reason') == 'needs_manual_scope_curation':
                return self._finding(
                    'included_scope_not_eligible',
                    self.SEVERITY_WARNING,
                    self.PUBLISHABILITY_NOT_ELIGIBLE,
                    'Included scope still contains a factual item that should stay in curation backlog, not in the curated scope.',
                    normalized,
                )
            return self._finding(
                'included_scope_low_signal',
                self.SEVERITY_WARNING,
                self.PUBLISHABILITY_ELIGIBLE_WITH_WARNINGS,
                'Included scope still contains a low-signal item.',
                normalized,
            )

        if classification.get('state') == SCOPE_ITEM_EXCLUDED_NOISE:
            if classification.get('reason') == 'conversational_follow_up':
                return self._finding(
                    'included_scope_conversational_follow_up',
                    self.SEVERITY_WARNING,
                    self.PUBLISHABILITY_NOT_ELIGIBLE,
                    'Included scope still contains conversational follow-up instead of factual scope.',
                    normalized,
                )
            return self._finding(
                'included_scope_not_eligible',
                self.SEVERITY_WARNING,
                self.PUBLISHABILITY_NOT_ELIGIBLE,
                'Included scope still contains a non-publishable item.',
                normalized,
            )
        return False

    def _review_scope_publishability(self, included_scope):
        findings = []
        if not included_scope:
            findings.append(
                self._finding(
                    'minimum_required_bucket_empty',
                    self.SEVERITY_WARNING,
                    self.PUBLISHABILITY_ELIGIBLE_WITH_WARNINGS,
                    'Included scope is empty in the latest mirror payload.',
                    '[empty]',
                )
            )
            return findings
        for item in included_scope or []:
            finding = self._review_included_scope_item(item)
            if finding:
                findings.append(finding)
        return findings

    def _review_planning_publishability(self, planning_summary):
        findings = []
        next_milestone_name = self._normalize(planning_summary.get('next_milestone_name'), max_chars=False)
        target_date = planning_summary.get('next_milestone_target_date')
        if next_milestone_name and target_date:
            parsed_target_date = fields.Date.from_string(target_date)
            if parsed_target_date and parsed_target_date < fields.Date.today():
                findings.append(
                    self._finding(
                        'next_milestone_target_in_past',
                        self.SEVERITY_WARNING,
                        self.PUBLISHABILITY_ELIGIBLE_WITH_WARNINGS,
                        'Next milestone target date is already in the past.',
                        '%s (%s)' % (next_milestone_name, target_date),
                    )
                )
        if next_milestone_name and not self._normalize(planning_summary.get('next_milestone_owner'), max_chars=False):
            findings.append(
                self._finding(
                    'next_milestone_owner_missing',
                    self.SEVERITY_WARNING,
                    self.PUBLISHABILITY_ELIGIBLE_WITH_WARNINGS,
                    'Next milestone does not define an owner.',
                    next_milestone_name,
                )
            )
        if next_milestone_name and int(planning_summary.get('open_tasks_for_next_milestone_count') or 0) == 0:
            findings.append(
                self._finding(
                    'next_milestone_without_open_tasks',
                    self.SEVERITY_WARNING,
                    self.PUBLISHABILITY_ELIGIBLE_WITH_WARNINGS,
                    'Next milestone has no open tasks linked to it.',
                    next_milestone_name,
                )
            )
        if not next_milestone_name:
            findings.append(
                self._finding(
                    'next_milestone_missing',
                    self.SEVERITY_OBSERVATION,
                    self.PUBLISHABILITY_ELIGIBLE_WITH_WARNINGS,
                    'Planning payload does not currently identify a next milestone.',
                    '[missing]',
                )
            )
        return findings

    def _project_plan_specific_warnings(self, payload):
        warnings = []
        for plan_item in payload.get('plan_items') or []:
            title = self._normalize(plan_item.get('title'), max_chars=False) or '[unknown]'
            planned_end = plan_item.get('planned_end')
            status = self._normalize(plan_item.get('status'), max_chars=False).lower()
            owner = self._normalize(plan_item.get('owner'), max_chars=False)
            if planned_end and status != 'completed':
                parsed_end = fields.Date.from_string(planned_end)
                if parsed_end and parsed_end < fields.Date.today():
                    warnings.append(
                        {
                            'bucket': 'plan_item_target_in_past',
                            'message': 'Project plan item target date is already in the past while the item is not completed.',
                            'evidence': '%s (%s)' % (title, planned_end),
                        }
                    )
            if not owner or is_placeholder_text(owner):
                warnings.append(
                    {
                        'bucket': 'plan_item_owner_missing',
                        'message': 'Project plan item does not define a valid owner.',
                        'evidence': title,
                    }
                )
        return warnings

    def review_mirror_payload(self, project_payload, planning_payload, tasks_payload, chatter_payload, attachments_payload):
        if not self.is_enabled():
            return {
                'enabled': False,
                'summary_status': 'ok',
                'publishability': self.PUBLISHABILITY_ELIGIBLE,
                'blocking_findings': [],
                'warning_findings': [],
                'observations': [],
                'bucket_reviews': [],
                'quality_score': 0,
                'feedback': False,
            }

        project_data = (project_payload or {}).get('project') or {}
        planning = (planning_payload or {}).get('planning') or {}
        planning_summary = planning.get('planning_summary') or {}
        included_scope = project_data.get('included_scope') or []
        factual_scope_backlog = project_data.get('factual_scope_backlog') or []
        scope_quality_review = project_data.get('scope_quality_review') or {}
        deliverables = project_data.get('deliverables') or []
        planning_items = planning.get('milestones') or []
        tasks = (tasks_payload or {}).get('tasks') or []
        chatter_messages = (chatter_payload or {}).get('messages') or []
        attachments = (attachments_payload or {}).get('attachments') or []

        blocking_findings = []
        warning_findings = self._review_scope_publishability(included_scope)
        observations = []

        essential_context_values = [
            project_data.get('repository_summary'),
            project_data.get('objective'),
            project_data.get('current_request'),
            project_data.get('current_process'),
            project_data.get('problem_or_need'),
            project_data.get('business_impact'),
        ]
        has_essential_context = any(self._normalize(value, max_chars=False) for value in essential_context_values)
        has_operational_evidence = bool(
            deliverables
            or planning_items
            or tasks
            or chatter_messages
            or attachments
            or int(planning_summary.get('open_task_count') or 0) > 0
            or int(planning_summary.get('open_tasks_for_next_milestone_count') or 0) > 0
            or self._normalize(planning_summary.get('next_milestone_name'), max_chars=False)
        )
        if not has_essential_context and not included_scope and not has_operational_evidence:
            blocking_findings.append(
                self._finding(
                    'essential_project_context_missing',
                    self.SEVERITY_BLOCKING,
                    self.PUBLISHABILITY_NOT_ELIGIBLE,
                    'Mirror payload is missing the minimum factual project context required for publication.',
                    '[project core is empty]',
                )
            )

        planning_findings = self._review_planning_publishability(planning_summary)
        warning_findings.extend([finding for finding in planning_findings if finding['severity'] == self.SEVERITY_WARNING])
        observations.extend([finding for finding in planning_findings if finding['severity'] == self.SEVERITY_OBSERVATION])

        blocking_findings = self._aggregate_warnings(blocking_findings)
        warning_findings = self._aggregate_warnings(warning_findings)
        observations = self._aggregate_warnings(observations)
        summary_status = self._mirror_summary_status(blocking_findings, warning_findings)
        publishability = self._mirror_publishability(blocking_findings, warning_findings)

        bucket_reviews = blocking_findings + warning_findings + observations
        factual_scope_backlog_reason_counts = self._review_factual_scope_backlog(
            factual_scope_backlog,
            scope_quality_review,
        )
        excluded_noise_reason_counts = self._review_excluded_noise(scope_quality_review)
        review = {
            'enabled': True,
            'summary_status': summary_status,
            'publishability': publishability,
            'blocking_findings': blocking_findings,
            'warning_findings': warning_findings,
            'observations': observations,
            'bucket_reviews': bucket_reviews,
            'blocking_count': len(blocking_findings),
            'warning_count': len(warning_findings),
            'observation_count': len(observations),
            'included_scope_count': int(scope_quality_review.get('included_scope_count') or len(included_scope)),
            'factual_scope_backlog_count': len(factual_scope_backlog),
            'factual_scope_backlog_reason_counts': factual_scope_backlog_reason_counts,
            'excluded_noise_count': int(scope_quality_review.get('excluded_noise_count') or 0),
            'excluded_noise_reason_counts': excluded_noise_reason_counts,
            'quality_score': self._mirror_score(len(blocking_findings), len(warning_findings), len(observations)),
        }
        review['feedback'] = self._build_mirror_feedback(review)
        return review

    def review_status_payload(self, payload):
        if not self.is_enabled():
            return {'enabled': False, 'quality_score': 0, 'warnings': [], 'feedback': False}

        raw_warnings = []
        for hit in self._placeholder_hits(payload):
            raw_warnings.append(
                {
                    'bucket': 'placeholder_residual',
                    'message': 'A placeholder survived into the publishable status payload.',
                    'evidence': self._normalize(hit, max_chars=180),
                }
        )
        for hit in self._workflow_hits(payload):
            raw_warnings.append(
                {
                    'bucket': 'workflow_text_detected',
                    'message': 'Workflow meta-text is still present in the publishable status payload.',
                    'evidence': self._normalize(hit, max_chars=180),
                }
        )
        summary_warning = self._status_low_signal_warning(payload)
        if summary_warning:
            raw_warnings.append(summary_warning)
        for duplicate in self._duplicate_hits(payload, ('milestones', 'blockers', 'risks', 'next_steps', 'pending_decisions')):
            raw_warnings.append(
                {
                    'bucket': 'duplicate_content',
                    'message': 'Duplicated lines remain across status buckets.',
                    'evidence': self._normalize(duplicate, max_chars=180),
                }
            )
        warnings = self._aggregate_warnings(raw_warnings)
        warning_occurrence_count = len(raw_warnings)

        return {
            'enabled': True,
            'quality_score': self._score(warning_occurrence_count),
            'warnings': warnings,
            'warning_occurrence_count': warning_occurrence_count,
            'warning_group_count': len(warnings),
            'feedback': self._build_feedback('status', warnings, warning_occurrence_count=warning_occurrence_count),
        }

    def review_scope_payload(self, payload):
        if not self.is_enabled():
            return {'enabled': False, 'quality_score': 0, 'warnings': [], 'feedback': False}

        raw_warnings = []
        for hit in self._placeholder_hits(payload):
            raw_warnings.append(
                {
                    'bucket': 'placeholder_residual',
                    'message': 'A placeholder survived into the publishable scope payload.',
                    'evidence': self._normalize(hit, max_chars=180),
                }
            )
        for hit in self._workflow_hits(payload):
            raw_warnings.append(
                {
                    'bucket': 'workflow_text_detected',
                    'message': 'Workflow meta-text is still present in the publishable scope payload.',
                    'evidence': self._normalize(hit, max_chars=180),
                }
            )
        raw_warnings.extend(self._scope_low_signal_warnings(payload))
        raw_warnings.extend(self._scope_acceptance_warnings(payload))
        for duplicate in self._duplicate_hits(payload, ('scope_overview', 'scope_items')):
            raw_warnings.append(
                {
                    'bucket': 'duplicate_content',
                    'message': 'Duplicated lines remain across scope payload sections.',
                    'evidence': self._normalize(duplicate, max_chars=180),
                }
            )
        warnings = self._aggregate_warnings(raw_warnings)
        warning_occurrence_count = len(raw_warnings)

        return {
            'enabled': True,
            'quality_score': self._score(warning_occurrence_count),
            'warnings': warnings,
            'warning_occurrence_count': warning_occurrence_count,
            'warning_group_count': len(warnings),
            'feedback': self._build_feedback('scope', warnings, warning_occurrence_count=warning_occurrence_count),
        }

    def _review_generic_payload(self, payload, label, collection_key=None, item_label='snapshot'):
        if not self.is_enabled():
            return {'enabled': False, 'quality_score': 0, 'warnings': [], 'feedback': False}

        raw_warnings = []
        for hit in self._placeholder_hits(payload):
            raw_warnings.append(
                {
                    'bucket': 'placeholder_residual',
                    'message': 'A placeholder survived into the publishable %s payload.' % label,
                    'evidence': self._normalize(hit, max_chars=180),
                }
            )
        for hit in self._workflow_hits(payload):
            raw_warnings.append(
                {
                    'bucket': 'workflow_text_detected',
                    'message': 'Workflow meta-text is still present in the publishable %s payload.' % label,
                    'evidence': self._normalize(hit, max_chars=180),
                }
            )
        if collection_key:
            empty_collection_warning = self._empty_collection_warning(payload, collection_key, item_label)
            if empty_collection_warning:
                raw_warnings.append(empty_collection_warning)

        warnings = self._aggregate_warnings(raw_warnings)
        warning_occurrence_count = len(raw_warnings)
        return {
            'enabled': True,
            'quality_score': self._score(warning_occurrence_count),
            'warnings': warnings,
            'warning_occurrence_count': warning_occurrence_count,
            'warning_group_count': len(warnings),
            'feedback': self._build_feedback(label, warnings, warning_occurrence_count=warning_occurrence_count),
        }

    def review_decisions_payload(self, payload):
        return self._review_generic_payload(payload, 'decisions', collection_key='decisions', item_label='decision')

    def review_risks_payload(self, payload):
        return self._review_generic_payload(payload, 'risks', collection_key='risks', item_label='risk')

    def review_deliveries_payload(self, payload):
        return self._review_generic_payload(payload, 'deliveries', collection_key='deliveries', item_label='delivery')

    def review_requirements_payload(self, payload):
        return self._review_generic_payload(
            payload,
            'requirements',
            collection_key='requirements',
            item_label='requirement',
        )

    def review_project_plan_payload(self, payload):
        review = self._review_generic_payload(
            payload,
            'project plan',
            collection_key='plan_items',
            item_label='plan item',
        )
        if not review.get('enabled'):
            return review

        raw_warnings = list(review.get('warnings') or [])
        raw_warnings.extend(self._project_plan_specific_warnings(payload))
        warnings = self._aggregate_warnings(raw_warnings)
        warning_occurrence_count = sum(max(1, int(warning.get('occurrence_count') or 1)) for warning in raw_warnings)
        review.update(
            {
                'quality_score': self._score(warning_occurrence_count),
                'warnings': warnings,
                'warning_occurrence_count': warning_occurrence_count,
                'warning_group_count': len(warnings),
                'feedback': self._build_feedback(
                    'project plan',
                    warnings,
                    warning_occurrence_count=warning_occurrence_count,
                ),
            }
        )
        return review

    def review_budget_payload(self, payload):
        return self._review_generic_payload(
            payload,
            'budget',
            collection_key='budget_lines',
            item_label='budget line',
        )
