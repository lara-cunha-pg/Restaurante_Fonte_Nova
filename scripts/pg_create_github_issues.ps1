param(
    [Parameter(Mandatory = $true)]
    [string]$RepoFullName,

    [string]$Token = $env:GITHUB_TOKEN,

    [string]$MilestoneTitle = 'V1 Redesign',

    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not $Token) {
    throw 'GitHub token em falta. Usa -Token ou define GITHUB_TOKEN.'
}

$repoParts = $RepoFullName.Split('/')
if ($repoParts.Count -ne 2) {
    throw "RepoFullName invalido: '$RepoFullName'. Usa o formato owner/repo."
}

$owner = $repoParts[0]
$repo = $repoParts[1]
$apiBase = "https://api.github.com/repos/$owner/$repo"

$headers = @{
    Authorization = "Bearer $Token"
    Accept        = 'application/vnd.github+json'
    'User-Agent'  = 'pg_create_github_issues.ps1'
    'X-GitHub-Api-Version' = '2022-11-28'
}

function Invoke-GitHubJson {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet('GET', 'POST')]
        [string]$Method,

        [Parameter(Mandatory = $true)]
        [string]$Uri,

        [object]$Body
    )

    $params = @{
        Method  = $Method
        Uri     = $Uri
        Headers = $headers
    }

    if ($null -ne $Body) {
        $params.ContentType = 'application/json'
        $params.Body = ($Body | ConvertTo-Json -Depth 20 -Compress)
    }

    return Invoke-RestMethod @params
}

function Get-AllIssues {
    $page = 1
    $all = @()

    while ($true) {
        $uri = "$apiBase/issues?state=all&per_page=100&page=$page"
        $batch = @(Invoke-GitHubJson -Method GET -Uri $uri)
        if (-not $batch -or $batch.Count -eq 0) {
            break
        }

        $all += $batch
        if ($batch.Count -lt 100) {
            break
        }

        $page += 1
    }

    return $all
}

function Get-OrCreateMilestone {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Title
    )

    $page = 1
    $milestones = @()

    while ($true) {
        $uri = "$apiBase/milestones?state=all&per_page=100&page=$page"
        $batch = @(Invoke-GitHubJson -Method GET -Uri $uri)
        if (-not $batch -or $batch.Count -eq 0) {
            break
        }

        $milestones += $batch
        if ($batch.Count -lt 100) {
            break
        }

        $page += 1
    }

    $existing = $milestones | Where-Object { $_.title -eq $Title } | Select-Object -First 1
    if ($existing) {
        return $existing.number
    }

    if ($DryRun) {
        Write-Host "[DRY RUN] Criaria milestone '$Title'"
        return $null
    }

    $created = Invoke-GitHubJson -Method POST -Uri "$apiBase/milestones" -Body @{
        title = $Title
    }
    Write-Host "Milestone criada: $($created.title) (#$($created.number))"
    return $created.number
}

function Get-LabelColor {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    switch ($Name) {
        'epic'     { return '5319e7' }
        'P1'       { return 'b60205' }
        'P2'       { return 'd93f0b' }
        'P3'       { return 'fbca04' }
        'sprint-1' { return '0e8a16' }
        'sprint-2' { return '1d76db' }
        'sprint-3' { return '0052cc' }
        'sprint-4' { return '5319e7' }
        'sprint-5' { return 'c5def5' }
        'sprint-6' { return 'bfdadc' }
        'sprint-7' { return 'f9d0c4' }
        'sprint-8' { return 'fef2c0' }
        default    { return 'ededed' }
    }
}

function Ensure-Label {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    $encoded = [System.Uri]::EscapeDataString($Name)
    $uri = "$apiBase/labels/$encoded"

    try {
        [void](Invoke-GitHubJson -Method GET -Uri $uri)
        return
    }
    catch {
        if ($_.Exception.Response.StatusCode.value__ -ne 404) {
            throw
        }
    }

    if ($DryRun) {
        Write-Host "[DRY RUN] Criaria label '$Name'"
        return
    }

    [void](Invoke-GitHubJson -Method POST -Uri "$apiBase/labels" -Body @{
        name  = $Name
        color = (Get-LabelColor -Name $Name)
    })

    Write-Host "Label criada: $Name"
}

$issues = @(
    @{
        title = 'Sprint 1 - Definir e implementar o novo contrato de dados do espelho'
        labels = @('epic', 'sprint-1', 'P1')
        body = @'
## Objetivo
Implementar o novo contrato base do espelho do projeto para o repositório, substituindo o modelo atual por artefactos simples, previsíveis e úteis para AI.

## Âmbito
- Definir schema de `.pg/project/project.json`
- Definir schema de `.pg/planning/planning.json`
- Definir schema de `.pg/tasks/tasks.json`
- Definir schema de `.pg/chatter/chatter.json`
- Definir schema de `.pg/attachments/attachments.json`
- Definir schema de `.pg/history/events.jsonl`
- Implementar builders/serializers base
- Garantir campos comuns: `odoo_model`, `odoo_id`, `record_url`, `synced_at`
- Preservar os bootstraps documentais existentes sem os expandir nesta fase
- Criar testes unitários dos payloads

## Dependências
- Nenhuma

## Critérios de aceitação
- Existe um contrato de dados claro para projeto, planeamento, tarefas, chatter, anexos e histórico
- Os payloads são gerados de forma consistente
- Todas as entidades incluem `odoo_model`, `odoo_id`, `record_url` e `synced_at`
'@
    }
    @{
        title = 'Sprint 2 - Refletir contexto estrutural e planeamento do projeto'
        labels = @('epic', 'sprint-2', 'P1')
        body = @'
## Objetivo
Refletir no repositório o contexto estrutural do projeto e os dados de planeamento necessários para controlo de âmbito e acompanhamento da execução.

## Âmbito
- Popular `project.json` com objetivo, descrição, âmbito incluído, âmbito excluído, entregáveis, restrições, pressupostos, stakeholders e responsáveis
- Popular `planning.json` com etapas, marcos, responsáveis, dependências, próximos passos, bloqueios e datas previstas
- Integrar dados vindos do addon de planeamento
- Garantir ligação entre orçamento adjudicado e plano inicial quando existir
- Validar perguntas de âmbito e próxima etapa com base no novo modelo

## Dependências
- Sprint 1 - Definir e implementar o novo contrato de dados do espelho

## Critérios de aceitação
- O repositório contém contexto suficiente para responder a `isto está dentro ou fora de âmbito?`
- O repositório contém contexto suficiente para responder a `qual a próxima etapa?` e `o que falta para a atingir?`
- `planning.json` reflete corretamente o planeamento do projeto
'@
    }
    @{
        title = 'Sprint 3 - Simplificar o onboarding e torná-lo o ponto único de configuração'
        labels = @('epic', 'sprint-3', 'P1')
        body = @'
## Objetivo
Redesenhar o onboarding para ser a principal funcionalidade de configuração do projeto, com poucos passos e linguagem funcional.

## Âmbito
- Redesenhar o wizard de onboarding
- Recolher projeto, repositório, branch, sync ativo e sync de chatter
- Recolher objetivo, descrição resumida, âmbito incluído, âmbito excluído, entregáveis, restrições, pressupostos, marcos e stakeholders
- Pré-preencher automaticamente dados já existentes no Odoo
- Garantir funcionamento com utilizador `Project User`
- Disparar sincronização inicial no final do onboarding
- Guardar estado e data do último onboarding aplicado

## Dependências
- Sprint 1 - Definir e implementar o novo contrato de dados do espelho
- Sprint 2 - Refletir contexto estrutural e planeamento do projeto

## Critérios de aceitação
- Um utilizador normal consegue configurar um projeto em poucos passos
- O projeto fica pronto para sincronização contínua
- O onboarding recolhe o contexto-base necessário para controlo de âmbito
'@
    }
    @{
        title = 'Sprint 4 - Implementar sincronização contínua de projeto e tarefas'
        labels = @('epic', 'sprint-4', 'P1')
        body = @'
## Objetivo
Substituir o publish manual pesado por sincronização incremental e contínua de projeto e tarefas para o repositório.

## Âmbito
- Mapear eventos relevantes de projeto e tarefas
- Implementar handlers de sync incremental
- Refletir criação, edição, mudança de etapa, conclusão, cancelamento e subtarefas
- Refletir registos operacionais relevantes com impacto no estado da tarefa
- Implementar deduplicação de eventos
- Implementar retry e reconciliação por cron/job
- Registar estado, timestamp e mensagem curta de cada sync

## Dependências
- Sprint 1 - Definir e implementar o novo contrato de dados do espelho
- Sprint 3 - Simplificar o onboarding e torná-lo o ponto único de configuração

## Critérios de aceitação
- Alterações em projeto e tarefas aparecem no repo com baixa latência
- Conclusão, cancelamento e mudança de etapa ficam refletidos
- Falhas de sync não bloqueiam o uso normal do Odoo
'@
    }
    @{
        title = 'Sprint 5 - Refletir chatter, notas internas e metadata de anexos'
        labels = @('epic', 'sprint-5', 'P1')
        body = @'
## Objetivo
Adicionar ao espelho do projeto o chatter relevante e a metadata dos anexos, de forma útil para consulta por humanos e por AI.

## Âmbito
- Refletir mensagens com cliente em `chatter.json`
- Refletir notas internas em `chatter.json`
- Distinguir tipo de entrada: cliente vs nota interna
- Associar cada entrada ao registo de origem e respetivo link Odoo
- Refletir metadata e link de anexos em `attachments.json`
- Alimentar `events.jsonl` com eventos de comunicação relevantes
- Aplicar limpeza mínima de ruído técnico quando necessário

## Dependências
- Sprint 1 - Definir e implementar o novo contrato de dados do espelho
- Sprint 4 - Implementar sincronização contínua de projeto e tarefas

## Critérios de aceitação
- O repo contém mensagens com cliente e notas internas relevantes
- Os anexos entram apenas com metadata e link
- O histórico simples é cronológico e consultável
'@
    }
    @{
        title = 'Sprint 6 - Gerar novo PG_CONTEXT.md a partir do espelho'
        labels = @('epic', 'sprint-6', 'P1')
        body = @'
## Objetivo
Redesenhar `PG_CONTEXT.md` para ser um documento consolidado, legível e derivado exclusivamente dos artefactos `.pg`.

## Âmbito
- Redesenhar template com 4 blocos: estrutural, planeamento, operação atual, comunicações/histórico recente
- Gerar `PG_CONTEXT.md` apenas a partir de `project.json`, `planning.json`, `tasks.json`, `chatter.json`, `attachments.json` e `events.jsonl`
- Incluir objetivo, âmbito incluído/excluído, entregáveis e restrições
- Incluir etapa atual, próxima etapa e o que falta para a atingir
- Incluir principais tarefas em aberto, bloqueios e próximos passos
- Incluir comunicações recentes relevantes
- Remover placeholders artificiais

## Dependências
- Sprint 2 - Refletir contexto estrutural e planeamento do projeto
- Sprint 4 - Implementar sincronização contínua de projeto e tarefas
- Sprint 5 - Refletir chatter, notas internas e metadata de anexos

## Critérios de aceitação
- Um humano lê rapidamente o estado do projeto
- O Codex consegue responder a perguntas de âmbito, planeamento e operação
- O documento é consistente com os snapshots `.pg`
'@
    }
    @{
        title = 'Sprint 7 - Simplificar UX e despromover funcionalidades legadas'
        labels = @('epic', 'sprint-7', 'P1')
        body = @'
## Objetivo
Remover da experiência principal tudo o que hoje cria complexidade sem servir a visão do produto.

## Âmbito
- Inventariar peças legadas que não encaixam na nova visão
- Retirar o fluxo consultivo do centro da UX
- Remover dependência funcional de `Recommendation Class` e `Consultive Gate` para o espelho
- Despromover publish manual por `scope`, `status`, `decisions`, `risks` e `deliveries`
- Simplificar menus, botões e vistas
- Manter apenas ações manuais úteis: `Onboarding`, `Sincronizar Agora`, `Regerar Contexto`
- Marcar funcionalidades antigas como `legacy` durante a transição

## Dependências
- Sprint 3 - Simplificar o onboarding e torná-lo o ponto único de configuração
- Sprint 4 - Implementar sincronização contínua de projeto e tarefas
- Sprint 6 - Gerar novo PG_CONTEXT.md a partir do espelho

## Critérios de aceitação
- O utilizador percebe o produto sem treino pesado
- O espelho funciona sem depender de workflows paralelos complexos
- O legado deixa de contaminar a experiência principal
'@
    }
    @{
        title = 'Sprint 8 - Migrar e validar a nova V1 num projeto real'
        labels = @('epic', 'sprint-8', 'P1')
        body = @'
## Objetivo
Validar a nova V1 num projeto real já em operação e fechar a adoção funcional.

## Âmbito
- Definir estratégia de coexistência temporária entre modelo antigo e novo
- Criar migração mínima para projetos já onboarded
- Regenerar snapshots no novo formato
- Validar ponta a ponta com `Odoo - Ancoravip Produção`
- Testar sequência completa: planeamento -> onboarding -> sync -> `PG_CONTEXT.md` -> consulta por Codex
- Criar checklist final por perfil: PM, consultor e programador
- Atualizar documentação operacional

## Dependências
- Sprint 1 - Definir e implementar o novo contrato de dados do espelho
- Sprint 2 - Refletir contexto estrutural e planeamento do projeto
- Sprint 3 - Simplificar o onboarding e torná-lo o ponto único de configuração
- Sprint 4 - Implementar sincronização contínua de projeto e tarefas
- Sprint 5 - Refletir chatter, notas internas e metadata de anexos
- Sprint 6 - Gerar novo PG_CONTEXT.md a partir do espelho
- Sprint 7 - Simplificar UX e despromover funcionalidades legadas

## Critérios de aceitação
- Um projeto real fica configurado e sincronizado com sucesso
- O repo é suficiente para apoiar PM, consultor e programador
- O Codex consegue apoiar dúvidas, ponto de situação e produção documental a partir do repo
'@
    }
)

$milestoneNumber = Get-OrCreateMilestone -Title $MilestoneTitle

$allLabels = $issues.labels | ForEach-Object { $_ } | Sort-Object -Unique
foreach ($label in $allLabels) {
    Ensure-Label -Name $label
}

$existingIssues = Get-AllIssues

foreach ($issue in $issues) {
    $existing = $existingIssues | Where-Object { -not $_.pull_request -and $_.title -eq $issue.title } | Select-Object -First 1
    if ($existing) {
        Write-Host "Issue ja existe: #$($existing.number) - $($issue.title)"
        continue
    }

    $payload = @{
        title  = $issue.title
        body   = $issue.body.Trim()
        labels = $issue.labels
    }

    if ($null -ne $milestoneNumber) {
        $payload.milestone = $milestoneNumber
    }

    if ($DryRun) {
        Write-Host "[DRY RUN] Criaria issue: $($issue.title)"
        continue
    }

    $created = Invoke-GitHubJson -Method POST -Uri "$apiBase/issues" -Body $payload
    Write-Host "Issue criada: #$($created.number) - $($created.title)"
}
