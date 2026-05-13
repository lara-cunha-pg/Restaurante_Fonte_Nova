param(
  [Parameter(Mandatory = $true)]
  [string]$RepoPath,

  [string]$ProjectPlanPath
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "pg_project_plan_sync_common.ps1")

$repo = [System.IO.Path]::GetFullPath($RepoPath)
if (-not (Test-Path $repo)) {
  throw "Repositorio nao encontrado: $repo"
}

$resolvedProjectPlanPath = Resolve-ProjectPlanSyncPath -RepositoryPath $repo -ExplicitProjectPlanPath $ProjectPlanPath
if (-not (Test-Path $resolvedProjectPlanPath)) {
  throw "PG_PROJECT_PLAN_SYNC.json nao encontrado em $resolvedProjectPlanPath"
}

$projectPlan = Get-ProjectPlanSyncData -Path $resolvedProjectPlanPath
[void](Assert-ProjectPlanSyncContract -Data $projectPlan)

Write-Host "OK: PG_PROJECT_PLAN_SYNC.json validado com sucesso"
