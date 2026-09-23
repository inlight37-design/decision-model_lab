# Show where each CLI resolves on PATH, its version and its signer. Runs --version only.
# Run it through fresh-shell.ps1 so PATH comes from the registry, not a stale shell.
foreach ($c in 'claude', 'codex', 'agy', 'gemini') {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if (-not $cmd) { "{0}: not on PATH" -f $c; continue }
    # Collect all output first: Select-Object -First would stop the pipe and report exit -1.
    $all = @(& $c --version 2>&1)
    $code = $LASTEXITCODE
    # The subject alone is not a check: record whether Windows reports the signature Valid.
    $sig = Get-AuthenticodeSignature $cmd.Source
    $signer = ($sig.SignerCertificate.Subject -split ',')[0]
    "{0}: {1} | exit={2} | {3} | {4} | signature={5}" -f $c, ($cmd.Source -replace [regex]::Escape($env:USERPROFILE), '~'), $code, $all[0], $signer, $sig.Status
}
# Files an agent creates under AppData from inside the Claude desktop app (MSIX) can
# land in the app's private store and be invisible to the user's own terminal.
$store = Join-Path $env:LOCALAPPDATA 'Packages\Claude_pzs8sxrjxfjjc\LocalCache\Local'
if (Test-Path $store) {
    $names = (Get-ChildItem $store -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -notin 'Claude', 'Microsoft' }).Name
    if ($names) { "WARNING: found in the Claude app's private AppData store (invisible outside the app): " + ($names -join ', ') }
}
