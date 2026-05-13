param(
  [Parameter(Mandatory = $true)]
  [string]$RepoPath,

  [string]$ScopePath
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "pg_scope_sync_common.ps1")
. (Join-Path $PSScriptRoot "pg_file_io_common.ps1")

function Get-ChildObject {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if ($property -and $property.Value -is [pscustomobject]) {
    return [pscustomobject]$property.Value
  }

  return $null
}

function Get-ScalarValue {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName,
    [string]$Fallback,
    [int]$MaxChars = 0,
    [switch]$StripEmailNoise
  )

  if (-not $Data) {
    return $Fallback
  }

  $property = $Data.PSObject.Properties[$PropertyName]
  if ($property -and $null -ne $property.Value -and -not [string]::IsNullOrWhiteSpace([string]$property.Value)) {
    if ($StripEmailNoise) {
      return (Normalize-PgText -Text ((Get-PgSanitizedLines -Items @([string]$property.Value) -StripEmailNoise -DropPlaceholders -MaxItems 1 -MaxChars $MaxChars) -join ' ') -Fallback $Fallback -MaxChars $MaxChars)
    }
    return (Normalize-PgText -Text ([string]$property.Value) -Fallback $Fallback -MaxChars $MaxChars -DropPlaceholders)
  }

  return $Fallback
}

function Get-ListValue {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName,
    [string]$Fallback,
    [int]$MaxItems = 0,
    [int]$MaxChars = 0,
    [switch]$StripEmailNoise
  )

  if (-not $Data) {
    return @($Fallback)
  }

  $property = $Data.PSObject.Properties[$PropertyName]
  if ($property -and $property.Value) {
    $items = @(Get-PgSanitizedLines -Items @($property.Value) -StripEmailNoise:$StripEmailNoise -DropPlaceholders -MaxItems $MaxItems -MaxChars $MaxChars)
    if ($items.Count -gt 0) {
      return $items
    }
  }

  return @($Fallback)
}

function Get-ArrayValue {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  if (-not $Data) {
    return @()
  }

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property -or $null -eq $property.Value) {
    return @()
  }

  return @($property.Value)
}

function Get-OptionalListValue {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName,
    [int]$MaxItems = 0,
    [int]$MaxChars = 0,
    [switch]$StripEmailNoise
  )

  if (-not $Data) {
    return @()
  }

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property -or $null -eq $property.Value) {
    return @()
  }

  return @(Get-PgSanitizedLines -Items @($property.Value) -StripEmailNoise:$StripEmailNoise -DropPlaceholders -MaxItems $MaxItems -MaxChars $MaxChars)
}

function Convert-ToBulletLines {
  param([string[]]$Items)

  return (Convert-ToPgBulletLines -Items $Items -MaxChars 220)
}

function Convert-ScopeItemsBlock {
  param(
    [System.Array]$ScopeItems,
    [pscustomobject]$ScopeSummary
  )

  $lines = @(
    "Resumo do scope sincronizado:",
    "- Itens ativos: $(Get-ScalarValue -Data $ScopeSummary -PropertyName 'active_scope_item_count' -Fallback '0')",
    "- Itens validados: $(Get-ScalarValue -Data $ScopeSummary -PropertyName 'validated_scope_item_count' -Fallback '0')",
    "- Itens propostos: $(Get-ScalarValue -Data $ScopeSummary -PropertyName 'proposed_scope_item_count' -Fallback '0')",
    "- Itens diferidos: $(Get-ScalarValue -Data $ScopeSummary -PropertyName 'deferred_scope_item_count' -Fallback '0')",
    "- Ultima alteracao de task: $(Get-ScalarValue -Data $ScopeSummary -PropertyName 'last_scope_change_at' -Fallback '[PONTO POR VALIDAR]')",
    "",
    "Itens em ambito:"
  )

  if ($ScopeItems.Count -eq 0) {
    $lines += "- [SEM ITENS ATIVOS]"
    return ($lines -join "`r`n")
  }

  $orderedItems = @(
    $ScopeItems | Sort-Object `
      @{ Expression = { [int](Get-ScalarValue -Data $_ -PropertyName 'scope_sequence' -Fallback '0') } }, `
      @{ Expression = { Get-ScalarValue -Data $_ -PropertyName 'task_name' -Fallback '' } }, `
      @{ Expression = { Get-ScalarValue -Data $_ -PropertyName 'task_id' -Fallback '0' } }
  )

  $itemIndex = 1
  foreach ($item in $orderedItems) {
    $lines += "$itemIndex. $(Get-ScalarValue -Data $item -PropertyName 'task_name' -Fallback '[PONTO POR VALIDAR]' -MaxChars 180)"
    $lines += "Track: $(Get-ScalarValue -Data $item -PropertyName 'scope_track' -Fallback 'approved_scope' -MaxChars 80)"
    $lines += "Estado: $(Get-ScalarValue -Data $item -PropertyName 'scope_state' -Fallback '[PONTO POR VALIDAR]' -MaxChars 80)"
    $lines += "Tipo: $(Get-ScalarValue -Data $item -PropertyName 'scope_kind' -Fallback '[PONTO POR VALIDAR]' -MaxChars 80)"
    $lines += "Sequencia: $(Get-ScalarValue -Data $item -PropertyName 'scope_sequence' -Fallback '0' -MaxChars 20)"
    $lines += "Resumo: $(Get-ScalarValue -Data $item -PropertyName 'scope_summary' -Fallback '[PONTO POR VALIDAR]' -MaxChars 220 -StripEmailNoise)"
    $lines += "Criterios de aceitacao:"
    $lines += Convert-ToPgBulletLines -Items (Get-ListValue -Data $item -PropertyName 'acceptance_criteria' -Fallback 'Sem criterios de aceitacao factuais publicados.' -MaxItems 8 -MaxChars 220 -StripEmailNoise) -Fallback 'Sem criterios de aceitacao factuais publicados.' -MaxChars 220

    $assignedUsers = Get-OptionalListValue -Data $item -PropertyName 'assigned_users' -MaxItems 10 -MaxChars 120
    if ($assignedUsers.Count -gt 0) {
      $lines += "Utilizadores atribuidos:"
      $lines += Convert-ToPgBulletLines -Items $assignedUsers -Fallback '[PONTO POR VALIDAR]' -MaxChars 120
    }

    $updatedAt = Get-ScalarValue -Data $item -PropertyName 'last_task_update_at' -Fallback '' -MaxChars 40
    if (-not [string]::IsNullOrWhiteSpace($updatedAt)) {
      $lines += "Atualizado em: $updatedAt"
    }

    $sourceUrl = Get-ScalarValue -Data $item -PropertyName 'source_url' -Fallback '' -MaxChars 300
    if (-not [string]::IsNullOrWhiteSpace($sourceUrl)) {
      $lines += "Origem: $sourceUrl"
    }

    if ($itemIndex -lt $orderedItems.Count) {
      $lines += ""
    }
    $itemIndex += 1
  }

  return ($lines -join "`r`n")
}

function Replace-MarkedBlock {
  param(
    [string]$Text,
    [string]$Marker,
    [string]$BlockContent
  )

  $start = "<!-- PG_AUTO:$Marker`:START -->"
  $end = "<!-- PG_AUTO:$Marker`:END -->"
  $pattern = "(?s)" + [regex]::Escape($start) + ".*?" + [regex]::Escape($end)
  $replacement = $start + "`r`n" + $BlockContent.TrimEnd() + "`r`n" + $end

  if (-not [regex]::IsMatch($Text, $pattern)) {
    throw "Marcadores nao encontrados para $Marker"
  }

  return [regex]::Replace($Text, $pattern, [System.Text.RegularExpressions.MatchEvaluator]{ param($match) $replacement })
}

function Set-LabeledValue {
  param(
    [string]$Text,
    [string]$Label,
    [string]$Value
  )

  $pattern = "(?m)^" + [regex]::Escape($Label) + ".*$"
  if ([regex]::IsMatch($Text, $pattern)) {
    return [regex]::Replace($Text, $pattern, $Label + " " + $Value)
  }

  return $Text
}

$repo = [System.IO.Path]::GetFullPath($RepoPath)
if (-not (Test-Path $repo)) {
  throw "Repositorio nao encontrado: $repo"
}

$contextPath = Join-Path $repo "PG_CONTEXT.md"
if (-not (Test-Path $contextPath)) {
  throw "PG_CONTEXT.md nao encontrado em $contextPath"
}

$resolvedScopePath = Resolve-ProjectScopeSyncPath -RepositoryPath $repo -ExplicitScopePath $ScopePath
if (-not (Test-Path $resolvedScopePath)) {
  throw "PG_SCOPE_SYNC.json nao encontrado em $resolvedScopePath"
}

$scope = Get-ProjectScopeSyncData -Path $resolvedScopePath
[void](Assert-ProjectScopeSyncContract -Data $scope)

$restrictions = Get-ChildObject -Data $scope -PropertyName "restrictions"
$overview = Get-ChildObject -Data $scope -PropertyName "scope_overview"
$projectLists = Get-ChildObject -Data $scope -PropertyName "project_lists"
$scopeSummary = Get-ChildObject -Data $scope -PropertyName "scope_summary"
$scopeItems = Get-ArrayValue -Data $scope -PropertyName "scope_items"
$sourceMetadata = Get-ChildObject -Data $scope -PropertyName "source_metadata"
$sourceReference = "{0} / {1} / {2}" -f `
  (Get-ScalarValue -Data $sourceMetadata -PropertyName "source_system" -Fallback "[PONTO POR VALIDAR]"), `
  (Get-ScalarValue -Data $sourceMetadata -PropertyName "source_model" -Fallback "[PONTO POR VALIDAR]"), `
  (Get-ScalarValue -Data $sourceMetadata -PropertyName "source_record_id" -Fallback "[PONTO POR VALIDAR]")

$context = Read-Utf8TextFile -Path $contextPath

$identificationBlock = @"
Nome do projeto: $(Get-ScalarValue -Data $scope -PropertyName "project_name" -Fallback "[PREENCHER]" -MaxChars 180)
Cliente / unidade: $(Get-ScalarValue -Data $scope -PropertyName "client_unit" -Fallback "[PREENCHER]" -MaxChars 180)
Resumo funcional do repositorio: $(Get-ScalarValue -Data $scope -PropertyName "repository_summary" -Fallback "[PREENCHER]" -MaxChars 220 -StripEmailNoise)
Fase atual do projeto: $(Get-ScalarValue -Data $scope -PropertyName "project_phase" -Fallback "[PONTO POR VALIDAR]" -MaxChars 80)
"@

$restrictionsBlock = @"
Configuracao standard permitida?: $(Get-ScalarValue -Data $restrictions -PropertyName "standard_allowed" -Fallback "[PONTO POR VALIDAR]" -MaxChars 40)
Modulos standard adicionais permitidos?: $(Get-ScalarValue -Data $restrictions -PropertyName "additional_modules_allowed" -Fallback "[PONTO POR VALIDAR]" -MaxChars 40)
Odoo Studio permitido?: $(Get-ScalarValue -Data $restrictions -PropertyName "studio_allowed" -Fallback "[PONTO POR VALIDAR]" -MaxChars 40)
Custom permitido?: $(Get-ScalarValue -Data $restrictions -PropertyName "custom_allowed" -Fallback "[PONTO POR VALIDAR]" -MaxChars 40)
Restricoes contratuais adicionais: $((Get-ListValue -Data $restrictions -PropertyName "additional_contract_restrictions" -Fallback "[PONTO POR VALIDAR]" -MaxItems 8 -MaxChars 160) -join "; ")
"@

$requestBlock = @"
Requisito / pedido atual: $(Get-ScalarValue -Data $overview -PropertyName "current_request" -Fallback "[PREENCHER]" -MaxChars 220 -StripEmailNoise)
Objetivo de negocio: $(Get-ScalarValue -Data $overview -PropertyName "business_goal" -Fallback "[PREENCHER]" -MaxChars 220 -StripEmailNoise)
Trigger: $(Get-ScalarValue -Data $overview -PropertyName "trigger" -Fallback "[PREENCHER]" -MaxChars 120)
Frequencia: $(Get-ScalarValue -Data $overview -PropertyName "frequency" -Fallback "[PREENCHER]" -MaxChars 120)
Volumes: $(Get-ScalarValue -Data $overview -PropertyName "volumes" -Fallback "[PREENCHER]" -MaxChars 120)
Urgencia: $(Get-ScalarValue -Data $overview -PropertyName "urgency" -Fallback "[PREENCHER]" -MaxChars 40)
Criterios de aceitacao:
$(Convert-ToPgBulletLines -Items (Get-ListValue -Data $overview -PropertyName "acceptance_criteria" -Fallback "Sem criterios de aceitacao factuais publicados." -MaxItems 8 -MaxChars 220 -StripEmailNoise) -Fallback "Sem criterios de aceitacao factuais publicados." -MaxChars 220)
"@

$processBlock = @"
Processo atual: $(Get-ScalarValue -Data $overview -PropertyName "current_process" -Fallback "[PREENCHER]" -MaxChars 220 -StripEmailNoise)
Utilizadores / papeis:
$(Convert-ToPgBulletLines -Items (Get-ListValue -Data $projectLists -PropertyName "users_and_roles" -Fallback "[PREENCHER]" -MaxItems 10 -MaxChars 160) -Fallback "[PREENCHER]" -MaxChars 160)
Excecoes conhecidas:
$(Convert-ToPgBulletLines -Items (Get-ListValue -Data $projectLists -PropertyName "known_exceptions" -Fallback "[PREENCHER]" -MaxItems 8 -MaxChars 220 -StripEmailNoise) -Fallback "[PREENCHER]" -MaxChars 220)
Aprovacoes:
$(Convert-ToPgBulletLines -Items (Get-ListValue -Data $projectLists -PropertyName "approvals" -Fallback "[PREENCHER]" -MaxItems 8 -MaxChars 220 -StripEmailNoise) -Fallback "[PREENCHER]" -MaxChars 220)
Documentos envolvidos:
$(Convert-ToPgBulletLines -Items (Get-ListValue -Data $projectLists -PropertyName "documents" -Fallback "[PREENCHER]" -MaxItems 8 -MaxChars 220 -StripEmailNoise) -Fallback "[PREENCHER]" -MaxChars 220)
Integracoes:
$(Convert-ToPgBulletLines -Items (Get-ListValue -Data $projectLists -PropertyName "integrations" -Fallback "[PREENCHER]" -MaxItems 8 -MaxChars 220 -StripEmailNoise) -Fallback "[PREENCHER]" -MaxChars 220)
Reporting esperado:
$(Convert-ToPgBulletLines -Items (Get-ListValue -Data $projectLists -PropertyName "reporting_needs" -Fallback "[PREENCHER]" -MaxItems 8 -MaxChars 220 -StripEmailNoise) -Fallback "[PREENCHER]" -MaxChars 220)
O que ja foi tentado ou validado no standard atual:
$(Convert-ToPgBulletLines -Items (Get-ListValue -Data $projectLists -PropertyName "standard_attempted_or_validated" -Fallback "[PREENCHER]" -MaxItems 8 -MaxChars 220 -StripEmailNoise) -Fallback "[PREENCHER]" -MaxChars 220)
Porque foi considerado insuficiente:
$(Convert-ToPgBulletLines -Items (Get-ListValue -Data $projectLists -PropertyName "why_standard_was_insufficient" -Fallback "[PREENCHER]" -MaxItems 8 -MaxChars 220 -StripEmailNoise) -Fallback "[PREENCHER]" -MaxChars 220)
"@

$problemBlock = @"
Problema / necessidade observada: $(Get-ScalarValue -Data $overview -PropertyName "problem_or_need" -Fallback "[PREENCHER]" -MaxChars 220 -StripEmailNoise)
"@

$impactBlock = @"
Impacto de negocio: $(Get-ScalarValue -Data $overview -PropertyName "business_impact" -Fallback "[PREENCHER]" -MaxChars 220 -StripEmailNoise)
"@

$scopeItemsBlock = Convert-ScopeItemsBlock -ScopeItems $scopeItems -ScopeSummary $scopeSummary

$context = Replace-MarkedBlock -Text $context -Marker "IDENTIFICACAO" -BlockContent $identificationBlock
$context = Replace-MarkedBlock -Text $context -Marker "RESTRICOES" -BlockContent $restrictionsBlock
$context = Replace-MarkedBlock -Text $context -Marker "PEDIDO_ATUAL" -BlockContent $requestBlock
$context = Replace-MarkedBlock -Text $context -Marker "PROCESSO_ATUAL" -BlockContent $processBlock
$context = Replace-MarkedBlock -Text $context -Marker "PROBLEMA_DOR" -BlockContent $problemBlock
$context = Replace-MarkedBlock -Text $context -Marker "IMPACTO_NEGOCIO" -BlockContent $impactBlock
$context = Replace-MarkedBlock -Text $context -Marker "SCOPE_ITEMS" -BlockContent $scopeItemsBlock
$context = Set-LabeledValue -Text $context -Label "Edicao:" -Value (Get-ScalarValue -Data $scope -PropertyName "odoo_edition" -Fallback "[PONTO POR VALIDAR]" -MaxChars 40)
$context = Set-LabeledValue -Text $context -Label "Ambiente:" -Value (Get-ScalarValue -Data $scope -PropertyName "odoo_environment" -Fallback "[PONTO POR VALIDAR]" -MaxChars 40)
$context = Set-LabeledValue -Text $context -Label "Ultima sincronizacao de ambito:" -Value (Get-ScalarValue -Data $sourceMetadata -PropertyName "sync_published_at" -Fallback "[NAO EXECUTADA]" -MaxChars 40)
$context = Set-LabeledValue -Text $context -Label "Fonte do ambito sincronizado:" -Value $sourceReference

Write-Utf8NoBomFile -Path $contextPath -Content $context

Write-Host "OK: PG_CONTEXT.md atualizado a partir do PG_SCOPE_SYNC.json"
