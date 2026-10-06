param(
    [string]$Root = ".",
    [string]$Device = "ce679eed",
    [string]$StorePass = "Kneekura1234",
    [string]$Alias = "kneekura",
    [int]$WaitSeconds = 20
)

$ErrorActionPreference = "Stop"

function Resolve-Exe {
    param([string]$Name, [string[]]$Candidates = @())
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($candidate in $Candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return (Resolve-Path $candidate).Path
        }
    }
    throw "Required executable not found: $Name"
}

$Root = (Resolve-Path $Root).Path
Set-Location $Root

$python = Resolve-Exe "python.exe" @()
$adb = Resolve-Exe "adb.exe" @("$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe")
$javac = Resolve-Exe "javac.exe" @("C:\Program Files\Android\Android Studio\jbr\bin\javac.exe")

if (-not $env:ANDROID_HOME) {
    $env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
}
$env:ANDROID_SDK_ROOT = $env:ANDROID_HOME

$exportZip = Join-Path $Root "nyanko_battlecats_2026-10-06.zip"
$shim = Join-Path $Root "libkneekura.so"
$keystore = Join-Path $Root "private\kneekura.p12"

foreach ($required in @($exportZip, $shim, $keystore)) {
    if (-not (Test-Path $required)) {
        throw "Required file missing: $required"
    }
}

& $adb -s $Device get-state | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "ADB device is not ready: $Device"
}

$out = Join-Path $Root "static-http-out"
if (Test-Path $out) {
    Remove-Item $out -Recurse -Force
}

Write-Host "[1/6] Building Frida-free static HTTP bridge..."
$buildArgs = @(
    "-m", "tools.base_mod.build_owned_static_http_bridge",
    $exportZip,
    "--flavor", "research",
    "--shim", $shim,
    "--keystore", $keystore,
    "--alias", $Alias,
    "--storepass", $StorePass,
    "--enable-backup-offline-replay",
    "--javac", $javac,
    "--output", $out
)
& $python @buildArgs
if ($LASTEXITCODE -ne 0) {
    throw "Static bridge build failed"
}

$signed = Join-Path $out "research-static-http-signed-splits"
$parity = Join-Path $signed "parity-report.json"
if (-not (Test-Path $parity)) {
    throw "Parity report missing: $parity"
}

$report = Get-Content $parity -Raw | ConvertFrom-Json
$requiredTrue = @(
    "original_new_http_code_preserved",
    "request_constructor_anchor_preserved",
    "offline_fallback_anchor_preserved",
    "unknown_request_super_fallthrough",
    "shim_dependency_present",
    "frida_absent"
)
foreach ($key in $requiredTrue) {
    if (-not $report.$key) {
        throw "Parity gate failed: $key"
    }
}

Write-Host "[2/6] Parity PASS"

$installDir = "C:\KneekuraStaticSmokeInstall"
New-Item -ItemType Directory -Force $installDir | Out-Null
Remove-Item "$installDir\*.apk" -Force -ErrorAction SilentlyContinue
Copy-Item "$signed\*.apk" $installDir -Force
$apks = @(Get-ChildItem "$installDir\*.apk" | Sort-Object Name | ForEach-Object { $_.FullName })

if ($apks.Count -ne 6) {
    throw "Expected 6 split APKs, found $($apks.Count)"
}

Write-Host "[3/6] Replacing research package..."
& $adb -s $Device uninstall jp.kn.trace.battlecats 2>$null | Out-Null

$installArgs = @("-s", $Device, "install-multiple", "--no-streaming", "-r") + $apks
& $adb @installArgs
if ($LASTEXITCODE -ne 0) {
    throw "APK installation failed"
}

Write-Host "[4/6] Launching Frida-free bridge..."
& $adb -s $Device logcat -c
& $adb -s $Device shell am start -n "jp.kn.trace.battlecats/jp.kn.trace.battlecats.MyActivity"
if ($LASTEXITCODE -ne 0) {
    throw "Activity launch failed"
}

Start-Sleep -Seconds $WaitSeconds

Write-Host "[5/6] Checking process..."
$pidText = (& $adb -s $Device shell pidof jp.kn.trace.battlecats).Trim()
if (-not $pidText) {
    throw "Research package is not alive after launch"
}
Write-Host "PID: $pidText"

$log = & $adb -s $Device logcat -d
$selected = @($log | Select-String -Pattern "KNEEKURA_STATIC_HTTP","Frida","FATAL EXCEPTION","Fatal signal")

$logPath = Join-Path $out "static-http-smoke-log.txt"
$selected | ForEach-Object { $_.Line } | Set-Content $logPath -Encoding UTF8

$replay = @($selected | Where-Object { $_.Line -match "KNEEKURA_STATIC_HTTP.*backup-local-replay requestId=" })
$frida = @($selected | Where-Object { $_.Line -match "Frida" })
$fatal = @($selected | Where-Object { $_.Line -match "FATAL EXCEPTION|Fatal signal" })

Write-Host "[6/6] Smoke result"
if ($selected.Count -gt 0) {
    $selected | ForEach-Object { Write-Host $_.Line }
} else {
    Write-Host "(no selected logcat lines)"
}

$result = [ordered]@{
    package_alive = $true
    pid = $pidText
    local_replay_seen = ($replay.Count -gt 0)
    frida_seen = ($frida.Count -gt 0)
    fatal_seen = ($fatal.Count -gt 0)
    parity_report = $parity
    smoke_log = $logPath
}
$resultPath = Join-Path $out "static-http-smoke-result.json"
$result | ConvertTo-Json -Depth 5 | Set-Content $resultPath -Encoding UTF8

Write-Host ""
Write-Host "Result:"
Write-Host ($result | ConvertTo-Json -Depth 5)
Write-Host ""
Write-Host "Return these two files only:"
Write-Host "  $parity"
Write-Host "  $resultPath"

if (($frida.Count -gt 0) -or ($fatal.Count -gt 0) -or ($replay.Count -eq 0)) {
    exit 2
}
exit 0
