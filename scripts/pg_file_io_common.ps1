function Read-Utf8TextFile {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Path
  )

  $targetPath = [System.IO.Path]::GetFullPath($Path)
  return [System.IO.File]::ReadAllText($targetPath, [System.Text.Encoding]::UTF8)
}

function Read-Utf8Lines {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Path
  )

  $targetPath = [System.IO.Path]::GetFullPath($Path)
  return [System.IO.File]::ReadAllLines($targetPath, [System.Text.Encoding]::UTF8)
}

function Read-Utf8JsonFile {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Path
  )

  return (Read-Utf8TextFile -Path $Path | ConvertFrom-Json)
}

function Write-Utf8NoBomFile {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Path,

    [Parameter(Mandatory = $true)]
    [AllowEmptyString()]
    [string]$Content
  )

  $targetPath = [System.IO.Path]::GetFullPath($Path)
  $directory = Split-Path -Parent $targetPath
  if ($directory -and -not (Test-Path $directory)) {
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
  }

  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($targetPath, $Content, $encoding)
}

$script:PgPlaceholderPattern = '^\[?\s*(?:PONTO POR VALIDAR|PREENCHER|TODO|TBD|PLACEHOLDER|POR VALIDAR)(?:\s*[:\-].*)?\s*\]?$'
$script:PgReplyHeaderPattern = '^\s*(?:From|De|Sent|Enviado|To|Para|Subject|Assunto|Cc|Date|Data)\s*:'
$script:PgReplyWrotePattern = '^\s*(?:On|Em)\b.+\b(?:wrote|escreveu)\s*:\s*$'
$script:PgReplySeparatorPattern = '^\s*(?:-{2,}\s*(?:Original|Forwarded)\s+Message\s*-{2,}|_{5,})\s*$'
$script:PgSignaturePattern = '^\s*(?:--+|__+|Best regards[,]?|Kind regards[,]?|Regards[,]?|Cumprimentos[,]?|Atenciosamente[,]?|Thanks[,]?|Sent from my|Enviado do meu)\b'
$script:PgMojibakeHints = @(
  [string][char]0x00C3,
  [string][char]0x00C2,
  [string][char]0x00E2,
  [string][char]0xFFFD,
  [string][char]0x00CC
)

function Get-PgTextMojibakeScore {
  param([AllowNull()][string]$Text)

  if ([string]::IsNullOrEmpty($Text)) {
    return 0
  }

  $score = 0
  foreach ($hint in $script:PgMojibakeHints) {
    $score += ([regex]::Matches($Text, [regex]::Escape($hint))).Count
  }
  return $score
}

function Repair-PgCommonMojibake {
  param([AllowNull()][string]$Text)

  if ([string]::IsNullOrEmpty($Text)) {
    return ''
  }

  $bestText = $Text
  $bestScore = Get-PgTextMojibakeScore -Text $Text
  if ($bestScore -eq 0) {
    return $Text
  }

  $encodings = @(
    [System.Text.Encoding]::GetEncoding('iso-8859-1'),
    [System.Text.Encoding]::GetEncoding(1252)
  )

  foreach ($encoding in $encodings) {
    try {
      $bytes = $encoding.GetBytes($Text)
      $candidate = [System.Text.Encoding]::UTF8.GetString($bytes)
      $candidateScore = Get-PgTextMojibakeScore -Text $candidate
      if ($candidateScore -lt $bestScore) {
        $bestText = $candidate
        $bestScore = $candidateScore
      }
    }
    catch {
      continue
    }
  }

  return $bestText
}

function Test-PgSuspiciousMojibake {
  param([AllowNull()][string]$Text)

  $normalized = Repair-PgCommonMojibake -Text $Text
  return ((Get-PgTextMojibakeScore -Text $normalized) -ge 2) -or ($normalized -like "*$([string][char]0xFFFD)*")
}

function Test-PgPlaceholderText {
  param([AllowNull()][string]$Text)

  return (-not [string]::IsNullOrWhiteSpace($Text)) -and [regex]::IsMatch($Text.Trim(), $script:PgPlaceholderPattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
}

function Test-PgQuotedReplyText {
  param([AllowNull()][string]$Text)

  if ([string]::IsNullOrWhiteSpace($Text)) {
    return $false
  }

  $meaningfulCount = 0
  foreach ($line in ($Text -replace "`r`n", "`n" -replace "`r", "`n").Split("`n")) {
    $trimmed = $line.Trim()
    if ([string]::IsNullOrWhiteSpace($trimmed)) {
      continue
    }
    if ($trimmed.StartsWith('>')) {
      if ($meaningfulCount -gt 0) {
        return $true
      }
      continue
    }
    if (
      [regex]::IsMatch($trimmed, $script:PgReplyHeaderPattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase) -or
      [regex]::IsMatch($trimmed, $script:PgReplyWrotePattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase) -or
      [regex]::IsMatch($trimmed, $script:PgReplySeparatorPattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    ) {
      return $true
    }
    $meaningfulCount += 1
  }

  return $false
}

function Test-PgSignatureText {
  param([AllowNull()][string]$Text)

  if ([string]::IsNullOrWhiteSpace($Text)) {
    return $false
  }

  foreach ($line in ($Text -replace "`r`n", "`n" -replace "`r", "`n").Split("`n")) {
    $trimmed = $line.Trim()
    if ([string]::IsNullOrWhiteSpace($trimmed)) {
      continue
    }
    if ([regex]::IsMatch($trimmed, $script:PgSignaturePattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)) {
      return $true
    }
  }

  return $false
}

function Normalize-PgText {
  param(
    [AllowNull()][string]$Text,
    [string]$Fallback = '',
    [int]$MaxChars = 0,
    [switch]$DropPlaceholders
  )

  $normalized = Repair-PgCommonMojibake -Text $Text
  if ($null -eq $normalized) {
    $normalized = ''
  }
  $normalized = [regex]::Replace($normalized, '\s+', ' ').Trim()

  if ($DropPlaceholders -and (Test-PgPlaceholderText -Text $normalized)) {
    $normalized = ''
  }

  if ($MaxChars -gt 0 -and $normalized.Length -gt $MaxChars) {
    if ($MaxChars -le 3) {
      $normalized = $normalized.Substring(0, $MaxChars)
    }
    else {
      $normalized = $normalized.Substring(0, $MaxChars - 3).TrimEnd(' ', ',', ';', ':') + '...'
    }
  }

  if (-not [string]::IsNullOrWhiteSpace($normalized)) {
    return $normalized
  }

  return $Fallback
}

function Get-PgSanitizedLines {
  param(
    [AllowNull()][object[]]$Items,
    [switch]$StripEmailNoise,
    [switch]$DropPlaceholders,
    [int]$MaxItems = 0,
    [int]$MaxChars = 0
  )

  $rawLines = @()
  foreach ($item in @($Items)) {
    if ($null -eq $item) {
      continue
    }
    $parts = ([string]$item -replace "`r`n", "`n" -replace "`r", "`n").Split("`n")
    $rawLines += $parts
  }

  $candidateLines = @()
  $meaningfulCount = 0
  foreach ($line in $rawLines) {
    $trimmed = ([string]$line).Trim()
    if ([string]::IsNullOrWhiteSpace($trimmed)) {
      continue
    }

    if ($StripEmailNoise) {
      if ($trimmed.StartsWith('>')) {
        if ($meaningfulCount -gt 0) {
          break
        }
        continue
      }

      if (
        [regex]::IsMatch($trimmed, $script:PgReplyHeaderPattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase) -or
        [regex]::IsMatch($trimmed, $script:PgReplyWrotePattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase) -or
        [regex]::IsMatch($trimmed, $script:PgReplySeparatorPattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
      ) {
        break
      }
    }

    $candidateLines += $trimmed
    $meaningfulCount += 1
  }

  $result = @()
  $seen = @{}
  $meaningfulCount = 0
  foreach ($line in $candidateLines) {
    if (
      $StripEmailNoise -and
      $meaningfulCount -gt 0 -and
      [regex]::IsMatch($line, $script:PgSignaturePattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    ) {
      break
    }

    $normalized = Normalize-PgText -Text $line.Trim(' ', '-', '*', "`t") -Fallback '' -MaxChars $MaxChars -DropPlaceholders:$DropPlaceholders
    if ([string]::IsNullOrWhiteSpace($normalized)) {
      continue
    }

    if (-not $seen.ContainsKey($normalized)) {
      $seen[$normalized] = $true
      $result += $normalized
      $meaningfulCount += 1
    }

    if ($MaxItems -gt 0 -and $result.Count -ge $MaxItems) {
      break
    }
  }

  return @($result)
}

function Convert-ToPgBulletLines {
  param(
    [AllowNull()][object[]]$Items,
    [string]$Fallback = '[PREENCHER]',
    [switch]$StripEmailNoise,
    [int]$MaxItems = 0,
    [int]$MaxChars = 0
  )

  $lines = Get-PgSanitizedLines -Items $Items -StripEmailNoise:$StripEmailNoise -DropPlaceholders -MaxItems $MaxItems -MaxChars $MaxChars
  if ($lines.Count -eq 0) {
    $lines = @($Fallback)
  }

  return (($lines | ForEach-Object { "- $_" }) -join "`r`n")
}
