# AGENTS_SHARED - Parametro Global Odoo Consulting Framework

## Finalidade do framework
Este ficheiro concentra as regras partilhadas do framework consultivo Odoo.
O objetivo principal e manter um metodo comum entre projetos e colaboradores, reduzindo customizacao prematura e forçando decisoes baseadas em evidencia.

## Fontes de verdade obrigatorias
Antes de concluir qualquer analise, recomendacao ou proposta tecnica, consultar obrigatoriamente:
1. `PG_CONTEXT.md`
2. codigo do projeto
3. `vendor/odoo_src`
4. documentacao oficial do Odoo da versao ativa registada no `PG_CONTEXT.md`

Se houver conflito entre memoria geral e o projeto atual, prevalece sempre:
- o codigo do projeto
- o source Odoo consultado em `vendor/odoo_src`
- a versao registada no `PG_CONTEXT.md`
- a documentacao oficial da mesma versao

Quando existirem, `PG_SCOPE_INTAKE.yaml`, `.pg/PG_SCOPE_SYNC.json` e `.pg/PG_PROJECT_STATUS_SYNC.json` servem como fontes estruturadas complementares para inicializar ou refrescar o contexto.
Estes ficheiros nao substituem o `PG_CONTEXT.md`, que continua a ser a memoria funcional e decisoria do projeto.

## Apoio consultivo reutilizavel
Quando o requisito se assemelhar a um caso recorrente, o agente pode consultar `.pg_framework/docs/PG_CONSULTING_DECISION_PATTERNS.md`.
Quando for util recuperar aprendizagem consultiva anterior, o agente pode consultar `.pg_framework/docs/PG_PROJECT_LEARNINGS.md`.
Estes ficheiros servem apenas como apoio ao raciocinio e nunca substituem a validacao do projeto atual contra `PG_CONTEXT.md`, codigo do projeto, `vendor/odoo_src` e documentacao oficial da versao ativa.

## Modo challenger
Quando existir uma proposta funcional ou tecnica concreta, o agente pode operar em modo challenger.
Nesse modo, deve criticar a solucao antes de a validar e usar `.pg_framework/docs/PG_CHALLENGER_PROMPT.md` como referencia.

## Ordem obrigatoria de decisao
Antes de propor qualquer desenvolvimento custom, validar e documentar sempre esta ordem:
1. solucao standard ja disponivel no projeto
2. solucao standard adicional disponivel no Odoo, mesmo que o modulo nao esteja instalado
3. solucao via Odoo Studio
4. desenvolvimento custom

Esta ordem e obrigatoria.
Nunca saltar a analise de modulos standard adicionais.
Nunca limitar a analise apenas aos modulos principais ja usados no projeto.
Na avaliacao de modulos standard adicionais, consultar tambem diretamente o `vendor/odoo_src` da versao ativa para descobrir modulos standard potencialmente relevantes, incluindo modulos novos do Odoo, e nao apenas exemplos presentes na documentacao do projeto.

## Validacoes obrigatorias antes de recomendar
Antes de fechar uma recomendacao, validar ou marcar explicitamente como `PONTO POR VALIDAR`:
- versao do Odoo
- edicao (`Community` ou `Enterprise`)
- ambiente (`SaaS`, `Odoo.sh` ou `on-premise`)
- restricoes contratuais do projeto:
  - configuracao standard permitida?
  - modulos standard adicionais permitidos?
  - Studio permitido?
  - custom permitido?

Se algum destes pontos for critico para a decisao e nao estiver confirmado, pedir clarificacao antes de concluir.

## Gestao de incerteza e evidencia
Esta secao e obrigatoria em analise funcional, consultoria e proposta tecnica.

O agente:
- nao deve adivinhar funcionalidades
- nao deve assumir comportamentos do Odoo sem validacao
- nao deve apresentar inferencias como factos
- nao deve recomendar customizacao sem evidencia
- deve pedir clarificacao quando faltar contexto critico
- deve declarar a incerteza explicitamente

Cada conclusao relevante deve distinguir entre:
- `FACTO OBSERVADO`: confirmado no codigo, no contexto do projeto ou na documentacao oficial
- `INFERENCIA`: conclusao provavel, mas nao confirmada
- `PONTO POR VALIDAR`: informacao necessaria antes da decisao

## Regras de consulta e evidencia
Sempre que a analise recorrer ao source Odoo ou a modulos standard:
- citar explicitamente os paths consultados em `vendor/odoo_src`
- citar os links da documentacao oficial consultada
- explicar o padrao encontrado antes de propor alteracoes
- se a recomendacao for `Modulo standard adicional`, classificar obrigatoriamente a cobertura do requisito como `TOTAL`, `PARCIAL` ou `PARCIAL COM ADAPTACAO DE PROCESSO`
- quando a recomendacao for `Modulo standard adicional`, explicar tambem as implicacoes de adocao, incluindo impacto funcional, impacto no processo e eventuais gaps remanescentes

Quando a conclusao for que standard ou Studio nao chegam, justificar explicitamente:
- porque a configuracao standard existente nao resolve
- porque um modulo standard adicional nao resolve
- porque Studio nao resolve ou introduz risco inadequado
- porque a opcao custom e necessaria apesar do impacto em upgrade, manutencao e contrato

## Classificacao obrigatoria da recomendacao final
Toda a recomendacao final deve ser classificada numa destas categorias:
- `Configuracao standard`
- `Modulo standard adicional`
- `Odoo Studio`
- `Customizacao leve`
- `Customizacao estrutural`
- `Nao recomendado / alto risco`

## Regras de implementacao
- `vendor/odoo_src` e estritamente `read-only`
- nunca alterar ficheiros dentro de `vendor/odoo_src`
- tudo o que for criado no projeto deve usar prefixo `pg_` quando aplicavel
- se houver restricao contratual contra custom code, nao propor custom como caminho principal
- se a recomendacao final for custom, a justificacao consultiva vem antes da proposta tecnica

## Formato minimo esperado na resposta
Sempre que houver analise de requisito, incluir no minimo:
1. objetivo funcional e dor de negocio
2. factos observados
3. inferencias
4. pontos por validar
5. analise das opcoes na ordem obrigatoria
6. recomendacao classificada
7. riscos, impactos e proximos passos
8. referencias consultadas:
   - `PG_CONTEXT.md`
   - paths do projeto
   - paths de `vendor/odoo_src`
   - links oficiais do Odoo da versao ativa

Se a recomendacao final for `Modulo standard adicional`, incluir tambem:
- cobertura do requisito: `TOTAL`, `PARCIAL` ou `PARCIAL COM ADAPTACAO DE PROCESSO`
- implicacoes de adocao

Antes de apresentar uma recomendacao consultiva final, aplicar tambem a verificacao definida em `.pg_framework/docs/PG_PRE_RESPONSE_CHECKLIST.md`.

## Atualizacao do contexto
`PG_CONTEXT.md` e a memoria funcional e decisoria do projeto.
Atualizar em marcos relevantes, incluindo:
- mudanca de decisao consultiva
- fecho de analise funcional
- conclusao de desenvolvimento relevante
- bloqueios, riscos ou restricoes novas
- antes de commit ou PR final, quando aplicavel

## Producao de documentos
Quando for pedido ao agente para produzir um documento (ponto de situacao, levantamento de ambito, orcamento, email ao cliente, proposta tecnica ou similar), o agente deve:
1. identificar o tipo de documento pedido
2. consultar o template correspondente em `.pg_framework/doc_templates/`
3. adaptar o template ao contexto especifico do projeto usando `PG_CONTEXT.md` e o contexto da sessao
4. respeitar a estrutura de seccoes e o tom de discurso definidos no template

Mapeamento de templates disponiveis:
- ponto de situacao / status report → `TPL_PONTO_SITUACAO.md`
- levantamento de ambito / analise de ambito → `TPL_LEVANTAMENTO_AMBITO.md`
- email ao cliente → `TPL_EMAIL_CLIENTE.md`
- proposta tecnica / fit-gap / analise de requisito → `TPL_PROPOSTA_TECNICA.md`
- orcamento / estimativa de esforco → `TPL_ORCAMENTO.md`

Se nao existir template especifico para o tipo de documento pedido, aplicar o tom e estrutura do template mais proximo e indicar explicitamente que nao existe template dedicado.
O agente nao deve produzir documentos formais sem consultar o template correspondente.

## Registo de consumo de tokens
No fim de cada sessao de trabalho num repositorio elegivel pela framework, o agente deve registar o consumo estimado em `.pg/tokens/consumption.jsonl`.

O registo deve ser acrescentado ao ficheiro (append) — nunca substituir o conteudo anterior.
Se o ficheiro nao existir, criar em `.pg/tokens/consumption.jsonl`.

Formato do registo — uma linha JSON por sessao:
{"date":"YYYY-MM-DD","agent":"claude|codex","model":"nome-do-modelo","session_summary":"descricao breve do trabalho realizado nesta sessao","estimated_input_tokens":0,"estimated_output_tokens":0,"notes":"observacoes opcionais"}

Instrucoes de estimativa:
- `estimated_input_tokens`: estimar com base no numero de ficheiros lidos, tamanho do historico da sessao e contexto carregado
- `estimated_output_tokens`: estimar com base no volume de respostas, codigo e documentos gerados
- quando nao for possivel estimar com confianca, registar 0 e indicar em `notes`
- o campo `session_summary` e obrigatorio e deve descrever o trabalho realizado (ex: "analise de requisito modulo stock", "implementacao batch onboarding wizard", "producao ponto de situacao projeto X")

O registo de tokens e obrigatorio mesmo que a sessao nao tenha produzido alteracoes ao codigo ou ficheiros.
