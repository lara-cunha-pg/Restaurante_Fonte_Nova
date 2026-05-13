param(
  [Parameter(Mandatory = $true)]
  [string]$RepoName,

  [string]$RepoPath,

  [switch]$Force
)

$ErrorActionPreference = "Stop"

function Resolve-TemplateRoot {
  return (Split-Path -Parent $PSScriptRoot)
}

function Resolve-TargetRepo {
  param(
    [string]$Name,
    [string]$ExplicitPath,
    [string]$TemplateRoot
  )

  if ($ExplicitPath) {
    return [System.IO.Path]::GetFullPath($ExplicitPath)
  }

  $reposRoot = Split-Path -Parent $TemplateRoot
  return Join-Path $reposRoot $Name
}

function Ensure-ParentDirectory {
  param([string]$FilePath)

  $parent = Split-Path -Parent $FilePath
  if (-not [string]::IsNullOrWhiteSpace($parent) -and -not (Test-Path $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
  }
}

$templateRoot = Resolve-TemplateRoot
$templatesDir = Join-Path $templateRoot "templates"
$repo = Resolve-TargetRepo -Name $RepoName -ExplicitPath $RepoPath -TemplateRoot $templateRoot

if (-not (Test-Path $repo)) {
  throw "Repositorio nao encontrado: $repo"
}

$copyMap = @(
  @{ Source = Join-Path $templatesDir ".editorconfig"; Destination = Join-Path $repo ".editorconfig" },
  @{ Source = Join-Path $templatesDir ".gitignore"; Destination = Join-Path $repo ".gitignore" },
  @{ Source = Join-Path $templatesDir ".gitattributes"; Destination = Join-Path $repo ".gitattributes" },
  @{ Source = Join-Path $templatesDir ".github\workflows\pg_refresh_pg_context.yml"; Destination = Join-Path $repo ".github\workflows\pg_refresh_pg_context.yml" },
  @{ Source = Join-Path $templatesDir "AGENTS.md"; Destination = Join-Path $repo "AGENTS.md" },
  @{ Source = Join-Path $templatesDir "CLAUDE.md"; Destination = Join-Path $repo "CLAUDE.md" },
  @{ Source = Join-Path $templatesDir "PG_CONTEXT.md"; Destination = Join-Path $repo "PG_CONTEXT.md" },
  @{ Source = Join-Path $templatesDir "PG_SCOPE_INTAKE.yaml"; Destination = Join-Path $repo "PG_SCOPE_INTAKE.yaml" },
  @{ Source = Join-Path $templateRoot "config.toml"; Destination = Join-Path $repo "config.toml" }
)

foreach ($item in $copyMap) {
  if (-not (Test-Path $item.Source)) {
    throw "Ficheiro de template nao encontrado: $($item.Source)"
  }

  if ((-not (Test-Path $item.Destination)) -or $Force) {
    Ensure-ParentDirectory -FilePath $item.Destination
    Copy-Item -Path $item.Source -Destination $item.Destination -Force:$Force
    Write-Host "OK: $($item.Destination)"
  } else {
    Write-Host "SKIP: $($item.Destination) ja existe"
  }
}

$contextDest = Join-Path $repo "PG_CONTEXT.md"
$contextSrc = Join-Path $templatesDir "PG_CONTEXT.md"
if ((Test-Path $contextDest) -and (Test-Path $contextSrc)) {
  $existingContent = Get-Content -Path $contextDest -Raw -ErrorAction SilentlyContinue
  if ($existingContent -notmatch "<!-- PG_AUTO:IDENTIFICACAO:START -->") {
    Copy-Item -Path $contextSrc -Destination $contextDest -Force
    Write-Host "OK: PG_CONTEXT.md substituido (formato sem marcadores PG_AUTO incompativel com o framework)"
  }
}

$frameworkLinkScript = Join-Path $PSScriptRoot "pg_link_framework.ps1"
if (Test-Path $frameworkLinkScript) {
  & $frameworkLinkScript -RepoPath $repo
}

$directoriesToEnsure = @(
  (Join-Path $repo "vendor"),
  (Join-Path $repo ".pg")
)

foreach ($directory in $directoriesToEnsure) {
  if (-not (Test-Path $directory)) {
    New-Item -ItemType Directory -Path $directory | Out-Null
    Write-Host "OK: criada pasta $directory"
  }
}

$statusTemplate = Join-Path $templatesDir ".pg\PG_PROJECT_STATUS_SYNC.json"
$statusDestination = Join-Path $repo ".pg\PG_PROJECT_STATUS_SYNC.json"
if (-not (Test-Path $statusTemplate)) {
  throw "Ficheiro de template nao encontrado: $statusTemplate"
}

if ((-not (Test-Path $statusDestination)) -or $Force) {
  Copy-Item -Path $statusTemplate -Destination $statusDestination -Force:$Force
  Write-Host "OK: $statusDestination"
} else {
  Write-Host "SKIP: $statusDestination ja existe"
}

$scopeTemplate = Join-Path $templatesDir ".pg\PG_SCOPE_SYNC.json"
$scopeDestination = Join-Path $repo ".pg\PG_SCOPE_SYNC.json"
if (-not (Test-Path $scopeTemplate)) {
  throw "Ficheiro de template nao encontrado: $scopeTemplate"
}

if ((-not (Test-Path $scopeDestination)) -or $Force) {
  Copy-Item -Path $scopeTemplate -Destination $scopeDestination -Force:$Force
  Write-Host "OK: $scopeDestination"
} else {
  Write-Host "SKIP: $scopeDestination ja existe"
}

$decisionsTemplate = Join-Path $templatesDir ".pg\PG_DECISIONS_SYNC.json"
$decisionsDestination = Join-Path $repo ".pg\PG_DECISIONS_SYNC.json"
if (-not (Test-Path $decisionsTemplate)) {
  throw "Ficheiro de template nao encontrado: $decisionsTemplate"
}

if ((-not (Test-Path $decisionsDestination)) -or $Force) {
  Copy-Item -Path $decisionsTemplate -Destination $decisionsDestination -Force:$Force
  Write-Host "OK: $decisionsDestination"
} else {
  Write-Host "SKIP: $decisionsDestination ja existe"
}

$risksTemplate = Join-Path $templatesDir ".pg\PG_RISKS_SYNC.json"
$risksDestination = Join-Path $repo ".pg\PG_RISKS_SYNC.json"
if (-not (Test-Path $risksTemplate)) {
  throw "Ficheiro de template nao encontrado: $risksTemplate"
}

if ((-not (Test-Path $risksDestination)) -or $Force) {
  Copy-Item -Path $risksTemplate -Destination $risksDestination -Force:$Force
  Write-Host "OK: $risksDestination"
} else {
  Write-Host "SKIP: $risksDestination ja existe"
}

$deliveriesTemplate = Join-Path $templatesDir ".pg\PG_DELIVERIES_SYNC.json"
$deliveriesDestination = Join-Path $repo ".pg\PG_DELIVERIES_SYNC.json"
if (-not (Test-Path $deliveriesTemplate)) {
  throw "Ficheiro de template nao encontrado: $deliveriesTemplate"
}

if ((-not (Test-Path $deliveriesDestination)) -or $Force) {
  Copy-Item -Path $deliveriesTemplate -Destination $deliveriesDestination -Force:$Force
  Write-Host "OK: $deliveriesDestination"
} else {
  Write-Host "SKIP: $deliveriesDestination ja existe"
}

$requirementsTemplate = Join-Path $templatesDir ".pg\PG_REQUIREMENTS_SYNC.json"
$requirementsDestination = Join-Path $repo ".pg\PG_REQUIREMENTS_SYNC.json"
if (-not (Test-Path $requirementsTemplate)) {
  throw "Ficheiro de template nao encontrado: $requirementsTemplate"
}

if ((-not (Test-Path $requirementsDestination)) -or $Force) {
  Copy-Item -Path $requirementsTemplate -Destination $requirementsDestination -Force:$Force
  Write-Host "OK: $requirementsDestination"
} else {
  Write-Host "SKIP: $requirementsDestination ja existe"
}

$projectPlanTemplate = Join-Path $templatesDir ".pg\PG_PROJECT_PLAN_SYNC.json"
$projectPlanDestination = Join-Path $repo ".pg\PG_PROJECT_PLAN_SYNC.json"
if (-not (Test-Path $projectPlanTemplate)) {
  throw "Ficheiro de template nao encontrado: $projectPlanTemplate"
}

if ((-not (Test-Path $projectPlanDestination)) -or $Force) {
  Copy-Item -Path $projectPlanTemplate -Destination $projectPlanDestination -Force:$Force
  Write-Host "OK: $projectPlanDestination"
} else {
  Write-Host "SKIP: $projectPlanDestination ja existe"
}

$budgetTemplate = Join-Path $templatesDir ".pg\PG_BUDGET_SYNC.json"
$budgetDestination = Join-Path $repo ".pg\PG_BUDGET_SYNC.json"
if (-not (Test-Path $budgetTemplate)) {
  throw "Ficheiro de template nao encontrado: $budgetTemplate"
}

if ((-not (Test-Path $budgetDestination)) -or $Force) {
  Copy-Item -Path $budgetTemplate -Destination $budgetDestination -Force:$Force
  Write-Host "OK: $budgetDestination"
} else {
  Write-Host "SKIP: $budgetDestination ja existe"
}

$claudeGlobalTemplate = Join-Path $templatesDir "CLAUDE_GLOBAL.md"
$homeDir = if ($env:USERPROFILE) { $env:USERPROFILE } else { $env:HOME }
$claudeGlobalDest = Join-Path $homeDir ".claude\CLAUDE.md"
if (Test-Path $claudeGlobalTemplate) {
  if ((-not (Test-Path $claudeGlobalDest)) -or $Force) {
    Ensure-ParentDirectory -FilePath $claudeGlobalDest
    Copy-Item -Path $claudeGlobalTemplate -Destination $claudeGlobalDest -Force:$Force
    Write-Host "OK: $claudeGlobalDest (CLAUDE global do utilizador criado)"
  } else {
    Write-Host "SKIP: $claudeGlobalDest ja existe (CLAUDE global do utilizador)"
  }
} else {
  Write-Host "SKIP: template CLAUDE_GLOBAL.md nao encontrado em $templatesDir"
}

$initScopeScript = Join-Path $PSScriptRoot "pg_init_scope_intake.ps1"
if (Test-Path $initScopeScript) {
  & $initScopeScript -RepoPath $repo -ProjectName $RepoName
}

$buildContextScript = Join-Path $PSScriptRoot "pg_build_pg_context.ps1"
if (Test-Path $buildContextScript) {
  $contextContent = Get-Content -Path (Join-Path $repo "PG_CONTEXT.md") -Raw -ErrorAction SilentlyContinue
  if ($contextContent -match "<!-- PG_AUTO:IDENTIFICACAO:START -->") {
    & $buildContextScript -RepoPath $repo
  } else {
    Write-Host "SKIP: PG_CONTEXT.md sem marcadores PG_AUTO; pg_build_pg_context.ps1 nao executado"
  }
}

$vendorPath = Join-Path $repo "vendor"
$communitySourcePath = Join-Path $vendorPath "odoo_src\community"
$legacyCore = Join-Path $vendorPath "odoo_core"
$syncScript = Join-Path $PSScriptRoot "pg_sync_pg_context.ps1"
if (((Test-Path $communitySourcePath) -or (Test-Path $legacyCore)) -and (Test-Path $syncScript)) {
  & $syncScript -RepoPath $repo
}
