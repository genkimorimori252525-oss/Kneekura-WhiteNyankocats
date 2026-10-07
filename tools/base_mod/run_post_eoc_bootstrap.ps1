param(
    [string]$Adb,
    [string]$Device,
    [string]$Package = "jp.kn.trace.battlecats",
    [string]$OwnedExport = "nyanko_battlecats_2026-10-06.zip",
    [string]$OutDir = "post-eoc-out",
    [switch]$Apply
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Resolve-Adb {
    param([string]$Explicit)
    if ($Explicit) {
        if (-not (Test-Path -LiteralPath $Explicit -PathType Leaf)) { throw "adb not found: $Explicit" }
        return (Resolve-Path -LiteralPath $Explicit).Path
    }
    $command = Get-Command adb -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    if ($env:LOCALAPPDATA) {
        $candidate = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    }
    throw "adb was not found"
}

function Select-Device {
    param([string]$AdbPath, [string]$Requested)
    if ($Requested) {
        $state = @(& $AdbPath -s $Requested get-state 2>$null)
        if ($LASTEXITCODE -ne 0 -or (($state -join "").Trim()) -ne "device") {
            throw "Requested adb device is not online: $Requested"
        }
        return $Requested
    }
    $devices = @()
    foreach ($line in @(& $AdbPath devices)) {
        if ($line -match "^([^\s]+)\s+device\s*$") { $devices += $Matches[1] }
    }
    if ($devices.Count -ne 1) { throw "Expected exactly one online adb device; use -Device <serial>" }
    return $devices[0]
}

function Test-RemotePath {
    param([string]$AdbPath, [string]$DeviceId, [string]$RemotePath)
    $escaped = $RemotePath.Replace("'", "'\''")
    $probe = @(& $AdbPath -s $DeviceId shell "if [ -e '$escaped' ]; then echo 1; else echo 0; fi" 2>$null)
    if ($LASTEXITCODE -ne 0 -or $probe.Count -eq 0) { return $false }
    return (($probe -join "").Trim() -eq "1")
}

function Get-Sha256 {
    param([string]$Path)
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Pull-Checked {
    param([string]$AdbPath, [string]$DeviceId, [string]$Remote, [string]$Local)
    & $AdbPath -s $DeviceId pull $Remote $Local | Out-Host
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $Local -PathType Leaf)) {
        throw "Failed to pull $Remote"
    }
}

function Push-Checked {
    param([string]$AdbPath, [string]$DeviceId, [string]$Local, [string]$Remote)
    & $AdbPath -s $DeviceId push $Local $Remote | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Failed to push $Local to $Remote" }
}

function Test-CleanBaseline {
    param([string]$Path, [string]$Output)
    & python -m tools.base_mod.verify_offline_baseline $Path --output $Output | Out-Host
    return ($LASTEXITCODE -eq 0)
}

function Restore-CurrentState {
    param(
        [string]$AdbPath,
        [string]$DeviceId,
        [string]$PackageName,
        [string]$RemoteRoot,
        [string]$CurrentSave,
        [string]$ExpectedSha,
        [string]$OldSentinel
    )
    Write-Host "Restoring the pre-Post-EoC player state..." -ForegroundColor Yellow
    & $AdbPath -s $DeviceId shell am force-stop $PackageName 2>$null | Out-Null
    $temp = "$RemoteRoot/SAVE_DATA.kneekura-posteoc-rollback"
    Push-Checked -AdbPath $AdbPath -DeviceId $DeviceId -Local $CurrentSave -Remote $temp
    & $AdbPath -s $DeviceId shell "mv '$temp' '$RemoteRoot/SAVE_DATA'" 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Post-EoC rollback replacement failed" }
    $verify = Join-Path (Split-Path -Parent $CurrentSave) "rollback-verify-current-SAVE_DATA"
    Pull-Checked -AdbPath $AdbPath -DeviceId $DeviceId -Remote "$RemoteRoot/SAVE_DATA" -Local $verify
    if ((Get-Sha256 -Path $verify) -ne $ExpectedSha) { throw "Post-EoC rollback SHA verification failed" }

    foreach ($sidecar in @(
        "KNEEKURA_POST_EOC_PROFILE.json",
        "KNEEKURA_CHANNEL.json",
        "KNEEKURA_LOGIN_POOL.json",
        "KNEEKURA_LOGIN_STATE.json"
    )) {
        & $AdbPath -s $DeviceId shell "rm -f '$RemoteRoot/$sidecar'" 2>$null | Out-Null
    }

    if ($OldSentinel -and (Test-Path -LiteralPath $OldSentinel -PathType Leaf)) {
        Push-Checked -AdbPath $AdbPath -DeviceId $DeviceId -Local $OldSentinel -Remote "$RemoteRoot/KNEEKURA_OFFLINE_MAX_BOOTSTRAP.json"
    }

    & $AdbPath -s $DeviceId shell am start -n "$PackageName/$PackageName.MyActivity" | Out-Host
    Write-Host "Pre-Post-EoC state restored." -ForegroundColor Green
}

$adbPath = Resolve-Adb -Explicit $Adb
$deviceId = Select-Device -AdbPath $adbPath -Requested $Device

$exportPath = [System.IO.Path]::GetFullPath($OwnedExport)
if (-not (Test-Path -LiteralPath $exportPath -PathType Leaf)) { throw "Owned export not found: $exportPath" }

$root = [System.IO.Path]::GetFullPath($OutDir)
New-Item -ItemType Directory -Force -Path $root | Out-Null

$remoteRoot = "/sdcard/Android/data/$Package/files"
$remoteSave = "$remoteRoot/SAVE_DATA"
$remoteCleanBackup = "$remoteRoot/SAVE_DATA.kneekura-premax"
$remoteOldSentinel = "$remoteRoot/KNEEKURA_OFFLINE_MAX_BOOTSTRAP.json"

if (-not (Test-RemotePath -AdbPath $adbPath -DeviceId $deviceId -RemotePath $remoteSave)) {
    throw "Research SAVE_DATA not found: $remoteSave"
}

Write-Host "[1/8] Capturing current playable state..."
& $adbPath -s $deviceId shell am force-stop $Package 2>$null | Out-Null
$currentSave = Join-Path $root "current-before-post-eoc-SAVE_DATA"
Pull-Checked -AdbPath $adbPath -DeviceId $deviceId -Remote $remoteSave -Local $currentSave
$currentSha = Get-Sha256 -Path $currentSave

$oldSentinel = Join-Path $root "current-max-sentinel.json"
if (Test-RemotePath -AdbPath $adbPath -DeviceId $deviceId -RemotePath $remoteOldSentinel) {
    Pull-Checked -AdbPath $adbPath -DeviceId $deviceId -Remote $remoteOldSentinel -Local $oldSentinel
} else {
    $oldSentinel = $null
}

Write-Host "[2/8] Locating a verified clean JP15.7.1 baseline..."
$cleanSource = Join-Path $root "source-clean-SAVE_DATA"
$baselineVerify = Join-Path $root "source-clean-verification.json"
$baselineFound = $false

if (Test-RemotePath -AdbPath $adbPath -DeviceId $deviceId -RemotePath $remoteCleanBackup) {
    Pull-Checked -AdbPath $adbPath -DeviceId $deviceId -Remote $remoteCleanBackup -Local $cleanSource
    if (Test-CleanBaseline -Path $cleanSource -Output $baselineVerify) { $baselineFound = $true }
}

if (-not $baselineFound) {
    foreach ($candidate in @(
        "offline-max-out\pre-apply-device-SAVE_DATA.rollback",
        "offline-max-out\pre-apply-device-SAVE_DATA"
    )) {
        $full = [System.IO.Path]::GetFullPath($candidate)
        if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { continue }
        Copy-Item -LiteralPath $full -Destination $cleanSource -Force
        if (Test-CleanBaseline -Path $cleanSource -Output $baselineVerify) {
            $baselineFound = $true
            break
        }
    }
}
if (-not $baselineFound) {
    throw "No verified JP15.7.1 clean baseline was found. Current SAVE_DATA was not modified."
}

Write-Host "[3/8] Building and statically verifying Post-EoC profile..."
$postEocSave = Join-Path $root "SAVE_DATA.post-eoc"
$buildReport = Join-Path $root "post-eoc-build-report.json"
& python -m tools.base_mod.build_post_eoc_save $cleanSource $exportPath --output $postEocSave --report $buildReport | Out-Host
if ($LASTEXITCODE -ne 0) { throw "Post-EoC build failed" }

$postEocVerification = Join-Path $root "post-eoc-static-verification.json"
& python -m tools.base_mod.verify_post_eoc_save $postEocSave $exportPath --output $postEocVerification | Out-Host
if ($LASTEXITCODE -ne 0) { throw "Post-EoC static semantic verification failed" }
$postEocSha = Get-Sha256 -Path $postEocSave

Write-Host "[4/8] Preparing offline LiveOps sidecars..."
$loginPool = Join-Path $root "KNEEKURA_LOGIN_POOL.json"
& python -m tools.liveops.build_login_pool $exportPath --output $loginPool | Out-Host
if ($LASTEXITCODE -ne 0) { throw "Login pool build failed" }

$channel = Join-Path $root "KNEEKURA_CHANNEL.json"
& python -m tools.liveops.build_default_channel $exportPath --output $channel | Out-Host
if ($LASTEXITCODE -ne 0) { throw "Content channel build failed" }

$loginState = Join-Path $root "KNEEKURA_LOGIN_STATE.json"
$loginSeed = [guid]::NewGuid().ToString("N")
$localDay = ([DateTime]::Today - [DateTime]"1970-01-01").Days
& python -m tools.liveops.init_login_state $loginPool --seed $loginSeed --local-day $localDay --output $loginState | Out-Host
if ($LASTEXITCODE -ne 0) { throw "Login state initialization failed" }

Write-Host ""
Write-Host "Static Post-EoC build is ready." -ForegroundColor Green
Write-Host "  candidate: $postEocSave"
Write-Host "  verification: $postEocVerification"
Write-Host "  candidate SHA-256: $postEocSha"
Write-Host ""

if (-not $Apply) {
    Write-Host "No device mutation was requested."
    Write-Host "Run the same command with -Apply when you want the one-click migration."
    exit 0
}

Write-Host "[5/8] Staging rollback + Post-EoC candidate..."
$remoteCurrentBackup = "$remoteRoot/SAVE_DATA.kneekura-before-posteoc"
$remoteTemp = "$remoteRoot/SAVE_DATA.kneekura-posteoc-new"
Push-Checked -AdbPath $adbPath -DeviceId $deviceId -Local $currentSave -Remote $remoteCurrentBackup
Push-Checked -AdbPath $adbPath -DeviceId $deviceId -Local $postEocSave -Remote $remoteTemp

$stagedVerify = Join-Path $root "staged-post-eoc-SAVE_DATA"
Pull-Checked -AdbPath $adbPath -DeviceId $deviceId -Remote $remoteTemp -Local $stagedVerify
if ((Get-Sha256 -Path $stagedVerify) -ne $postEocSha) {
    throw "Staged Post-EoC candidate hash mismatch; current SAVE_DATA is untouched"
}

Write-Host "[6/8] Promoting Post-EoC SAVE_DATA and sidecars..."
& $adbPath -s $deviceId shell "mv '$remoteTemp' '$remoteSave'" 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Failed to promote Post-EoC SAVE_DATA; rollback backup is preserved" }

Push-Checked -AdbPath $adbPath -DeviceId $deviceId -Local $channel -Remote "$remoteRoot/KNEEKURA_CHANNEL.json"
Push-Checked -AdbPath $adbPath -DeviceId $deviceId -Local $loginPool -Remote "$remoteRoot/KNEEKURA_LOGIN_POOL.json"
Push-Checked -AdbPath $adbPath -DeviceId $deviceId -Local $loginState -Remote "$remoteRoot/KNEEKURA_LOGIN_STATE.json"

if ($oldSentinel) {
    & $adbPath -s $deviceId shell "if [ -e '$remoteOldSentinel' ]; then mv '$remoteOldSentinel' '$remoteRoot/KNEEKURA_OFFLINE_MAX_BOOTSTRAP.archived.json'; fi" 2>$null | Out-Null
}

Write-Host "[7/8] Running bounded original-UI restart smoke..."
& $adbPath -s $deviceId shell am start -n "$Package/$Package.MyActivity" | Out-Host
Start-Sleep -Seconds 8
$pidFirst = @(& $adbPath -s $deviceId shell pidof $Package 2>$null)
if (($pidFirst -join "").Trim().Length -eq 0) {
    Restore-CurrentState -AdbPath $adbPath -DeviceId $deviceId -PackageName $Package -RemoteRoot $remoteRoot -CurrentSave $currentSave -ExpectedSha $currentSha -OldSentinel $oldSentinel
    throw "Original UI process was not alive after Post-EoC first launch; rollback completed"
}

& $adbPath -s $deviceId shell am force-stop $Package 2>$null | Out-Null
Start-Sleep -Seconds 2
& $adbPath -s $deviceId shell am start -n "$Package/$Package.MyActivity" | Out-Host
Start-Sleep -Seconds 8
$pidSecond = @(& $adbPath -s $deviceId shell pidof $Package 2>$null)
if (($pidSecond -join "").Trim().Length -eq 0) {
    Restore-CurrentState -AdbPath $adbPath -DeviceId $deviceId -PackageName $Package -RemoteRoot $remoteRoot -CurrentSave $currentSave -ExpectedSha $currentSha -OldSentinel $oldSentinel
    throw "Original UI process was not alive after Post-EoC restart; rollback completed"
}

Write-Host "[8/8] Pulling and verifying persisted Post-EoC state..."
$postRestart = Join-Path $root "post-restart-SAVE_DATA"
Pull-Checked -AdbPath $adbPath -DeviceId $deviceId -Remote $remoteSave -Local $postRestart
$postRestartVerification = Join-Path $root "post-restart-verification.json"
& python -m tools.base_mod.verify_post_eoc_save $postRestart $exportPath --output $postRestartVerification --allow-runtime-rewrite | Out-Host

if ($LASTEXITCODE -ne 0) {
    Restore-CurrentState -AdbPath $adbPath -DeviceId $deviceId -PackageName $Package -RemoteRoot $remoteRoot -CurrentSave $currentSave -ExpectedSha $currentSha -OldSentinel $oldSentinel
    throw "Persisted Post-EoC SAVE_DATA failed semantic verification; rollback completed"
}
$postRestartVerificationObject = Get-Content -LiteralPath $postRestartVerification -Raw | ConvertFrom-Json

$profileSentinel = Join-Path $root "KNEEKURA_POST_EOC_PROFILE.json"
$result = [ordered]@{
    schema_version = 1
    mode = "kneekura-post-eoc-bootstrap"
    package = $Package
    previous_save_sha256 = $currentSha
    clean_source_sha256 = (Get-Sha256 -Path $cleanSource)
    candidate_sha256 = $postEocSha
    post_restart_sha256 = (Get-Sha256 -Path $postRestart)
    static_verification = $postEocVerification
    post_restart_verification = $postRestartVerification
    post_restart_verification_level = $postRestartVerificationObject.verification_level
    post_restart_layout_profile = $postRestartVerificationObject.layout_profile
    post_restart_semantic_scope_complete = $postRestartVerificationObject.semantic_scope_complete
    original_ui_first_launch_alive = $true
    original_ui_restart_alive = $true
    current_state_backup_remote = $remoteCurrentBackup
    clean_baseline_remote = $remoteCleanBackup
    login_pool = "KNEEKURA_LOGIN_POOL.json"
    login_state = "KNEEKURA_LOGIN_STATE.json"
    channel = "KNEEKURA_CHANNEL.json"
    login_runtime_provider_connected = $false
    event_runtime_schedule_provider_connected = $false
    applied = $true
}
$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $profileSentinel -Encoding UTF8
Push-Checked -AdbPath $adbPath -DeviceId $deviceId -Local $profileSentinel -Remote "$remoteRoot/KNEEKURA_POST_EOC_PROFILE.json"

$resultPath = Join-Path $root "post-eoc-bootstrap-result.json"
$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $resultPath -Encoding UTF8

Write-Host ""
Write-Host "Kneekura Post-EoC profile passed static + restart verification." -ForegroundColor Green
Write-Host "Result: $resultPath"
Write-Host "You can play immediately. Login/event runtime providers remain separate future LiveOps integrations."
