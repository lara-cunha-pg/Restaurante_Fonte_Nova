param(
  [Parameter(Mandatory = $true)]
  [string]$RepoPath,

  [switch]$RequireOdooSource,

  [switch]$CheckPgAiDevAssistant
)

$ErrorActionPreference = "Stop"

$script:ErrorCount = 0
$script:WarningCount = 0

. (Join-Path $PSScriptRoot "pg_file_io_common.ps1")

function Write-CheckResult {
  param(
    [ValidateSet('OK', 'WARN', 'ERROR')]
    [string]$Level,
    [string]$Message
  )

  Write-Host "$Level`: $Message"
}

function Add-Error {
  param([string]$Message)

  $script:ErrorCount += 1
  Write-CheckResult -Level 'ERROR' -Message $Message
}

function Add-Warning {
  param([string]$Message)

  $script:WarningCount += 1
  Write-CheckResult -Level 'WARN' -Message $Message
}

function Test-RequiredPath {
  param(
    [string]$Path,
    [string]$Label
  )

  if (Test-Path $Path) {
    Write-CheckResult -Level 'OK' -Message $Label
    return $true
  }

  Add-Error -Message "$Label em falta: $Path"
  return $false
}

function Test-OptionalPath {
  param(
    [string]$Path,
    [string]$Label
  )

  if (Test-Path $Path) {
    Write-CheckResult -Level 'OK' -Message $Label
    return $true
  }

  Add-Warning -Message "$Label em falta: $Path"
  return $false
}

function Get-JsonDataOrNull {
  param([string]$Path)

  try {
    return (Read-Utf8JsonFile -Path $Path)
  }
  catch {
    return $null
  }
}

function Test-JsonDocument {
  param(
    [string]$Path,
    [string]$Label
  )

  $data = Get-JsonDataOrNull -Path $Path
  if ($data) {
    Write-CheckResult -Level 'OK' -Message "$Label parseado com sucesso"
    return $data
  }

  Add-Error -Message "$Label invalido ou nao parseavel: $Path"
  return $null
}

function Test-TextEncodingNoise {
  param(
    [string]$Text,
    [string]$Label
  )

  if ([string]::IsNullOrWhiteSpace($Text)) {
    return
  }

  if ((Get-PgTextMojibakeScore -Text $Text) -gt 0 -or (Test-PgSuspiciousMojibake -Text $Text)) {
    Add-Warning -Message "$Label contem padroes compativeis com mojibake ou ruido de encoding"
  }
}

function Test-TextPlaceholderNoise {
  param(
    [string]$Text,
    [string]$Label
  )

  if ([string]::IsNullOrWhiteSpace($Text)) {
    return
  }

  if ((Test-PgPlaceholderText -Text $Text) -or $Text.Contains('[PONTO POR VALIDAR]') -or $Text.Contains('[PREENCHER]')) {
    Add-Warning -Message "$Label contem placeholders que deviam ter sido substituidos"
  }
}

function Test-TextQuotedReplyNoise {
  param(
    [string]$Text,
    [string]$Label
  )

  if ([string]::IsNullOrWhiteSpace($Text)) {
    return
  }

  if (Test-PgQuotedReplyText -Text $Text) {
    Add-Warning -Message "$Label contem quoted replies ou headers de email que nao deviam ser materializados"
  }
}

function Test-TextSignatureNoise {
  param(
    [string]$Text,
    [string]$Label
  )

  if ([string]::IsNullOrWhiteSpace($Text)) {
    return
  }

  if (Test-PgSignatureText -Text $Text) {
    Add-Warning -Message "$Label contem assinatura ou boilerplate de email"
  }
}

function Test-TextLengthHealth {
  param(
    [string]$Text,
    [string]$Label,
    [int]$MaxChars = 260
  )

  if ([string]::IsNullOrWhiteSpace($Text)) {
    return
  }

  if ($Text.Length -gt $MaxChars) {
    Add-Warning -Message "$Label excede $MaxChars caracteres e pode indicar reaproveitamento defensivo insuficiente"
  }
}

function Get-NormalizedSemanticText {
  param([string]$Text)

  if ([string]::IsNullOrWhiteSpace($Text)) {
    return ''
  }

  $normalized = $Text.ToLowerInvariant().Trim()
  $normalized = [regex]::Replace($normalized, '\s+', ' ')
  return $normalized.Trim(" .,:;!?()[]{}'`"")
}

function Test-ListSemanticHealth {
  param(
    [string]$Label,
    [string[]]$Items,
    [switch]$WarnIfEmpty,
    [string]$EmptyWarningMessage
  )

  $cleanItems = @($Items | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
  if ($cleanItems.Count -eq 0) {
    if ($WarnIfEmpty) {
      if ([string]::IsNullOrWhiteSpace($EmptyWarningMessage)) {
        Add-Warning -Message "$Label nao contem itens factuais publicados"
      }
      else {
        Add-Warning -Message $EmptyWarningMessage
      }
    }
    return
  }

  foreach ($item in $cleanItems) {
    Test-TextEncodingNoise -Text $item -Label "$Label item"
    Test-TextPlaceholderNoise -Text $item -Label "$Label item"
    Test-TextQuotedReplyNoise -Text $item -Label "$Label item"
    Test-TextSignatureNoise -Text $item -Label "$Label item"
    Test-TextLengthHealth -Text $item -Label "$Label item"
  }

  $seen = @{}
  foreach ($item in $cleanItems) {
    $normalized = Get-NormalizedSemanticText -Text $item
    if ([string]::IsNullOrWhiteSpace($normalized)) {
      continue
    }

    if ($seen.ContainsKey($normalized)) {
      Add-Warning -Message "$Label contem itens duplicados ou semanticamente identicos"
      break
    }

    $seen[$normalized] = $true
  }
}

function Test-CrossListOverlap {
  param(
    [string]$LeftLabel,
    [string[]]$LeftItems,
    [string]$RightLabel,
    [string[]]$RightItems
  )

  $leftSet = @{}
  foreach ($item in @($LeftItems | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })) {
    $normalized = Get-NormalizedSemanticText -Text $item
    if (-not [string]::IsNullOrWhiteSpace($normalized)) {
      $leftSet[$normalized] = $true
    }
  }

  if ($leftSet.Count -eq 0) {
    return
  }

  foreach ($item in @($RightItems | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })) {
    $normalized = Get-NormalizedSemanticText -Text $item
    if ([string]::IsNullOrWhiteSpace($normalized)) {
      continue
    }

    if ($leftSet.ContainsKey($normalized)) {
      Add-Warning -Message "$LeftLabel e $RightLabel contem pelo menos um item semanticamente igual; rever classificacao do conteudo"
      return
    }
  }
}

function Test-ScopeSnapshotReady {
  param([pscustomobject]$Data)

  if (-not $Data) {
    return $false
  }

  return (
    -not [string]::IsNullOrWhiteSpace([string]$Data.project_name) -and
    $Data.source_metadata -and
    -not [string]::IsNullOrWhiteSpace([string]$Data.source_metadata.sync_published_at) -and
    -not [string]::IsNullOrWhiteSpace([string]$Data.source_metadata.payload_hash)
  )
}

function Test-StatusSnapshotReady {
  param([pscustomobject]$Data)

  if (-not $Data) {
    return $false
  }

  return (
    -not [string]::IsNullOrWhiteSpace([string]$Data.project_name) -and
    -not [string]::IsNullOrWhiteSpace([string]$Data.sync_published_at)
  )
}

function Test-DecisionsSnapshotReady {
  param([pscustomobject]$Data)

  if (-not $Data) {
    return $false
  }

  return (
    -not [string]::IsNullOrWhiteSpace([string]$Data.project_name) -and
    $Data.source_metadata -and
    -not [string]::IsNullOrWhiteSpace([string]$Data.source_metadata.sync_published_at) -and
    -not [string]::IsNullOrWhiteSpace([string]$Data.source_metadata.payload_hash)
  )
}

function Test-RisksSnapshotReady {
  param([pscustomobject]$Data)

  if (-not $Data) {
    return $false
  }

  return (
    -not [string]::IsNullOrWhiteSpace([string]$Data.project_name) -and
    $Data.source_metadata -and
    -not [string]::IsNullOrWhiteSpace([string]$Data.source_metadata.sync_published_at) -and
    -not [string]::IsNullOrWhiteSpace([string]$Data.source_metadata.payload_hash)
  )
}

function Test-DeliveriesSnapshotReady {
  param([pscustomobject]$Data)

  if (-not $Data) {
    return $false
  }

  return (
    -not [string]::IsNullOrWhiteSpace([string]$Data.project_name) -and
    $Data.source_metadata -and
    -not [string]::IsNullOrWhiteSpace([string]$Data.source_metadata.sync_published_at) -and
    -not [string]::IsNullOrWhiteSpace([string]$Data.source_metadata.payload_hash)
  )
}

function Test-RequirementsSnapshotReady {
  param([pscustomobject]$Data)

  if (-not $Data) {
    return $false
  }

  return (
    -not [string]::IsNullOrWhiteSpace([string]$Data.project_name) -and
    $Data.source_metadata -and
    -not [string]::IsNullOrWhiteSpace([string]$Data.source_metadata.sync_published_at) -and
    -not [string]::IsNullOrWhiteSpace([string]$Data.source_metadata.payload_hash)
  )
}

function Test-ProjectPlanSnapshotReady {
  param([pscustomobject]$Data)

  if (-not $Data) {
    return $false
  }

  return (
    -not [string]::IsNullOrWhiteSpace([string]$Data.project_name) -and
    $Data.source_metadata -and
    -not [string]::IsNullOrWhiteSpace([string]$Data.source_metadata.sync_published_at) -and
    -not [string]::IsNullOrWhiteSpace([string]$Data.source_metadata.payload_hash)
  )
}

function Test-BudgetSnapshotReady {
  param([pscustomobject]$Data)

  if (-not $Data) {
    return $false
  }

  return (
    -not [string]::IsNullOrWhiteSpace([string]$Data.project_name) -and
    $Data.source_metadata -and
    -not [string]::IsNullOrWhiteSpace([string]$Data.source_metadata.sync_published_at) -and
    -not [string]::IsNullOrWhiteSpace([string]$Data.source_metadata.payload_hash)
  )
}

function Test-ManifestVersion {
  param(
    [string]$ManifestPath
  )

  if (-not (Test-Path $ManifestPath)) {
    Add-Error -Message "Manifest do addon em falta: $ManifestPath"
    return $false
  }

  $content = Read-Utf8TextFile -Path $ManifestPath
  $versionMatch = [regex]::Match($content, "'version'\s*:\s*'([^']+)'")
  $summaryMatch = [regex]::Match($content, "'summary'\s*:\s*'([^']+)'")

  if (-not $versionMatch.Success) {
    Add-Error -Message "Nao foi possivel detetar a versao no manifest: $ManifestPath"
    return $false
  }

  $version = $versionMatch.Groups[1].Value
  Write-CheckResult -Level 'OK' -Message "Versao do addon detetada: $version"

  if ($summaryMatch.Success) {
    Write-CheckResult -Level 'OK' -Message "Summary do addon: $($summaryMatch.Groups[1].Value)"
  }

  return $true
}

function Get-MarkedBlock {
  param(
    [string]$Text,
    [string]$Marker
  )

  $pattern = "(?s)<!-- PG_AUTO:$Marker`:START -->\s*(.*?)\s*<!-- PG_AUTO:$Marker`:END -->"
  $match = [regex]::Match($Text, $pattern)
  if (-not $match.Success) {
    return $null
  }

  return $match.Groups[1].Value
}

function Test-PgContextMarkers {
  param([string]$ContextText)

  if (-not ($ContextText -match "<!-- PG_AUTO:IDENTIFICACAO:START -->")) {
    Add-Warning -Message "PG_CONTEXT.md nao tem marcadores PG_AUTO (ficheiro gerado pelo mirror - checks de marcadores ignorados)"
    return
  }

  $markers = @(
    'IDENTIFICACAO',
    'RESTRICOES',
    'PEDIDO_ATUAL',
    'PROCESSO_ATUAL',
    'PROBLEMA_DOR',
    'IMPACTO_NEGOCIO',
    'SCOPE_ITEMS',
    'STATUS_SYNC'
  )

  foreach ($marker in $markers) {
    $start = "<!-- PG_AUTO:$marker`:START -->"
    $end = "<!-- PG_AUTO:$marker`:END -->"

    if ($ContextText.Contains($start) -and $ContextText.Contains($end)) {
      Write-CheckResult -Level 'OK' -Message "Marcadores PG_AUTO presentes para $marker"
    }
    else {
      Add-Error -Message "Marcadores PG_AUTO em falta para $marker no PG_CONTEXT.md"
    }
  }
}

function Test-WorkflowSemantics {
  param([string]$WorkflowText)

  if ([string]::IsNullOrWhiteSpace($WorkflowText)) {
    Add-Error -Message 'Workflow de refresh de contexto vazio ou nao legivel'
    return
  }

  $checks = @(
    @{ Needle = '.pg/PG_SCOPE_SYNC.json'; Label = 'Workflow observa alteracoes de PG_SCOPE_SYNC.json' },
    @{ Needle = '.pg/PG_PROJECT_STATUS_SYNC.json'; Label = 'Workflow observa alteracoes de PG_PROJECT_STATUS_SYNC.json' },
    @{ Needle = 'pg_refresh_pg_context.ps1'; Label = 'Workflow chama pg_refresh_pg_context.ps1' },
    @{ Needle = 'PG_TEMPLATE_REPO_TOKEN'; Label = 'Workflow documenta o secret PG_TEMPLATE_REPO_TOKEN' }
  )

  foreach ($check in $checks) {
    if ($WorkflowText.Contains($check.Needle)) {
      Write-CheckResult -Level 'OK' -Message $check.Label
    }
    else {
      Add-Warning -Message "Workflow de refresh nao contem a referencia esperada: $($check.Needle)"
    }
  }
}

function Test-ContextContains {
  param(
    [string]$Haystack,
    [string]$Needle,
    [string]$SuccessLabel,
    [string]$WarningMessage
  )

  if ([string]::IsNullOrWhiteSpace($Needle)) {
    return
  }

  if ($Haystack -like "*$Needle*") {
    Write-CheckResult -Level 'OK' -Message $SuccessLabel
  }
  else {
    Add-Warning -Message $WarningMessage
  }
}

function Test-ScopeContextSemantics {
  param(
    [string]$ContextText,
    [pscustomobject]$ScopeData
  )

  $identificationBlock = Get-MarkedBlock -Text $ContextText -Marker 'IDENTIFICACAO'
  $requestBlock = Get-MarkedBlock -Text $ContextText -Marker 'PEDIDO_ATUAL'
  $processBlock = Get-MarkedBlock -Text $ContextText -Marker 'PROCESSO_ATUAL'
  $problemBlock = Get-MarkedBlock -Text $ContextText -Marker 'PROBLEMA_DOR'
  $impactBlock = Get-MarkedBlock -Text $ContextText -Marker 'IMPACTO_NEGOCIO'
  $scopeItemsBlock = Get-MarkedBlock -Text $ContextText -Marker 'SCOPE_ITEMS'

  if (-not $identificationBlock) {
    Add-Error -Message 'Bloco IDENTIFICACAO nao encontrado no PG_CONTEXT.md'
    return
  }
  if (-not $scopeItemsBlock) {
    Add-Error -Message 'Bloco SCOPE_ITEMS nao encontrado no PG_CONTEXT.md'
    return
  }

  foreach ($block in @(
    @{ Label = 'Bloco IDENTIFICACAO'; Text = $identificationBlock },
    @{ Label = 'Bloco PEDIDO_ATUAL'; Text = $requestBlock },
    @{ Label = 'Bloco PROCESSO_ATUAL'; Text = $processBlock },
    @{ Label = 'Bloco PROBLEMA_DOR'; Text = $problemBlock },
    @{ Label = 'Bloco IMPACTO_NEGOCIO'; Text = $impactBlock },
    @{ Label = 'Bloco SCOPE_ITEMS'; Text = $scopeItemsBlock }
  )) {
    Test-TextQuotedReplyNoise -Text $block.Text -Label $block.Label
    Test-TextSignatureNoise -Text $block.Text -Label $block.Label
  }

  $sourceReference = "{0} / {1} / {2}" -f `
    [string]$ScopeData.source_metadata.source_system, `
    [string]$ScopeData.source_metadata.source_model, `
    [string]$ScopeData.source_metadata.source_record_id

  Test-ContextContains -Haystack $identificationBlock `
    -Needle ("Nome do projeto: " + [string]$ScopeData.project_name) `
    -SuccessLabel 'PG_CONTEXT.md reflete project_name do scope sync' `
    -WarningMessage 'PG_CONTEXT.md nao reflete o project_name atual do snapshot de scope'

  Test-ContextContains -Haystack $identificationBlock `
    -Needle ("Fase atual do projeto: " + [string]$ScopeData.project_phase) `
    -SuccessLabel 'PG_CONTEXT.md reflete project_phase do scope sync' `
    -WarningMessage 'PG_CONTEXT.md nao reflete a fase atual do snapshot de scope'

  Test-ContextContains -Haystack $ContextText `
    -Needle ("Ultima sincronizacao de ambito: " + [string]$ScopeData.source_metadata.sync_published_at) `
    -SuccessLabel 'PG_CONTEXT.md reflete a data do ultimo scope sync' `
    -WarningMessage 'PG_CONTEXT.md nao reflete a data do ultimo scope sync'

  Test-ContextContains -Haystack $ContextText `
    -Needle ("Fonte do ambito sincronizado: " + $sourceReference) `
    -SuccessLabel 'PG_CONTEXT.md reflete a origem do ultimo scope sync' `
    -WarningMessage 'PG_CONTEXT.md nao reflete a origem atual do snapshot de scope'

  Test-ContextContains -Haystack $scopeItemsBlock `
    -Needle ("- Itens ativos: " + [string]$ScopeData.scope_summary.active_scope_item_count) `
    -SuccessLabel 'PG_CONTEXT.md reflete a contagem de itens ativos do scope sync' `
    -WarningMessage 'PG_CONTEXT.md nao reflete a contagem atual de itens ativos do scope sync'

  $scopeItems = @($ScopeData.scope_items)
  if ($scopeItems.Count -gt 0) {
    $firstItem = $scopeItems[0]
    Test-ContextContains -Haystack $scopeItemsBlock `
      -Needle ([string]$firstItem.task_name) `
      -SuccessLabel 'PG_CONTEXT.md materializa pelo menos uma task do scope sync' `
      -WarningMessage 'PG_CONTEXT.md nao materializa a task esperada do snapshot de scope'

    Test-ContextContains -Haystack $scopeItemsBlock `
      -Needle ([string]$firstItem.scope_summary) `
      -SuccessLabel 'PG_CONTEXT.md materializa o resumo de task do scope sync' `
      -WarningMessage 'PG_CONTEXT.md nao materializa o resumo atual da task em scope'
  }

  if ($scopeItemsBlock.Contains('[PREENCHER]')) {
    Add-Warning -Message 'Bloco SCOPE_ITEMS ainda contem placeholders [PREENCHER]'
  }
}

function Test-ScopeSnapshotContentSemantics {
  param([pscustomobject]$ScopeData)

  $overview = $ScopeData.scope_overview
  if ($overview) {
    Test-TextEncodingNoise -Text ([string]$overview.business_goal) -Label 'scope_overview.business_goal'
    Test-TextEncodingNoise -Text ([string]$overview.current_request) -Label 'scope_overview.current_request'
    Test-TextPlaceholderNoise -Text ([string]$overview.business_goal) -Label 'scope_overview.business_goal'
    Test-TextPlaceholderNoise -Text ([string]$overview.current_request) -Label 'scope_overview.current_request'
    Test-TextQuotedReplyNoise -Text ([string]$overview.business_goal) -Label 'scope_overview.business_goal'
    Test-TextQuotedReplyNoise -Text ([string]$overview.current_request) -Label 'scope_overview.current_request'
    Test-TextSignatureNoise -Text ([string]$overview.business_goal) -Label 'scope_overview.business_goal'
    Test-TextSignatureNoise -Text ([string]$overview.current_request) -Label 'scope_overview.current_request'
    Test-TextLengthHealth -Text ([string]$overview.business_goal) -Label 'scope_overview.business_goal'
    Test-TextLengthHealth -Text ([string]$overview.current_request) -Label 'scope_overview.current_request'
    Test-ListSemanticHealth `
      -Label 'scope_overview.acceptance_criteria' `
      -Items @($overview.acceptance_criteria) `
      -WarnIfEmpty `
      -EmptyWarningMessage 'scope_overview.acceptance_criteria vazio; o ambito publicado ainda nao consolidou criterios factuais'
  }

  foreach ($item in @($ScopeData.scope_items)) {
    Test-TextEncodingNoise -Text ([string]$item.task_name) -Label 'scope_items.task_name'
    Test-TextEncodingNoise -Text ([string]$item.scope_summary) -Label 'scope_items.scope_summary'
    Test-TextPlaceholderNoise -Text ([string]$item.scope_summary) -Label 'scope_items.scope_summary'
    Test-TextQuotedReplyNoise -Text ([string]$item.scope_summary) -Label 'scope_items.scope_summary'
    Test-TextSignatureNoise -Text ([string]$item.scope_summary) -Label 'scope_items.scope_summary'
    Test-TextLengthHealth -Text ([string]$item.scope_summary) -Label 'scope_items.scope_summary'
    Test-ListSemanticHealth `
      -Label "scope_items.acceptance_criteria task $([string]$item.task_id)" `
      -Items @($item.acceptance_criteria) `
      -WarnIfEmpty `
      -EmptyWarningMessage "scope_items.acceptance_criteria task $([string]$item.task_id) vazio; falta consolidar criterios factuais"
  }
}

function Test-StatusContextSemantics {
  param(
    [string]$ContextText,
    [pscustomobject]$StatusData
  )

  $statusBlock = Get-MarkedBlock -Text $ContextText -Marker 'STATUS_SYNC'
  if (-not $statusBlock) {
    Add-Error -Message 'Bloco STATUS_SYNC nao encontrado no PG_CONTEXT.md'
    return
  }

  Test-TextQuotedReplyNoise -Text $statusBlock -Label 'Bloco STATUS_SYNC'
  Test-TextSignatureNoise -Text $statusBlock -Label 'Bloco STATUS_SYNC'

  Test-ContextContains -Haystack $statusBlock `
    -Needle ("Schema do snapshot: " + [string]$StatusData.schema_version) `
    -SuccessLabel 'PG_CONTEXT.md reflete o schema do status sync' `
    -WarningMessage 'PG_CONTEXT.md nao reflete o schema atual do snapshot de status'

  Test-ContextContains -Haystack $statusBlock `
    -Needle ("Estado geral reportado: " + [string]$StatusData.status_summary) `
    -SuccessLabel 'PG_CONTEXT.md reflete o status_summary atual' `
    -WarningMessage 'PG_CONTEXT.md nao reflete o status_summary atual do snapshot operacional'

  Test-ContextContains -Haystack $statusBlock `
    -Needle ("Trigger de sync: " + [string]$StatusData.sync_trigger) `
    -SuccessLabel 'PG_CONTEXT.md reflete o trigger do status sync' `
    -WarningMessage 'PG_CONTEXT.md nao reflete o trigger atual do status sync'

  Test-ContextContains -Haystack $statusBlock `
    -Needle ("Branch de sync: " + [string]$StatusData.repo_branch) `
    -SuccessLabel 'PG_CONTEXT.md reflete a branch do status sync' `
    -WarningMessage 'PG_CONTEXT.md nao reflete a branch atual do status sync'

  if (-not [string]::IsNullOrWhiteSpace([string]$StatusData.owner)) {
    Test-ContextContains -Haystack $statusBlock `
      -Needle ("Owner atual: " + [string]$StatusData.owner) `
      -SuccessLabel 'PG_CONTEXT.md reflete o owner atual do status sync' `
      -WarningMessage 'PG_CONTEXT.md nao reflete o owner atual do snapshot operacional'
  }

  if ($statusBlock.Contains('[PREENCHER]')) {
    Add-Warning -Message 'Bloco STATUS_SYNC ainda contem placeholders [PREENCHER]'
  }
}

function Test-StatusSnapshotContentSemantics {
  param([pscustomobject]$StatusData)

  Test-TextEncodingNoise -Text ([string]$StatusData.status_summary) -Label 'status_summary'
  Test-TextPlaceholderNoise -Text ([string]$StatusData.status_summary) -Label 'status_summary'
  Test-TextQuotedReplyNoise -Text ([string]$StatusData.status_summary) -Label 'status_summary'
  Test-TextSignatureNoise -Text ([string]$StatusData.status_summary) -Label 'status_summary'
  Test-TextLengthHealth -Text ([string]$StatusData.status_summary) -Label 'status_summary'
  Test-TextEncodingNoise -Text ([string]$StatusData.owner) -Label 'owner'
  Test-TextPlaceholderNoise -Text ([string]$StatusData.owner) -Label 'owner'

  $milestones = @($StatusData.milestones)
  $blockers = @($StatusData.blockers)
  $risks = @($StatusData.risks)
  $nextSteps = @($StatusData.next_steps)
  $pendingDecisions = @($StatusData.pending_decisions)

  Test-ListSemanticHealth -Label 'milestones' -Items $milestones
  Test-ListSemanticHealth -Label 'blockers' -Items $blockers
  Test-ListSemanticHealth -Label 'risks' -Items $risks
  Test-ListSemanticHealth -Label 'next_steps' -Items $nextSteps
  Test-ListSemanticHealth -Label 'pending_decisions' -Items $pendingDecisions

  Test-CrossListOverlap -LeftLabel 'blockers' -LeftItems $blockers -RightLabel 'next_steps' -RightItems $nextSteps
  Test-CrossListOverlap -LeftLabel 'risks' -LeftItems $risks -RightLabel 'next_steps' -RightItems $nextSteps
  Test-CrossListOverlap -LeftLabel 'risks' -LeftItems $risks -RightLabel 'blockers' -RightItems $blockers
  Test-CrossListOverlap -LeftLabel 'next_steps' -LeftItems $nextSteps -RightLabel 'pending_decisions' -RightItems $pendingDecisions
}

$repo = [System.IO.Path]::GetFullPath($RepoPath)
if (-not (Test-Path $repo)) {
  throw "Repositorio nao encontrado: $repo"
}

$frameworkScriptsRoot = Join-Path $repo '.pg_framework\scripts'
$contextPath = Join-Path $repo 'PG_CONTEXT.md'
$scopePath = Join-Path $repo '.pg\PG_SCOPE_SYNC.json'
$statusPath = Join-Path $repo '.pg\PG_PROJECT_STATUS_SYNC.json'
$decisionsPath = Join-Path $repo '.pg\PG_DECISIONS_SYNC.json'
$risksPath = Join-Path $repo '.pg\PG_RISKS_SYNC.json'
$deliveriesPath = Join-Path $repo '.pg\PG_DELIVERIES_SYNC.json'
$requirementsPath = Join-Path $repo '.pg\PG_REQUIREMENTS_SYNC.json'
$projectPlanPath = Join-Path $repo '.pg\PG_PROJECT_PLAN_SYNC.json'
$budgetPath = Join-Path $repo '.pg\PG_BUDGET_SYNC.json'
$workflowPath = Join-Path $repo '.github\workflows\pg_refresh_pg_context.yml'

$requiredPaths = @(
  @{ Path = Join-Path $repo '.pg_framework'; Label = 'Framework partilhado acessivel via .pg_framework' },
  @{ Path = Join-Path $repo '.editorconfig'; Label = '.editorconfig presente na raiz' },
  @{ Path = Join-Path $repo '.gitignore'; Label = '.gitignore presente na raiz' },
  @{ Path = Join-Path $repo '.gitattributes'; Label = '.gitattributes presente na raiz' },
  @{ Path = $workflowPath; Label = 'Workflow GitHub de refresh de contexto presente' },
  @{ Path = Join-Path $repo 'AGENTS.md'; Label = 'AGENTS.md presente' },
  @{ Path = Join-Path $repo 'CLAUDE.md'; Label = 'CLAUDE.md presente' },
  @{ Path = $contextPath; Label = 'PG_CONTEXT.md presente' },
  @{ Path = Join-Path $repo 'PG_SCOPE_INTAKE.yaml'; Label = 'PG_SCOPE_INTAKE.yaml presente' },
  @{ Path = Join-Path $repo 'config.toml'; Label = 'config.toml presente' },
  @{ Path = $scopePath; Label = '.pg/PG_SCOPE_SYNC.json presente' },
  @{ Path = $statusPath; Label = '.pg/PG_PROJECT_STATUS_SYNC.json presente' },
  @{ Path = $decisionsPath; Label = '.pg/PG_DECISIONS_SYNC.json presente' },
  @{ Path = $risksPath; Label = '.pg/PG_RISKS_SYNC.json presente' },
  @{ Path = $deliveriesPath; Label = '.pg/PG_DELIVERIES_SYNC.json presente' },
  @{ Path = $requirementsPath; Label = '.pg/PG_REQUIREMENTS_SYNC.json presente' },
  @{ Path = $projectPlanPath; Label = '.pg/PG_PROJECT_PLAN_SYNC.json presente' },
  @{ Path = $budgetPath; Label = '.pg/PG_BUDGET_SYNC.json presente' },
  @{ Path = Join-Path $frameworkScriptsRoot 'pg_refresh_pg_context.ps1'; Label = 'Script pg_refresh_pg_context.ps1 acessivel' },
  @{ Path = Join-Path $frameworkScriptsRoot 'pg_validate_scope_sync.ps1'; Label = 'Script pg_validate_scope_sync.ps1 acessivel' },
  @{ Path = Join-Path $frameworkScriptsRoot 'pg_apply_scope_sync.ps1'; Label = 'Script pg_apply_scope_sync.ps1 acessivel' },
  @{ Path = Join-Path $frameworkScriptsRoot 'pg_validate_project_status_sync.ps1'; Label = 'Script pg_validate_project_status_sync.ps1 acessivel' },
  @{ Path = Join-Path $frameworkScriptsRoot 'pg_apply_project_status_sync.ps1'; Label = 'Script pg_apply_project_status_sync.ps1 acessivel' },
  @{ Path = Join-Path $frameworkScriptsRoot 'pg_validate_decisions_sync.ps1'; Label = 'Script pg_validate_decisions_sync.ps1 acessivel' },
  @{ Path = Join-Path $frameworkScriptsRoot 'pg_validate_risks_sync.ps1'; Label = 'Script pg_validate_risks_sync.ps1 acessivel' },
  @{ Path = Join-Path $frameworkScriptsRoot 'pg_validate_deliveries_sync.ps1'; Label = 'Script pg_validate_deliveries_sync.ps1 acessivel' },
  @{ Path = Join-Path $frameworkScriptsRoot 'pg_validate_requirements_sync.ps1'; Label = 'Script pg_validate_requirements_sync.ps1 acessivel' },
  @{ Path = Join-Path $frameworkScriptsRoot 'pg_validate_project_plan_sync.ps1'; Label = 'Script pg_validate_project_plan_sync.ps1 acessivel' },
  @{ Path = Join-Path $frameworkScriptsRoot 'pg_validate_budget_sync.ps1'; Label = 'Script pg_validate_budget_sync.ps1 acessivel' }
)

foreach ($item in $requiredPaths) {
  [void](Test-RequiredPath -Path $item.Path -Label $item.Label)
}

$communitySource = Join-Path $repo 'vendor\odoo_src\community'
if ($RequireOdooSource) {
  [void](Test-RequiredPath -Path $communitySource -Label 'Source Community do Odoo presente')
}
else {
  [void](Test-OptionalPath -Path $communitySource -Label 'Source Community do Odoo presente')
}

if ($CheckPgAiDevAssistant) {
  $addonRoot = Join-Path $repo 'pg_brodoo'
  if (Test-RequiredPath -Path $addonRoot -Label 'Addon pg_brodoo presente') {
    [void](Test-ManifestVersion -ManifestPath (Join-Path $addonRoot '__manifest__.py'))

    $addonRequired = @(
      'models\project_project.py',
      'models\pg_project_risk.py',
      'models\project_milestone.py',
      'models\pg_project_budget_line.py',
      'models\pg_project_budget_sync_run.py',
      'models\pg_project_deliveries_sync_run.py',
      'models\pg_project_decisions_sync_run.py',
      'models\pg_project_plan_sync_run.py',
      'models\pg_project_requirements_sync_run.py',
      'models\pg_project_risks_sync_run.py',
      'models\pg_project_scope_sync_run.py',
      'models\pg_project_status_sync_run.py',
      'views\project_project_views.xml',
      'views\project_task_scope_views.xml',
      'views\pg_project_deliveries_sync_run_views.xml',
      'views\pg_project_budget_sync_run_views.xml',
      'views\pg_project_decisions_sync_run_views.xml',
      'views\pg_project_plan_sync_run_views.xml',
      'views\pg_project_requirements_sync_run_views.xml',
      'views\pg_project_risks_sync_run_views.xml',
      'views\pg_project_scope_sync_run_views.xml',
      'views\pg_project_status_sync_run_views.xml'
    )

    foreach ($relativePath in $addonRequired) {
      [void](Test-RequiredPath -Path (Join-Path $addonRoot $relativePath) -Label "Addon: $relativePath")
    }
  }
}

$contextText = $null
if (Test-Path $contextPath) {
  $contextText = Read-Utf8TextFile -Path $contextPath
  Test-TextEncodingNoise -Text $contextText -Label 'PG_CONTEXT.md'
  Test-PgContextMarkers -ContextText $contextText
}

if (Test-Path $workflowPath) {
  Test-WorkflowSemantics -WorkflowText (Read-Utf8TextFile -Path $workflowPath)
}

$scopeData = $null
if (Test-Path $scopePath) {
  $scopeText = Read-Utf8TextFile -Path $scopePath
  Test-TextEncodingNoise -Text $scopeText -Label 'PG_SCOPE_SYNC.json'
  Test-TextQuotedReplyNoise -Text $scopeText -Label 'PG_SCOPE_SYNC.json'
  Test-TextSignatureNoise -Text $scopeText -Label 'PG_SCOPE_SYNC.json'
  $scopeData = Test-JsonDocument -Path $scopePath -Label 'PG_SCOPE_SYNC.json'
}

$statusData = $null
if (Test-Path $statusPath) {
  $statusText = Read-Utf8TextFile -Path $statusPath
  Test-TextEncodingNoise -Text $statusText -Label 'PG_PROJECT_STATUS_SYNC.json'
  Test-TextQuotedReplyNoise -Text $statusText -Label 'PG_PROJECT_STATUS_SYNC.json'
  Test-TextSignatureNoise -Text $statusText -Label 'PG_PROJECT_STATUS_SYNC.json'
  $statusData = Test-JsonDocument -Path $statusPath -Label 'PG_PROJECT_STATUS_SYNC.json'
}

$decisionsData = $null
if (Test-Path $decisionsPath) {
  $decisionsText = Read-Utf8TextFile -Path $decisionsPath
  Test-TextEncodingNoise -Text $decisionsText -Label 'PG_DECISIONS_SYNC.json'
  Test-TextQuotedReplyNoise -Text $decisionsText -Label 'PG_DECISIONS_SYNC.json'
  Test-TextSignatureNoise -Text $decisionsText -Label 'PG_DECISIONS_SYNC.json'
  $decisionsData = Test-JsonDocument -Path $decisionsPath -Label 'PG_DECISIONS_SYNC.json'
}

$risksData = $null
if (Test-Path $risksPath) {
  $risksText = Read-Utf8TextFile -Path $risksPath
  Test-TextEncodingNoise -Text $risksText -Label 'PG_RISKS_SYNC.json'
  Test-TextQuotedReplyNoise -Text $risksText -Label 'PG_RISKS_SYNC.json'
  Test-TextSignatureNoise -Text $risksText -Label 'PG_RISKS_SYNC.json'
  $risksData = Test-JsonDocument -Path $risksPath -Label 'PG_RISKS_SYNC.json'
}

$deliveriesData = $null
if (Test-Path $deliveriesPath) {
  $deliveriesText = Read-Utf8TextFile -Path $deliveriesPath
  Test-TextEncodingNoise -Text $deliveriesText -Label 'PG_DELIVERIES_SYNC.json'
  Test-TextQuotedReplyNoise -Text $deliveriesText -Label 'PG_DELIVERIES_SYNC.json'
  Test-TextSignatureNoise -Text $deliveriesText -Label 'PG_DELIVERIES_SYNC.json'
  $deliveriesData = Test-JsonDocument -Path $deliveriesPath -Label 'PG_DELIVERIES_SYNC.json'
}

$requirementsData = $null
if (Test-Path $requirementsPath) {
  $requirementsText = Read-Utf8TextFile -Path $requirementsPath
  Test-TextEncodingNoise -Text $requirementsText -Label 'PG_REQUIREMENTS_SYNC.json'
  Test-TextQuotedReplyNoise -Text $requirementsText -Label 'PG_REQUIREMENTS_SYNC.json'
  Test-TextSignatureNoise -Text $requirementsText -Label 'PG_REQUIREMENTS_SYNC.json'
  $requirementsData = Test-JsonDocument -Path $requirementsPath -Label 'PG_REQUIREMENTS_SYNC.json'
}

$projectPlanData = $null
if (Test-Path $projectPlanPath) {
  $projectPlanText = Read-Utf8TextFile -Path $projectPlanPath
  Test-TextEncodingNoise -Text $projectPlanText -Label 'PG_PROJECT_PLAN_SYNC.json'
  Test-TextQuotedReplyNoise -Text $projectPlanText -Label 'PG_PROJECT_PLAN_SYNC.json'
  Test-TextSignatureNoise -Text $projectPlanText -Label 'PG_PROJECT_PLAN_SYNC.json'
  $projectPlanData = Test-JsonDocument -Path $projectPlanPath -Label 'PG_PROJECT_PLAN_SYNC.json'
}

$budgetData = $null
if (Test-Path $budgetPath) {
  $budgetText = Read-Utf8TextFile -Path $budgetPath
  Test-TextEncodingNoise -Text $budgetText -Label 'PG_BUDGET_SYNC.json'
  Test-TextQuotedReplyNoise -Text $budgetText -Label 'PG_BUDGET_SYNC.json'
  Test-TextSignatureNoise -Text $budgetText -Label 'PG_BUDGET_SYNC.json'
  $budgetData = Test-JsonDocument -Path $budgetPath -Label 'PG_BUDGET_SYNC.json'
}

if ($scopeData) {
  if (Test-ScopeSnapshotReady -Data $scopeData) {
    Test-ScopeSnapshotContentSemantics -ScopeData $scopeData

    try {
      & (Join-Path $frameworkScriptsRoot 'pg_validate_scope_sync.ps1') -RepoPath $repo -ScopePath $scopePath | Out-Null
      Write-CheckResult -Level 'OK' -Message 'Contrato do PG_SCOPE_SYNC.json validado'
    }
    catch {
      Add-Error -Message "PG_SCOPE_SYNC.json publicado mas invalido: $($_.Exception.Message)"
    }

    if ($contextText) {
      Test-ScopeContextSemantics -ContextText $contextText -ScopeData $scopeData
    }
  }
  else {
    Add-Warning -Message 'PG_SCOPE_SYNC.json existe mas ainda esta em estado placeholder ou sem publish real'
  }
}

if ($statusData) {
  if (Test-StatusSnapshotReady -Data $statusData) {
    Test-StatusSnapshotContentSemantics -StatusData $statusData

    try {
      & (Join-Path $frameworkScriptsRoot 'pg_validate_project_status_sync.ps1') -RepoPath $repo -StatusPath $statusPath | Out-Null
      Write-CheckResult -Level 'OK' -Message 'Contrato do PG_PROJECT_STATUS_SYNC.json validado'
    }
    catch {
      Add-Error -Message "PG_PROJECT_STATUS_SYNC.json publicado mas invalido: $($_.Exception.Message)"
    }

    if ($contextText) {
      Test-StatusContextSemantics -ContextText $contextText -StatusData $statusData
    }
  }
  else {
    Add-Warning -Message 'PG_PROJECT_STATUS_SYNC.json existe mas ainda esta em estado placeholder ou sem publish real'
  }
}

if ($decisionsData) {
  if (Test-DecisionsSnapshotReady -Data $decisionsData) {
    try {
      & (Join-Path $frameworkScriptsRoot 'pg_validate_decisions_sync.ps1') -RepoPath $repo -DecisionsPath $decisionsPath | Out-Null
      Write-CheckResult -Level 'OK' -Message 'Contrato do PG_DECISIONS_SYNC.json validado'
    }
    catch {
      Add-Error -Message "PG_DECISIONS_SYNC.json publicado mas invalido: $($_.Exception.Message)"
    }
  }
  else {
    Add-Warning -Message 'PG_DECISIONS_SYNC.json existe mas ainda esta em estado placeholder ou sem publish real'
  }
}

if ($risksData) {
  if (Test-RisksSnapshotReady -Data $risksData) {
    try {
      & (Join-Path $frameworkScriptsRoot 'pg_validate_risks_sync.ps1') -RepoPath $repo -RisksPath $risksPath | Out-Null
      Write-CheckResult -Level 'OK' -Message 'Contrato do PG_RISKS_SYNC.json validado'
    }
    catch {
      Add-Error -Message "PG_RISKS_SYNC.json publicado mas invalido: $($_.Exception.Message)"
    }
  }
  else {
    Add-Warning -Message 'PG_RISKS_SYNC.json existe mas ainda esta em estado placeholder ou sem publish real'
  }
}

if ($deliveriesData) {
  if (Test-DeliveriesSnapshotReady -Data $deliveriesData) {
    try {
      & (Join-Path $frameworkScriptsRoot 'pg_validate_deliveries_sync.ps1') -RepoPath $repo -DeliveriesPath $deliveriesPath | Out-Null
      Write-CheckResult -Level 'OK' -Message 'Contrato do PG_DELIVERIES_SYNC.json validado'
    }
    catch {
      Add-Error -Message "PG_DELIVERIES_SYNC.json publicado mas invalido: $($_.Exception.Message)"
    }
  }
  else {
    Add-Warning -Message 'PG_DELIVERIES_SYNC.json existe mas ainda esta em estado placeholder ou sem publish real'
  }
}

if ($requirementsData) {
  if (Test-RequirementsSnapshotReady -Data $requirementsData) {
    try {
      & (Join-Path $frameworkScriptsRoot 'pg_validate_requirements_sync.ps1') -RepoPath $repo -RequirementsPath $requirementsPath | Out-Null
      Write-CheckResult -Level 'OK' -Message 'Contrato do PG_REQUIREMENTS_SYNC.json validado'
    }
    catch {
      Add-Error -Message "PG_REQUIREMENTS_SYNC.json publicado mas invalido: $($_.Exception.Message)"
    }
  }
  else {
    Add-Warning -Message 'PG_REQUIREMENTS_SYNC.json existe mas ainda esta em estado placeholder ou sem publish real'
  }
}

if ($projectPlanData) {
  if (Test-ProjectPlanSnapshotReady -Data $projectPlanData) {
    try {
      & (Join-Path $frameworkScriptsRoot 'pg_validate_project_plan_sync.ps1') -RepoPath $repo -ProjectPlanPath $projectPlanPath | Out-Null
      Write-CheckResult -Level 'OK' -Message 'Contrato do PG_PROJECT_PLAN_SYNC.json validado'
    }
    catch {
      Add-Error -Message "PG_PROJECT_PLAN_SYNC.json publicado mas invalido: $($_.Exception.Message)"
    }
  }
  else {
    Add-Warning -Message 'PG_PROJECT_PLAN_SYNC.json existe mas ainda esta em estado placeholder ou sem publish real'
  }
}

if ($budgetData) {
  if (Test-BudgetSnapshotReady -Data $budgetData) {
    try {
      & (Join-Path $frameworkScriptsRoot 'pg_validate_budget_sync.ps1') -RepoPath $repo -BudgetPath $budgetPath | Out-Null
      Write-CheckResult -Level 'OK' -Message 'Contrato do PG_BUDGET_SYNC.json validado'
    }
    catch {
      Add-Error -Message "PG_BUDGET_SYNC.json publicado mas invalido: $($_.Exception.Message)"
    }
  }
  else {
    Add-Warning -Message 'PG_BUDGET_SYNC.json existe mas ainda esta em estado placeholder ou sem publish real'
  }
}

if ($script:ErrorCount -gt 0) {
  throw "Smoke test falhou com $($script:ErrorCount) erro(s) e $($script:WarningCount) warning(s)."
}

if ($script:WarningCount -gt 0) {
  Write-Host "OK: smoke test do repositorio concluido sem erros e com $($script:WarningCount) warning(s)"
}
else {
  Write-Host 'OK: smoke test do repositorio concluido sem erros'
}
