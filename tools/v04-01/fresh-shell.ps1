# Run a script in an environment close to a brand-new PowerShell window.
#
# AI tools inject their own variables into the shell they give an agent (the
# Claude desktop app added 26: CLAUDECODE, ANTHROPIC_BASE_URL, ...). This rebuilds
# the AI-tool variables and PATH from the user and machine registry scopes (user
# wins): a variable only this process has is removed, one the process overrode goes
# back to the registry value, and one added to the registry after this shell started
# appears. Other variables (proxy settings and so on) are left as they are, so this
# is not a brand-new window. Same rule as fresh_environment() in
# tools/runtime_inventory.py. Nothing persistent is changed.
#
# Usage (from the repository root):
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\v04-01\fresh-shell.ps1 -Script tools\v04-01\check-versions.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\v04-01\fresh-shell.ps1 -Script tools\v04-01\probe.ps1 P1-agy aux-pc
param(
    [Parameter(Mandatory = $true)][string]$Script,
    [Parameter(ValueFromRemainingArguments = $true)]$Rest
)

$prefix = '^(CLAUDE|ANTHROPIC|CODEX|OPENAI|GEMINI|GOOGLE_|MCP_)'
$persistent = @{}   # hashtable keys ignore case, like Windows variable names
foreach ($scope in 'Machine', 'User') {
    $vars = [Environment]::GetEnvironmentVariables($scope)
    foreach ($name in $vars.Keys) {
        if ($name -match $prefix) { $persistent[$name] = $vars[$name] }
    }
}
$removed = @()
foreach ($name in (Get-ChildItem Env: | Select-Object -ExpandProperty Name)) {
    if ($name -match $prefix -and -not $persistent.ContainsKey($name)) {
        Remove-Item "Env:$name" -ErrorAction SilentlyContinue
        $removed += $name
    }
}
foreach ($name in $persistent.Keys) {
    [Environment]::SetEnvironmentVariable($name, $persistent[$name], 'Process')
}
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
Write-Output ("[fresh-shell] removed process-only AI-tool variables: {0}; set from the registry: {1}" -f $removed.Count, $persistent.Count)
& $Script @Rest
exit $LASTEXITCODE
