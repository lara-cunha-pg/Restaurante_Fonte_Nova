param(
  [Parameter(Mandatory = $true)]
  [string]$RepoPath,

  [string]$IntakePath
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "pg_file_io_common.ps1")

function Resolve-DefaultIntakePath {
  param(
    [string]$RepositoryPath,
    [string]$ExplicitIntakePath
  )

  if ($ExplicitIntakePath) {
    return [System.IO.Path]::GetFullPath($ExplicitIntakePath)
  }

  return Join-Path ([System.IO.Path]::GetFullPath($RepositoryPath)) "PG_SCOPE_INTAKE.yaml"
}

function Get-FlatYamlData {
  param([string]$Path)

  $data = @{}
  $currentListKey = $null

  foreach ($rawLine in Read-Utf8Lines -Path $Path) {
    $line = $rawLine.TrimEnd()

    if ([string]::IsNullOrWhiteSpace($line)) {
      continue
    }

    if ($line.TrimStart().StartsWith("#")) {
      continue
    }

    $keyMatch = [regex]::Match($line, "^([A-Za-z0-9_]+):\s*(.*)$")
    if ($keyMatch.Success) {
      $key = $keyMatch.Groups[1].Value
      $value = $keyMatch.Groups[2].Value.Trim()

      if ($value.Length -eq 0) {
        $data[$key] = @()
        $currentListKey = $key
      } else {
        $data[$key] = $value.Trim("'`"")
        $currentListKey = $null
      }

      continue
    }

    $listMatch = [regex]::Match($line, "^\s*-\s*(.*)$")
    if ($listMatch.Success -and $currentListKey) {
      $currentValue = @($data[$currentListKey])
      $currentValue += $listMatch.Groups[1].Value.Trim().Trim("'`"")
      $data[$currentListKey] = $currentValue
    }
  }

  return $data
}

function Get-ScalarValue {
  param(
    [hashtable]$Data,
    [string]$Key,
    [string]$Fallback = "[PONTO POR VALIDAR]",
    [int]$MaxChars = 0,
    [switch]$StripEmailNoise
  )

  if ($Data.ContainsKey($Key)) {
    $value = $Data[$Key]
    if ($value -isnot [System.Array] -and -not [string]::IsNullOrWhiteSpace($value)) {
      if ($StripEmailNoise) {
        return (Normalize-PgText -Text ((Get-PgSanitizedLines -Items @([string]$value) -StripEmailNoise -DropPlaceholders -MaxItems 1 -MaxChars $MaxChars) -join ' ') -Fallback $Fallback -MaxChars $MaxChars)
      }
      return (Normalize-PgText -Text ([string]$value) -Fallback $Fallback -MaxChars $MaxChars -DropPlaceholders)
    }
  }

  return $Fallback
}

function Get-ListValue {
  param(
    [hashtable]$Data,
    [string]$Key,
    [string]$Fallback = "[PREENCHER]",
    [int]$MaxItems = 0,
    [int]$MaxChars = 0,
    [switch]$StripEmailNoise
  )

  if ($Data.ContainsKey($Key)) {
    $value = $Data[$Key]
    if ($value -is [System.Array]) {
      $items = @(Get-PgSanitizedLines -Items @($value) -StripEmailNoise:$StripEmailNoise -DropPlaceholders -MaxItems $MaxItems -MaxChars $MaxChars)
      if ($items.Count -gt 0) {
        return $items
      }
    }
  }

  return @($Fallback)
}

function Convert-ToBulletLines {
  param([string[]]$Items)

  return (Convert-ToPgBulletLines -Items $Items -MaxChars 220)
}

function Replace-MarkedBlock {
  param(
    [string]$Text,
    [string]$Marker,
    [string]$BlockContent
  )

  $start = "<!-- PG_AUTO:$Marker`:START -->"
  $end = "<!-- PG_AUTO:$Marker`:END -->"
  $pattern = "(?s)" + [regex]::Escape($start) + ".*?" + [regex]::Escape($end)
  $replacement = $start + "`r`n" + $BlockContent.TrimEnd() + "`r`n" + $end

  if (-not [regex]::IsMatch($Text, $pattern)) {
    throw "Marcadores nao encontrados para $Marker"
  }

  return [regex]::Replace($Text, $pattern, [System.Text.RegularExpressions.MatchEvaluator]{ param($match) $replacement })
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

$repo = [System.IO.Path]::GetFullPath($RepoPath)
if (-not (Test-Path $repo)) {
  throw "Repositorio nao encontrado: $repo"
}

$contextPath = Join-Path $repo "PG_CONTEXT.md"
if (-not (Test-Path $contextPath)) {
  throw "PG_CONTEXT.md nao encontrado em $contextPath"
}

$resolvedIntakePath = Resolve-DefaultIntakePath -RepositoryPath $repo -ExplicitIntakePath $IntakePath
if (-not (Test-Path $resolvedIntakePath)) {
  throw "PG_SCOPE_INTAKE.yaml nao encontrado em $resolvedIntakePath"
}

$intake = Get-FlatYamlData -Path $resolvedIntakePath
$context = Read-Utf8TextFile -Path $contextPath

if (-not ($context -match "<!-- PG_AUTO:IDENTIFICACAO:START -->")) {
  Write-Host "SKIP: PG_CONTEXT.md nao tem marcadores PG_AUTO (ficheiro gerado pelo mirror - nao aplicavel)"
  exit 0
}

$identificationBlock = @"
Nome do projeto: $(Get-ScalarValue -Data $intake -Key "project_name" -Fallback "[PREENCHER]" -MaxChars 180)
Cliente / unidade: $(Get-ScalarValue -Data $intake -Key "client_unit" -Fallback "[PREENCHER]" -MaxChars 180)
Resumo funcional do repositorio: $(Get-ScalarValue -Data $intake -Key "repository_summary" -Fallback "[PREENCHER]" -MaxChars 220 -StripEmailNoise)
Fase atual do projeto: $(Get-ScalarValue -Data $intake -Key "project_phase" -MaxChars 80)
"@

$restrictionsBlock = @"
Configuracao standard permitida?: $(Get-ScalarValue -Data $intake -Key "standard_allowed" -MaxChars 40)
Modulos standard adicionais permitidos?: $(Get-ScalarValue -Data $intake -Key "additional_modules_allowed" -MaxChars 40)
Odoo Studio permitido?: $(Get-ScalarValue -Data $intake -Key "studio_allowed" -MaxChars 40)
Custom permitido?: $(Get-ScalarValue -Data $intake -Key "custom_allowed" -MaxChars 40)
Restricoes contratuais adicionais: $(Get-ScalarValue -Data $intake -Key "additional_contract_restrictions" -MaxChars 220 -StripEmailNoise)
"@

$requestBlock = @"
Requisito / pedido atual: $(Get-ScalarValue -Data $intake -Key "current_request" -Fallback "[PREENCHER]" -MaxChars 220 -StripEmailNoise)
Objetivo de negocio: $(Get-ScalarValue -Data $intake -Key "business_goal" -Fallback "[PREENCHER]" -MaxChars 220 -StripEmailNoise)
Trigger: $(Get-ScalarValue -Data $intake -Key "trigger" -Fallback "[PREENCHER]" -MaxChars 120)
Frequencia: $(Get-ScalarValue -Data $intake -Key "frequency" -Fallback "[PREENCHER]" -MaxChars 120)
Volumes: $(Get-ScalarValue -Data $intake -Key "volumes" -Fallback "[PREENCHER]" -MaxChars 120)
Urgencia: $(Get-ScalarValue -Data $intake -Key "urgency" -Fallback "[PREENCHER]" -MaxChars 40)
Criterios de aceitacao:
$(Convert-ToPgBulletLines -Items (Get-ListValue -Data $intake -Key "acceptance_criteria" -MaxItems 8 -MaxChars 220 -StripEmailNoise) -Fallback "[PREENCHER]" -MaxChars 220)
"@

$processBlock = @"
Processo atual: $(Get-ScalarValue -Data $intake -Key "current_process" -Fallback "[PREENCHER]" -MaxChars 220 -StripEmailNoise)
Utilizadores / papeis:
$(Convert-ToPgBulletLines -Items (Get-ListValue -Data $intake -Key "users_and_roles" -MaxItems 10 -MaxChars 160) -Fallback "[PREENCHER]" -MaxChars 160)
Excecoes conhecidas:
$(Convert-ToPgBulletLines -Items (Get-ListValue -Data $intake -Key "known_exceptions" -MaxItems 8 -MaxChars 220 -StripEmailNoise) -Fallback "[PREENCHER]" -MaxChars 220)
Aprovacoes:
$(Convert-ToPgBulletLines -Items (Get-ListValue -Data $intake -Key "approvals" -MaxItems 8 -MaxChars 220 -StripEmailNoise) -Fallback "[PREENCHER]" -MaxChars 220)
Documentos envolvidos:
$(Convert-ToPgBulletLines -Items (Get-ListValue -Data $intake -Key "documents" -MaxItems 8 -MaxChars 220 -StripEmailNoise) -Fallback "[PREENCHER]" -MaxChars 220)
Integracoes:
$(Convert-ToPgBulletLines -Items (Get-ListValue -Data $intake -Key "integrations" -MaxItems 8 -MaxChars 220 -StripEmailNoise) -Fallback "[PREENCHER]" -MaxChars 220)
Reporting esperado:
$(Convert-ToPgBulletLines -Items (Get-ListValue -Data $intake -Key "reporting_needs" -MaxItems 8 -MaxChars 220 -StripEmailNoise) -Fallback "[PREENCHER]" -MaxChars 220)
O que ja foi tentado ou validado no standard atual:
$(Convert-ToPgBulletLines -Items (Get-ListValue -Data $intake -Key "standard_attempted_or_validated" -MaxItems 8 -MaxChars 220 -StripEmailNoise) -Fallback "[PREENCHER]" -MaxChars 220)
Porque foi considerado insuficiente:
$(Convert-ToPgBulletLines -Items (Get-ListValue -Data $intake -Key "why_standard_was_insufficient" -MaxItems 8 -MaxChars 220 -StripEmailNoise) -Fallback "[PREENCHER]" -MaxChars 220)
"@

$problemBlock = @"
Problema / necessidade observada: $(Get-ScalarValue -Data $intake -Key "problem_or_need" -Fallback "[PREENCHER]" -MaxChars 220 -StripEmailNoise)
"@

$impactBlock = @"
Impacto de negocio: $(Get-ScalarValue -Data $intake -Key "business_impact" -Fallback "[PREENCHER]" -MaxChars 220 -StripEmailNoise)
"@

$context = Replace-MarkedBlock -Text $context -Marker "IDENTIFICACAO" -BlockContent $identificationBlock
$context = Replace-MarkedBlock -Text $context -Marker "RESTRICOES" -BlockContent $restrictionsBlock
$context = Replace-MarkedBlock -Text $context -Marker "PEDIDO_ATUAL" -BlockContent $requestBlock
$context = Replace-MarkedBlock -Text $context -Marker "PROCESSO_ATUAL" -BlockContent $processBlock
$context = Replace-MarkedBlock -Text $context -Marker "PROBLEMA_DOR" -BlockContent $problemBlock
$context = Replace-MarkedBlock -Text $context -Marker "IMPACTO_NEGOCIO" -BlockContent $impactBlock
$context = Set-LabeledValue -Text $context -Label "Edicao:" -Value (Get-ScalarValue -Data $intake -Key "odoo_edition" -MaxChars 40)
$context = Set-LabeledValue -Text $context -Label "Ambiente:" -Value (Get-ScalarValue -Data $intake -Key "odoo_environment" -MaxChars 40)

Write-Utf8NoBomFile -Path $contextPath -Content $context

Write-Host "OK: PG_CONTEXT.md atualizado a partir do PG_SCOPE_INTAKE.yaml"
