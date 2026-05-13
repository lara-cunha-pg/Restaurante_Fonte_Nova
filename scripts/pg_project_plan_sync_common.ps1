. (Join-Path $PSScriptRoot "pg_file_io_common.ps1")

function Resolve-ProjectPlanSyncPath {
  param(
    [string]$RepositoryPath,
    [string]$ExplicitProjectPlanPath
  )

  if ($ExplicitProjectPlanPath) {
    return [System.IO.Path]::GetFullPath($ExplicitProjectPlanPath)
  }

  return Join-Path ([System.IO.Path]::GetFullPath($RepositoryPath)) ".pg\PG_PROJECT_PLAN_SYNC.json"
}

function Get-ProjectPlanSyncData {
  param([string]$Path)

  try {
    return (Read-Utf8JsonFile -Path $Path)
  } catch {
    throw "PG_PROJECT_PLAN_SYNC.json invalido ou com JSON mal formado: $Path"
  }
}

function Assert-RequiredStringProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property -or [string]::IsNullOrWhiteSpace([string]$property.Value)) {
    throw "Campo obrigatorio em falta ou vazio no PG_PROJECT_PLAN_SYNC.json: $PropertyName"
  }
}

function Assert-OptionalStringProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if ($property -and $null -ne $property.Value -and ($property.Value -isnot [string])) {
    throw "Campo opcional com tipo invalido no PG_PROJECT_PLAN_SYNC.json: $PropertyName"
  }
}

function Assert-RequiredValueProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property -or $null -eq $property.Value -or [string]::IsNullOrWhiteSpace([string]$property.Value)) {
    throw "Campo obrigatorio em falta ou vazio no PG_PROJECT_PLAN_SYNC.json: $PropertyName"
  }
}

function Assert-ArrayProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property) {
    throw "Array obrigatorio em falta no PG_PROJECT_PLAN_SYNC.json: $PropertyName"
  }

  if ($property.Value -isnot [System.Array]) {
    throw "Campo com tipo invalido no PG_PROJECT_PLAN_SYNC.json. Esperado array: $PropertyName"
  }

  return @($property.Value)
}

function Assert-StringArrayProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName,
    [switch]$AllowEmpty
  )

  $values = Assert-ArrayProperty -Data $Data -PropertyName $PropertyName
  if (-not $AllowEmpty -and $values.Count -eq 0) {
    throw "Array obrigatorio sem itens no PG_PROJECT_PLAN_SYNC.json: $PropertyName"
  }

  foreach ($value in $values) {
    if ([string]::IsNullOrWhiteSpace([string]$value)) {
      throw "Array com item vazio no PG_PROJECT_PLAN_SYNC.json: $PropertyName"
    }
  }

  return $values
}

function Assert-ObjectProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property -or $null -eq $property.Value) {
    throw "Objeto obrigatorio em falta no PG_PROJECT_PLAN_SYNC.json: $PropertyName"
  }

  if ($property.Value -isnot [pscustomobject]) {
    throw "Campo com tipo invalido no PG_PROJECT_PLAN_SYNC.json. Esperado objeto: $PropertyName"
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
    throw "Campo de data obrigatorio em falta ou vazio no PG_PROJECT_PLAN_SYNC.json: $PropertyName"
  }

  [DateTimeOffset]$parsed = [DateTimeOffset]::MinValue
  if (-not [DateTimeOffset]::TryParse([string]$property.Value, [ref]$parsed)) {
    throw "Campo de data com formato invalido no PG_PROJECT_PLAN_SYNC.json: $PropertyName"
  }
}

function Assert-NullableDateProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property) {
    throw "Campo de data obrigatorio em falta no PG_PROJECT_PLAN_SYNC.json: $PropertyName"
  }

  if ($null -eq $property.Value -or [string]::IsNullOrWhiteSpace([string]$property.Value)) {
    return
  }

  [DateTimeOffset]$parsed = [DateTimeOffset]::MinValue
  if (-not [DateTimeOffset]::TryParse([string]$property.Value, [ref]$parsed)) {
    throw "Campo de data com formato invalido no PG_PROJECT_PLAN_SYNC.json: $PropertyName"
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
    throw "Campo com valor invalido no PG_PROJECT_PLAN_SYNC.json: $PropertyName"
  }
}

function Assert-ProjectPlanSyncContract {
  param([pscustomobject]$Data)

  foreach ($propertyName in @("schema_version", "project_name")) {
    Assert-RequiredStringProperty -Data $Data -PropertyName $propertyName
  }

  Assert-RequiredValueProperty -Data $Data -PropertyName "project_id"
  Assert-OptionalStringProperty -Data $Data -PropertyName "project_phase"
  Assert-NullableDateProperty -Data $Data -PropertyName "go_live_target"

  $planItems = Assert-ArrayProperty -Data $Data -PropertyName "plan_items"
  foreach ($planItem in $planItems) {
    if ($planItem -isnot [pscustomobject]) {
      throw "Array plan_items com item invalido no PG_PROJECT_PLAN_SYNC.json. Esperado objeto."
    }

    foreach ($propertyName in @(
      "plan_item_id",
      "title",
      "item_type",
      "status",
      "owner"
    )) {
      Assert-RequiredStringProperty -Data $planItem -PropertyName $propertyName
    }

    Assert-NullableDateProperty -Data $planItem -PropertyName "planned_start"
    Assert-NullableDateProperty -Data $planItem -PropertyName "planned_end"
    if (
      ($null -eq $planItem.planned_start -or [string]::IsNullOrWhiteSpace([string]$planItem.planned_start)) -or
      ($null -eq $planItem.planned_end -or [string]::IsNullOrWhiteSpace([string]$planItem.planned_end))
    ) {
      throw "Cada item publicado precisa de planned_start e planned_end no PG_PROJECT_PLAN_SYNC.json."
    }

    Assert-AllowedStringProperty -Data $planItem -PropertyName "item_type" -AllowedValues @("milestone")
    Assert-AllowedStringProperty -Data $planItem -PropertyName "status" -AllowedValues @("planned", "in_progress", "completed")
    Assert-StringArrayProperty -Data $planItem -PropertyName "dependency_refs" -AllowEmpty | Out-Null

    if ($planItem.PSObject.Properties["source_milestone_id"]) {
      Assert-RequiredValueProperty -Data $planItem -PropertyName "source_milestone_id"
    }
    if ($planItem.PSObject.Properties["plan_origin"]) {
      Assert-AllowedStringProperty -Data $planItem -PropertyName "plan_origin" -AllowedValues @("project_milestone_baseline")
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
