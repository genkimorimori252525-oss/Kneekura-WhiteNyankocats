# Owner Windows 11 private research preparation; safe by default.
# No -DoBuild: read-only validation only, no signing key/password input,
# no ADB, publisher game/SAVE, uninstall, signed APK output, or download.
# -DoBuild: passes vetted local inputs to BUILD-OWNER-RESEARCH-PAIR.ps1,
# which interactively requests the owner's EXISTING research signing password.
[CmdletBinding()]
param(
    [switch]$DoBuild,
    [switch]$EnableOfflineServerImport,
    [switch]$RequireScene97ResolverWitness,
    [string]$ResearchShimFolder,
    [string]$SigningAlias,
    [string]$RepositoryRoot = (Join-Path $HOME 'Downloads\Kneekura-WhiteNyankocats')
)
$ErrorActionPreference = 'Stop'
function Require-One([array]$paths, [string]$label) {
    if ($paths.Count -ne 1) {
        throw ('Expected exactly one existing private ' + $label +
               ' (found ' + $paths.Count + '); no action performed')
    }
    $item = $paths[0]
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw ('Untrusted symlink found in private ' + $label)
    }
    return $item.FullName
}
function Digest([string]$file) {
    return (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
}
$repo = (Resolve-Path -LiteralPath $RepositoryRoot -ErrorAction Stop).Path
if ((git -C $repo branch --show-current).Trim() -ne 'jolly/balance-madoka-godzilla-2026-10-09') {
    throw 'Not the CURRENT.md active original-game research branch'
}
$private = Join-Path $repo 'private'
if (-not (Test-Path -LiteralPath $private -PathType Container)) {
    throw 'Owner private source folder unavailable'
}
if (((Get-Item -LiteralPath $private).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
    throw 'Owner private source folder is a symlink'
}
$ownerExport = Join-Path $HOME 'Downloads\にーくらにゃんこ\nyanko_battlecats_2026-10-06.zip'
if (-not (Test-Path -LiteralPath $ownerExport -PathType Leaf)) {
    throw 'Existing owned original JP15.7.1 export absent'
}
if ((Digest $ownerExport) -ne '38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56') {
    throw 'Original game source checksum does not match CURRENT.md'
}
$official = Join-Path $private 'official-shadowhook-2.0.1.aar'
if (-not (Test-Path -LiteralPath $official -PathType Leaf) -or
    (Digest $official) -ne '2cad01ff4d59542958775e19f281981a7e84b39670b5fae75905b8511e10c7cd') {
    throw 'Official paired ShadowHook AAR is missing or does not match verified hash'
}
$nativeFolders = @(Get-ChildItem -LiteralPath $private -Directory -Filter 'passive-arm64-public-*')
if (-not [string]::IsNullOrWhiteSpace($ResearchShimFolder)) {
    # The opt-in new observer must come from an EXPLICIT new private folder,
    # never silently select one among old and new compiled artifacts.
    if (-not $RequireScene97ResolverWitness) {
        throw 'EXPLICIT_SCENE97_SHIM_REQUIRES_DIAGNOSTIC_MODE_NO_ACTION'
    }
    $nativeFolder = (Resolve-Path -LiteralPath $ResearchShimFolder -ErrorAction Stop).Path
    $privatePrefix = $private.TrimEnd([IO.Path]::DirectorySeparatorChar) +
        [IO.Path]::DirectorySeparatorChar
    if (-not $nativeFolder.StartsWith(
            $privatePrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'EXPLICIT_SCENE97_SHIM_MUST_BE_INSIDE_PRIVATE_NO_ACTION'
    }
    $walk = Get-Item -LiteralPath $nativeFolder -ErrorAction Stop
    if (-not $walk.PSIsContainer) {
        throw 'EXPLICIT_SCENE97_SHIM_NOT_A_FOLDER_NO_ACTION'
    }
    while ($null -ne $walk -and
           $walk.FullName.StartsWith(
               $privatePrefix, [StringComparison]::OrdinalIgnoreCase)) {
        if (($walk.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw 'EXPLICIT_SCENE97_SHIM_SYMLINK_NO_ACTION'
        }
        $walk = $walk.Parent
    }
} else {
    $nativeFolder = Require-One $nativeFolders 'PASSIVE ARM64 compiler artifact folder'
}
$native = Join-Path $nativeFolder 'libkneekura.so'
$passiveShimReceipt = Join-Path $nativeFolder 'PUBLIC_PASSIVE_SHIM_RECEIPT.json'
if (-not (Test-Path -LiteralPath $native -PathType Leaf) -or
    -not (Test-Path -LiteralPath $passiveShimReceipt -PathType Leaf)) {
    throw 'CI-built passive ARM64 native receipt and binary are incomplete'
}
$nativeProof = Get-Content -LiteralPath $passiveShimReceipt -Raw -Encoding UTF8 | ConvertFrom-Json
if ($nativeProof.schema -ne 'public-original-research-passive-shim-v1' -or
    $nativeProof.original_save_writer_enabled -ne $false -or
    $nativeProof.fixed_error_markers_compiled -ne $true -or
    (Digest $native) -ne $nativeProof.sha256) {
    throw 'The pinned no-SAVE-writer native artifact does not match its source receipt'
}
if ($RequireScene97ResolverWitness -and
    $nativeProof.scene97_resolver_histogram_compiled -ne $true) {
    throw 'SCENE97_OBSERVER_RECEIPT_NOT_ATTESTED_NO_BUILD_OR_INSTALL'
}
& git -C $repo merge-base --is-ancestor $nativeProof.git_commit HEAD
if ($LASTEXITCODE -ne 0) { throw 'PASSIVE ARM64 compiler source not in current Git history' }
$keystore = Require-One @(
    Get-ChildItem -LiteralPath $private -Recurse -File -ErrorAction Stop |
        Where-Object { $_.Extension -in @('.p12', '.jks', '.keystore') }
) 'existing research signing key'
# Avoid confusing the UNSIGNED source-preserving test outputs with an
# already installed research baseline signed base APK.
$previousBase = Require-One @(
    Get-ChildItem -LiteralPath $private -Recurse -File -Filter 'base.apk' |
        Where-Object {
            $_.FullName -notlike '*\unsigned-original-native-pair-*' -and
            $_.FullName -notlike '*\passive-arm64-public-*' -and
            # A failed rebuild leaves .static-http-work/original-splits,
            # bootstrap/bridge intermediates and sometimes a partial APK.
            # None is a trustworthy previously INSTALLED signed baseline.
            $_.FullName -notmatch '[\\/]official-shadowhook-pair-passive-[^\\/]+[\\/]'
        }
) 'previously signed local research base.apk'
$sdk = Join-Path $env:LOCALAPPDATA 'Android\Sdk'
$signer = Join-Path $sdk 'build-tools\35.0.0\apksigner.bat'
if (-not (Test-Path -LiteralPath $signer -PathType Leaf)) {
    throw 'Owner confirmed Android SDK35 apksigner not found'
}
# Java 17/21 may print harmless restricted-method warnings to stderr.
# Windows PowerShell 5.1 with ErrorActionPreference Stop incorrectly treats
# native stderr as a terminating PowerShell error even when exit code is 0.
# Capture/discard only this metadata-only tool's output, then inspect EXIT CODE.
$priorPreference = $ErrorActionPreference
try {
    $ErrorActionPreference = 'Continue'
    & $signer verify --print-certs $previousBase 1>$null 2>$null
    $certificateVerifyExit = $LASTEXITCODE
} finally {
    $ErrorActionPreference = $priorPreference
}
if ($certificateVerifyExit -ne 0) {
    throw 'The proposed old research base APK is not a valid signed APK'
}
# Earlier SAFE unsigned candidates may coexist; never delete owner files
# merely to choose the current opt-in offline import profile. Require a
# complete native/source gate whose mode matches this explicit build switch.
$unsignedCandidates = @(Get-ChildItem -LiteralPath $private -Directory -Filter 'unsigned-original-native-pair-*' |
    Sort-Object LastWriteTime -Descending)
$presignReport = $null
$proof = $null
foreach ($stage in $unsignedCandidates) {
    if (($stage.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        continue
    }
    $unsignedStageReceipt = Join-Path $stage.FullName 'UNSIGNED-RESEARCH-RECEIPT.json'
    if (-not (Test-Path -LiteralPath $unsignedStageReceipt -PathType Leaf)) {
        continue
    }
    $candidateProof = Get-Content -LiteralPath $unsignedStageReceipt -Raw -Encoding UTF8 | ConvertFrom-Json
    if ([bool]$candidateProof.owner_original_393_file_import_feature_opt_in -eq [bool]$EnableOfflineServerImport) {
        $presignReport = $unsignedStageReceipt
        $proof = $candidateProof
        break
    }
}
if ($null -eq $proof) {
    throw 'No original private unsigned source parity proof for this selected import mode'
}
if ($proof.status -ne 'PASS_PRIVATE_UNSIGNED_ORIGINAL_SIX_SPLITS_NOT_INSTALLABLE' -or
    $proof.exact_original_native_presign_status -ne 'PINNED_REPACKAGED_JP1571_ORIGINAL_SCENE_VMA_AND_EXPORT_VERIFIED' -or
    ($proof.unsigned_original_splits_sha256 | Get-Member -MemberType NoteProperty).Count -ne 6) {
    throw 'Private JP15.7.1 original native source parity is not yet accepted'
}
Write-Host 'OWNER_PRIVATE_ORIGINAL_BUILD_INPUTS_READY_NO_DEVICE_OR_KEY_USED' -ForegroundColor Green
Write-Host 'Verified: 6 real original unsigned research APKs, official 2-native ShadowHook, CI passive ARM64.'
if (-not $DoBuild) {
    Write-Host 'Read-only PREPARED state only. No signing or Android updates performed.'
    Write-Host 'When personally ready: run this script again with -DoBuild (then enter original research alias and private password).'
    return
}
if ([string]::IsNullOrWhiteSpace($SigningAlias)) {
    $SigningAlias = Read-Host 'EXISTING research key alias (required; not the password; Enter alone cancels)'
}
if ([string]::IsNullOrWhiteSpace($SigningAlias)) {
    # A blank prompt means no user-supplied alias. It does NOT prove the
    # keystore lacks an alias or that a password is incorrect.
    # Do not open a keystore, prompt for a secret, rebuild or install.
    throw 'RESEARCH_SIGNING_ALIAS_MISSING_NO_ACTION: rerun with -DoBuild -SigningAlias "<existing research key alias>"'
}
if ($SigningAlias -notmatch '^[A-Za-z0-9._-]{1,80}$') {
    throw 'RESEARCH_SIGNING_ALIAS_FORMAT_INVALID_NO_ACTION'
}
$buildScript = Join-Path $PSScriptRoot 'BUILD-OWNER-RESEARCH-PAIR.ps1'
if (-not (Test-Path -LiteralPath $buildScript -PathType Leaf)) {
    throw 'Existing private build-only owner script unavailable'
}
# This call signs ONLY local derived original research APKs. It does NOT install
# anything or access the phone. The target script asks for the private password.
& $buildScript -RepositoryRoot $repo -OwnerExportZip $ownerExport `
    -PassiveShimSo $native -PassiveShimReceipt $passiveShimReceipt `
    -ResearchKeystore $keystore -PreviouslySignedBaseApk $previousBase `
    -SigningAlias $SigningAlias -OfficialShadowHookAar $official `
    -EnableOfflineServerImport:$EnableOfflineServerImport
if (-not $?) {
    throw 'Existing-signer original build was not successful; nothing installed'
}
Write-Host 'Private signing completed, but REAL DEVICE SIGNER PREFLIGHT is still required.' -ForegroundColor Yellow
