param(
    [string]$Root = ".",
    [string]$Device = "",
    [string]$StorePass = "",
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
if (Test-Path $out) {
    Remove-Item $out -Recurse -Force
}
New-Item -ItemType Directory -Force $out | Out-Null

Write-Host "[1/8] Building Personal feature-OFF shipping profile..."
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

Write-Host "[2/8] Auditing Personal shipping profile..."
$personalSigned = Join-Path $out "personal\personal-signed-splits"
$personalReport = Join-Path $out "personal-shipping-parity.json"
& $python -m tools.base_mod.verify_shipping_profile $personalSigned --flavor personal --output $personalReport
if ($LASTEXITCODE -ne 0) { throw "Personal shipping parity failed" }

Write-Host "[3/8] Building Practice feature-OFF shipping profile..."
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

Write-Host "[4/8] Auditing Practice shipping profile..."
$practiceSigned = Join-Path $out "practice\practice-signed-splits"
$practiceReport = Join-Path $out "practice-shipping-parity.json"
& $python -m tools.base_mod.verify_shipping_profile $practiceSigned --flavor practice --output $practiceReport
if ($LASTEXITCODE -ne 0) { throw "Practice shipping parity failed" }

Write-Host "[5/8] Building exact set-1089 original-UI gacha proof..."
$gachaOut = Join-Path $out "gacha-ui-proof"
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

$gachaSigned = Join-Path $gachaOut "research-gacha-ui-proof-signed-splits"
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

Write-Host "[6/8] Installing isolated research gacha proof..."
$installDir = "C:\KneekuraGachaProofInstall"
New-Item -ItemType Directory -Force $installDir | Out-Null
Remove-Item "$installDir\*.apk" -Force -ErrorAction SilentlyContinue
Copy-Item "$gachaSigned\*.apk" $installDir -Force
$apks = @(Get-ChildItem "$installDir\*.apk" | Sort-Object Name | ForEach-Object { $_.FullName })
if ($apks.Count -ne 6) {
    throw "Expected six gacha-proof split APKs, found $($apks.Count)"
}

& $adb -s $Device uninstall jp.kn.trace.battlecats 2>$null | Out-Null
$installArgs = @("-s", $Device, "install-multiple", "--no-streaming", "-r") + $apks
& $adb @installArgs
if ($LASTEXITCODE -ne 0) { throw "Gacha proof APK installation failed" }

Write-Host "[7/8] Launching original Battle Cats scene host..."
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

$logPath = Join-Path $out "gacha-ui-proof-smoke-log.txt"
$selected | ForEach-Object { $_.Line } | Set-Content $logPath -Encoding UTF8

if ($frida.Count -gt 0) { throw "Frida marker appeared in final proof" }
if ($fatal.Count -gt 0) { throw "Fatal Android marker appeared in final proof" }

Write-Host ""
Write-Host "[8/8] One manual original-UI check"
Write-Host "On the phone, open the normal Rare Gacha screen."
Write-Host "Do not perform a draw yet."
Write-Host "The proof appends set 1089 using the original Rare Gacha tables."
Write-Host "Its banner metadata clones original visible set 49, so it may look like an existing banner."
Write-Host "This check determines whether the original schedule already exposes the appended set."
Write-Host ""

$originalUiOk = Read-YesNo "Did the normal Battle Cats Rare Gacha screen open without a custom Kneekura screen or crash?"
$downloadGateSeen = $false
$extraBanner = $null
if ($originalUiOk) {
    $extraBanner = Read-YesNo "Did you observe an additional/duplicated Rare Gacha banner after installing the proof?"
} else {
    $downloadGateSeen = Read-YesNo "Did the app stop at the additional game-data download screen before the Rare Gacha UI?"
}

$result = [ordered]@{
    schema_version = 1
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
    research_frida_seen = ($frida.Count -gt 0)
    fatal_seen = ($fatal.Count -gt 0)
    backup_local_replay_seen = ($replay.Count -gt 0)
    original_rare_gacha_ui_opened = $originalUiOk
    appended_banner_visible = $extraBanner
    additional_download_gate_seen = $downloadGateSeen
    schedule_provider_required = if ($originalUiOk) { -not $extraBanner } else { $null }
    runtime_gate_classification = if (-not $originalUiOk -and $downloadGateSeen) {
        "server_asset_download_gate"
    } elseif (-not $originalUiOk) {
        "original_ui_not_reached"
    } elseif (-not $extraBanner) {
        "gacha_visibility_schedule_not_exposed"
    } else {
        "original_ui_set_visible"
    }
    personal_report = $personalReport
    practice_report = $practiceReport
    gacha_proof_ledger = $proofLedger
    gacha_data_proof = $dataProof
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

if (-not $originalUiOk) {
    if ($downloadGateSeen) {
        Write-Host ""
        Write-Host "Static/data proof PASS, but the original UI is blocked by the server-asset download gate."
        Write-Host "Do not classify this as a gacha schedule failure."
        exit 5
    }
    exit 3
}
if (-not $extraBanner) {
    Write-Host ""
    Write-Host "Static/data proof PASS, but original schedule did not expose set 1089."
    Write-Host "Next implementation is a narrow local gacha-visibility schedule provider."
    exit 4
}
exit 0
