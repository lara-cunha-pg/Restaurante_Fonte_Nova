param(
  [Parameter(Mandatory = $true, Position = 0)]
  [string]$RepoName,

  [Parameter(Position = 1)]
  [string]$Series,

  [Parameter(Position = 2)]
  [ValidateSet("auto", "community", "enterprise")]
  [string]$Edition = "auto",

  [string]$RepoPath,

  [string]$GlobalSourceRoot,

  [switch]$ForceRelink,

  [string]$CommunityRemoteUrl = "https://github.com/odoo/odoo.git",

  [string]$EnterpriseRemoteUrl = "https://github.com/odoo/enterprise.git"
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "pg_file_io_common.ps1")

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

function Test-WindowsPlatform {
  $isWindowsVariable = Get-Variable -Name IsWindows -ErrorAction SilentlyContinue
  if ($isWindowsVariable) {
    return [bool]$isWindowsVariable.Value
  }

  return [System.Environment]::OSVersion.Platform -eq [System.PlatformID]::Win32NT
}

function Resolve-GlobalSourceRootPath {
  param([string]$ExplicitRoot)

  if (-not [string]::IsNullOrWhiteSpace($ExplicitRoot)) {
    return [System.IO.Path]::GetFullPath($ExplicitRoot)
  }

  if (-not [string]::IsNullOrWhiteSpace($env:PG_ODOO_SOURCE_ROOT)) {
    return [System.IO.Path]::GetFullPath($env:PG_ODOO_SOURCE_ROOT)
  }

  return Join-Path $HOME ".pg\odoo_src"
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

function Get-SeriesInfo {
  param([string]$Value)

  if ([string]::IsNullOrWhiteSpace($Value)) {
    return $null
  }

  $trimmed = $Value.Trim()

  if ($trimmed -match "^(?<major>\d+)\.(?<minor>\d+)$") {
    return [pscustomobject]@{
      Series = "{0}.{1}" -f $Matches["major"], $Matches["minor"]
      TokenEdition = $null
    }
  }

  if ($trimmed -match "^(?<major>\d+)(?<edition>[ce])$") {
    return [pscustomobject]@{
      Series = "{0}.0" -f $Matches["major"]
      TokenEdition = if ($Matches["edition"] -eq "e") { "enterprise" } else { "community" }
    }
  }

  if ($trimmed -match "^(?<major>\d+)$") {
    return [pscustomobject]@{
      Series = "{0}.0" -f $Matches["major"]
      TokenEdition = $null
    }
  }

  throw "Serie Odoo invalida: $Value. Exemplos validos: 19.0, 19e, 19c."
}

function Get-SeriesFromContext {
  param([string]$RepositoryPath)

  $contextPath = Join-Path $RepositoryPath "PG_CONTEXT.md"
  if (-not (Test-Path $contextPath)) {
    return $null
  }

  $content = Read-Utf8TextFile -Path $contextPath
  $value = Get-LabeledValue -Text $content -Label "Versao do Odoo:"
  if (-not $value) {
    return $null
  }

  try {
    return Get-SeriesInfo -Value $value
  } catch {
    return $null
  }
}

function Get-EditionFromContext {
  param([string]$RepositoryPath)

  $contextPath = Join-Path $RepositoryPath "PG_CONTEXT.md"
  if (-not (Test-Path $contextPath)) {
    return $null
  }

  $content = Read-Utf8TextFile -Path $contextPath
  $value = Get-LabeledValue -Text $content -Label "Edicao:"
  if (-not $value) {
    return $null
  }

  $normalized = $value.Trim().ToLowerInvariant()
  if ($normalized -eq "community") {
    return "community"
  }

  if ($normalized -eq "enterprise") {
    return "enterprise"
  }

  return $null
}

function Resolve-RequestedSeries {
  param(
    [string]$ExplicitSeries,
    [string]$RepositoryPath
  )

  $explicitInfo = Get-SeriesInfo -Value $ExplicitSeries
  if ($explicitInfo) {
    return $explicitInfo
  }

  $contextInfo = Get-SeriesFromContext -RepositoryPath $RepositoryPath
  if ($contextInfo) {
    return $contextInfo
  }

  throw "Nao foi possivel determinar a serie do Odoo. Indica a serie explicitamente, por exemplo: 19.0 ou 19e."
}

function Resolve-RequestedEdition {
  param(
    [string]$ExplicitEdition,
    [string]$RepositoryPath,
    [string]$TokenEdition
  )

  if ($ExplicitEdition -and $ExplicitEdition -ne "auto") {
    return $ExplicitEdition
  }

  if ($TokenEdition) {
    return $TokenEdition
  }

  $contextEdition = Get-EditionFromContext -RepositoryPath $RepositoryPath
  if ($contextEdition) {
    return $contextEdition
  }

  return "community"
}

function Invoke-Git {
  param([string[]]$Arguments)

  & git @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "Falha ao executar git $($Arguments -join ' ')"
  }
}

function Test-GitWorktreeClean {
  param([string]$Path)

  $status = & git -C $Path status --porcelain
  if ($LASTEXITCODE -ne 0) {
    throw "Nao foi possivel verificar o estado Git em $Path"
  }

  return [string]::IsNullOrWhiteSpace(($status -join [Environment]::NewLine))
}

function Ensure-Directory {
  param([string]$Path)

  if (-not (Test-Path $Path)) {
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
  }
}

function Test-ReparsePoint {
  param([string]$Path)

  if (-not (Test-Path $Path)) {
    return $false
  }

  $item = Get-Item -LiteralPath $Path -Force
  return (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)
}

function Assert-PathInsideRoot {
  param(
    [string]$Path,
    [string]$Root,
    [string]$Label
  )

  $fullPath = [System.IO.Path]::GetFullPath($Path)
  $fullRoot = [System.IO.Path]::GetFullPath($Root)
  $normalizedRoot = $fullRoot.TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar

  if (-not ($fullPath.StartsWith($normalizedRoot, [System.StringComparison]::OrdinalIgnoreCase) -or
      $fullPath.Equals($fullRoot, [System.StringComparison]::OrdinalIgnoreCase))) {
    throw "$Label fora da raiz esperada. Path: $fullPath ; Root: $fullRoot"
  }
}

function New-JunctionLink {
  param(
    [string]$LinkPath,
    [string]$TargetPath
  )

  if (Test-WindowsPlatform) {
    try {
      New-Item -ItemType Junction -Path $LinkPath -Target $TargetPath | Out-Null
      return
    } catch {
      $escapedLink = '"' + $LinkPath + '"'
      $escapedTarget = '"' + $TargetPath + '"'
      cmd /c "mklink /J $escapedLink $escapedTarget" | Out-Null
      if ($LASTEXITCODE -ne 0) {
        throw "Falha ao criar junction $LinkPath -> $TargetPath"
      }
    }
  } else {
    New-Item -ItemType SymbolicLink -Path $LinkPath -Target $TargetPath | Out-Null
  }
}

function Ensure-RepoSourceLink {
  param(
    [string]$RepositoryPath,
    [string]$LinkPath,
    [string]$TargetPath,
    [switch]$AllowReplace
  )

  $repoFullPath = [System.IO.Path]::GetFullPath($RepositoryPath)
  $linkFullPath = [System.IO.Path]::GetFullPath($LinkPath)
  $targetFullPath = [System.IO.Path]::GetFullPath($TargetPath)

  Assert-PathInsideRoot -Path $linkFullPath -Root $repoFullPath -Label "Link de source Odoo"
  Ensure-Directory -Path (Split-Path -Parent $linkFullPath)

  if (Test-Path $linkFullPath) {
    if (Test-ReparsePoint -Path $linkFullPath) {
      Remove-Item -LiteralPath $linkFullPath -Force
      Write-Host "OK: link anterior removido em $linkFullPath"
    } else {
      if (-not $AllowReplace) {
        throw "Ja existe uma pasta local em $linkFullPath. Usa -ForceRelink para substituir pela ligacao global."
      }

      Remove-Item -LiteralPath $linkFullPath -Recurse -Force
      Write-Host "OK: pasta local removida em $linkFullPath para adotar source global"
    }
  }

  New-JunctionLink -LinkPath $linkFullPath -TargetPath $targetFullPath
  Write-Host "OK: link de source criado $linkFullPath -> $targetFullPath"
}

function Sync-GitClone {
  param(
    [string]$RemoteUrl,
    [string]$Branch,
    [string]$DestinationPath
  )

  $parentPath = Split-Path -Parent $DestinationPath
  if (-not (Test-Path $parentPath)) {
    New-Item -ItemType Directory -Path $parentPath | Out-Null
  }

  if (Test-Path $DestinationPath) {
    if (-not (Test-Path (Join-Path $DestinationPath ".git"))) {
      throw "O destino ja existe mas nao e um repositorio Git: $DestinationPath"
    }

    if (-not (Test-GitWorktreeClean -Path $DestinationPath)) {
      throw "O checkout Odoo em $DestinationPath tem alteracoes locais. Limpa-o antes de atualizar."
    }

    Invoke-Git -Arguments @("-C", $DestinationPath, "remote", "set-url", "origin", $RemoteUrl)
    Invoke-Git -Arguments @("-C", $DestinationPath, "fetch", "origin", $Branch, "--depth", "1")
    Invoke-Git -Arguments @("-C", $DestinationPath, "checkout", "-B", $Branch, "origin/$Branch")
    Write-Host "OK: checkout atualizado em $DestinationPath ($Branch)"
    return
  }

  Invoke-Git -Arguments @("clone", "--branch", $Branch, "--single-branch", $RemoteUrl, $DestinationPath)
  Write-Host "OK: clone criado em $DestinationPath ($Branch)"
}

$templateRoot = Resolve-TemplateRoot
$repo = Resolve-TargetRepo -Name $RepoName -ExplicitPath $RepoPath -TemplateRoot $templateRoot

if (-not (Test-Path $repo)) {
  throw "Repositorio nao encontrado: $repo"
}

if (-not (Test-GitAvailable)) {
  throw "Git nao encontrado no PATH. Instala Git antes de clonar o source do Odoo."
}

$seriesInfo = Resolve-RequestedSeries -ExplicitSeries $Series -RepositoryPath $repo
$effectiveEdition = Resolve-RequestedEdition -ExplicitEdition $Edition -RepositoryPath $repo -TokenEdition $seriesInfo.TokenEdition

$globalSourceRoot = Resolve-GlobalSourceRootPath -ExplicitRoot $GlobalSourceRoot
$globalSeriesRoot = Join-Path $globalSourceRoot $seriesInfo.Series
Ensure-Directory -Path $globalSeriesRoot

$communityPath = Join-Path $globalSeriesRoot "community"
$enterprisePath = Join-Path $globalSeriesRoot "enterprise"

Sync-GitClone -RemoteUrl $CommunityRemoteUrl -Branch $seriesInfo.Series -DestinationPath $communityPath

if ($effectiveEdition -eq "enterprise") {
  try {
    Sync-GitClone -RemoteUrl $EnterpriseRemoteUrl -Branch $seriesInfo.Series -DestinationPath $enterprisePath
  } catch {
    throw "Falha ao obter o source Enterprise. Confirma acesso ao repositorio oficial do Odoo e autenticacao Git. Erro original: $($_.Exception.Message)"
  }
}

$repoSourceLink = Join-Path $repo "vendor\odoo_src"
Ensure-RepoSourceLink -RepositoryPath $repo -LinkPath $repoSourceLink -TargetPath $globalSeriesRoot -AllowReplace:$ForceRelink.IsPresent

$syncScript = Join-Path $PSScriptRoot "pg_sync_pg_context.ps1"
& $syncScript -RepoPath $repo -CommunityPath $communityPath -EnterprisePath $(if ($effectiveEdition -eq "enterprise") { $enterprisePath } else { $null }) -EditionHint $effectiveEdition

Write-Host "OK: source global ativo em $globalSeriesRoot"
