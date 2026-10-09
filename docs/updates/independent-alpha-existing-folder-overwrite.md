# 独立Android Alpha — 既存フォルダへ上書きする従来の更新方式

2026-10-09。ユーザーが慣れた「にーくらにゃんこへZIP上書き展開＋PowerShell1行」に統一する。

- 個人用のZIPは会話内で渡す。ZIP直下に `tools/base_mod/run_independent_alpha_update.ps1` と `tools/base_mod/independent_alpha_20261009/{INSTALL-ALPHA.ps1,independent-alpha.apk,INSTALL-MANIFEST.json,OVERLAY-MANIFEST.json}`。余分な親ディレクトリは付けない。
- 導入（USB接続後、プロジェクトルート）：`powershell -ExecutionPolicy Bypass -File .\tools\base_mod\run_independent_alpha_update.ps1 -Apply`
- `-Apply`なしは**ハッシュ・マニフェストの静的確認のみ**で、端末を操作しない。任意の `-TransferOwnedExport` は元ZIP（ルート直下）を検査して端末にUSB送信する。
- 配布は独立アプリ `jp.kneekura.whitenyankocats`、versionCode4の Stage Fidelity Alpha。原作同等/完成版1.01ではない。
- APKはGitHub Actions `37874721255` の成果物、SHA256 `9fc91ad09da1f242669404b86abbb53030aca133206f27c2cfb501a443a9ec3b`。署名用元 `INSTALL-ALPHA.ps1` SHA256 `5f2b19732ee61913863b3bf8147137706f284b85d837e0e9886e68e0965b0b25`。
- 初回のみ PC `%LOCALAPPDATA%\Kneekura\OwnerSigning` の固定オーナー鍵を作成する。以後同じ鍵とパスワード。元ゲーム `jp.co.ponos.battlecats` および従来 `jp.kn.*` のセーブ/APIには触れない。
- USB・Android SDK・Javaは既存の環境を再利用。既存独立アプリと署名が違う場合はバックアップ元APK退避後に**停止**。アンインストール/データ消去/公式データ移行なし。
- 上書きZIPに個人 `.venv`、APK署名鍵、`SAVE_DATA`、旧元APK/Packは含めない。GitHubには導入スクリプト/手順だけ保存し、バイナリ/秘密鍵は会話で手渡し。
- 実機の導入・iボタン閲覧・再起動永続性はユーザー確認待ち。既存の独立Alphaセーブのバックアップ/復元が可能とは保証せず、署名が違ってもアンインストールしない。

今後、配布方式の変更が不要なら**この形式を毎回使うこと**。以前の配布方式から勝手に standalone ZIP を新設しない。


## PS51-JAVA-NULL repair (2026-10-09)

Important: the previous ZIPs failed first because of PowerShell 5.1 UTF-8 BOM and then because unset JAVA_HOME was used directly as Join-Path Path. Those releases are withdrawn; use only the repaired ZIP.

The repaired overwrite ZIP includes an additional source file: tools/base_mod/resolve_java_keytool.ps1. Both entrypoint and nested INSTALL-ALPHA.ps1 use UTF-8 BOM; the nested installer dot-sources the shared resolver. It now finds Java keytool from PATH, guarded JAVA_HOME/JDK_HOME and installed JDK paths, instead of requiring JAVA_HOME to be set.

Read-only Java check (does NOT install):

    powershell -ExecutionPolicy Bypass -File .\tools\base_mod\independent_alpha_20261009\INSTALL-ALPHA.ps1 -CheckJava

Optional read-only full tool availability check:

    powershell -ExecutionPolicy Bypass -File .\tools\base_mod\independent_alpha_20261009\INSTALL-ALPHA.ps1 -CheckPrerequisites

Actual update remains one familiar command after ZIP overwrite:

    powershell -ExecutionPolicy Bypass -File .\tools\base_mod\run_independent_alpha_update.ps1 -Apply

Exact repaired nested installer SHA256: a2f6f8f011275296340fcaec15e49eb498e0f4bd77096ce92ad8d5ee59c08bc4
Exact shared Java resolver SHA256: d36f57ce928807fde46738ab64ad1f61e7b651118c08821842ffe3835b3b18f0
APK SHA256 (unchanged): 9fc91ad09da1f242669404b86abbb53030aca133206f27c2cfb501a443a9ec3b

CI: Windows Powershell 5.1 tests missing JAVA_HOME/LOCALAPPDATA. Actual user USB signing/key/password and on-device install are separate USER_GATE, NOT covered by CI.
