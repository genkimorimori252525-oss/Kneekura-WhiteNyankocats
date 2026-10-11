# Original JP15.7.1 isolated research: build-only, reuse the EXISTING research signer.
# PowerShell 5.1. NEVER installs/restarts/clears any Android application or SAVE.
# Inputs: owner original ZIP, public PASSIVE C shim + CI SHA receipt, official
# ByteDance ShadowHook 2.0.1 AAR, owner's existing PRIVATE research .p12.
[CmdletBinding()]
param(
    [string]$RepositoryRoot = (Join-Path $HOME 'Downloads\Kneekura-WhiteNyankocats'),
    [string]$OwnerExportZip = (Join-Path $HOME 'Downloads\にーくらにゃんこ\nyanko_battlecats_2026-10-06.zip'),
    [Parameter(Mandatory=$true)][string]$PassiveShimSo,
    [Parameter(Mandatory=$true)][string]$PassiveShimReceipt,
    [Parameter(Mandatory=$true)][string]$ResearchKeystore,
    [Parameter(Mandatory=$true)][string]$PreviouslySignedBaseApk,
    [Parameter(Mandatory=$true)][string]$SigningAlias,
    [string]$OfficialShadowHookAar
)
$ErrorActionPreference = 'Stop'
$package = 'jp.kn.local.battlecats'
$expectedOwnerSha = '38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56'
$expectedAarSha = '2cad01ff4d59542958775e19f281981a7e84b39670b5fae75905b8511e10c7cd'
function RequireFile([string]$path, [string]$label) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required owner-private file is missing: $label"
    }
    $item = Get-Item -LiteralPath $path
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Owner-private symlink/reparse point refused: $label"
    }
    return $item.FullName
}
function Sha256([string]$path) {
    return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
}
function SignerDigest([string]$path, [string]$tool) {
    # Native Java tools can warn on stderr while returning success. PowerShell
    # 5.1 ErrorAction Stop must not turn those warnings into false failures.
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $result = @(& $tool verify --print-certs $path 2>&1)
        $verifyExit = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    if ($verifyExit -ne 0) { throw 'Previously signed or new base APK certificate audit failed' }
    $matchingLines = @($result | Where-Object { $_ -match '(?i)Signer #1 certificate SHA-256 digest:\s*([a-f0-9:]+)' })
    if ($matchingLines.Count -ne 1) { throw 'Exactly one primary APK signing certificate digest is required' }
    if ($matchingLines[0] -notmatch '(?i)Signer #1 certificate SHA-256 digest:\s*([a-f0-9:]+)') {
        throw 'Unable to parse a trusted Android signing-certificate digest'
    }
    $digest = $Matches[1]
    return $digest.Replace(':','').ToLowerInvariant()
}
$repo = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$zip = RequireFile $OwnerExportZip 'original JP15.7.1 owner export ZIP'
$shim = RequireFile $PassiveShimSo 'CI-compiled passive research shim'
$receiptPath = RequireFile $PassiveShimReceipt 'CI passive shim SHA receipt'
$keystore = RequireFile $ResearchKeystore 'existing isolated research signing keystore'
$existingBase = RequireFile $PreviouslySignedBaseApk 'previously installed research signed base.apk'
if (-not (Test-Path -LiteralPath (Join-Path $repo 'CURRENT.md') -PathType Leaf)) {
    throw 'The exact Kneekura research repository checkout is missing'
}
$buildSource = Join-Path $repo 'tools\base_mod\prepare_original_scene_witness.py'
$buildSource = RequireFile $buildSource 'official two-library research build source'
if (-not ((Get-Content -LiteralPath $buildSource -Raw) -match 'EXTRA_NATIVE_COMPANION_ENTRY')) {
    throw 'Repository checkout is stale: official ShadowHook pair support missing'
}
$branch = (& git -C $repo branch --show-current 2>$null | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $branch -ne 'jolly/balance-madoka-godzilla-2026-10-09') {
    throw 'Expected the existing active research branch; do not rebuild from unrelated branch'
}
if ((Sha256 $zip) -ne $expectedOwnerSha) { throw 'Owner original export ZIP checksum differs' }
$receipt = Get-Content -LiteralPath $receiptPath -Raw | ConvertFrom-Json
if ($receipt.schema -ne 'public-original-research-passive-shim-v1' -or
    $receipt.original_save_writer_enabled -ne $false -or
    $receipt.fixed_error_markers_compiled -ne $true -or
    $receipt.elf_abi -ne 'arm64-v8a' -or
    $receipt.sha256 -notmatch '^[a-f0-9]{64}$' -or
    $receipt.git_commit -notmatch '^[a-f0-9]{40}$' -or
    (Sha256 $shim) -ne $receipt.sha256) {
    throw 'Public passive research shim receipt/hash is invalid'
}
& git -C $repo merge-base --is-ancestor $receipt.git_commit HEAD 2>$null
if ($LASTEXITCODE -ne 0) {
    throw 'CI passive native shim is not from the current repository history'
}
if ($SigningAlias -notmatch '^[a-zA-Z0-9._-]{1,80}$') {
    throw 'Unsafe or empty existing research signing alias'
}
# No ADB invoked; this is build-only. The separately installed PONOS app is untouched.
$sdk = Join-Path $env:LOCALAPPDATA 'Android\Sdk'
$toolDir = Join-Path $sdk 'build-tools\35.0.0'
$zipalign = RequireFile (Join-Path $toolDir 'zipalign.exe') 'zipalign 35'
$apksigner = RequireFile (Join-Path $toolDir 'apksigner.bat') 'apksigner 35'
$d8 = RequireFile (Join-Path $toolDir 'd8.bat') 'd8 35'
$androidJar = RequireFile (Join-Path $sdk 'platforms\android-35\android.jar') 'Android API 35'
$javac = (Get-Command javac.exe -ErrorAction SilentlyContinue)
if ($null -ne $javac) {
    $javacPath = $javac.Source
} else {
    $javacPath = RequireFile 'C:\Program Files\Android\Android Studio\jbr\bin\javac.exe' 'Java compiler 17'
}
if ([string]::IsNullOrWhiteSpace($OfficialShadowHookAar)) {
    $OfficialShadowHookAar = Join-Path $repo 'private\official-shadowhook-2.0.1.aar'
}
if (-not (Test-Path -LiteralPath $OfficialShadowHookAar -PathType Leaf)) {
    $targetParent = Split-Path -Parent $OfficialShadowHookAar
    if (-not (Test-Path -LiteralPath $targetParent -PathType Container)) {
        New-Item -ItemType Directory -Path $targetParent -Force | Out-Null
    }
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $url = 'https://repo.maven.apache.org/maven2/com/bytedance/android/shadowhook/2.0.1/shadowhook-2.0.1.aar'
    Write-Host 'Fetching PUBLIC official MIT ShadowHook AAR to private local disk...'
    Invoke-WebRequest -Uri $url -OutFile $OfficialShadowHookAar -UseBasicParsing
}
$aar = RequireFile $OfficialShadowHookAar 'official Maven ShadowHook 2.0.1 AAR'
if ((Sha256 $aar) -ne $expectedAarSha) {
    throw 'Official ShadowHook AAR SHA256 differs from vetted Maven original'
}
if (Test-Path -LiteralPath $keystore -PathType Leaf) {
    Write-Host 'Existing signing keystore found; this script will NEVER generate a replacement.'
}
# Non-destructive candidate directory. No Android install commands exist here.
$privateRoot = Join-Path $repo 'private'
if (-not (Test-Path -LiteralPath $privateRoot -PathType Container)) {
    New-Item -ItemType Directory -Path $privateRoot -Force | Out-Null
}
$unique = [Guid]::NewGuid().ToString('N')
$out = Join-Path $privateRoot ('official-shadowhook-pair-passive-' + $unique)
# Do not create another ~166 MB staging directory before the alias/password/
# existing-cert check succeeds. A rejected key leaves no new private output.
$secure = Read-Host 'Password for the EXISTING research keystore (not the publisher key)' -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $password = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}
# A fresh process-only variable name avoids passing the owner's password in
# PowerShell/Python/apksigner command lines. Never persist it to disk/registry.
$secretEnvName = 'KNEEKURA_OWNER_SIGN_' + [Guid]::NewGuid().ToString('N').ToUpperInvariant()
[Environment]::SetEnvironmentVariable($secretEnvName, $password, 'Process')
$password = $null
try {
    # Check the existing owner research keystore BEFORE rebuilding ~166 MiB
    # of original game APKs. If the alias or password is wrong, no new signed
    # private candidate is attempted and no raw Java error/password is shown.
    $keytoolPath = Join-Path (Split-Path -Parent $javacPath) 'keytool.exe'
    $keytoolPath = RequireFile $keytoolPath 'existing local JDK keytool'
    Push-Location $repo
    try {
        $signerPreflightArgs = @(
            '-3.12', '-m', 'tools.base_mod.verify_original_research_signer',
            '--keystore', $keystore, '--alias', $SigningAlias,
            '--storepass-env', $secretEnvName,
            '--previous-signed-base', $existingBase,
            '--keytool', $keytoolPath, '--apksigner', $apksigner
        )
        & py @signerPreflightArgs
        if ($LASTEXITCODE -ne 0) {
            throw 'EXISTING_RESEARCH_KEYSTORE_PREFLIGHT_BLOCKED_NO_SIGNING_ATTEMPT'
        }
        if (Test-Path -LiteralPath $out) {
            throw 'Refuse to overwrite an existing private build directory'
        }
        New-Item -ItemType Directory -Path $out -ErrorAction Stop | Out-Null
        $buildArgs = @(
            '-3.12', '-m', 'tools.base_mod.build_owned_static_http_bridge',
            $zip, '--flavor', 'local-research',
            '--shim', $shim, '--keystore', $keystore,
            '--alias', $SigningAlias,
            '--storepass-env', $secretEnvName, '--keypass-env', $secretEnvName,
            '--research-no-internet-permission',
            '--research-shadowhook-aar', $aar,
            '--zipalign', $zipalign, '--apksigner', $apksigner,
            '--javac', $javacPath, '--d8', $d8, '--android-jar', $androidJar,
            '--root', $repo, '--output', $out
        )
        & py @buildArgs 1> (Join-Path $out 'PRIVATE-build-receipt.json')
        if ($LASTEXITCODE -ne 0) { throw 'Static research AAR-pair build did not pass' }
    } finally {
        Pop-Location
    }
} finally {
    [Environment]::SetEnvironmentVariable($secretEnvName, $null, 'Process')
    $password = $null
    $secure.Dispose()
}
$signed = Join-Path $out 'local-research-static-http-signed-splits'
# Bind the signed 6-split candidate to the same validated public-only
# PASSIVE native shim/CI receipt. Never put the owner's game or passwords
# in this receipt. The independent read-only device preflight requires it.
$copiedReceipt = Join-Path $signed 'PASSIVE_SHIM_BUILD_SOURCE_RECEIPT.json'
if (Test-Path -LiteralPath $copiedReceipt) {
    throw 'Unexpected existing signed candidate source receipt; do not overwrite'
}
Copy-Item -LiteralPath $receiptPath -Destination $copiedReceipt -ErrorAction Stop
$newBase = RequireFile (Join-Path $signed 'base.apk') 'newly signed research base APK'
$before = SignerDigest $existingBase $apksigner
$after = SignerDigest $newBase $apksigner
if ($before -ne $after) {
    throw 'Research APK signer differs from PREVIOUSLY installed baseline. Do NOT install this build.'
}
$requiredApks = @('base.apk', 'split_config.arm64_v8a.apk',
    'split_config.en.apk', 'split_config.ja.apk',
    'split_config.xxhdpi.apk', 'split_InstallPack.apk')
foreach ($name in $requiredApks) {
    [void](RequireFile (Join-Path $signed $name) ('six-split research output ' + $name))
}
@(
 'BUILD_ONLY_STATIC_PASS; PROVIDED_PREVIOUS_SIGNED_BASE_CERT_MATCHED',
 'The supplied previous signed APK matches the new certificate; installed device signer NOT independently checked.',
 'Before any -r device update, compare with the actual installed isolated package signer read-only.',
 'This did not install, uninstall, force-stop, log in, or touch any Android SAVE.',
 'This is passive hook observation only; virgin SAVE writer NOT enabled.',
 'Original gameplay, boot, assets, 0 SDK/IPC egress and Level60 NOT verified.'
) | Out-File -LiteralPath (Join-Path $out 'PRIVATE-BUILD-STATUS.txt') -Encoding utf8
Write-Host 'BUILD_ONLY_PASS; PROVIDED_PREVIOUS_SIGNED_BASE_CERT_MATCHED' -ForegroundColor Green
Write-Host ('PRIVATE six-split output: ' + $signed)
Write-Host 'No device actions were performed. Installed package signer is NOT yet checked; do NOT install until device preflight.'
