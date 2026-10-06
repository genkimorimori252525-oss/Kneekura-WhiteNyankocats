param(
    [string]$Adb,
    [string]$Device,
    [string]$Package = "jp.kn.trace.battlecats",
    [string]$Backup = "offline-max-out\pre-apply-device-SAVE_DATA.rollback",
    [string]$OutDir = "offline-max-out"
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
    if ($Requested) { return $Requested }
    $devices = @()
    foreach ($line in @(& $AdbPath devices)) {
        if ($line -match "^([^\s]+)\s+device\s*$") { $devices += $Matches[1] }
    }
    if ($devices.Count -ne 1) { throw "Expected exactly one online adb device; use -Device <serial>" }
    return $devices[0]
}

function Get-Sha256 {
    param([string]$Path)
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

$adbPath = Resolve-Adb -Explicit $Adb
$deviceId = Select-Device -AdbPath $adbPath -Requested $Device

$backupPath = [System.IO.Path]::GetFullPath($Backup)
if (-not (Test-Path -LiteralPath $backupPath -PathType Leaf)) {
    throw "Rollback SAVE_DATA not found: $backupPath"
}
$backupSha = Get-Sha256 -Path $backupPath
$rollbackBaselineVerification = Join-Path ([System.IO.Path]::GetFullPath($OutDir)) "rollback-baseline-verification.json"
& python -m tools.base_mod.verify_offline_baseline $backupPath --output $rollbackBaselineVerification | Out-Host
if ($LASTEXITCODE -ne 0) {
    throw "Rollback file is not an approved JP 15.7.1 clean baseline"
}

$root = [System.IO.Path]::GetFullPath($OutDir)
New-Item -ItemType Directory -Force -Path $root | Out-Null

$remoteRoot = "/sdcard/Android/data/$Package/files"
$remoteSave = "$remoteRoot/SAVE_DATA"
$remoteTemp = "$remoteRoot/SAVE_DATA.kneekura-rollback"

Write-Host "Force-stopping isolated research package..."
& $adbPath -s $deviceId shell am force-stop $Package 2>$null | Out-Null

Write-Host "Pushing exact pre-MAX rollback SAVE_DATA..."
& $adbPath -s $deviceId push $backupPath $remoteTemp | Out-Host
if ($LASTEXITCODE -ne 0) { throw "Rollback push failed" }

& $adbPath -s $deviceId shell "mv '$remoteTemp' '$remoteSave'" 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Rollback replacement failed" }

$verify = Join-Path $root "manual-rollback-verify-SAVE_DATA"
& $adbPath -s $deviceId pull $remoteSave $verify | Out-Host
if ($LASTEXITCODE -ne 0) { throw "Rollback verification pull failed" }
$verifySha = Get-Sha256 -Path $verify
if ($verifySha -ne $backupSha) {
    throw "Rollback verification SHA mismatch: $verifySha != $backupSha"
}

& $adbPath -s $deviceId shell "rm -f '$remoteRoot/KNEEKURA_OFFLINE_MAX_BOOTSTRAP.json'" 2>$null | Out-Null

$result = [ordered]@{
    schema_version = 1
    mode = "offline-max-manual-rollback"
    package = $Package
    restored_sha256 = $verifySha
    baseline_verification = $rollbackBaselineVerification
    rollback_verified = $true
}
$resultPath = Join-Path $root "offline-max-rollback-result.json"
$result | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $resultPath -Encoding UTF8

Write-Host "Rollback verified. Relaunching original scene..." -ForegroundColor Green
& $adbPath -s $deviceId shell am start -n "$Package/$Package.MyActivity" | Out-Host
Write-Host "Result: $resultPath"
