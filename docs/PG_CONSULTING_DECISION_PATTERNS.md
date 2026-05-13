# PG_CONSULTING_DECISION_PATTERNS

Este ficheiro funciona como biblioteca leve de padroes consultivos recorrentes em projetos Odoo.
Serve apenas como apoio ao raciocinio consultivo. Nunca substitui a validacao do projeto atual contra `PG_CONTEXT.md`, codigo do projeto, `vendor/odoo_src` e documentacao oficial da versao ativa.

## PADRAO 001 - Aprovacoes multi-nivel
Tipo de pedido:
- aprovacao em varios niveis por valor, equipa, departamento ou tipo de documento

Opcoes a avaliar primeiro:
- configuracoes standard do modulo atual
- modulos standard adicionais de approvals, purchase, expenses ou account
- regras de seguranca e atividades standard

Cobertura standard tipica:
- parcial

Quando Studio pode chegar:
- quando a regra e simples, com poucos estados e poucas excecoes

Quando custom pode ser necessario:
- quando ha matriz complexa de aprovadores, escalonamento automatico ou logica transversal a varios modulos

Riscos tipicos:
- fluxo demasiado complexo
- bypass operacional fora do sistema
- dependencia de grupos e regras mal definidas

Nota consultiva:
- muitos pedidos de "workflow custom" sao na verdade falta de configuracao, modulo adicional ou clarificacao de autoridade de aprovacao

## PADRAO 002 - Campos adicionais e regras simples
Tipo de pedido:
- campos extra, obrigatoriedade condicional, pequenas validacoes e automatismos basicos

Opcoes a avaliar primeiro:
- campos standard ja existentes
- Studio
- automacoes simples ou configuracao nativa

Cobertura standard tipica:
- parcial com forte potencial via Studio

Quando Studio pode chegar:
- quando o requisito e local ao modelo, sem logica transversal pesada

Quando custom pode ser necessario:
- quando a regra depende de multiplos modelos, performance critica ou comportamento tecnico nao suportado em Studio

Riscos tipicos:
- proliferacao de campos sem dono funcional
- regras isoladas que degradam UX

Nota consultiva:
- confirmar sempre se o pedido e necessidade real ou apenas preferencia de layout

## PADRAO 003 - Contratos, subscricoes e recorrencia
Tipo de pedido:
- faturacao recorrente, renovacoes, contratos de servico, SLAs e recorrencia comercial

Opcoes a avaliar primeiro:
- modulos standard de subscriptions, sales, helpdesk ou field service
- configuracao de produtos recorrentes

Cobertura standard tipica:
- parcial a total, dependendo da edicao e do processo

Quando Studio pode chegar:
- quando so faltam campos, vistas ou pequenas regras de suporte

Quando custom pode ser necessario:
- quando ha logica contratual muito especifica, calculo avancado, integracao externa ou compliance setorial

Riscos tipicos:
- misturar contrato juridico com objeto operacional no Odoo
- recorrencia mal modelada a partir de vendas avulsas

Nota consultiva:
- distinguir sempre entre contrato comercial, renovacao operacional e mecanismo de faturacao

## PADRAO 004 - Gestao documental e assinatura
Tipo de pedido:
- anexos, aprovacoes documentais, assinatura eletronica, controlo de versoes e trilho de auditoria

Opcoes a avaliar primeiro:
- modulos standard de documents, sign, knowledge e attachments do modulo atual
- permissoes e estrutura documental standard

Cobertura standard tipica:
- parcial a total

Quando Studio pode chegar:
- quando faltam apenas campos, tags, classificacao ou pequenas acoes

Quando custom pode ser necessario:
- quando ha requisitos legais, integracoes com DMS externo ou governanca documental muito especifica

Riscos tipicos:
- tratar problema operacional como mera organizacao de ficheiros
- excesso de anexos sem taxonomia

Nota consultiva:
- confirmar se a dor e assinatura, arquivo, pesquisa ou controlo de processo

## PADRAO 005 - CRM para projeto para faturacao
Tipo de pedido:
- continuidade do processo desde lead ou oportunidade ate entrega e faturacao

Opcoes a avaliar primeiro:
- integracao standard entre crm, sale, project, helpdesk, timesheets e accounting
- configuracao de produtos e politicas de faturacao

Cobertura standard tipica:
- parcial a total

Quando Studio pode chegar:
- quando faltam apenas checkpoints visuais ou pequenos campos de passagem

Quando custom pode ser necessario:
- quando ha regras de handoff muito especificas, calculo contratual especial ou orquestracao entre varias entidades

Riscos tipicos:
- tentar resolver desalinhamento organizacional com automacao excessiva
- fases comerciais e operacionais mal definidas

Nota consultiva:
- muitos gaps aparentes sao configuracao insuficiente de produtos, projetos ou politica de faturacao

## PADRAO 006 - Compras com aprovacao ou validacao
Tipo de pedido:
- autorizacao de compras, limiares por valor, segregacao de funcoes e controlo de excecoes

Opcoes a avaliar primeiro:
- configuracao standard de purchase
- modulos standard adicionais de approvals
- regras de acesso e atividades standard

Cobertura standard tipica:
- parcial

Quando Studio pode chegar:
- quando a necessidade e visibilidade, campos adicionais ou passos simples

Quando custom pode ser necessario:
- quando ha politica multicriterio complexa, integracao com procurement externo ou controlo avancado por centro de custo

Riscos tipicos:
- criar workflow pesado para compensar politica interna pouco clara
- bloqueios operacionais em compras urgentes

Nota consultiva:
- validar primeiro se o objetivo e governance, compliance ou controlo de custo

## PADRAO 007 - Logistica com rastreabilidade
Tipo de pedido:
- lotes, series, tracking, qualidade, localizacoes e historico operacional

Opcoes a avaliar primeiro:
- configuracoes standard de inventory, barcode, quality, mrp e repair
- parametrizacao de tracking por produto e por operacao

Cobertura standard tipica:
- parcial a total

Quando Studio pode chegar:
- quando faltam apenas campos complementares, etiquetas internas ou pequenas vistas

Quando custom pode ser necessario:
- quando ha rastreabilidade regulatoria especifica, recolha de dados em hardware proprio ou cadeia logistica altamente especial

Riscos tipicos:
- desenho de processo fisico incoerente com o sistema
- excesso de custom para compensar disciplina operacional fraca

Nota consultiva:
- antes de pensar em custom, confirmar se o problema esta na configuracao de rotas, tracking ou qualidade

## PADRAO 008 - Reporting e dashboards
Tipo de pedido:
- indicadores, dashboards operacionais, analise de desempenho e relatorios executivos

Opcoes a avaliar primeiro:
- relatorios standard
- pivots, graphs, spreadsheets e dashboards nativos
- modulos standard adicionais relacionados com o dominio

Cobertura standard tipica:
- parcial a total para analise operacional

Quando Studio pode chegar:
- quando o gap e de apresentacao simples ou pequenos campos auxiliares

Quando custom pode ser necessario:
- quando ha metricas compostas, consolidacao multi-fonte, performance critica ou layout analitico muito especifico

Riscos tipicos:
- pedir dashboard quando o problema real e qualidade de dados
- querer KPI definitivo sem definicao funcional estavel

Nota consultiva:
- validar sempre definicao de indicador, periodicidade, fonte de dados e decisao que o relatorio suporta
