param(
  [Parameter(Mandatory = $true)]
  [string]$RepoPath,

  [string]$StatusPath
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "pg_project_status_sync_common.ps1")

$repo = [System.IO.Path]::GetFullPath($RepoPath)
if (-not (Test-Path $repo)) {
  throw "Repositorio nao encontrado: $repo"
}

$resolvedStatusPath = Resolve-ProjectStatusSyncPath -RepositoryPath $repo -ExplicitStatusPath $StatusPath
if (-not (Test-Path $resolvedStatusPath)) {
  throw "PG_PROJECT_STATUS_SYNC.json nao encontrado em $resolvedStatusPath"
}

$status = Get-ProjectStatusSyncData -Path $resolvedStatusPath
[void](Assert-ProjectStatusSyncContract -Data $status)

Write-Host "OK: PG_PROJECT_STATUS_SYNC.json validado com sucesso"
