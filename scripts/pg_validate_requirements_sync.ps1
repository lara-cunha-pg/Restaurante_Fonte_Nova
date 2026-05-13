param(
  [Parameter(Mandatory = $true)]
  [string]$RepoPath,

  [string]$RequirementsPath
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "pg_requirements_sync_common.ps1")

$repo = [System.IO.Path]::GetFullPath($RepoPath)
if (-not (Test-Path $repo)) {
  throw "Repositorio nao encontrado: $repo"
}

$resolvedRequirementsPath = Resolve-ProjectRequirementsSyncPath -RepositoryPath $repo -ExplicitRequirementsPath $RequirementsPath
if (-not (Test-Path $resolvedRequirementsPath)) {
  throw "PG_REQUIREMENTS_SYNC.json nao encontrado em $resolvedRequirementsPath"
}

$requirements = Get-ProjectRequirementsSyncData -Path $resolvedRequirementsPath
[void](Assert-ProjectRequirementsSyncContract -Data $requirements)

Write-Host "OK: PG_REQUIREMENTS_SYNC.json validado com sucesso"
