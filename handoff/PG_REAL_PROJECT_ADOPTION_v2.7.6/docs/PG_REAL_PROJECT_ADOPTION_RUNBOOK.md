# PG_REAL_PROJECT_ADOPTION_RUNBOOK

## Objetivo

Este documento serve como guiao operacional completo para um colega executar a primeira adocao real da framework e do addon num projeto Parametro Global ja existente.

Este nao e um documento de desenho.
E um guiao de execucao.

Deve ser usado em conjunto com:
- `docs/PG_REAL_PROJECT_ADOPTION_CONTEXT.md`
- `docs/PG_REAL_PROJECT_ADOPTION_CHECKLIST.md`
- `docs/PG_REAL_PROJECT_ADOPTION_REPORT_TEMPLATE.md`

Para aprofundamento tecnico, consultar os documentos oficiais na raiz do repositorio `_pg_template`, em especial:
- `docs/PG_AI_DEV_ASSISTANT_OPERATIONS.md`
- `docs/PG_GITHUB_CONTEXT_AUTOMATION.md`
- `docs/PG_FRAMEWORK_ADDON_TEST_GUIDE.md`
- `docs/PG_TROUBLESHOOTING.md`

Regra:
- esta pasta `handoff` e apenas orientacao
- os scripts e o codigo a usar sao sempre os da raiz do repositorio `_pg_template`

## Publico-alvo

Este runbook foi escrito para um colega que:
- nao acompanhou o desenvolvimento da framework
- vai testar a adocao numa branch de testes
- vai usar uma base de dados de staging no Odoo.sh
- precisa de executar tudo de A a Z sem depender de contexto oral

## Baseline a testar

Baseline recomendada para a primeira adocao real:
- `_pg_template v2.7.6`

Regra:
- usar tag/version fixa
- nao testar contra `main`

## O que esta em avaliacao

O objetivo do teste nao e "ver se o modulo instala".
O objetivo e validar o fluxo completo:

- setup do repositorio
- setup GitHub
- setup Odoo.sh e base de dados de staging
- onboarding do addon
- consolidacao minima brownfield
- `scope sync`
- `status sync`
- refresh automatico do `PG_CONTEXT.md`
- fluxo consultivo na task
- dashboard operacional

## Perimetro seguro do teste

Este teste deve correr apenas em:
- branch de testes do repositorio do projeto
- branch de staging no Odoo.sh
- base de dados de teste/staging

Nao usar:
- branch principal de desenvolvimento sem isolamento
- branch de producao
- base de dados de producao

## Inputs que o colega deve receber antes de comecar

Antes do arranque, quem entrega a tarefa deve fornecer:

- nome do repositorio GitHub do projeto
- URL do projeto Odoo.sh
- nome da branch de testes
- confirmacao de qual a branch base do projeto
- acesso ao repositorio GitHub
- acesso ao projeto Odoo.sh
- acesso ao Odoo backend da base de staging
- token GitHub para o addon, se nao estiver ja configurado
- `OpenAI API Key`, se tambem se pretender validar `Gerar Prompt AI`
- confirmacao de quem e o PM ou owner funcional que valida o estado atual

Se algum destes inputs faltar, o teste nao deve arrancar.

## Resultado esperado no fim

No fim deste runbook, o colega deve conseguir provar:

- o repositorio esta alinhado com a baseline taggeada
- o addon instala/upgrade na branch de testes
- o Odoo publica snapshots factuais de ambito e status
- o GitHub Action regenera o `PG_CONTEXT.md`
- a task exige disciplina consultiva antes do fluxo AI
- o dashboard operacional reflete corretamente o estado do projeto

## Fase 0 - Preparar a pasta local

### Objetivo

Garantir que o colega consegue trabalhar localmente no repositorio antes de tocar no Odoo.

### Passos

1. Confirmar que tem localmente:
- Git
- PowerShell
- acesso a `C:\Users\Utilizador\Desktop\Repos`

2. Fazer clone do repositorio do projeto, se ainda nao existir localmente:

```powershell
cd C:\Users\Utilizador\Desktop\Repos
git clone URL_DO_REPO
```

3. Entrar no repositorio:

```powershell
cd C:\Users\Utilizador\Desktop\Repos\NOME_DO_REPO
```

4. Confirmar a branch atual:

```powershell
git branch --show-current
git status
```

### Evidencia

- screenshot ou texto de `git branch --show-current`
- screenshot ou texto de `git status`

## Fase 1 - Preparar a branch de testes

### Objetivo

Garantir que o teste corre numa branch isolada.

### Passos

1. Fazer checkout da branch base do projeto:

```powershell
git checkout NOME_DA_BRANCH_BASE
git pull origin NOME_DA_BRANCH_BASE
```

2. Criar ou atualizar a branch de testes:

```powershell
git checkout -B NOME_DA_BRANCH_DE_TESTE
git push -u origin NOME_DA_BRANCH_DE_TESTE
```

Se a branch ja existir:

```powershell
git checkout NOME_DA_BRANCH_DE_TESTE
git pull origin NOME_DA_BRANCH_DE_TESTE
```

### Evidencia

- nome da branch de testes
- SHA do commit de partida

## Fase 2 - Alinhar o repositorio com a baseline da framework

### Objetivo

Levar o repositorio do projeto para a baseline atual sem depender de copias manuais de ficheiros.

### Caso A. O projeto ainda nao foi bootstrapado

Usar:

```powershell
cd C:\Users\Utilizador\Desktop\Repos\_pg_template
.\scripts\pg_bootstrap_assisted.ps1 -RepoName "NOME_DO_REPO" -SyncAddon -CloneOdooSource -Series 19.0 -Edition community
```

### Caso B. O projeto ja foi bootstrapado

Usar:

```powershell
cd C:\Users\Utilizador\Desktop\Repos\_pg_template
.\scripts\pg_sync_shared_assets.ps1 -RepoName "NOME_DO_REPO" -SyncAddon
```

### Confirmacoes obrigatorias

No repositorio do projeto, confirmar:
- `.pg_framework`
- `.github/workflows/pg_refresh_pg_context.yml`
- `PG_CONTEXT.md`
- `PG_SCOPE_INTAKE.yaml`
- `.pg/PG_SCOPE_SYNC.json`
- `.pg/PG_PROJECT_STATUS_SYNC.json`
- `pg_brodoo`

### Smoke test

Executar:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\Utilizador\Desktop\Repos\_pg_template\scripts\pg_smoke_test_repo.ps1 -RepoPath C:\Users\Utilizador\Desktop\Repos\NOME_DO_REPO -RequireOdooSource -CheckPgAiDevAssistant
```

### Commit da baseline no projeto

Se o alinhamento alterou ficheiros:

```powershell
cd C:\Users\Utilizador\Desktop\Repos\NOME_DO_REPO
git status
git add .
git commit -m "chore: adopt _pg_template v2.7.6 baseline"
git push origin NOME_DA_BRANCH_DE_TESTE
```

### Evidencia

- output do smoke test
- `git status`
- SHA do commit da baseline no projeto

## Fase 3 - Configurar o GitHub do projeto

### Objetivo

Garantir que o repositorio consegue regenerar `PG_CONTEXT.md` automaticamente.

### 1. Secret obrigatorio

No GitHub do projeto:
- `Settings`
- `Secrets and variables`
- `Actions`
- `Secrets`

Criar:
- `PG_TEMPLATE_REPO_TOKEN`

Permissao minima:
- leitura do repositorio `_pg_template`

### 2. Variable obrigatoria

No GitHub do projeto:
- `Settings`
- `Secrets and variables`
- `Actions`
- `Variables`

Criar:
- `PG_TEMPLATE_REF = v2.7.6`

Opcional:
- `PG_TEMPLATE_REPO = bruno-pinheiro-pg/_pg_template`

### Evidencia

- screenshot do secret existente
- screenshot da variable `PG_TEMPLATE_REF = v2.7.6`

## Fase 4 - Preparar Odoo.sh e a base de staging

### Objetivo

Garantir que a branch de testes do repositorio esta ligada a uma build utilizavel no Odoo.sh.

### Passos

1. Abrir o projeto no Odoo.sh
2. Ir a `Branches`
3. Selecionar a branch de testes
4. Confirmar que existe uma build da branch de testes
5. Esperar a build terminar
6. Validar que a build nao tem `ERROR` ou `Traceback`

Se a branch de staging ainda nao existir no Odoo.sh:
- criar primeiro a branch de staging/teste no GitHub
- esperar o Odoo.sh reconhece-la

### Evidencia

- screenshot da branch de testes
- screenshot da build com sucesso

## Fase 5 - Instalar ou fazer upgrade do addon

### Objetivo

Garantir que a base de staging ja esta com a versao certa do addon.

### Passos

1. Abrir a base de staging
2. Ir a `Apps`
3. Atualizar a lista de apps se necessario
4. Procurar `PG AI Dev Assistant`
5. Se nao estiver instalado:
- instalar

6. Se ja estiver instalado:
- fazer `Upgrade`

7. Confirmar que:
- o projeto mostra a tab `PG Scope Sync`
- a task mostra a tab `AI Dev Assistant`
- a task mostra a tab `PG Scope`

### Evidencia

- screenshot do modulo instalado ou upgraded
- screenshot da tab `PG Scope Sync` no projeto
- screenshot da tab `AI Dev Assistant` numa task

## Fase 6 - Configurar Settings do addon

### Objetivo

Garantir que o addon tem credenciais e modelos minimos para funcionar.

### Passos

1. Ir a `Settings`
2. Encontrar a secao `AI Development`
3. Confirmar ou preencher:
- `GitHub Token`
- `OpenAI API Key`
- `GPT Prompt Model`

4. Se necessario:
- clicar `Importar e Sync GitHub`
- clicar `Atualizar Modelos`

### Evidencia

- screenshot da secao `GitHub Delivery`
- screenshot da secao `OpenAI Prompt Generation`

## Fase 7 - Executar o onboarding wizard

### Objetivo

Ligar o projeto real ao repositorio e branch corretos sem configuracao dispersa.

### Passos

1. Abrir `PG AI Onboarding`
2. Selecionar:
- `Project`
- `Repository`
- `Repository Branch`

3. Ativar:
- `Enable Scope Sync`
- `Enable Status Sync`

4. Definir:
- `Scope Sync Mode = Event Driven`

5. Clicar:
- `Validar Publish`
- `Aplicar Onboarding`

### Validacao

No projeto, confirmar:
- `PG Repository`
- `PG Repo Branch`
- `Scope Sync Enabled`
- `Status Sync Enabled`
- `Scope Sync Mode`

### Evidencia

- screenshot do wizard preenchido
- screenshot do projeto depois do onboarding aplicado

## Fase 8 - Consolidacao brownfield minima

### Objetivo

Estruturar apenas o presente do projeto.

### Regra

Nao tentar classificar todo o historico.
Olhar apenas para tasks abertas, recentes ou claramente relevantes.

### Passos

1. No projeto, preencher ou rever:
- `Project Phase`
- `Odoo Version`
- `Odoo Edition`
- `Odoo Environment`
- `Business Goal`
- `Current Request`
- `Current Process`
- `Problem Or Need`
- `Business Impact`
- `Repository Summary`

2. Rever apenas `10-20` tasks no maximo na primeira ronda
3. Marcar cada task revista como:
- `approved_scope`
- `operational_backlog`
- `internal_note`

4. Nas tasks `approved_scope`, preencher:
- `Scope Summary`
- `Acceptance Criteria`, quando possivel

### Evidencia

- screenshot do projeto com metadados minimos
- lista das tasks revistas
- contagem de tasks em `approved_scope`

## Fase 9 - Primeiro ciclo factual de scope

### Passos

1. No projeto, clicar `Publicar Ambito`
2. Abrir `Ver Scope Sync`
3. Confirmar que a run termina em `done`
4. No GitHub do projeto, confirmar commit:
- `chore(pg-sync): refresh project scope from odoo`

5. Ir a `Actions`
6. Abrir `PG Refresh Context`
7. Confirmar execucao `Success`
8. Confirmar commit automatico:
- `chore(pg-sync): refresh PG_CONTEXT from snapshots [skip ci]`

### Local

```powershell
cd C:\Users\Utilizador\Desktop\Repos\NOME_DO_REPO
git pull origin NOME_DA_BRANCH_DE_TESTE
Get-Content .\.pg\PG_SCOPE_SYNC.json
Get-Content .\PG_CONTEXT.md
```

### Evidencia

- screenshot da run `Scope Sync`
- SHA do commit do snapshot
- SHA do commit automatico de refresh
- screenshot ou diff do `PG_CONTEXT.md`

## Fase 10 - Primeiro ciclo factual de status

### Passos

1. No projeto, clicar `Gerar Draft de Situacao`
2. Rever o draft
3. Clicar `Aplicar Draft ao Status`
4. Ajustar manualmente:
- `Status Summary`
- `Blockers`
- `Risks`
- `Next Steps`
- `Pending Decisions`
- `Status Owner`

5. Clicar `Publicar Ponto de Situacao`
6. Abrir `Ver Status Sync`
7. Confirmar que a run termina em `done`
8. No GitHub do projeto, confirmar commit:
- `chore(pg-sync): refresh project status from odoo`
9. Confirmar nova execucao `Success` de `PG Refresh Context`

### Local

```powershell
cd C:\Users\Utilizador\Desktop\Repos\NOME_DO_REPO
git pull origin NOME_DA_BRANCH_DE_TESTE
Get-Content .\.pg\PG_PROJECT_STATUS_SYNC.json
Get-Content .\PG_CONTEXT.md
```

### Evidencia

- screenshot da run `Status Sync`
- SHA do commit do snapshot de status
- SHA do commit automatico de refresh
- screenshot ou diff do `PG_CONTEXT.md`

## Fase 11 - Primeiro ciclo consultivo real

### Passos

1. Escolher uma task ativa e relevante
2. Abrir a tab `AI Dev Assistant`
3. Confirmar o bloco `Guided Consultive Flow`
4. Preencher:
- `Standard Review`
- `Additional Module Review` quando aplicavel
- `Studio Review` quando aplicavel
- `Recommendation Class`
- `Recommendation Justification`
- `Consultive Gate Notes`

5. Clicar `Marcar Gate Consultivo Pronto`
6. Clicar `Gerar Prompt AI`

### Validacao

Confirmar:
- `Guided Consultive Flow = Ready`
- `Consultive Gate = Ready`
- `Consultive decision history` tem `Gate Ready`
- `Consultive decision history` tem `Prompt Generated`
- `Prompt AI Draft` esta preenchido

### Evidencia

- screenshot da task antes do gate
- screenshot da task depois do gate
- screenshot do historico consultivo
- screenshot do prompt gerado

## Fase 12 - Dashboard operacional

### Passos

1. Abrir `Project > Configuration > PG Operational Dashboard`
2. Confirmar os contadores:
- `Scope Attention Project Count`
- `Status Attention Project Count`
- `Blocked AI Task Count`
- `AI-Ready Task Count`
- `Failed Scope Sync Run Count`
- `Failed Status Sync Run Count`

3. Validar se os numeros batem certo com o estado atual

### Evidencia

- screenshot do dashboard

## Fase 13 - Smoke test final

### Passos

```powershell
cd C:\Users\Utilizador\Desktop\Repos\NOME_DO_REPO
git pull origin NOME_DA_BRANCH_DE_TESTE
powershell -ExecutionPolicy Bypass -File C:\Users\Utilizador\Desktop\Repos\_pg_template\scripts\pg_smoke_test_repo.ps1 -RepoPath C:\Users\Utilizador\Desktop\Repos\NOME_DO_REPO -RequireOdooSource -CheckPgAiDevAssistant
```

### Resultado esperado

- smoke test sem erros

### Evidencia

- output completo do smoke test

## Criterios de stop imediato

Parar e escalar se acontecer um destes casos:

- build Odoo.sh falha com erro real
- addon nao instala ou nao faz upgrade
- token GitHub nao permite sync
- `PG Refresh Context` falha repetidamente
- o projeto exige classificacao massiva de historico para produzir um primeiro snapshot util

## Entrega final do colega

No fim, o colega deve entregar:

1. checklist preenchida:
- `docs/PG_REAL_PROJECT_ADOPTION_CHECKLIST.md`

2. relatorio preenchido:
- `docs/PG_REAL_PROJECT_ADOPTION_REPORT_TEMPLATE.md`

3. anexo ou nota com:
- SHAs relevantes
- screenshots
- output do smoke test
- lista curta de problemas encontrados

## Regra de interpretacao final

Se o colega conseguir fechar este runbook sem arqueologia extensa e sem falhas repetidas de infraestrutura, a baseline `v2.7.6` fica validada para adocao controlada em projetos reais brownfield.
