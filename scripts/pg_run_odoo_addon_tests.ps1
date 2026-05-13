param(
  [string]$PythonExePath,

  [string]$OdooBinPath,

  [string]$ConfigPath,

  [string]$DatabaseName,

  [switch]$SkipUpgrade,

  [switch]$KeepDatabase
)

$ErrorActionPreference = "Stop"

function Resolve-TemplateRoot {
  return (Split-Path -Parent $PSScriptRoot)
}

function Get-DefaultIfExists {
  param([string]$Path)
  if ($Path -and (Test-Path $Path)) {
    return [System.IO.Path]::GetFullPath($Path)
  }
  return $null
}

function Get-IniValue {
  param(
    [string]$Path,
    [string]$Key
  )

  if (-not (Test-Path $Path)) {
    return $null
  }

  foreach ($line in Get-Content $Path) {
    if ($line -match "^\s*$([regex]::Escape($Key))\s*=\s*(.*)$") {
      return $Matches[1].Trim()
    }
  }
  return $null
}

function Resolve-ExecutablePath {
  param(
    [string]$ConfiguredPath,
    [string[]]$Candidates,
    [string]$Label
  )

  $resolved = Get-DefaultIfExists -Path $ConfiguredPath
  if ($resolved) {
    return $resolved
  }

  foreach ($candidate in $Candidates) {
    $resolved = Get-DefaultIfExists -Path $candidate
    if ($resolved) {
      return $resolved
    }
  }

  throw "$Label nao encontrado."
}

function Get-AddonsPaths {
  param([string]$OdooServerRoot, [string]$TemplateRoot)

  $paths = @()
  foreach ($candidate in @(
    (Join-Path $OdooServerRoot 'odoo\addons'),
    $TemplateRoot
  )) {
    if ((Test-Path $candidate) -and ($paths -notcontains $candidate)) {
      $paths += $candidate
    }
  }
  return $paths
}

function Invoke-OdooCommand {
  param(
    [string]$PythonExe,
    [string]$OdooBin,
    [string[]]$Arguments
  )

  Write-Host "RUN: $PythonExe $OdooBin $($Arguments -join ' ')"
  & $PythonExe $OdooBin @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "Falha ao executar testes do addon com codigo de saida $LASTEXITCODE."
  }
}

function Remove-TestDatabase {
  param(
    [string]$ConfigPathValue,
    [string]$DbName
  )

  $pgPath = Get-IniValue -Path $ConfigPathValue -Key 'pg_path'
  $dbHost = Get-IniValue -Path $ConfigPathValue -Key 'db_host'
  $dbPort = Get-IniValue -Path $ConfigPathValue -Key 'db_port'
  $dbUser = Get-IniValue -Path $ConfigPathValue -Key 'db_user'
  $dbPassword = Get-IniValue -Path $ConfigPathValue -Key 'db_password'

  $dropDbExe = $null
  if ($pgPath) {
    $dropDbExe = Get-DefaultIfExists -Path (Join-Path $pgPath 'dropdb.exe')
  }
  if (-not $dropDbExe) {
    $dropDbExe = Get-DefaultIfExists -Path 'dropdb'
  }
  if (-not $dropDbExe) {
    Write-Warning "Nao foi possivel localizar dropdb. A base de dados de teste foi mantida: $DbName"
    return
  }

  $env:PGPASSWORD = $dbPassword
  try {
    & $dropDbExe '--if-exists' '--host' $dbHost '--port' $dbPort '--username' $dbUser $DbName
    if ($LASTEXITCODE -ne 0) {
      Write-Warning "Falha ao remover a base de dados de teste: $DbName"
    } else {
      Write-Host "OK: base de dados de teste removida: $DbName"
    }
  }
  finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
  }
}

$templateRoot = Resolve-TemplateRoot

$defaultPython = 'C:\Program Files\Odoo 19.0e.20260206\python\python.exe'
$defaultOdooBin = 'C:\Program Files\Odoo 19.0e.20260206\server\odoo-bin'
$defaultConfig = 'C:\Program Files\Odoo 19.0e.20260206\server\odoo.conf'

$pythonExe = Resolve-ExecutablePath -ConfiguredPath $PythonExePath -Candidates @($defaultPython) -Label 'Python do Odoo'
$odooBin = Resolve-ExecutablePath -ConfiguredPath $OdooBinPath -Candidates @($defaultOdooBin) -Label 'odoo-bin'
$config = Resolve-ExecutablePath -ConfiguredPath $ConfigPath -Candidates @($defaultConfig) -Label 'odoo.conf'

$odooServerRoot = Split-Path -Parent $odooBin
$addonsPaths = Get-AddonsPaths -OdooServerRoot $odooServerRoot -TemplateRoot $templateRoot
$addonsPathValue = ($addonsPaths -join ',')

if (-not $DatabaseName) {
  $DatabaseName = 'pg_brodoo_test_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
}

$commonArgs = @(
  'server',
  '-c', $config,
  '-d', $DatabaseName,
  '--addons-path', $addonsPathValue,
  '--without-demo',
  '--test-enable',
  '--test-tags', '/pg_brodoo',
  '--no-http',
  '--max-cron-threads', '0',
  '--stop-after-init',
  '-i', 'pg_brodoo'
)

try {
  Invoke-OdooCommand -PythonExe $pythonExe -OdooBin $odooBin -Arguments $commonArgs

  if (-not $SkipUpgrade) {
    $upgradeArgs = @(
      'server',
      '-c', $config,
      '-d', $DatabaseName,
      '--addons-path', $addonsPathValue,
      '--without-demo',
      '--test-enable',
      '--test-tags', '/pg_brodoo',
      '--no-http',
      '--max-cron-threads', '0',
      '--stop-after-init',
      '-u', 'pg_brodoo'
    )
    Invoke-OdooCommand -PythonExe $pythonExe -OdooBin $odooBin -Arguments $upgradeArgs
  }

  Write-Host "OK: testes automatizados do addon concluidos com sucesso na base $DatabaseName"
}
finally {
  if (-not $KeepDatabase) {
    Remove-TestDatabase -ConfigPathValue $config -DbName $DatabaseName
  } else {
    Write-Host "WARN: base de dados de teste mantida: $DatabaseName"
  }
}
