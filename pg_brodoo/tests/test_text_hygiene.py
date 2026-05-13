from odoo.tests import TransactionCase, tagged

from ..services.text_hygiene import SCOPE_ITEM_EXCLUDED_NOISE
from ..services.text_hygiene import SCOPE_ITEM_FACTUAL_BUT_NEEDS_CURATION
from ..services.text_hygiene import SCOPE_ITEM_INCLUDED
from ..services.text_hygiene import classify_scope_item
from ..services.text_hygiene import curate_scope_publication_lines
from ..services.text_hygiene import has_safe_scope_split_boundary
from ..services.text_hygiene import is_compound_scope_summary
from ..services.text_hygiene import is_conversational_follow_up_scope_summary
from ..services.text_hygiene import has_suspicious_mojibake
from ..services.text_hygiene import is_low_signal_attachment_name
from ..services.text_hygiene import is_low_signal_scope_summary
from ..services.text_hygiene import is_non_factual_scope_summary
from ..services.text_hygiene import is_technical_noise_scope_summary
from ..services.text_hygiene import is_weak_nominal_scope_item
from ..services.text_hygiene import is_weak_scope_heading
from ..services.text_hygiene import normalize_inline_text
from ..services.text_hygiene import sanitize_message_body
from ..services.text_hygiene import sanitize_scope_publication_candidate
from ..services.text_hygiene import split_scope_publication_candidates
from ..services.text_hygiene import split_unique_text_lines
from ..services.text_hygiene import strip_inline_email_noise


@tagged('post_install', '-at_install')
class TestTextHygiene(TransactionCase):
    def test_sanitize_message_body_strips_quoted_reply_and_signature(self):
        body = """
            <p>Blocked until the customer shares the API credentials.</p>
            <p>Best regards,<br/>Project Manager</p>
            <p>On Tue, 2 Apr 2026 at 10:00, Customer wrote:</p>
            <blockquote><p>Approved for production.</p></blockquote>
        """

        sanitized = sanitize_message_body(body)

        self.assertEqual(sanitized, 'Blocked until the customer shares the API credentials.')

    def test_sanitize_message_body_strips_disclaimer_and_odoo_asset_noise(self):
        body = """
            <p>@Manuel Silva Bom dia.</p>
            <p>Envie por favor o ficheiro atualizado para validaÃ§Ã£o.</p>
            <p>Aviso Legal Este e-mail (incluindo Anexos) poderÃ¡ conter informaÃ§Ã£o confidencial.</p>
            <p>/odoo/res.partner/132421 /web/image/45386?access_token=abc</p>
        """

        sanitized = sanitize_message_body(body)

        self.assertEqual(sanitized, '@Manuel Silva Bom dia. Envie por favor o ficheiro atualizado para validaÃ§Ã£o.')

    def test_normalize_inline_text_repairs_common_mojibake(self):
        normalized = normalize_inline_text('IntegraÃƒÆ’Ã‚Â§ÃƒÆ’Ã‚Â£o aprovada para produÃƒÆ’Ã‚Â§ÃƒÆ’Ã‚Â£o.')

        self.assertEqual(normalized, 'IntegraÃ§Ã£o aprovada para produÃ§Ã£o.')
        self.assertFalse(has_suspicious_mojibake(normalized))

    def test_split_unique_text_lines_drops_placeholders_and_truncates(self):
        long_line = 'Validar alinhamento tecnico com o cliente ' * 12

        lines = split_unique_text_lines(
            '\n'.join(
                [
                    '[PONTO POR VALIDAR]',
                    'Validar webhook GitHub',
                    'Validar webhook GitHub',
                    long_line,
                ]
            ),
            max_line_chars=80,
        )

        self.assertEqual(lines[0], 'Validar webhook GitHub')
        self.assertEqual(len(lines), 2)
        self.assertLessEqual(len(lines[1]), 80)
        self.assertTrue(lines[1].endswith('...'))

    def test_strip_inline_email_noise_removes_links_and_reference_tokens(self):
        sanitized = strip_inline_email_noise(
            'https://www.parametro.global/mail/message/419786 [1] '
            'Ao importar encomendas em curso criar o projeto com a ref. interna. '
            'https://maps.app.goo.gl/Qd4uDd4WebQM9iSs8'
        )

        self.assertEqual(
            sanitized,
            'Ao importar encomendas em curso criar o projeto com a ref. interna.',
        )

    def test_strip_inline_email_noise_removes_disclaimer_and_odoo_asset_references(self):
        sanitized = strip_inline_email_noise(
            'Reencaminho o pedido do cliente. '
            'Aviso Legal Este e-mail contÃ©m informaÃ§Ã£o confidencial. '
            '/odoo/res.partner/132421 /web/image/45386?access_token=abc'
        )

        self.assertEqual(sanitized, 'Reencaminho o pedido do cliente.')

    def test_is_non_factual_scope_summary_flags_real_ancoravip_email_variants(self):
        self.assertTrue(
            is_non_factual_scope_summary(
                'Conforme conversado na reuniÃ£o na AncoraVip envio em anexo a informaÃ§Ã£o '
                'solicitada para darmos inÃ­cio ao arranque da implementaÃ§Ã£o do Odoo.'
            )
        )
        self.assertTrue(
            is_non_factual_scope_summary(
                'penso jÃ¡ ter fornecido toda a informaÃ§Ã£o solicitada. Preciso por favor que '
                'me indiquem qual a prÃ³xima fase para nos podermos organizar.'
            )
        )
        self.assertTrue(is_non_factual_scope_summary('> Whatsapp'))
        self.assertTrue(
            is_non_factual_scope_summary(
                'Rui Ribeiro Image ANCORA VIP INDUSTRY, LDA. Unidade2 Rua do Bairro da Boavista '
                'Freamunde ( Mail None geral@ancoravip.pt None None Image None Image None Image '
                'Image mailto:geral@ancoravip.pt'
            )
        )

    def test_strip_inline_email_noise_removes_leading_quote_marker(self):
        sanitized = strip_inline_email_noise('> Criar campo "Registo Verificado"')

        self.assertEqual(sanitized, 'Criar campo "Registo Verificado"')

    def test_is_low_signal_scope_summary_flags_real_ancoravip_heading_and_filename_noise(self):
        self.assertTrue(is_low_signal_scope_summary('Email Odoo Security'))
        self.assertTrue(is_low_signal_scope_summary('Odoo - seguimento de trabalhos'))
        self.assertTrue(is_low_signal_scope_summary('lista fornecedores / clientes'))
        self.assertTrue(is_low_signal_scope_summary('Template Orcamento - Odoo Import V2.2.xlsm'))
        self.assertTrue(is_low_signal_scope_summary('WhatsApp Business'))
        self.assertTrue(is_low_signal_scope_summary('Rua do Bairro da Boavista Freamunde'))
        self.assertTrue(is_low_signal_scope_summary('Avenida Central 145 Freamunde'))
        self.assertTrue(is_low_signal_scope_summary('comercial@ancoravip.pt'))
        self.assertTrue(is_low_signal_scope_summary('Arvore de categorias (Inventario)'))

    def test_is_technical_noise_scope_summary_flags_contact_and_asset_metadata_noise(self):
        self.assertTrue(
            is_technical_noise_scope_summary(
                'Rui Ribeiro Image ANCORA VIP INDUSTRY, LDA. Unidade2 Rua do Bairro da Boavista '
                'Mail geral@ancoravip.pt Tel. +351 255 878 612'
            )
        )
        self.assertTrue(is_technical_noise_scope_summary('WhatsApp Business'))
        self.assertFalse(
            is_technical_noise_scope_summary('Validar email de notificacoes usado no arranque do projeto')
        )

    def test_is_weak_scope_heading_flags_generic_single_heading_variants(self):
        self.assertTrue(is_weak_scope_heading('Agendamento'))
        self.assertTrue(is_weak_scope_heading('Orcamentacao'))
        self.assertTrue(is_weak_scope_heading('Template'))
        self.assertFalse(is_weak_scope_heading('Importar contactos de clientes e fornecedores'))

    def test_is_weak_nominal_scope_item_flags_short_nominal_labels_and_names(self):
        self.assertTrue(is_weak_nominal_scope_item('Kick Off'))
        self.assertTrue(is_weak_nominal_scope_item('Go-Live'))
        self.assertTrue(is_weak_nominal_scope_item('Projeto'))
        self.assertTrue(is_weak_nominal_scope_item('Contabilidade'))
        self.assertTrue(is_weak_nominal_scope_item('Rui Ribeiro'))
        self.assertTrue(is_weak_nominal_scope_item('ANCORA VIP INDUSTRY, LDA.'))
        self.assertTrue(is_weak_nominal_scope_item('orladora'))
        self.assertTrue(is_weak_nominal_scope_item('Testar e'))
        self.assertTrue(is_weak_nominal_scope_item('Formacao CRM'))
        self.assertTrue(is_weak_nominal_scope_item('ANCORAVIP Website'))
        self.assertTrue(is_weak_nominal_scope_item('Codigo de Subscricao'))
        self.assertTrue(is_weak_nominal_scope_item('Coluna A "Artigo" Ref. Cliente'))
        self.assertFalse(is_weak_nominal_scope_item('Importar contactos de clientes e fornecedores'))

    def test_is_conversational_follow_up_scope_summary_flags_follow_up_phrases(self):
        self.assertTrue(is_conversational_follow_up_scope_summary('Qualquer duvida dispoe.'))
        self.assertTrue(is_conversational_follow_up_scope_summary('Fico a aguardar feedback da vossa parte.'))
        self.assertTrue(is_conversational_follow_up_scope_summary('Fico a aguardar resposta o mais breve possivel.'))
        self.assertTrue(is_conversational_follow_up_scope_summary('Recebi o email que anexo, nao sei do que se trata.'))
        self.assertTrue(is_conversational_follow_up_scope_summary('Hoje de tarde sempre passas por ca para dar seguimento ao arranque do Odoo?'))
        self.assertTrue(is_conversational_follow_up_scope_summary('necessito tambem do template para a parte comercial.'))
        self.assertTrue(is_conversational_follow_up_scope_summary('Por favor, analisa e da-me feedback.'))
        self.assertTrue(is_conversational_follow_up_scope_summary('Rui pediu para o elucidar sobre que custos financeiros implica.'))
        self.assertTrue(is_conversational_follow_up_scope_summary('Fiquei de lhe enviar um email informativo sobre este assunto.'))
        self.assertTrue(is_non_factual_scope_summary('em relacao ao tema de extrair um ficheiro de consumos efetivos penso que o consigo fazer desta forma.'))
        self.assertTrue(is_non_factual_scope_summary('surgiu novas algumas complicacoes no uso do template inicial.'))
        self.assertFalse(
            is_conversational_follow_up_scope_summary('Configurar workflow de validacao do arranque do Odoo')
        )

    def test_compound_scope_helpers_detect_safe_and_unsafe_cases(self):
        safe_item = 'Criar utilizadores; Configurar permissoes; Validar acessos'
        unsafe_item = (
            'Testar e Corrigir importacao de encomendas em curso Alterar arrastar tarefa para producao '
            'Alterar campo de mapeamento de secao para mapeamento obrigatorio'
        )

        self.assertTrue(has_safe_scope_split_boundary(safe_item))
        self.assertTrue(is_compound_scope_summary(safe_item))
        self.assertFalse(has_safe_scope_split_boundary(unsafe_item))
        self.assertTrue(is_compound_scope_summary(unsafe_item))

    def test_split_scope_publication_candidates_splits_only_when_boundary_is_safe(self):
        self.assertEqual(
            split_scope_publication_candidates(
                'Criar utilizadores; Configurar permissoes; Validar acessos',
                max_chars=220,
            ),
            ['Criar utilizadores', 'Configurar permissoes', 'Validar acessos'],
        )
        self.assertEqual(
            split_scope_publication_candidates(
                'No chao de fabrica pedir pin de acesso aos centros de trabalho por fabrica '
                'Anliasar merge de contactos das encomendas importadas Verificar se e possivel passar '
                'a ref. interna da encomenda para o numero da encomenda em odoo',
                max_chars=220,
            ),
            [
                'No chao de fabrica pedir pin de acesso aos centros de trabalho por fabrica',
                'Anliasar merge de contactos das encomendas importadas',
                'Verificar se e possivel passar a ref. interna da encomenda para o numero da encomenda em odoo',
            ],
        )
        self.assertEqual(
            split_scope_publication_candidates(
                'Incluir nome do cliente do registo do projeto e torna-lo visivel '
                'Ao finalizar producao no chao de fabrica registar automaticamente a expedicao dos artigos finalizados',
                max_chars=220,
            ),
            [
                'Incluir nome do cliente do registo do projeto e torna-lo visivel',
                'Ao finalizar producao no chao de fabrica registar automaticamente a expedicao dos artigos finalizados',
            ],
        )
        self.assertFalse(
            split_scope_publication_candidates(
                'Testar e Corrigir importacao de encomendas em curso Alterar arrastar tarefa para producao '
                'Alterar campo de mapeamento de secao para mapeamento obrigatorio',
                max_chars=220,
            )
        )

    def test_sanitize_scope_publication_candidate_rejects_noise_and_keeps_factual_lines(self):
        self.assertFalse(
            sanitize_scope_publication_candidate(
                'Conforme conversado na reuniao na AncoraVip envio em anexo a informacao solicitada.'
            )
        )
        self.assertFalse(sanitize_scope_publication_candidate('Qualquer duvida dispoe.'))
        self.assertFalse(sanitize_scope_publication_candidate('Fico a aguardar feedback da vossa parte.'))
        self.assertFalse(sanitize_scope_publication_candidate('Rui Ribeiro'))
        self.assertFalse(sanitize_scope_publication_candidate('Whatsapp'))
        self.assertFalse(sanitize_scope_publication_candidate('WhatsApp Business'))
        self.assertFalse(sanitize_scope_publication_candidate('Documento de Ancora Vip'))
        self.assertFalse(sanitize_scope_publication_candidate('o email a monitorizar no Dep. Comercial e o seguinte'))
        self.assertFalse(sanitize_scope_publication_candidate('ANCORA VIP INDUSTRY, LDA.'))
        self.assertFalse(sanitize_scope_publication_candidate('Rua do Bairro da Boavista Freamunde'))
        self.assertFalse(sanitize_scope_publication_candidate('Avenida Central 145 Freamunde'))
        self.assertFalse(sanitize_scope_publication_candidate('comercial@ancoravip.pt'))
        self.assertFalse(sanitize_scope_publication_candidate('Testar e'))
        self.assertFalse(sanitize_scope_publication_candidate('Fiquei de lhe enviar um email informativo sobre este assunto.'))
        self.assertFalse(sanitize_scope_publication_candidate('Arvore de categorias (Inventario)'))
        self.assertFalse(sanitize_scope_publication_candidate('Formacao CRM'))
        self.assertFalse(sanitize_scope_publication_candidate('ANCORAVIP Website'))
        self.assertFalse(sanitize_scope_publication_candidate('Codigo de Subscricao'))
        self.assertFalse(sanitize_scope_publication_candidate('Coluna A "Artigo" Ref. Cliente'))
        self.assertFalse(sanitize_scope_publication_candidate('em relacao ao tema de extrair um ficheiro de consumos efetivos penso que o consigo fazer desta forma.'))
        self.assertFalse(sanitize_scope_publication_candidate('surgiu novas algumas complicacoes no uso do template inicial.'))
        self.assertFalse(sanitize_scope_publication_candidate('Template Orcamento - Odoo Import V2.2.xlsm'))
        self.assertFalse(
            sanitize_scope_publication_candidate(
                'ANCORA VIP INDUSTRY, LDA. Unidade2 Rua do Bairro da Boavista Mail geral@ancoravip.pt '
                'Tel. +351 255 878 612'
            )
        )
        self.assertEqual(
            sanitize_scope_publication_candidate('Whatsapp Criar campo "Registo Verificado"'),
            'Criar campo "Registo Verificado"',
        )
        self.assertEqual(
            sanitize_scope_publication_candidate('> Criar campo "Registo Verificado"'),
            'Criar campo "Registo Verificado"',
        )

    def test_curate_scope_publication_lines_deduplicates_and_filters_globally(self):
        curated = curate_scope_publication_lines(
            [
                'Agendamento',
                'Importar contactos de clientes e fornecedores',
                'Importar contactos de clientes e fornecedores',
                'Template Orcamento - Odoo Import V2.2.xlsm',
                'WhatsApp Business',
                'ANCORA VIP INDUSTRY, LDA. Unidade2 Rua do Bairro da Boavista Mail geral@ancoravip.pt',
                'Documento de Ancora Vip',
                'o email a monitorizar no Dep. Comercial e o seguinte',
                'Rua do Bairro da Boavista Freamunde',
                'Avenida Central 145 Freamunde',
                'comercial@ancoravip.pt',
                '> Criar campo "Registo Verificado"',
                'Whatsapp Criar campo "Registo Verificado"',
                'Testar e',
                'Fiquei de lhe enviar um email informativo sobre este assunto.',
                'Arvore de categorias (Inventario)',
                'Formacao CRM',
                'ANCORAVIP Website',
                'Codigo de Subscricao',
                'Coluna A "Artigo" Ref. Cliente',
                'em relacao ao tema de extrair um ficheiro de consumos efetivos penso que o consigo fazer desta forma.',
                'surgiu novas algumas complicacoes no uso do template inicial.',
                'Vendas \u200bAcrescentar separador nas ordens de venda para refletir estado da producao',
                'Criar utilizadores; Configurar permissoes; Validar acessos',
                'Fico a aguardar feedback da vossa parte.',
                'Rui Ribeiro',
                'Go-Live',
                'Projeto',
            ],
            max_chars=220,
        )

        self.assertEqual(
            curated,
            [
                'Importar contactos de clientes e fornecedores',
                'Criar campo "Registo Verificado"',
                'Acrescentar separador nas ordens de venda para refletir estado da producao',
                'Criar utilizadores',
                'Configurar permissoes',
                'Validar acessos',
            ],
        )

    def test_classify_scope_item_uses_single_contract_for_scope_states(self):
        included = classify_scope_item('Criar utilizadores; Configurar permissoes', max_chars=220)
        backlog = classify_scope_item(
            'Incluir nome do cliente do registo do projeto Ao finalizar producao no chao de fabrica registar automaticamente a expedicao.',
            max_chars=220,
        )
        excluded = classify_scope_item('Fico a aguardar feedback da vossa parte.', max_chars=220)

        self.assertEqual(included['state'], SCOPE_ITEM_INCLUDED)
        self.assertEqual(included['reason'], 'safe_split_available')
        self.assertEqual(included['publication_candidates'], ['Criar utilizadores', 'Configurar permissoes'])

        self.assertEqual(backlog['state'], SCOPE_ITEM_FACTUAL_BUT_NEEDS_CURATION)
        self.assertEqual(backlog['reason'], 'compound_item')
        self.assertEqual(backlog['publication_candidates'], [])

        self.assertEqual(excluded['state'], SCOPE_ITEM_EXCLUDED_NOISE)
        self.assertEqual(excluded['reason'], 'conversational_follow_up')

    def test_classify_scope_item_preserves_factual_contact_and_follow_up_in_backlog(self):
        contact_reference = classify_scope_item('Rua do Bairro da Boavista Freamunde', max_chars=220)
        factual_follow_up = classify_scope_item(
            'necessito tambem do template para a parte comercial.',
            max_chars=220,
        )

        self.assertEqual(contact_reference['state'], SCOPE_ITEM_FACTUAL_BUT_NEEDS_CURATION)
        self.assertEqual(contact_reference['reason'], 'needs_manual_scope_curation')
        self.assertEqual(contact_reference['publication_candidates'], [])

        self.assertEqual(factual_follow_up['state'], SCOPE_ITEM_FACTUAL_BUT_NEEDS_CURATION)
        self.assertEqual(factual_follow_up['reason'], 'needs_manual_scope_curation')
        self.assertEqual(factual_follow_up['publication_candidates'], [])

    def test_is_low_signal_attachment_name_flags_generic_generated_images(self):
        self.assertTrue(is_low_signal_attachment_name('image005.png'))
        self.assertTrue(is_low_signal_attachment_name('image3'))
        self.assertTrue(is_low_signal_attachment_name('document_12.pdf'))
        self.assertFalse(is_low_signal_attachment_name('email_cliente.pdf'))
