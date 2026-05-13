param(
  [Parameter(Mandatory = $true)]
  [string]$RepoName,

  [string]$RepoPath,

  [string]$Series,

  [ValidateSet("auto", "community", "enterprise")]
  [string]$Edition = "auto",

  [switch]$CloneOdooSource,

  [switch]$SkipSmokeTest,

  [switch]$SkipGitInit,

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

function Test-GitAvailable {
  return [bool](Get-Command git -ErrorAction SilentlyContinue)
}

function Ensure-RepositoryDirectory {
  param([string]$Path)

  if (Test-Path $Path) {
    Write-Host "OK: diretorio do repositorio disponivel em $Path"
    return
  }

  New-Item -ItemType Directory -Path $Path | Out-Null
  Write-Host "OK: diretorio do repositorio criado em $Path"
}

function Initialize-GitRepositoryIfMissing {
  param([string]$Path)

  $gitPath = Join-Path $Path ".git"
  if (Test-Path $gitPath) {
    Write-Host "SKIP: repositorio Git ja inicializado em $Path"
    return
  }

  if (-not (Test-GitAvailable)) {
    Write-Host "WARN: Git nao encontrado; repositorio local nao sera inicializado automaticamente"
    return
  }

  & git -C $Path init -b main | Out-Null
  if ($LASTEXITCODE -ne 0) {
    & git -C $Path init | Out-Null
    if ($LASTEXITCODE -ne 0) {
      throw "Falha ao inicializar repositorio Git em $Path"
    }

    & git -C $Path checkout -b main | Out-Null
    if ($LASTEXITCODE -ne 0) {
      throw "Falha ao definir a branch main em $Path"
    }
  }

  Write-Host "OK: repositorio Git inicializado em $Path"
}

function Invoke-TemplateScript {
  param(
    [string]$ScriptName,
    [hashtable]$Parameters
  )

  $scriptPath = Join-Path $PSScriptRoot $ScriptName
  if (-not (Test-Path $scriptPath)) {
    throw "Script do template nao encontrado: $scriptPath"
  }

  & $scriptPath @Parameters
}

$templateRoot = Resolve-TemplateRoot
$repo = Resolve-TargetRepo -Name $RepoName -ExplicitPath $RepoPath -TemplateRoot $templateRoot

Ensure-RepositoryDirectory -Path $repo

if (-not $SkipGitInit) {
  Initialize-GitRepositoryIfMissing -Path $repo
}

Invoke-TemplateScript -ScriptName "pg_bootstrap_repo.ps1" -Parameters @{
  RepoName = $RepoName
  RepoPath = $repo
  Force = $Force.IsPresent
}

$sharedAssetParams = @{
  RepoName = $RepoName
  RepoPath = $repo
  Force = $Force.IsPresent
}

Invoke-TemplateScript -ScriptName "pg_sync_shared_assets.ps1" -Parameters $sharedAssetParams

$shouldCloneSource = (
  $CloneOdooSource.IsPresent -or
  $PSBoundParameters.ContainsKey("Series") -or
  ($PSBoundParameters.ContainsKey("Edition") -and $Edition -ne "auto")
)

if ($shouldCloneSource) {
  $cloneParams = @{
    RepoName = $RepoName
    RepoPath = $repo
    Edition = $Edition
  }

  if ($Series) {
    $cloneParams["Series"] = $Series
  }

  Invoke-TemplateScript -ScriptName "pg_clone_odoo_source.ps1" -Parameters $cloneParams
}

if (-not $SkipSmokeTest) {
  $smokeParams = @{
    RepoPath = $repo
  }

  if ($shouldCloneSource) {
    $smokeParams["RequireOdooSource"] = $true
  }

  Invoke-TemplateScript -ScriptName "pg_smoke_test_repo.ps1" -Parameters $smokeParams
}

Write-Host "OK: bootstrap assistido concluido para $repo"
