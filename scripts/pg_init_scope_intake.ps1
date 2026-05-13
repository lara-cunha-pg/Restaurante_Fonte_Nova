param(
  [Parameter(Mandatory = $true)]
  [string]$RepoPath,

  [string]$ProjectName,

  [string]$ClientUnit,

  [string]$RepositorySummary,

  [string]$ProjectPhase,

  [switch]$Force
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "pg_file_io_common.ps1")

function Resolve-TemplateRoot {
  return (Split-Path -Parent $PSScriptRoot)
}

function Set-YamlScalarValue {
  param(
    [string]$Text,
    [string]$Key,
    [string]$Value
  )

  $pattern = "(?m)^" + [regex]::Escape($Key) + ":\s*.*$"
  $replacement = $Key + ": " + $Value

  if ([regex]::IsMatch($Text, $pattern)) {
    return [regex]::Replace($Text, $pattern, $replacement)
  }

  return $Text
}

function Get-YamlScalarValue {
  param(
    [string]$Text,
    [string]$Key
  )

  $pattern = "(?m)^" + [regex]::Escape($Key) + ":\s*(.*)$"
  $match = [regex]::Match($Text, $pattern)
  if ($match.Success) {
    return $match.Groups[1].Value.Trim()
  }

  return $null
}

$templateRoot = Resolve-TemplateRoot
$repo = [System.IO.Path]::GetFullPath($RepoPath)
if (-not (Test-Path $repo)) {
  throw "Repositorio nao encontrado: $repo"
}

$templatePath = Join-Path $templateRoot "templates\PG_SCOPE_INTAKE.yaml"
$targetPath = Join-Path $repo "PG_SCOPE_INTAKE.yaml"

if ((-not (Test-Path $targetPath)) -or $Force) {
  Copy-Item -Path $templatePath -Destination $targetPath -Force:$Force
}

$projectFolderName = Split-Path -Leaf $repo
$content = Read-Utf8TextFile -Path $targetPath
$currentProjectName = Get-YamlScalarValue -Text $content -Key "project_name"

if ($ProjectName) {
  $content = Set-YamlScalarValue -Text $content -Key "project_name" -Value $ProjectName
} elseif (($currentProjectName -eq "[PREENCHER]") -or (-not $currentProjectName)) {
  $content = Set-YamlScalarValue -Text $content -Key "project_name" -Value $projectFolderName
}

if ($ClientUnit) {
  $content = Set-YamlScalarValue -Text $content -Key "client_unit" -Value $ClientUnit
}

if ($RepositorySummary) {
  $content = Set-YamlScalarValue -Text $content -Key "repository_summary" -Value $RepositorySummary
}

if ($ProjectPhase) {
  $content = Set-YamlScalarValue -Text $content -Key "project_phase" -Value $ProjectPhase
}

Write-Utf8NoBomFile -Path $targetPath -Content $content

Write-Host "OK: PG_SCOPE_INTAKE.yaml inicializado em $targetPath"
