param(
  [Parameter(Mandatory = $true)]
  [string]$RepoPath,

  [string]$DecisionsPath
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "pg_decisions_sync_common.ps1")

$repo = [System.IO.Path]::GetFullPath($RepoPath)
if (-not (Test-Path $repo)) {
  throw "Repositorio nao encontrado: $repo"
}

$resolvedDecisionsPath = Resolve-ProjectDecisionsSyncPath -RepositoryPath $repo -ExplicitDecisionsPath $DecisionsPath
if (-not (Test-Path $resolvedDecisionsPath)) {
  throw "PG_DECISIONS_SYNC.json nao encontrado em $resolvedDecisionsPath"
}

$decisions = Get-ProjectDecisionsSyncData -Path $resolvedDecisionsPath
[void](Assert-ProjectDecisionsSyncContract -Data $decisions)

Write-Host "OK: PG_DECISIONS_SYNC.json validado com sucesso"
