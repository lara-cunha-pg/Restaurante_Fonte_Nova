param(
  [Parameter(Mandatory = $true)]
  [string]$RepoPath,

  [string]$RisksPath
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "pg_risks_sync_common.ps1")

$repo = [System.IO.Path]::GetFullPath($RepoPath)
if (-not (Test-Path $repo)) {
  throw "Repositorio nao encontrado: $repo"
}

$resolvedRisksPath = Resolve-ProjectRisksSyncPath -RepositoryPath $repo -ExplicitRisksPath $RisksPath
if (-not (Test-Path $resolvedRisksPath)) {
  throw "PG_RISKS_SYNC.json nao encontrado em $resolvedRisksPath"
}

$risks = Get-ProjectRisksSyncData -Path $resolvedRisksPath
[void](Assert-ProjectRisksSyncContract -Data $risks)

Write-Host "OK: PG_RISKS_SYNC.json validado com sucesso"
