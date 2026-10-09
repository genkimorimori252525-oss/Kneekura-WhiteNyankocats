# Owner-safe JDK executable discovery for Windows PowerShell 5.1.
# This file must be checked by real Windows PowerShell in CI.
# Never assume JAVA_HOME/JDK_HOME/PATH or ProgramFiles are set.
function Resolve-JavaKeytool {
    $localAppDataRoot = $env:LOCALAPPDATA
    if ([string]::IsNullOrWhiteSpace($localAppDataRoot)) {
        $localAppDataRoot = [Environment]::GetFolderPath('LocalApplicationData')
    }
    if ([string]::IsNullOrWhiteSpace($localAppDataRoot)) {
        throw 'LOCALAPPDATA is missing; cannot inspect installed Java JDK locations safely.'
    }
    # Never Join-Path an optional environment variable before checking it.
    foreach ($commandName in @('keytool.exe', 'keytool')) {
        $command = Get-Command -Name $commandName -CommandType Application -ErrorAction SilentlyContinue
        if ($command -and (Test-Path -LiteralPath $command.Source -PathType Leaf)) {
            return $command.Source
        }
    }
    $jdkRoots = New-Object 'System.Collections.Generic.List[string]'
    foreach ($environmentName in @('JAVA_HOME', 'JDK_HOME')) {
        $root = [Environment]::GetEnvironmentVariable($environmentName)
        if (-not [string]::IsNullOrWhiteSpace($root)) { $jdkRoots.Add($root) }
    }
    foreach ($javaCommandName in @('java.exe', 'java')) {
        $javaCommand = Get-Command -Name $javaCommandName -CommandType Application -ErrorAction SilentlyContinue
        if ($javaCommand -and -not [string]::IsNullOrWhiteSpace($javaCommand.Source)) {
            $jdkRoots.Add((Split-Path -Path (Split-Path -Path $javaCommand.Source -Parent) -Parent))
        }
    }
    $standardRoots = @(
        (Join-Path $localAppDataRoot 'Programs\Eclipse Adoptium'),
        (Join-Path $localAppDataRoot 'Android\Studio\jbr')
    )
    if (-not [string]::IsNullOrWhiteSpace($env:ProgramFiles)) {
        $standardRoots += (Join-Path $env:ProgramFiles 'Java')
        $standardRoots += (Join-Path $env:ProgramFiles 'Eclipse Adoptium')
    }
    foreach ($candidateRoot in $standardRoots) {
        if ([string]::IsNullOrWhiteSpace($candidateRoot)) { continue }
        if (Test-Path -LiteralPath $candidateRoot -PathType Container) {
            $jdkRoots.Add($candidateRoot)
            foreach ($child in @(Get-ChildItem -LiteralPath $candidateRoot -Directory -ErrorAction SilentlyContinue)) {
                $jdkRoots.Add($child.FullName)
            }
        }
    }
    foreach ($jdkRoot in $jdkRoots) {
        if ([string]::IsNullOrWhiteSpace($jdkRoot)) { continue }
        foreach ($exe in @('bin\keytool.exe', 'bin\keytool')) {
            $path = Join-Path -Path $jdkRoot -ChildPath $exe
            if (Test-Path -LiteralPath $path -PathType Leaf) { return $path }
        }
    }
    throw 'Java keytool.exe not found. Install JDK 17 or set JAVA_HOME to the JDK root (e.g. C:\\Program Files\\Java\\jdk-17); no APK installed.'
}
