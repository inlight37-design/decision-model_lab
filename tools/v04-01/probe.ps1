# V04-01 tier 2: run ONE probe from the runbook (section 4) and save its redacted output.
#
# Run it through fresh-shell.ps1, one probe at a time, and read the result before the
# next one. Probes P1, P4 and P1-agy call a model (a small amount of subscription quota);
# P2 and P3 are expected to fail before any model call. Needs the user's approval.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\v04-01\fresh-shell.ps1 -Script tools\v04-01\probe.ps1 P3-agy aux-pc
#
# Output: docs\experiments\v04-01-inventory\hosts\<label>\tier2\<probe>.txt with e-mail
# addresses, UUIDs, token-like strings and the home path masked. Check the file before
# committing. P4-claude lists the user's plugins and connected services: summarise it with
# summarize_claude_init.py and keep the raw stream off the repository.
param(
    [Parameter(Mandatory = $true, Position = 0)][string]$Id,
    [Parameter(Position = 1)][string]$HostLabel = 'aux-pc'
)

[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$ErrorActionPreference = 'Continue'
if ($HostLabel -notmatch '^[a-z0-9][a-z0-9-]{1,39}$') { Write-Output "invalid host label"; exit 2 }

$prompt = 'Reply with exactly: OK'
$probes = @{
    'P1-claude' = @('claude', '-p', $prompt, '--output-format', 'json', '--permission-mode', 'dontAsk')
    'P1-codex'  = @('codex', 'exec', '--json', '--skip-git-repo-check', '--ephemeral', $prompt)
    'P1-agy'    = @('agy', '-p', $prompt, '--output-format', 'json')
    'P2-claude' = @('claude', '--bare', '-p', $prompt, '--output-format', 'json')
    'P3-claude' = @('claude', '-p', $prompt, '--permission-mode', 'notamode')
    'P3-codex'  = @('codex', 'exec', '--skip-git-repo-check', '--sandbox', 'notamode', $prompt)
    'P3-agy'    = @('agy', '-p', $prompt, '--output-format', 'notaformat')
    # P3b: a misspelled restriction flag. Added on aux-pc after agy silently ignored an invalid
    # --output-format value; a typo in a sandbox or permission flag must not run unrestricted.
    'P3b-claude' = @('claude', '-p', $prompt, '--permision-mode', 'plan')
    'P3b-codex'  = @('codex', 'exec', '--skip-git-repo-check', '--sandbx', 'read-only', $prompt)
    'P3b-agy'    = @('agy', '-p', $prompt, '--sandbx')
    'P4-claude' = @('claude', '-p', $prompt, '--output-format', 'stream-json', '--verbose')
    # P4b: can Claude run with a clean context and still use the subscription? --bare cannot (P2).
    # --restricted (2.1.280 help) ignores user/project/local settings; --strict-mcp-config with no
    # --mcp-config drops MCP servers; --disable-slash-commands drops skills; --tools "" drops tools.
    # Windows PowerShell 5.1 drops an empty-string argument, so '""' is passed to mean "".
    'P4b-claude' = @('claude', '-p', $prompt, '--output-format', 'stream-json', '--verbose', '--restricted', '--strict-mcp-config', '--disable-slash-commands', '--tools', '""')
    'P4-codex'  = @('codex', 'exec', '--json', '--skip-git-repo-check', '--ephemeral', '--ignore-user-config', '--ignore-rules', $prompt)
    'P5-agy'    = @('agy', 'models')
}
if (-not $probes.ContainsKey($Id)) { Write-Output ("unknown probe; choose one of: " + (($probes.Keys | Sort-Object) -join ', ')); exit 2 }

$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$out = Join-Path $repo "docs\experiments\v04-01-inventory\hosts\$HostLabel\tier2"
New-Item -ItemType Directory -Force $out | Out-Null

# An empty folder outside the repository, so no project instructions reach the model.
$work = Join-Path $env:TEMP 'v0401-probe'
New-Item -ItemType Directory -Force $work | Out-Null
Set-Location $work
if (Get-ChildItem $work -Force) { Write-Output "probe folder $work is not empty; a previous probe wrote into it. Record that, then empty it."; exit 2 }

$homeDir = $env:USERPROFILE
function Hide([string]$t) {
    $t = $t.Replace($homeDir, '~').Replace($homeDir.Replace('\', '\\'), '~').Replace($homeDir.Replace('\', '/'), '~')
    $t = $t -replace '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', '<email>'
    $t = $t -replace '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', '<uuid>'
    $t = $t -replace '(?<![A-Za-z0-9])(sk-[A-Za-z0-9_-]{16,}|eyJ[A-Za-z0-9._-]{20,})', '<redacted>'
    return $t
}

$exe, $argv = $probes[$Id]
$argv = @($argv)
$sw = [Diagnostics.Stopwatch]::StartNew()
# stdin is not forwarded: codex exec waits on an open stdin (observed on aux-pc).
$raw = & $exe @argv 2>&1 | ForEach-Object { "$_" } | Out-String
$code = $LASTEXITCODE
$sw.Stop()
$shown = ($probes[$Id] | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }) -join ' '
$text = "# probe: $Id`n# command: $shown`n# cwd: empty folder outside the repository`n# environment: fresh (AI-tool variables removed)`n# exit: $code`n# duration_ms: $($sw.ElapsedMilliseconds)`n`n" + (Hide $raw)
[IO.File]::WriteAllText((Join-Path $out "$Id.txt"), $text, [Text.UTF8Encoding]::new($false))
Write-Output ("{0}: exit={1} ms={2}" -f $Id, $code, $sw.ElapsedMilliseconds)
Write-Output (Hide $raw)
exit 0
