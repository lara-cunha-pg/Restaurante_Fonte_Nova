. (Join-Path $PSScriptRoot "pg_file_io_common.ps1")

function Resolve-ProjectDecisionsSyncPath {
  param(
    [string]$RepositoryPath,
    [string]$ExplicitDecisionsPath
  )

  if ($ExplicitDecisionsPath) {
    return [System.IO.Path]::GetFullPath($ExplicitDecisionsPath)
  }

  return Join-Path ([System.IO.Path]::GetFullPath($RepositoryPath)) ".pg\PG_DECISIONS_SYNC.json"
}

function Get-ProjectDecisionsSyncData {
  param([string]$Path)

  try {
    return (Read-Utf8JsonFile -Path $Path)
  } catch {
    throw "PG_DECISIONS_SYNC.json invalido ou com JSON mal formado: $Path"
  }
}

function Assert-RequiredStringProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property -or [string]::IsNullOrWhiteSpace([string]$property.Value)) {
    throw "Campo obrigatorio em falta ou vazio no PG_DECISIONS_SYNC.json: $PropertyName"
  }
}

function Assert-OptionalStringProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if ($property -and $null -ne $property.Value -and ($property.Value -isnot [string])) {
    throw "Campo opcional com tipo invalido no PG_DECISIONS_SYNC.json: $PropertyName"
  }
}

function Assert-RequiredValueProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property -or $null -eq $property.Value -or [string]::IsNullOrWhiteSpace([string]$property.Value)) {
    throw "Campo obrigatorio em falta ou vazio no PG_DECISIONS_SYNC.json: $PropertyName"
  }
}

function Assert-ArrayProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property) {
    throw "Array obrigatorio em falta no PG_DECISIONS_SYNC.json: $PropertyName"
  }

  if ($property.Value -isnot [System.Array]) {
    throw "Campo com tipo invalido no PG_DECISIONS_SYNC.json. Esperado array: $PropertyName"
  }

  return @($property.Value)
}

function Assert-ObjectProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property -or $null -eq $property.Value) {
    throw "Objeto obrigatorio em falta no PG_DECISIONS_SYNC.json: $PropertyName"
  }

  if ($property.Value -isnot [pscustomobject]) {
    throw "Campo com tipo invalido no PG_DECISIONS_SYNC.json. Esperado objeto: $PropertyName"
  }

  return [pscustomobject]$property.Value
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

    throw "Campo de data obrigatorio em falta ou vazio no PG_DECISIONS_SYNC.json: $PropertyName"
  }

  [DateTimeOffset]$parsed = [DateTimeOffset]::MinValue
  if (-not [DateTimeOffset]::TryParse([string]$property.Value, [ref]$parsed)) {
    throw "Campo de data com formato invalido no PG_DECISIONS_SYNC.json: $PropertyName"
  }
}

function Assert-AllowedStringProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName,
    [string[]]$AllowedValues
  )

  Assert-RequiredStringProperty -Data $Data -PropertyName $PropertyName
  $value = [string]$Data.PSObject.Properties[$PropertyName].Value
  if ($AllowedValues -notcontains $value) {
    throw "Campo com valor invalido no PG_DECISIONS_SYNC.json: $PropertyName"
  }
}

function Assert-ProjectDecisionsSyncContract {
  param([pscustomobject]$Data)

  foreach ($propertyName in @("schema_version", "project_name")) {
    Assert-RequiredStringProperty -Data $Data -PropertyName $propertyName
  }

  Assert-RequiredValueProperty -Data $Data -PropertyName "project_id"
  Assert-OptionalStringProperty -Data $Data -PropertyName "project_phase"

  $decisions = Assert-ArrayProperty -Data $Data -PropertyName "decisions"
  foreach ($decision in $decisions) {
    if ($decision -isnot [pscustomobject]) {
      throw "Array decisions com item invalido no PG_DECISIONS_SYNC.json. Esperado objeto."
    }

    foreach ($propertyName in @(
      "decision_id",
      "title",
      "decision_summary",
      "decision_state",
      "decided_at",
      "decided_by",
      "impact_scope",
      "source_reference"
    )) {
      Assert-RequiredStringProperty -Data $decision -PropertyName $propertyName
    }

    Assert-DateTimeProperty -Data $decision -PropertyName "decided_at"
    Assert-AllowedStringProperty -Data $decision -PropertyName "decision_state" -AllowedValues @("closed")
    Assert-AllowedStringProperty -Data $decision -PropertyName "impact_scope" -AllowedValues @("task_scope_item")
    Assert-OptionalStringProperty -Data $decision -PropertyName "decision_origin"
    Assert-OptionalStringProperty -Data $decision -PropertyName "recommendation_class"
    Assert-OptionalStringProperty -Data $decision -PropertyName "recommended_module"
    Assert-OptionalStringProperty -Data $decision -PropertyName "rationale_summary"
    Assert-OptionalStringProperty -Data $decision -PropertyName "scope_state"
    if ($decision.PSObject.Properties["source_task_id"]) {
      Assert-RequiredValueProperty -Data $decision -PropertyName "source_task_id"
    }
  }

  $sourceMetadata = Assert-ObjectProperty -Data $Data -PropertyName "source_metadata"
  foreach ($propertyName in @(
    "source_system",
    "source_model",
    "sync_trigger",
    "sync_published_by",
    "repo_branch",
    "payload_hash"
  )) {
    Assert-RequiredStringProperty -Data $sourceMetadata -PropertyName $propertyName
  }
  Assert-RequiredValueProperty -Data $sourceMetadata -PropertyName "source_record_id"
  Assert-DateTimeProperty -Data $sourceMetadata -PropertyName "sync_published_at"
  Assert-OptionalStringProperty -Data $sourceMetadata -PropertyName "source_record_url"

  return $Data
}
