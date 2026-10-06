param(
    [string]$Root = ".",
    [string]$Device = "",
    [string]$StorePass = "",
    [string]$Alias = "kneekura",
    [int]$WaitSeconds = 20,
    [switch]$Clean
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

function Read-YesNo {
    param([string]$Prompt)
    while ($true) {
        $answer = (Read-Host "$Prompt [y/n]").Trim().ToLowerInvariant()
        if ($answer -in @("y", "yes")) { return $true }
        if ($answer -in @("n", "no")) { return $false }
    }
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

if (-not $Device) {
    $deviceLines = @(& $adb devices | Select-Object -Skip 1 | Where-Object {
        $_ -match "\sdevice\s*$"
    })
    $deviceIds = @($deviceLines | ForEach-Object { ($_ -split "\s+")[0] })
    if ($deviceIds.Count -ne 1) {
        throw "Expected exactly one authorized ADB device; found $($deviceIds.Count). Pass -Device explicitly if needed."
    }
    $Device = $deviceIds[0]
}

if (-not $StorePass) {
    if ($env:KNEEKURA_STOREPASS) {
        $StorePass = $env:KNEEKURA_STOREPASS
    } else {
        $secure = Read-Host "Kneekura keystore password" -AsSecureString
        $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
        try {
            $StorePass = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
        } finally {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
        }
    }
}
if (-not $StorePass) {
    throw "Keystore password is required"
}

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

$out = Join-Path $Root "phase-c-final-out"
if ($Clean -and (Test-Path $out)) {
    Remove-Item $out -Recurse -Force
}
New-Item -ItemType Directory -Force $out | Out-Null

$personalSigned = Join-Path $out "personal\personal-signed-splits"
$personalReport = Join-Path $out "personal-shipping-parity.json"

Write-Host "[1/9] Preparing Personal feature-OFF shipping profile..."
if (-not (Test-Path (Join-Path $personalSigned "parity-report.json"))) {
    $personalArgs = @(
        "-m", "tools.base_mod.build_owned_boot_smoke",
        $exportZip,
        "--flavor", "personal",
        "--shim", $shim,
        "--keystore", $keystore,
        "--alias", $Alias,
        "--storepass", $StorePass,
        "--output", (Join-Path $out "personal")
    )
    & $python @personalArgs
    if ($LASTEXITCODE -ne 0) { throw "Personal build failed" }
} else {
    Write-Host "Reusing existing Personal signed splits."
}

Write-Host "[2/9] Auditing Personal shipping profile..."
& $python -m tools.base_mod.verify_shipping_profile $personalSigned --flavor personal --output $personalReport
if ($LASTEXITCODE -ne 0) { throw "Personal shipping parity failed" }

$practiceSigned = Join-Path $out "practice\practice-signed-splits"
$practiceReport = Join-Path $out "practice-shipping-parity.json"

Write-Host "[3/9] Preparing Practice feature-OFF shipping profile..."
if (-not (Test-Path (Join-Path $practiceSigned "parity-report.json"))) {
    $practiceArgs = @(
        "-m", "tools.base_mod.build_owned_boot_smoke",
        $exportZip,
        "--flavor", "practice",
        "--shim", $shim,
        "--keystore", $keystore,
        "--alias", $Alias,
        "--storepass", $StorePass,
        "--output", (Join-Path $out "practice")
    )
    & $python @practiceArgs
    if ($LASTEXITCODE -ne 0) { throw "Practice build failed" }
} else {
    Write-Host "Reusing existing Practice signed splits."
}

Write-Host "[4/9] Auditing Practice shipping profile..."
& $python -m tools.base_mod.verify_shipping_profile $practiceSigned --flavor practice --output $practiceReport
if ($LASTEXITCODE -ne 0) { throw "Practice shipping parity failed" }

Write-Host "[5/9] Preparing exact set-1089 original-UI gacha proof..."
$gachaOut = Join-Path $out "gacha-ui-proof"
$gachaSigned = Join-Path $gachaOut "research-gacha-ui-proof-signed-splits"
$existingBridgeLedger = Join-Path $gachaSigned "http-bridge-build-ledger.json"
$needGachaBuild = $true

if (-not $Clean -and (Test-Path $existingBridgeLedger)) {
    try {
        $existingBridge = Get-Content $existingBridgeLedger -Raw | ConvertFrom-Json
        if ($existingBridge.use_external_files_dir -eq $true) {
            $needGachaBuild = $false
            Write-Host "Reusing gacha proof with research external-files cache mode."
        }
    } catch {
        $needGachaBuild = $true
    }
}

if ($needGachaBuild) {
    if (Test-Path $gachaOut) {
        Remove-Item $gachaOut -Recurse -Force
    }
    $gachaArgs = @(
        "-m", "tools.base_mod.build_owned_gacha_ui_proof",
        $exportZip,
        "--shim", $shim,
        "--keystore", $keystore,
        "--alias", $Alias,
        "--storepass", $StorePass,
        "--javac", $javac,
        "--output", $gachaOut
    )
    & $python @gachaArgs
    if ($LASTEXITCODE -ne 0) { throw "Gacha UI proof build failed" }
}

$proofLedger = Join-Path $gachaSigned "gacha-ui-proof-ledger.json"
$dataProof = Join-Path $gachaSigned "gacha-data-proof-report.json"
if (-not (Test-Path $proofLedger) -or -not (Test-Path $dataProof)) {
    throw "Gacha proof reports are missing"
}

$proof = Get-Content $proofLedger -Raw | ConvertFrom-Json
if ($proof.new_set_id -ne 1089) { throw "Gacha proof set id drift" }
if (($proof.prototype_unit_ids -join ",") -ne "37,30,34") {
    throw "Gacha proof unit selection drift"
}
if ($proof.clone_option_set -ne 49) { throw "Gacha option clone drift" }
if (-not $proof.data_rows_verified_append_only) { throw "Gacha append-only verification failed" }
if ($proof.frida_absent -ne $true) { throw "Frida leaked into gacha proof" }
if ($proof.research_external_files_dir -ne $true) {
    throw "Research gacha proof is missing external-files cache mode"
}

Write-Host "[6/9] Auditing the original 615 MiB server-asset gate..."
$downloadGateReport = Join-Path $out "server-download-gate-report.json"
$gateArgs = @(
    "-m", "tools.base_mod.analyze_server_download_gate",
    $exportZip,
    "--output", $downloadGateReport
)
& $python @gateArgs
if ($LASTEXITCODE -ne 0) { throw "Server download gate audit failed" }
$downloadGate = Get-Content $downloadGateReport -Raw | ConvertFrom-Json
if ($downloadGate.conclusion.matches_615_mib_prompt -ne $true) {
    throw "Exact download tables no longer match the observed 615 MiB gate"
}
Write-Host ("Exact original download tables: {0} lanes, {1:N2} MiB." -f $downloadGate.download_lane_count, $downloadGate.total_archive_mib)

Write-Host "[7/9] Installing/updating isolated research gacha proof..."
$installDir = "C:\KneekuraGachaProofInstall"
New-Item -ItemType Directory -Force $installDir | Out-Null
Remove-Item "$installDir\*.apk" -Force -ErrorAction SilentlyContinue
Copy-Item "$gachaSigned\*.apk" $installDir -Force
$apks = @(Get-ChildItem "$installDir\*.apk" | Sort-Object Name | ForEach-Object { $_.FullName })
if ($apks.Count -ne 6) {
    throw "Expected six gacha-proof split APKs, found $($apks.Count)"
}

# Intentionally do not uninstall. The same owner-controlled signing key allows
# an in-place -r upgrade, preserving the original downloader's local cache.
$installArgs = @("-s", $Device, "install-multiple", "--no-streaming", "-r") + $apks
& $adb @installArgs
if ($LASTEXITCODE -ne 0) { throw "Gacha proof APK installation failed" }

Write-Host "[8/9] Launching original Battle Cats scene host..."
& $adb -s $Device logcat -c
& $adb -s $Device shell am start -n "jp.kn.trace.battlecats/jp.kn.trace.battlecats.MyActivity"
if ($LASTEXITCODE -ne 0) { throw "Gacha proof Activity launch failed" }
Start-Sleep -Seconds $WaitSeconds

$pidText = (& $adb -s $Device shell pidof jp.kn.trace.battlecats).Trim()
if (-not $pidText) {
    throw "Research gacha proof package is not alive"
}

$log = & $adb -s $Device logcat -d
$selected = @($log | Select-String -Pattern "Frida","FATAL EXCEPTION","Fatal signal","KNEEKURA_STATIC_HTTP")
$frida = @($selected | Where-Object { $_.Line -match "Frida" })
$fatal = @($selected | Where-Object { $_.Line -match "FATAL EXCEPTION|Fatal signal" })
$replay = @($selected | Where-Object { $_.Line -match "KNEEKURA_STATIC_HTTP.*backup-local-replay" })
$externalDirMarker = @($selected | Where-Object { $_.Line -match "KNEEKURA_STATIC_HTTP.*external-files-dir active" })

$logPath = Join-Path $out "gacha-ui-proof-smoke-log.txt"
$selected | ForEach-Object { $_.Line } | Set-Content $logPath -Encoding UTF8

if ($frida.Count -gt 0) { throw "Frida marker appeared in final proof" }
if ($fatal.Count -gt 0) { throw "Fatal Android marker appeared in final proof" }

Write-Host ""
Write-Host "[9/9] Original downloader + original-UI check"
Write-Host "The isolated research flavor now maps getFilesDir() to its own app-specific"
Write-Host "external files directory. Personal/Practice shipping profiles are unchanged."
Write-Host ""

$downloadGateSeen = Read-YesNo "Is the additional game-data download screen currently blocking the normal game UI?"
$originalDownloadAttempted = $false
$originalDownloadCompleted = $false

if ($downloadGateSeen) {
    Write-Host ""
    Write-Host ("Static evidence proves this is the original {0}-lane server asset bootstrap ({1:N2} MiB)." -f $downloadGate.download_lane_count, $downloadGate.total_archive_mib)
    Write-Host "It is not evidence about gacha scheduling."
    $originalDownloadAttempted = Read-YesNo "Do you want to let the unchanged original Battle Cats downloader complete this one-time download now?"
    if ($originalDownloadAttempted) {
        Write-Host ""
        Write-Host "On the phone, press the ORIGINAL download button and wait until it finishes."
        Write-Host "Do not close this PowerShell window."
        [void](Read-Host "When the download has finished and the app has left the download screen, press Enter here")
        Start-Sleep -Seconds 3
        $afterDownloadPid = (& $adb -s $Device shell pidof jp.kn.trace.battlecats).Trim()
        if (-not $afterDownloadPid) {
            throw "Research package exited during the original server-asset download"
        }
        $originalDownloadCompleted = -not (Read-YesNo "Is the additional download screen still blocking the app?")
    }
}

$externalFilesPath = "/sdcard/Android/data/jp.kn.trace.battlecats/files"
$externalFileCount = $null
$externalCacheKiB = $null
try {
    $externalFileCount = (& $adb -s $Device shell "find $externalFilesPath -type f 2>/dev/null | wc -l").Trim()
    $externalCacheKiB = (& $adb -s $Device shell "du -sk $externalFilesPath 2>/dev/null | cut -f1").Trim()
} catch {
    # Supplemental evidence only.
}

$originalUiOk = $false
$extraBanner = $null
if (-not $downloadGateSeen -or $originalDownloadCompleted) {
    Write-Host ""
    Write-Host "Open the normal Battle Cats Rare Gacha screen."
    Write-Host "Do not perform a draw yet."
    Write-Host "The proof appends set 1089 using the original Rare Gacha tables."
    Write-Host "Its banner metadata clones original visible set 49, so it may look like an existing banner."
    $originalUiOk = Read-YesNo "Did the normal Battle Cats Rare Gacha screen open without a custom Kneekura screen or crash?"
    if ($originalUiOk) {
        $extraBanner = Read-YesNo "Did you observe an additional/duplicated Rare Gacha banner after installing the proof?"
    }
}

$runtimeClassification = if ($downloadGateSeen -and -not $originalDownloadCompleted) {
    "server_asset_download_gate"
} elseif (-not $originalUiOk) {
    "original_ui_not_reached"
} elseif (-not $extraBanner) {
    "gacha_visibility_schedule_not_exposed"
} else {
    "original_ui_set_visible"
}

$result = [ordered]@{
    schema_version = 2
    package_alive = $true
    pid = $pidText
    personal_shipping_parity = $true
    practice_shipping_parity = $true
    personal_frida_absent = $true
    practice_frida_absent = $true
    gacha_proof_set_id = 1089
    gacha_proof_units = @(37, 30, 34)
    gacha_clone_option_set = 49
    gacha_rows_append_only = $true
    research_external_files_dir = $true
    research_frida_seen = ($frida.Count -gt 0)
    fatal_seen = ($fatal.Count -gt 0)
    backup_local_replay_seen = ($replay.Count -gt 0)
    external_files_dir_marker_seen = ($externalDirMarker.Count -gt 0)
    additional_download_gate_seen = $downloadGateSeen
    original_download_attempted = $originalDownloadAttempted
    original_download_completed = $originalDownloadCompleted
    exact_download_lane_count = $downloadGate.download_lane_count
    exact_download_archive_bytes = $downloadGate.total_archive_bytes
    exact_download_archive_mib = $downloadGate.total_archive_mib
    external_files_path = $externalFilesPath
    external_file_count = $externalFileCount
    external_cache_kib = $externalCacheKiB
    original_rare_gacha_ui_opened = $originalUiOk
    appended_banner_visible = $extraBanner
    schedule_provider_required = if ($originalUiOk) { -not $extraBanner } else { $null }
    runtime_gate_classification = $runtimeClassification
    personal_report = $personalReport
    practice_report = $practiceReport
    gacha_proof_ledger = $proofLedger
    gacha_data_proof = $dataProof
    server_download_gate_report = $downloadGateReport
    smoke_log = $logPath
}

$resultPath = Join-Path $out "phase-c-final-result.json"
$result | ConvertTo-Json -Depth 6 | Set-Content $resultPath -Encoding UTF8

Write-Host ""
Write-Host "Final result:"
Write-Host ($result | ConvertTo-Json -Depth 6)
Write-Host ""
Write-Host "Return this file:"
Write-Host "  $resultPath"

if ($runtimeClassification -eq "server_asset_download_gate") {
    Write-Host ""
    Write-Host "Static/data proof PASS, but the original server-asset bootstrap is still incomplete."
    Write-Host "This is not a gacha schedule failure."
    exit 5
}
if (-not $originalUiOk) {
    exit 3
}
if (-not $extraBanner) {
    Write-Host ""
    Write-Host "Original Rare Gacha UI reached, but set 1089 was not exposed."
    Write-Host "Only now is a narrow local gacha-visibility schedule provider indicated."
    exit 4
}
exit 0
