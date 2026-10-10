# Original JP15.7.1 isolated research app six-split update (Windows PowerShell 5.1)
# Does NOTHING without explicit -ApproveUpdateOfIsolatedResearchApp.
# Never touches publisher app, does not uninstall, clear SAVE, downgrade or launch.
# The Python core preflights actual installed signer and all six candidate APKs.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$CandidateSignedSplitDirectory,
    [Parameter(Mandatory=$true)][switch]$ApproveUpdateOfIsolatedResearchApp,
    [string]$RepositoryRoot = (Join-Path $HOME 'Downloads\Kneekura-WhiteNyankocats')
)
$ErrorActionPreference = 'Stop'
if (-not $ApproveUpdateOfIsolatedResearchApp) {
    throw 'Explicit isolated research app update approval is required; nothing changed'
}
if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
    throw 'Owner Android SDK location unavailable'
}
if (-not (Test-Path -LiteralPath $RepositoryRoot -PathType Container)) {
    throw 'Owner repository folder unavailable'
}
$repo = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$adb = Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe'
$apksigner = Join-Path $env:LOCALAPPDATA 'Android\Sdk\build-tools\35.0.0\apksigner.bat'
$core = Join-Path $repo 'tools\base_mod\update_original_isolated_research.py'
foreach ($file in @($adb, $apksigner, $core)) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
        throw 'Required validated owner research tool unavailable'
    }
}
if (-not (Test-Path -LiteralPath $CandidateSignedSplitDirectory -PathType Container)) {
    throw 'Signed isolated original research six-split candidate unavailable'
}
Write-Host 'OWNER-APPROVED TARGET ONLY: jp.kn.local.battlecats' -ForegroundColor Yellow
Write-Host 'No original PONOS app, no SAVE clearing and no automatic game launch.'
Push-Location $repo
try {
    $argv = @(
        '-3.12', '-m', 'tools.base_mod.update_original_isolated_research',
        '--repo', $repo, '--candidate', $CandidateSignedSplitDirectory,
        '--adb', $adb, '--apksigner', $apksigner,
        '--approve-isolated-research-update', 'YES_UPDATE_ONLY_jp.kn.local.battlecats'
    )
    & py @argv
    if ($LASTEXITCODE -ne 0) {
        throw 'Isolated original research six-split update was BLOCKED or unverified; do NOT retry blindly'
    }
} finally {
    Pop-Location
}
Write-Host 'Only isolated research update metadata was verified. Game boot remains UNVERIFIED.'
Write-Host 'A separate one-shot private crash capture is the next device test.'
