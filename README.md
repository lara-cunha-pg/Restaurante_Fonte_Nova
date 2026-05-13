# _pg_template - Bootstrap consultivo para repositorios Odoo

Ultima release fechada do template: `v2.9.1`

Estado operativo atual:
- modelo dominante atual: `PG AI Assistant V1 mirror redesign`
- piloto V1 fechado formalmente com leitura `READY WITH GUARDRAILS`
- `Ronda 1 - Contrato minimo global` fechada em `2026-04-21`
- `Ronda 2 - Hygiene global` fechada em `2026-04-21`
- ronda ativa atual: `Ronda 3 - Segmentacao semantica conservadora`
- correcao de rumo da ronda ativa: `included_scope` passa a assumir-se como vista curada principal, nao como contentor unico de verdade factual
- a verdade factual relevante mas ainda insuficiente deixa de ser removida silenciosamente e passa a ser preservada como backlog factual pendente de curadoria
- o gestor do projeto passa a ter de ser sinalizado sobre o que existe no Odoo mas ainda nao esta suficientemente estruturado para entrar no `included_scope`
- proxima frente de implementacao dentro da ronda: separar `included_scope` curado de `factual_scope_backlog` e expor essa sinalizacao no espelho e no Odoo
- o modelo operativo curto desta ronda fica fixado em `docs/PG_MIRROR_TRANSFORMATION_OPERATING_MODEL.md`
- o modelo concreto de preservacao factual e sinalizacao ao gestor fica fixado em `docs/PG_MIRROR_FACTUAL_SIGNALING_MODEL.md`
- a execucao acelerada desta ronda fica fixada em `docs/PG_MIRROR_TRANSFORMATION_ACCELERATED_BACKLOG.md`
- a execucao concreta da ronda ativa fica fixada em `docs/PG_MIRROR_TRANSFORMATION_ROUND3_ADDON_TASKS.md`
- a baseline `v2.9.0` e os documentos `V29` passam a valer como linha historica anterior, nao como backlog dominante atual

Este template prepara novos repositorios Odoo para dois objetivos em simultaneo:
- bootstrap tecnico consistente
- disciplina consultiva Odoo antes de qualquer decisao de desenvolvimento
- preparacao de intake estruturado e refresh factual do contexto a partir do estado do projeto
- referencia estavel ao framework partilhado a partir de cada projeto

O template deixa de ser apenas um guard-rail de desenvolvimento. Passa a obrigar o agente a validar primeiro configuracao standard, depois modulos standard adicionais, depois Studio e so por fim custom.

## Principios base

- `vendor/odoo_src` e apenas referencia tecnica e e `read-only`
- o source Odoo nunca entra no Git
- tudo o que for criado no projeto usa prefixo `pg_` quando aplicavel
- o agente consulta sempre `PG_CONTEXT.md`, codigo do projeto, `vendor/odoo_src` e documentacao oficial da versao ativa
- o agente nao adivinha nem apresenta inferencias como factos
- o contexto funcional e decisorio vive no `PG_CONTEXT.md`
- `PG_SCOPE_INTAKE.yaml` e a fonte estruturada do ambito inicial do projeto
- `.pg/PG_SCOPE_SYNC.json` guarda snapshots factuais do ambito vivo do projeto
- `.pg/PG_PROJECT_STATUS_SYNC.json` guarda snapshots factuais do estado operacional
- `.pg/PG_DECISIONS_SYNC.json` guarda snapshots factuais das decisoes oficiais fechadas do projeto
- `.pg/PG_RISKS_SYNC.json` guarda snapshots factuais dos riscos oficiais publicados do projeto
- `.pg/PG_DELIVERIES_SYNC.json` guarda snapshots factuais dos entregaveis oficiais publicados do projeto
- `.pg/PG_REQUIREMENTS_SYNC.json` guarda snapshots factuais dos requisitos oficiais publicados do projeto
- `.pg/PG_PROJECT_PLAN_SYNC.json` guarda snapshots factuais do plano oficial publicado do projeto
- `.pg/PG_BUDGET_SYNC.json` guarda snapshots factuais do budget oficial publicado do projeto
- o `status sync` da baseline atual e `manual-only`; nao existe publicacao recorrente por evento ou schedule
- a framework pode gerar drafts factuais de status para revisao, mas o publish oficial continua manual
- o addon passa a expor um wizard de onboarding para ligar GitHub, projeto, repositorio e toggles principais num unico fluxo
- a task passa a expor um fluxo consultivo guiado por etapas para discovery, fit-gap, recomendacao final e gate
- o addon passa a expor um dashboard operacional centralizado para projetos com atencao, runs falhadas e tasks bloqueadas
- o projeto sinaliza quando o estado operacional mudou e ainda falta novo publish manual
- o fluxo AI da task exige `Consultive Gate` marcado como pronto antes de `Gerar Prompt AI` e `Executar com Codex`
- a task tem de registar classificacao consultiva final (`standard`, `modulo adicional`, `Studio`, `custom`) antes do fluxo AI
- o snapshot factual de scope inclui apenas tasks classificadas como `approved_scope`
- a task passa a suportar drafts heuristicas para `Scope Summary`, `Acceptance Criteria` e `Scope Kind`, mantendo-os separados dos campos oficiais ate aplicacao explicita
- o projeto passa a suportar geracao e aplicacao assistida em massa de drafts de scope para acelerar consolidacao brownfield
- o dashboard operacional passa a destacar o que ainda falta consolidar no brownfield antes de confiar no `scope sync`
- o draft operacional de status passa a considerar explicitamente backlog operacional, enriquecimento de scope em falta, drafts `needs_review` e runs com erro em cenarios brownfield
- a task passa a suportar drafts consultivos assistidos para `Recommendation Class`, reviews minimas e `Recommendation Justification`, mantendo sugestoes separadas da decisao final oficial
- a task mantem um trilho minimo de decisao consultiva para gate, prompt e trigger do Codex
- `.pg_framework/` e a referencia local ao framework partilhado
- a framework passa a integrar sinais filtrados do chatter de projeto e task como grounding auditavel para drafts de scope, status e consultoria
- o apoio LLM fica limitado a mensagens ambiguas do chatter, com JSON estrito, validacao forte e fallback deterministico

## Ordem obrigatoria de decisao

Antes de propor desenvolvimento custom, o agente tem de validar esta ordem:
1. standard ja existente no projeto
2. modulo standard adicional do Odoo, mesmo que nao esteja instalado
3. Odoo Studio
4. custom

Esta ordem e obrigatoria e aplica-se a analise funcional, consultoria e desenvolvimento.
A descoberta de modulos standard adicionais deve considerar sempre o `vendor/odoo_src` da versao ativa, incluindo modulos novos introduzidos pelo Odoo.

## Estrutura

```text
_pg_template/
|-- templates/   -> ficheiros copiados para cada projeto
|-- scripts/     -> bootstrap, clone/update do source Odoo, intake e sincronizacao do contexto
|-- docs/        -> documentacao de apoio
|                   -> ex: PG_DECISION_ENGINE_PROMPT.md (prompt para analise consultiva Odoo)
|-- vendor/      -> ligacoes locais para source Odoo em cache global da maquina
|-- .pg/         -> reservado para snapshots factuais locais ao projeto
|-- config.toml
`-- README.md
```

## Documentacao de apoio

- `docs/PROMPT_INICIAL.md` - prompt inicial para orientar o agente no projeto
- `docs/PG_DISCOVERY_PROMPT.md` - prompt para qualificar pedidos antes de preencher ou atualizar o contexto
- `docs/PG_FIT_GAP_FRAMING_PROMPT.md` - prompt leve para mapear fit e gap antes da decisao consultiva
- `docs/PG_DECISION_ENGINE_PROMPT.md` - prompt avancado para analise consultiva Odoo (standard -> modulo adicional -> Studio -> custom)
- `docs/PG_CHALLENGER_PROMPT.md` - prompt para desafiar propostas e validar decisoes antes de implementacao
- `docs/PG_SCOPE_INTAKE_SPEC.md` - especificacao do ficheiro estruturado de ambito inicial do projeto
- `docs/PG_SCOPE_SYNC_SPEC.md` - especificacao do ficheiro de sync factual do ambito vindo do Odoo
- `docs/PG_ODOO_SCOPE_SYNC_INTEGRATION.md` - contrato de integracao entre Odoo PG e `.pg/PG_SCOPE_SYNC.json`
- `docs/PG_SCOPE_ENRICHMENT_TECHNICAL_DESIGN.md` - desenho tecnico do automatismo para reduzir preenchimento manual de `Scope Summary`, `Acceptance Criteria` e `Scope Kind`
- `docs/PG_PROJECT_STATUS_SYNC_SPEC.md` - especificacao do ficheiro de sync factual vindo do Odoo
- `docs/PG_ODOO_PROJECT_STATUS_SYNC_INTEGRATION.md` - contrato de integracao entre Odoo PG e `.pg/PG_PROJECT_STATUS_SYNC.json`
- `docs/PG_TEMPLATE_EVOLUTION_ROADMAP.md` - roadmap operativo das proximas iteracoes da framework
- `docs/PG_MIRROR_FACTUAL_SIGNALING_MODEL.md` - modelo concreto para preservar verdade factual insuficientemente curada e sinalizar ao gestor o que ainda falta consolidar no Odoo
- `docs/PG_REP_001_EXECUTION.md` - abertura formal da frente `REP-001` para definir o modelo de conhecimento do projeto e a proposta inicial de entregaveis
- `docs/PG_REP_001_ARTIFACT_MATRIX.md` - matriz inicial da Fase A de `REP-001` com artefactos atuais, objetos Odoo sem artefacto repo e artefactos planeados
- `docs/PG_REP_001_MINIMUM_CONTRACTS.md` - contratos minimos da Fase B de `REP-001` com ownership factual, campos minimos, exclusoes e criterio de versionamento
- `docs/PG_REP_001_PG_CONTEXT_TARGET.md` - proposta da Fase C para reorganizar o `PG_CONTEXT.md` por camadas, com migracao segura sem partir marcadores atuais
- `docs/PG_REP_001_REP_002_CUT.md` - corte operacional da Fase D de `REP-001`, com slices recomendadas para `REP-002` e escolha inicial de `PG_DECISIONS_SYNC`
- `docs/PG_REP_002_SLICE_1_PG_DECISIONS_SYNC_EXECUTION.md` - abertura formal da primeira slice de `REP-002` para publicar decisoes oficiais do projeto em `.pg/PG_DECISIONS_SYNC.json`
- `docs/PG_REP_002_SLICE_1_PG_DECISIONS_SYNC_DISCOVERY.md` - discovery da Fase A da slice `PG_DECISIONS_SYNC`, com inventario factual do addon e fronteira entre estado oficial, trail consultivo e status derivado
- `docs/PG_REP_002_SLICE_1_PG_DECISIONS_SYNC_PHASE_D_RUNBOOK.md` - runbook operativo da Fase D da slice `PG_DECISIONS_SYNC`, com propagacao para deploy, `Upgrade` no Odoo e validacao factual em `ancoravip/teste`
- `docs/PG_REP_002_SLICE_2_PG_RISKS_SYNC_EXECUTION.md` - abertura formal da segunda slice de `REP-002` para publicar riscos oficiais do projeto em `.pg/PG_RISKS_SYNC.json`
- `docs/PG_REP_002_SLICE_2_PG_RISKS_SYNC_DISCOVERY.md` - discovery da Fase A da slice `PG_RISKS_SYNC`, com inventario factual do addon e fronteira entre risco oficial, status narrado, quality review e chatter
- `docs/PG_REP_002_SLICE_2_PG_RISKS_SYNC_PHASE_D_RUNBOOK.md` - runbook operativo da Fase D da slice `PG_RISKS_SYNC`, com worktrees limpos, delta de deploy, `Upgrade` no Odoo e medicao factual em `ancoravip/teste`
- `docs/PG_REP_002_SLICE_3_PG_DELIVERIES_SYNC_EXECUTION.md` - abertura formal da terceira slice de `REP-002` para publicar entregaveis oficiais do projeto em `.pg/PG_DELIVERIES_SYNC.json`
- `docs/PG_REP_002_SLICE_3_PG_DELIVERIES_SYNC_DISCOVERY.md` - discovery da Fase A da slice `PG_DELIVERIES_SYNC`, com inventario factual do addon, do standard `project.milestone` e fronteira entre entregavel oficial, task operacional, status narrado e chatter
- `docs/PG_REP_002_SLICE_3_PG_DELIVERIES_SYNC_PHASE_D_RUNBOOK.md` - runbook da Fase D de `PG_DELIVERIES_SYNC`, com topologia, worktrees de deploy/medicao e passos de validacao operacional ate ao piloto
- `docs/PG_REP_002_SLICE_4_PG_REQUIREMENTS_SYNC_EXECUTION.md` - abertura formal da quarta slice de `REP-002` para publicar requisitos oficiais do projeto em `.pg/PG_REQUIREMENTS_SYNC.json`
- `docs/PG_REP_002_SLICE_4_PG_REQUIREMENTS_SYNC_DISCOVERY.md` - discovery da Fase A da slice `PG_REQUIREMENTS_SYNC`, com inventario factual do addon e fronteira entre requisito oficial, `approved_scope`, drafts de scope e task operacional
- `docs/PG_REP_002_SLICE_4_PG_REQUIREMENTS_SYNC_PHASE_D_RUNBOOK.md` - runbook da Fase D de `PG_REQUIREMENTS_SYNC`, com deploy para `Parametro_Global/TesteExo`, `Upgrade` no Odoo e validacao factual em `ancoravip/teste`
- `docs/PG_REP_002_SLICE_5_PG_PROJECT_PLAN_SYNC_EXECUTION.md` - abertura formal da quinta slice de `REP-002` para publicar plano oficial do projeto em `.pg/PG_PROJECT_PLAN_SYNC.json`
- `docs/PG_REP_002_SLICE_5_PG_PROJECT_PLAN_SYNC_DISCOVERY.md` - discovery da Fase A da slice `PG_PROJECT_PLAN_SYNC`, com inventario factual do addon e fronteira entre plano oficial, milestones, status narrado, task operacional e budget
- `docs/PG_REP_002_SLICE_5_PG_PROJECT_PLAN_SYNC_PHASE_D_RUNBOOK.md` - runbook da Fase D de `PG_PROJECT_PLAN_SYNC`, com deploy para `Parametro_Global/TesteExo`, correcao de vista, `Upgrade` no Odoo e validacao factual em `ancoravip/teste`
- `docs/PG_PROJECT_PLAN_SYNC_SPEC.md` - spec da Fase B de `REP-002 - Slice 5`, com schema minimo, elegibilidade e regras semanticas de `.pg/PG_PROJECT_PLAN_SYNC.json`
- `docs/PG_ODOO_PROJECT_PLAN_SYNC_INTEGRATION.md` - contrato Odoo -> repo da Fase B de `REP-002 - Slice 5`, com escolha de publish manual ao nivel do projeto e fonte factual primaria em composicao conservadora `project.project` + `project.milestone`
- `docs/PG_REP_002_SLICE_6_PG_BUDGET_SYNC_EXECUTION.md` - abertura formal da sexta slice de `REP-002` para publicar budget oficial do projeto em `.pg/PG_BUDGET_SYNC.json`
- `docs/PG_REP_002_SLICE_6_PG_BUDGET_SYNC_DISCOVERY.md` - discovery da Fase A da slice `PG_BUDGET_SYNC`, com inventario factual do budget atual no addon e fronteira entre importacao de orcamento, venda, plano, task operacional e budget oficial
- `docs/PG_REP_002_SLICE_6_PG_BUDGET_SYNC_PHASE_D_RUNBOOK.md` - runbook da Fase D de `PG_BUDGET_SYNC`, com deploy para `Parametro_Global/TesteExo`, `Upgrade` no Odoo e validacao factual em `ancoravip/teste`
- `docs/PG_BUDGET_SYNC_SPEC.md` - spec da Fase B de `REP-002 - Slice 6`, com schema minimo, elegibilidade e regras semanticas de `.pg/PG_BUDGET_SYNC.json`
- `docs/PG_ODOO_BUDGET_SYNC_INTEGRATION.md` - contrato Odoo -> repo da Fase B de `REP-002 - Slice 6`, com escolha de publish manual ao nivel do projeto e fonte factual primaria em budget register dedicado ancorado no projeto
- `docs/PG_REP_003_SCOPE_STATUS_CURATION_EXECUTION.md` - abertura formal de `REP-003`, dedicada a reforcar curadoria de `scope` e `status`, com fronteira explicita entre oficial, draft assistido, candidato e evidencia
- `docs/PG_REP_003_SCOPE_STATUS_CURATION_DISCOVERY.md` - discovery da Fase A de `REP-003`, com inventario factual da fronteira atual entre `scope`, `status`, `draft`, `task` e `chatter` no addon
- `docs/PG_SCOPE_STATUS_CURATION_CONTRACT.md` - contrato minimo da Fase B de `REP-003`, com regra operativa para `oficial`, `draft assistido`, `candidato` e `evidencia` em `scope` e `status`; a `Fase C` desta frente fica implementada no addon com reforco minimo de feedback de curadoria antes de `apply` em `scope` e `status`
- `docs/PG_REP_003_SCOPE_STATUS_CURATION_PHASE_D_RUNBOOK.md` - runbook factual da Fase D de `REP-003`, com deploy em `Parametro_Global/TesteExo`, correcao de regressao UX e validacao piloto do feedback de curadoria de `scope` e `status`
- `docs/PG_REP_004_PG_CONTEXT_REDESIGN_EXECUTION.md` - execucao de `REP-004`, com abertura formal da frente e fecho das Fases C e D do redesenho compativel de `PG_CONTEXT.md`
- `docs/PG_REP_004_PG_CONTEXT_REDESIGN_DISCOVERY.md` - discovery da Fase A de `REP-004`, com inventario factual do `PG_CONTEXT.md` atual, writers locais/remotos e acoplamentos com snapshots, scripts e smoke tests
- `docs/PG_CONTEXT_REDESIGN_CONTRACT.md` - contrato da Fase B de `REP-004`, com estrutura alvo do novo `PG_CONTEXT.md` e estrategia de migracao segura para template, scripts, workflow GitHub e smoke tests
- `docs/PG_REP_004_PG_CONTEXT_REDESIGN_PHASE_D_RUNBOOK.md` - runbook factual da Fase D de `REP-004`, com sincronizacao do espelho `_pg_template`, refresh do `PG_CONTEXT.md` operacional e validacao do smoke test em `Parametro_Global/TesteExo`
- `docs/PG_REP_005_QUALITY_REVIEW_PRE_PUBLICATION_EXECUTION.md` - abertura formal de `REP-005`, dedicada ao quality review estrutural antes de publish factual e ao endurecimento do gating pre-publicacao
- `docs/PG_REP_005_QUALITY_REVIEW_PRE_PUBLICATION_DISCOVERY.md` - discovery da Fase A de `REP-005`, com inventario factual do quality review atual no addon, nos scripts e nos validadores, separando `blocking`, `warning` e analise auxiliar
- `docs/PG_QUALITY_REVIEW_PRE_PUBLICATION_CONTRACT.md` - contrato da Fase B de `REP-005`, com taxonomia minima de `blocking`, `warning` e `observacao` e estrategia conservadora de integracao no circuito atual; a `Fase C` desta frente fica implementada no addon com feedback pre-publicacao explicito para `decisions`, `risks`, `deliveries`, `requirements`, `project plan` e `budget`
- `docs/PG_REP_005_QUALITY_REVIEW_PRE_PUBLICATION_PHASE_D_RUNBOOK.md` - runbook factual da Fase D de `REP-005`, com deploy para `Parametro_Global/TesteExo`, resolucao do bloqueio de estilos no Odoo.sh e validacao piloto do feedback pre-publicacao no projeto e nos runs
- `docs/PG_MIRROR_TRANSFORMATION_OPERATING_MODEL.md` - modelo operativo curto da camada global de transformacao do espelho, com regras de boa gestao no Odoo, elegibilidade para espelho e checks automaticos antes da publicacao
- `docs/PG_MIRROR_TRANSFORMATION_ACCELERATED_BACKLOG.md` - backlog acelerado da camada de transformacao para fechar em poucas rondas a higiene global, segmentacao semantica conservadora, coerencia de planeamento e operabilidade no Odoo
- `docs/PG_REP_006_GLOBAL_UX_SIMPLIFICATION_DISCOVERY.md` - discovery da Fase A de `REP-006`, com inventario factual da superficie UX atual em projeto, task, dashboard, settings e onboarding, separando uso operacional de diagnostico e administracao
- `docs/PG_REP_006_GLOBAL_UX_SIMPLIFICATION_CONTRACT.md` - contrato da Fase B de `REP-006`, com taxonomia minima da nova superficie UX, fronteira entre `equipa operacional` e `modo avancado/admin` e guardrails de implementacao da simplificacao
- `docs/PG_REP_006_GLOBAL_UX_SIMPLIFICATION_EXECUTION.md` - execucao de `REP-006`, com fecho formal da simplificacao UX global do addon `pg_brodoo` e validacao operacional final em `Parametro_Global/TesteExo`
- `docs/PG_REP_006_GLOBAL_UX_SIMPLIFICATION_PHASE_D_RUNBOOK.md` - runbook factual da `Fase D` de `REP-006`, com checklist de validacao manual em Odoo para projeto, task e dashboard e registo do fecho factual da frente
- `docs/PG_REP_007_CONTROLLED_BROWNFIELD_EXECUTION.md` - execucao de `REP-007`, dedicada a controlar a superficie brownfield sem voltar a aproximar backlog, drafts e candidatos da camada oficial; a frente fica fechada com validacao operacional final em `Parametro_Global/TesteExo`
- `docs/PG_REP_007_CONTROLLED_BROWNFIELD_DISCOVERY.md` - discovery da Fase A de `REP-007`, com inventario factual da classificacao brownfield atual, drafts de enrichment, feedback de status e superficies brownfield ainda expostas
- `docs/PG_REP_007_CONTROLLED_BROWNFIELD_CONTRACT.md` - contrato da Fase B de `REP-007`, com taxonomia minima brownfield, fronteira entre `task`, `project` e `dashboard` e regra explicita de que nada brownfield promove sozinho para `status` oficial ou snapshots `.pg`
- `docs/PG_REP_007_CONTROLLED_BROWNFIELD_PHASE_D_RUNBOOK.md` - runbook factual da `Fase D` de `REP-007`, com checklist manual em Odoo para `task`, `project` e `dashboard` e registo do fecho factual da validacao final
- `docs/PG_REQUIREMENTS_SYNC_SPEC.md` - spec da Fase B de `REP-002 - Slice 4`, com schema minimo, elegibilidade e regras semanticas de `.pg/PG_REQUIREMENTS_SYNC.json`
- `docs/PG_ODOO_REQUIREMENTS_SYNC_INTEGRATION.md` - contrato Odoo -> repo da Fase B de `REP-002 - Slice 4`, com escolha de publish manual ao nivel do projeto e fonte factual primaria em extensao conservadora de `project.task` em `approved_scope`
- `docs/PG_DELIVERIES_SYNC_SPEC.md` - spec da Fase B de `REP-002 - Slice 3`, com schema minimo, elegibilidade e regras semanticas de `.pg/PG_DELIVERIES_SYNC.json`
- `docs/PG_ODOO_DELIVERIES_SYNC_INTEGRATION.md` - contrato Odoo -> repo da Fase B de `REP-002 - Slice 3`, com escolha de publish manual ao nivel do projeto e fonte factual primaria em extensao conservadora de `project.milestone`
- `docs/PG_RISKS_SYNC_SPEC.md` - spec da Fase B de `REP-002 - Slice 2`, com schema minimo, elegibilidade e regras semanticas de `.pg/PG_RISKS_SYNC.json`
- `docs/PG_ODOO_RISKS_SYNC_INTEGRATION.md` - contrato Odoo -> repo da Fase B de `REP-002 - Slice 2`, com escolha de publish manual ao nivel do projeto e fonte factual primaria em objeto dedicado de risco
- `docs/PG_DECISIONS_SYNC_SPEC.md` - spec da Fase B de `REP-002 - Slice 1`, com schema minimo, elegibilidade e regras semanticas de `.pg/PG_DECISIONS_SYNC.json`
- `docs/PG_ODOO_DECISIONS_SYNC_INTEGRATION.md` - contrato Odoo -> repo da Fase B de `REP-002 - Slice 1`, com escolha de publish manual ao nivel do projeto e mapeamento inicial a partir de `project.task`
- `docs/PG_V29_PILOT_VALIDATION_RUNBOOK.md` - roteiro historico da ronda de validacao da baseline `v2.9.0`, anterior ao fecho do modelo V1
- `docs/PG_V29_PILOT_REPORT_TEMPLATE.md` - template historico de relatorio da ronda `v2.9.0`
- `docs/PG_V29_PHASE_1_2_EXECUTION_CHECKLIST.md` - checklist historica de execucao das `Fases 1` e `2` do piloto `v2.9.0`
- `docs/PG_V29_ADOPTION_BACKLOG.md` - backlog historico da ronda de adocao da baseline `v2.9.0`
- `docs/PG_CURRENT_WORKING_STATE.md` - ponto de entrada operativo atual, com a frente dominante, bloqueio principal e proximo passo logico
- `docs/PG_V1_MIRROR_MIGRATION_RUNBOOK.md` - runbook para migrar projetos legacy para o espelho V1 sem perder configuracao existente
- `docs/PG_V1_PILOT_VALIDATION_CHECKLIST.md` - checklist curta da validacao funcional do espelho V1
- `docs/PG_V1_PILOT_REPORT_2026-04-20.md` - relatorio factual do piloto V1 fechado com `READY WITH GUARDRAILS`
- `docs/PG_V25_BACKLOG.md` - backlog objetivo e priorizado da iteracao `v2.5`
- `docs/PG_V26_BACKLOG.md` - backlog objetivo e priorizado da iteracao `v2.6`
- `docs/PG_V27_BACKLOG.md` - backlog objetivo e priorizado da iteracao `v2.7`
- `docs/PG_V28_BACKLOG.md` - backlog objetivo e priorizado da iteracao `v2.8`
- `docs/PG_V29_BACKLOG.md` - backlog objetivo e priorizado da iteracao `v2.9`
- `docs/PG_GITHUB_CONTEXT_AUTOMATION.md` - workflow GitHub para regenerar `PG_CONTEXT.md` a partir dos snapshots `.pg`
- `docs/PG_REAL_PROJECT_ADOPTION_CHECKLIST.md` - checklist executavel para a primeira adocao real, com foco em brownfield e esforco minimo
- `docs/PG_REAL_PROJECT_ADOPTION_RUNBOOK.md` - guiao A a Z para um colega executar a primeira adocao real numa branch de testes e base de staging
- `docs/PG_REAL_PROJECT_ADOPTION_REPORT_TEMPLATE.md` - template de relatorio para devolver evidencias, SHAs, problemas e decisao `Go / No-Go`
- `docs/PG_RELEASE_POLICY.md` - politica operacional para promover o `_pg_template` a release utilizavel
- `docs/PG_CONTENT_HYGIENE.md` - checklist curta para encoding, placeholders e coerencia entre `risks`, `blockers` e `next_steps`
- `docs/PG_AI_DEV_ASSISTANT_OPERATIONS.md` - operacao do addon, setup GitHub/OpenAI/Codex, sync factual e troubleshooting Odoo 19
- `docs/PG_STATUS_SYNC_POLICY_NOTE.md` - decisao arquitetural e criterio de reavaliacao do `status sync` manual-only
- `docs/PG_TROUBLESHOOTING.md` - problemas recorrentes e resolucoes operacionais validadas no piloto
- `docs/PG_ODOO_SOURCE_SETUP.md` - setup do source Odoo por `git clone` em cache global e ligacao `vendor/odoo_src` no repo
- `docs/PG_SHARED_VS_LOCAL_MODEL.md` - regra do que fica partilhado no framework e local ao projeto
- `docs/PG_CONSULTING_DECISION_PATTERNS.md` - biblioteca leve de padroes consultivos recorrentes
- `docs/PG_PROJECT_LEARNINGS.md` - memoria evolutiva de aprendizagens consultivas reutilizaveis
- `docs/PG_PRE_RESPONSE_CHECKLIST.md` - checklist de verificacao antes de recomendacoes consultivas finais
- `docs/PG_TEMPLATE_VERSIONING.md` - regras simples de versionamento do template
- `CHANGELOG.md` - registo de versoes e evolucoes do template

## Bootstrap de um novo repositorio

Antes de correr os comandos abaixo, define o root real do template no teu ambiente:

```powershell
$TEMPLATE_ROOT = "C:\CAMINHO\PARA\_pg_template"
$REPOS_ROOT = "C:\CAMINHO\PARA\Repos"
Test-Path "$TEMPLATE_ROOT\scripts\pg_bootstrap_assisted.ps1"
```

Se o `Test-Path` devolver `False`, o path esta errado e tens de o corrigir antes de continuar.

Regra pratica:
- o `TEMPLATE_ROOT` tem de ser a pasta que contem este `README.md` e a pasta `scripts/`
- num clone normal do GitHub (`git clone ...`), isso costuma ser `...\_pg_template`
- um caminho `...\_pg_template\_pg_template` so acontece quando o clone foi feito dentro de uma pasta pai que ja tinha o mesmo nome

### Fluxo curto recomendado

Para um arranque assistido, usar:

```powershell
cd $TEMPLATE_ROOT
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\pg_bootstrap_assisted.ps1" -RepoName "NOME_DO_REPO" -RepoPath "$REPOS_ROOT\NOME_DO_REPO" -CloneOdooSource -Series 19.0 -Edition enterprise
```

O script:
- cria o diretorio do repositorio se ainda nao existir
- inicializa Git localmente quando necessario
- aplica bootstrap
- sincroniza os assets partilhados
- clona o source Odoo quando pedido
- corre o smoke test final

### 1. Aplicar o template ao repositorio

```powershell
cd $TEMPLATE_ROOT
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\pg_bootstrap_repo.ps1" -RepoName "NOME_DO_REPO" -RepoPath "$REPOS_ROOT\NOME_DO_REPO"
```

O bootstrap copia, por omissao, se ainda nao existirem:
- `.editorconfig`
- `AGENTS.md`
- `CLAUDE.md`
- `PG_CONTEXT.md`
- `PG_SCOPE_INTAKE.yaml`
- `config.toml`
- `.gitignore`
- `.gitattributes`
- `.github/workflows/pg_refresh_pg_context.yml`
- `.pg/PG_SCOPE_SYNC.json`
- `.pg/PG_PROJECT_STATUS_SYNC.json`
- `.pg/PG_DECISIONS_SYNC.json`
- `.pg/PG_RISKS_SYNC.json`
- `.pg/PG_DELIVERIES_SYNC.json`
- `.pg/PG_REQUIREMENTS_SYNC.json`
- `.pg/PG_PROJECT_PLAN_SYNC.json`
- `.pg/PG_BUDGET_SYNC.json`

Tambem garante as pastas `vendor/` e `.pg/` e cria `.pg_framework/` como referencia local ao framework partilhado.
Os scripts do template passam tambem a escrever ficheiros textuais em UTF-8 explicito para reduzir risco de corrupcao de acentos no Windows.

### 2. Preparar o source Odoo por git clone

O `odoo/enterprise` e um repositorio privado — precisas de acesso e de ter as credenciais GitHub configuradas. O Windows usa o Git Credential Manager por omissao; se ainda nao estiver configurado, o git vai pedir username e Personal Access Token (scope `repo`) na primeira vez e guarda automaticamente.

```powershell
cd $TEMPLATE_ROOT
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\pg_clone_odoo_source.ps1" -RepoName "NOME_DO_REPO" -RepoPath "$REPOS_ROOT\NOME_DO_REPO" -Series "19.0" -Edition "enterprise"
```

Exemplos:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\pg_clone_odoo_source.ps1" -RepoName "cliente_x" -RepoPath "$REPOS_ROOT\cliente_x" -Series "19.0" -Edition "community"
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\pg_clone_odoo_source.ps1" -RepoName "cliente_x" -RepoPath "$REPOS_ROOT\cliente_x" -Series "19.0" -Edition "enterprise"
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\pg_clone_odoo_source.ps1" -RepoName "cliente_x" -RepoPath "$REPOS_ROOT\cliente_x" -Series "19e"
```

O script:
- cria ou atualiza um cache global por serie em `%USERPROFILE%\.pg\odoo_src\<SERIE>\community`
- cria ou atualiza tambem `%USERPROFILE%\.pg\odoo_src\<SERIE>\enterprise` quando a edicao for `enterprise`
- cria ou atualiza `vendor/odoo_src` no repo como ligacao para o cache global da serie
- usa os repositorios oficiais `odoo/odoo` e, quando houver acesso, `odoo/enterprise`
- atualiza o `PG_CONTEXT.md` com versao, paths do source e links oficiais da documentacao dessa versao

O script legado `scripts/pg_link_odoo_core.cmd` continua disponivel apenas como wrapper de compatibilidade, mas o fluxo recomendado passa a ser sempre `pg_clone_odoo_source`.

### 3. Confirmar os pontos de decisao antes de trabalhar

No repositorio bootstrapado, confirmar e preencher:
- `PG_SCOPE_INTAKE.yaml`
- versao do Odoo
- edicao
- ambiente
- restricoes contratuais
- pedido funcional atual
- processo atual
- dor e impacto de negocio

Depois materializar o contexto inicial:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\pg_build_pg_context.ps1" -RepoPath "$REPOS_ROOT\NOME_DO_REPO"
```

Sem estes pontos, o template obriga o agente a pedir clarificacao antes de concluir.

### 4. Verificar o estado do repositorio

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\pg_smoke_test_repo.ps1" -RepoPath "$REPOS_ROOT\NOME_DO_REPO"
```

Todos os `OK` e sem erros significa que o repositorio esta operacional. Os `WARN` sobre snapshots placeholder ou source Odoo em falta sao normais nesta fase.

## Bootstrap em Linux / macOS

Os scripts sao os mesmos. A unica diferenca e o comando de invocacao: usa `pwsh` em vez de `powershell`, e nao e necessario `Set-ExecutionPolicy`.

### Pre-requisito: PowerShell Core

```bash
# Ubuntu / Debian / Linux Mint
sudo apt-get install -y wget
wget -q "https://packages.microsoft.com/config/ubuntu/22.04/packages-microsoft-prod.deb"
sudo dpkg -i packages-microsoft-prod.deb
sudo apt-get update -q && sudo apt-get install -y powershell
rm packages-microsoft-prod.deb

# macOS (Homebrew)
brew install --cask powershell
```

Verificar a instalacao:

```bash
pwsh --version
```

### Definir os paths de base

```bash
TEMPLATE_ROOT="/CAMINHO/PARA/_pg_template"
REPOS_ROOT="/CAMINHO/PARA/Repos"
pwsh -Command "Test-Path '$TEMPLATE_ROOT/scripts/pg_bootstrap_assisted.ps1'"
```

Se devolver `False`, o path esta errado.

### Fluxo curto recomendado

```bash
cd "$TEMPLATE_ROOT"
pwsh scripts/pg_bootstrap_assisted.ps1 -RepoName "NOME_DO_REPO" -RepoPath "$REPOS_ROOT/NOME_DO_REPO" -CloneOdooSource -Series 19.0 -Edition enterprise
```

### 1. Aplicar o template ao repositorio

```bash
cd "$TEMPLATE_ROOT"
pwsh scripts/pg_bootstrap_repo.ps1 -RepoName "NOME_DO_REPO" -RepoPath "$REPOS_ROOT/NOME_DO_REPO"
```

### 2. Preparar o source Odoo por git clone

O `odoo/enterprise` e um repositorio privado — precisas de acesso e de ter as credenciais GitHub configuradas. Faz isto uma vez na maquina antes de correr o script:

```bash
git config --global credential.helper store
```

Na primeira vez que o clone pedir credenciais, usa o teu username GitHub e um Personal Access Token (scope `repo`) como password. O git guarda e nao volta a pedir.

```bash
cd "$TEMPLATE_ROOT"
pwsh scripts/pg_clone_odoo_source.ps1 -RepoName "NOME_DO_REPO" -RepoPath "$REPOS_ROOT/NOME_DO_REPO" -Series "19.0" -Edition "enterprise"
```

O cache global fica em `~/.pg/odoo_src/<SERIE>/` (equivalente a `%USERPROFILE%\.pg\odoo_src\<SERIE>\` no Windows). Para projetos seguintes com a mesma serie o clone ja nao e repetido — so e criado o link `vendor/odoo_src`.

### 3. Confirmar os pontos de decisao antes de trabalhar

```bash
pwsh scripts/pg_build_pg_context.ps1 -RepoPath "$REPOS_ROOT/NOME_DO_REPO"
```

### 4. Verificar o estado do repositorio

```bash
pwsh scripts/pg_smoke_test_repo.ps1 -RepoPath "$REPOS_ROOT/NOME_DO_REPO"
```

Todos os `OK` e sem erros significa que o repositorio esta operacional. Os `WARN` sobre snapshots placeholder ou source Odoo em falta sao normais nesta fase.

### Sincronizar um repositorio ja bootstrapado

```bash
cd "$TEMPLATE_ROOT"
pwsh scripts/pg_sync_shared_assets.ps1 -RepoName "NOME_DO_REPO"
```

### Notas de compatibilidade

- O `.pg_framework/` e criado como symlink no Linux/macOS e como Junction no Windows. Para garantir que o Git ignore corretamente ambos os casos, o `.gitignore` do template usa paths ancorados sem `/` final para `/.pg_framework` e `/vendor/odoo_src`.
- O `~/.claude/CLAUDE.md` global e criado automaticamente pelo bootstrap se ainda nao existir.
- Todos os outros scripts do template funcionam sem alteracoes com `pwsh`.

## Scripts incluidos

- `scripts/pg_bootstrap_repo.ps1`: aplica o template a um repositorio
- `scripts/pg_link_framework.ps1`: cria ou atualiza `.pg_framework/` para apontar para o framework partilhado
- `scripts/pg_clone_odoo_source.ps1`: faz clone ou update do source Odoo oficial em cache global por serie, cria ligacao `vendor/odoo_src` no repo e sincroniza o `PG_CONTEXT.md`
- `scripts/pg_clone_odoo_source.cmd`: wrapper para uso rapido em CMD
- `scripts/pg_init_scope_intake.ps1`: inicializa ou preenche o `PG_SCOPE_INTAKE.yaml`
- `scripts/pg_build_pg_context.ps1`: semeia blocos auto-geridos do `PG_CONTEXT.md` a partir do intake
- `scripts/pg_validate_scope_sync.ps1`: valida o contrato do snapshot factual de ambito antes de o aplicar
- `scripts/pg_apply_scope_sync.ps1`: aplica o ultimo snapshot factual de `.pg/PG_SCOPE_SYNC.json` ao `PG_CONTEXT.md`
- `scripts/pg_validate_project_status_sync.ps1`: valida o contrato do snapshot factual antes de o aplicar
- `scripts/pg_apply_project_status_sync.ps1`: aplica o ultimo snapshot factual de `.pg/PG_PROJECT_STATUS_SYNC.json` ao `PG_CONTEXT.md`
- `scripts/pg_validate_decisions_sync.ps1`: valida o contrato do snapshot factual de decisoes publicadas
- `scripts/pg_validate_risks_sync.ps1`: valida o contrato do snapshot factual de riscos oficiais publicados
- `scripts/pg_validate_deliveries_sync.ps1`: valida o contrato do snapshot factual de entregaveis oficiais publicados
- `scripts/pg_validate_requirements_sync.ps1`: valida o contrato do snapshot factual de requisitos oficiais publicados
- `scripts/pg_validate_project_plan_sync.ps1`: valida o contrato do snapshot factual do plano oficial publicado
- `scripts/pg_validate_budget_sync.ps1`: valida o contrato do snapshot factual do budget oficial publicado
- `scripts/pg_refresh_pg_context.ps1`: orquestra a aplicacao de scope sync, fallback de intake e status sync
- `scripts/pg_link_odoo_core.ps1`: wrapper legado que redireciona para o fluxo novo baseado em `git clone`
- `scripts/pg_link_odoo_core.cmd`: wrapper legado para uso rapido em CMD
- `scripts/pg_sync_pg_context.ps1`: deteta a versao do Odoo no source checkout e atualiza metadados no `PG_CONTEXT.md`
- `scripts/pg_smoke_test_repo.ps1`: smoke test estrutural e semantico minimo da framework, snapshots `.pg`, blocos `PG_AUTO` do `PG_CONTEXT.md` e higiene textual basica
- `scripts/pg_run_odoo_addon_tests.ps1`: executa instalacao, upgrade e suite automatizada minima do addon `pg_brodoo` em Odoo 19 local
- `scripts/pg_sync_shared_assets.ps1`: sincroniza ficheiros partilhados do template para repositorios ja bootstrapados, sem tocar no estado local do projeto
- `scripts/pg_bootstrap_assisted.ps1`: agrega bootstrap, sync de assets, clone opcional do source Odoo e smoke test final

Compatibilidade de agentes:
- Codex usa `AGENTS.md` como instrucoes locais do projeto.
- Claude Code usa `CLAUDE.md` como memoria de projeto.
- O `CLAUDE.md` do template importa `AGENTS.md` e `.pg_framework/templates/AGENTS_SHARED.md`, para evitar divergencia entre agentes.

Na baseline atual, os projetos bootstrapados passam tambem a receber um workflow GitHub que consegue regenerar `PG_CONTEXT.md` quando os snapshots `.pg` mudam no remoto.
Ver `docs/PG_GITHUB_CONTEXT_AUTOMATION.md`.

Exemplo rapido para correr os testes automatizados minimos do addon:

```powershell
powershell -ExecutionPolicy Bypass -File "$TEMPLATE_ROOT\scripts\pg_run_odoo_addon_tests.ps1"
```

## Publicar o proprio `_pg_template`

O `_pg_template` deve existir tambem como repositorio Git versionado.
Depois de criares o remoto, o fluxo minimo e este:

```powershell
cd $TEMPLATE_ROOT
git remote add origin URL_DO_REPO
git push -u origin main
```

Se o remoto ja existir:

```powershell
cd $TEMPLATE_ROOT
git remote -v
git push origin main
```

Recomendacao:

- manter `main` como branch de referencia da framework
- tratar `_pg_template` como source of truth
- so propagar para projetos bootstrapados o que ja foi consolidado no template

A politica de release da framework esta formalizada em `docs/PG_RELEASE_POLICY.md`.
A ultima release fechada continua a ser `v2.9.1`, mas a linha operativa atual passa a estar ancorada em `docs/PG_CURRENT_WORKING_STATE.md`, `docs/PG_V1_PILOT_REPORT_2026-04-20.md`, `docs/PG_V1_PILOT_VALIDATION_CHECKLIST.md` e `docs/PG_V1_MIRROR_MIGRATION_RUNBOOK.md`.
Os documentos `V29` ficam preservados como historico da linha anterior e nao devem ser usados como backlog dominante sem revalidacao explicita.

## O que o template passa a impor

- raciocinio consultivo antes de coding
- avaliacao obrigatoria de modulos standard adicionais
- consulta obrigatoria a `PG_CONTEXT.md`, codigo do projeto, `vendor/odoo_src` e documentacao oficial da mesma versao
- classificacao final da recomendacao
- justificacao explicita quando standard ou Studio nao chegam
- separacao entre `FACTO OBSERVADO`, `INFERENCIA` e `PONTO POR VALIDAR`

## Exemplo de decisao consultiva esperada

Pedido: "queremos aprovacoes multi-etapa em compras"

Fluxo esperado:
1. verificar se o projeto ja usa aprovacoes standard de compras
2. avaliar modulos standard adicionais relacionados com approvals, purchase ou studio-supported automation
3. avaliar se Studio cobre o gap sem risco contratual ou de upgrade excessivo
4. so depois propor custom, com justificacao e paths do source consultados

## Regras nao opcionais

- nunca alterar `vendor/odoo_src`
- nunca versionar o source Odoo
- nunca recomendar custom sem justificar porque as opcoes anteriores falham
- nunca fechar conclusoes com base em suposicoes
- manter `PG_CONTEXT.md` alinhado com a decisao atual do projeto
