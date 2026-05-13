# CHANGELOG

Todas as evolucoes relevantes do `_pg_template` devem ser registadas neste ficheiro.

## v2.9.1 - 2026-04-24

Status:
- melhoria incremental compativel sobre a baseline `v2.9.0`

Resumo:
- `pg_clone_odoo_source` passa a usar cache global por serie em `%USERPROFILE%\.pg\odoo_src` (ou `PG_ODOO_SOURCE_ROOT`)
- cada repositorio deixa de duplicar o source Odoo e passa a ter `vendor/odoo_src` como ligacao para o cache global
- documentacao de setup e README atualizados para o novo fluxo partilhado

## v2.9.0 - 2026-04-12

Status:
- release de fecho formal da iteracao `v2.9`

Resumo:
- fecho formal da iteracao `v2.9`
- baseline `grounded chatter signals` promovida a release `v2.9.0`
- pipeline de ingestao, filtro, classificacao, validacao, grounding e explainability de sinais do chatter de projeto e task
- enriquecimento controlado de `status draft`, `consultive draft` e `scope draft` com sinais validados do chatter
- dashboard operacional com visibilidade agregada sobre sinais `candidate`, `validated`, `stale` e `rejected`
- apoio LLM controlado apenas para mensagens ambiguas do chatter, com JSON estrito, validacao forte e fallback deterministico

## v2.8.3 - 2026-04-12

Status:
- melhoria incremental compativel sobre a baseline `v2.8.2`

Resumo:
- apoio LLM controlado para mensagens ambiguas do chatter, restrito a classificacao em JSON estrito com validacao forte e fallback deterministico
- rejeicao automatica de saidas LLM fora de schema, contraditorias ou sem evidencia textual presente na mensagem original
- endurecimento da classificacao de sinais de `approval` para excluir estados pendentes como `waiting for approval`, evitando falsos positivos no grounding dos drafts

## v2.8.2 - 2026-04-10

Status:
- melhoria incremental compativel sobre a baseline `v2.8.0`

Resumo:
- pipeline de sinais de chatter fechada na install/upgrade do addon com cron e vistas carregadas pelo manifesto
- `status draft`, `consultive draft` e `scope draft` passam a consumir sinais validados do chatter como grounding secundario e auditavel
- dashboard operacional passa a expor visibilidade agregada sobre sinais validados, candidatos, stale e targets com refresh em falta

## v2.8.1 - 2026-04-10

Status:
- melhoria incremental compativel sobre a baseline `v2.8.0`

Resumo:
- abertura formal da `v2.9` com backlog objetivo em `docs/PG_V29_BACKLOG.md`
- `grounded chatter signals` fixado como proxima frente estrutural da framework
- `README`, roadmap e backlog alinhados para preparar o arranque da implementacao da `v2.9`

## v2.8.0 - 2026-04-09

Status:
- release de fecho formal da iteracao `v2.8`

Resumo:
- fecho formal da iteracao `v2.8`
- baseline brownfield acceleration promovida a release `v2.8.0`
- draft heuristico de enriquecimento de scope na task para `Scope Summary`, `Acceptance Criteria` e `Scope Kind`
- geracao e aplicacao assistida em massa desses drafts ao nivel do projeto
- dashboard brownfield incorporado no dashboard operacional
- draft operacional reforcado para projetos antigos
- pre-preenchimento consultivo assistido na task

## v2.7.13 - 2026-04-09

Status:
- melhoria incremental compativel sobre a baseline `v2.7.12`

Resumo:
- a `project.task` passa a suportar drafts consultivos assistidos para `Recommendation Class`, `Standard Review`, `Additional Module Review`, `Studio Review` e `Recommendation Justification`
- as sugestoes passam a ter score de confianca, feedback explicito e modulo adicional sugerido quando aplicavel
- a aplicacao continua assistida e so promove campos oficiais ainda vazios, mantendo a separacao entre draft consultivo e decisao final oficial

## v2.7.12 - 2026-04-09

Status:
- melhoria incremental compativel sobre a baseline `v2.7.11`

Resumo:
- o draft operacional passa a considerar explicitamente sinais brownfield vindos do `approved_scope`, backlog operacional, drafts `needs_review` e runs com erro
- o feedback do draft no projeto passa a indicar quando a consolidacao brownfield ainda esta incompleta antes do publish manual
- blockers, risks, next steps e pending decisions ficam mais uteis em projetos antigos sem transformar o publish oficial em automatico

## v2.7.11 - 2026-04-09

Status:
- melhoria incremental compativel sobre a baseline `v2.7.10`

Resumo:
- o `PG Operational Dashboard` passa a incluir um bloco brownfield para consolidacao inicial de projetos antigos
- novos contadores e listas destacam tasks `approved_scope` sem `Scope Summary`, sem `Acceptance Criteria`, sem `Scope Kind` e drafts `needs_review`
- a visibilidade brownfield fica agregada no dashboard existente, sem criar uma superficie operacional paralela

## v2.7.10 - 2026-04-09

Status:
- melhoria incremental compativel sobre a baseline `v2.7.9`

Resumo:
- novas acoes no projeto para gerar drafts de enriquecimento de scope em massa e aplicar sugestoes elegiveis de alta confianca
- o projeto passa a expor contadores de consolidacao brownfield para drafts pendentes, casos `needs_review` e sugestoes aplicadas
- o `scope sync` continua a publicar apenas campos oficiais, mesmo quando os drafts sao gerados ao nivel do projeto

## v2.7.9 - 2026-04-09

Status:
- melhoria incremental compativel sobre a baseline `v2.7.8`

Resumo:
- novo draft heuristico de enriquecimento de scope ao nivel da task para sugerir `Scope Kind`, `Scope Summary` e `Acceptance Criteria`
- as sugestoes passam a ter score de confianca, feedback e metadados de geracao, sem contaminar o `scope sync` factual ate aplicacao explicita
- nova cobertura automatizada garante que os campos sugeridos nao entram no `PG_SCOPE_SYNC.json` antes de serem promovidos a campos oficiais

## v2.7.8 - 2026-04-09

Status:
- melhoria incremental compativel sobre a baseline `v2.7.7`

Resumo:
- nova abertura formal da `v2.8` com backlog objetivo em `docs/PG_V28_BACKLOG.md`
- `brownfield acceleration` fixado como proxima frente prioritaria da framework
- roadmap e documentacao central alinhados para colocar o enriquecimento de scope como `P0`

## v2.7.7 - 2026-04-09

Status:
- melhoria incremental compativel sobre a baseline `v2.7.6`

Resumo:
- novo `docs/PG_SCOPE_ENRICHMENT_TECHNICAL_DESIGN.md` com desenho tecnico do automatismo para reduzir dependencia manual de `Scope Summary`, `Acceptance Criteria` e `Scope Kind`
- roadmap atualizado para fixar `brownfield acceleration` como proxima frente recomendada apos a `v2.7`
- documentacao central alinhada para refletir a nova prioridade de automatismo

## v2.7.6 - 2026-04-02

Status:
- melhoria incremental compativel sobre a baseline `v2.7.5`

Resumo:
- novo `docs/PG_REAL_PROJECT_ADOPTION_RUNBOOK.md` com execucao A a Z para um colega testar a adocao da framework num projeto real em branch de testes e base de staging
- novo `docs/PG_REAL_PROJECT_ADOPTION_REPORT_TEMPLATE.md` para recolha estruturada de evidencias, SHAs, problemas e decisao `Go / No-Go`
- `docs/PG_REAL_PROJECT_ADOPTION_CHECKLIST.md` ajustada para branch de testes, base de staging, handoff entre colegas e entregaveis finais do executor

## v2.7.5 - 2026-04-02

Status:
- melhoria incremental compativel sobre a baseline `v2.7.4`

Resumo:
- novo `docs/PG_REAL_PROJECT_ADOPTION_CHECKLIST.md` com checklist executavel para a primeira adocao real da framework
- foco explicito em projetos `brownfield`, com consolidacao do estado atual em vez de reconstrucao do historico
- criterios de esforco, gates de saida e sinais objetivos para decidir quando a adocao ja justifica mais automatismo

## v2.7.4 - 2026-04-02

Status:
- hotfix compativel sobre a baseline `v2.7.3`

Resumo:
- dark mode do separador `AI Dev Assistant` passa a usar asset `.dark.scss` proprio do Odoo
- remocao do fallback por `prefers-color-scheme`, que prendia o separador ao tema do sistema operativo
- o separador volta a acompanhar corretamente a preferencia light/dark definida no perfil do utilizador

## v2.7.3 - 2026-04-02

Status:
- hotfix compativel sobre a baseline `v2.7.2`

Resumo:
- segundo ajuste de UX do separador `AI Dev Assistant` para dark mode no backend do Odoo
- fallback adicional para ambientes onde o dark mode nao expoe `data-bs-theme="dark"`
- grelha/lista embebida do historico consultivo passa a herdar a paleta escura correta

## v2.7.2 - 2026-04-02

Status:
- hotfix compativel sobre a baseline `v2.7.1`

Resumo:
- UX do separador `AI Dev Assistant` alinhada com o tema light/dark do backend do Odoo
- substituicao de superficies e inputs com cores fixas por tokens semanticos theme-aware
- melhoria de contraste em dark mode para cards, textos, badges, info notes e textareas

## v2.7.1 - 2026-04-01

Status:
- hotfix compativel sobre a baseline `v2.7.0`

Resumo:
- leitura explicita UTF-8 nos scripts de refresh, smoke test e materializacao de contexto
- eliminacao de falsos positivos de mojibake no `PG_CONTEXT.md` em Windows PowerShell
- correcao do runtime partilhado usado pela GitHub Action `PG Refresh Context`

## v2.7.0 - 2026-04-01

Status:
- baseline formal de automacao intuitiva sobre a referencia `v2.6.0`

Resumo:
- fecho formal da iteracao `v2.7`
- GitHub Action para regenerar `PG_CONTEXT.md` a partir dos snapshots `.pg`
- drafts factuais de status com revisao e publish manual
- wizard de onboarding do addon
- fluxo consultivo guiado na task
- dashboard operacional centralizado
- release pronta para adocao como baseline `v2.7.0`

## v2.6.5 - 2026-04-01

Status:
- melhoria incremental compativel sobre a baseline `v2.6.0`

Resumo:
- novo fluxo consultivo guiado na task, com etapas explicitas de discovery, fit-gap, recomendacao final e gate
- a task passa a mostrar qual o passo atual e o que falta para desbloquear AI
- a UX do fluxo AI deixa de depender tanto de memoria metodologica informal
- testes automatizados passam a cobrir a progressao guiada do fluxo consultivo

## v2.6.6 - 2026-04-01

Status:
- melhoria incremental compativel sobre a baseline `v2.6.0`

Resumo:
- novo dashboard operacional centralizado do addon
- agregacao de projetos com atencao de scope/status, tasks bloqueadas ou prontas para AI e runs falhadas
- dashboard passa a abrir diretamente as listas filtradas para acao operacional
- testes automatizados passam a cobrir a agregacao principal do dashboard

## v2.6.4 - 2026-04-01

Status:
- melhoria incremental compativel sobre a baseline `v2.6.0`

Resumo:
- novo wizard de onboarding do addon para configurar GitHub e projeto num unico fluxo
- import da conta GitHub, sync de branches e validacao de readiness passam a estar acessiveis no wizard
- o wizard aplica repositorio, branch e toggles de scope/status sync sem obrigar a navegar por settings dispersas
- testes automatizados passam a cobrir o novo fluxo de onboarding

## v2.6.3 - 2026-04-01

Status:
- melhoria incremental compativel sobre a baseline `v2.6.0`

Resumo:
- geracao automatica de draft operacional no projeto antes do `status sync` oficial
- novas acoes `Gerar Draft de Situacao` e `Aplicar Draft ao Status`
- separacao explicita entre `draft` revisto e `published` manual
- testes automatizados do addon reforcados para validar o novo fluxo de draft

## v2.6.2 - 2026-04-01

Status:
- melhoria incremental compativel sobre a baseline `v2.6.0`

Resumo:
- novo workflow GitHub para regenerar `PG_CONTEXT.md` quando `.pg/PG_SCOPE_SYNC.json` ou `.pg/PG_PROJECT_STATUS_SYNC.json` mudam no remoto
- bootstrap e sync de assets passam a introduzir este workflow nos projetos
- novo guia `docs/PG_GITHUB_CONTEXT_AUTOMATION.md` com secret, variaveis e fluxo de adocao
- smoke test passa a validar a presenca e a semantica minima do workflow

## v2.6.1 - 2026-04-01

Status:
- melhoria incremental compativel com abertura da iteracao `v2.7`

Resumo:
- nova `docs/PG_V27_BACKLOG.md` com backlog orientado a automacao intuitiva da framework
- abertura formal da `v2.7` sem alterar a baseline funcional `v2.6.0`
- roadmap e versioning passam a refletir a nova frente: GitHub Action para `PG_CONTEXT.md`, auto-draft de status, wizard de onboarding, fluxo guiado consultivo e dashboard operacional

## v2.6.0 - 2026-04-01

Status:
- release de fecho formal da iteracao `v2.6`

Resumo:
- gating consultivo antes de AI entregue na `project.task`
- classificacao final obrigatoria `standard`, `modulo adicional`, `Studio` ou `custom`
- separacao explicita entre `approved_scope`, backlog operacional e notas internas
- trilho minimo de decisao consultiva com historico proprio na task
- `status sync` manual-only confirmado com indicador de `Needs Publish` e feedback de revisao
- backlog da `v2.6` fechado e baseline promovida a release taggeada

## v2.5.6 - 2026-04-01

Resumo:
- reavaliacao dirigida do `status sync` confirma a politica `manual-only`
- o projeto passa a sinalizar `Status Sync Needs Publish` quando o estado operacional muda depois do ultimo publish
- novo `Status Sync Review Feedback` torna visivel quando o publish manual ainda esta em falta
- nova nota arquitetural com criterio explicito para futura reavaliacao do `status sync`

## v2.5.5 - 2026-04-01

Resumo:
- novo trilho de decisao consultiva na `project.task`
- snapshots minimos de decisao passam a ser registados para `gate_ready`, `prompt_generated` e `codex_queued`
- o contexto entregue ao AI passa a incluir historico consultivo minimo, deixando de depender apenas do texto livre atual
- cobertura automatizada adicionada para `PG-V26-004`

## v2.5.4 - 2026-04-01

Resumo:
- separacao explicita entre `approved_scope`, `operational_backlog` e `internal_note` na task
- `.pg/PG_SCOPE_SYNC.json` passa a incluir apenas tasks classificadas como `approved_scope`
- backlog operacional e notas internas deixam de entrar em `scope_items`
- `PG_CONTEXT.md` continua focado no ambito factual aprovado
- cobertura automatizada adicionada para `PG-V26-003`

## v2.5.3 - 2026-04-01

Resumo:
- classificacao consultiva final obrigatoria na task antes do fluxo AI
- quatro classes suportadas: `standard`, `modulo adicional`, `Studio`, `custom`
- revisoes minimas por etapa e justificacao final passam a ser exigidas antes do gate consultivo poder ficar `ready`
- a classificacao e validada contra as restricoes do projeto e entra no contexto entregue ao AI
- novos testes automatizados do addon para `PG-V26-002`

## v2.5.2 - 2026-04-01

Status:
- melhoria incremental compativel

Resumo:
- novo gate consultivo minimo na `project.task` antes de `Gerar Prompt AI` e `Executar com Codex`
- o gate exige notas minimas e contexto factual basico no projeto antes de poder ser marcado como `ready`
- alteracoes relevantes na task ou no contexto consultivo do projeto reabrem automaticamente o gate
- novo conjunto de testes automatizados do gate em Odoo 19
- fecho do item `PG-V26-001` do backlog objetivo da `v2.6`

## v2.5.1 - 2026-04-01

Status:
- melhoria incremental compativel

Resumo:
- nova `docs/PG_V26_BACKLOG.md` com backlog objetivo da iteracao consultiva seguinte
- roadmap e backlog da `v2.5` passam a deixar explicito que a baseline tecnica ficou fechada e que a frente seguinte e governacao consultiva
- abertura formal da `v2.6` sem alterar a baseline funcional `v2.5.0`

## v2.5.0 - 2026-04-01

Status:
- melhoria incremental compativel com fecho da iteracao `v2.5`

Resumo:
- novo `scripts/pg_bootstrap_assisted.ps1` para agregar bootstrap, sync de assets, sync opcional do addon, clone opcional do source Odoo e smoke test final
- README e checklist de bootstrap passam a documentar um fluxo curto assistido para arranque de novos repositorios
- fecho do item `PG-V25-007` e conclusao formal da iteracao `v2.5`

## v2.4.11 - 2026-04-01

Status:
- melhoria incremental compativel

Resumo:
- novo `docs/PG_AI_DEV_ASSISTANT_OPERATIONS.md` com operacao dedicada do addon `pg_brodoo`
- setup GitHub, separacao entre sync factual e AI delivery, permissoes recomendadas e troubleshooting Odoo 19 passam a estar documentados num unico guia
- fecho do item `PG-V25-006` do backlog objetivo da `v2.5`

## v2.4.10 - 2026-04-01

Status:
- melhoria incremental compativel

Resumo:
- novo `docs/PG_CONTENT_HYGIENE.md` com checklist curta para encoding, placeholders e coerencia semantica do conteudo
- `pg_smoke_test_repo.ps1` passa a sinalizar mojibake, placeholders publicados e sobreposicoes suspeitas entre `risks`, `blockers`, `next_steps` e `pending_decisions`
- fecho do item `PG-V25-005` do backlog objetivo da `v2.5`

## v2.4.9 - 2026-04-01

Status:
- melhoria incremental compativel

Resumo:
- `PG_PROJECT_STATUS_SYNC` fica formalmente definido como `manual-only` na baseline atual
- fecho do item `PG-V25-004` do backlog objetivo da `v2.5`
- backlog, roadmap, README, versioning e guia de testes alinhados com a decisao de produto

## v2.4.8 - 2026-04-01

Status:
- melhoria incremental compativel

Resumo:
- `pg_smoke_test_repo.ps1` passa a validar semantica minima dos snapshots publicados e dos blocos `PG_AUTO` do `PG_CONTEXT.md`
- o smoke test diferencia falhas estruturais de warnings documentais
- fecho do item `PG-V25-003` do backlog objetivo da `v2.5`

## v2.4.7 - 2026-04-01

Status:
- melhoria incremental compativel

Resumo:
- nova `docs/PG_RELEASE_POLICY.md` com politica operacional de release do `_pg_template`
- fecho do item `PG-V25-002` do backlog objetivo da `v2.5`
- alinhamento entre README, versioning e backlog para promover baselines validadas a releases utilizaveis

## v2.4.6 - 2026-04-01

Status:
- melhoria incremental compativel

Resumo:
- nova suite automatizada minima do addon `pg_brodoo` para Odoo 19
- novo `scripts/pg_run_odoo_addon_tests.ps1` para validar instalacao, upgrade e testes locais do addon
- fecho do item `PG-V25-001` do backlog objetivo da `v2.5`

## v2.4.5 - 2026-04-01

Status:
- melhoria incremental compativel

Resumo:
- novo `docs/PG_V25_BACKLOG.md` com backlog objetivo, priorizado e orientado a criterios de aceitacao
- ligacao explicita entre roadmap, backlog e a proxima iteracao operacional da framework
- clarificacao do ponto de chegada esperado para o fecho da `v2.5`

## v2.4.4 - 2026-04-01

Status:
- melhoria incremental compativel

Resumo:
- novo `docs/PG_TROUBLESHOOTING.md` com resolucao dos problemas reais encontrados no piloto
- clarificacao operacional de scripts, snapshots placeholder, GitHub token, acesso a `odoo/enterprise`, Odoo 19 e encoding
- melhoria da capacidade de suporte e onboarding sem alterar a base funcional da framework

## v2.4.3 - 2026-04-01

Status:
- melhoria incremental compativel

Resumo:
- `.gitattributes` do template e dos repositorios bootstrapados passa a cobrir tambem `ps1`, `cmd`, `toml`, `json`, `yaml` e `.editorconfig`
- reducao do ruido de `LF/CRLF` em ficheiros operacionais criticos do template
- endurecimento coerente com a politica de escrita explicita em UTF-8 introduzida em `v2.4.1`

## v2.4.2 - 2026-04-01

Status:
- melhoria incremental compativel

Resumo:
- novo `pg_smoke_test_repo.ps1` para validacao rapida de repositorios bootstrapados
- novo `pg_sync_shared_assets.ps1` para sincronizar ficheiros partilhados do template em repositorios ja existentes
- documentacao do bootstrap reforcada para suportar alinhamento continuo entre `_pg_template` e projetos piloto

## v2.4.1 - 2026-04-01

Status:
- melhoria incremental compativel

Resumo:
- scripts que materializam `PG_CONTEXT.md` e `PG_SCOPE_INTAKE.yaml` passam a escrever ficheiros em UTF-8 explicito
- bootstrap passa a copiar `.editorconfig` para novos repositorios
- endurecimento contra problemas de encoding e line endings observados durante a validacao do piloto

## v2.4 - 2026-04-01

Status:
- mudanca estrutural relevante no template

Resumo:
- addon `pg_brodoo` passa a suportar publicacao manual de `.pg/PG_PROJECT_STATUS_SYNC.json`
- novos modelos e vistas de `PG Status Sync Runs` para rastreabilidade operacional do snapshot
- `PG_CONTEXT.md` passa a materializar tambem `scope_items` em bloco auto-gerido proprio
- correcoes de compatibilidade Odoo 19 consolidadas no addon durante o ciclo de validacao real
- guia de testes atualizado para incluir `status sync` e a nova versao funcional do addon

## v2.3 - 2026-03-31

Status:
- mudanca estrutural relevante no template

Resumo:
- fluxo principal de consulta ao Odoo passa de instalacao local do ERP para `git clone` do source oficial
- novo layout `vendor/odoo_src/community` e `vendor/odoo_src/enterprise`
- novo script `pg_clone_odoo_source` e sincronizacao do `PG_CONTEXT.md` adaptada ao source checkout
- `pg_link_odoo_core` passa a wrapper legado de compatibilidade

## v2.2 - 2026-03-31

Status:
- mudanca estrutural relevante no template

Resumo:
- novo contrato `.pg/PG_SCOPE_SYNC.json` para sync factual de ambito vindo do Odoo
- novos scripts para validar, aplicar e orquestrar scope sync no `PG_CONTEXT.md`
- bootstrap, `config.toml` e documentacao atualizados para suportar scope sync

## v2.1 - 2026-03-24

Status:
- melhoria incremental compativel sobre o v2.0

Resumo:
- contrato tecnico mais explicito para `.pg/PG_PROJECT_STATUS_SYNC.json`
- validacao dedicada do snapshot factual antes de atualizar o `PG_CONTEXT.md`
- documento de integracao Odoo -> repositorio com campos, botao manual e regras do payload

## v2.0 - 2026-03-24

Status:
- mudanca estrutural relevante no template

Resumo:
- `AGENTS.md` local passa a ser wrapper leve por projeto
- `templates/AGENTS_SHARED.md` concentra as regras partilhadas do framework
- bootstrap cria `.pg_framework/` como referencia local ao framework partilhado
- formalizacao tecnica do modelo shared framework vs project-local state

## v1.2 - 2026-03-24

Status:
- melhoria incremental compativel

Resumo:
- `PG_SCOPE_INTAKE.yaml` como fonte estruturada local para ambito inicial do projeto
- `.pg/PG_PROJECT_STATUS_SYNC.json` como snapshot factual do estado operacional vindo do Odoo
- scripts para inicializar intake, materializar blocos auto-geridos do `PG_CONTEXT.md` e aplicar o ultimo snapshot factual
- clarificacao do modelo partilhado vs local no framework

## v1.1 - 2026-03-24

Status:
- melhoria incremental compativel

Resumo:
- camada leve de discovery antes do `PG_CONTEXT`
- novo `PG_DISCOVERY_PROMPT.md` para qualificar pedidos incompletos, ambiguos ou ainda imaturos para decisao
- gate explicito para seguir para contexto, aprofundar discovery ou pedir demo / validacao standard

## v1.0 - [YYYY-MM-DD]

Status:
- ready for production use

Resumo:
- bootstrap consultivo para repositorios Odoo
- ordem obrigatoria de decisao: standard -> modulo adicional -> Studio -> custom
- gestao explicita de evidencia, incerteza e validacao contra o source Odoo de referencia
- memoria consultiva leve e checklist de verificacao antes de recomendacoes finais
