# One owner-local secret prompt. Everything else is fail-closed and automatic.
# JP15.7.1 ORIGINAL six-split isolated research package only.
# No publisher app, SAVE clearing, new signing key, Wi-Fi mode changes, or downloads.
# Owner already authorized the guarded research update and boot capture.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\base_mod\OWNER-OFFLINE-615-ONE-SHOT.ps1
[CmdletBinding()]
param(
    [string]$RepositoryRoot = (Join-Path $HOME 'Downloads\Kneekura-WhiteNyankocats'),
    [string]$SigningAlias = '252525',
    [switch]$OnlyPreflight
)
$ErrorActionPreference = 'Stop'
function Require-SafeExistingFile([string]$path) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw 'MISSING_REQUIRED_OWNER_TOOL' }
    if (((Get-Item -LiteralPath $path).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw 'UNTRUSTED_OWNER_TOOL_SYMLINK'
    }
    return $path
}
$repo = (Resolve-Path -LiteralPath $RepositoryRoot -ErrorAction Stop).Path
if ((git -C $repo branch --show-current).Trim() -ne 'jolly/balance-madoka-godzilla-2026-10-09') {
    throw 'INCORRECT_ORIGINAL_GAME_BRANCH_NO_ACTION'
}
$dirty = @(git -C $repo status --porcelain=v1)
if ($dirty.Count) { throw 'DIRTY_GIT_WORKTREE_NO_ACTION' }
if ($SigningAlias -notmatch '^[A-Za-z0-9._-]{1,80}$') { throw 'UNSAFE_SIGNING_ALIAS_HINT_NO_ACTION' }
$private = Join-Path $repo 'private'
if (-not (Test-Path -LiteralPath $private -PathType Container) -or
    ((Get-Item -LiteralPath $private).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
    throw 'OWNER_PRIVATE_ROOT_MISSING_OR_UNSAFE'
}
$adb = Require-SafeExistingFile (Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe')
$signer = Require-SafeExistingFile (Join-Path $PSScriptRoot 'OWNER-READY-TO-SIGN.ps1')
$stager = Require-SafeExistingFile (Join-Path $PSScriptRoot 'stage_original_393_to_research_device.py')
$checker = Require-SafeExistingFile (Join-Path $PSScriptRoot 'CHECK-OWNER-RESEARCH-DEVICE-SIGNER.ps1')
$installer = Require-SafeExistingFile (Join-Path $PSScriptRoot 'INSTALL-OWNER-RESEARCH-PAIR.ps1')
$collector = Require-SafeExistingFile (Join-Path $PSScriptRoot 'CAPTURE-OWNER-ORIGINAL-CRASH.ps1')
$audit = Require-SafeExistingFile (Join-Path $PSScriptRoot 'audit_original_offline_boot_events.py')
$candidates = @(Get-ChildItem -LiteralPath $private -Directory -Filter 'official-shadowhook-pair-passive-*')
$before = @{}
foreach ($item in $candidates) { $before[$item.FullName] = $true }
$devices = @(& $adb devices | Where-Object { $_ -match '^\S+\s+device\s*$' })
if ($LASTEXITCODE -ne 0 -or $devices.Count -ne 1) { throw 'ONE_AUTHORIZED_RESEARCH_DEVICE_REQUIRED_NO_ACTION' }
$device = ($devices[0] -split '\s+')[0]
$installed = @(& $adb -s $device shell pm path jp.kn.local.battlecats 2>$null)
if ($LASTEXITCODE -ne 0 -or @($installed | Where-Object { $_ -match '^package:/' }).Count -ne 6) {
    throw 'EXISTING_ISOLATED_ORIGINAL_SIX_SPLITS_REQUIRED'
}
$source = Join-Path $private 'original-jp1571-verified-server-cache'
if (-not (Test-Path -LiteralPath $source -PathType Container)) { throw 'ORIGINAL_358_MD5_CACHE_MISSING' }
$older = Join-Path $private 'official-shadowhook-pair-passive-ed7e7899518143f3bda6bbbc7f1660c4\local-research-static-http-signed-splits'
if (-not (Test-Path -LiteralPath $older -PathType Container)) {
    throw 'PINNED_ORIGINAL_OWNER_INSTALLPACK_MISSING'
}
Push-Location -LiteralPath $repo
try {
    $prepareArgs = @('-3.12','-m','tools.base_mod.stage_original_393_to_research_device',
        '--repo',$repo,'--candidate',$older,'--cache',$source,'--adb',$adb)
    if ($OnlyPreflight) {
        & py @prepareArgs
        if ($LASTEXITCODE -ne 0) { throw 'OWNER_393_SOURCE_PREFLIGHT_BLOCKED' }
        & powershell -NoProfile -ExecutionPolicy Bypass -File $signer -RepositoryRoot $repo -EnableOfflineServerImport
        if ($LASTEXITCODE -ne 0) { throw 'OWNER_SIGNING_INPUTS_NOT_READY' }
        Write-Host 'OWNER_OFFLINE_ONE_SHOT_READONLY_PREFLIGHT_PASS'
        return
    }
    # The 393 exact original assets must exist in OUR package's own staging
    # area. May repair only a bad-MD5 file inside that fixed isolated stage.
    & py @prepareArgs --stage --repair-incomplete
    if ($LASTEXITCODE -ne 0) { throw 'ORIGINAL_393_EXTERNAL_STAGE_BLOCKED_NO_INSTALL' }
    Write-Host 'ALL_393_ORIGINAL_EXTERNAL_ASSETS_MD5_VERIFIED'
    # This is the ONLY step requiring the owner's secret. The original
    # child script itself prompts on the owner's local PowerShell console.
    # We never read, store, log or forward the private password.
    & powershell -NoProfile -ExecutionPolicy Bypass -File $signer -RepositoryRoot $repo -DoBuild -SigningAlias $SigningAlias -EnableOfflineServerImport
    if ($LASTEXITCODE -ne 0) { throw 'OWNER_PRIVATE_SIGNING_FAILED_NO_INSTALL' }
    $after = @(Get-ChildItem -LiteralPath $private -Directory -Filter 'official-shadowhook-pair-passive-*' |
        Where-Object { -not $before.ContainsKey($_.FullName) })
    if ($after.Count -ne 1) { throw 'EXPECTED_EXACTLY_ONE_NEW_OWNER_SIGNED_APK_FOLDER' }
    $build = $after[0]
    if (($build.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw 'NEW_SIGNED_RESEARCH_FOLDER_SYMLINK'
    }
    $signed = Join-Path $build.FullName 'local-research-static-http-signed-splits'
    if (@(Get-ChildItem -LiteralPath $signed -File -Filter '*.apk').Count -ne 6) {
        throw 'NEW_SIGNED_ORIGINAL_SIX_SPLIT_COUNT_MISMATCH'
    }
    & powershell -NoProfile -ExecutionPolicy Bypass -File $checker -RepositoryRoot $repo -CandidateSignedSplitDirectory $signed
    if ($LASTEXITCODE -ne 0) { throw 'REAL_INSTALLED_RESEARCH_SIGNER_MISMATCH_NO_INSTALL' }
    $devicesNow = @(& $adb devices | Where-Object { $_ -match '^\S+\s+device\s*$' })
    if ($devicesNow.Count -ne 1 -or ($devicesNow[0] -split '\s+')[0] -ne $device) {
        throw 'ANDROID_DEVICE_CHANGED_AFTER_SIGNING_ABORT'
    }
    # Only the already-approved distinct app; no PONOS app, no pm clear.
    & $adb -s $device shell am force-stop jp.kn.local.battlecats
    if ($LASTEXITCODE -ne 0) { throw 'ISOLATED_RESEARCH_STOP_FAILED_NO_INSTALL' }
    Start-Sleep -Seconds 2
    $running = (@(& $adb -s $device shell pidof jp.kn.local.battlecats 2>$null) -join '').Trim()
    if ($running -match '^\d+$') { throw 'ISOLATED_RESEARCH_STILL_RUNNING_ABORT' }
    & powershell -NoProfile -ExecutionPolicy Bypass -File $installer -RepositoryRoot $repo -CandidateSignedSplitDirectory $signed -ApproveUpdateOfIsolatedResearchApp
    if ($LASTEXITCODE -ne 0) { throw 'ONE_RESEARCH_UPDATE_FAILED_DO_NOT_RETRY' }
    $capture = Join-Path $private 'original-crash-captures'
    $known = @{}
    if (Test-Path -LiteralPath $capture -PathType Container) {
        Get-ChildItem -LiteralPath $capture -File -Filter '*-filtered-logcat-PRIVATE.txt' | ForEach-Object { $known[$_.FullName] = $true }
    }
    & powershell -NoProfile -ExecutionPolicy Bypass -File $collector -RepositoryRoot $repo -ObserveSeconds 30
    if ($LASTEXITCODE -ne 0) { throw 'ORIGINAL_GAME_SINGLE_BOOT_CAPTURE_BLOCKED_NO_RETRY' }
    $newLogs = @(Get-ChildItem -LiteralPath $capture -File -Filter '*-filtered-logcat-PRIVATE.txt' |
        Where-Object { -not $known.ContainsKey($_.FullName) })
    if ($newLogs.Count -ne 1) { throw 'ONE_OWNER_PRIVATE_ORIGINAL_CAPTURE_REQUIRED' }
    & py -3.12 -m tools.base_mod.audit_original_offline_boot_events --repo $repo --private-log $newLogs[0].FullName
    if ($LASTEXITCODE -ne 0) { throw 'PRIVATE_BOOT_EVENT_AUDIT_FAILED' }
    Write-Host 'RESEARCH_ONLY_SIGNED_UPDATED_AND_SINGLE_BOOT_OBSERVED_CHECK_BASE_SEPARATELY'
    Write-Host 'No PONOS package, SAVE clear, device connectivity settings or new key touched.'
} finally {
    Pop-Location
}
