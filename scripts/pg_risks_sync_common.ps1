. (Join-Path $PSScriptRoot "pg_file_io_common.ps1")

function Resolve-ProjectRisksSyncPath {
  param(
    [string]$RepositoryPath,
    [string]$ExplicitRisksPath
  )

  if ($ExplicitRisksPath) {
    return [System.IO.Path]::GetFullPath($ExplicitRisksPath)
  }

  return Join-Path ([System.IO.Path]::GetFullPath($RepositoryPath)) ".pg\PG_RISKS_SYNC.json"
}

function Get-ProjectRisksSyncData {
  param([string]$Path)

  try {
    return (Read-Utf8JsonFile -Path $Path)
  } catch {
    throw "PG_RISKS_SYNC.json invalido ou com JSON mal formado: $Path"
  }
}

function Assert-RequiredStringProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property -or [string]::IsNullOrWhiteSpace([string]$property.Value)) {
    throw "Campo obrigatorio em falta ou vazio no PG_RISKS_SYNC.json: $PropertyName"
  }
}

function Assert-OptionalStringProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if ($property -and $null -ne $property.Value -and ($property.Value -isnot [string])) {
    throw "Campo opcional com tipo invalido no PG_RISKS_SYNC.json: $PropertyName"
  }
}

function Assert-RequiredValueProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property -or $null -eq $property.Value -or [string]::IsNullOrWhiteSpace([string]$property.Value)) {
    throw "Campo obrigatorio em falta ou vazio no PG_RISKS_SYNC.json: $PropertyName"
  }
}

function Assert-ArrayProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property) {
    throw "Array obrigatorio em falta no PG_RISKS_SYNC.json: $PropertyName"
  }

  if ($property.Value -isnot [System.Array]) {
    throw "Campo com tipo invalido no PG_RISKS_SYNC.json. Esperado array: $PropertyName"
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
    throw "Objeto obrigatorio em falta no PG_RISKS_SYNC.json: $PropertyName"
  }

  if ($property.Value -isnot [pscustomobject]) {
    throw "Campo com tipo invalido no PG_RISKS_SYNC.json. Esperado objeto: $PropertyName"
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

    throw "Campo de data obrigatorio em falta ou vazio no PG_RISKS_SYNC.json: $PropertyName"
  }

  [DateTimeOffset]$parsed = [DateTimeOffset]::MinValue
  if (-not [DateTimeOffset]::TryParse([string]$property.Value, [ref]$parsed)) {
    throw "Campo de data com formato invalido no PG_RISKS_SYNC.json: $PropertyName"
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
    throw "Campo com valor invalido no PG_RISKS_SYNC.json: $PropertyName"
  }
}

function Assert-ProjectRisksSyncContract {
  param([pscustomobject]$Data)

  foreach ($propertyName in @("schema_version", "project_name")) {
    Assert-RequiredStringProperty -Data $Data -PropertyName $propertyName
  }

  Assert-RequiredValueProperty -Data $Data -PropertyName "project_id"
  Assert-OptionalStringProperty -Data $Data -PropertyName "project_phase"

  $risks = Assert-ArrayProperty -Data $Data -PropertyName "risks"
  foreach ($risk in $risks) {
    if ($risk -isnot [pscustomobject]) {
      throw "Array risks com item invalido no PG_RISKS_SYNC.json. Esperado objeto."
    }

    foreach ($propertyName in @(
      "risk_id",
      "title",
      "description",
      "severity",
      "status",
      "mitigation",
      "owner",
      "last_review_at",
      "source_reference"
    )) {
      Assert-RequiredStringProperty -Data $risk -PropertyName $propertyName
    }

    Assert-DateTimeProperty -Data $risk -PropertyName "last_review_at"
    Assert-AllowedStringProperty -Data $risk -PropertyName "severity" -AllowedValues @("low", "medium", "high", "critical")
    Assert-AllowedStringProperty -Data $risk -PropertyName "status" -AllowedValues @("open", "monitoring", "mitigated")
    Assert-OptionalStringProperty -Data $risk -PropertyName "risk_origin"
    if ($risk.PSObject.Properties["source_risk_id"]) {
      Assert-RequiredValueProperty -Data $risk -PropertyName "source_risk_id"
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
