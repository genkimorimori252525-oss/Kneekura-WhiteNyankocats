<#
LEVEL #12: Offline owner-private native LIEF proof, not an APK installer.
Requires the original JP15.7.1 ZIP, Python 3.12 x64 and the public LIEF
wheel/receipt downloaded from the GitHub Windows Actions artifact.
No ADB, APK install/sign, root, account, SAVE access or external HTTP.
Produces only a new metadata JSON in the repository gitignored private/.
Usage from repository root:
 powershell -ExecutionPolicy Bypass -File .\tools\base_mod\run_owner_lief_probe.ps1 -OwnerExport ".\nyanko_battlecats_2026-10-06.zip" -WheelDirectory ".\build\owner-lief-wheel"
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$OwnerExport,
    [Parameter(Mandatory = $true)][string]$WheelDirectory,
    [string]$Root = "."
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path -LiteralPath $Root -ErrorAction Stop).Path
$owner = (Resolve-Path -LiteralPath $OwnerExport -ErrorAction Stop).Path
$wheels = (Resolve-Path -LiteralPath $WheelDirectory -ErrorAction Stop).Path
if (-not (Test-Path -LiteralPath $owner -PathType Leaf)) {
    throw "Original owned JP15.7.1 ZIP is missing"
}
$verifier = Join-Path $repo "tools\base_mod\original_scene_native_image_gate.py"
if (-not (Test-Path -LiteralPath $verifier -PathType Leaf)) {
    throw "Repository root must contain the existing exact native verifier"
}
$name = "lief-0.17.6-cp312-cp312-win_amd64.whl"
$wheel = Join-Path $wheels $name
$receiptPath = Join-Path $wheels "wheel-receipt.json"
if (-not (Test-Path -LiteralPath $wheel -PathType Leaf) -or
    -not (Test-Path -LiteralPath $receiptPath -PathType Leaf)) {
    throw "Exact public LIEF wheel and SHA256 receipt are required"
}
$found = @(Get-ChildItem -LiteralPath $wheels -Filter "*.whl" -File)
if ($found.Count -ne 1 -or $found[0].Name -ne $name) {
    throw "Only one pinned Windows Python3.12 wheel is accepted"
}
$receipt = Get-Content -LiteralPath $receiptPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($receipt.schema -ne "kneekura-offline-win312-lief-wheel-v1" -or
    $receipt.wheel_name -ne $name -or
    $receipt.sha256 -notmatch "^[0-9a-fA-F]{64}$" -or
    $receipt.lief_version -ne "0.17.6" -or
    $receipt.target_python -ne "3.12" -or
    $receipt.target_platform -ne "win_amd64" -or
    $receipt.original_game_apk_or_save_downloaded -ne $false -or
    $receipt.ready_to_install_game -ne $false) {
    throw "Unknown or unsafe public wheel metadata"
}
$sha = (Get-FileHash -LiteralPath $wheel -Algorithm SHA256).Hash.ToLowerInvariant()
if ($sha -ne $receipt.sha256.ToLowerInvariant()) {
    throw "Public wheel SHA256 mismatch; refusing execution"
}
$launcher = Get-Command py -ErrorAction Stop
& $launcher.Source -3.12 -c "import sys; assert sys.version_info[:2] == (3,12) and sys.maxsize > 2**32"
if ($LASTEXITCODE -ne 0) { throw "Requires Python 3.12 x64" }
$private = Join-Path $repo "private"
if (-not (Test-Path -LiteralPath $private -PathType Container)) {
    New-Item -ItemType Directory -Path $private -ErrorAction Stop | Out-Null
}
$tag = [guid]::NewGuid().ToString("N")
$venv = Join-Path $private ("lief-probe-py312-" + $tag)
$output = Join-Path $private ("level-original-lief-" + $tag + ".json")
if ((Test-Path -LiteralPath $venv) -or (Test-Path -LiteralPath $output)) {
    throw "Refusing to overwrite any private owner file"
}
& $launcher.Source -3.12 -m venv $venv
if ($LASTEXITCODE -ne 0) { throw "Isolated Python 3.12 environment creation failed" }
$python = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Isolated Python 3.12 interpreter unavailable"
}
& $python -m pip install --no-index --no-deps --no-cache-dir --find-links $wheels "lief==0.17.6"
if ($LASTEXITCODE -ne 0) { throw "Offline LIEF installation failed" }
& $python -c "import lief; assert lief.__version__ == '0.17.6'"
if ($LASTEXITCODE -ne 0) { throw "Offline LIEF import/version failure" }
Push-Location $repo
try {
    & $python -m tools.base_mod.original_scene_native_image_gate --owned-export $owner --metadata-output $output
    $exitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}
if (-not (Test-Path -LiteralPath $output -PathType Leaf)) {
    throw "No metadata-only native verification receipt produced"
}
$result = Get-Content -LiteralPath $output -Raw -Encoding UTF8 | ConvertFrom-Json
Write-Host ("Private metadata receipt: " + $output)
Write-Host ("Research LIEF status: " + $result.status)
if ($exitCode -ne 0 -or
    $result.status -ne "PASS_PRIVATE_TEMP_NATIVE_LIEF_ROUNDTRIP_ONLY" -or
    $result.original_library_LIEF_rewrite_executed -ne $true -or
    $result.original_text_preserved_after_LIEF_rewrite -ne $true -or
    $result.original_APK_or_SAVE_written -ne $false -or
    $result.ready_to_sign_or_install -ne $false) {
    throw "LIEF research BLOCKED; no game installation or release can follow"
}
Write-Host "Source LIEF native probe PASS, no APK/SAVE/signing/device changes"
