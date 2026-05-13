param(
  [Parameter(Mandatory = $true)]
  [string]$RepoPath,

  [switch]$SkipIntakeFallback
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "pg_file_io_common.ps1")

function Get-JsonDataOrNull {
  param([string]$Path)

  try {
    return (Read-Utf8JsonFile -Path $Path)
  } catch {
    return $null
  }
}

function Test-ScopeSnapshotReady {
  param([string]$Path)

  if (-not (Test-Path $Path)) {
    return $false
  }

  $data = Get-JsonDataOrNull -Path $Path
  if (-not $data) {
    return $false
  }

  return (
    -not [string]::IsNullOrWhiteSpace([string]$data.project_name) -and
    $data.source_metadata -and
    -not [string]::IsNullOrWhiteSpace([string]$data.source_metadata.sync_published_at) -and
    -not [string]::IsNullOrWhiteSpace([string]$data.source_metadata.payload_hash)
  )
}

function Test-StatusSnapshotReady {
  param([string]$Path)

  if (-not (Test-Path $Path)) {
    return $false
  }

  $data = Get-JsonDataOrNull -Path $Path
  if (-not $data) {
    return $false
  }

  return (
    -not [string]::IsNullOrWhiteSpace([string]$data.project_name) -and
    -not [string]::IsNullOrWhiteSpace([string]$data.sync_published_at)
  )
}

$repo = [System.IO.Path]::GetFullPath($RepoPath)
if (-not (Test-Path $repo)) {
  throw "Repositorio nao encontrado: $repo"
}

$scopePath = Join-Path $repo ".pg\PG_SCOPE_SYNC.json"
$statusPath = Join-Path $repo ".pg\PG_PROJECT_STATUS_SYNC.json"
$intakePath = Join-Path $repo "PG_SCOPE_INTAKE.yaml"

if (Test-ScopeSnapshotReady -Path $scopePath) {
  & (Join-Path $PSScriptRoot "pg_validate_scope_sync.ps1") -RepoPath $repo -ScopePath $scopePath
  & (Join-Path $PSScriptRoot "pg_apply_scope_sync.ps1") -RepoPath $repo -ScopePath $scopePath
} elseif ((-not $SkipIntakeFallback) -and (Test-Path $intakePath)) {
  & (Join-Path $PSScriptRoot "pg_build_pg_context.ps1") -RepoPath $repo -IntakePath $intakePath
}

if (Test-StatusSnapshotReady -Path $statusPath) {
  & (Join-Path $PSScriptRoot "pg_validate_project_status_sync.ps1") -RepoPath $repo -StatusPath $statusPath
  & (Join-Path $PSScriptRoot "pg_apply_project_status_sync.ps1") -RepoPath $repo -StatusPath $statusPath
}

Write-Host "OK: refresh do PG_CONTEXT.md concluido"
