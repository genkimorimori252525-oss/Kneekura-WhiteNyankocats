# Owner-safe Java JDK resolver. Source through the Windows PowerShell 5.1 installer.
# Never touch ADB, APKs, player SAVE or the filesystem other than file discovery.
function Resolve-JavaKeytool {
    [CmdletBinding()]
    param()

    foreach ($name in @('keytool.exe', 'keytool')) {
        $found = Get-Command -Name $name -CommandType Application -ErrorAction SilentlyContinue
        if ($found -and -not [string]::IsNullOrWhiteSpace($found.Source) -and
            (Test-Path -LiteralPath $found.Source -PathType Leaf)) {
            return $found.Source
        }
    }
    $candidates = New-Object 'System.Collections.Generic.List[string]'
    foreach ($name in @('JAVA_HOME', 'JDK_HOME')) {
        $home = [Environment]::GetEnvironmentVariable($name)
        if (-not [string]::IsNullOrWhiteSpace($home)) { $candidates.Add($home.Trim('"')) }
    }
    foreach ($name in @('java.exe', 'java')) {
        $cmd = Get-Command -Name $name -CommandType Application -ErrorAction SilentlyContinue
        if ($cmd -and -not [string]::IsNullOrWhiteSpace($cmd.Source)) {
            $javaBin = Split-Path -Path $cmd.Source -Parent
            if (-not [string]::IsNullOrWhiteSpace($javaBin)) {
                $jdkHome = Split-Path -Path $javaBin -Parent
                if (-not [string]::IsNullOrWhiteSpace($jdkHome)) { $candidates.Add($jdkHome) }
            }
        }
    }
    $roots = New-Object 'System.Collections.Generic.List[string]'
    foreach ($variable in @('ProgramFiles', 'ProgramFiles(x86)')) {
        $home = [Environment]::GetEnvironmentVariable($variable)
        if (-not [string]::IsNullOrWhiteSpace($home)) {
            foreach ($segment in @('Java', 'Eclipse Adoptium', 'Microsoft', 'Zulu')) {
                $roots.Add((Join-Path -Path $home -ChildPath $segment))
            }
            $roots.Add((Join-Path -Path $home -ChildPath 'Android\Android Studio\jbr'))
        }
    }
    $local = [Environment]::GetEnvironmentVariable('LOCALAPPDATA')
    if (-not [string]::IsNullOrWhiteSpace($local)) {
        $roots.Add((Join-Path -Path $local -ChildPath 'Programs\Eclipse Adoptium'))
        $roots.Add((Join-Path -Path $local -ChildPath 'Android\Studio\jbr'))
    }
    foreach ($root in $roots) {
        if ([string]::IsNullOrWhiteSpace($root) -or
            -not (Test-Path -LiteralPath $root -PathType Container)) { continue }
        $candidates.Add($root)
        foreach ($child in @(Get-ChildItem -LiteralPath $root -Directory -ErrorAction SilentlyContinue)) {
            $candidates.Add($child.FullName)
        }
    }
    foreach ($root in $candidates) {
        if ([string]::IsNullOrWhiteSpace($root)) { continue }
        $exe = Join-Path -Path $root -ChildPath 'bin\keytool.exe'
        if (Test-Path -LiteralPath $exe -PathType Leaf) { return $exe }
    }
    throw 'Java JDK keytool.exe not found. Install JDK 17 or add JDK\bin to PATH. JAVA_HOME is optional. No APK was installed.'
}
