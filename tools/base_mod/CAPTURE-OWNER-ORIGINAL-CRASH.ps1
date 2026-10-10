# Single owner-triggered original JP15.7.1 research crash capture, Windows PowerShell 5.1.
# PRIVATE log is never automatically shared. No app/data clear, no reinstall,
# no original PONOS app/SAVE, no logcat -c, no Android force-stop.
# Only one isolated research launcher request, AFTER log capture starts.
[CmdletBinding()]
param(
    [string]$RepositoryRoot = (Join-Path $HOME 'Downloads\Kneekura-WhiteNyankocats'),
    [int]$ObserveSeconds = 18
)
$ErrorActionPreference = 'Stop'
if ($ObserveSeconds -lt 5 -or $ObserveSeconds -gt 30) {
    throw 'Research crash capture limited to a single 5-30 second window'
}
if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
    throw 'LOCALAPPDATA Android SDK location unavailable'
}
$adb = Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe'
if (-not (Test-Path -LiteralPath $adb -PathType Leaf)) {
    throw 'Owner Android SDK adb.exe missing'
}
if (-not (Test-Path -LiteralPath $RepositoryRoot -PathType Container)) {
    throw 'Owner Kneekura research repository missing'
}
$repo = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$package = 'jp.kn.local.battlecats'
$devices = @(
    & $adb devices |
    Select-String '^\S+\s+device\s*$' |
    ForEach-Object { ($_.Line -split '\s+')[0] }
)
if ($LASTEXITCODE -ne 0 -or $devices.Count -ne 1) {
    throw 'Exactly one authorized USB-debugging Android device is required'
}
$device = $devices[0]
$paths = @(& $adb -s $device shell pm path $package 2>$null)
if ($LASTEXITCODE -ne 0 -or @($paths | Where-Object { $_ -match '^package:/' }).Count -ne 6) {
    throw 'Original isolated research six-split package is not installed'
}
$currentPid = (@(& $adb -s $device shell pidof $package 2>$null) -join '').Trim()
if ($currentPid -match '^[0-9]+$') {
    throw 'Research app already running: do not restart or stop it with this collector'
}
$private = Join-Path $repo 'private\original-crash-captures'
if ((Test-Path -LiteralPath $private) -and
    ((Get-Item -LiteralPath $private).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw 'Unsafe private capture folder symlink'
}
New-Item -ItemType Directory -Path $private -Force | Out-Null
$stamp = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N').Substring(0,6)
$raw = Join-Path $private ($stamp + '-filtered-logcat-PRIVATE.txt')
$stderr = Join-Path $private ($stamp + '-adb-stderr-PRIVATE.txt')
$proc = $null
try {
    $logArgs = @('-s', $device, 'logcat', '-b', 'main', '-b', 'system',
        '-b', 'crash', '-v', 'threadtime', '-T', '1', '-s',
        'AndroidRuntime:E', 'libc:F', 'DEBUG:E', 'DEBUG:F',
        'linker:E', 'linker64:E', 'KNEEKURA_STATIC_HTTP:I',
        'ActivityManager:I', 'ActivityTaskManager:I', '*:S')
    $startOptions = @{
        FilePath = $adb
        ArgumentList = $logArgs
        PassThru = $true
        WindowStyle = 'Hidden'
        RedirectStandardOutput = $raw
        RedirectStandardError = $stderr
    }
    $proc = Start-Process @startOptions
    Start-Sleep -Seconds 2
    if ($proc.HasExited) { throw 'ADB logcat collector ended before research app launch' }
    $started = @(& $adb -s $device shell am start -n ($package + '/' + $package + '.MyActivity') 2>$null)
    if ($LASTEXITCODE -ne 0 -or ($started -join ' ') -notmatch 'Starting: Intent') {
        throw 'Isolated research app launch request not accepted'
    }
    Write-Host 'Single research launch requested (not game boot proof). Collecting locally...' -ForegroundColor Cyan
    Start-Sleep -Seconds $ObserveSeconds
} finally {
    # Stop ONLY the local ADB logcat child process. Android app is untouched.
    if ($null -ne $proc) {
        try {
            if (-not $proc.HasExited) {
                Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            }
        } catch {}
    }
}
Push-Location $repo
try {
    $arguments = @(
        '-3.12', '-m', 'tools.base_mod.summarize_original_crash_capture',
        '--repo', $repo, '--raw', $raw
    )
    & py @arguments
    if ($LASTEXITCODE -ne 0) {
        throw 'Private original crash log could not be sanitized; DO NOT SHARE raw log'
    }
} finally {
    Pop-Location
}
Write-Host 'PRIVATE-RESEARCH-AGGREGATE-PASS; raw log not shared; no phone data changed' -ForegroundColor Green
Write-Host 'Share only generated original-crash-aggregate-*.json after personal review.'
