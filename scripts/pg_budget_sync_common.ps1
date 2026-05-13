. (Join-Path $PSScriptRoot "pg_file_io_common.ps1")

function Resolve-BudgetSyncPath {
  param(
    [string]$RepositoryPath,
    [string]$ExplicitBudgetPath
  )

  if ($ExplicitBudgetPath) {
    return [System.IO.Path]::GetFullPath($ExplicitBudgetPath)
  }

  return Join-Path ([System.IO.Path]::GetFullPath($RepositoryPath)) ".pg\PG_BUDGET_SYNC.json"
}

function Get-BudgetSyncData {
  param([string]$Path)

  try {
    return (Read-Utf8JsonFile -Path $Path)
  } catch {
    throw "PG_BUDGET_SYNC.json invalido ou com JSON mal formado: $Path"
  }
}

function Assert-BudgetRequiredStringProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property -or [string]::IsNullOrWhiteSpace([string]$property.Value)) {
    throw "Campo obrigatorio em falta ou vazio no PG_BUDGET_SYNC.json: $PropertyName"
  }
}

function Assert-BudgetRequiredValueProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property -or $null -eq $property.Value -or [string]::IsNullOrWhiteSpace([string]$property.Value)) {
    throw "Campo obrigatorio em falta ou vazio no PG_BUDGET_SYNC.json: $PropertyName"
  }
}

function Assert-BudgetOptionalStringProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if ($property -and $null -ne $property.Value -and ($property.Value -isnot [string])) {
    throw "Campo opcional com tipo invalido no PG_BUDGET_SYNC.json: $PropertyName"
  }
}

function Assert-BudgetArrayProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property) {
    throw "Array obrigatorio em falta no PG_BUDGET_SYNC.json: $PropertyName"
  }

  if ($property.Value -isnot [System.Array]) {
    throw "Campo com tipo invalido no PG_BUDGET_SYNC.json. Esperado array: $PropertyName"
  }

  return @($property.Value)
}

function Assert-BudgetObjectProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property -or $null -eq $property.Value) {
    throw "Objeto obrigatorio em falta no PG_BUDGET_SYNC.json: $PropertyName"
  }

  if ($property.Value -isnot [pscustomobject]) {
    throw "Campo com tipo invalido no PG_BUDGET_SYNC.json. Esperado objeto: $PropertyName"
  }

  return [pscustomobject]$property.Value
}

function Assert-BudgetNumericProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property -or $null -eq $property.Value) {
    throw "Campo numerico obrigatorio em falta no PG_BUDGET_SYNC.json: $PropertyName"
  }

  if ($property.Value -isnot [byte] -and $property.Value -isnot [int16] -and $property.Value -isnot [int32] -and $property.Value -isnot [int64] -and $property.Value -isnot [decimal] -and $property.Value -isnot [double] -and $property.Value -isnot [single]) {
    throw "Campo numerico com tipo invalido no PG_BUDGET_SYNC.json: $PropertyName"
  }
}

function Assert-BudgetDateTimeProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if (-not $property -or [string]::IsNullOrWhiteSpace([string]$property.Value)) {
    throw "Campo de data obrigatorio em falta ou vazio no PG_BUDGET_SYNC.json: $PropertyName"
  }

  [DateTimeOffset]$parsed = [DateTimeOffset]::MinValue
  if (-not [DateTimeOffset]::TryParse([string]$property.Value, [ref]$parsed)) {
    throw "Campo de data com formato invalido no PG_BUDGET_SYNC.json: $PropertyName"
  }
}

function Assert-BudgetAllowedStringProperty {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName,
    [string[]]$AllowedValues
  )

  Assert-BudgetRequiredStringProperty -Data $Data -PropertyName $PropertyName
  $value = [string]$Data.PSObject.Properties[$PropertyName].Value
  if ($AllowedValues -notcontains $value) {
    throw "Campo com valor invalido no PG_BUDGET_SYNC.json: $PropertyName"
  }
}

function Assert-BudgetSyncContract {
  param([pscustomobject]$Data)

  foreach ($propertyName in @("schema_version", "project_name", "budget_currency")) {
    Assert-BudgetRequiredStringProperty -Data $Data -PropertyName $propertyName
  }

  Assert-BudgetRequiredValueProperty -Data $Data -PropertyName "project_id"
  Assert-BudgetOptionalStringProperty -Data $Data -PropertyName "budget_owner"

  if ($Data.PSObject.Properties["baseline_status"] -and -not [string]::IsNullOrWhiteSpace([string]$Data.baseline_status)) {
    Assert-BudgetAllowedStringProperty -Data $Data -PropertyName "baseline_status" -AllowedValues @("draft", "approved", "consuming", "closed")
  }
  if ($Data.PSObject.Properties["materiality_threshold"] -and $null -ne $Data.materiality_threshold -and [string]$Data.materiality_threshold -ne "") {
    Assert-BudgetNumericProperty -Data $Data -PropertyName "materiality_threshold"
  }

  $budgetLines = Assert-BudgetArrayProperty -Data $Data -PropertyName "budget_lines"
  foreach ($budgetLine in $budgetLines) {
    if ($budgetLine -isnot [pscustomobject]) {
      throw "Array budget_lines com item invalido no PG_BUDGET_SYNC.json. Esperado objeto."
    }

    foreach ($propertyName in @(
      "budget_line_id",
      "category",
      "status",
      "owner"
    )) {
      Assert-BudgetRequiredStringProperty -Data $budgetLine -PropertyName $propertyName
    }

    foreach ($propertyName in @(
      "planned_amount",
      "approved_amount",
      "consumed_amount"
    )) {
      Assert-BudgetNumericProperty -Data $budgetLine -PropertyName $propertyName
    }

    Assert-BudgetAllowedStringProperty -Data $budgetLine -PropertyName "status" -AllowedValues @("draft", "approved", "consuming", "closed")

    if ($budgetLine.PSObject.Properties["source_budget_line_id"]) {
      Assert-BudgetRequiredValueProperty -Data $budgetLine -PropertyName "source_budget_line_id"
    }
    if ($budgetLine.PSObject.Properties["budget_origin"]) {
      Assert-BudgetAllowedStringProperty -Data $budgetLine -PropertyName "budget_origin" -AllowedValues @("project_budget_register")
    }
    if ($budgetLine.PSObject.Properties["notes"]) {
      Assert-BudgetOptionalStringProperty -Data $budgetLine -PropertyName "notes"
    }
  }

  $sourceMetadata = Assert-BudgetObjectProperty -Data $Data -PropertyName "source_metadata"
  foreach ($propertyName in @(
    "source_system",
    "source_model",
    "sync_trigger",
    "sync_published_by",
    "repo_branch",
    "payload_hash"
  )) {
    Assert-BudgetRequiredStringProperty -Data $sourceMetadata -PropertyName $propertyName
  }
  Assert-BudgetRequiredValueProperty -Data $sourceMetadata -PropertyName "source_record_id"
  Assert-BudgetDateTimeProperty -Data $sourceMetadata -PropertyName "sync_published_at"
  Assert-BudgetOptionalStringProperty -Data $sourceMetadata -PropertyName "source_record_url"

  return $Data
}
