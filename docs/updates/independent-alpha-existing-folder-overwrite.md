# 独立Android Alpha — オーナーWindows環境と従来の上書きZIP方式（現行）

## 0.3.1 / 未来編1章のお宝を含む最新配布（2026-10-09）

**最新：** `kneekura-alpha-itf1-superior-overlay-20261009.zip`（SHA256 `01a1ea0a9991c8c01a413b13a13dc490b4588e2bd3dabe797b7c807c2bac6b27`）、独立Android versionCode **5**、最新APK SHA `491bf95fe1f494460c280ef1c253ccd25a303bfc31b5dd916f23564d4e30c3c1`。これ以降、本文の`versionCode4`、`HOME-fixed` ZIPは**過去版の説明**や。最新の正しい実行方法・保存状態の契約は [0.3.1独立版手順](independent-alpha-itf1-superior-2026-10-09.md) と [ストーリー初期状態v2](../architecture/kneekura-independent-story-checkpoint-v2.md) にある。

最新ZIPも7ファイルで、既存`にーくらにゃんこ`直下に上書きするだけ。Java resolverは実績あるPS5.1用同一ファイルを維持、`INSTALL-ALPHA.ps1`はversionCode5と新APK SHAのみ更新し、署名鍵・端末・元JPセーブはリセットしない。事前`-CheckPrerequisites`と`adb devices`で準備を確認してから、いつもの`run_independent_alpha_update.ps1 -Apply`で導入する。実機USBは未検証。


最終確認：2026-10-09。**この文書を最優先の案内とし、以前の配布ZIPの古いSHAや旧手順は docs/research/failure-repair-history.md の履歴だけとして扱う。**

## 添付された旧Lv60 ZIPと今回の独立Alpha ZIPは何が同じか

オーナーが比較用に添付した `kneekura-level60-native-cap-update.zip` は、**118ファイル**でZIPルートに `README-FIRST.txt`、`tools/base_mod/run_level_cap_unlock.ps1` などが入る。SHA256 `a019a6dd273fda91f6d08320b931931c9bf33335f5f57cf4cfecc7899653caa0`。これは旧研究アプリ `jp.kn.trace.battlecats` のSAVE_DATAレベル上限変更であり、デフォルトの端末選択は1台自動、複数接続時は旧引数 `-Device <serial>` を使う。

**現行配布** `kneekura-alpha-overlay-ps51-HOME-fixed-20261009.zip` は**7ファイル**、SHA256 `bacfa9b5b6a672385601071c96cd997e2b905e3d6fb5146cb1e4b84a6f11ac7c`。両方ともZIPルートには余分な親フォルダがない。既存の `C:\Users\genki\Downloads\にーくらにゃんこ` **へ直接上書き展開**する。現行Alphaの中身：

- `READ-ME-にーくら-alpha-上書き更新.txt`
- `tools/base_mod/run_independent_alpha_update.ps1`
- `tools/base_mod/resolve_java_keytool.ps1`
- `tools/base_mod/independent_alpha_20261009/INSTALL-ALPHA.ps1`
- `tools/base_mod/independent_alpha_20261009/independent-alpha.apk`
- `tools/base_mod/independent_alpha_20261009/INSTALL-MANIFEST.json`
- `tools/base_mod/independent_alpha_20261009/OVERLAY-MANIFEST.json`

今回のAlphaは**旧レベル上限セーブ改変とは無関係の独立Androidアプリ** `jp.kneekura.whitenyankocats`（versionCode 4、Stage Fidelity Alpha）や。元ゲームと旧研究アプリのSAVE_DATAは扱わない。旧Lv60 ZIPをこの独立Alphaを入れるためにもう一度上書きしないこと。

## USB導入の事前条件（すべて明示する）

オーナーの環境はWindows11、**Windows PowerShell 5.1（`powershell.exe`）**、日本語文字を含む上記プロジェクトパス、既存Java17・Android SDK、`JAVA_HOME`は未設定でもよい。CLIは通常PowerShellをプロジェクトルートで開く。

1. USBデータ転送ができるケーブルでPCとスマホを接続する。スマホはロック解除し、開発者向けオプションの「USBデバッグ」をONにする。**スマホの「USBデバッグを許可しますか？」に許可**を選択。Windows側でADBドライバが要る機種もある。USBファイル転送(MTP)を強制指定する必要は通常ないが、認識しない場合はケーブル/ドライバ/USBモードを確認する。
2. PCのJava17 JDK `keytool.exe`、ADB（SDK Platform-Tools）、Android SDK Build-Toolsの `aapt`、`apksigner`、`zipalign` が使える必要がある。**設定を推測しない**。これで端末を書き換えずに存在確認：
   
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\tools\base_mod\independent_alpha_20261009\INSTALL-ALPHA.ps1 -CheckPrerequisites
   ```

   **5項目すべて`[PASS]`になるまで`-Apply`は実行しない。** Javaを確認するだけなら `-CheckJava` も可能。`JAVA_HOME`は必須ではない。
3. ADBの接続確認をする（これは確認コマンドで、特別な「deviceモード」を設定する操作ではない）：

   ```powershell
   adb devices
   ```

   ADBがPATHにないがAndroid SDKが標準位置にある場合は `& "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" devices` を使う。`<端末のシリアル>    device` が**1行だけ**出れば成功。`unauthorized`ならスマホの許可ダイアログを承認、`offline`ならUSBの再接続など、空ならケーブル/ドライバ・USBデバッグ設定を確認。
4. 端末が1台だけ`device`の場合、新Alphaスクリプトは**自動選択するので`-Device`も`-DeviceSerial`も不要**。複数の`device`（エミュレーターや無線ADB含む）がある場合だけ、今のスクリプトでは`-DeviceSerial "実際のシリアル"`を指定。旧Lv60スクリプトの`-Device`とは**引数名が違う**。
5. 事前確認が2つとも通ったら、同じプロジェクトルートから現行Alphaを実行：
   
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\tools\base_mod\run_independent_alpha_update.ps1 -Apply
   ```
   
   複数端末でしかも端末を1つにできない場合だけ：
   
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\tools\base_mod\run_independent_alpha_update.ps1 -Apply -DeviceSerial "adb devicesのシリアル"
   ```

   **初回はローカルAPKのオーナー署名パスワード設定が必要**。鍵は `%LOCALAPPDATA%\Kneekura\OwnerSigning\kneekura-owner-signing.p12` に保存する。次回も同じパスワードと秘密鍵を使う。別署名で既存独立Alphaが入っていれば保護のため中止し、アンインストールやアプリデータ消去をしてはならない。端末によってはインストール確認/USB経由のインストール許可が追加で求められる場合がある。

## 正確な検証境界

現行ZIPは7ファイルCRCと全マニフェスト SHA256、入口/内部/ヘルパーのUTF-8 BOM、`$HOME`衝突排除、APK本体SHA256 `9fc91ad09da1f242669404b86abbb53030aca133206f27c2cfb501a443a9ec3b` を実物に対して静的照合した。**実際にこのオーナーのWindows/USB端末で全インストールを実行した証明ではない**。CIと実機のゲートは分ける。過去のBOM、`JAVA_HOME`なし、読み取り専用 `$HOME` 事故は `docs/research/failure-repair-history.md` に残した。

現行Alphaは本家と同じ全キャラ/戦闘の完成品ではない。元ZIP `nyanko_battlecats_2026-10-06.zip`、Python仮想環境`.venv`、旧研究セーブは**今回のAPKインストールには不要**。`-TransferOwnedExport`は所有元ZIPを後から任意で転送するときだけで、通常のAlpha導入では付けない。ネットワーク接続もゲーム起動には不要。

**これからの配布も同じ「ZIPを従来のルートへ上書き展開→既存スクリプトを1回実行」形式にし、端末の前提条件と選択フラグを先に明示する。**
