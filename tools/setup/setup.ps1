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
#     CLIs pinned to the observed versions (tools/setup/setup-wsl.sh). If an official installer changed,
#     read the file it names and rerun with -AcceptInstallerSha codex=<sha256> (or claude=...).
#  6. logins, one after another, each approved in your browser: GitHub, Claude, Codex. -SkipLogin skips.
#  7. tools/setup/check_setup.py on Windows and in Ubuntu.
#
# Exit codes: 0 ready (tools and subscription logins; strict runs still need this machine's own
# observation), 1 a step failed, 2 not finished yet (restart Windows or open a new window, then run
# the same command again). A failure is never reported as success.
# Never reads or stores passwords or tokens, never calls a model. -CheckOnly changes nothing and
# reports what each step would do. A transcript goes to %USERPROFILE%\dml-setup.log.
# ASCII only: Windows PowerShell 5.1 reads BOM-less UTF-8 scripts as ANSI.
param(
    [string]$RepoDir = 'C:\ai\decision-model_lab',
    [string]$Distro = 'Ubuntu-24.04',
    [string]$RepoUrl = 'https://github.com/inlight37-design/decision-model_lab.git',
    [string[]]$AcceptInstallerSha = @(),
    [switch]$CheckOnly,
    [switch]$SkipLogin,
    [switch]$Apps,
    [switch]$Resume
)

$script:Log = Join-Path $env:USERPROFILE 'dml-setup.log'
$script:LinuxRepo = ''

function Step([string]$text) { Write-Host ''; Write-Host "== $text" -ForegroundColor Cyan }
function Say([string]$text) { Write-Host "   $text" }
function Would([string]$text) { Write-Host "   would: $text" -ForegroundColor Yellow }
function Stop-Setup([string]$text, [int]$code = 1) {
    # Code 2 means "not finished yet", 1 means a step failed. Neither is success.
    if ($code -eq 2) { Write-Host "   NOT FINISHED: $text" -ForegroundColor Yellow }
    else { Write-Host "   STOP: $text" -ForegroundColor Red }
    Write-Host "   Run the same command again afterwards; finished steps are skipped. Log: $script:Log"
    try { Stop-Transcript | Out-Null } catch {}
    exit $code
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
function Get-LinuxUid {
    if ((Get-Distros) -notcontains $Distro) { return '' }
    return (& wsl.exe -d $Distro -e id -u 2>$null | Out-String).Trim()
}
function Register-Resume {
    $command = "powershell.exe -NoProfile -ExecutionPolicy Bypass -NoExit -File `"$RepoDir\tools\setup\setup.ps1`" -Resume -RepoDir `"$RepoDir`" -Distro $Distro"
    if ($SkipLogin) { $command += ' -SkipLogin' }
    Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce' -Name 'decision-model_lab-setup' -Value $command
}

function Get-Packages {
    $list = @(
        @{ Name = 'Git';          Exe = 'git';    Args = @('--version'); Id = 'Git.Git';            Required = $true },
        @{ Name = 'GitHub CLI';   Exe = 'gh';     Args = @('--version'); Id = 'GitHub.cli';         Required = $true },
        @{ Name = 'Python 3.12+'; Exe = 'python'; Args = @();            Id = 'Python.Python.3.13'; Required = $true },
        @{ Name = 'Node.js LTS';  Exe = 'node';   Args = @('--version'); Id = 'OpenJS.NodeJS.LTS';  Required = $false }
    )
    if ($Apps) { $list += @{ Name = 'Claude desktop app'; Exe = ''; Args = @(); Id = 'Anthropic.Claude'; Required = $false } }
    return $list
}
function Test-Package($p) {
    if ($p.Id -like 'Python.*') { return [bool](Get-PythonCommand) }
    if ($p.Exe) { return (Test-Works $p.Exe $p.Args) }
    return [bool](winget list --id $p.Id -e --disable-interactivity 2>$null | Select-String -SimpleMatch $p.Id)
}

# ---- 1. Windows tools -----------------------------------------------------------------------
function Install-WindowsTools {
    Step '1/7 Windows tools (winget)'
    $notVisible = @()
    foreach ($p in (Get-Packages)) {
        if (Test-Package $p) { Say "ok      $($p.Name)"; continue }
        if ($CheckOnly) { Would "winget install --id $($p.Id)"; continue }
        if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { Stop-Setup 'winget is missing. Install "App Installer" from the Microsoft Store.' }
        Say "install $($p.Name) ($($p.Id))"
        winget install --id $p.Id -e --source winget --accept-package-agreements --accept-source-agreements --disable-interactivity
        $code = $LASTEXITCODE
        Update-SessionPath
        if (Test-Package $p) { Say "ok      $($p.Name) installed"; continue }
        if ($code -ne 0) {
            if ($p.Required) { Stop-Setup "winget could not install $($p.Name) ($($p.Id), exit $code)." }
            Say "WARNING: $($p.Name) was not installed (winget exit $code). It is optional; its checks will be skipped."
            continue
        }
        if ($p.Required) { $notVisible += $p.Name }
        else { Say "NOTE: $($p.Name) was installed but is not visible in this window yet." }
    }
    if ($notVisible.Count -gt 0) {
        Stop-Setup ('Installed but not visible in this window yet: ' + ($notVisible -join ', ') + '. Open a NEW PowerShell window.') 2
    }
}

# ---- 2. Repository ----------------------------------------------------------------------------
function Initialize-Repository {
    Step "2/7 Repository at $RepoDir"
    if (Test-Path (Join-Path $RepoDir '.git')) { Say 'ok      already cloned (left as it is)' }
    elseif ($CheckOnly) { Would "git clone $RepoUrl $RepoDir" }
    else {
        New-Item -ItemType Directory -Force -Path (Split-Path $RepoDir) | Out-Null
        git clone $RepoUrl $RepoDir
        if ($LASTEXITCODE -ne 0) { Stop-Setup 'git clone failed.' }
    }
    if ($CheckOnly) { return }
    Push-Location $RepoDir
    Invoke-Python @('-m', 'pip', 'install', '--disable-pip-version-check', '-q', '-r', 'requirements-design.txt')
    $pip = $LASTEXITCODE
    git config core.hooksPath .githooks
    $hook = $LASTEXITCODE
    Pop-Location
    if ($pip -ne 0) { Stop-Setup 'pip could not install the test dependency (requirements-design.txt).' }
    if ($hook -ne 0) { Say 'WARNING: the encoding hook is not on (git config core.hooksPath .githooks). CI still checks.' }
    else { Say 'ok      test dependency and encoding hook' }
}

# ---- 3. WSL and Ubuntu ------------------------------------------------------------------------
function Install-Wsl {
    Step "3/7 WSL and $Distro"
    if ((Get-Distros) -contains $Distro) { Say "ok      $Distro is installed"; return }
    if ($CheckOnly) { Would "wsl --install -d $Distro --no-launch (administrator approval; maybe a restart)"; return }
    Say 'Windows will ask for administrator approval (UAC) to install WSL and Ubuntu.'
    try { Start-Process wsl.exe -ArgumentList @('--install', '-d', $Distro, '--no-launch') -Verb RunAs -Wait } catch { Stop-Setup 'administrator approval was declined.' }
    if ((Get-Distros) -contains $Distro) { Say "ok      $Distro installed"; return }
    $null = & wsl.exe --status 2>$null
    if ($LASTEXITCODE -eq 0) {
        # WSL works but this distribution needs its first launch to register: do it here.
        Say 'Finishing the Ubuntu install in this window.'
        & wsl.exe --install -d $Distro
        if ((Get-Distros) -contains $Distro) { Say "ok      $Distro installed"; return }
    }
    Register-Resume
    Say 'Windows must restart to finish enabling WSL. After you sign in again, this setup continues by itself.'
    if ((Read-Host '   Restart now? (y/n)') -eq 'y') { Restart-Computer }
    Stop-Setup 'restart Windows to finish WSL; the setup continues after you sign in.' 2
}

# ---- 4. Linux user ----------------------------------------------------------------------------
function New-LinuxUser {
    Step '4/7 Your Linux user'
    $uid = Get-LinuxUid
    if ($uid -and $uid -ne '0') { Say 'ok      a Linux user exists and is the default'; return }
    if ($CheckOnly) { Would 'create your Linux user (Ubuntu asks for a name and a password)'; return }
    Say 'Ubuntu will ask you for a new user name and password. They stay inside Ubuntu.'
    Say 'When you see the Ubuntu prompt ending in $, type  exit  and press Enter to continue.'
    & wsl.exe -d $Distro
    $uid = Get-LinuxUid
    if ($uid -eq '0') {
        # This Ubuntu did not run its first-run questions: create the user from root instead.
        $name = Read-Host '   Linux user name (lowercase letters, digits, - or _)'
        if ($name -notmatch '^[a-z_][a-z0-9_-]{0,31}$') { Stop-Setup 'that is not a valid Linux user name.' }
        & wsl.exe -d $Distro -u root -e useradd -m -s /bin/bash -G sudo $name
        if ($LASTEXITCODE -ne 0) { Stop-Setup "Ubuntu could not create the user $name." }
        Say "Set the password for $name (typed into Ubuntu's passwd, not seen by this script):"
        & wsl.exe -d $Distro -u root -e passwd $name
        if ($LASTEXITCODE -ne 0) { Stop-Setup "the password for $name was not set." }
        Invoke-Linux -Root "printf '\n[user]\ndefault=%s\n' '$name' >> /etc/wsl.conf"
        if ($LASTEXITCODE -ne 0) { Stop-Setup 'could not make the new user the default (/etc/wsl.conf).' }
        & wsl.exe --terminate $Distro | Out-Null
        $uid = Get-LinuxUid
    }
    if (-not $uid -or $uid -eq '0') { Stop-Setup 'no Linux user is the default yet.' }
    Say 'ok      Linux user ready'
}

# ---- 5. Packages and CLIs inside Ubuntu -------------------------------------------------------
function Install-LinuxTools {
    Step '5/7 Packages and CLIs inside Ubuntu'
    foreach ($a in $AcceptInstallerSha) {
        if ($a -notmatch '^(codex|claude)=[0-9a-f]{64}$') { Stop-Setup "-AcceptInstallerSha takes codex=<sha256> or claude=<sha256>, not '$a'." }
    }
    if ((Get-Distros) -contains $Distro -and (Test-Path (Join-Path $RepoDir 'tools\setup\setup-wsl.sh'))) {
        $script:LinuxRepo = (& wsl.exe -d $Distro -e wslpath -a $RepoDir | Out-String).Trim()
    }
    if (-not $script:LinuxRepo) {
        if ($CheckOnly) { Would 'install apt packages and the CLIs (needs the distribution and the clone first)'; return }
        Stop-Setup "Ubuntu or $RepoDir\tools\setup\setup-wsl.sh is missing."
    }
    $check = if ($CheckOnly) { ' --check' } else { '' }
    Invoke-Linux -Root "bash '$script:LinuxRepo/tools/setup/setup-wsl.sh' --apt-only$check"
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        if ($CheckOnly) { Say "WARNING: the apt check reported a problem (exit $code)." }
        else { Stop-Setup 'apt packages were not installed (see above).' }
    }
    $approve = ($AcceptInstallerSha | ForEach-Object { " --accept-installer-sha $_" }) -join ''
    Invoke-Linux "cd '$script:LinuxRepo' && bash tools/setup/setup-wsl.sh --no-final$check$approve"
    $code = $LASTEXITCODE
    if ($code -eq 0) { return }
    if ($CheckOnly) { Say "WARNING: the Ubuntu check reported a problem (exit $code)."; return }
    switch ($code) {
        3 { Stop-Setup 'an official installer is not the one approved. Read the file named above; to run exactly that file, run this again with  -AcceptInstallerSha <codex|claude>=<sha256>  using the value printed above.' }
        4 { Stop-Setup 'the observed CLI versions could not be read (see above).' }
        default { Stop-Setup "installing the CLIs failed (exit $code, see above)." }
    }
}

# ---- 6. Logins --------------------------------------------------------------------------------
function Test-GitHubLogin { $null = & gh auth status 2>$null; return ($LASTEXITCODE -eq 0) }
function Test-ClaudeLogin {
    # Same rule as check_setup.py: the status command must succeed and report the claude.ai subscription.
    $out = Invoke-Linux 'claude auth status 2>/dev/null' | Out-String
    if ($LASTEXITCODE -ne 0) { return $false }
    try { $s = $out | ConvertFrom-Json } catch { return $false }
    return ($s.loggedIn -eq $true -and $s.authMethod -eq 'claude.ai')
}
function Test-CodexLogin {
    $out = Invoke-Linux 'codex login status 2>&1' | Out-String
    return ($LASTEXITCODE -eq 0 -and $out -match 'ChatGPT')
}
function Invoke-Logins {
    Step '6/7 Logins (each one is approved in your browser)'
    if ($SkipLogin) { Say 'skipped (-SkipLogin)'; return }
    if (Test-GitHubLogin) { Say 'ok      GitHub' }
    elseif ($CheckOnly) { Would 'gh auth login --web' }
    else {
        gh auth login --web --git-protocol https --hostname github.com
        if (Test-GitHubLogin) { Say 'ok      GitHub' } else { Say 'WARNING: GitHub login is not finished.' }
    }
    if (-not $CheckOnly -and (Test-GitHubLogin) -and -not (git config --global user.name)) {
        # Commit identity from the GitHub account: the login name and GitHub's no-reply address.
        $login = (gh api user --jq .login 2>$null | Out-String).Trim()
        $id = (gh api user --jq .id 2>$null | Out-String).Trim()
        if ($login -and $id) {
            git config --global user.name $login
            git config --global user.email "$id+$login@users.noreply.github.com"
            Say "ok      git commit identity: $login (GitHub no-reply address)"
        }
    }
    if (-not $script:LinuxRepo) { return }
    if (Test-ClaudeLogin) { Say 'ok      Claude' }
    elseif ($CheckOnly) { Would 'claude auth login (inside Ubuntu)' }
    else {
        Say 'Claude login: choose the Claude subscription (claude.ai), not an API key.'
        Invoke-Linux 'claude auth login'
        if (Test-ClaudeLogin) { Say 'ok      Claude' } else { Say 'WARNING: Claude subscription login is not finished.' }
    }
    if (Test-CodexLogin) { Say 'ok      Codex' }
    elseif ($CheckOnly) { Would 'codex login (inside Ubuntu)' }
    else {
        Say 'Codex login: sign in with your ChatGPT account.'
        Invoke-Linux 'codex login'
        if (Test-CodexLogin) { Say 'ok      Codex' } else { Say 'WARNING: Codex ChatGPT login is not finished.' }
    }
}

# ---- 7. Check ---------------------------------------------------------------------------------
function Invoke-FinalCheck {
    # Sets $script:FinalCode instead of returning it. Called as a statement, the checks print straight to
    # the screen. Assigning the function's output once mixed their lines into the code, which turned
    # "not ready" into exit 0; piping them through PowerShell instead garbles their Korean text.
    Step '7/7 Check'
    $script:FinalCode = 0
    if (Test-Path (Join-Path $RepoDir 'tools\setup\check_setup.py')) {
        Push-Location $RepoDir
        Invoke-Python @('tools\setup\check_setup.py')
        if ($LASTEXITCODE -ne 0) { $script:FinalCode = 1 }
        Pop-Location
    } else { Say 'skipped on Windows: the clone is not there yet'; $script:FinalCode = 1 }
    if ($script:LinuxRepo) {
        Invoke-Linux "cd '$script:LinuxRepo' && python3 tools/setup/check_setup.py"
        if ($LASTEXITCODE -ne 0) { $script:FinalCode = 1 }
    } elseif (-not $CheckOnly) { $script:FinalCode = 1 }
}

function Invoke-Setup {
    try { Start-Transcript -Path $script:Log -Append | Out-Null } catch {}
    Write-Host 'decision-model_lab one-touch setup' -ForegroundColor Cyan
    if ($CheckOnly) { Say 'check only: nothing will be installed or changed' }
    if ($Resume) { Say 'continuing after the restart' }
    if ($RepoDir -like "$env:LOCALAPPDATA*") { Stop-Setup 'choose a folder outside AppData for -RepoDir (see docs/SETUP.md, trap 1).' }
    Install-WindowsTools
    Initialize-Repository
    Install-Wsl
    New-LinuxUser
    Install-LinuxTools
    Invoke-Logins
    Invoke-FinalCheck
    $code = [int]$script:FinalCode
    Write-Host ''
    if ($code -eq 0) {
        Write-Host 'Setup is complete: tools, Ubuntu, CLIs and subscription logins are ready.' -ForegroundColor Green
        Write-Host 'Strict runs still need this machine''s own observation (docs/SETUP.md section 4). Next: NEXT-SESSION.md.'
    } else {
        Write-Host "Some required items are not ready (see above). Fix them and run the same command again. Log: $script:Log" -ForegroundColor Yellow
    }
    try { Stop-Transcript | Out-Null } catch {}
    exit $code
}

# Tests dot-source this file with DML_SETUP_AS_LIBRARY=1 to call one step with stand-in commands.
if ($env:DML_SETUP_AS_LIBRARY -ne '1') { Invoke-Setup }
