param(
  [Parameter(Mandatory = $true)]
  [string]$RepoPath,

  [string]$ScopePath
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "pg_scope_sync_common.ps1")

$repo = [System.IO.Path]::GetFullPath($RepoPath)
if (-not (Test-Path $repo)) {
  throw "Repositorio nao encontrado: $repo"
}

$resolvedScopePath = Resolve-ProjectScopeSyncPath -RepositoryPath $repo -ExplicitScopePath $ScopePath
if (-not (Test-Path $resolvedScopePath)) {
  throw "PG_SCOPE_SYNC.json nao encontrado em $resolvedScopePath"
}

$scope = Get-ProjectScopeSyncData -Path $resolvedScopePath
[void](Assert-ProjectScopeSyncContract -Data $scope)

Write-Host "OK: PG_SCOPE_SYNC.json validado com sucesso"
