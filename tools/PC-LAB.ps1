#requires -Version 5.1
param(
    [ValidateSet('Setup','Build','Run','Update','Check','Verify')][string]$Action = 'Run',
    [string]$StateRoot = (Join-Path $env:USERPROFILE 'Downloads\Kneekura-WhiteNyankocats\private\pc-lab'),
    [ValidateRange(10,300)][int]$ObserveSeconds = 30,
    [switch]$Install
)
$ErrorActionPreference = 'Stop'
$sourceRoot = Split-Path -Parent $PSScriptRoot
function Invoke-Lab([string[]]$CommandArgs) {
    & py -3.12 -B -m tools.pc_lab --state $StateRoot @CommandArgs
    if ($LASTEXITCODE -ne 0) { throw 'PC_LAB_COMMAND_FAILED_SEE_PRIVATE_EVIDENCE' }
}
function Invoke-Build {
    $inputFile = Join-Path $StateRoot 'inputs.json'
    if (-not (Test-Path -LiteralPath $inputFile -PathType Leaf)) {
        throw 'PC_LAB_INPUTS_NOT_REGISTERED_USE_PYTHON_BUILD_WITH_OWNER_ZIP_AND_OFFICIAL_AAR_ONCE'
    }
    $inputs = Get-Content -LiteralPath $inputFile -Raw -Encoding UTF8 | ConvertFrom-Json
    Invoke-Lab @('build','--owner-zip',$inputs.owner_zip,'--official-aar',$inputs.official_aar)
}
Push-Location $sourceRoot
try {
    switch ($Action) {
        'Setup' { Invoke-Lab @('setup') }
        'Build' { Invoke-Build }
        'Check' { Invoke-Lab @('check') }
        'Verify' { Invoke-Lab @('verify-capture') }
        'Update' {
            Invoke-Lab @('setup')
            Invoke-Build
            Invoke-Lab @('run','--install','--seconds',[string]$ObserveSeconds)
        }
        'Run' {
            $runArgs = @('run','--seconds',[string]$ObserveSeconds)
            if ($Install) { $runArgs += '--install' }
            Invoke-Lab $runArgs
        }
    }
} finally {
    Pop-Location
}
