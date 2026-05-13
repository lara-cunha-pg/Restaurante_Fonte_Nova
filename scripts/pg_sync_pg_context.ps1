param(
  [Parameter(Mandatory = $true)]
  [string]$RepoPath,

  [string]$CommunityPath,

  [string]$EnterprisePath,

  [ValidateSet("community", "enterprise")]
  [string]$EditionHint
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "pg_file_io_common.ps1")

function Resolve-CommunityPath {
  param(
    [string]$RepositoryPath,
    [string]$ExplicitCommunityPath
  )

  if ($ExplicitCommunityPath) {
    return [System.IO.Path]::GetFullPath($ExplicitCommunityPath)
  }

  $repo = [System.IO.Path]::GetFullPath($RepositoryPath)
  $sourceClone = Join-Path $repo "vendor\odoo_src\community"
  if (Test-Path $sourceClone) {
    return $sourceClone
  }

  return Join-Path $repo "vendor\odoo_core"
}

function Resolve-EnterprisePath {
  param(
    [string]$RepositoryPath,
    [string]$ExplicitEnterprisePath
  )

  if ($ExplicitEnterprisePath) {
    return [System.IO.Path]::GetFullPath($ExplicitEnterprisePath)
  }

  $candidate = Join-Path ([System.IO.Path]::GetFullPath($RepositoryPath)) "vendor\odoo_src\enterprise"
  if (Test-Path $candidate) {
    return $candidate
  }

  return $null
}

function Get-OdooReleaseMetadata {
  param(
    [string]$CommunitySourcePath,
    [string]$EnterpriseSourcePath,
    [string]$EditionHint
  )

  $releasePath = Join-Path $CommunitySourcePath "odoo\release.py"
  if (-not (Test-Path $releasePath)) {
    throw "release.py nao encontrado em $releasePath"
  }

  $content = Read-Utf8TextFile -Path $releasePath
  $versionMatch = [regex]::Match($content, "version_info\s*=\s*\(\s*(\d+)\s*,\s*(\d+)")
  if (-not $versionMatch.Success) {
    throw "Nao foi possivel detetar a versao do Odoo em $releasePath"
  }

  $series = "{0}.{1}" -f $versionMatch.Groups[1].Value, $versionMatch.Groups[2].Value
  $edition = $null
  $editionEvidence = @()
  if ($EditionHint -eq "enterprise") {
    $editionEvidence += "hint explicito de edicao enterprise"
    $edition = "Enterprise"
  } elseif ($EditionHint -eq "community") {
    $editionEvidence += "hint explicito de edicao community"
    $edition = "Community"
  } elseif ($content -match "\+e(?:[-']|$)") {
    $editionEvidence += "release.py contem marcador +e"
    $edition = "Enterprise"
  } elseif ($content -match "repos_heads\s*=\s*\{[^}]*'enterprise'\s*:") {
    $editionEvidence += "release.py referencia repositorio enterprise"
    $edition = "Enterprise"
  } elseif ($EnterpriseSourcePath -and (Test-Path $EnterpriseSourcePath)) {
    $editionEvidence += "existe checkout enterprise em vendor/odoo_src/enterprise"
    $edition = "Enterprise"
  }

  return @{
    Series = $series
    Edition = $edition
    ReleasePath = $releasePath
    EditionEvidence = $editionEvidence
  }
}

function Set-LabeledValue {
  param(
    [string]$Text,
    [string]$Label,
    [string]$Value
  )

  $pattern = "(?m)^" + [regex]::Escape($Label) + ".*$"
  if ([regex]::IsMatch($Text, $pattern)) {
    return [regex]::Replace($Text, $pattern, $Label + " " + $Value)
  }

  return $Text
}

function Ensure-LabeledValue {
  param(
    [string]$Text,
    [string]$Label,
    [string]$Value,
    [string]$InsertAfterLabel
  )

  $pattern = "(?m)^" + [regex]::Escape($Label) + ".*$"
  if ([regex]::IsMatch($Text, $pattern)) {
    return [regex]::Replace($Text, $pattern, $Label + " " + $Value)
  }

  if ($InsertAfterLabel) {
    $anchorPattern = "(?m)^" + [regex]::Escape($InsertAfterLabel) + ".*$"
    $match = [regex]::Match($Text, $anchorPattern)
    if ($match.Success) {
      return $Text.Insert($match.Index + $match.Length, [Environment]::NewLine + $Label + " " + $Value)
    }
  }

  return $Text + [Environment]::NewLine + $Label + " " + $Value
}

function Get-LabeledValue {
  param(
    [string]$Text,
    [string]$Label
  )

  $pattern = "(?m)^" + [regex]::Escape($Label) + "\s*(.*)$"
  $match = [regex]::Match($Text, $pattern)
  if ($match.Success) {
    return $match.Groups[1].Value.Trim()
  }

  return $null
}

$repoPath = [System.IO.Path]::GetFullPath($RepoPath)
if (-not (Test-Path $repoPath)) {
  throw "Repositorio nao encontrado: $repoPath"
}

$contextPath = Join-Path $repoPath "PG_CONTEXT.md"
if (-not (Test-Path $contextPath)) {
  throw "PG_CONTEXT.md nao encontrado em $contextPath"
}

$resolvedCommunityPath = Resolve-CommunityPath -RepositoryPath $repoPath -ExplicitCommunityPath $CommunityPath
if (-not (Test-Path $resolvedCommunityPath)) {
  throw "Source Community do Odoo nao encontrado em $resolvedCommunityPath"
}

$resolvedEnterprisePath = Resolve-EnterprisePath -RepositoryPath $repoPath -ExplicitEnterprisePath $EnterprisePath
$metadata = Get-OdooReleaseMetadata -CommunitySourcePath $resolvedCommunityPath -EnterpriseSourcePath $resolvedEnterprisePath -EditionHint $EditionHint
$docsBase = "https://www.odoo.com/documentation/$($metadata.Series)/"
$studioDocs = $docsBase + "applications/studio.html"
$developerDocs = $docsBase + "developer/reference.html"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"

$context = Read-Utf8TextFile -Path $contextPath
$context = Set-LabeledValue -Text $context -Label "Versao do Odoo:" -Value $metadata.Series
$context = Ensure-LabeledValue -Text $context -Label "Path do core:" -Value $resolvedCommunityPath -InsertAfterLabel "Ambiente:"
$context = Ensure-LabeledValue -Text $context -Label "Path source Enterprise:" -Value $(if ($resolvedEnterprisePath) { $resolvedEnterprisePath } else { "[NAO CONFIGURADO]" }) -InsertAfterLabel "Path do core:"
$context = Set-LabeledValue -Text $context -Label "Documentacao oficial base:" -Value $docsBase
$context = Set-LabeledValue -Text $context -Label "Documentacao Studio:" -Value $studioDocs
$context = Set-LabeledValue -Text $context -Label "Documentacao Developer:" -Value $developerDocs
$context = Set-LabeledValue -Text $context -Label "Ultima sincronizacao automatica:" -Value $timestamp

if ($metadata.Edition) {
  $context = Set-LabeledValue -Text $context -Label "Edicao:" -Value $metadata.Edition
} else {
  $currentEdition = Get-LabeledValue -Text $context -Label "Edicao:"
  if (-not $currentEdition) {
    $context = Set-LabeledValue -Text $context -Label "Edicao:" -Value "[PONTO POR VALIDAR]"
  }
}

Write-Utf8NoBomFile -Path $contextPath -Content $context

Write-Host "OK: PG_CONTEXT.md atualizado com metadados do source Odoo"
Write-Host "  Versao: $($metadata.Series)"
Write-Host "  Community: $resolvedCommunityPath"
if ($resolvedEnterprisePath) {
  Write-Host "  Enterprise: $resolvedEnterprisePath"
}
Write-Host "  Docs: $docsBase"
if ($metadata.Edition) {
  Write-Host "  Edicao: $($metadata.Edition)"
} else {
  Write-Host "  Edicao: mantida sem conclusao automatica"
}
