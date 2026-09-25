# Opens the Decision Lab app with one click: starts the screen server inside WSL (app/launch.py) and
# shows it in its own window (a Microsoft Edge app window with a dedicated profile). Closing that window
# asks the server to stop; it stops as soon as no participant or synthesis is running, so closing the
# window never cuts a model call short. The server, readiness check, ledger, caps and sealing are
# app.server's own; app/launch.py only picks the observation record, the models and the ledger.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File app\start.ps1                   # Codex + Claude (subscription CLIs)
#   powershell -NoProfile -ExecutionPolicy Bypass -File app\start.ps1 -Mock             # no model calls
#   powershell -NoProfile -ExecutionPolicy Bypass -File app\start.ps1 -InstallShortcut  # desktop icon for this copy
#
# If the real mode is refused (for example the observation record expired), it says why and offers the
# mock mode; it never falls back silently. Exit codes: 0 opened and closed, 1 failed, 3 refused.
# ASCII only: Windows PowerShell 5.1 reads BOM-less UTF-8 scripts as ANSI, so the Korean messages below
# are \u escapes (read with [regex]::Unescape).
param(
    [switch]$Mock,
    [switch]$InstallShortcut,
    [string]$Distro = 'Ubuntu-24.04'
)

$Repo = Split-Path -Parent $PSScriptRoot
$AppHome = Join-Path $env:USERPROFILE '.decision-model-lab'     # outside AppData on purpose (docs/SETUP.md trap 1)
$EdgeProfile = Join-Path $AppHome 'edge-app'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false
Add-Type -AssemblyName System.Windows.Forms, System.Drawing

$Text = @{
    OPENING = 'Decision Lab\uC744 \uC5EC\uB294 \uC911\uC785\uB2C8\uB2E4\u2026'
    NO_WSL = 'WSL\uC758 Ubuntu\uC5D0\uC11C \uC571\uC744 \uBD80\uB974\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4.\n\n\uCC98\uC74C\uC774\uBA74 docs\\SETUP.md\uC758 \uD55C \uC904 \uC124\uCE58\uB97C \uBA3C\uC800 \uD558\uC138\uC694. \uC774\uBBF8 \uD588\uB2E4\uBA74 \uCEF4\uD4E8\uD130\uB97C \uB2E4\uC2DC \uCF20 \uB4A4 \uB2E4\uC2DC \uC5F4\uC5B4 \uBCF4\uC138\uC694.'
    REFUSED = '\uC2E4\uC81C \uBAA8\uB4DC(Codex\u00B7Claude)\uB97C \uC5F4 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4.\n\n{0}\n\n\uBAA8\uB378\uC744 \uBD80\uB974\uC9C0 \uC54A\uB294 \uBAA8\uC758 \uBAA8\uB4DC\uB85C \uC5F4\uAE4C\uC694?'
    FAILED = '\uC571\uC744 \uC5F4\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4.\n\n{0}\n\n\uC790\uC138\uD55C \uAE30\uB85D: WSL\uC758 ~/.local/state/decision-model-lab/app/server.log'
    NO_EDGE = '\uC571\uC744 \uAE30\uBCF8 \uBE0C\uB77C\uC6B0\uC800\uC5D0\uC11C \uC5F4\uC5C8\uC2B5\uB2C8\uB2E4.\n\n\uB2E4 \uC4F4 \uB4A4 \uC774 \uCC3D\uC758 [\uD655\uC778]\uC744 \uB204\uB974\uBA74 \uC571\uC744 \uB055\uB2C8\uB2E4.'
    WAITING = '\uC9C4\uD589 \uC911\uC778 \uD638\uCD9C\uC774 \uB05D\uB098\uBA74 \uC571\uC774 \uC2A4\uC2A4\uB85C \uAEBC\uC9D1\uB2C8\uB2E4.'
    UNSETTLED = '\uB05D\uB0AC\uB294\uC9C0 \uD655\uC778\uD558\uC9C0 \uBABB\uD55C \uC791\uC5C5\uC774 \uB0A8\uC558\uC2B5\uB2C8\uB2E4. \uC6D0\uC7A5\uC740 \uADF8\uB300\uB85C \uC788\uACE0, \uB2E4\uC74C\uC5D0 \uC5F4\uBA74 \uD654\uBA74\uC5D0\uC11C \uD655\uC778\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4.'
    SHORTCUT = '\uBC14\uD0D5 \uD654\uBA74\uC5D0 ''Decision Lab'' \uC544\uC774\uCF58\uC744 \uB9CC\uB4E4\uC5C8\uC2B5\uB2C8\uB2E4.\n\n{0}'
    RUNNING = 'Decision Lab\uC774 \uCF1C\uC838 \uC788\uC2B5\uB2C8\uB2E4. \uC571 \uCC3D\uC744 \uB2EB\uC73C\uBA74 \uAEBC\uC9D1\uB2C8\uB2E4.'
}
function T([string]$key) { [regex]::Unescape($Text[$key]) }

function Say([string]$message, [string]$buttons = 'OK', [string]$icon = 'Information') {
    $owner = New-Object System.Windows.Forms.Form -Property @{ TopMost = $true }
    try { return [System.Windows.Forms.MessageBox]::Show($owner, $message, 'Decision Lab', $buttons, $icon) }
    finally { $owner.Dispose() }
}

# One app.launch command inside WSL; returns its last JSON line as an object, or $null.
function Launch([string]$command) {
    $lines = & wsl.exe -d $Distro --cd $Repo -- bash -lc "python3 -m app.launch $command"
    $json = @($lines | Where-Object { $_ -match '^\s*\{' }) | Select-Object -Last 1
    if ($json) { return ($json | ConvertFrom-Json) }
    return $null
}

function Find-Edge {
    foreach ($path in @("${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
                        "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe")) {
        if ($path -and (Test-Path $path)) { return $path }
    }
    $found = Get-Command msedge.exe -ErrorAction SilentlyContinue
    if ($found) { return $found.Source }
    return $null
}

# Edge processes of our dedicated profile: the app windows and their helpers.
function App-Windows {
    @(Get-CimInstance Win32_Process -Filter "Name='msedge.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -and $_.CommandLine.Contains($EdgeProfile) })
}

function Write-AppIcon([string]$path) {
    # A 256 px PNG inside an .ico container (Windows Vista and later read PNG icons).
    $bitmap = New-Object System.Drawing.Bitmap 256, 256
    $g = [System.Drawing.Graphics]::FromImage($bitmap)
    $g.SmoothingMode = 'AntiAlias'
    $g.TextRenderingHint = 'AntiAliasGridFit'
    $g.Clear([System.Drawing.Color]::Transparent)
    $g.FillEllipse((New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(51, 81, 140))), 8, 8, 240, 240)
    $font = New-Object System.Drawing.Font 'Segoe UI', 92, ([System.Drawing.FontStyle]::Bold), ([System.Drawing.GraphicsUnit]::Pixel)
    $format = New-Object System.Drawing.StringFormat
    $format.Alignment = 'Center'
    $format.LineAlignment = 'Center'
    $g.DrawString('DL', $font, [System.Drawing.Brushes]::White, (New-Object System.Drawing.RectangleF 0, 6, 256, 256), $format)
    $g.Dispose()
    $png = New-Object System.IO.MemoryStream
    $bitmap.Save($png, [System.Drawing.Imaging.ImageFormat]::Png)
    $bitmap.Dispose()
    $bytes = $png.ToArray()
    $writer = New-Object System.IO.BinaryWriter ([System.IO.File]::Create($path))
    try {
        $writer.Write([UInt16]0); $writer.Write([UInt16]1); $writer.Write([UInt16]1)          # icon directory, one image
        $writer.Write([byte]0); $writer.Write([byte]0); $writer.Write([byte]0); $writer.Write([byte]0)  # 256x256
        $writer.Write([UInt16]1); $writer.Write([UInt16]32); $writer.Write([UInt32]$bytes.Length); $writer.Write([UInt32]22)
        $writer.Write($bytes)
    } finally { $writer.Close() }
}

if ($InstallShortcut) {
    New-Item -ItemType Directory -Force -Path $AppHome | Out-Null
    $icon = Join-Path $AppHome 'app.ico'
    Write-AppIcon $icon
    $link = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Decision Lab.lnk'
    $shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut($link)
    $shortcut.TargetPath = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$PSCommandPath`""
    $shortcut.WorkingDirectory = $Repo
    $shortcut.IconLocation = "$icon,0"
    $shortcut.Description = 'Decision Lab'
    $shortcut.Save()
    Write-Output $link
    exit 0
}

$tray = New-Object System.Windows.Forms.NotifyIcon
$tray.Icon = [System.Drawing.SystemIcons]::Information
$tray.Text = 'Decision Lab'
$tray.Visible = $true
$tray.ShowBalloonTip(4000, 'Decision Lab', (T 'OPENING'), 'Info')
try {
    $status = Launch 'status'
    if ($null -eq $status) { Say (T 'NO_WSL') 'OK' 'Error' | Out-Null; exit 1 }

    $owner = $true        # this copy of the script stops the server when the window closes
    if ($status.running) {
        if ($status.stop_requested) { Launch 'cancel-stop' | Out-Null }
        $opened = Launch 'url --wait 10'
        if ((App-Windows).Count -gt 0) { $owner = $false }   # an earlier copy is already watching the window
    } else {
        $nonce = [guid]::NewGuid().ToString('N')
        $flag = ''
        if ($Mock) { $flag = '--mock' }
        $serve = @('-d', $Distro, '--cd', "`"$Repo`"", '--', 'bash', '-lc', "`"python3 -m app.launch serve $flag --nonce $nonce`"")
        Start-Process -FilePath 'wsl.exe' -ArgumentList $serve -WindowStyle Hidden | Out-Null
        $opened = Launch "url --wait 120 --nonce $nonce"
    }

    if ($null -eq $opened -or -not $opened.ok) {
        $reasons = 'no answer from WSL'
        if ($opened -and $opened.reasons) { $reasons = ($opened.reasons -join "`n") }
        if ($opened -and $opened.status -eq 'refused' -and -not $Mock) {
            if ((Say ((T 'REFUSED') -f $reasons) 'YesNo' 'Warning') -eq 'Yes') {
                $tray.Dispose()
                & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $PSCommandPath -Mock -Distro $Distro
                exit $LASTEXITCODE
            }
            exit 3
        }
        Say ((T 'FAILED') -f $reasons) 'OK' 'Error' | Out-Null
        exit 1
    }

    $edge = Find-Edge
    if ($edge) {
        New-Item -ItemType Directory -Force -Path $EdgeProfile | Out-Null
        $edgeArgs = @("--app=$($opened.url)", "--user-data-dir=`"$EdgeProfile`"", '--no-first-run',
                      '--no-default-browser-check', '--window-size=1320,900')
        Start-Process -FilePath $edge -ArgumentList $edgeArgs | Out-Null
    } else {
        Start-Process $opened.url | Out-Null
    }
    if (-not $owner) { exit 0 }

    $tray.Text = 'Decision Lab'
    $tray.ShowBalloonTip(4000, 'Decision Lab', (T 'RUNNING'), 'Info')
    $appeared = $false
    if ($edge) {
        $deadline = (Get-Date).AddSeconds(20)
        while (-not $appeared -and (Get-Date) -lt $deadline) {
            Start-Sleep -Milliseconds 500
            $appeared = (App-Windows).Count -gt 0
        }
    }
    if ($appeared) {
        while ((App-Windows).Count -gt 0) { Start-Sleep -Seconds 2 }
    } else {
        Say (T 'NO_EDGE') | Out-Null
    }

    $stopped = Launch 'stop --wait 20'
    if ($stopped -and $stopped.waiting_for_work) {
        $tray.ShowBalloonTip(5000, 'Decision Lab', (T 'WAITING'), 'Info')
        Start-Sleep -Seconds 5
    } elseif ($stopped -and $stopped.was_running -and $stopped.exit_code -ne 0) {
        Say (T 'UNSETTLED') 'OK' 'Warning' | Out-Null
    }
    exit 0
} finally {
    $tray.Dispose()
}
