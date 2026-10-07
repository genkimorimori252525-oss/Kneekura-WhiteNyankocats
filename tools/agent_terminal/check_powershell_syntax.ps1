param(
    [string]$Root = "tools/base_mod"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$resolvedRoot = (Resolve-Path $Root).Path
$files = @(Get-ChildItem -Path $resolvedRoot -Recurse -File -Filter "*.ps1" | Sort-Object FullName)
if ($files.Count -eq 0) {
    throw "No PowerShell scripts found under: $resolvedRoot"
}

$failureCount = 0
foreach ($file in $files) {
    $tokens = $null
    $errors = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile(
        $file.FullName,
        [ref]$tokens,
        [ref]$errors
    )

    if ($errors.Count -eq 0) {
        Write-Host "[PASS] $($file.FullName)"
        continue
    }

    $failureCount++
    Write-Host "[FAIL] $($file.FullName)" -ForegroundColor Red
    foreach ($parseError in $errors) {
        $extent = $parseError.Extent
        Write-Host ("  line {0}, column {1}: {2}" -f $extent.StartLineNumber, $extent.StartColumnNumber, $parseError.Message) -ForegroundColor Red
    }
}

if ($failureCount -gt 0) {
    throw "PowerShell syntax validation failed for $failureCount file(s)"
}

Write-Host "PowerShell syntax validation passed for $($files.Count) file(s)."
