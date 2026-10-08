param(
    [string]$OwnedExport = "nyanko_battlecats_2026-10-06.zip",
    [string]$OutDir = "kneekura-update-1.01-preview",
    [string]$Package,
    [string]$Device,
    [switch]$CheckLevelCaps,
    [switch]$ApplyLevelCaps
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Unzip tools/base_mod and update101 at the existing Kneekura project root.
$project = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "../.."))
$exportPath = if ([System.IO.Path]::IsPathRooted($OwnedExport)) {
    [System.IO.Path]::GetFullPath($OwnedExport)
} else { [System.IO.Path]::GetFullPath((Join-Path $project $OwnedExport)) }
$outputPath = if ([System.IO.Path]::IsPathRooted($OutDir)) {
    [System.IO.Path]::GetFullPath($OutDir)
} else { [System.IO.Path]::GetFullPath((Join-Path $project $OutDir)) }
$levelCapRunner = Join-Path $project "tools/base_mod/run_level_cap_unlock.ps1"
$previewRoot = Join-Path $project "update101"

if (-not (Test-Path -LiteralPath $exportPath -PathType Leaf)) {
    throw "Missing exact owned JP15.7.1 export: $exportPath"
}
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python not found in PATH; activate the project's .venv first"
}

Write-Host "[1/2] Preparing 1.01 data-only STATIC preview (does not install)..."
& python (Join-Path $previewRoot "prepare_101.py") --owned-export $exportPath --output $outputPath
if ($LASTEXITCODE -ne 0) { throw "The owned-source preflight failed" }

Write-Host "[2/2] Verifying static builder tests..."
& python (Join-Path $previewRoot "test_prepare_101.py")
if ($LASTEXITCODE -ne 0) { throw "Static preview tests failed" }

Write-Host "KNEEKURA 1.01 static preview built; original APK, device and SAVE_DATA untouched."
Write-Host "The preview is NOT installable. Castle 1-damage and exact stats still require original-game runtime code."

if ($CheckLevelCaps -or $ApplyLevelCaps) {
    if (-not (Test-Path -LiteralPath $levelCapRunner -PathType Leaf)) {
        throw "Existing native level-cap runner not found: $levelCapRunner"
    }
    if ([string]::IsNullOrWhiteSpace($Package)) {
        throw "Specify -Package with your existing Kneekura app ID before any device operation"
    }
    $options = @("-OwnedExport", $exportPath, "-OutDir", (Join-Path $outputPath "level-cap"), "-Package", $Package)
    if ($Device) { $options += @("-Device", $Device) }
    if ($ApplyLevelCaps) {
        # Delegated ONLY to the previously validated existing migration runner:
        # exact backup, candidate verification, original-UI restart, rollback.
        $options += "-Apply"
        Write-Host "Applying ONLY the existing level-cap migration to $Package..."
    } else { Write-Host "Checking ONLY existing level-cap migration; no SAVE_DATA write..." }
    & $levelCapRunner @options
    if ($LASTEXITCODE -ne 0) { throw "Native level-cap runner failed" }
}

Write-Host "No balance APK install was performed; do not mistake this kit for shipped 1.01."