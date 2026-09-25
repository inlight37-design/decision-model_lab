# Prepare a Windows PC for this repository. Safe to run again. Run it from a normal PowerShell window:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\setup\setup-windows.ps1 [-CheckOnly] [-Wsl]
#
# 1. Installs missing tools with winget: Git, GitHub CLI, Python 3.13, Node.js LTS. winget asks you to
#    accept each package's terms; this script does not accept them for you.
# 2. Installs the Python test dependency (requirements-design.txt) and turns on the encoding hook.
# 3. Checks for the Ubuntu WSL distribution. It does not install WSL (that needs an admin window and a
#    reboot); it prints the command. With -Wsl it runs tools/setup/setup-wsl.sh inside Ubuntu, where
#    sudo asks for your Linux password.
# 4. Runs tools\setup\check_setup.py and exits with its code (0 = every required item is ready).
#
# Never logs in, never calls a model. -CheckOnly changes nothing and only reports.
# ASCII only: Windows PowerShell 5.1 reads BOM-less UTF-8 scripts as ANSI.
param([switch]$CheckOnly, [switch]$Wsl, [string]$Distro = 'Ubuntu-24.04')

$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $root

function Test-Works([string]$exe, [string[]]$arguments) {
    # The Microsoft Store 'python' alias is found by Get-Command but does not run, so run it.
    if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { return $false }
    try { $null = & $exe @arguments 2>$null; return ($LASTEXITCODE -eq 0) } catch { return $false }
}

$packages = @(
    @{ Name = 'Git';         Exe = 'git';    Args = @('--version'); Id = 'Git.Git' },
    @{ Name = 'GitHub CLI';  Exe = 'gh';     Args = @('--version'); Id = 'GitHub.cli' },
    @{ Name = 'Python 3.12+'; Exe = 'python'; Args = @('-c', 'import sys; sys.exit(sys.version_info < (3, 12))'); Id = 'Python.Python.3.13' },
    @{ Name = 'Node.js LTS'; Exe = 'node';   Args = @('--version'); Id = 'OpenJS.NodeJS.LTS' }
)
$installed = 0
foreach ($p in $packages) {
    if (Test-Works $p.Exe $p.Args) { 'ok       {0}' -f $p.Name; continue }
    if ($CheckOnly) { 'missing  {0}  -> winget install --id {1} -e' -f $p.Name, $p.Id; continue }
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        'winget is not available. Install "App Installer" from the Microsoft Store, then run this again.'
        exit 1
    }
    'install  {0} ({1})' -f $p.Name, $p.Id
    winget install --id $p.Id -e --source winget
    if ($LASTEXITCODE -ne 0) { 'WARNING: winget returned {0} for {1}' -f $LASTEXITCODE, $p.Id }
    $installed++
}
if ($installed -gt 0) {
    'Installed {0} package(s). Open a NEW PowerShell window so PATH is refreshed, then run this script again.' -f $installed
    exit 0
}

if (-not $CheckOnly) {
    python -m pip install --disable-pip-version-check -r requirements-design.txt
    git config core.hooksPath .githooks
}

$hasDistro = $false
if (Get-Command wsl.exe -ErrorAction SilentlyContinue) {
    # wsl.exe prints UTF-16; PowerShell 5.1 reads it with NUL characters between letters.
    $names = @(wsl.exe --list --quiet) | ForEach-Object { ($_ -replace "`0", '').Trim() }
    $hasDistro = $names -contains $Distro
}
if (-not $hasDistro) {
    'WSL distribution {0} not found. Live CLI runs need it (offline checks do not).' -f $Distro
    '  In an ADMIN PowerShell:  wsl --install -d {0}' -f $Distro
    '  Reboot, open Ubuntu once to create your Linux user, then run this script again with -Wsl.'
} elseif ($Wsl -and -not $CheckOnly) {
    $linuxRoot = (wsl.exe -d $Distro -e wslpath -a $root | Out-String).Trim()
    wsl.exe -d $Distro -e bash -lc "cd '$linuxRoot' && bash tools/setup/setup-wsl.sh"
} else {
    'WSL {0} found. To prepare it: rerun with -Wsl, or inside Ubuntu run  bash tools/setup/setup-wsl.sh' -f $Distro
}

python tools\setup\check_setup.py
exit $LASTEXITCODE
