import json
import re

from .text_hygiene import curate_scope_publication_lines
from .text_hygiene import is_low_signal_attachment_name
from .text_hygiene import scope_classification_reason_label


HIGH_SIGNAL_PATTERNS = (
    r'\bblocked?\b',
    r'\bbloquead[oa]s?\b',
    r'\brisk\b',
    r'\brisco\b',
    r'\bdecid',
    r'\bagreed\b',
    r'\bapproved?\b',
    r'\baprovad[oa]s?\b',
    r'\bnext step[s]?\b',
    r'\bpr[oó]ximos passos\b',
    r'\bdepends on\b',
    r'\bdepend[eê]ncia\b',
    r'\bdepende de\b',
    r'\bgo-live\b',
    r'\bgo live\b',
    r'\bdeadline\b',
    r'\bprazo\b',
)


class ProjectMirrorContextBuilder:
    def _value(self, value, fallback='N/A'):
        if value in (False, None, '', []):
            return fallback
        return str(value)

    def _render_list(self, values, fallback='- N/A'):
        if not values:
            return fallback
        return '\n'.join(f"- {value}" for value in values)

    def _render_limited_items(self, values, formatter=None, limit=False, fallback='- N/A'):
        if not values:
            return fallback
        formatter = formatter or (lambda item: str(item))
        items = list(values)
        rendered = [formatter(item) for item in (items[:limit] if limit else items)]
        lines = [line for line in rendered if line]
        if limit and len(items) > limit:
            lines.append(f"- + {len(items) - limit} adicionais")
        return '\n'.join(lines) if lines else fallback

    def _short_text(self, value, max_chars=180):
        text = self._value(value, fallback='').strip()
        if not text:
            return ''
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 3].rstrip(' ,;:-') + '...'

    def _render_key_value_lines(self, pairs, fallback='- N/A'):
        lines = []
        for label, value in pairs:
            if value in (False, None, '', []):
                continue
            lines.append(f"- {label}: {value}")
        return '\n'.join(lines) if lines else fallback

    def _format_task_line(self, task):
        stage = self._value(task.get('stage_name'))
        owner = ', '.join(task.get('assignees') or []) or 'Sem responsavel'
        priority = self._value(task.get('priority'), fallback='0')
        return f"- {task.get('name', 'Task sem nome')} | etapa: {stage} | prioridade: {priority} | responsaveis: {owner}"

    def _render_task_list(self, tasks, limit=10, fallback='- N/A'):
        return self._render_limited_items(tasks, formatter=self._format_task_line, limit=limit, fallback=fallback)

    def _render_milestones(self, milestones, limit=10):
        def _format_milestone(milestone):
            return "- {name} | estado: {status} | owner: {owner} | target: {target}".format(
                name=milestone.get('name', 'Marco sem nome'),
                status=self._value(milestone.get('status')),
                owner=self._value(milestone.get('owner')),
                target=self._value(milestone.get('planned_end')),
            )
        return self._render_limited_items(milestones, formatter=_format_milestone, limit=limit)

    def _message_signal_score(self, message):
        body = (message.get('body') or '').strip().lower()
        if not body:
            return 0
        score = 0
        for pattern in HIGH_SIGNAL_PATTERNS:
            if re.search(pattern, body, re.IGNORECASE):
                score += 1
        if message.get('attachments'):
            score += 1
        if message.get('entry_type') == 'customer_message' and score:
            score += 1
        return score

    def _select_context_messages(self, messages, limit=3):
        if not messages:
            return []
        deduped = []
        seen = set()
        for index, message in enumerate(messages):
            key = (
                (message.get('body') or '').strip(),
                message.get('linked_model'),
                message.get('linked_record_id'),
            )
            if key in seen:
                continue
            seen.add(key)
            scored = dict(message)
            scored['_signal_score'] = self._message_signal_score(message)
            scored['_order'] = index
            deduped.append(scored)
        ranked = sorted(deduped, key=lambda item: (-item['_signal_score'], item['_order']))
        if any(item['_signal_score'] > 0 for item in ranked):
            ranked = [item for item in ranked if item['_signal_score'] > 0]
        return ranked[:limit]

    def _render_messages(self, messages, limit=3):
        def _format_message(message):
            body = self._short_text(message.get('body'), max_chars=180)
            attachment_count = len(message.get('attachments') or [])
            attachment_suffix = f" | anexos: {attachment_count}" if attachment_count else ''
            return "- [{date}] {author} - {body}{attachment_suffix}".format(
                date=self._value(message.get('date')),
                author=self._value(message.get('author')),
                body=body,
                attachment_suffix=attachment_suffix,
            )
        return self._render_limited_items(self._select_context_messages(messages, limit=limit), formatter=_format_message)

    def _render_attachments(self, attachments, limit=3):
        attachments = [
            attachment
            for attachment in (attachments or [])
            if not is_low_signal_attachment_name(attachment.get('name'))
        ]

        def _format_attachment(attachment):
            return "- {name} | tipo: {mimetype} | origem: {linked_model}:{linked_record_id}".format(
                name=self._value(attachment.get('name')),
                mimetype=self._value(attachment.get('mimetype')),
                linked_model=self._value(attachment.get('linked_model')),
                linked_record_id=self._value(attachment.get('linked_record_id')),
            )
        return self._render_limited_items(attachments, formatter=_format_attachment, limit=limit)

    def _render_permission(self, value):
        if value == 'yes':
            return 'PERMITIDO'
        if value == 'no':
            return 'NÃO PERMITIDO'
        return 'Não definido'

    def _render_governance_section(self, governance):
        lines = []
        odoo_version = governance.get('odoo_version') or ''
        odoo_edition = governance.get('odoo_edition') or 'unknown'
        odoo_environment = governance.get('odoo_environment') or 'unknown'
        if odoo_version:
            lines.append(f"- Versao Odoo: {odoo_version}")
        if odoo_edition != 'unknown':
            lines.append(f"- Edicao: {odoo_edition}")
        if odoo_environment != 'unknown':
            lines.append(f"- Ambiente: {odoo_environment}")
        lines.append(f"- Configuracao standard: {self._render_permission(governance.get('standard_allowed'))}")
        lines.append(f"- Modulos standard adicionais: {self._render_permission(governance.get('additional_modules_allowed'))}")
        lines.append(f"- Odoo Studio: {self._render_permission(governance.get('studio_allowed'))}")
        lines.append(f"- Desenvolvimento custom: {self._render_permission(governance.get('custom_allowed'))}")
        restrictions = governance.get('additional_contract_restrictions') or ''
        if restrictions:
            lines.append(f"- Restricoes adicionais: {restrictions}")
        urgency = governance.get('urgency') or 'unknown'
        if urgency != 'unknown':
            lines.append(f"- Urgencia: {urgency}")
        return '\n'.join(lines) if lines else '- N/A'

    def _render_history(self, events, limit=3):
        def _format_event(event):
            entity = event.get('entity') or {}
            return "- [{timestamp}] {event_type} | {summary} | origem: {model}:{record_id}".format(
                timestamp=self._value(event.get('timestamp')),
                event_type=self._value(event.get('event_type')),
                summary=self._short_text(event.get('summary'), max_chars=160),
                model=self._value(entity.get('odoo_model')),
                record_id=self._value(entity.get('odoo_id')),
            )
        return self._render_limited_items(events, formatter=_format_event, limit=limit)

    def _render_scope_backlog(self, backlog_items, limit=8):
        def _format_item(item):
            if not isinstance(item, dict):
                return ''
            reason = self._value(item.get('reason_label'))
            value = self._short_text(item.get('item'), max_chars=180)
            source = self._value(item.get('source_label'), fallback='')
            source_suffix = f" | origem: {source}" if source else ''
            return f"- {value} | motivo: {reason}{source_suffix}"

        return self._render_limited_items(backlog_items, formatter=_format_item, limit=limit)

    def _render_reason_summary(self, reason_counts, limit=4, fallback='- N/A'):
        if not reason_counts:
            return fallback
        ordered_reasons = sorted(
            reason_counts.items(),
            key=lambda item: (-int(item[1] or 0), item[0]),
        )
        return '- ' + ', '.join(
            "%s: %s" % (scope_classification_reason_label(reason), int(count or 0))
            for reason, count in ordered_reasons[:limit]
        )

    def parse_history_events_text(self, history_text):
        if not history_text:
            return []
        events = []
        for line in history_text.splitlines():
            line = (line or '').strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                events.append(payload)
        return events

    def build_context_markdown(
        self,
        project_payload,
        planning_payload,
        tasks_payload,
        chatter_payload,
        attachments_payload,
        history_events=None,
    ):
        project = project_payload.get('project') or {}
        governance = project.get('governance') or {}
        planning = planning_payload.get('planning') or {}
        planning_summary = planning.get('planning_summary') or {}
        next_milestone = planning.get('next_milestone') or {}
        tasks = tasks_payload.get('tasks') or []
        open_tasks = [task for task in tasks if not task.get('is_closed') and not task.get('is_cancelled')]
        chatter_messages = chatter_payload.get('messages') or []
        customer_messages = [message for message in chatter_messages if message.get('entry_type') == 'customer_message']
        internal_notes = [message for message in chatter_messages if message.get('entry_type') == 'internal_note']
        attachments = attachments_payload.get('attachments') or []
        history_events = history_events or []
        included_scope = curate_scope_publication_lines(project.get('included_scope') or [], max_items=12, max_chars=220)
        factual_scope_backlog = project.get('factual_scope_backlog') or []
        scope_quality_review = project.get('scope_quality_review') or {}
        included_scope_count = int(scope_quality_review.get('included_scope_count') or len(included_scope))
        factual_scope_backlog_count = int(scope_quality_review.get('factual_scope_backlog_count') or len(factual_scope_backlog))
        excluded_noise_count = int(scope_quality_review.get('excluded_noise_count') or 0)

        lines = [
            '# PG_CONTEXT - Contexto Global do Projeto',
            '',
            '> Artefacto derivado exclusivamente do espelho `.pg` publicado a partir do Odoo.',
            '> Serve como contexto consolidado para leitura humana e para agentes AI.',
            '',
            '## 1. Contexto Estrutural',
            '',
            f"- Projeto: {self._value(project.get('name'))}",
            f"- Cliente: {self._value(project.get('client_name'))}",
            f"- Gestor: {self._value(project.get('project_manager'))}",
            f"- Repositorio: {self._value(project.get('repository_full_name'))}",
            f"- Branch: {self._value(project.get('repository_branch'))}",
            f"- Fase atual: {self._value(project.get('phase'))}",
            f"- Etapa atual: {self._value(project.get('stage_name'))}",
            f"- Ultimo sync do espelho: {self._value(project_payload.get('source_metadata', {}).get('sync_published_at'))}",
            '',
            '### Objetivo e pedido atual',
            '',
            f"Objetivo do projeto: {self._value(project.get('objective'))}",
            '',
            f"Pedido atual: {self._value(project.get('current_request'))}",
            '',
            self._render_key_value_lines(
                [
                    ('Problema ou necessidade', project.get('problem_or_need')),
                    ('Impacto no negocio', project.get('business_impact')),
                    ('Unidade do cliente', project.get('client_unit')),
                ]
            ),
            '',
            '### Ambito incluido',
            '',
            self._render_limited_items(included_scope, limit=12),
            '',
            '### Itens factuais a curar no Odoo',
            '',
            f"- Total no ambito curado: {included_scope_count}",
            f"- Total pendente de curadoria: {factual_scope_backlog_count}",
            f"- Ruido excluido na curadoria: {excluded_noise_count}",
            'Motivos dominantes de curadoria pendente:',
            self._render_reason_summary(scope_quality_review.get('curation_reason_counts') or {}),
            self._render_scope_backlog(factual_scope_backlog, limit=8),
            '',
            '### Ambito excluido',
            '',
            self._render_limited_items(project.get('excluded_scope') or [], limit=8),
            '',
            '### Entregaveis',
            '',
            self._render_limited_items(project.get('deliverables') or [], limit=8),
            '',
            '### Restricoes e pressupostos',
            '',
            'Restricoes:',
            self._render_limited_items(project.get('restrictions') or [], limit=6),
            '',
            'Pressupostos:',
            self._render_limited_items(project.get('assumptions') or [], limit=6),
            '',
            'Stakeholders:',
            self._render_limited_items(project.get('stakeholders') or [], limit=6),
            '',
            '### Contrato e Parametros Odoo',
            '',
            '> Parametros lidos do Odoo. Os agentes AI devem respeitar estas restricoes em todas as respostas.',
            '',
            self._render_governance_section(governance),
            '',
            '## 2. Planeamento',
            '',
            f"- Total de marcos: {self._value(planning.get('milestone_count'), fallback='0')}",
            f"- Proxima etapa/marco: {self._value(next_milestone.get('name'))}",
            f"- Target da proxima etapa: {self._value(next_milestone.get('planned_end'))}",
            f"- Owner da proxima etapa: {self._value(next_milestone.get('owner'))}",
            f"- Tasks abertas no projeto: {self._value(planning_summary.get('open_task_count'), fallback='0')}",
            f"- Tasks abertas para a proxima etapa: {self._value(planning_summary.get('open_tasks_for_next_milestone_count'), fallback='0')}",
            '',
            '### Marcos planeados',
            '',
            self._render_milestones(planning.get('milestones') or [], limit=10),
            '',
            '### O que falta para atingir a proxima etapa',
            '',
            self._render_task_list(planning_summary.get('open_tasks_for_next_milestone') or [], limit=8),
            '',
            '### Proximas prioridades abertas',
            '',
            self._render_task_list(planning_summary.get('open_high_priority_tasks') or [], limit=8),
            '',
            '## 3. Operacao Atual',
            '',
            f"- Total de tarefas espelhadas: {self._value(tasks_payload.get('task_count'), fallback='0')}",
            f"- Tarefas abertas: {len(open_tasks)}",
            f"- Go-live alvo: {self._value(project.get('go_live_target'))}",
            '',
            '### Resumo operacional',
            '',
            f"Estado operacional reportado: {self._value(project.get('status_summary'))}",
            '',
            '### Principais tarefas abertas',
            '',
            self._render_task_list(open_tasks, limit=10),
            '',
            '## 4. Comunicacoes e Historico Recente',
            '',
            f"- Mensagens espelhadas: {self._value(chatter_payload.get('message_count'), fallback='0')}",
            f"- Mensagens com cliente: {len(customer_messages)}",
            f"- Notas internas: {len(internal_notes)}",
            f"- Anexos espelhados: {self._value(attachments_payload.get('attachment_count'), fallback='0')}",
            '',
            '### Comunicacoes recentes com cliente',
            '',
            self._render_messages(customer_messages, limit=3),
            '',
            '### Notas internas recentes',
            '',
            self._render_messages(internal_notes, limit=3),
            '',
            '### Metadata de anexos recentes',
            '',
            self._render_attachments(attachments, limit=3),
            '',
            '### Historico simples recente',
            '',
            self._render_history(history_events, limit=3),
            '',
        ]
        return '\n'.join(lines).rstrip() + '\n'
