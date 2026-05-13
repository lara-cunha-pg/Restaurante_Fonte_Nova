param(
  [Parameter(Mandatory = $true)]
  [string]$RepoPath,

  [string]$ExportCsvPath
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "pg_file_io_common.ps1")

function Get-ScopeSyncPath {
  param([string]$RootPath)

  return (Join-Path $RootPath ".pg\PG_SCOPE_SYNC.json")
}

function Get-TokenCount {
  param([AllowNull()][string]$Text)

  $normalized = Normalize-PgText -Text $Text -DropPlaceholders
  if ([string]::IsNullOrWhiteSpace($normalized)) {
    return 0
  }

  return @($normalized.Split(' ', [System.StringSplitOptions]::RemoveEmptyEntries)).Count
}

function Get-NormalizedCriteria {
  param([AllowNull()][object[]]$Criteria)

  return @(
    Get-PgSanitizedLines `
      -Items @($Criteria) `
      -StripEmailNoise `
      -DropPlaceholders `
      -MaxChars 220
  )
}

function Test-GenericExactSummary {
  param([AllowNull()][string]$Summary)

  $normalized = (Normalize-PgText -Text $Summary -DropPlaceholders).ToLowerInvariant()
  if ([string]::IsNullOrWhiteSpace($normalized)) {
    return $false
  }

  $formD = $normalized.Normalize([Text.NormalizationForm]::FormD)
  $builder = New-Object System.Text.StringBuilder
  foreach ($char in $formD.ToCharArray()) {
    if ([Globalization.CharUnicodeInfo]::GetUnicodeCategory($char) -ne [Globalization.UnicodeCategory]::NonSpacingMark) {
      [void]$builder.Append($char)
    }
  }
  $normalized = $builder.ToString().Normalize([Text.NormalizationForm]::FormC)

  $genericSummaries = @(
    "configuracao",
    "configuracoes",
    "validacao",
    "validacoes",
    "ajustes",
    "melhorias",
    "desenvolvimento",
    "customizacao",
    "customizacao odoo",
    "analise",
    "analise funcional",
    "suporte",
    "vendas",
    "inventario",
    "compras",
    "contabilidade",
    "projeto"
  )

  return $genericSummaries -contains $normalized
}

function Test-PlaceholderItem {
  param(
    [AllowNull()][string]$Summary,
    [AllowNull()][object[]]$Criteria
  )

  if (Test-PgPlaceholderText -Text $Summary) {
    return $true
  }

  foreach ($line in @($Criteria)) {
    if (Test-PgPlaceholderText -Text ([string]$line)) {
      return $true
    }
  }

  return $false
}

function Get-WeaknessFlags {
  param(
    [AllowNull()][string]$Summary,
    [AllowNull()][object[]]$Criteria
  )

  $flags = @()
  $tokenCount = Get-TokenCount -Text $Summary
  $normalizedCriteria = Get-NormalizedCriteria -Criteria $Criteria

  if ($tokenCount -le 2) {
    $flags += "short_summary"
  }
  if (Test-GenericExactSummary -Summary $Summary) {
    $flags += "generic_summary"
  }
  if (-not $normalizedCriteria -or $normalizedCriteria.Count -eq 0) {
    $flags += "empty_criteria"
  }
  if (Test-PlaceholderItem -Summary $Summary -Criteria $Criteria) {
    $flags += "placeholder"
  }

  return $flags
}

$repoRoot = [System.IO.Path]::GetFullPath($RepoPath)
if (-not (Test-Path $repoRoot)) {
  throw "RepoPath inexistente: $repoRoot"
}

$scopePath = Get-ScopeSyncPath -RootPath $repoRoot
if (-not (Test-Path $scopePath)) {
  throw "Ficheiro scope sync inexistente: $scopePath"
}

$scope = Read-Utf8JsonFile -Path $scopePath
$items = @($scope.scope_items)

$rows = @()
foreach ($item in $items) {
  $summary = [string]$item.scope_summary
  $criteria = @($item.acceptance_criteria)
  $flags = @(Get-WeaknessFlags -Summary $summary -Criteria $criteria)
  $rows += [pscustomobject]@{
    task_id = [string]$item.task_id
    task_name = Normalize-PgText -Text ([string]$item.task_name) -MaxChars 120
    scope_summary = Normalize-PgText -Text $summary -MaxChars 160
    acceptance_criteria_count = (Get-NormalizedCriteria -Criteria $criteria).Count
    token_count = Get-TokenCount -Text $summary
    weakness_flags = ($flags -join ';')
    source_url = [string]$item.source_url
  }
}

$emptyCriteriaCount = @(
  $rows | Where-Object { $_.weakness_flags -match '(^|;)empty_criteria(;|$)' }
).Count

$genericExactScopeSummaryCount = @(
  $rows | Where-Object { $_.weakness_flags -match '(^|;)generic_summary(;|$)' }
).Count

$shortScopeSummaryCount = @(
  $rows | Where-Object { $_.weakness_flags -match '(^|;)short_summary(;|$)' }
).Count

$placeholderItemCount = @(
  $rows | Where-Object { $_.weakness_flags -match '(^|;)placeholder(;|$)' }
).Count

$metrics = [ordered]@{
  repo_path = $repoRoot
  scope_sync_path = $scopePath
  scope_items = $rows.Count
  empty_acceptance_criteria = $emptyCriteriaCount
  generic_exact_scope_summary = $genericExactScopeSummaryCount
  short_scope_summary_le2_tokens = $shortScopeSummaryCount
  placeholder_items = $placeholderItemCount
}

Write-Output "Scope quality metrics"
$metrics.GetEnumerator() | ForEach-Object {
  Write-Output ("- {0}: {1}" -f $_.Key, $_.Value)
}

$candidateRows = @(
  $rows |
    Where-Object { -not [string]::IsNullOrWhiteSpace($_.weakness_flags) } |
    Sort-Object @{ Expression = { ($_.weakness_flags -split ';').Count }; Descending = $true }, task_id
)

if ($ExportCsvPath) {
  $targetCsvPath = [System.IO.Path]::GetFullPath($ExportCsvPath)
  $directory = Split-Path -Parent $targetCsvPath
  if ($directory -and -not (Test-Path $directory)) {
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
  }
  $candidateRows | Export-Csv -Path $targetCsvPath -NoTypeInformation -Encoding utf8
  Write-Output ("- exported_candidate_rows: {0}" -f $targetCsvPath)
}

if ($candidateRows.Count -gt 0) {
  Write-Output ""
  Write-Output "Top weak scope items"
  foreach ($row in ($candidateRows | Select-Object -First 10)) {
    Write-Output ("- task {0}: {1} [{2}]" -f $row.task_id, $row.task_name, $row.weakness_flags)
  }
}
