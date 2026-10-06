param(
    [string]$Adb,
    [string]$Device,
    [string]$Package = "jp.kn.trace.battlecats",
    [string]$OutDir = "offline-profile-out"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Resolve-Adb {
    param([string]$Explicit)
    if ($Explicit) {
        if (-not (Test-Path -LiteralPath $Explicit -PathType Leaf)) {
            throw "adb not found: $Explicit"
        }
        return (Resolve-Path -LiteralPath $Explicit).Path
    }

    $command = Get-Command adb -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    if ($env:LOCALAPPDATA) {
        $candidate = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return $candidate
        }
    }

    throw "adb was not found. Put Android platform-tools on PATH or pass -Adb."
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

    $lines = @(& $AdbPath devices)
    if ($LASTEXITCODE -ne 0) {
        throw "adb devices failed"
    }

    $devices = @()
    foreach ($line in $lines) {
        if ($line -match "^([^\s]+)\s+device\s*$") {
            $devices += $Matches[1]
        }
    }

    if ($devices.Count -eq 0) {
        throw "No online adb device found"
    }
    if ($devices.Count -gt 1) {
        throw "Multiple adb devices found; rerun with -Device <serial>"
    }
    return $devices[0]
}

function Test-RemotePath {
    param([string]$AdbPath, [string]$DeviceId, [string]$RemotePath)

    # Avoid PowerShell turning Android 'ls: ... No such file' stderr into a
    # terminating NativeCommandError. Ask the remote shell for a quiet boolean.
    $escaped = $RemotePath.Replace("'", "'\''")
    $probe = @(& $AdbPath -s $DeviceId shell "if [ -e '$escaped' ]; then echo 1; else echo 0; fi" 2>$null)
    if ($LASTEXITCODE -ne 0 -or $probe.Count -eq 0) { return $false }
    return (($probe -join "").Trim() -eq "1")
}

$adbPath = Resolve-Adb -Explicit $Adb
$deviceId = Select-Device -AdbPath $adbPath -Requested $Device

$root = [System.IO.Path]::GetFullPath($OutDir)
$baselineDir = Join-Path $root "baseline"
New-Item -ItemType Directory -Force -Path $baselineDir | Out-Null

$remoteCandidates = @(
    "/sdcard/Android/data/$Package/files",
    "/storage/emulated/0/Android/data/$Package/files"
)

$remoteRoot = $null
foreach ($candidate in $remoteCandidates) {
    if (Test-RemotePath -AdbPath $adbPath -DeviceId $deviceId -RemotePath $candidate) {
        $remoteRoot = $candidate
        break
    }
}

$versionName = $null
$versionCode = $null
$packageDump = @(& $adbPath -s $deviceId shell dumpsys package $Package 2>$null)
foreach ($line in $packageDump) {
    if (-not $versionName -and $line -match "versionName=([^\s]+)") {
        $versionName = $Matches[1]
    }
    if (-not $versionCode -and $line -match "versionCode=([0-9]+)") {
        $versionCode = [int64]$Matches[1]
    }
}

$inventory = @()
$files = @()
$saveNames = @("SAVE_DATA", "SAVE_DATA4", "SAVE_DATA8", "BACKUP_SAVE_DATA")

if ($remoteRoot) {
    $inventory = @(& $adbPath -s $deviceId shell find $remoteRoot -maxdepth 2 -type f 2>$null)
    if ($LASTEXITCODE -ne 0) {
        $inventory = @(& $adbPath -s $deviceId shell ls -R $remoteRoot 2>$null)
    }

    foreach ($name in $saveNames) {
        $remote = "$remoteRoot/$name"
        if (-not (Test-RemotePath -AdbPath $adbPath -DeviceId $deviceId -RemotePath $remote)) {
            continue
        }

        $local = Join-Path $baselineDir $name
        & $adbPath -s $deviceId pull $remote $local | Out-Host
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $local -PathType Leaf)) {
            throw "Failed to pull $remote"
        }

        $item = Get-Item -LiteralPath $local
        $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $local).Hash.ToLowerInvariant()
        $rollback = Join-Path $baselineDir ($name + ".rollback")
        Copy-Item -LiteralPath $local -Destination $rollback -Force
        $rollbackHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $rollback).Hash.ToLowerInvariant()
        if ($rollbackHash -ne $hash) {
            throw "Rollback copy hash mismatch for $name"
        }

        $inspectionPath = $null
        $inspectionExitCode = $null
        if ($name -eq "SAVE_DATA") {
            $inspectionPath = Join-Path $baselineDir "SAVE_DATA-inspection.json"
            & python -m tools.base_mod.inspect_save_data $local --output $inspectionPath | Out-Host
            $inspectionExitCode = $LASTEXITCODE
        }

        $files += [ordered]@{
            name = $name
            remote_path = $remote
            local_path = $local
            rollback_path = $rollback
            size = [int64]$item.Length
            sha256 = $hash
            rollback_sha256 = $rollbackHash
            inspection_path = $inspectionPath
            inspection_exit_code = $inspectionExitCode
        }
    }
}

$result = [ordered]@{
    schema_version = 1
    mode = "offline-profile-readonly-probe"
    package = $Package
    device = $deviceId
    version_name = $versionName
    version_code = $versionCode
    remote_files_dir = $remoteRoot
    remote_files_dir_found = [bool]$remoteRoot
    save_data_found = [bool]($files | Where-Object { $_.name -eq "SAVE_DATA" })
    save_family_files_found = $files.Count
    files = $files
    inventory = @($inventory)
    mutation_attempted = $false
    adb_push_used = $false
    rollback_copies_created = $files.Count
    save_inspection_generated = [bool]($files | Where-Object { $_.name -eq "SAVE_DATA" -and $_.inspection_path })
}

New-Item -ItemType Directory -Force -Path $root | Out-Null
$resultPath = Join-Path $root "offline-profile-probe.json"
$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $resultPath -Encoding UTF8

$bundlePath = Join-Path $root "offline-profile-baseline-bundle.zip"
if (Test-Path -LiteralPath $bundlePath) {
    Remove-Item -LiteralPath $bundlePath -Force
}
$bundleInputs = @($resultPath)
if (Test-Path -LiteralPath $baselineDir -PathType Container) {
    $bundleInputs += $baselineDir
}
Compress-Archive -Path $bundleInputs -DestinationPath $bundlePath -CompressionLevel Optimal

Write-Host ""
Write-Host "Offline profile read-only probe:"
Write-Host ($result | ConvertTo-Json -Depth 8)
Write-Host ""
Write-Host "Result: $resultPath"
Write-Host "Bundle: $bundlePath"
if (-not $result.save_data_found) {
    Write-Host "SAVE_DATA was not found. No device file was modified." -ForegroundColor Yellow
} else {
    Write-Host "Baseline + rollback copies captured. No device file was modified." -ForegroundColor Green
}
