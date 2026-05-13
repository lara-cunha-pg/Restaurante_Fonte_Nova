param(
  [Parameter(Mandatory = $true)]
  [string]$RepoName,

  [string]$CoreSelector,

  [string]$RepoPath
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

$templateRoot = Resolve-TemplateRoot
$repo = Resolve-TargetRepo -Name $RepoName -ExplicitPath $RepoPath -TemplateRoot $templateRoot

if (-not (Test-Path $repo)) {
  throw "Repositorio nao encontrado: $repo"
}

$series = $null
$edition = "auto"

if ($CoreSelector) {
  if ($CoreSelector -match "^(?<major>\d+)(?:\.(?<minor>\d+))?(?<edition>[ce])?$") {
    $minor = if ($Matches["minor"]) { $Matches["minor"] } else { "0" }
    $series = "{0}.{1}" -f $Matches["major"], $minor

    if ($Matches["edition"] -eq "e") {
      $edition = "enterprise"
    }

    if ($Matches["edition"] -eq "c") {
      $edition = "community"
    }
  } elseif (Test-Path $CoreSelector) {
    Write-Warning "pg_link_odoo_core.ps1 esta obsoleto. Foi feita apenas a sincronizacao do contexto com o path indicado, sem criar ligacao em vendor/."
    & (Join-Path $PSScriptRoot "pg_sync_pg_context.ps1") -RepoPath $repo -CommunityPath $CoreSelector
    return
  } else {
    throw "CoreSelector legacy invalido. Usa, por exemplo, 19.0, 19e, 19c ou migra para scripts\\pg_clone_odoo_source.ps1."
  }
}

Write-Warning "pg_link_odoo_core.ps1 esta obsoleto. Usa scripts\\pg_clone_odoo_source.ps1. A executar fluxo novo baseado em git clone."
& (Join-Path $PSScriptRoot "pg_clone_odoo_source.ps1") -RepoName $RepoName -RepoPath $RepoPath -Series $series -Edition $edition
