param(
    [ValidateSet("jp.kn.white.battlecats", "jp.kn.clean.battlecats", "jp.kn.trace.battlecats")]
    [string]$Package = "jp.kn.white.battlecats",
    [string]$Device = "",
    [string]$BackupRoot = "private/kneekura-101-backups",
    [string]$SignedSplits = ""
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "../.."))
$backupRootPath = if ([IO.Path]::IsPathRooted($BackupRoot)) {
    [IO.Path]::GetFullPath($BackupRoot)
} else { [IO.Path]::GetFullPath((Join-Path $root $BackupRoot)) }
$destination = Join-Path $backupRootPath ("backup-" + (Get-Date).ToString("yyyyMMdd-HHmmss"))
if (Test-Path -LiteralPath $destination) { throw "Backup already exists: $destination" }
Push-Location $root
try {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        throw "Python not found. Activate the project .venv"
    }
    Write-Host "KNEEKURA 1.01: VERIFY + BACKUP ONLY (NO GAME UPDATE)" -ForegroundColor Cyan
    Write-Host "Save and fully close the game first. Backup: $destination"
    $argv = @("-m", "tools.base_mod.verify_update_101_device",
        "--package", $Package, "--backup-dir", $destination)
    if ($Device) { $argv += @("--device", $Device) }
    if ($SignedSplits) {
        $signedPath = [IO.Path]::GetFullPath($SignedSplits)
        $argv += @("--signed-splits", $signedPath)
    }
    & python @argv
    if ($LASTEXITCODE -ne 0) {
        throw "SAVE or signer preflight failed; NO INSTALL was attempted"
    }
    Write-Host "PASS: original SAVE_DATA and APKs backed up without changing the app." -ForegroundColor Green
    Write-Host "Keep this private backup directory: $destination"
} finally { Pop-Location }