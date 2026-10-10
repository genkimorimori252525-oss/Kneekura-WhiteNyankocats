# READ ONLY - check original research six-split update signer BEFORE any -r install.
# Windows PowerShell 5.1; never installs, uninstalls, launches, stops or reads SAVE.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$CandidateSignedSplitDirectory,
    [string]$RepositoryRoot = (Join-Path $HOME 'Downloads\Kneekura-WhiteNyankocats')
)
$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
    throw 'Android SDK location unavailable (LOCALAPPDATA is empty)'
}
if (-not (Test-Path -LiteralPath $RepositoryRoot -PathType Container)) {
    throw 'Owner repository checkout is missing'
}
$repo = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$adb = Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe'
$apksigner = Join-Path $env:LOCALAPPDATA 'Android\Sdk\build-tools\35.0.0\apksigner.bat'
foreach ($file in @($adb, $apksigner)) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
        throw 'Android SDK platform-tools / build-tools 35.0.0 not installed at owner confirmed path'
    }
}
$module = Join-Path $repo 'tools\base_mod\preflight_original_device_update.py'
if (-not (Test-Path -LiteralPath $module -PathType Leaf)) {
    throw 'GitHub research checkout is stale; update existing branch first'
}
if (-not (Test-Path -LiteralPath $CandidateSignedSplitDirectory -PathType Container)) {
    throw 'Signed original research six-split candidate directory missing'
}
Push-Location $repo
try {
    $commandArgs = @(
        '-3.12', '-m', 'tools.base_mod.preflight_original_device_update',
        '--repo', $repo,
        '--candidate', $CandidateSignedSplitDirectory,
        '--adb', $adb,
        '--apksigner', $apksigner
    )
    & py @commandArgs
    if ($LASTEXITCODE -ne 0) {
        throw 'Installed research signing certificate preflight BLOCKED; DO NOT INSTALL'
    }
} finally {
    Pop-Location
}
Write-Host 'READ_ONLY_DEVICE_SIGNER_PASS; NO APK INSTALL OR SAVE ACTION' -ForegroundColor Green
Write-Host 'Only the separate research jp.kn.local.battlecats was examined.'
Write-Host 'This did not prove first-boot gameplay, Level60 or complete offline egress.'
