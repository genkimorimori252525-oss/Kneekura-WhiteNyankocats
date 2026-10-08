param(
    [string]$Adb,
    [string]$Device,
    [string]$Package = "jp.kn.trace.battlecats",
    [string]$OwnedExport = "nyanko_battlecats_2026-10-06.zip",
    [string]$OutDir = "level-cap-unlock-out",
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
        $candidatePath = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
        if (Test-Path -LiteralPath $candidatePath -PathType Leaf) { return $candidatePath }
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

function Restore-Backup {
    param(
        [string]$AdbPath,
        [string]$DeviceId,
        [string]$PackageName,
        [string]$RemoteRoot,
        [string]$BackupPath,
        [string]$ExpectedSha
    )
    Write-Host "Restoring pre-migration SAVE_DATA..." -ForegroundColor Yellow
    & $AdbPath -s $DeviceId shell am force-stop $PackageName 2>$null | Out-Null
    $temp = "$RemoteRoot/SAVE_DATA.kneekura-levelcap-rollback-temp"
    Push-Checked -AdbPath $AdbPath -DeviceId $DeviceId -Local $BackupPath -Remote $temp
    & $AdbPath -s $DeviceId shell "mv '$temp' '$RemoteRoot/SAVE_DATA'" 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Level-cap rollback replacement failed" }
    $verifyPath = Join-Path (Split-Path -Parent $BackupPath) "rollback-verify-SAVE_DATA"
    Pull-Checked -AdbPath $AdbPath -DeviceId $DeviceId -Remote "$RemoteRoot/SAVE_DATA" -Local $verifyPath
    if ((Get-Sha256 -Path $verifyPath) -ne $ExpectedSha) { throw "Level-cap rollback SHA verification failed" }
    Write-Host "Pre-migration SAVE_DATA restored." -ForegroundColor Green
}

$adbPath = Resolve-Adb -Explicit $Adb
$deviceId = Select-Device -AdbPath $adbPath -Requested $Device
$exportPath = [System.IO.Path]::GetFullPath($OwnedExport)
if (-not (Test-Path -LiteralPath $exportPath -PathType Leaf)) { throw "Owned export not found: $exportPath" }

$root = [System.IO.Path]::GetFullPath($OutDir)
New-Item -ItemType Directory -Force -Path $root | Out-Null

$remoteRoot = "/sdcard/Android/data/$Package/files"
$remoteSave = "$remoteRoot/SAVE_DATA"
$remoteBackup = "$remoteRoot/SAVE_DATA.kneekura-before-levelcap-v1"
$remoteTemp = "$remoteRoot/SAVE_DATA.kneekura-levelcap-v1-new"
$remoteSentinel = "$remoteRoot/KNEEKURA_LEVEL_CAP_UNLOCK_V1.json"

Write-Host "[1/6] Capturing current SAVE_DATA..."
& $adbPath -s $deviceId shell am force-stop $Package 2>$null | Out-Null
$currentSave = Join-Path $root "pre-level-cap-SAVE_DATA"
Pull-Checked -AdbPath $adbPath -DeviceId $deviceId -Remote $remoteSave -Local $currentSave
$currentSha = Get-Sha256 -Path $currentSave

$preVerify = Join-Path $root "pre-level-cap-verification.json"
& python -m tools.base_mod.level_cap_unlock verify $currentSave $exportPath --output $preVerify | Out-Host
$preAlreadyUnlocked = ($LASTEXITCODE -eq 0)

Write-Host "[2/6] Building additive native-cap migration..."
$candidate = Join-Path $root "SAVE_DATA.level-cap-v1"
$buildReport = Join-Path $root "level-cap-build-report.json"
& python -m tools.base_mod.level_cap_unlock apply $currentSave $exportPath --output $candidate --report $buildReport | Out-Host
if ($LASTEXITCODE -ne 0) { throw "Level-cap candidate build failed" }

$candidateVerify = Join-Path $root "level-cap-candidate-verification.json"
& python -m tools.base_mod.level_cap_unlock verify $candidate $exportPath --output $candidateVerify | Out-Host
if ($LASTEXITCODE -ne 0) { throw "Level-cap candidate semantic verification failed" }
$candidateSha = Get-Sha256 -Path $candidate

Write-Host ""
Write-Host "Native level-cap migration is statically ready." -ForegroundColor Green
Write-Host "  current SHA-256:   $currentSha"
Write-Host "  candidate SHA-256: $candidateSha"
Write-Host "  Lv60-native units: 323"
Write-Host "  Lv50-native units: 493"
Write-Host "No story clear flags or current Cat levels are changed."

if (-not $Apply) {
    Write-Host "No device mutation was requested."
    Write-Host "Run the same command with -Apply to install this migration."
    exit 0
}

Write-Host "[3/6] Staging exact rollback copy and candidate..."
Push-Checked -AdbPath $adbPath -DeviceId $deviceId -Local $currentSave -Remote $remoteBackup
Push-Checked -AdbPath $adbPath -DeviceId $deviceId -Local $candidate -Remote $remoteTemp

$staged = Join-Path $root "staged-level-cap-SAVE_DATA"
Pull-Checked -AdbPath $adbPath -DeviceId $deviceId -Remote $remoteTemp -Local $staged
if ((Get-Sha256 -Path $staged) -ne $candidateSha) {
    throw "Staged level-cap candidate SHA mismatch; current SAVE_DATA is untouched"
}

Write-Host "[4/6] Promoting level-cap migration..."
& $adbPath -s $deviceId shell "mv '$remoteTemp' '$remoteSave'" 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Failed to promote level-cap SAVE_DATA; rollback copy is preserved" }

Write-Host "[5/6] Running bounded original-UI restart smoke..."
& $adbPath -s $deviceId shell am start -n "$Package/$Package.MyActivity" | Out-Host
Start-Sleep -Seconds 8
$pidFirst = @(& $adbPath -s $deviceId shell pidof $Package 2>$null)
if (($pidFirst -join "").Trim().Length -eq 0) {
    Restore-Backup -AdbPath $adbPath -DeviceId $deviceId -PackageName $Package -RemoteRoot $remoteRoot -BackupPath $currentSave -ExpectedSha $currentSha
    throw "Original UI process was not alive after level-cap migration; rollback completed"
}

& $adbPath -s $deviceId shell am force-stop $Package 2>$null | Out-Null
Start-Sleep -Seconds 2
& $adbPath -s $deviceId shell am start -n "$Package/$Package.MyActivity" | Out-Host
Start-Sleep -Seconds 8
$pidSecond = @(& $adbPath -s $deviceId shell pidof $Package 2>$null)
if (($pidSecond -join "").Trim().Length -eq 0) {
    Restore-Backup -AdbPath $adbPath -DeviceId $deviceId -PackageName $Package -RemoteRoot $remoteRoot -BackupPath $currentSave -ExpectedSha $currentSha
    throw "Original UI process was not alive after level-cap restart; rollback completed"
}

Write-Host "[6/6] Verifying persisted native caps..."
$postRestart = Join-Path $root "post-restart-level-cap-SAVE_DATA"
Pull-Checked -AdbPath $adbPath -DeviceId $deviceId -Remote $remoteSave -Local $postRestart
$postVerify = Join-Path $root "post-restart-level-cap-verification.json"
& python -m tools.base_mod.level_cap_unlock verify $postRestart $exportPath --output $postVerify | Out-Host
if ($LASTEXITCODE -ne 0) {
    Restore-Backup -AdbPath $adbPath -DeviceId $deviceId -PackageName $Package -RemoteRoot $remoteRoot -BackupPath $currentSave -ExpectedSha $currentSha
    throw "Persisted level-cap state failed semantic verification; rollback completed"
}

$result = [ordered]@{
    schema_version = 1
    mode = "kneekura-native-level-cap-unlock-v1"
    package = $Package
    requested_cap = 60
    native_level60_unit_count = 323
    native_level50_unit_count = 493
    current_save_sha256 = $currentSha
    candidate_sha256 = $candidateSha
    post_restart_sha256 = (Get-Sha256 -Path $postRestart)
    pre_already_satisfied = $preAlreadyUnlocked
    build_report = $buildReport
    candidate_verification = $candidateVerify
    post_restart_verification = $postVerify
    remote_rollback_copy = $remoteBackup
    story_progress_modified = $false
    current_levels_modified = $false
    ownership_modified = $false
    catseyes_used_history_modified = $false
    applied = $true
}
$resultPath = Join-Path $root "level-cap-unlock-result.json"
$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $resultPath -Encoding UTF8
Push-Checked -AdbPath $adbPath -DeviceId $deviceId -Local $resultPath -Remote $remoteSentinel

Write-Host ""
Write-Host "Kneekura native level-cap unlock passed." -ForegroundColor Green
Write-Host "Lv60-capable JP15.7.1 units can now reach 60 without changing Legend progress."
Write-Host "Result: $resultPath"
Write-Host "Rollback copy remains at: $remoteBackup"
