# One-touch setup of decision-model_lab on a Windows PC. Safe to run again: every step checks first
# and skips what is already done.
#
# New PC - one line in a normal (not admin) PowerShell window:
#   irm https://raw.githubusercontent.com/inlight37-design/decision-model_lab/main/tools/setup/setup.ps1 -OutFile "$env:TEMP\dml-setup.ps1"; powershell -NoProfile -ExecutionPolicy Bypass -File "$env:TEMP\dml-setup.ps1"
# Existing clone:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\setup\setup.ps1
#
# Steps, in order:
#  1. winget: Git, GitHub CLI, Python 3.13, Node.js LTS (and the Claude desktop app with -Apps).
#     Running this script is your consent to those packages' terms; winget is told to accept them.
#  2. clone the repository to -RepoDir (default C:\ai\decision-model_lab), install the Python test
#     dependency, turn on the encoding hook.
#  3. WSL and Ubuntu-24.04. Windows asks for administrator approval (UAC). If Windows must restart,
#     the script registers itself to continue after you sign in again (RunOnce, removed when it runs).
#  4. your Linux user: Ubuntu asks for a user name and password; they stay inside Ubuntu.
#  5. apt packages as root inside Ubuntu (no sudo password), then the official Codex and Claude Code
#     CLIs pinned to the observed versions (tools/setup/setup-wsl.sh).
#  6. logins, one after another, each approved in your browser: GitHub, Claude, Codex. -SkipLogin skips.
#  7. tools/setup/check_setup.py on Windows and in Ubuntu. Exit code 0 = every required item is ready.
#
# Never reads or stores passwords or tokens, never calls a model. -CheckOnly changes nothing and
# reports what each step would do. A transcript goes to %USERPROFILE%\dml-setup.log.
# ASCII only: Windows PowerShell 5.1 reads BOM-less UTF-8 scripts as ANSI.
param(
    [string]$RepoDir = 'C:\ai\decision-model_lab',
    [string]$Distro = 'Ubuntu-24.04',
    [string]$RepoUrl = 'https://github.com/inlight37-design/decision-model_lab.git',
    [switch]$CheckOnly,
    [switch]$SkipLogin,
    [switch]$Apps,
    [switch]$Resume
)

$log = Join-Path $env:USERPROFILE 'dml-setup.log'
try { Start-Transcript -Path $log -Append | Out-Null } catch {}

function Step([string]$text) { Write-Host ''; Write-Host "== $text" -ForegroundColor Cyan }
function Say([string]$text) { Write-Host "   $text" }
function Would([string]$text) { Write-Host "   would: $text" -ForegroundColor Yellow }
function Stop-Setup([string]$text) {
    Write-Host "   STOP: $text" -ForegroundColor Red
    Write-Host "   Fix that and run the same command again; finished steps are skipped. Log: $log"
    try { Stop-Transcript | Out-Null } catch {}
    exit 1
}
function Update-SessionPath {
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
}
function Test-Works([string]$exe, [string[]]$arguments) {
    # The Microsoft Store 'python' alias is found by Get-Command but does not run, so run it.
    if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { return $false }
    try { $null = & $exe @arguments 2>$null; return ($LASTEXITCODE -eq 0) } catch { return $false }
}
function Get-PythonCommand {
    # 'python' may be missing from PATH right after winget installs it; the 'py' launcher still works.
    $probe = @('-c', 'import sys; sys.exit(sys.version_info < (3, 12))')
    if (Test-Works 'python' $probe) { return ,@('python') }
    if (Test-Works 'py' (@('-3') + $probe)) { return ,@('py', '-3') }
    return $null
}
function Invoke-Python([string[]]$arguments) {
    $cmd = Get-PythonCommand
    if (-not $cmd) { $global:LASTEXITCODE = 1; Say 'Python 3.12+ was not found.'; return }
    $rest = @(); if ($cmd.Count -gt 1) { $rest = $cmd[1..($cmd.Count - 1)] }
    & $cmd[0] @rest @arguments
}
function Get-Distros {
    # wsl.exe prints UTF-16; PowerShell 5.1 reads it with NUL characters between letters.
    if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) { return @() }
    try { return @(& wsl.exe --list --quiet 2>$null | ForEach-Object { ($_ -replace "`0", '').Trim() } | Where-Object { $_ }) }
    catch { return @() }
}
function Invoke-Linux([string]$command, [switch]$Root) {
    # Runs one bash command inside the distribution: login shell for the user, plain bash for root.
    if ($Root) { & wsl.exe -d $Distro -u root -e bash -c $command } else { & wsl.exe -d $Distro -e bash -lc $command }
}
function Register-Resume {
    $command = "powershell.exe -NoProfile -ExecutionPolicy Bypass -NoExit -File `"$RepoDir\tools\setup\setup.ps1`" -Resume -RepoDir `"$RepoDir`" -Distro $Distro"
    if ($SkipLogin) { $command += ' -SkipLogin' }
    Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce' -Name 'decision-model_lab-setup' -Value $command
}

Write-Host 'decision-model_lab one-touch setup' -ForegroundColor Cyan
if ($CheckOnly) { Say 'check only: nothing will be installed or changed' }
if ($Resume) { Say 'continuing after the restart' }
if ($RepoDir -like "$env:LOCALAPPDATA*") { Stop-Setup "Choose a folder outside AppData for -RepoDir (see docs/SETUP.md, trap 1)." }

# ---- 1. Windows tools -----------------------------------------------------------------------
Step '1/7 Windows tools (winget)'
$packages = @(
    @{ Name = 'Git';          Exe = 'git';    Args = @('--version'); Id = 'Git.Git' },
    @{ Name = 'GitHub CLI';   Exe = 'gh';     Args = @('--version'); Id = 'GitHub.cli' },
    @{ Name = 'Python 3.12+'; Exe = 'python'; Args = @('-c', 'import sys; sys.exit(sys.version_info < (3, 12))'); Id = 'Python.Python.3.13' },
    @{ Name = 'Node.js LTS';  Exe = 'node';   Args = @('--version'); Id = 'OpenJS.NodeJS.LTS' }
)
if ($Apps) { $packages += @{ Name = 'Claude desktop app'; Exe = ''; Args = @(); Id = 'Anthropic.Claude' } }
foreach ($p in $packages) {
    $present = if ($p.Id -like 'Python.*') { [bool](Get-PythonCommand) } elseif ($p.Exe) { Test-Works $p.Exe $p.Args } else { [bool](winget list --id $p.Id -e --disable-interactivity 2>$null | Select-String -SimpleMatch $p.Id) }
    if ($present) { Say "ok      $($p.Name)"; continue }
    if ($CheckOnly) { Would "winget install --id $($p.Id)"; continue }
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { Stop-Setup 'winget is missing. Install "App Installer" from the Microsoft Store.' }
    Say "install $($p.Name) ($($p.Id))"
    winget install --id $p.Id -e --source winget --accept-package-agreements --accept-source-agreements --disable-interactivity
    Update-SessionPath
    $found = if ($p.Id -like 'Python.*') { [bool](Get-PythonCommand) } elseif ($p.Exe) { Test-Works $p.Exe $p.Args } else { $true }
    if (-not $found) { Say "WARNING: $($p.Name) is still not on PATH. If a later step fails, open a new window and run again." }
}

# ---- 2. Repository ----------------------------------------------------------------------------
Step "2/7 Repository at $RepoDir"
if (Test-Path (Join-Path $RepoDir '.git')) { Say 'ok      already cloned (left as it is)' }
elseif ($CheckOnly) { Would "git clone $RepoUrl $RepoDir" }
else {
    New-Item -ItemType Directory -Force -Path (Split-Path $RepoDir) | Out-Null
    git clone $RepoUrl $RepoDir
    if ($LASTEXITCODE -ne 0) { Stop-Setup 'git clone failed.' }
}
if (-not $CheckOnly) {
    Push-Location $RepoDir
    Invoke-Python @('-m', 'pip', 'install', '--disable-pip-version-check', '-q', '-r', 'requirements-design.txt')
    if ($LASTEXITCODE -ne 0) { Say 'WARNING: pip install failed; schema tests will skip until jsonschema is installed.' }
    git config core.hooksPath .githooks
    Pop-Location
    Say 'ok      test dependency and encoding hook'
}

# ---- 3. WSL and Ubuntu ------------------------------------------------------------------------
Step "3/7 WSL and $Distro"
if ((Get-Distros) -contains $Distro) { Say "ok      $Distro is installed" }
elseif ($CheckOnly) { Would "wsl --install -d $Distro --no-launch (administrator approval; maybe a restart)" }
else {
    Say 'Windows will ask for administrator approval (UAC) to install WSL and Ubuntu.'
    try { Start-Process wsl.exe -ArgumentList @('--install', '-d', $Distro, '--no-launch') -Verb RunAs -Wait } catch { Stop-Setup 'administrator approval was declined.' }
    if ((Get-Distros) -notcontains $Distro) {
        $null = & wsl.exe --status 2>$null
        if ($LASTEXITCODE -eq 0) {
            # WSL works but this distribution needs its first launch to register: do it here.
            Say 'Finishing the Ubuntu install in this window.'
            & wsl.exe --install -d $Distro
        }
        if ((Get-Distros) -notcontains $Distro) {
            Register-Resume
            Say 'Windows must restart to finish enabling WSL. After you sign in again, this setup continues by itself.'
            if ((Read-Host '   Restart now? (y/n)') -eq 'y') { Restart-Computer }
            try { Stop-Transcript | Out-Null } catch {}
            exit 0
        }
    }
}

# ---- 4. Linux user ----------------------------------------------------------------------------
Step '4/7 Your Linux user'
$uid = ''
if ((Get-Distros) -contains $Distro) { $uid = (& wsl.exe -d $Distro -e id -u 2>$null | Out-String).Trim() }
if ($uid -and $uid -ne '0') { Say 'ok      a Linux user exists and is the default' }
elseif ($CheckOnly) { Would 'create your Linux user (Ubuntu asks for a name and a password)' }
else {
    Say 'Ubuntu will ask you for a new user name and password. They stay inside Ubuntu.'
    Say 'When you see the Ubuntu prompt ending in $, type  exit  and press Enter to continue.'
    & wsl.exe -d $Distro
    $uid = (& wsl.exe -d $Distro -e id -u 2>$null | Out-String).Trim()
    if ($uid -eq '0') {
        # This Ubuntu did not run its first-run questions: create the user from root instead.
        $name = Read-Host '   Linux user name (lowercase letters, digits, - or _)'
        if ($name -notmatch '^[a-z_][a-z0-9_-]{0,31}$') { Stop-Setup 'that is not a valid Linux user name.' }
        & wsl.exe -d $Distro -u root -e useradd -m -s /bin/bash -G sudo $name
        Say "Set the password for $name (typed into Ubuntu's passwd, not seen by this script):"
        & wsl.exe -d $Distro -u root -e passwd $name
        Invoke-Linux -Root "printf '\n[user]\ndefault=%s\n' '$name' >> /etc/wsl.conf"
        & wsl.exe --terminate $Distro | Out-Null
        $uid = (& wsl.exe -d $Distro -e id -u 2>$null | Out-String).Trim()
        if ($uid -eq '0') { Stop-Setup 'the Linux user was not set as the default.' }
    }
    Say 'ok      Linux user ready'
}

# ---- 5. Packages and CLIs inside Ubuntu -------------------------------------------------------
Step '5/7 Packages and CLIs inside Ubuntu'
$linuxRepo = ''
if ((Get-Distros) -contains $Distro -and (Test-Path (Join-Path $RepoDir 'tools\setup\setup-wsl.sh'))) {
    $linuxRepo = (& wsl.exe -d $Distro -e wslpath -a $RepoDir | Out-String).Trim()
}
if (-not $linuxRepo) {
    if ($CheckOnly) { Would 'install apt packages and the CLIs (needs the distribution and the clone first)' }
    else { Stop-Setup "Ubuntu or $RepoDir\tools\setup\setup-wsl.sh is missing." }
} else {
    $check = if ($CheckOnly) { ' --check' } else { '' }
    Invoke-Linux -Root "bash '$linuxRepo/tools/setup/setup-wsl.sh' --apt-only$check"
    if ($LASTEXITCODE -ne 0) { Stop-Setup 'apt packages were not installed.' }
    Invoke-Linux "cd '$linuxRepo' && bash tools/setup/setup-wsl.sh --no-final$check"
    if ($LASTEXITCODE -ne 0) { Stop-Setup 'the CLIs were not installed (see the message above).' }
}

# ---- 6. Logins --------------------------------------------------------------------------------
Step '6/7 Logins (each one is approved in your browser)'
if ($SkipLogin) { Say 'skipped (-SkipLogin)' }
else {
    $null = & gh auth status 2>$null
    if ($LASTEXITCODE -eq 0) { Say 'ok      GitHub' }
    elseif ($CheckOnly) { Would 'gh auth login --web' }
    else { gh auth login --web --git-protocol https --hostname github.com }
    if (-not $CheckOnly -and -not (git config --global user.name)) {
        # Commit identity from the GitHub account: the login name and GitHub's no-reply address.
        $login = (gh api user --jq .login 2>$null | Out-String).Trim()
        $id = (gh api user --jq .id 2>$null | Out-String).Trim()
        if ($login -and $id) {
            git config --global user.name $login
            git config --global user.email "$id+$login@users.noreply.github.com"
            Say "ok      git commit identity: $login (GitHub no-reply address)"
        }
    }
    if ($linuxRepo) {
        $claude = (Invoke-Linux 'claude auth status 2>/dev/null' | Out-String)
        if ($claude -match '"loggedIn":\s*true') { Say 'ok      Claude' }
        elseif ($CheckOnly) { Would 'claude auth login (inside Ubuntu)' }
        else { Say 'Claude login: choose the Claude subscription (claude.ai), not an API key.'; Invoke-Linux 'claude auth login' }
        $null = Invoke-Linux 'codex login status >/dev/null 2>&1'
        if ($LASTEXITCODE -eq 0) { Say 'ok      Codex' }
        elseif ($CheckOnly) { Would 'codex login (inside Ubuntu)' }
        else { Say 'Codex login: sign in with your ChatGPT account.'; Invoke-Linux 'codex login' }
    }
}

# ---- 7. Check ---------------------------------------------------------------------------------
Step '7/7 Check'
$code = 0
if (Test-Path (Join-Path $RepoDir 'tools\setup\check_setup.py')) {
    Push-Location $RepoDir
    Invoke-Python @('tools\setup\check_setup.py')
    if ($LASTEXITCODE -ne 0) { $code = 1 }
    Pop-Location
} else { Say 'skipped on Windows: the clone is not there yet'; $code = 1 }
if ($linuxRepo) {
    Invoke-Linux "cd '$linuxRepo' && python3 tools/setup/check_setup.py"
    if ($LASTEXITCODE -ne 0) { $code = 1 }
}
Write-Host ''
if ($code -eq 0) { Write-Host 'All required items are ready. Next: open NEXT-SESSION.md in the repository.' -ForegroundColor Green }
else { Write-Host "Some required items are not ready (see above). Run the same command again after fixing them. Log: $log" -ForegroundColor Yellow }
try { Stop-Transcript | Out-Null } catch {}
exit $code
