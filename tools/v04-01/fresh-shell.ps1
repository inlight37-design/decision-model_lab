# Run a script in an environment close to a brand-new PowerShell window.
#
# AI tools inject their own variables into the shell they give an agent (the
# Claude desktop app added 26: CLAUDECODE, ANTHROPIC_BASE_URL, ...). This removes
# AI-tool variables that exist only in this process (not in the user or machine
# registry scope) and rebuilds PATH from the registry, so a CLI started from here
# sees what the user's own terminal would see. Nothing persistent is changed.
#
# Usage (from the repository root):
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\v04-01\fresh-shell.ps1 -Script tools\v04-01\check-versions.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\v04-01\fresh-shell.ps1 -Script tools\v04-01\probe.ps1 P1-agy aux-pc
param(
    [Parameter(Mandatory = $true)][string]$Script,
    [Parameter(ValueFromRemainingArguments = $true)]$Rest
)

$prefix = '^(CLAUDE|ANTHROPIC|CODEX|OPENAI|GEMINI|GOOGLE_|MCP_)'
$removed = @()
foreach ($name in (Get-ChildItem Env: | Select-Object -ExpandProperty Name)) {
    if ($name -match $prefix -and
        -not [Environment]::GetEnvironmentVariable($name, 'User') -and
        -not [Environment]::GetEnvironmentVariable($name, 'Machine')) {
        Remove-Item "Env:$name" -ErrorAction SilentlyContinue
        $removed += $name
    }
}
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
Write-Output ("[fresh-shell] removed process-only AI-tool variables: " + $removed.Count)
& $Script @Rest
exit $LASTEXITCODE
