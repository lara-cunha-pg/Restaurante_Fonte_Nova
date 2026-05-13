param(
  [Parameter(Mandatory = $true)]
  [string]$RepoPath,

  [string]$StatusPath
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "pg_project_status_sync_common.ps1")
. (Join-Path $PSScriptRoot "pg_file_io_common.ps1")

function Get-ScalarValue {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName,
    [string]$Fallback,
    [int]$MaxChars = 0,
    [switch]$StripEmailNoise
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if ($property -and $null -ne $property.Value -and -not [string]::IsNullOrWhiteSpace([string]$property.Value)) {
    if ($StripEmailNoise) {
      return (Normalize-PgText -Text ((Get-PgSanitizedLines -Items @([string]$property.Value) -StripEmailNoise -DropPlaceholders -MaxItems 1 -MaxChars $MaxChars) -join ' ') -Fallback $Fallback -MaxChars $MaxChars)
    }
    return (Normalize-PgText -Text ([string]$property.Value) -Fallback $Fallback -MaxChars $MaxChars -DropPlaceholders)
  }

  return $Fallback
}

function Get-ListValue {
  param(
    [pscustomobject]$Data,
    [string]$PropertyName,
    [string]$Fallback,
    [int]$MaxItems = 0,
    [int]$MaxChars = 0,
    [switch]$StripEmailNoise
  )

  $property = $Data.PSObject.Properties[$PropertyName]
  if ($property -and $property.Value) {
    $items = @(Get-PgSanitizedLines -Items @($property.Value) -StripEmailNoise:$StripEmailNoise -DropPlaceholders -MaxItems $MaxItems -MaxChars $MaxChars)
    if ($items.Count -gt 0) {
      return $items
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

$repo = [System.IO.Path]::GetFullPath($RepoPath)
if (-not (Test-Path $repo)) {
  throw "Repositorio nao encontrado: $repo"
}

$contextPath = Join-Path $repo "PG_CONTEXT.md"
if (-not (Test-Path $contextPath)) {
  throw "PG_CONTEXT.md nao encontrado em $contextPath"
}

$resolvedStatusPath = Resolve-ProjectStatusSyncPath -RepositoryPath $repo -ExplicitStatusPath $StatusPath
if (-not (Test-Path $resolvedStatusPath)) {
  throw "PG_PROJECT_STATUS_SYNC.json nao encontrado em $resolvedStatusPath"
}

$status = Get-ProjectStatusSyncData -Path $resolvedStatusPath
[void](Assert-ProjectStatusSyncContract -Data $status)
$context = Read-Utf8TextFile -Path $contextPath

$statusBlock = @"
Schema do snapshot: $(Get-ScalarValue -Data $status -PropertyName "schema_version" -Fallback "[PONTO POR VALIDAR]" -MaxChars 40)
Ultima atualizacao recebida do Odoo: $(Get-ScalarValue -Data $status -PropertyName "last_update_at" -Fallback "[NAO SINCRONIZADA]" -MaxChars 40)
Fase reportada no ultimo sync: $(Get-ScalarValue -Data $status -PropertyName "phase" -Fallback "[PONTO POR VALIDAR]" -MaxChars 80)
Estado geral reportado: $(Get-ScalarValue -Data $status -PropertyName "status_summary" -Fallback "[PONTO POR VALIDAR]" -StripEmailNoise)
Sistema de origem: $(Get-ScalarValue -Data $status -PropertyName "source_system" -Fallback "[PONTO POR VALIDAR]" -MaxChars 80)
Modelo Odoo de origem: $(Get-ScalarValue -Data $status -PropertyName "source_model" -Fallback "[PONTO POR VALIDAR]" -MaxChars 80)
Record Odoo de origem: $(Get-ScalarValue -Data $status -PropertyName "source_record_id" -Fallback "[PONTO POR VALIDAR]" -MaxChars 40)
URL do record Odoo: $(Get-ScalarValue -Data $status -PropertyName "source_record_url" -Fallback "[PONTO POR VALIDAR]" -MaxChars 300)
Publicado no repositorio em: $(Get-ScalarValue -Data $status -PropertyName "sync_published_at" -Fallback "[PONTO POR VALIDAR]" -MaxChars 40)
Publicado por: $(Get-ScalarValue -Data $status -PropertyName "sync_published_by" -Fallback "[PONTO POR VALIDAR]" -MaxChars 120)
Trigger de sync: $(Get-ScalarValue -Data $status -PropertyName "sync_trigger" -Fallback "[PONTO POR VALIDAR]" -MaxChars 80)
Branch de sync: $(Get-ScalarValue -Data $status -PropertyName "repo_branch" -Fallback "[PONTO POR VALIDAR]" -MaxChars 120)
Milestones:
$(Convert-ToPgBulletLines -Items (Get-ListValue -Data $status -PropertyName "milestones" -Fallback "Sem milestones factuais publicadas." -MaxItems 8 -MaxChars 220 -StripEmailNoise) -Fallback "Sem milestones factuais publicadas." -MaxChars 220)
Bloqueios:
$(Convert-ToPgBulletLines -Items (Get-ListValue -Data $status -PropertyName "blockers" -Fallback "Sem bloqueios factuais publicados." -MaxItems 8 -MaxChars 220 -StripEmailNoise) -Fallback "Sem bloqueios factuais publicados." -MaxChars 220)
Riscos operacionais:
$(Convert-ToPgBulletLines -Items (Get-ListValue -Data $status -PropertyName "risks" -Fallback "Sem riscos factuais publicados." -MaxItems 8 -MaxChars 220 -StripEmailNoise) -Fallback "Sem riscos factuais publicados." -MaxChars 220)
Proximos passos operacionais:
$(Convert-ToPgBulletLines -Items (Get-ListValue -Data $status -PropertyName "next_steps" -Fallback "Sem proximos passos factuais publicados." -MaxItems 8 -MaxChars 220 -StripEmailNoise) -Fallback "Sem proximos passos factuais publicados." -MaxChars 220)
Decisoes pendentes:
$(Convert-ToPgBulletLines -Items (Get-ListValue -Data $status -PropertyName "pending_decisions" -Fallback "Sem decisoes pendentes factuais publicadas." -MaxItems 8 -MaxChars 220 -StripEmailNoise) -Fallback "Sem decisoes pendentes factuais publicadas." -MaxChars 220)
Go-live alvo: $(Get-ScalarValue -Data $status -PropertyName "go_live_target" -Fallback "[PONTO POR VALIDAR]" -MaxChars 40)
Owner atual: $(Get-ScalarValue -Data $status -PropertyName "owner" -Fallback "[PONTO POR VALIDAR]" -MaxChars 120)
Fonte Odoo / referencia: $(Get-ScalarValue -Data $status -PropertyName "source_reference" -Fallback "[PONTO POR VALIDAR]" -MaxChars 220)
"@

$context = Replace-MarkedBlock -Text $context -Marker "STATUS_SYNC" -BlockContent $statusBlock
Write-Utf8NoBomFile -Path $contextPath -Content $context

Write-Host "OK: PG_CONTEXT.md atualizado a partir do PG_PROJECT_STATUS_SYNC.json"
