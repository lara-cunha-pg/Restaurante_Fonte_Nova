. (Join-Path $PSScriptRoot "pg_file_io_common.ps1")

function Resolve-ProjectScopeSyncPath {
  param(
    [string]$RepositoryPath,
    [string]$ExplicitScopePath
  )

  if ($ExplicitScopePath) {
    return [System.IO.Path]::GetFullPath($ExplicitScopePath)
  }

  return Join-Path ([System.IO.Path]::GetFullPath($RepositoryPath)) ".pg\PG_SCOPE_SYNC.json"
}

function Get-ProjectScopeSyncData {
  param([string]$Path)

  try {
    return (Read-Utf8JsonFile -Path $Path)
  } catch {
    throw "PG_SCOPE_SYNC.json invalido ou com JSON mal formado: $Path"
  }
}

function Assert-RequiredStringProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property -or [string]::IsNullOrWhiteSpace([string]$property.Value)) {
    throw "Campo obrigatorio em falta ou vazio no PG_SCOPE_SYNC.json: $PropertyName"
  }
}

function Assert-OptionalStringProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if ($property -and $null -ne $property.Value -and ($property.Value -isnot [string])) {
    throw "Campo opcional com tipo invalido no PG_SCOPE_SYNC.json: $PropertyName"
  }
}

function Assert-RequiredValueProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property -or $null -eq $property.Value -or [string]::IsNullOrWhiteSpace([string]$property.Value)) {
    throw "Campo obrigatorio em falta ou vazio no PG_SCOPE_SYNC.json: $PropertyName"
  }
}

function Assert-ObjectProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property -or $null -eq $property.Value) {
    throw "Objeto obrigatorio em falta no PG_SCOPE_SYNC.json: $PropertyName"
  }

  if ($property.Value -isnot [pscustomobject]) {
    throw "Campo com tipo invalido no PG_SCOPE_SYNC.json. Esperado objeto: $PropertyName"
  }

  return [pscustomobject]$property.Value
}

function Assert-ArrayProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property) {
    throw "Array obrigatorio em falta no PG_SCOPE_SYNC.json: $PropertyName"
  }

  if ($property.Value -isnot [System.Array]) {
    throw "Campo com tipo invalido no PG_SCOPE_SYNC.json. Esperado array: $PropertyName"
  }

  return @($property.Value)
}

function Assert-StringArrayProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $items = Assert-ArrayProperty -Data $Data -PropertyName $PropertyName
  foreach ($item in $items) {
    if ($item -isnot [string]) {
      throw "Array com valor invalido no PG_SCOPE_SYNC.json. Esperado string em: $PropertyName"
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

    throw "Campo de data obrigatorio em falta ou vazio no PG_SCOPE_SYNC.json: $PropertyName"
  }

  [DateTimeOffset]$parsed = [DateTimeOffset]::MinValue
  if (-not [DateTimeOffset]::TryParse([string]$property.Value, [ref]$parsed)) {
    throw "Campo de data com formato invalido no PG_SCOPE_SYNC.json: $PropertyName"
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
    throw "Campo com valor invalido no PG_SCOPE_SYNC.json: $PropertyName"
  }
}

function Assert-ProjectScopeSyncContract {
  param([pscustomobject]$Data)

  $requiredRootStrings = @(
    "schema_version",
    "project_name",
    "project_phase",
    "odoo_edition",
    "odoo_environment"
  )

  foreach ($propertyName in $requiredRootStrings) {
    Assert-RequiredStringProperty -Data $Data -PropertyName $propertyName
  }

  Assert-RequiredValueProperty -Data $Data -PropertyName "project_id"
  Assert-OptionalStringProperty -Data $Data -PropertyName "client_unit"
  Assert-OptionalStringProperty -Data $Data -PropertyName "repository_summary"
  Assert-OptionalStringProperty -Data $Data -PropertyName "odoo_version"

  $restrictions = Assert-ObjectProperty -Data $Data -PropertyName "restrictions"
  Assert-AllowedStringProperty -Data $restrictions -PropertyName "standard_allowed" -AllowedValues @("yes", "no", "unknown")
  Assert-AllowedStringProperty -Data $restrictions -PropertyName "additional_modules_allowed" -AllowedValues @("yes", "no", "unknown")
  Assert-AllowedStringProperty -Data $restrictions -PropertyName "studio_allowed" -AllowedValues @("yes", "no", "unknown")
  Assert-AllowedStringProperty -Data $restrictions -PropertyName "custom_allowed" -AllowedValues @("yes", "no", "unknown")
  Assert-StringArrayProperty -Data $restrictions -PropertyName "additional_contract_restrictions"

  $overview = Assert-ObjectProperty -Data $Data -PropertyName "scope_overview"
  $overviewStrings = @(
    "business_goal",
    "current_request",
    "current_process",
    "problem_or_need",
    "business_impact",
    "trigger",
    "frequency",
    "volumes",
    "urgency"
  )
  foreach ($propertyName in $overviewStrings) {
    Assert-RequiredStringProperty -Data $overview -PropertyName $propertyName
  }
  Assert-StringArrayProperty -Data $overview -PropertyName "acceptance_criteria"

  $projectLists = Assert-ObjectProperty -Data $Data -PropertyName "project_lists"
  $projectListProperties = @(
    "users_and_roles",
    "known_exceptions",
    "approvals",
    "documents",
    "integrations",
    "reporting_needs",
    "standard_attempted_or_validated",
    "why_standard_was_insufficient"
  )
  foreach ($propertyName in $projectListProperties) {
    Assert-StringArrayProperty -Data $projectLists -PropertyName $propertyName
  }

  $scopeItems = Assert-ArrayProperty -Data $Data -PropertyName "scope_items"
  foreach ($item in $scopeItems) {
    if ($item -isnot [pscustomobject]) {
      throw "Array scope_items com item invalido no PG_SCOPE_SYNC.json. Esperado objeto."
    }

    Assert-RequiredValueProperty -Data $item -PropertyName "task_id"
    Assert-RequiredStringProperty -Data $item -PropertyName "task_name"
    Assert-AllowedStringProperty -Data $item -PropertyName "scope_track" -AllowedValues @("approved_scope", "operational_backlog", "internal_note")
    Assert-RequiredStringProperty -Data $item -PropertyName "scope_state"
    Assert-RequiredStringProperty -Data $item -PropertyName "scope_kind"
    Assert-OptionalStringProperty -Data $item -PropertyName "scope_summary"
    Assert-StringArrayProperty -Data $item -PropertyName "acceptance_criteria"
    Assert-DateTimeProperty -Data $item -PropertyName "last_task_update_at"
    Assert-OptionalStringProperty -Data $item -PropertyName "task_stage"
    Assert-OptionalStringProperty -Data $item -PropertyName "task_priority"
    Assert-OptionalStringProperty -Data $item -PropertyName "source_url"
    if ($item.PSObject.Properties["task_tags"]) {
      Assert-StringArrayProperty -Data $item -PropertyName "task_tags"
    }
    if ($item.PSObject.Properties["assigned_users"]) {
      Assert-StringArrayProperty -Data $item -PropertyName "assigned_users"
    }
  }

  $scopeSummary = Assert-ObjectProperty -Data $Data -PropertyName "scope_summary"
  Assert-DateTimeProperty -Data $scopeSummary -PropertyName "last_scope_change_at" -Optional

  $sourceMetadata = Assert-ObjectProperty -Data $Data -PropertyName "source_metadata"
  $sourceStrings = @(
    "source_system",
    "source_model",
    "sync_trigger",
    "sync_published_by",
    "repo_branch",
    "payload_hash"
  )
  foreach ($propertyName in $sourceStrings) {
    Assert-RequiredStringProperty -Data $sourceMetadata -PropertyName $propertyName
  }
  Assert-RequiredValueProperty -Data $sourceMetadata -PropertyName "source_record_id"
  Assert-DateTimeProperty -Data $sourceMetadata -PropertyName "sync_published_at"
  Assert-OptionalStringProperty -Data $sourceMetadata -PropertyName "source_record_url"
  Assert-OptionalStringProperty -Data $sourceMetadata -PropertyName "sync_reason"

  return $Data
}
