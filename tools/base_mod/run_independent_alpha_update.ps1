param(
    [switch]$Apply,
    [switch]$TransferOwnedExport,
    [string]$DeviceSerial = "",
    [switch]$NoLaunch
)

# KNEEKURA independent Android Alpha, familiar project-root overlay runner.
# Without -Apply only verifies local payload. With -Apply delegates safely to
# the previously verified owner-signing APK installer (NO uninstall/clear data).
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$bundleDir = Join-Path $PSScriptRoot 'independent_alpha_20261009'
$installer = Join-Path $bundleDir 'INSTALL-ALPHA.ps1'
$apk = Join-Path $bundleDir 'independent-alpha.apk'
$manifest = Join-Path $bundleDir 'INSTALL-MANIFEST.json'

if (-not (Test-Path -LiteralPath (Join-Path $repo 'tools/base_mod') -PathType Container)) {
    throw '既存の「にーくらにゃんこ」フォルダのルートで上書き展開してな。'
}
$expectedFiles = @{
    'INSTALL-ALPHA.ps1' = '5f2b19732ee61913863b3bf8147137706f284b85d837e0e9886e68e0965b0b25'
    'independent-alpha.apk' = '9fc91ad09da1f242669404b86abbb53030aca133206f27c2cfb501a443a9ec3b'
}
foreach ($item in $expectedFiles.GetEnumerator()) {
    $file = Join-Path $bundleDir $item.Key
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
        throw "必要な配布ファイルが欠けている: $file"
    }
    $actual = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $item.Value) {
        throw "配布ファイルのハッシュが一致せえへん: $($item.Key)"
    }
}
if (-not (Test-Path -LiteralPath $manifest -PathType Leaf)) {
    throw "配布マニフェストが欠けている: $manifest"
}
$info = Get-Content -LiteralPath $manifest -Raw -Encoding UTF8 | ConvertFrom-Json
if (($info.app_id -ne 'jp.kneekura.whitenyankocats') -or
    ($info.source_commit -ne '2ffd09feac9ececc674765fc35d60b603efa5059')) {
    throw '想定と異なる独立Android版や。導入を中止する。'
}

Write-Host 'にーくら大戦争・独立Android Alpha（上書き展開型）' -ForegroundColor Cyan
Write-Host "対象プロジェクト: $repo"
Write-Host '対象パッケージ: jp.kneekura.whitenyankocats（元のにゃんこアプリとは別）'
Write-Host 'APK・スクリプト・manifestの元データ照合: PASS' -ForegroundColor Green

if (-not $Apply) {
    Write-Host '検証のみ終了。実際に導入するときは、いつもどおり末尾に -Apply を付けてな。' -ForegroundColor Yellow
    Write-Host 'powershell -ExecutionPolicy Bypass -File .\tools\base_mod\run_independent_alpha_update.ps1 -Apply'
    return
}

$installerArgs = @{}
if (-not [string]::IsNullOrWhiteSpace($DeviceSerial)) {
    $installerArgs['DeviceSerial'] = $DeviceSerial
}
if ($NoLaunch) { $installerArgs['NoLaunch'] = $true }
if ($TransferOwnedExport) {
    $ownedExport = Join-Path $repo 'nyanko_battlecats_2026-10-06.zip'
    if (-not (Test-Path -LiteralPath $ownedExport -PathType Leaf)) {
        throw "所有済みJP15.7.1 ZIPがプロジェクトのルートにない: $ownedExport"
    }
    $installerArgs['OwnedExport'] = $ownedExport
}

Write-Host '元にゃんこアプリ/SAVE_DATAを削除・初期化する処理は実行しないで。' -ForegroundColor Yellow
Write-Host '現在の独立版の署名が違う場合も、既存データを守るため中止する。'
& $installer @installerArgs
Write-Host '独立Android版の更新用スクリプトが正常終了したで。右上 i を確認してな。' -ForegroundColor Green
