import re
import unicodedata

from odoo.tools import html2plaintext


PLACEHOLDER_LINE_RE = re.compile(
    r'^\[?\s*(?:ponto por validar|preencher|todo|tbd|placeholder|por validar)\s*(?:[:\-].*)?\]?\s*$',
    re.IGNORECASE,
)
REPLY_HEADER_RE = re.compile(
    r'^\s*(?:from|de|sent|enviado|to|para|subject|assunto|cc|date|data)\s*:',
    re.IGNORECASE,
)
REPLY_WROTE_RE = re.compile(
    r'^\s*(?:on|em)\b.+\b(?:wrote|escreveu)\s*:\s*$',
    re.IGNORECASE,
)
REPLY_SEPARATOR_RE = re.compile(
    r'^\s*(?:-{2,}\s*(?:original|forwarded)\s+message\s*-{2,}|_{5,})\s*$',
    re.IGNORECASE,
)
SIGNATURE_MARKER_RE = re.compile(
    r'^\s*(?:--+|__+|best regards[,]?|kind regards[,]?|regards[,]?|com os melhores cumprimentos[,]?|cumprimentos[,]?|atenciosamente[,]?|thanks[,]?|sent from my|enviado do meu)\b',
    re.IGNORECASE,
)
LEGAL_DISCLAIMER_MARKER_RE = re.compile(
    r'^\s*(?:aviso legal|disclaimer|confidentiality notice|este e-mail|this e-mail transmission)\b',
    re.IGNORECASE,
)
INLINE_SIGNATURE_RE = re.compile(
    r'\b(?:best regards|kind regards|regards|com os melhores cumprimentos|cumprimentos|atenciosamente|thanks)\b.*$',
    re.IGNORECASE,
)
INLINE_MARKUP_RE = re.compile(r'(?<!\w)[*_`]+([^*_`]+?)[*_`]+')
INLINE_REPLY_RE = re.compile(
    r'\b(?:on|em)\b.+\b(?:wrote|escreveu)\s*:.*$',
    re.IGNORECASE,
)
INLINE_CONTACT_MARKER_RE = re.compile(
    r'\b(?:mail\s*:|tel\.?|tlm\.?|telefone\s*:|telemovel\s*:|whatsapp\s*:|contacto\s*:|contact\s*:|unidade1\s*:|unidade2\s*:|maps\.app\.goo\.gl|chamada para rede|www\.|http[s]?://)',
    re.IGNORECASE,
)
INLINE_PHONE_RE = re.compile(
    r'(?:\+?\d[\d\s()./-]{7,}\d)',
    re.IGNORECASE,
)
INLINE_EMAIL_RE = re.compile(
    r'\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b',
    re.IGNORECASE,
)
INLINE_URL_RE = re.compile(r'(?:https?://\S+|www\.\S+)', re.IGNORECASE)
INLINE_REFERENCE_TOKEN_RE = re.compile(r'\[(?:\d+|link|anexo)\]', re.IGNORECASE)
INLINE_MAIL_MESSAGE_RE = re.compile(r'https?://\S+/mail/message/\d+(?:\s*\[\d+\])?', re.IGNORECASE)
INLINE_ODOO_ASSET_RE = re.compile(
    r'(?:/odoo/\S+|/web/(?:image|content)/\S+)',
    re.IGNORECASE,
)
INLINE_GREETING_RE = re.compile(
    r'^\s*(?:bom dia|boa tarde|boa noite|ol[aá]|hello)\b',
    re.IGNORECASE,
)
INLINE_ASSET_TOKEN_RE = re.compile(r'\b(?:image|imagem|none)\s*\[\d+\]\b', re.IGNORECASE)
INLINE_DANGLING_CONNECTOR_RE = re.compile(r'^(?:e|ou|o|a|de|da|do|para|com)(?:\s+)?$', re.IGNORECASE)
DANGLING_SCOPE_FRAGMENT_RE = re.compile(
    r'^(?:alterar|associar|configurar|confirmar|consolidar|corrigir|criar|desenvolver|'
    r'formar|garantir|importa(?:r|cao)|incluir|instalar|integrar|investigar|migrar|'
    r'possibilitar|preparar|re[-\s]?importa(?:r|cao)|registar|substituir|testar|validar|'
    r'verificar|acrescentar|anali(?:sar|zar)|anliasar|pedir|questionar|sugerir|eliminar)\s+'
    r'(?:e|ou|de|da|do|para|com|em|no|na|sem|por)$',
    re.IGNORECASE,
)
ADDRESS_FRAGMENT_RE = re.compile(
    r'^(?:rua|avenida|av\.?|travessa|tv\.?|alameda|estrada|lugar|praca|praça|praceta|bairro|zona\s+industrial)\b',
    re.IGNORECASE,
)
WHATSAPP_ARROW_RE = re.compile(r'(?<!\S)->\s*')
INLINE_QUOTE_PREFIX_RE = re.compile(r'^\s*>\s*')
ATTACHMENT_FILENAME_RE = re.compile(
    r'(?:^|[\s:;-])([^\s\\/:*?"<>|]+\.(?:xlsx?|xlsm|csv|pdf|png|jpe?g|gif|docx?|pptx?|txt|zip|xml|json|ya?ml))$',
    re.IGNORECASE,
)
CHANNEL_LABEL_ONLY_RE = re.compile(
    r'^(?:whats?app(?:\s+business)?|email|mail|teams|slack|chat|telefone|telemovel|phone|call|chamada)$',
    re.IGNORECASE,
)
GENERIC_SCOPE_HEADING_RE = re.compile(
    r'^(?:agendamento|categorias|codigo|compras|configuracao|configuração|crm|desenvolvimento|email|'
    r'formacao|formação|gestao|gestão|importacao|importação|mail|odoo|orcamentacao|orçamentação|'
    r'ponto|seguimento|template|teste|vendas|whatsapp)$',
    re.IGNORECASE,
)
LOW_SIGNAL_SCOPE_EXACT_RE = re.compile(
    r'^(?:email\s+odoo\s+security|odoo\s*-\s*seguimento\s+de\s+trabalhos|lista\s+fornecedores\s*/\s*clientes)$',
    re.IGNORECASE,
)
LOW_SIGNAL_SCOPE_PATTERN_RE = re.compile(
    r'^(?:documento\s+de\b|o\s+email\s+a\s+monitorizar\b|arvore\s+de\s+categorias\b)',
    re.IGNORECASE,
)
WEAK_NOMINAL_SCOPE_EXACT_RE = re.compile(
    r'^(?:kick[\s-]?off|go[\s-]?live|odoo|projeto|projecto|contabilidade)$',
    re.IGNORECASE,
)
WEAK_NOMINAL_SCOPE_PATTERN_RE = re.compile(
    r'^(?:forma(?:cao|ção)\s+(?:crm|website)|(?:[a-z0-9._-]+\s+)?website|'
    r'codigo\s+de\s+subscri(?:cao|ção)|coluna\s+[a-z]\b.*|'
    r'arvore\s+de\s+categorias\b.*)$',
    re.IGNORECASE,
)
NON_FACTUAL_SCOPE_PREFIX_RE = re.compile(
    r'^\s*(?:conforme conversad\w*|penso\b|preciso\b|envio\b|segue\b|boa\s+(?:tarde|noite)|bom dia|obrigad[oa]\b|>\s*whatsapp\b)',
    re.IGNORECASE,
)
NON_FACTUAL_SCOPE_FRAGMENT_RE = re.compile(
    r'\b(?:envio em anexo|darmos ini\w*|para nos podermos organizar|quando pensas|'
    r'ja(?:\s+te)?\s+ter\s+fornecido|qual\s+a\s+proxima\s+fase|preciso\s+por\s+favor|'
    r'ponto\s+de\s+situ\w+|continuarmos\s+a\s+dar\s+seguimento|conforme combinado|'
    r'em\s+relacao\s+ao\s+tema\s+de\b|penso\s+que\s+o\s+consigo\s+fazer\b|'
    r'surgiu\s+novas?\s+algumas?\s+complica\w+)\b',
    re.IGNORECASE,
)
NON_FACTUAL_SCOPE_NOISE_TOKENS = (
    'mail none',
    'mailto:',
    'image none',
    'de:',
    'enviada:',
    'assunto:',
    'ver tarefa',
)
CONVERSATIONAL_FOLLOW_UP_PREFIX_RE = re.compile(
    r'^\s*(?:qualquer\s+duvid\w*|fico\s+a\s+aguardar\b|aguardo\b|recebi\s+o\s+email\b|'
    r'hoje\s+de\s+tarde\b|obrigad[oa]\b|disponha\b|seguimos\s+em\s+contacto\b|'
    r'ficamos\s+a\s+aguardar\b|necessito\b|por\s+favor\b|rui\s+pediu\b|'
    r'o\s+email\s+a\s+monitorizar\b|fiquei\s+de\s+lhe\s+enviar\b)',
    re.IGNORECASE,
)
CONVERSATIONAL_FOLLOW_UP_FRAGMENT_RE = re.compile(
    r'\b(?:qualquer\s+duvid\w*|fico\s+a\s+aguardar\b|aguardo\s+(?:feedback|resposta)\b|'
    r'nao\s+sei\s+do\s+que\s+se\s+trata\b|sempre\s+passas\s+por\s+ca\b|'
    r'passas\s+por\s+ca\b|o\s+mais\s+breve\s+possivel\b|da\s+vossa\s+parte\b|'
    r'da[-\s]?me\s+feedback\b|template\s+para\s+a\s+parte\s+comercial\b|'
    r'pediu\s+para\s+o\s+elucidar\b|quais\s+os\s+requisitos\b|'
    r'que\s+custos\s+financeiros\s+implic\w+\b|o\s+email\s+a\s+monitorizar\b|'
    r'fiquei\s+de\s+lhe\s+enviar\b|email\s+informativo\s+sobre\s+este\s+assunto\b)\b',
    re.IGNORECASE,
)
ACTION_SCOPE_LEAD_RE = re.compile(
    r'\b(?:alterar|associar|configurar|confirmar|consolidar|corrigir|criar|desenvolver|'
    r'formar|garantir|importa(?:r|cao)|incluir|instalar|integrar|investigar|migrar|'
    r'possibilitar|preparar|re[-\s]?importa(?:r|cao)|registar|substituir|testar|validar|'
    r'verificar|acrescentar|anali(?:sar|zar)|anliasar|pedir|questionar|sugerir|eliminar)\b',
    re.IGNORECASE,
)
SAFE_SCOPE_SPLIT_RE = re.compile(
    r'\s*(?:;\s+|\s+\|\s+|[•·]\s*|\n+|(?<=\.)\s+(?=(?:alterar|associar|configurar|confirmar|'
    r'consolidar|corrigir|criar|desenvolver|formar|garantir|importa(?:r|cao)|incluir|'
    r'instalar|integrar|investigar|migrar|possibilitar|preparar|re[-\s]?importa(?:r|cao)|'
    r'registar|substituir|testar|validar|verificar|acrescentar|anali(?:sar|zar)|anliasar|'
    r'pedir|questionar|sugerir|eliminar)\b))',
    re.IGNORECASE,
)
CAPITALIZED_ACTION_SPLIT_RE = re.compile(
    r'\s+(?=(?:Alterar|Associar|Configurar|Confirmar|Consolidar|Corrigir|Criar|Desenvolver|'
    r'Formar|Garantir|Importa(?:r|cao|ção)|Incluir|Instalar|Integrar|Investigar|Migrar|'
    r'Possibilitar|Preparar|Re[-\s]?importa(?:r|cao|ção)|Registar|Substituir|Testar|'
    r'Validar|Verificar|Acrescentar|Anali(?:sar|zar)|Anliasar|Pedir|Questionar|Sugerir|Eliminar)\b)'
)
CONTEXTUAL_ACTION_SPLIT_RE = re.compile(
    r'\s+(?=(?:Ao\s+(?:confirmar|finalizar|importar|criar|registar|validar)|'
    r'Antes\s+de\s+(?:importar|confirmar|criar|validar))\b)'
)
LEADING_SCOPE_LABEL_PREFIX_RE = re.compile(
    r'^(?:(?:whats?app(?:\s+business)?|email|mail|crm|vendas|compras)\s+)+'
    r'(?=(?:alterar|associar|configurar|confirmar|consolidar|corrigir|criar|desenvolver|'
    r'formar|garantir|importa(?:r|cao)|incluir|instalar|integrar|investigar|migrar|'
    r'possibilitar|preparar|re[-\s]?importa(?:r|cao)|registar|substituir|testar|validar|'
    r'verificar|acrescentar|anali(?:sar|zar)|anliasar|pedir|questionar|sugerir|eliminar)\b)',
    re.IGNORECASE,
)
MOJIBAKE_HINTS = ('Ãƒ', 'Ã‚', 'Ã¢', 'Ã¯Â¿Â½', 'ÃŒ')
STATUS_WORKFLOW_PREFIXES = (
    'review this draft',
    'apply the draft',
    'publish a fresh manual status snapshot',
    'latest status publication status:',
    'latest scope sync status:',
    'no status snapshot has been published yet',
    'no scope snapshot has been published yet',
    'operational status changed since the last manual publication',
    'the published operational status may be stale',
)
LOW_SIGNAL_ATTACHMENT_NAME_RE = re.compile(
    r'^(?:image|imagem|img|photo|foto|scan|screenshot|captura|anexo|attachment|documento|document)[\s._-]*\d+(?:\.(?:png|jpe?g|gif|pdf))?$',
    re.IGNORECASE,
)
CONTACT_METADATA_TOKEN_PATTERNS = (
    r'\bimage\b',
    r'\bimagem\b',
    r'\bimg\b',
    r'\bmail\b',
    r'\bemail\b',
    r'\bmailto\b',
    r'\btel\b',
    r'\btelefone\b',
    r'\btlm\b',
    r'\btelemovel\b',
    r'\bwhatsapp\b',
    r'\bcontacto\b',
    r'\bcontact\b',
    r'\bunidade\d*\b',
    r'\bmorada\b',
    r'\brua\b',
    r'\bavenida\b',
    r'\bmaps\.app\.goo\.gl\b',
    r'\bnif\b',
    r'\blda\b',
    r'\bltd\b',
    r'\bsa\b',
)
FACTUAL_SCOPE_HINT_RE = re.compile(
    r'\b(?:crm|website|whats?app|comercial|contabilidade|go[\s-]?live|template|orcament\w*|'
    r'inventari\w*|categoria\w*|artig\w*|client\w*|forneced\w*|produ\w*|expedi\w*|'
    r'encomend\w*|projet\w*|odoo|stock\w*|ordem\w*|venda\w*|compr\w*|solidworks|'
    r'consum\w*|sobr\w*|mapeamento|campo|centro(?:s)?\s+de\s+trabalho|tablet\w*|'
    r'utilizador\w*|perfil\w*|integra\w*|importa\w*|registo\s+verificado|'
    r'informacao\s+complementar|lista\s+de\s+materiais)\b',
    re.IGNORECASE,
)

SCOPE_ITEM_INCLUDED = 'included'
SCOPE_ITEM_FACTUAL_BUT_NEEDS_CURATION = 'factual_but_needs_curation'
SCOPE_ITEM_EXCLUDED_NOISE = 'excluded_noise'

SCOPE_CLASSIFICATION_REASON_LABELS = {
    'included': 'Incluido',
    'safe_split_available': 'Segmentacao segura disponivel',
    'weak_nominal_item': 'Item nominal fraco',
    'compound_item': 'Item composto',
    'insufficient_detail': 'Detalhe insuficiente',
    'needs_manual_scope_curation': 'Curadoria manual necessaria',
    'technical_noise': 'Ruido tecnico',
    'non_factual': 'Item nao factual',
    'conversational_follow_up': 'Follow-up conversacional',
    'empty_or_collapsed': 'Item vazio ou colapsado',
}


def format_scope_reason_summary(reason_counts, limit=4):
    if not reason_counts:
        return False
    ordered_reasons = sorted(
        reason_counts.items(),
        key=lambda item: (-int(item[1] or 0), item[0]),
    )
    return ', '.join(
        "%s: %s" % (scope_classification_reason_label(reason), int(count or 0))
        for reason, count in ordered_reasons[:limit]
    ) or False


def build_scope_quality_feedback(
    included_scope_count,
    factual_scope_backlog_count,
    factual_scope_backlog_reason_counts=None,
    excluded_noise_count=0,
    excluded_noise_reason_counts=None,
):
    factual_scope_backlog_reason_summary = format_scope_reason_summary(
        factual_scope_backlog_reason_counts or {}
    )
    excluded_noise_reason_summary = format_scope_reason_summary(
        excluded_noise_reason_counts or {}
    )
    factual_scope_backlog_feedback = (
        "Itens factuais pendentes de curadoria: %s. Motivos dominantes: %s."
        % (int(factual_scope_backlog_count or 0), factual_scope_backlog_reason_summary or 'n/a')
        if factual_scope_backlog_count
        else False
    )
    excluded_noise_feedback = (
        "Ruido excluido do scope curado: %s. Motivos dominantes: %s."
        % (int(excluded_noise_count or 0), excluded_noise_reason_summary or 'n/a')
        if excluded_noise_count
        else False
    )
    scope_signal_lines = [
        "Ambito curado pronto no espelho: %s item(s)." % int(included_scope_count or 0),
        "Itens factuais pendentes de curadoria no Odoo: %s." % int(factual_scope_backlog_count or 0),
        "Ruido excluido na curadoria: %s." % int(excluded_noise_count or 0),
    ]
    if factual_scope_backlog_count:
        scope_signal_lines.append(
            "Motivos dominantes para backlog factual: %s."
            % (factual_scope_backlog_reason_summary or 'n/a')
        )
        scope_signal_lines.append(
            "Acao recomendada ao gestor: clarificar estes itens no Odoo antes de os promover ao ambito principal."
        )
    return {
        'factual_scope_backlog_reason_summary': factual_scope_backlog_reason_summary,
        'factual_scope_backlog_feedback': factual_scope_backlog_feedback,
        'excluded_noise_reason_summary': excluded_noise_reason_summary,
        'excluded_noise_feedback': excluded_noise_feedback,
        'scope_signal_feedback': ' '.join(scope_signal_lines),
    }


def _normalize_line_endings(value):
    return (value or '').replace('\r\n', '\n').replace('\r', '\n')


def _mojibake_score(value):
    text = value or ''
    score = 0
    for hint in MOJIBAKE_HINTS:
        score += text.count(hint)
    return score


def repair_mojibake(value):
    text = value or ''
    if not _mojibake_score(text):
        return text

    best_text = text
    best_score = _mojibake_score(text)
    improved = True
    while improved and best_score:
        improved = False
        for source_encoding in ('latin1', 'cp1252'):
            try:
                candidate = best_text.encode(source_encoding).decode('utf-8')
            except (UnicodeDecodeError, UnicodeEncodeError):
                continue
            candidate_score = _mojibake_score(candidate)
            if candidate_score < best_score:
                best_text = candidate
                best_score = candidate_score
                improved = True
    return best_text


def has_suspicious_mojibake(value):
    text = repair_mojibake(value or '')
    return _mojibake_score(text) >= 2 or '\ufffd' in text


def safe_truncate(value, max_chars):
    text = (value or '').strip()
    if not max_chars or len(text) <= max_chars:
        return text
    if max_chars <= 3:
        return text[:max_chars]
    return text[: max_chars - 3].rstrip(' ,;:\n') + '...'


def fold_text_for_matching(value):
    text = repair_mojibake(value or '')
    if not text:
        return ''
    folded = unicodedata.normalize('NFKD', text)
    return ''.join(char for char in folded if not unicodedata.combining(char)).lower()


def is_placeholder_text(value):
    return bool(PLACEHOLDER_LINE_RE.match((value or '').strip()))


def is_channel_label_only(raw_value, cleaned_value=''):
    cleaned_text = cleaned_value or normalize_inline_text(raw_value, fallback='', max_chars=False, drop_placeholders=True)
    if not cleaned_text:
        return True
    return bool(CHANNEL_LABEL_ONLY_RE.match(fold_text_for_matching(cleaned_text)))


def is_contact_or_asset_metadata_dominated(raw_value, cleaned_value=''):
    raw_text = repair_mojibake(raw_value or '')
    cleaned_text = cleaned_value or normalize_inline_text(raw_text, fallback='', max_chars=False, drop_placeholders=True)
    if not cleaned_text:
        return True

    folded = ' '.join(
        value for value in (fold_text_for_matching(raw_text), fold_text_for_matching(cleaned_text)) if value
    )
    tokens = [token for token in re.split(r'[\W_]+', folded) if token]
    if not tokens:
        return True

    metadata_hits = sum(1 for pattern in CONTACT_METADATA_TOKEN_PATTERNS if re.search(pattern, folded))
    has_contact_hint = bool(
        re.search(r'\b(?:mail|email|mailto|tel|telefone|tlm|telemovel|whatsapp|contacto|contact|maps\.app\.goo\.gl)\b', folded)
    )
    has_location_hint = bool(re.search(r'\b(?:unidade\d*|morada|rua|avenida|nif)\b', folded))
    has_asset_hint = bool(re.search(r'\b(?:image|imagem|img)\b', folded))
    has_legal_entity_hint = bool(re.search(r'\b(?:lda|ltd|sa)\b', folded))

    if metadata_hits >= 4:
        return True
    if metadata_hits >= 3 and len(tokens) <= 18:
        return True
    if ADDRESS_FRAGMENT_RE.match(cleaned_text) and len(tokens) <= 12 and not ACTION_SCOPE_LEAD_RE.search(folded):
        return True
    if has_location_hint and len(tokens) <= 8 and not ACTION_SCOPE_LEAD_RE.search(folded):
        return True
    if INLINE_EMAIL_RE.search(raw_text) and len(tokens) <= 10 and not ACTION_SCOPE_LEAD_RE.search(folded):
        return True
    if len(tokens) <= 18 and (
        (has_contact_hint and has_location_hint)
        or (has_asset_hint and has_contact_hint)
        or (has_legal_entity_hint and (has_contact_hint or has_location_hint))
    ):
        return True
    return False


def has_factual_scope_hint(raw_value, cleaned_value=''):
    cleaned_text = cleaned_value or normalize_inline_text(raw_value, fallback='', max_chars=False, drop_placeholders=True)
    if not cleaned_text:
        return False
    folded = ' '.join(
        value for value in (fold_text_for_matching(raw_value or ''), fold_text_for_matching(cleaned_text)) if value
    )
    if not folded:
        return False
    if ACTION_SCOPE_LEAD_RE.search(folded):
        return True
    return bool(FACTUAL_SCOPE_HINT_RE.search(folded))


def is_factual_contact_or_location_reference(raw_value, cleaned_value=''):
    raw_text = repair_mojibake(raw_value or '')
    cleaned_text = cleaned_value or normalize_inline_text(raw_text, fallback='', max_chars=False, drop_placeholders=True)
    if not cleaned_text:
        return False
    folded = ' '.join(
        value for value in (fold_text_for_matching(raw_text), fold_text_for_matching(cleaned_text)) if value
    )
    tokens = [token for token in re.split(r'[\W_]+', folded) if token]
    if not tokens:
        return False

    has_email = bool(INLINE_EMAIL_RE.search(raw_text) or INLINE_EMAIL_RE.search(cleaned_text))
    has_address = bool(ADDRESS_FRAGMENT_RE.match(cleaned_text) or re.search(r'\b(?:rua|avenida|av\b|travessa|alameda|bairro|morada|freamunde)\b', folded))
    has_legal_entity = bool(re.search(r'\b(?:lda|ltd|sa)\b', folded))
    has_person_like_name = _looks_like_person_or_label_name(cleaned_text)
    has_contact_location_mix = is_contact_or_asset_metadata_dominated(raw_text, cleaned_text)

    if has_contact_location_mix and (has_email or has_address or has_legal_entity):
        return True
    if has_email and len(tokens) <= 12:
        return True
    if has_address and len(tokens) <= 14 and not ACTION_SCOPE_LEAD_RE.search(folded):
        return True
    if has_legal_entity and len(tokens) <= 8 and not ACTION_SCOPE_LEAD_RE.search(folded):
        return True
    if has_person_like_name and len(tokens) <= 4 and not has_factual_scope_hint(raw_text, cleaned_text):
        return True
    return False


def is_factual_follow_up_scope_summary(raw_value, cleaned_value=''):
    raw_text = repair_mojibake(raw_value or '')
    cleaned_text = cleaned_value or normalize_inline_text(raw_text, fallback='', max_chars=False, drop_placeholders=True)
    if not cleaned_text:
        return False
    if not is_conversational_follow_up_scope_summary(raw_text, cleaned_text):
        return False
    folded = fold_text_for_matching(cleaned_text)
    if any(
        token in folded
        for token in (
            'template',
            'website',
            'comercial',
            'whatsapp',
            'custos',
            'requisitos',
            'crm',
            'orcament',
            'inventari',
        )
    ):
        return True
    return has_factual_scope_hint(raw_text, cleaned_text)


def is_weak_scope_heading(raw_value, cleaned_value=''):
    cleaned_text = cleaned_value or normalize_inline_text(raw_value, fallback='', max_chars=False, drop_placeholders=True)
    if not cleaned_text:
        return True
    folded_cleaned = fold_text_for_matching(cleaned_text)
    tokens = [token for token in re.split(r'[\W_]+', folded_cleaned) if token]
    if not tokens:
        return True
    if GENERIC_SCOPE_HEADING_RE.match(folded_cleaned):
        return True
    if len(tokens) == 1 and len(tokens[0]) <= 4:
        return True
    return False


def _scope_tokens(value):
    return [token for token in re.split(r'[\W_]+', fold_text_for_matching(value)) if token]


def scope_classification_reason_label(reason):
    return SCOPE_CLASSIFICATION_REASON_LABELS.get(reason, 'Curadoria manual necessaria')


def _looks_like_person_or_label_name(cleaned_text):
    tokens = [token for token in (cleaned_text or '').split() if token]
    if len(tokens) not in (2, 3):
        return False
    if any(re.search(r'\d', token) for token in tokens):
        return False
    if any('-' in token for token in tokens):
        return False
    if not all(token[:1].isupper() and token[1:].islower() for token in tokens):
        return False
    return True


def is_weak_nominal_scope_item(raw_value, cleaned_value=''):
    cleaned_text = cleaned_value or normalize_inline_text(raw_value, fallback='', max_chars=False, drop_placeholders=True)
    if not cleaned_text:
        return True
    folded_cleaned = fold_text_for_matching(cleaned_text)
    tokens = _scope_tokens(cleaned_text)
    if not tokens:
        return True
    if WEAK_NOMINAL_SCOPE_EXACT_RE.match(folded_cleaned):
        return True
    if WEAK_NOMINAL_SCOPE_PATTERN_RE.match(folded_cleaned):
        return True
    if any(token in {'lda', 'ltd', 'sa'} for token in tokens) and len(tokens) <= 4 and not ACTION_SCOPE_LEAD_RE.search(folded_cleaned):
        return True
    if _looks_like_person_or_label_name(cleaned_text):
        return True
    if DANGLING_SCOPE_FRAGMENT_RE.match(cleaned_text):
        return True
    if len(tokens) <= 2 and not ACTION_SCOPE_LEAD_RE.search(folded_cleaned) and (
        cleaned_text == cleaned_text.title() or cleaned_text == cleaned_text.lower()
    ):
        return True
    return False


def _split_scope_fragments(cleaned_text):
    fragments = [fragment.strip(' ,;:-') for fragment in SAFE_SCOPE_SPLIT_RE.split(cleaned_text or '') if fragment.strip(' ,;:-')]
    if len(fragments) > 1:
        return fragments
    fragments = [
        fragment.strip(' ,;:-')
        for fragment in CAPITALIZED_ACTION_SPLIT_RE.split(cleaned_text or '')
        if fragment.strip(' ,;:-')
    ]
    if len(fragments) > 1:
        return fragments
    return [
        fragment.strip(' ,;:-')
        for fragment in CONTEXTUAL_ACTION_SPLIT_RE.split(cleaned_text or '')
        if fragment.strip(' ,;:-')
    ]


def strip_scope_leading_label_prefix(value):
    text = normalize_inline_text(value, fallback='', max_chars=False, drop_placeholders=True)
    if not text:
        return ''
    previous = None
    while text != previous:
        previous = text
        text = LEADING_SCOPE_LABEL_PREFIX_RE.sub('', text).strip()
    return text


def has_safe_scope_split_boundary(raw_value, cleaned_value=''):
    cleaned_text = cleaned_value or strip_inline_email_noise(raw_value, max_chars=False)
    cleaned_text = normalize_inline_text(cleaned_text, fallback='', max_chars=False, drop_placeholders=True)
    if not cleaned_text:
        return False
    return len(_split_scope_fragments(cleaned_text)) > 1


def is_compound_scope_summary(raw_value, cleaned_value=''):
    cleaned_text = cleaned_value or strip_inline_email_noise(raw_value, max_chars=False)
    cleaned_text = normalize_inline_text(cleaned_text, fallback='', max_chars=False, drop_placeholders=True)
    if not cleaned_text:
        return False

    if has_safe_scope_split_boundary(raw_value, cleaned_text):
        return True

    tokens = _scope_tokens(cleaned_text)
    if len(tokens) < 8:
        return False
    action_hits = len(ACTION_SCOPE_LEAD_RE.findall(fold_text_for_matching(cleaned_text)))
    if action_hits >= 3:
        return True
    if action_hits >= 2 and len(tokens) >= 18 and ' notas' in (' ' + fold_text_for_matching(cleaned_text)):
        return True
    return False


def is_conversational_follow_up_scope_summary(raw_value, cleaned_value=''):
    cleaned_text = cleaned_value or strip_inline_email_noise(raw_value, max_chars=False)
    cleaned_text = normalize_inline_text(cleaned_text, fallback='', max_chars=False, drop_placeholders=True)
    if not cleaned_text:
        return False
    folded_cleaned = fold_text_for_matching(cleaned_text)
    if CONVERSATIONAL_FOLLOW_UP_PREFIX_RE.match(folded_cleaned):
        return True
    if CONVERSATIONAL_FOLLOW_UP_FRAGMENT_RE.search(folded_cleaned):
        return True
    if cleaned_text.endswith('?') and not ACTION_SCOPE_LEAD_RE.search(folded_cleaned):
        return True
    return False


def strip_inline_markup(value):
    text = repair_mojibake(value or '')
    if not text:
        return ''
    previous = None
    while text != previous:
        previous = text
        text = INLINE_MARKUP_RE.sub(r'\1', text)
    text = re.sub(r'(?<!\w)[*_`]+(?=\w)', '', text)
    text = re.sub(r'(?<=\w)[*_`]+(?=\s|$)', '', text)
    text = re.sub(r'\s+([,.;:])', r'\1', text)
    return text


def normalize_inline_text(value, fallback='', max_chars=False, drop_placeholders=False):
    text = strip_inline_markup(value or '')
    text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    if drop_placeholders and is_placeholder_text(text):
        text = ''
    text = safe_truncate(text, max_chars)
    if text:
        return text
    return fallback if fallback is not None else ''


def _strip_reply_lines(lines):
    sanitized = []
    for line in lines:
        stripped = (line or '').strip()
        if not stripped:
            sanitized.append('')
            continue
        if stripped.startswith('>'):
            if sanitized:
                break
            continue
        if REPLY_WROTE_RE.match(stripped) or REPLY_HEADER_RE.match(stripped) or REPLY_SEPARATOR_RE.match(stripped):
            break
        sanitized.append(stripped)
    return sanitized


def _strip_signature_lines(lines):
    sanitized = []
    meaningful_lines = 0
    for line in lines:
        stripped = (line or '').strip()
        if not stripped:
            sanitized.append('')
            continue
        if meaningful_lines and (SIGNATURE_MARKER_RE.match(stripped) or LEGAL_DISCLAIMER_MARKER_RE.match(stripped)):
            break
        sanitized.append(stripped)
        meaningful_lines += 1
    return sanitized


def _sanitize_lines(value, from_html=False, strip_email_noise=False, max_line_chars=False, max_items=False):
    text = html2plaintext(value or '') if from_html else (value or '')
    text = repair_mojibake(text)
    lines = _normalize_line_endings(text).split('\n')
    if strip_email_noise:
        lines = _strip_reply_lines(lines)
        lines = _strip_signature_lines(lines)

    result = []
    seen = set()
    for raw_line in lines:
        candidate = raw_line.strip(' -*\t')
        if strip_email_noise:
            candidate = strip_inline_email_noise(candidate, max_chars=False)
        normalized = normalize_inline_text(
            candidate,
            fallback='',
            max_chars=max_line_chars,
            drop_placeholders=True,
        )
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
        if max_items and len(result) >= max_items:
            break
    return result


def strip_inline_email_noise(value, max_chars=False):
    text = repair_mojibake(value or '')
    text = _normalize_line_endings(text)
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        return ''

    text = INLINE_QUOTE_PREFIX_RE.sub('', text)
    legal_disclaimer_match = LEGAL_DISCLAIMER_MARKER_RE.search(text)
    if legal_disclaimer_match:
        text = text[:legal_disclaimer_match.start()].rstrip(' ,;:-')
    text = INLINE_REPLY_RE.sub('', text).strip()
    text = INLINE_MAIL_MESSAGE_RE.sub(' ', text)
    text = INLINE_ODOO_ASSET_RE.sub(' ', text)
    text = INLINE_URL_RE.sub(' ', text)
    text = INLINE_REFERENCE_TOKEN_RE.sub(' ', text)
    text = INLINE_SIGNATURE_RE.sub('', text).strip(' ,;:-')
    text = INLINE_ASSET_TOKEN_RE.sub(' ', text)
    text = INLINE_PHONE_RE.sub(' ', text)
    contact_match = INLINE_CONTACT_MARKER_RE.search(text)
    if contact_match:
        text = text[:contact_match.start()].rstrip(' ,;:-')
    text = WHATSAPP_ARROW_RE.sub('', text)
    text = re.sub(r'\s+', ' ', text).strip(' ,;:-')
    if INLINE_DANGLING_CONNECTOR_RE.match(text):
        text = ''
    return safe_truncate(text, max_chars)


def is_low_signal_scope_summary(raw_value, cleaned_value=''):
    raw_text = repair_mojibake(raw_value or '')
    cleaned_text = cleaned_value or strip_inline_email_noise(raw_text)
    cleaned_text = strip_scope_leading_label_prefix(cleaned_text)
    cleaned_text = normalize_inline_text(cleaned_text, fallback='', max_chars=False, drop_placeholders=True)
    if not cleaned_text:
        return True
    folded_cleaned = fold_text_for_matching(cleaned_text)
    tokens = [token for token in re.split(r'[\W_]+', cleaned_text.lower()) if token]
    if not tokens:
        return True
    if len(tokens) == 1 and len(tokens[0]) <= 3:
        return True
    if LOW_SIGNAL_SCOPE_EXACT_RE.match(folded_cleaned):
        return True
    if LOW_SIGNAL_SCOPE_PATTERN_RE.match(folded_cleaned):
        return True
    if is_channel_label_only(raw_text, cleaned_text):
        return True
    if is_contact_or_asset_metadata_dominated(raw_text, cleaned_text):
        return True
    if is_weak_scope_heading(raw_text, cleaned_text):
        return True
    if is_weak_nominal_scope_item(raw_text, cleaned_text):
        return True
    if ATTACHMENT_FILENAME_RE.search(cleaned_text) and len(tokens) <= 6:
        return True
    if INLINE_PHONE_RE.search(cleaned_text):
        text_without_phone = INLINE_PHONE_RE.sub(' ', cleaned_text)
        text_without_phone = normalize_inline_text(text_without_phone, fallback='', max_chars=False, drop_placeholders=True)
        if not text_without_phone or INLINE_DANGLING_CONNECTOR_RE.match(text_without_phone):
            return True

    lowered_raw = raw_text.lower()
    lowered_cleaned = cleaned_text.lower()
    noise_hits = 0
    for needle in (
        'com os melhores cumprimentos',
        'best regards',
        'cumprimentos',
        'atenciosamente',
        'image [',
        'imagem [',
        'none [',
        'mail:',
        'tel.',
        'tel:',
        'tlm.',
        'tlm:',
        'unidade1',
        'unidade2',
        'maps.app.goo.gl',
        'chamada para rede',
    ):
        if needle in lowered_raw:
            noise_hits += 1

    if lowered_cleaned.startswith('com os melhores cumprimentos'):
        return True
    if lowered_cleaned.startswith('bom dia') or lowered_cleaned.startswith('boa tarde'):
        return True
    if INLINE_GREETING_RE.match(cleaned_text) and (noise_hits or '?' in cleaned_text):
        return True
    if noise_hits and len(cleaned_text.split()) <= 2 and len(cleaned_text) < 18:
        return True
    if noise_hits >= 3 and len(cleaned_text.split()) <= 20:
        return True
    if not re.search(r'[A-Za-zÀ-ÿ]', cleaned_text):
        return True
    return False


def is_technical_noise_scope_summary(raw_value, cleaned_value=''):
    raw_text = repair_mojibake(raw_value or '')
    cleaned_text = cleaned_value or strip_inline_email_noise(raw_text, max_chars=False)
    cleaned_text = strip_scope_leading_label_prefix(cleaned_text)
    cleaned_text = normalize_inline_text(cleaned_text, fallback='', max_chars=False, drop_placeholders=True)
    if not cleaned_text:
        return True

    folded_cleaned = fold_text_for_matching(cleaned_text)
    tokens = [token for token in re.split(r'[\W_]+', cleaned_text.lower()) if token]
    if LOW_SIGNAL_SCOPE_EXACT_RE.match(folded_cleaned):
        return True
    if is_channel_label_only(raw_text, cleaned_text):
        return True
    if is_contact_or_asset_metadata_dominated(raw_text, cleaned_text):
        return True
    if folded_cleaned in {'whatsapp', 'email', 'mail', 'template'}:
        return True
    if is_weak_scope_heading(raw_text, cleaned_text) and len(tokens) <= 2:
        return True
    if ATTACHMENT_FILENAME_RE.search(cleaned_text) and len(tokens) <= 8:
        return True
    if INLINE_PHONE_RE.search(cleaned_text):
        text_without_phone = INLINE_PHONE_RE.sub(' ', cleaned_text)
        text_without_phone = normalize_inline_text(text_without_phone, fallback='', max_chars=False, drop_placeholders=True)
        if not text_without_phone or INLINE_DANGLING_CONNECTOR_RE.match(text_without_phone):
            return True
    if not re.search(r'[a-z]', folded_cleaned):
        return True
    return False


def is_non_factual_scope_summary(raw_value, cleaned_value=''):
    raw_text = repair_mojibake(raw_value or '')
    cleaned_text = cleaned_value or strip_inline_email_noise(raw_text, max_chars=False)
    cleaned_text = strip_scope_leading_label_prefix(cleaned_text)
    cleaned_text = normalize_inline_text(cleaned_text, fallback='', max_chars=False, drop_placeholders=True)
    if not cleaned_text:
        return True

    lowered_raw = fold_text_for_matching(raw_text)
    lowered_cleaned = fold_text_for_matching(cleaned_text)
    if any(token in lowered_raw or token in lowered_cleaned for token in NON_FACTUAL_SCOPE_NOISE_TOKENS):
        return True
    if NON_FACTUAL_SCOPE_PREFIX_RE.match(lowered_cleaned):
        return True
    if NON_FACTUAL_SCOPE_FRAGMENT_RE.search(lowered_cleaned):
        return True
    if is_conversational_follow_up_scope_summary(raw_text, cleaned_text):
        return True
    return False


def classify_scope_item(value, max_chars=False):
    raw_text = repair_mojibake(value or '')
    normalized_raw_text = normalize_inline_text(raw_text, fallback='', max_chars=False, drop_placeholders=True)
    cleaned_text = strip_inline_email_noise(raw_text, max_chars=False)
    cleaned_text = strip_scope_leading_label_prefix(cleaned_text)
    cleaned_text = normalize_inline_text(cleaned_text, fallback='', max_chars=False, drop_placeholders=True)

    result = {
        'state': SCOPE_ITEM_EXCLUDED_NOISE,
        'reason': 'empty_or_collapsed',
        'reason_label': scope_classification_reason_label('empty_or_collapsed'),
        'raw_item': raw_text,
        'normalized_raw_item': normalized_raw_text,
        'normalized_item': '',
        'publication_candidates': [],
        'has_safe_split_boundary': False,
        'needs_hygiene': bool(normalized_raw_text),
    }
    if not cleaned_text:
        return result

    result['normalized_item'] = safe_truncate(cleaned_text, max_chars)
    result['needs_hygiene'] = cleaned_text != normalized_raw_text
    result['has_safe_split_boundary'] = has_safe_scope_split_boundary(raw_text, cleaned_text)

    if is_conversational_follow_up_scope_summary(raw_text, cleaned_text):
        if is_factual_follow_up_scope_summary(raw_text, cleaned_text):
            result['state'] = SCOPE_ITEM_FACTUAL_BUT_NEEDS_CURATION
            result['reason'] = 'needs_manual_scope_curation'
            result['reason_label'] = scope_classification_reason_label('needs_manual_scope_curation')
            return result
        result['reason'] = 'conversational_follow_up'
        result['reason_label'] = scope_classification_reason_label('conversational_follow_up')
        return result
    if is_technical_noise_scope_summary(raw_text, cleaned_text):
        if is_factual_contact_or_location_reference(raw_text, cleaned_text) or has_factual_scope_hint(raw_text, cleaned_text):
            result['state'] = SCOPE_ITEM_FACTUAL_BUT_NEEDS_CURATION
            result['reason'] = 'needs_manual_scope_curation'
            result['reason_label'] = scope_classification_reason_label('needs_manual_scope_curation')
            return result
        result['reason'] = 'technical_noise'
        result['reason_label'] = scope_classification_reason_label('technical_noise')
        return result
    if is_non_factual_scope_summary(raw_text, cleaned_text):
        if is_factual_contact_or_location_reference(raw_text, cleaned_text) or has_factual_scope_hint(raw_text, cleaned_text):
            result['state'] = SCOPE_ITEM_FACTUAL_BUT_NEEDS_CURATION
            result['reason'] = 'needs_manual_scope_curation'
            result['reason_label'] = scope_classification_reason_label('needs_manual_scope_curation')
            return result
        result['reason'] = 'non_factual'
        result['reason_label'] = scope_classification_reason_label('non_factual')
        return result

    if result['has_safe_split_boundary']:
        candidates = []
        for fragment in _split_scope_fragments(cleaned_text):
            candidate = sanitize_scope_publication_candidate(fragment, max_chars=max_chars)
            if candidate and candidate not in candidates:
                candidates.append(candidate)
        if candidates:
            result['state'] = SCOPE_ITEM_INCLUDED
            result['reason'] = 'safe_split_available' if len(candidates) > 1 else 'included'
            result['reason_label'] = scope_classification_reason_label(result['reason'])
            result['publication_candidates'] = candidates
            return result

    if is_compound_scope_summary(raw_text, cleaned_text):
        result['state'] = SCOPE_ITEM_FACTUAL_BUT_NEEDS_CURATION
        result['reason'] = 'compound_item'
        result['reason_label'] = scope_classification_reason_label('compound_item')
        return result
    if is_weak_nominal_scope_item(raw_text, cleaned_text) or is_weak_scope_heading(raw_text, cleaned_text):
        result['state'] = SCOPE_ITEM_FACTUAL_BUT_NEEDS_CURATION
        result['reason'] = 'weak_nominal_item'
        result['reason_label'] = scope_classification_reason_label('weak_nominal_item')
        return result
    if is_low_signal_scope_summary(raw_text, cleaned_text):
        result['state'] = SCOPE_ITEM_FACTUAL_BUT_NEEDS_CURATION
        result['reason'] = 'insufficient_detail'
        result['reason_label'] = scope_classification_reason_label('insufficient_detail')
        return result

    result['state'] = SCOPE_ITEM_INCLUDED
    result['reason'] = 'included'
    result['reason_label'] = scope_classification_reason_label('included')
    result['publication_candidates'] = [result['normalized_item']] if result['normalized_item'] else []
    return result


def sanitize_scope_publication_candidate(value, max_chars=False):
    raw_text = repair_mojibake(value or '')
    cleaned_text = strip_inline_email_noise(raw_text, max_chars=False)
    cleaned_text = strip_scope_leading_label_prefix(cleaned_text)
    cleaned_text = normalize_inline_text(cleaned_text, fallback='', max_chars=False, drop_placeholders=True)
    if not cleaned_text:
        return ''
    if is_technical_noise_scope_summary(raw_text, cleaned_text):
        return ''
    if is_low_signal_scope_summary(raw_text, cleaned_text):
        return ''
    if is_non_factual_scope_summary(raw_text, cleaned_text):
        return ''
    if is_weak_nominal_scope_item(raw_text, cleaned_text):
        return ''
    if DANGLING_SCOPE_FRAGMENT_RE.match(cleaned_text):
        return ''
    if is_conversational_follow_up_scope_summary(raw_text, cleaned_text):
        return ''
    if is_compound_scope_summary(raw_text, cleaned_text) and not has_safe_scope_split_boundary(raw_text, cleaned_text):
        return ''
    return safe_truncate(cleaned_text, max_chars)


def split_scope_publication_candidates(value, max_items=False, max_chars=False):
    raw_text = repair_mojibake(value or '')
    cleaned_text = strip_inline_email_noise(raw_text, max_chars=False)
    cleaned_text = strip_scope_leading_label_prefix(cleaned_text)
    cleaned_text = normalize_inline_text(cleaned_text, fallback='', max_chars=False, drop_placeholders=True)
    if not cleaned_text:
        return []

    values = []
    fragments = _split_scope_fragments(cleaned_text) if has_safe_scope_split_boundary(raw_text, cleaned_text) else [cleaned_text]
    for fragment in fragments:
        candidate = sanitize_scope_publication_candidate(fragment, max_chars=max_chars)
        if not candidate or candidate in values:
            continue
        values.append(candidate)
        if max_items and len(values) >= max_items:
            return values

    if values:
        return values
    if is_compound_scope_summary(raw_text, cleaned_text):
        return []
    candidate = sanitize_scope_publication_candidate(cleaned_text, max_chars=max_chars)
    return [candidate] if candidate else []


def curate_scope_publication_lines(values, max_items=False, max_chars=False):
    curated = []
    for value in values or []:
        for candidate in split_scope_publication_candidates(value, max_chars=max_chars):
            if not candidate or candidate in curated:
                continue
            curated.append(candidate)
            if max_items and len(curated) >= max_items:
                return curated
    return curated


def is_low_signal_attachment_name(value):
    cleaned_text = normalize_inline_text(value, fallback='', max_chars=False, drop_placeholders=True)
    if not cleaned_text:
        return True
    folded_cleaned = fold_text_for_matching(cleaned_text)
    if LOW_SIGNAL_ATTACHMENT_NAME_RE.match(folded_cleaned):
        return True
    if ATTACHMENT_FILENAME_RE.search(cleaned_text):
        basename = cleaned_text.rsplit('.', 1)[0]
        basename_tokens = [token for token in re.split(r'[\W_]+', fold_text_for_matching(basename)) if token]
        if basename_tokens and all(
            token in {'image', 'imagem', 'img', 'photo', 'foto', 'scan', 'screenshot', 'captura', 'anexo', 'attachment', 'documento', 'document'}
            or token.isdigit()
            for token in basename_tokens
        ):
            return True
    return False


def filter_status_workflow_lines(items):
    filtered = []
    for item in items or []:
        normalized = normalize_inline_text(item, fallback='', max_chars=False, drop_placeholders=True)
        lowered = normalized.lower()
        if not normalized:
            continue
        if any(lowered.startswith(prefix) for prefix in STATUS_WORKFLOW_PREFIXES):
            continue
        filtered.append(normalized)
    return filtered


def sanitize_status_summary(value, max_chars=False):
    text = repair_mojibake(value or '')
    sentences = re.split(r'(?<=[\.\!\?])\s+', text)
    filtered = []
    for sentence in sentences:
        normalized = normalize_inline_text(sentence, fallback='', max_chars=False, drop_placeholders=True)
        lowered = normalized.lower()
        if not normalized:
            continue
        if any(lowered.startswith(prefix) for prefix in STATUS_WORKFLOW_PREFIXES):
            continue
        filtered.append(normalized)
    return normalize_inline_text(' '.join(filtered), fallback='', max_chars=max_chars, drop_placeholders=True)


def sanitize_message_body(value, max_chars=1200):
    text = ' '.join(
        _sanitize_lines(
            value,
            from_html=True,
            strip_email_noise=True,
            max_line_chars=280,
        )
    )
    return normalize_inline_text(text, fallback='', max_chars=max_chars, drop_placeholders=True)


def sanitize_plaintext(value, from_html=False, max_chars=False, strip_email_noise=False):
    lines = _sanitize_lines(
        value,
        from_html=from_html,
        strip_email_noise=strip_email_noise,
        max_line_chars=max_chars,
    )
    return normalize_inline_text(' '.join(lines), fallback='', max_chars=max_chars, drop_placeholders=True)


def split_unique_text_lines(value, from_html=False, max_items=False, max_line_chars=False, strip_email_noise=False):
    return _sanitize_lines(
        value,
        from_html=from_html,
        strip_email_noise=strip_email_noise,
        max_line_chars=max_line_chars,
        max_items=max_items,
    )
