param(
  [Parameter(Mandatory = $true)]
  [string]$RepoPath,

  [string]$DeliveriesPath
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "pg_deliveries_sync_common.ps1")

$repo = [System.IO.Path]::GetFullPath($RepoPath)
if (-not (Test-Path $repo)) {
  throw "Repositorio nao encontrado: $repo"
}

$resolvedDeliveriesPath = Resolve-ProjectDeliveriesSyncPath -RepositoryPath $repo -ExplicitDeliveriesPath $DeliveriesPath
if (-not (Test-Path $resolvedDeliveriesPath)) {
  throw "PG_DELIVERIES_SYNC.json nao encontrado em $resolvedDeliveriesPath"
}

$deliveries = Get-ProjectDeliveriesSyncData -Path $resolvedDeliveriesPath
[void](Assert-ProjectDeliveriesSyncContract -Data $deliveries)

Write-Host "OK: PG_DELIVERIES_SYNC.json validado com sucesso"
