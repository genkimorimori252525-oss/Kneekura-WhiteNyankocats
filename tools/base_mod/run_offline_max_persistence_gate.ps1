param(
    [string]$Adb,
    [string]$Device,
    [string]$Package = "jp.kn.trace.battlecats",
    [string]$OwnedExport = "nyanko_battlecats_2026-10-06.zip",
    [string]$SignedSplitDir = "phase-c-final-out\gacha-ui-proof\research-gacha-ui-proof-signed-splits",
    [string]$OutDir = "offline-max-persistence-out"
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

function Get-OptionalProperty {
    param(
        [object]$Object,
        [string]$Name,
        $DefaultValue = $null
    )
    if ($null -eq $Object) { return $DefaultValue }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) { return $DefaultValue }
    return $property.Value
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

function Restore-PreUpgradeSave {
    param(
        [string]$AdbPath,
        [string]$DeviceId,
        [string]$PackageName,
        [string]$RemoteRoot,
        [string]$SaveBackup,
        [string]$SentinelBackup
    )
    Write-Host "Restoring the pre-install-r MAX save..." -ForegroundColor Yellow
    & $AdbPath -s $DeviceId shell am force-stop $PackageName 2>$null | Out-Null
    $temp = "$RemoteRoot/SAVE_DATA.kneekura-persistence-rollback"
    Push-Checked -AdbPath $AdbPath -DeviceId $DeviceId -Local $SaveBackup -Remote $temp
    & $AdbPath -s $DeviceId shell "mv '$temp' '$RemoteRoot/SAVE_DATA'" 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Pre-upgrade SAVE_DATA restore failed" }
    if (Test-Path -LiteralPath $SentinelBackup -PathType Leaf) {
        Push-Checked -AdbPath $AdbPath -DeviceId $DeviceId -Local $SentinelBackup -Remote "$RemoteRoot/KNEEKURA_OFFLINE_MAX_BOOTSTRAP.json"
    }
}

$adbPath = Resolve-Adb -Explicit $Adb
$deviceId = Select-Device -AdbPath $adbPath -Requested $Device

$exportPath = [System.IO.Path]::GetFullPath($OwnedExport)
if (-not (Test-Path -LiteralPath $exportPath -PathType Leaf)) { throw "Owned export not found: $exportPath" }

$splitRoot = [System.IO.Path]::GetFullPath($SignedSplitDir)
if (-not (Test-Path -LiteralPath $splitRoot -PathType Container)) {
    throw "Signed research split directory not found: $splitRoot"
}
$sourceApks = @(Get-ChildItem -LiteralPath $splitRoot -Filter *.apk -File | Sort-Object Name)
if ($sourceApks.Count -ne 6) { throw "Expected exactly 6 signed research APK splits, found $($sourceApks.Count)" }

# adb.exe on Windows can mis-decode non-ASCII host paths. Always stage the
# signed split APKs under an ASCII-only path before install-multiple.
$systemDrive = if ($env:SystemDrive) { $env:SystemDrive } else { "C:" }
$asciiStageRoot = Join-Path $systemDrive ("KneekuraAdbStage\\persistence-" + $PID)
if ($asciiStageRoot -match "[^\x00-\x7F]") {
    throw "ASCII adb staging path unexpectedly contains non-ASCII characters: $asciiStageRoot"
}
if (Test-Path -LiteralPath $asciiStageRoot) {
    Remove-Item -LiteralPath $asciiStageRoot -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $asciiStageRoot | Out-Null

$stagedApks = @()
$splitHashes = @()
foreach ($sourceApk in $sourceApks) {
    if ($sourceApk.Name -match "[^\x00-\x7F]") {
        throw "APK filename is not ASCII-safe for adb staging: $($sourceApk.Name)"
    }

    $stagedPath = Join-Path $asciiStageRoot $sourceApk.Name
    Copy-Item -LiteralPath $sourceApk.FullName -Destination $stagedPath -Force

    $sourceHash = Get-Sha256 -Path $sourceApk.FullName
    $stagedHash = Get-Sha256 -Path $stagedPath
    if ($sourceHash -ne $stagedHash) {
        throw "Staged APK hash mismatch for $($sourceApk.Name)"
    }

    $stagedApks += $stagedPath
    $splitHashes += [ordered]@{
        name = $sourceApk.Name
        sha256 = $sourceHash
    }
}
if ($stagedApks.Count -ne 6) {
    throw "ASCII staging did not produce exactly 6 APKs"
}

$root = [System.IO.Path]::GetFullPath($OutDir)
New-Item -ItemType Directory -Force -Path $root | Out-Null
$logPath = Join-Path $root "offline-max-persistence-gate.log"
$log = New-Object System.Collections.Generic.List[string]

$remoteRoot = "/sdcard/Android/data/$Package/files"
$remoteSave = "$remoteRoot/SAVE_DATA"
$remoteSentinel = "$remoteRoot/KNEEKURA_OFFLINE_MAX_BOOTSTRAP.json"

if (-not (Test-RemotePath -AdbPath $adbPath -DeviceId $deviceId -RemotePath $remoteSave)) {
    throw "Research SAVE_DATA not found"
}
if (-not (Test-RemotePath -AdbPath $adbPath -DeviceId $deviceId -RemotePath $remoteSentinel)) {
    throw "Offline MAX bootstrap sentinel not found. Run the guarded MAX bootstrap first."
}

Write-Host "[1/6] Capturing the pre-install-r MAX state..."
& $adbPath -s $deviceId shell am force-stop $Package 2>$null | Out-Null
$preSave = Join-Path $root "pre-install-r-SAVE_DATA"
$preSentinel = Join-Path $root "pre-install-r-sentinel.json"
Pull-Checked -AdbPath $adbPath -DeviceId $deviceId -Remote $remoteSave -Local $preSave
Pull-Checked -AdbPath $adbPath -DeviceId $deviceId -Remote $remoteSentinel -Local $preSentinel
$preSha = Get-Sha256 -Path $preSave

$preVerify = Join-Path $root "pre-install-r-max-verification.json"
& python -m tools.base_mod.verify_offline_max_save $preSave $exportPath --output $preVerify --allow-runtime-rewrite | Out-Host
if ($LASTEXITCODE -ne 0) { throw "Pre-install-r SAVE_DATA no longer satisfies the MAX contract" }
$preVerifyObject = Get-Content -LiteralPath $preVerify -Raw | ConvertFrom-Json

Write-Host "[2/6] Confirming first persistence proof remains offline..."
$offline = (Read-Host "Are Wi-Fi and mobile data disabled? [y/n]").Trim().ToLowerInvariant()
if ($offline -notin @("y", "yes")) {
    Write-Host "Aborted before install -r. No package or SAVE_DATA change was made." -ForegroundColor Yellow
    exit 0
}

Write-Host "[3/6] Performing same-signature install-multiple -r without uninstall..."
Write-Host "      adb APK staging: $asciiStageRoot"
$installArgs = @("-s", $deviceId, "install-multiple", "--no-streaming", "-r") + $stagedApks

$oldErrorActionPreference = $ErrorActionPreference
$installOutput = @()
$installExitCode = $null
try {
    # Native stderr must be captured as install evidence rather than promoted to
    # a terminating PowerShell exception before LASTEXITCODE can be inspected.
    $ErrorActionPreference = "Continue"
    $installOutput = @(& $adbPath @installArgs 2>&1)
    $installExitCode = $LASTEXITCODE
}
finally {
    $ErrorActionPreference = $oldErrorActionPreference
}
$installOutput | ForEach-Object { $log.Add([string]$_) }

if ($installExitCode -ne 0) {
    $log.Add("ascii_stage_root=$asciiStageRoot")
    $log.Add("install_exit_code=$installExitCode")
    $log | Set-Content -LiteralPath $logPath -Encoding UTF8
    throw "adb install-multiple -r failed; SAVE_DATA was not modified by this runner and backup is at $preSave"
}

if (-not (Test-RemotePath -AdbPath $adbPath -DeviceId $deviceId -RemotePath $remoteSave)) {
    Restore-PreUpgradeSave -AdbPath $adbPath -DeviceId $deviceId -PackageName $Package -RemoteRoot $remoteRoot -SaveBackup $preSave -SentinelBackup $preSentinel
    throw "SAVE_DATA disappeared after install -r; pre-upgrade MAX save restored"
}
if (-not (Test-RemotePath -AdbPath $adbPath -DeviceId $deviceId -RemotePath $remoteSentinel)) {
    Restore-PreUpgradeSave -AdbPath $adbPath -DeviceId $deviceId -PackageName $Package -RemoteRoot $remoteRoot -SaveBackup $preSave -SentinelBackup $preSentinel
    throw "Bootstrap sentinel disappeared after install -r; pre-upgrade state restored"
}

Write-Host "[4/6] Launching original UI after install -r..."
$launchOutput = @(& $adbPath -s $deviceId shell am start -n "$Package/$Package.MyActivity" 2>&1)
$launchOutput | ForEach-Object { $log.Add([string]$_) }
Start-Sleep -Seconds 8
$uiOk = (Read-Host "Did the original UI open normally and still show the MAX profile? [y/n]").Trim().ToLowerInvariant()
if ($uiOk -notin @("y", "yes")) {
    Restore-PreUpgradeSave -AdbPath $adbPath -DeviceId $deviceId -PackageName $Package -RemoteRoot $remoteRoot -SaveBackup $preSave -SentinelBackup $preSentinel
    $log.Add("manual_ui_check=failed; pre-upgrade SAVE_DATA restored")
    $log | Set-Content -LiteralPath $logPath -Encoding UTF8
    exit 3
}

Write-Host "[5/6] Pulling and verifying post-install-r SAVE_DATA..."
$postSave = Join-Path $root "post-install-r-SAVE_DATA"
Pull-Checked -AdbPath $adbPath -DeviceId $deviceId -Remote $remoteSave -Local $postSave
$postSha = Get-Sha256 -Path $postSave
$postVerify = Join-Path $root "post-install-r-max-verification.json"
& python -m tools.base_mod.verify_offline_max_save $postSave $exportPath --output $postVerify --allow-runtime-rewrite | Out-Host
if ($LASTEXITCODE -ne 0) {
    Restore-PreUpgradeSave -AdbPath $adbPath -DeviceId $deviceId -PackageName $Package -RemoteRoot $remoteRoot -SaveBackup $preSave -SentinelBackup $preSentinel
    $log.Add("post_install_max_verification=failed; pre-upgrade SAVE_DATA restored")
    $log | Set-Content -LiteralPath $logPath -Encoding UTF8
    exit 4
}
$postVerifyObject = Get-Content -LiteralPath $postVerify -Raw | ConvertFrom-Json

Write-Host "[6/6] Recording persistence evidence..."
$preVerificationLevel = Get-OptionalProperty -Object $preVerifyObject -Name "verification_level" -DefaultValue "unknown"
$preLayoutProfile = Get-OptionalProperty -Object $preVerifyObject -Name "layout_profile" -DefaultValue "unknown"
$preSemanticComplete = [bool](Get-OptionalProperty -Object $preVerifyObject -Name "semantic_scope_complete" -DefaultValue $false)

$postVerificationLevel = Get-OptionalProperty -Object $postVerifyObject -Name "verification_level" -DefaultValue "unknown"
$postLayoutProfile = Get-OptionalProperty -Object $postVerifyObject -Name "layout_profile" -DefaultValue "unknown"
$postSemanticComplete = [bool](Get-OptionalProperty -Object $postVerifyObject -Name "semantic_scope_complete" -DefaultValue $false)

$fullSemanticPersistence = $preSemanticComplete -and $postSemanticComplete

$result = [ordered]@{
    schema_version = 1
    mode = "offline-max-install-r-persistence-gate"
    package = $Package
    signed_split_dir = $splitRoot
    signed_split_count = $sourceApks.Count
    adb_ascii_stage_root = $asciiStageRoot
    staged_split_count = $stagedApks.Count
    split_sha256 = $splitHashes
    install_r_success = $true
    uninstall_used = $false
    pre_install_save_sha256 = $preSha
    post_install_save_sha256 = $postSha
    sentinel_survived_install_r = $true
    pre_install_max_verification = $preVerify
    pre_install_verification_level = $preVerificationLevel
    pre_install_layout_profile = $preLayoutProfile
    pre_install_semantic_scope_complete = $preSemanticComplete
    post_install_max_verification = $postVerify
    post_install_verification_level = $postVerificationLevel
    post_install_layout_profile = $postLayoutProfile
    post_install_semantic_scope_complete = $postSemanticComplete
    full_semantic_persistence_verified = $fullSemanticPersistence
    original_ui_manual_check = $true
    network_disabled_confirmed_by_user = $true
    log = $logPath
}
$resultPath = Join-Path $root "offline-max-persistence-gate-result.json"
$result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $resultPath -Encoding UTF8
if ($fullSemanticPersistence) {
    $log.Add("persistence_gate=passed-full-semantic")
} else {
    $log.Add("persistence_gate=passed-stable-prefix-only")
}
$log | Set-Content -LiteralPath $logPath -Encoding UTF8

Write-Host ""
if ($fullSemanticPersistence) {
    Write-Host "Offline MAX install -r persistence gate passed (full semantic)." -ForegroundColor Green
} else {
    Write-Host "Offline MAX install -r persistence gate passed at stable-prefix scope; full semantic mapping is pending for this SAVE_DATA length." -ForegroundColor Yellow
}
Write-Host "Result: $resultPath"
Write-Host "Log:    $logPath"
