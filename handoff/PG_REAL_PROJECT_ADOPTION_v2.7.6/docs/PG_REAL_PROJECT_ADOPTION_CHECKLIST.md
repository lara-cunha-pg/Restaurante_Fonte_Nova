# PG_REAL_PROJECT_ADOPTION_CHECKLIST

## Objetivo

Esta checklist transforma a adocao da baseline `v2.7.x` num fluxo executavel para o primeiro projeto real.
Foi desenhada para reduzir risco na primeira adocao fora do piloto `brodoo_v2`, com foco especial em projetos `brownfield`, ou seja, projetos que ja estao em desenvolvimento.

Esta checklist nao substitui o guiao operativo.
Para execucao por um colega que nao acompanhou o desenvolvimento da framework, usar em conjunto com:
- `docs/PG_REAL_PROJECT_ADOPTION_RUNBOOK.md`
- `docs/PG_REAL_PROJECT_ADOPTION_REPORT_TEMPLATE.md`

Regra central:
- nao tentar reconstruir todo o passado do projeto
- consolidar apenas o estado atual do ambito, do status e da disciplina consultiva

## Quando usar esta checklist

Usar esta checklist quando:
- a framework vai ser adotada pela primeira vez num projeto real
- o projeto ja esta em curso
- existe um PM ou owner funcional disponivel para validar o estado atual
- o objetivo e colocar o projeto a gerar snapshots uteis rapidamente, sem arqueologia excessiva

Nao usar esta checklist como primeira opcao quando:
- o projeto esta em fase critica de go-live sem margem para ajustes
- o backlog esta caotico e ninguem consegue distinguir o que esta aprovado do que e apenas ruido operacional
- a equipa ainda nao consegue garantir ownership do `status sync` manual

## Baseline a fixar antes de comecar

- [ ] Fixar a release exata do template no repositorio alvo com `PG_TEMPLATE_REF`
- [ ] Usar uma baseline taggeada e nao `main`
- [ ] Evitar alteracoes funcionais locais antes de fechar o primeiro ciclo real

Recomendacao atual:
- baseline minima recomendada: `v2.7.6`

## Gate 0 - Escolha do projeto

Antes de arrancar esta checklist, garantir que ja existem:
- repositorio GitHub definido
- branch de testes definida
- projeto Odoo.sh definido
- base de dados de staging definida
- owner funcional ou PM nomeado

- [ ] Escolher um projeto real com complexidade baixa ou media
- [ ] Confirmar que existe um PM ou owner funcional disponivel
- [ ] Confirmar que existe um repositorio GitHub dedicado ao projeto
- [ ] Confirmar que ha margem para uma sessao inicial de consolidacao de `2h a 4h`
- [ ] Confirmar que nao e necessario reconstruir historico completo para o projeto ficar operavel

Criterio de saida:
- projeto escolhido
- owner nomeado
- repositorio definido

## Fase 1 - Preparacao tecnica minima

### 1. Repositorio

- [ ] Criar ou confirmar o repositorio GitHub do projeto
- [ ] Bootstrapar o repositorio com o `_pg_template`
- [ ] Sincronizar o addon `pg_brodoo`
- [ ] Clonar o source Odoo em `vendor/odoo_src` quando aplicavel

Fluxo recomendado:

```powershell
cd C:\Users\Utilizador\Desktop\Repos\_pg_template
.\scripts\pg_bootstrap_assisted.ps1 -RepoName "NOME_DO_REPO" -SyncAddon -CloneOdooSource -Series 19.0 -Edition community
```

### 2. GitHub

- [ ] Criar o secret `PG_TEMPLATE_REPO_TOKEN`
- [ ] Criar a variable `PG_TEMPLATE_REF`
- [ ] Confirmar que `PG_TEMPLATE_REF` aponta para a tag exata adotada
- [ ] Confirmar que o teste vai correr na branch de testes e nao numa branch produtiva

### 3. Smoke test local

- [ ] Correr o smoke test estrutural e semantico

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\Utilizador\Desktop\Repos\_pg_template\scripts\pg_smoke_test_repo.ps1 -RepoPath C:\Users\Utilizador\Desktop\Repos\NOME_DO_REPO -RequireOdooSource -CheckPgAiDevAssistant
```

Criterio de saida:
- repositorio bootstrapado
- smoke test sem erros
- workflow `PG Refresh Context` presente

## Fase 2 - Preparacao do Odoo e onboarding

### 4. Odoo.sh

- [ ] Confirmar o nome da branch de testes no Odoo.sh
- [ ] Fazer deploy da branch de teste
- [ ] Confirmar build sem erros
- [ ] Instalar ou fazer `Upgrade` ao modulo `PG AI Dev Assistant`
- [ ] Confirmar que a base de dados usada e a de staging/teste

### 5. Settings

- [ ] Configurar `GitHub Token`
- [ ] Configurar `OpenAI API Key`
- [ ] Configurar `GPT Prompt Model`
- [ ] Confirmar que o addon consegue importar/sincronizar repositorios GitHub
- [ ] Confirmar que o colega executor tem acesso suficiente para executar estes passos

### 6. Wizard de onboarding

- [ ] Abrir o wizard `PG AI Onboarding`
- [ ] Selecionar o projeto real
- [ ] Selecionar `Repository` e `Repository Branch`
- [ ] Ativar `Enable Scope Sync`
- [ ] Ativar `Enable Status Sync`
- [ ] Definir `Scope Sync Mode = Event Driven` quando fizer sentido
- [ ] Clicar `Validar Publish`
- [ ] Clicar `Aplicar Onboarding`

Criterio de saida:
- projeto ligado ao repo certo
- branch certa
- toggles de sync ativos

## Fase 3 - Consolidacao brownfield minima

### Regra principal

Nao classificar o projeto inteiro.
Classificar apenas o que esta vivo e relevante agora.

### 7. Metadados minimos do projeto

- [ ] `Project Phase`
- [ ] `Odoo Version`
- [ ] `Odoo Edition`
- [ ] `Odoo Environment`
- [ ] `Business Goal`
- [ ] `Current Request`
- [ ] `Current Process`
- [ ] `Problem Or Need`
- [ ] `Business Impact`
- [ ] `Repository Summary`

### 8. Tarefas a rever

- [ ] Rever apenas tarefas abertas, recentes ou claramente relevantes
- [ ] Limitar a primeira ronda a `10-20` tasks
- [ ] Ignorar tarefas fechadas antigas que ja nao tenham valor para o estado atual

### 9. Classificacao minima das tasks

Para cada task revista, marcar apenas uma destas:
- [ ] `approved_scope`
- [ ] `operational_backlog`
- [ ] `internal_note`

Nas tasks marcadas como `approved_scope`:
- [ ] preencher `Scope Summary`
- [ ] preencher `Acceptance Criteria` quando possivel
- [ ] confirmar `Scope Relevant = True`

Criterio de saida:
- existe um conjunto pequeno e coerente de tasks em `approved_scope`
- backlog operacional deixa de contaminar o ambito aprovado

## Fase 4 - Primeiro ciclo factual

### 10. Primeiro publish de ambito

- [ ] Clicar `Publicar Ambito`
- [ ] Validar `PG Scope Sync Run = done`
- [ ] Confirmar atualizacao de `.pg/PG_SCOPE_SYNC.json`
- [ ] Confirmar execucao `Success` da GitHub Action `PG Refresh Context`
- [ ] Confirmar `PG_CONTEXT.md` atualizado no remoto

### 11. Primeiro status operacional

- [ ] Clicar `Gerar Draft de Situacao`
- [ ] Rever o draft
- [ ] Clicar `Aplicar Draft ao Status`
- [ ] Corrigir manualmente `Status Summary`
- [ ] Corrigir manualmente `Blockers`
- [ ] Corrigir manualmente `Risks`
- [ ] Corrigir manualmente `Next Steps`
- [ ] Corrigir manualmente `Pending Decisions`
- [ ] Preencher `Status Owner`
- [ ] Clicar `Publicar Ponto de Situacao`
- [ ] Validar `PG Status Sync Run = done`
- [ ] Confirmar atualizacao de `.pg/PG_PROJECT_STATUS_SYNC.json`
- [ ] Confirmar nova execucao `Success` da GitHub Action `PG Refresh Context`

Criterio de saida:
- `PG_CONTEXT.md` ja reflete ambito atual e status atual do projeto

## Fase 5 - Primeiro ciclo consultivo real

### 12. Escolher uma task real

- [ ] Escolher uma task ativa e relevante
- [ ] Confirmar que a task tem contexto funcional minimo

### 13. Fechar o fluxo consultivo

- [ ] Preencher `Standard Review`
- [ ] Preencher `Additional Module Review` quando aplicavel
- [ ] Preencher `Studio Review` quando aplicavel
- [ ] Definir `Recommendation Class`
- [ ] Preencher `Recommendation Justification`
- [ ] Preencher `Consultive Gate Notes`
- [ ] Clicar `Marcar Gate Consultivo Pronto`
- [ ] Clicar `Gerar Prompt AI`

### 14. Validar a evidencia

- [ ] `Guided Consultive Flow` fica `Ready`
- [ ] `Consultive Gate` fica `Ready`
- [ ] `Consultive decision history` regista pelo menos `Gate Ready`
- [ ] `Consultive decision history` regista `Prompt Generated`
- [ ] `Prompt AI Draft` fica preenchido

Criterio de saida:
- a disciplina consultiva ficou validada numa task real

## Fase 6 - Dashboard e observacao operacional

### 15. Dashboard

- [ ] Abrir `PG Operational Dashboard`
- [ ] Confirmar que os contadores refletem o estado real do projeto
- [ ] Confirmar se existem projetos com atencao de scope
- [ ] Confirmar se existem projetos com atencao de status
- [ ] Confirmar tasks bloqueadas pelo gate
- [ ] Confirmar tasks prontas para AI
- [ ] Confirmar runs falhadas

### 16. Primeiras 2 semanas de operacao

Todos os dias uteis:
- [ ] rever dashboard
- [ ] rever runs falhadas
- [ ] rever stale state de status
- [ ] confirmar se o PM publicou status quando necessario
- [ ] confirmar se as tasks prontas para AI passaram pelo gate

No fim das 2 semanas:
- [ ] separar problemas em `bug`
- [ ] separar problemas em `melhoria UX`
- [ ] separar problemas em `nova evolucao de produto`

Criterio de saida:
- operacao minima estavel durante 2 semanas

## Go / No-Go da adocao

### Go

- [ ] bootstrap sem erros
- [ ] addon instalado/upgrade sem erros
- [ ] `scope sync` a funcionar
- [ ] `status sync` a funcionar
- [ ] GitHub Action a atualizar `PG_CONTEXT.md`
- [ ] onboarding wizard validado
- [ ] fluxo consultivo validado numa task
- [ ] dashboard coerente

### No-Go

- [ ] a equipa ainda nao consegue distinguir `approved_scope` de backlog operacional
- [ ] o PM nao assume o `status sync` manual
- [ ] a Action falha com frequencia
- [ ] o projeto precisa de reconstruir demasiado historico para gerar snapshots uteis

## Indicadores de esforco aceitavel

Esforco realista esperado:
- `2h a 3h` para projeto pequeno/medio minimamente organizado
- `4h a 6h` para projeto confuso mas recuperavel

Sinal de que a adocao ja esta demasiado lenta:
- mais de `50` tasks precisam de classificacao manual imediata
- o PM nao consegue dizer o que esta realmente aprovado
- o draft de status sai quase sempre inutil e precisa de reescrita total
- a equipa nao consegue operar o projeto sem reinterpretar tudo a cada sessao

## Quando justificar novo automatismo

Se a checklist acima ficar sistematicamente lenta, os automatismos mais uteis a considerar sao:
- sugestao inicial de `Scope Track` por stage/tag
- shortlist automatica de tasks candidatas a `approved_scope`
- draft de status mais forte para brownfield
- assistente de migracao brownfield orientado a consolidar apenas o presente

## Conclusao pratica

Se esta checklist for cumprida sem bloquear o projeto e sem exigir arqueologia extensa, a baseline `v2.7.x` ja e suficientemente madura para adocao real controlada.
Se o processo exigir reconstrucao pesada do historico, o problema nao esta apenas na framework; esta tambem na qualidade do estado atual do proprio projeto.

## Entregaveis esperados do executor

No fim da execucao, o colega deve devolver:
- esta checklist preenchida
- `docs/PG_REAL_PROJECT_ADOPTION_REPORT_TEMPLATE.md` preenchido
- SHAs principais do teste
- screenshots minimos de setup, runs, Action, task consultiva e dashboard
