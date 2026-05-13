. (Join-Path $PSScriptRoot "pg_file_io_common.ps1")

function Resolve-ProjectStatusSyncPath {
  param(
    [string]$RepositoryPath,
    [string]$ExplicitStatusPath
  )

  if ($ExplicitStatusPath) {
    return [System.IO.Path]::GetFullPath($ExplicitStatusPath)
  }

  return Join-Path ([System.IO.Path]::GetFullPath($RepositoryPath)) ".pg\PG_PROJECT_STATUS_SYNC.json"
}

function Get-ProjectStatusSyncData {
  param([string]$Path)

  try {
    return (Read-Utf8JsonFile -Path $Path)
  } catch {
    throw "PG_PROJECT_STATUS_SYNC.json invalido ou com JSON mal formado: $Path"
  }
}

function Assert-RequiredStringProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property -or [string]::IsNullOrWhiteSpace([string]$property.Value)) {
    throw "Campo obrigatorio em falta ou vazio no PG_PROJECT_STATUS_SYNC.json: $PropertyName"
  }
}

function Assert-OptionalStringProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if ($property -and $null -ne $property.Value -and ($property.Value -isnot [string])) {
    throw "Campo opcional com tipo invalido no PG_PROJECT_STATUS_SYNC.json: $PropertyName"
  }
}

function Assert-ArrayProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property) {
    throw "Array obrigatorio em falta no PG_PROJECT_STATUS_SYNC.json: $PropertyName"
  }

  if ($property.Value -isnot [System.Array]) {
    throw "Campo com tipo invalido no PG_PROJECT_STATUS_SYNC.json. Esperado array: $PropertyName"
  }

  foreach ($item in $property.Value) {
    if ($item -isnot [string]) {
      throw "Array com valor invalido no PG_PROJECT_STATUS_SYNC.json. Esperado string em: $PropertyName"
    }
  }
}

function Assert-DateTimeProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName,
    [switch]$Optional
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property -or [string]::IsNullOrWhiteSpace([string]$property.Value)) {
    if ($Optional) {
      return
    }

    throw "Campo de data obrigatorio em falta ou vazio no PG_PROJECT_STATUS_SYNC.json: $PropertyName"
  }

  [DateTimeOffset]$parsed = [DateTimeOffset]::MinValue
  if (-not [DateTimeOffset]::TryParse([string]$property.Value, [ref]$parsed)) {
    throw "Campo de data com formato invalido no PG_PROJECT_STATUS_SYNC.json: $PropertyName"
  }
}

function Assert-ProjectStatusSyncContract {
  param([pscustomobject]$Data)

  $requiredStringProperties = @(
    "schema_version",
    "project_name",
    "phase",
    "status_summary",
    "source_reference",
    "source_system"
  )

  foreach ($propertyName in $requiredStringProperties) {
    Assert-RequiredStringProperty -Data $Data -PropertyName $propertyName
  }

  Assert-DateTimeProperty -Data $Data -PropertyName "last_update_at"
  Assert-DateTimeProperty -Data $Data -PropertyName "sync_published_at" -Optional

  $arrayProperties = @(
    "milestones",
    "blockers",
    "risks",
    "next_steps",
    "pending_decisions"
  )

  foreach ($propertyName in $arrayProperties) {
    Assert-ArrayProperty -Data $Data -PropertyName $propertyName
  }

  $optionalStringProperties = @(
    "go_live_target",
    "owner",
    "source_model",
    "source_record_id",
    "source_record_url",
    "sync_published_by",
    "sync_trigger",
    "repo_branch"
  )

  foreach ($propertyName in $optionalStringProperties) {
    Assert-OptionalStringProperty -Data $Data -PropertyName $propertyName
  }

  return $Data
}
