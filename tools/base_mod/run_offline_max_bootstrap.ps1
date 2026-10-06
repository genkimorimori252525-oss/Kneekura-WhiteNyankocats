param(
    [string]$Adb,
    [string]$Device,
    [string]$Package = "jp.kn.trace.battlecats",
    [string]$OwnedExport = "nyanko_battlecats_2026-10-06.zip",
    [string]$OutDir = "offline-max-out"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ExpectedBaselineSha256 = "cad00e84f3d64910b623b8a89b57ae1a37e8947554f4b418f50efa1c6bdc1d3c"
$ExpectedCandidateSha256 = "0f5cbdadf2536f05af7748f7696ca93233dfb01d80dfe98a17da0fd5e6cf65e7"

function Resolve-Adb {
    param([string]$Explicit)
    if ($Explicit) {
        if (-not (Test-Path -LiteralPath $Explicit -PathType Leaf)) {
            throw "adb not found: $Explicit"
        }
        return (Resolve-Path -LiteralPath $Explicit).Path
    }
    $command = Get-Command adb -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    if ($env:LOCALAPPDATA) {
        $candidate = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    }
    throw "adb was not found. Put Android platform-tools on PATH or pass -Adb."
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
    $lines = @(& $AdbPath devices)
    $devices = @()
    foreach ($line in $lines) {
        if ($line -match "^([^\s]+)\s+device\s*$") { $devices += $Matches[1] }
    }
    if ($devices.Count -eq 0) { throw "No online adb device found" }
    if ($devices.Count -gt 1) { throw "Multiple adb devices found; use -Device <serial>" }
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

function Restore-Baseline {
    param([string]$AdbPath, [string]$DeviceId, [string]$PackageName, [string]$RemoteRoot, [string]$Backup, [string]$VerifyDir)
    Write-Host "Rolling back the exact pre-apply SAVE_DATA..." -ForegroundColor Yellow
    & $AdbPath -s $DeviceId shell am force-stop $PackageName 2>$null | Out-Null
    $rollbackTemp = "$RemoteRoot/SAVE_DATA.kneekura-rollback"
    Push-Checked -AdbPath $AdbPath -DeviceId $DeviceId -Local $Backup -Remote $rollbackTemp
    & $AdbPath -s $DeviceId shell "mv '$rollbackTemp' '$RemoteRoot/SAVE_DATA'" 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Rollback mv failed" }
    $verify = Join-Path $VerifyDir "rollback-verify-SAVE_DATA"
    Pull-Checked -AdbPath $AdbPath -DeviceId $DeviceId -Remote "$RemoteRoot/SAVE_DATA" -Local $verify
    $rollbackSha = Get-Sha256 -Path $verify
    if ($rollbackSha -ne $ExpectedBaselineSha256) { throw "Rollback verification failed: $rollbackSha" }
    & $AdbPath -s $DeviceId shell "rm -f '$RemoteRoot/KNEEKURA_OFFLINE_MAX_BOOTSTRAP.json'" 2>$null | Out-Null
    Write-Host "Rollback verified." -ForegroundColor Green
}

$adbPath = Resolve-Adb -Explicit $Adb
$deviceId = Select-Device -AdbPath $adbPath -Requested $Device

$exportPath = [System.IO.Path]::GetFullPath($OwnedExport)
if (-not (Test-Path -LiteralPath $exportPath -PathType Leaf)) { throw "Owned export not found: $exportPath" }

$root = [System.IO.Path]::GetFullPath($OutDir)
New-Item -ItemType Directory -Force -Path $root | Out-Null

$remoteRoot = "/sdcard/Android/data/$Package/files"
$remoteSave = "$remoteRoot/SAVE_DATA"
$remoteSentinel = "$remoteRoot/KNEEKURA_OFFLINE_MAX_BOOTSTRAP.json"

if (-not (Test-RemotePath -AdbPath $adbPath -DeviceId $deviceId -RemotePath $remoteSave)) {
    throw "Research SAVE_DATA not found: $remoteSave"
}
if (Test-RemotePath -AdbPath $adbPath -DeviceId $deviceId -RemotePath $remoteSentinel) {
    Write-Host "Offline MAX bootstrap sentinel already exists. No SAVE_DATA was changed." -ForegroundColor Yellow
    Write-Host "Use the rollback runner first if you intentionally want to return to the pre-MAX baseline."
    exit 0
}

Write-Host "[1/7] Force-stopping only the isolated research package..."
& $adbPath -s $deviceId shell am force-stop $Package 2>$null | Out-Null

Write-Host "[2/7] Pulling an immutable pre-apply device backup..."
$backup = Join-Path $root "pre-apply-device-SAVE_DATA"
Pull-Checked -AdbPath $adbPath -DeviceId $deviceId -Remote $remoteSave -Local $backup
$backupSha = Get-Sha256 -Path $backup
if ($backupSha -ne $ExpectedBaselineSha256) {
    throw "Current device SAVE_DATA is not the approved exact baseline. Expected: $ExpectedBaselineSha256 Actual: $backupSha. No device file was modified."
}
$rollbackCopy = Join-Path $root "pre-apply-device-SAVE_DATA.rollback"
Copy-Item -LiteralPath $backup -Destination $rollbackCopy -Force
if ((Get-Sha256 -Path $rollbackCopy) -ne $backupSha) { throw "Local rollback copy hash mismatch" }

Write-Host "[3/7] Building the exact one-time offline MAX candidate..."
$candidate = Join-Path $root "SAVE_DATA.offline-max"
$report = Join-Path $root "offline-max-build-report.json"
& python -m tools.base_mod.build_offline_max_save $backup $exportPath --output $candidate --report $report | Out-Host
if ($LASTEXITCODE -ne 0) { throw "Offline MAX SAVE_DATA build failed" }
$candidateSha = Get-Sha256 -Path $candidate
if ($candidateSha -ne $ExpectedCandidateSha256) { throw "Candidate SHA-256 mismatch: $candidateSha" }

$inspection = Join-Path $root "offline-max-candidate-inspection.json"
& python -m tools.base_mod.inspect_save_data $candidate --output $inspection | Out-Host
if ($LASTEXITCODE -ne 0) { throw "Candidate SAVE_DATA integrity inspection failed" }

Write-Host ""
Write-Host "Pre-apply backup: $backup"
Write-Host "Candidate SHA-256: $candidateSha"
Write-Host ""
Write-Host "For this first runtime proof, disable Wi-Fi and mobile data on the Android device." -ForegroundColor Yellow
$offline = (Read-Host "Are Wi-Fi and mobile data disabled? [y/n]").Trim().ToLowerInvariant()
if ($offline -notin @("y", "yes")) {
    Write-Host "Aborted before device mutation. Candidate and backup remain on the PC." -ForegroundColor Yellow
    exit 0
}
$confirm = Read-Host "Type APPLY to replace only jp.kn.trace.battlecats SAVE_DATA"
if ($confirm -cne "APPLY") {
    Write-Host "Aborted before device mutation. Candidate and backup remain on the PC." -ForegroundColor Yellow
    exit 0
}

Write-Host "[4/7] Staging candidate and a second rollback copy on the research package..."
$remoteBackup = "$remoteRoot/SAVE_DATA.kneekura-premax"
$remoteTemp = "$remoteRoot/SAVE_DATA.kneekura-new"
Push-Checked -AdbPath $adbPath -DeviceId $deviceId -Local $rollbackCopy -Remote $remoteBackup
Push-Checked -AdbPath $adbPath -DeviceId $deviceId -Local $candidate -Remote $remoteTemp
$stageVerify = Join-Path $root "staged-candidate-verify"
Pull-Checked -AdbPath $adbPath -DeviceId $deviceId -Remote $remoteTemp -Local $stageVerify
if ((Get-Sha256 -Path $stageVerify) -ne $ExpectedCandidateSha256) {
    throw "Staged candidate verification failed; original SAVE_DATA is still untouched"
}

Write-Host "[5/7] Atomically replacing the research SAVE_DATA..."
& $adbPath -s $deviceId shell "mv '$remoteTemp' '$remoteSave'" 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Failed to replace research SAVE_DATA; remote backup is still present at $remoteBackup" }
$installedVerify = Join-Path $root "installed-candidate-verify"
Pull-Checked -AdbPath $adbPath -DeviceId $deviceId -Remote $remoteSave -Local $installedVerify
$installedSha = Get-Sha256 -Path $installedVerify
if ($installedSha -ne $ExpectedCandidateSha256) {
    Restore-Baseline -AdbPath $adbPath -DeviceId $deviceId -PackageName $Package -RemoteRoot $remoteRoot -Backup $rollbackCopy -VerifyDir $root
    throw "Installed SAVE_DATA hash mismatch; rollback completed"
}

Write-Host "[6/7] Launching original Battle Cats scene with the candidate..."
& $adbPath -s $deviceId shell am start -n "$Package/$Package.MyActivity" | Out-Host
Start-Sleep -Seconds 8
$firstOk = (Read-Host "Did the original Battle Cats UI open normally without a save/data-read error? [y/n]").Trim().ToLowerInvariant()
if ($firstOk -notin @("y", "yes")) {
    Restore-Baseline -AdbPath $adbPath -DeviceId $deviceId -PackageName $Package -RemoteRoot $remoteRoot -Backup $rollbackCopy -VerifyDir $root
    Write-Host "Candidate rejected by manual UI check; rollback completed."
    exit 3
}

Write-Host "[7/7] Verifying that the candidate survives a normal process restart..."
& $adbPath -s $deviceId shell am force-stop $Package 2>$null | Out-Null
Start-Sleep -Seconds 2
& $adbPath -s $deviceId shell am start -n "$Package/$Package.MyActivity" | Out-Host
Start-Sleep -Seconds 8
$secondOk = (Read-Host "After the restart, did the original UI still open normally with the MAX profile intact? [y/n]").Trim().ToLowerInvariant()
if ($secondOk -notin @("y", "yes")) {
    Restore-Baseline -AdbPath $adbPath -DeviceId $deviceId -PackageName $Package -RemoteRoot $remoteRoot -Backup $rollbackCopy -VerifyDir $root
    Write-Host "Restart verification failed; rollback completed."
    exit 4
}

$postRestart = Join-Path $root "post-restart-SAVE_DATA"
Pull-Checked -AdbPath $adbPath -DeviceId $deviceId -Remote $remoteSave -Local $postRestart
$postRestartSha = Get-Sha256 -Path $postRestart

$postRestartVerification = Join-Path $root "post-restart-max-verification.json"
& python -m tools.base_mod.verify_offline_max_save $postRestart $exportPath --output $postRestartVerification --allow-runtime-rewrite | Out-Host
if ($LASTEXITCODE -ne 0) {
    Restore-Baseline -AdbPath $adbPath -DeviceId $deviceId -PackageName $Package -RemoteRoot $remoteRoot -Backup $rollbackCopy -VerifyDir $root
    Write-Host "Post-restart SAVE_DATA failed even the stable-prefix runtime verification; rollback completed."
    exit 5
}

$sentinelLocal = Join-Path $root "KNEEKURA_OFFLINE_MAX_BOOTSTRAP.json"
$result = [ordered]@{
    schema_version = 1
    mode = "offline-max-bootstrap-runtime-proof"
    package = $Package
    baseline_sha256 = $ExpectedBaselineSha256
    candidate_sha256 = $ExpectedCandidateSha256
    installed_sha256_before_launch = $installedSha
    post_restart_save_sha256 = $postRestartSha
    post_restart_max_verification = $postRestartVerification
    post_restart_size = (Get-Item -LiteralPath $postRestart).Length
    post_restart_runtime_rewrite_allowed = $true
    first_launch_original_ui_ok = $true
    second_launch_original_ui_ok = $true
    rollback_local = $rollbackCopy
    rollback_remote = $remoteBackup
    bootstrap_applied_once = $true
    network_disabled_confirmed_by_user = $true
}
$result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $sentinelLocal -Encoding UTF8
Push-Checked -AdbPath $adbPath -DeviceId $deviceId -Local $sentinelLocal -Remote $remoteSentinel

$resultPath = Join-Path $root "offline-max-bootstrap-result.json"
$result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $resultPath -Encoding UTF8
Write-Host ""
Write-Host "Offline MAX bootstrap runtime proof passed." -ForegroundColor Green
Write-Host "The sentinel prevents this bootstrap from overwriting later player changes."
Write-Host "Result: $resultPath"
Write-Host "Rollback: $rollbackCopy"
