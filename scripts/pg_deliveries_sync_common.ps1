. (Join-Path $PSScriptRoot "pg_file_io_common.ps1")

function Resolve-ProjectDeliveriesSyncPath {
  param(
    [string]$RepositoryPath,
    [string]$ExplicitDeliveriesPath
  )

  if ($ExplicitDeliveriesPath) {
    return [System.IO.Path]::GetFullPath($ExplicitDeliveriesPath)
  }

  return Join-Path ([System.IO.Path]::GetFullPath($RepositoryPath)) ".pg\PG_DELIVERIES_SYNC.json"
}

function Get-ProjectDeliveriesSyncData {
  param([string]$Path)

  try {
    return (Read-Utf8JsonFile -Path $Path)
  } catch {
    throw "PG_DELIVERIES_SYNC.json invalido ou com JSON mal formado: $Path"
  }
}

function Assert-RequiredStringProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property -or [string]::IsNullOrWhiteSpace([string]$property.Value)) {
    throw "Campo obrigatorio em falta ou vazio no PG_DELIVERIES_SYNC.json: $PropertyName"
  }
}

function Assert-OptionalStringProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if ($property -and $null -ne $property.Value -and ($property.Value -isnot [string])) {
    throw "Campo opcional com tipo invalido no PG_DELIVERIES_SYNC.json: $PropertyName"
  }
}

function Assert-RequiredValueProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property -or $null -eq $property.Value -or [string]::IsNullOrWhiteSpace([string]$property.Value)) {
    throw "Campo obrigatorio em falta ou vazio no PG_DELIVERIES_SYNC.json: $PropertyName"
  }
}

function Assert-ArrayProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property) {
    throw "Array obrigatorio em falta no PG_DELIVERIES_SYNC.json: $PropertyName"
  }

  if ($property.Value -isnot [System.Array]) {
    throw "Campo com tipo invalido no PG_DELIVERIES_SYNC.json. Esperado array: $PropertyName"
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
    throw "Objeto obrigatorio em falta no PG_DELIVERIES_SYNC.json: $PropertyName"
  }

  if ($property.Value -isnot [pscustomobject]) {
    throw "Campo com tipo invalido no PG_DELIVERIES_SYNC.json. Esperado objeto: $PropertyName"
  }

  return [pscustomobject]$property.Value
}

function Assert-DateTimeProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property -or [string]::IsNullOrWhiteSpace([string]$property.Value)) {
    throw "Campo de data obrigatorio em falta ou vazio no PG_DELIVERIES_SYNC.json: $PropertyName"
  }

  [DateTimeOffset]$parsed = [DateTimeOffset]::MinValue
  if (-not [DateTimeOffset]::TryParse([string]$property.Value, [ref]$parsed)) {
    throw "Campo de data com formato invalido no PG_DELIVERIES_SYNC.json: $PropertyName"
  }
}

function Assert-NullableDateProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property) {
    throw "Campo de data obrigatorio em falta no PG_DELIVERIES_SYNC.json: $PropertyName"
  }

  if ($null -eq $property.Value -or [string]::IsNullOrWhiteSpace([string]$property.Value)) {
    return
  }

  [DateTimeOffset]$parsed = [DateTimeOffset]::MinValue
  if (-not [DateTimeOffset]::TryParse([string]$property.Value, [ref]$parsed)) {
    throw "Campo de data com formato invalido no PG_DELIVERIES_SYNC.json: $PropertyName"
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
    throw "Campo com valor invalido no PG_DELIVERIES_SYNC.json: $PropertyName"
  }
}

function Assert-ProjectDeliveriesSyncContract {
  param([pscustomobject]$Data)

  foreach ($propertyName in @("schema_version", "project_name")) {
    Assert-RequiredStringProperty -Data $Data -PropertyName $propertyName
  }

  Assert-RequiredValueProperty -Data $Data -PropertyName "project_id"
  Assert-OptionalStringProperty -Data $Data -PropertyName "project_phase"

  $deliveries = Assert-ArrayProperty -Data $Data -PropertyName "deliveries"
  foreach ($delivery in $deliveries) {
    if ($delivery -isnot [pscustomobject]) {
      throw "Array deliveries com item invalido no PG_DELIVERIES_SYNC.json. Esperado objeto."
    }

    foreach ($propertyName in @(
      "delivery_id",
      "title",
      "delivery_state",
      "owner",
      "acceptance_state",
      "source_reference"
    )) {
      Assert-RequiredStringProperty -Data $delivery -PropertyName $propertyName
    }

    Assert-NullableDateProperty -Data $delivery -PropertyName "planned_date"
    Assert-NullableDateProperty -Data $delivery -PropertyName "actual_date"
    if (
      ($null -eq $delivery.planned_date -or [string]::IsNullOrWhiteSpace([string]$delivery.planned_date)) -and
      ($null -eq $delivery.actual_date -or [string]::IsNullOrWhiteSpace([string]$delivery.actual_date))
    ) {
      throw "Cada delivery publicado precisa de planned_date ou actual_date no PG_DELIVERIES_SYNC.json."
    }

    Assert-AllowedStringProperty -Data $delivery -PropertyName "delivery_state" -AllowedValues @("planned", "in_progress", "delivered")
    Assert-AllowedStringProperty -Data $delivery -PropertyName "acceptance_state" -AllowedValues @("pending", "accepted", "rejected")
    Assert-OptionalStringProperty -Data $delivery -PropertyName "delivery_origin"
    if ($delivery.PSObject.Properties["source_milestone_id"]) {
      Assert-RequiredValueProperty -Data $delivery -PropertyName "source_milestone_id"
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
