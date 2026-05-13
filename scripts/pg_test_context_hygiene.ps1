param()

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "pg_file_io_common.ps1")

function Assert-True {
  param(
    [bool]$Condition,
    [string]$Message
  )

  if (-not $Condition) {
    throw $Message
  }
}

function Assert-False {
  param(
    [bool]$Condition,
    [string]$Message
  )

  if ($Condition) {
    throw $Message
  }
}

function Assert-Contains {
  param(
    [string]$Text,
    [string]$Expected,
    [string]$Message
  )

  $haystack = if ($null -eq $Text) { '' } else { $Text }
  if (-not $haystack.Contains($Expected)) {
    throw $Message
  }
}

function Assert-NotContains {
  param(
    [string]$Text,
    [string]$Unexpected,
    [string]$Message
  )

  $haystack = if ($null -eq $Text) { '' } else { $Text }
  if ($haystack.Contains($Unexpected)) {
    throw $Message
  }
}

function Get-MarkedBlock {
  param(
    [string]$Text,
    [string]$Marker
  )

  $pattern = "(?s)<!-- PG_AUTO:$Marker`:START -->\s*(.*?)\s*<!-- PG_AUTO:$Marker`:END -->"
  $match = [regex]::Match($Text, $pattern)
  if (-not $match.Success) {
    throw "Marcadores nao encontrados para $Marker"
  }

  return $match.Groups[1].Value
}

function Join-Chars {
  param([int[]]$Codes)

  return ([string]::Concat(@($Codes | ForEach-Object { [char]$_ })))
}

function New-FixtureRepo {
  param(
    [string]$RootPath,
    [string]$Name,
    [switch]$DirtySnapshots
  )

  $repo = Join-Path $RootPath $Name
  New-Item -ItemType Directory -Path $repo -Force | Out-Null
  New-Item -ItemType Directory -Path (Join-Path $repo '.pg') -Force | Out-Null
  New-Item -ItemType Directory -Path (Join-Path $repo '.pg_framework\scripts') -Force | Out-Null
  New-Item -ItemType Directory -Path (Join-Path $repo '.pg_framework\templates') -Force | Out-Null
  New-Item -ItemType Directory -Path (Join-Path $repo '.github\workflows') -Force | Out-Null

  Copy-Item -LiteralPath (Join-Path (Split-Path -Parent $PSScriptRoot) '.editorconfig') -Destination (Join-Path $repo '.editorconfig') -Force
  Copy-Item -LiteralPath (Join-Path (Split-Path -Parent $PSScriptRoot) '.gitignore') -Destination (Join-Path $repo '.gitignore') -Force
  Copy-Item -LiteralPath (Join-Path (Split-Path -Parent $PSScriptRoot) '.gitattributes') -Destination (Join-Path $repo '.gitattributes') -Force
  Copy-Item -LiteralPath (Join-Path (Split-Path -Parent $PSScriptRoot) 'config.toml') -Destination (Join-Path $repo 'config.toml') -Force
  Copy-Item -LiteralPath (Join-Path (Split-Path -Parent $PSScriptRoot) 'templates\AGENTS.md') -Destination (Join-Path $repo 'AGENTS.md') -Force
  Copy-Item -LiteralPath (Join-Path (Split-Path -Parent $PSScriptRoot) 'templates\CLAUDE.md') -Destination (Join-Path $repo 'CLAUDE.md') -Force
  Copy-Item -LiteralPath (Join-Path (Split-Path -Parent $PSScriptRoot) 'templates\PG_CONTEXT.md') -Destination (Join-Path $repo 'PG_CONTEXT.md') -Force
  Copy-Item -LiteralPath (Join-Path (Split-Path -Parent $PSScriptRoot) 'templates\PG_SCOPE_INTAKE.yaml') -Destination (Join-Path $repo 'PG_SCOPE_INTAKE.yaml') -Force
  Copy-Item -LiteralPath (Join-Path (Split-Path -Parent $PSScriptRoot) 'templates\AGENTS_SHARED.md') -Destination (Join-Path $repo '.pg_framework\templates\AGENTS_SHARED.md') -Force
  Copy-Item -Path (Join-Path (Split-Path -Parent $PSScriptRoot) 'templates\.pg\*.json') -Destination (Join-Path $repo '.pg') -Force
  Copy-Item -Path (Join-Path $PSScriptRoot '*.ps1') -Destination (Join-Path $repo '.pg_framework\scripts') -Force
  Copy-Item -LiteralPath (Join-Path (Split-Path -Parent $PSScriptRoot) 'templates\.github\workflows\pg_refresh_pg_context.yml') -Destination (Join-Path $repo '.github\workflows\pg_refresh_pg_context.yml') -Force

  if ($DirtySnapshots) {
    $mojibakeCao = Join-Chars -Codes @(0x00C3, 0x00A7, 0x00C3, 0x00A3)
    $scopeSummary = "Integra${mojibakeCao}o de faturacao pronta para produ${mojibakeCao}o.`nBest regards,"
    $currentRequest = "Cliente pediu integra${mojibakeCao}o de faturacao com o ERP.`nOn Tue, 2 Apr 2026 at 10:00, Customer wrote:`n> Podem avancar."
    $acceptance = @('[PONTO POR VALIDAR]', 'Validar webhook GitHub', 'Validar webhook GitHub')
    $statusSummary = "Integra${mojibakeCao}o pronta para produ${mojibakeCao}o com checklist de go-live, sincronizacao de contactos, validacao de dados mestre, confirmacao do cliente e passagem assistida para operacao sem depender de follow-up informal por email."
    $nextSteps = @(
      "Validar deploy em producao",
      "On Tue, 2 Apr 2026 at 10:00, Customer wrote:",
      "> Aprovar deploy"
    )
    $blockers = @(
      "Blocked until customer approval.",
      "Best regards,",
      "Project Manager"
    )
    $risks = @(
      ('Risco operacional de atraso na integracao ' * 20).Trim()
    )
  }
  else {
    $scopeSummary = "Integracao de faturacao pronta para producao."
    $currentRequest = "Cliente pediu integracao de faturacao com o ERP."
    $acceptance = @('Validar webhook GitHub')
    $statusSummary = "Integracao pronta para producao."
    $nextSteps = @('Validar deploy em producao')
    $blockers = @('Blocked until customer approval.')
    $risks = @('Risco operacional de atraso na integracao.')
  }

  $scopePayload = [ordered]@{
    schema_version = '1.0'
    project_name = 'Projeto Hygiene'
    project_id = 99
    client_unit = 'Consulting'
    repository_summary = 'Repositorio piloto para validar higiene textual.'
    project_phase = 'delivery'
    odoo_version = '19.0'
    odoo_edition = 'community'
    odoo_environment = 'on_premise'
    restrictions = [ordered]@{
      standard_allowed = 'yes'
      additional_modules_allowed = 'yes'
      studio_allowed = 'yes'
      custom_allowed = 'yes'
      additional_contract_restrictions = @('Sem restricoes extra')
    }
    scope_overview = [ordered]@{
      business_goal = 'Automatizar faturacao.'
      current_request = $currentRequest
      current_process = 'Processo atual com validacao manual.'
      problem_or_need = 'Evitar retrabalho e ruido operacional.'
      business_impact = 'Menos erro manual e mais previsibilidade.'
      trigger = 'Pedido do cliente'
      frequency = 'Diaria'
      volumes = '50'
      urgency = 'high'
      acceptance_criteria = $acceptance
    }
    project_lists = [ordered]@{
      users_and_roles = @('PM', 'Consultor')
      known_exceptions = @('Sem excecoes')
      approvals = @('Aprovacao do cliente')
      documents = @('Documento funcional')
      integrations = @('GitHub')
      reporting_needs = @('Dashboard operacional')
      standard_attempted_or_validated = @('Configuracao standard revista')
      why_standard_was_insufficient = @('Necessidade de integracao externa')
    }
    scope_items = @(
      [ordered]@{
        task_id = 101
        task_name = 'Integracao faturacao'
        task_stage = 'Em Progresso'
        task_priority = '1'
        task_tags = @('integration')
        scope_track = 'approved_scope'
        scope_state = 'validated'
        scope_kind = 'integration'
        scope_sequence = 10
        scope_summary = $scopeSummary
        acceptance_criteria = $acceptance
        assigned_users = @('PM', 'PM')
        last_task_update_at = '2026-04-13 10:00:00'
        source_url = 'https://example.test/web#id=101&model=project.task'
      }
    )
    scope_summary = [ordered]@{
      active_scope_item_count = 1
      validated_scope_item_count = 1
      proposed_scope_item_count = 0
      deferred_scope_item_count = 0
      last_scope_change_at = '2026-04-13 10:00:00'
    }
    source_metadata = [ordered]@{
      source_system = 'odoo_parametro_global'
      source_model = 'project.project'
      source_record_id = 99
      source_record_url = 'https://example.test/web#id=99&model=project.project'
      sync_trigger = 'manual'
      sync_reason = 'manual publish'
      sync_published_at = '2026-04-13 10:05:00'
      sync_published_by = 'Test User'
      repo_branch = 'main'
      payload_hash = 'sha256:test-scope'
    }
  }

  $statusPayload = [ordered]@{
    schema_version = '1.0'
    project_name = 'Projeto Hygiene'
    last_update_at = '2026-04-13 10:07:00'
    phase = 'delivery'
    status_summary = $statusSummary
    milestones = @('Marco validado', 'Marco validado')
    blockers = $blockers
    risks = $risks
    next_steps = $nextSteps
    pending_decisions = @('[PREENCHER]', 'Confirmar data de go-live')
    go_live_target = '2026-05-01'
    owner = 'PM'
    source_reference = 'project.project 99 - Projeto Hygiene'
    source_system = 'odoo_parametro_global'
    source_model = 'project.project'
    source_record_id = '99'
    source_record_url = 'https://example.test/web#id=99&model=project.project'
    sync_published_at = '2026-04-13 10:10:00'
    sync_published_by = 'Test User'
    sync_trigger = 'manual_button'
    repo_branch = 'main'
  }

  Write-Utf8NoBomFile -Path (Join-Path $repo '.pg\PG_SCOPE_SYNC.json') -Content (($scopePayload | ConvertTo-Json -Depth 8) + "`n")
  Write-Utf8NoBomFile -Path (Join-Path $repo '.pg\PG_PROJECT_STATUS_SYNC.json') -Content (($statusPayload | ConvertTo-Json -Depth 8) + "`n")

  return $repo
}

function Invoke-PowerShellScript {
  param(
    [string]$ScriptPath,
    [string[]]$Arguments
  )

  $output = & powershell -NoProfile -ExecutionPolicy Bypass -File $ScriptPath @Arguments 2>&1
  $exitCode = $LASTEXITCODE
  return [pscustomobject]@{
    Output = ($output | Out-String)
    ExitCode = $exitCode
  }
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('pg_imp003_stage2_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null

try {
  $dirtyRepo = New-FixtureRepo -RootPath $tempRoot -Name 'dirty_repo' -DirtySnapshots
  $cleanRepo = New-FixtureRepo -RootPath $tempRoot -Name 'clean_repo'
  $cleanCao = Join-Chars -Codes @(0x00E7, 0x00E3)

  $dirtyRefresh = Invoke-PowerShellScript -ScriptPath (Join-Path $dirtyRepo '.pg_framework\scripts\pg_refresh_pg_context.ps1') -Arguments @('-RepoPath', $dirtyRepo)
  Assert-True -Condition ($dirtyRefresh.ExitCode -eq 0) -Message "Refresh falhou no fixture dirty: $($dirtyRefresh.Output)"

  $dirtyContext = Read-Utf8TextFile -Path (Join-Path $dirtyRepo 'PG_CONTEXT.md')
  $dirtyStatusBlock = Get-MarkedBlock -Text $dirtyContext -Marker 'STATUS_SYNC'
  $dirtyScopeBlock = Get-MarkedBlock -Text $dirtyContext -Marker 'SCOPE_ITEMS'
  $dirtyRequestBlock = Get-MarkedBlock -Text $dirtyContext -Marker 'PEDIDO_ATUAL'

  $expectedStatusSummary = "Integra${cleanCao}o pronta para produ${cleanCao}o com checklist de go-live, sincronizacao de contactos, validacao de dados mestre, confirmacao do cliente e passagem assistida para operacao sem depender de follow-up informal por email."
  Assert-Contains -Text $dirtyStatusBlock -Expected $expectedStatusSummary -Message 'O status materializado nao reparou mojibake ou foi truncado no PG_CONTEXT.'
  Assert-NotContains -Text $dirtyStatusBlock -Unexpected 'Best regards' -Message 'A assinatura entrou no bloco STATUS_SYNC.'
  Assert-NotContains -Text $dirtyStatusBlock -Unexpected 'wrote:' -Message 'Quoted reply entrou no bloco STATUS_SYNC.'
  Assert-NotContains -Text $dirtyRequestBlock -Unexpected 'wrote:' -Message 'Quoted reply entrou no bloco PEDIDO_ATUAL.'
  Assert-NotContains -Text $dirtyScopeBlock -Unexpected '[PONTO POR VALIDAR]' -Message 'Placeholder residual entrou no bloco SCOPE_ITEMS.'
  Assert-True -Condition ([regex]::Matches($dirtyStatusBlock, [regex]::Escape('- Marco validado')).Count -eq 1) -Message 'Milestones duplicados nao foram reduzidos.'
  Assert-True -Condition ($dirtyStatusBlock -like '*...*') -Message 'Truncagem defensiva nao foi aplicada no bloco STATUS_SYNC.'

  $dirtySmoke = Invoke-PowerShellScript -ScriptPath (Join-Path $dirtyRepo '.pg_framework\scripts\pg_smoke_test_repo.ps1') -Arguments @('-RepoPath', $dirtyRepo)
  Assert-True -Condition ($dirtySmoke.ExitCode -eq 0) -Message "Smoke test falhou no fixture dirty: $($dirtySmoke.Output)"
  Assert-Contains -Text $dirtySmoke.Output -Expected 'mojibake' -Message 'Smoke test nao sinalizou mojibake no fixture dirty.'
  Assert-Contains -Text $dirtySmoke.Output -Expected 'quoted replies' -Message 'Smoke test nao sinalizou quoted replies no fixture dirty.'
  Assert-Contains -Text $dirtySmoke.Output -Expected 'assinatura' -Message 'Smoke test nao sinalizou assinatura no fixture dirty.'

  $cleanRefresh = Invoke-PowerShellScript -ScriptPath (Join-Path $cleanRepo '.pg_framework\scripts\pg_refresh_pg_context.ps1') -Arguments @('-RepoPath', $cleanRepo)
  Assert-True -Condition ($cleanRefresh.ExitCode -eq 0) -Message "Refresh falhou no fixture clean: $($cleanRefresh.Output)"

  $cleanSmoke = Invoke-PowerShellScript -ScriptPath (Join-Path $cleanRepo '.pg_framework\scripts\pg_smoke_test_repo.ps1') -Arguments @('-RepoPath', $cleanRepo)
  Assert-True -Condition ($cleanSmoke.ExitCode -eq 0) -Message "Smoke test falhou no fixture clean: $($cleanSmoke.Output)"
  Assert-False -Condition ($cleanSmoke.Output -like '*quoted replies*') -Message 'Smoke test limpo ainda sinalizou quoted replies.'
  Assert-False -Condition ($cleanSmoke.Output -like '*assinatura*') -Message 'Smoke test limpo ainda sinalizou assinatura.'
  Assert-False -Condition ($cleanSmoke.Output -like '*mojibake*') -Message 'Smoke test limpo ainda sinalizou mojibake.'
  Assert-False -Condition ($cleanSmoke.Output -like '*reaproveitamento defensivo insuficiente*') -Message 'Smoke test limpo ainda sinalizou truncagem insuficiente.'

  Write-Host 'OK: testes de higiene de contexto concluidos com sucesso'
}
finally {
  if (Test-Path $tempRoot) {
    Remove-Item -LiteralPath $tempRoot -Recurse -Force
  }
}
