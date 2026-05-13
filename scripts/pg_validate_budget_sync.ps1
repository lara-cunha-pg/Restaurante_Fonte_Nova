param(
  [Parameter(Mandatory = $true)]
  [string]$RepoPath,

  [string]$BudgetPath
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "pg_budget_sync_common.ps1")

$repo = [System.IO.Path]::GetFullPath($RepoPath)
if (-not (Test-Path $repo)) {
  throw "Repositorio nao encontrado: $repo"
}

$resolvedBudgetPath = Resolve-BudgetSyncPath -RepositoryPath $repo -ExplicitBudgetPath $BudgetPath
if (-not (Test-Path $resolvedBudgetPath)) {
  throw "PG_BUDGET_SYNC.json nao encontrado em $resolvedBudgetPath"
}

$budget = Get-BudgetSyncData -Path $resolvedBudgetPath
[void](Assert-BudgetSyncContract -Data $budget)

Write-Host "OK: PG_BUDGET_SYNC.json validado com sucesso"
