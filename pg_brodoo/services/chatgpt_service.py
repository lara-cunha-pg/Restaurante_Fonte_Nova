import json
import logging

import requests

from odoo import _
from odoo.exceptions import UserError
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)


DEFAULT_BASE_PROMPT = """Objetivo: Transformar uma descricao funcional numa instrucao tecnica para um agente Codex.

Input:
- Nome: {task_name}
- Descricao: {task_description}
- Odoo versao: {odoo_version}

Output:

1. Contexto tecnico
2. Objetivo
3. Escopo tecnico
4. Models envolvidos
5. Views necessarias
6. Logica backend
7. Estrutura de ficheiros
8. Instrucoes para Codex executar no repo

Regras:
- Output tecnico
- Sem explicacoes desnecessarias
- Preparado para execucao automatica
"""

DEFAULT_PROMPT_INSTRUCTIONS = 'Gera apenas o prompt tecnico pedido. Nao incluas explicacoes adicionais.'
DEFAULT_PROMPT_MODEL = 'gpt-4.1-mini'
DEFAULT_CODEX_MODEL = 'gpt-5.3-codex'


class ChatGptPromptService:
    RESPONSES_API_URL = 'https://api.openai.com/v1/responses'
    MODELS_API_URL = 'https://api.openai.com/v1/models'
    DEFAULT_PROMPT_MODEL = DEFAULT_PROMPT_MODEL
    DEFAULT_CODEX_MODEL = DEFAULT_CODEX_MODEL
    DEFAULT_TIMEOUT = 120
    MODEL_CACHE_PARAM = 'pg_openai_available_models'
    DEFAULT_FALLBACK_MODELS = (
        'gpt-4.1-mini',
        'gpt-5.4',
        'gpt-5.3-codex',
        'gpt-5.2-codex',
    )

    def __init__(self, env):
        self.env = env
        self.params = env['ir.config_parameter'].sudo()

    def _get_param(self, key, default=None):
        return self.params.get_param(key, default)

    def _get_timeout(self):
        timeout = self._get_param('pg_openai_timeout', self.DEFAULT_TIMEOUT)
        try:
            return max(int(timeout), 1)
        except (TypeError, ValueError):
            return self.DEFAULT_TIMEOUT

    def _get_required_api_key(self):
        api_key = (self._get_param('pg_openai_api_key') or '').strip()
        if not api_key:
            raise UserError(_("Configuracao em falta: OpenAI API Key."))
        return api_key

    def _get_prompt_model(self):
        return (self._get_param('pg_openai_model') or self.DEFAULT_PROMPT_MODEL).strip()

    def _get_odoo_version(self):
        return (self._get_param('pg_odoo_version') or '19').strip()

    def _get_prompt_template(self):
        return self._get_param('pg_openai_prompt_template', DEFAULT_BASE_PROMPT) or DEFAULT_BASE_PROMPT

    def _get_prompt_instructions(self):
        return (
            self._get_param('pg_openai_prompt_instructions', DEFAULT_PROMPT_INSTRUCTIONS)
            or DEFAULT_PROMPT_INSTRUCTIONS
        )

    def _get_fallback_models(self):
        raw_value = self._get_param('pg_openai_fallback_models') or ''
        values = []
        for part in raw_value.replace('\r', '\n').replace(',', '\n').split('\n'):
            model_id = part.strip()
            if model_id and model_id not in values:
                values.append(model_id)
        if values:
            return values
        return list(self.DEFAULT_FALLBACK_MODELS)

    def _headers(self):
        return {
            'Authorization': f'Bearer {self._get_required_api_key()}',
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

    def _response_text(self, model, instructions, input_text, failure_message, text_format=None):
        payload = {
            'model': model,
            'instructions': instructions,
            'input': input_text,
            'text': {'format': text_format or {'type': 'text'}},
        }
        try:
            response = requests.post(
                self.RESPONSES_API_URL,
                headers=self._headers(),
                json=payload,
                timeout=self._get_timeout(),
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            _logger.exception("OpenAI responses request failed")
            raise UserError(failure_message % exc) from exc

        result = self._extract_output_text(response.json())
        if not result:
            raise UserError(_("A OpenAI nao devolveu texto utilizavel."))
        return result

    def _normalize_models(self, models):
        normalized_models = []
        seen_models = set()
        for model in models:
            model_id = (model.get('id') or '').strip()
            label = (model.get('label') or model_id).strip()
            if not model_id or model_id in seen_models:
                continue
            normalized_models.append({'id': model_id, 'label': label})
            seen_models.add(model_id)

        for fallback_id in self._get_fallback_models():
            if fallback_id not in seen_models:
                normalized_models.append({'id': fallback_id, 'label': fallback_id})
                seen_models.add(fallback_id)

        normalized_models.sort(key=lambda item: item['label'].lower())
        return normalized_models

    def _read_cached_models(self):
        raw_value = (self._get_param(self.MODEL_CACHE_PARAM) or '').strip()
        if not raw_value:
            return []
        try:
            return self._normalize_models(json.loads(raw_value))
        except ValueError:
            _logger.exception("Failed to parse cached model list")
            return []

    def _store_cached_models(self, models):
        normalized_models = self._normalize_models(models)
        self.params.set_param(self.MODEL_CACHE_PARAM, json.dumps(normalized_models))
        return normalized_models

    def _fetch_models_from_api(self):
        try:
            response = requests.get(
                self.MODELS_API_URL,
                headers={'Authorization': f'Bearer {self._get_required_api_key()}'},
                timeout=self._get_timeout(),
            )
            response.raise_for_status()
        except (UserError, requests.exceptions.RequestException):
            _logger.exception("Failed to refresh model list from OpenAI API")
            return []

        models = []
        for model in response.json().get('data', []):
            model_id = (model.get('id') or '').strip()
            if not model_id.startswith('gpt-'):
                continue
            models.append({'id': model_id, 'label': model_id})
        return models

    def refresh_available_models(self):
        api_models = self._fetch_models_from_api() or [{'id': model_id, 'label': model_id} for model_id in self._get_fallback_models()]
        return self._store_cached_models(api_models)

    def get_available_models(self, refresh=False, codex_only=False):
        if refresh:
            models = self.refresh_available_models()
        else:
            models = self._read_cached_models() or self.refresh_available_models()

        if codex_only:
            codex_models = [model for model in models if 'codex' in model['id']]
            if codex_models:
                return codex_models
            return [{'id': self.DEFAULT_CODEX_MODEL, 'label': self.DEFAULT_CODEX_MODEL}]
        return models

    def get_available_models_for_selection(self, refresh=False, codex_only=False):
        return [
            (model['id'], model['label'])
            for model in self.get_available_models(refresh=refresh, codex_only=codex_only)
        ]

    def generate_prompt(self, task):
        task_description = html2plaintext(task.description or '').strip() or _('Sem descricao funcional.')
        prompt = self._get_prompt_template().format(
            task_name=task.name or '',
            task_description=task_description,
            odoo_version=self._get_odoo_version(),
        )
        continuity_context = task.build_ai_continuity_context()
        if continuity_context:
            prompt = (
                f"{prompt}\n\n"
                "Historico acumulado da task:\n"
                f"{continuity_context}\n\n"
                "Se o pedido atual for incremental, preserva a continuidade com este historico."
            )
        return self._response_text(
            self._get_prompt_model(),
            self._get_prompt_instructions(),
            prompt,
            _("Falha ao gerar o prompt tecnico com OpenAI: %s"),
        )
