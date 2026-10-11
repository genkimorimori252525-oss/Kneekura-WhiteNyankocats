param(
    [string]$OwnedExport = "nyanko_battlecats_2026-10-06.zip",
    [string]$PreviewDir = "kneekura-update-1.01-preview",
    [string]$OutDir = "kneekura-update-1.01-owner-gate",
    [string]$Package = "jp.kn.trace.battlecats",
    [string]$Device = "",
    [switch]$CollectPrivateServerPacks,
    [switch]$SkipUnsignedCandidate
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "../.."))
$exportPath = if ([IO.Path]::IsPathRooted($OwnedExport)) {
    [IO.Path]::GetFullPath($OwnedExport)
} else {
    [IO.Path]::GetFullPath((Join-Path $projectRoot $OwnedExport))
}
$previewPath = if ([IO.Path]::IsPathRooted($PreviewDir)) {
    [IO.Path]::GetFullPath($PreviewDir)
} else {
    [IO.Path]::GetFullPath((Join-Path $projectRoot $PreviewDir))
}
$destination = if ([IO.Path]::IsPathRooted($OutDir)) {
    [IO.Path]::GetFullPath($OutDir)
} else {
    [IO.Path]::GetFullPath((Join-Path $projectRoot $OutDir))
}

Push-Location $projectRoot
try {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        throw "python not found; activate Kneekura project .venv"
    }
    if (-not (Test-Path -LiteralPath $exportPath -PathType Leaf)) {
        throw "exact JP15.7.1 owner ZIP missing: $exportPath"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $previewPath "receipt.json") -PathType Leaf)) {
        throw "1.01 validated preview missing; first run the existing run_update_101_preflight.ps1"
    }

    if (-not $SkipUnsignedCandidate) {
        $unsignedOutput = Join-Path $destination "unsigned-research-splits"
        if (Test-Path -LiteralPath $unsignedOutput) {
            throw "unsigned output already exists; no overwrites permitted: $unsignedOutput"
        }
        Write-Host "[1/2] Building UNSIGNED data-only 1.01 candidate..."
        $builderArgs = @(
            "-m", "tools.base_mod.build_update_101_unsigned",
            "--owned-export", $exportPath,
            "--preview", $previewPath,
            "--output", $unsignedOutput
        )
        & python @builderArgs
        if ($LASTEXITCODE -ne 0) { throw "unsigned candidate failed validation" }
        Write-Host "Candidate is UNSIGNED and NOT INSTALLABLE. Never adb install it." -ForegroundColor Yellow
    } else {
        Write-Host "[1/2] Unsigned candidate skipped."
    }

    if ($CollectPrivateServerPacks) {
        $assetOutput = Join-Path $destination "private-owner-server-packs"
        if (Test-Path -LiteralPath $assetOutput) {
            throw "private asset destination already exists; no overwrite"
        }
        Write-Host "[2/2] Read-only ADB pull of 4 owner Server source pairs..."
        $args = @(
            "-m", "tools.base_mod.collect_update_101_server_assets",
            "--package", $Package,
            "--output", $assetOutput,
            "--pull"
        )
        if ($Device) { $args += @("--device", $Device) }
        & python @args
        if ($LASTEXITCODE -ne 0) {
            throw "original Server asset inventory/pull not complete; no game state modified"
        }
        $rigOut = Join-Path $destination "private-extracted-godzilla-rig"
        Write-Host "Extracting 7 original enemy rig files privately (NOT converting)..."
        $rigArgs = @(
            "-m", "tools.base_mod.extract_godzilla_owner_rig",
            "--m-number-list", (Join-Path $assetOutput "MNumberServer.list"),
            "--m-number-pack", (Join-Path $assetOutput "MNumberServer.pack"),
            "--w-imagedata-list", (Join-Path $assetOutput "WImageDataServer.list"),
            "--w-imagedata-pack", (Join-Path $assetOutput "WImageDataServer.pack"),
            "--output", $rigOut
        )
        & python @rigArgs
        if ($LASTEXITCODE -ne 0) {
            throw "private Godzilla animation rig source gate failed; no asset conversion claimed"
        }
        Write-Host "Rig extraction complete; original model conversion/device proof remain." -ForegroundColor Green
    } else {
        Write-Host "[2/2] Private Server cache collection NOT requested; no ADB commands."
    }

    Write-Host ""
    Write-Host "Kneekura Update 1.01 research gate completed." -ForegroundColor Green
    Write-Host "IMPORTANT: NO signed/installed 1.01 game build created." -ForegroundColor Yellow
    Write-Host "Existing SAVE_DATA, official UI and native release behavior untouched."
} finally {
    Pop-Location
}