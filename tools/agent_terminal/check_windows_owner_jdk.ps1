# Run with Windows PowerShell 5.1, not pwsh 7, before ANY owner release.
# No ADB access, no APK installation and no signing-key use.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$helper = Join-Path $root 'tools/base_mod/resolve_java_keytool.ps1'
$wrapper = Join-Path $root 'tools/base_mod/run_independent_alpha_update.ps1'

foreach ($scriptFile in @($helper,$wrapper)) {
    $bytes = [IO.File]::ReadAllBytes($scriptFile)
    if ($bytes.Length -lt 3 -or $bytes[0] -ne 239 -or $bytes[1] -ne 187 -or $bytes[2] -ne 191) {
        throw "Missing PS5.1 UTF-8 BOM: $scriptFile"
    }
    $tokens = $null
    $errors = $null
    $ast = [System.Management.Automation.Language.Parser]::ParseFile(
        $scriptFile, [ref]$tokens, [ref]$errors
    )
    if ($errors.Count -gt 0) { throw "Parser failed on $scriptFile : $errors" }
    $reserved = @('home', 'host', 'pid', 'pshome', 'psscriptroot',
                  'pscommandpath', 'input', 'matches', 'myinvocation',
                  'profile', 'pwd', 'error', 'lastExitCode')
    $assignments = $ast.FindAll({
        param($node)
        $node -is [System.Management.Automation.Language.AssignmentStatementAst]
    }, $true)
    foreach ($assignment in $assignments) {
        $leftVars = $assignment.Left.FindAll({
            param($node)
            $node -is [System.Management.Automation.Language.VariableExpressionAst]
        }, $true)
        foreach ($v in $leftVars) {
            if ($reserved -contains $v.VariablePath.UserPath) {
                throw "Read-only/automatic PowerShell variable assignment in $scriptFile : $($v.Extent.Text)"
            }
        }
    }
}
Write-Host 'PASS: two PowerShell scripts parsed; reserved variable assignment scan' -ForegroundColor Green

# Simulate owner's actual incident: JAVA_HOME not set; no executable keytool
# in PATH; only a fake JDK_HOME directory. Keytool is NEVER executed.
$tempRoot = Join-Path ([IO.Path]::GetTempPath()) (
    'kneekura-ps51-test-' + [guid]::NewGuid().ToString('N')
)
$bin = Join-Path $tempRoot 'bin'
[void][IO.Directory]::CreateDirectory($bin)
$fakeKeytool = Join-Path $bin 'keytool.exe'
[IO.File]::WriteAllBytes($fakeKeytool, [byte[]]@(77,90))
$pathBefore = $env:PATH
$javaBefore = $env:JAVA_HOME
$jdkBefore = $env:JDK_HOME
$localBefore = $env:LOCALAPPDATA
try {
    $env:JAVA_HOME = $null
    $env:JDK_HOME = $tempRoot
    $env:LOCALAPPDATA = $null
    $env:PATH = (Join-Path $env:SystemRoot 'system32')
    . $helper
    $actual = Resolve-JavaKeytool
    if ($actual -ne $fakeKeytool) {
        throw "Expected JDK_HOME mock keytool ($fakeKeytool), got $actual"
    }
    Write-Host "PASS: JAVA_HOME null, LOCALAPPDATA null, PATH isolated, JDK_HOME fallback" -ForegroundColor Green
} finally {
    $env:PATH = $pathBefore
    $env:JAVA_HOME = $javaBefore
    $env:JDK_HOME = $jdkBefore
    $env:LOCALAPPDATA = $localBefore
    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}

# Independent no-JAVA_HOME PATH discovery using real JDK17 installed on CI.
$real = Get-Command keytool.exe -CommandType Application -ErrorAction SilentlyContinue
if ($real -and -not [string]::IsNullOrWhiteSpace($real.Source)) {
    $saved = $env:JAVA_HOME
    try {
        $env:JAVA_HOME = $null
        $resolved = Resolve-JavaKeytool
        if (-not (Test-Path -LiteralPath $resolved -PathType Leaf)) {
            throw 'PATH-resolved keytool does not exist'
        }
        Write-Host 'PASS: actual Java keytool detected with JAVA_HOME unset' -ForegroundColor Green
    } finally { $env:JAVA_HOME = $saved }
}
