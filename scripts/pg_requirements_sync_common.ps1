. (Join-Path $PSScriptRoot "pg_file_io_common.ps1")

function Resolve-ProjectRequirementsSyncPath {
  param(
    [string]$RepositoryPath,
    [string]$ExplicitRequirementsPath
  )

  if ($ExplicitRequirementsPath) {
    return [System.IO.Path]::GetFullPath($ExplicitRequirementsPath)
  }

  return Join-Path ([System.IO.Path]::GetFullPath($RepositoryPath)) ".pg\PG_REQUIREMENTS_SYNC.json"
}

function Get-ProjectRequirementsSyncData {
  param([string]$Path)

  try {
    return (Read-Utf8JsonFile -Path $Path)
  } catch {
    throw "PG_REQUIREMENTS_SYNC.json invalido ou com JSON mal formado: $Path"
  }
}

function Assert-RequiredStringProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property -or [string]::IsNullOrWhiteSpace([string]$property.Value)) {
    throw "Campo obrigatorio em falta ou vazio no PG_REQUIREMENTS_SYNC.json: $PropertyName"
  }
}

function Assert-OptionalStringProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if ($property -and $null -ne $property.Value -and ($property.Value -isnot [string])) {
    throw "Campo opcional com tipo invalido no PG_REQUIREMENTS_SYNC.json: $PropertyName"
  }
}

function Assert-RequiredValueProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property -or $null -eq $property.Value -or [string]::IsNullOrWhiteSpace([string]$property.Value)) {
    throw "Campo obrigatorio em falta ou vazio no PG_REQUIREMENTS_SYNC.json: $PropertyName"
  }
}

function Assert-ArrayProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property) {
    throw "Array obrigatorio em falta no PG_REQUIREMENTS_SYNC.json: $PropertyName"
  }

  if ($property.Value -isnot [System.Array]) {
    throw "Campo com tipo invalido no PG_REQUIREMENTS_SYNC.json. Esperado array: $PropertyName"
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
    throw "Array obrigatorio sem itens no PG_REQUIREMENTS_SYNC.json: $PropertyName"
  }

  foreach ($value in $values) {
    if ([string]::IsNullOrWhiteSpace([string]$value)) {
      throw "Array com item vazio no PG_REQUIREMENTS_SYNC.json: $PropertyName"
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
    throw "Objeto obrigatorio em falta no PG_REQUIREMENTS_SYNC.json: $PropertyName"
  }

  if ($property.Value -isnot [pscustomobject]) {
    throw "Campo com tipo invalido no PG_REQUIREMENTS_SYNC.json. Esperado objeto: $PropertyName"
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
    throw "Campo de data obrigatorio em falta ou vazio no PG_REQUIREMENTS_SYNC.json: $PropertyName"
  }

  [DateTimeOffset]$parsed = [DateTimeOffset]::MinValue
  if (-not [DateTimeOffset]::TryParse([string]$property.Value, [ref]$parsed)) {
    throw "Campo de data com formato invalido no PG_REQUIREMENTS_SYNC.json: $PropertyName"
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
    throw "Campo com valor invalido no PG_REQUIREMENTS_SYNC.json: $PropertyName"
  }
}

function Assert-ProjectRequirementsSyncContract {
  param([pscustomobject]$Data)

  foreach ($propertyName in @("schema_version", "project_name")) {
    Assert-RequiredStringProperty -Data $Data -PropertyName $propertyName
  }

  Assert-RequiredValueProperty -Data $Data -PropertyName "project_id"
  Assert-OptionalStringProperty -Data $Data -PropertyName "project_phase"

  $requirements = Assert-ArrayProperty -Data $Data -PropertyName "requirements"
  foreach ($requirement in $requirements) {
    if ($requirement -isnot [pscustomobject]) {
      throw "Array requirements com item invalido no PG_REQUIREMENTS_SYNC.json. Esperado objeto."
    }

    foreach ($propertyName in @(
      "requirement_id",
      "title",
      "summary",
      "status",
      "priority",
      "owner"
    )) {
      Assert-RequiredStringProperty -Data $requirement -PropertyName $propertyName
    }

    Assert-AllowedStringProperty -Data $requirement -PropertyName "status" -AllowedValues @("approved", "deferred")
    Assert-AllowedStringProperty -Data $requirement -PropertyName "priority" -AllowedValues @("low", "medium", "high", "critical")
    Assert-StringArrayProperty -Data $requirement -PropertyName "traceability_refs" | Out-Null

    if ($requirement.PSObject.Properties["acceptance_criteria"]) {
      Assert-StringArrayProperty -Data $requirement -PropertyName "acceptance_criteria" -AllowEmpty | Out-Null
    }
    if ($requirement.PSObject.Properties["source_task_id"]) {
      Assert-RequiredValueProperty -Data $requirement -PropertyName "source_task_id"
    }
    if ($requirement.PSObject.Properties["requirement_origin"]) {
      Assert-AllowedStringProperty -Data $requirement -PropertyName "requirement_origin" -AllowedValues @("approved_scope_task")
    }
    if ($requirement.PSObject.Properties["scope_state"]) {
      Assert-AllowedStringProperty -Data $requirement -PropertyName "scope_state" -AllowedValues @("validated", "deferred")
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
