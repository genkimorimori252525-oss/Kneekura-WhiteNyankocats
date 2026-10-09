# 独立Android Alpha — 既存フォルダへ上書きする従来の更新方式

2026-10-09。ユーザーが慣れた「にーくらにゃんこへZIP上書き展開＋PowerShell1行」に統一する。

- 個人用のZIPは会話内で渡す。ZIP直下に `tools/base_mod/run_independent_alpha_update.ps1` と `tools/base_mod/independent_alpha_20261009/{INSTALL-ALPHA.ps1,independent-alpha.apk,INSTALL-MANIFEST.json,OVERLAY-MANIFEST.json}`。余分な親ディレクトリは付けない。
- 導入（USB接続後、プロジェクトルート）：`powershell -ExecutionPolicy Bypass -File .\tools\base_mod\run_independent_alpha_update.ps1 -Apply`
- `-Apply`なしは**ハッシュ・マニフェストの静的確認のみ**で、端末を操作しない。任意の `-TransferOwnedExport` は元ZIP（ルート直下）を検査して端末にUSB送信する。
- 配布は独立アプリ `jp.kneekura.whitenyankocats`、versionCode4の Stage Fidelity Alpha。原作同等/完成版1.01ではない。
- APKはGitHub Actions `37874721255` の成果物、SHA256 `9fc91ad09da1f242669404b86abbb53030aca133206f27c2cfb501a443a9ec3b`。署名用修正版 `INSTALL-ALPHA.ps1` SHA256 `a2f6f8f011275296340fcaec15e49eb498e0f4bd77096ce92ad8d5ee59c08bc4`。
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
Exact shared Java resolver SHA256: 6f9ab5a9164f9ce1005c9cb961cc2e1c61bfc13b24cd29ba74c9fd44d9fbedbf
APK SHA256 (unchanged): 9fc91ad09da1f242669404b86abbb53030aca133206f27c2cfb501a443a9ec3b

CI: Windows Powershell 5.1 tests missing JAVA_HOME/LOCALAPPDATA. Actual user USB signing/key/password and on-device install are separate USER_GATE, NOT covered by CI.

### 2026-10-09 release candidate fingerprint and mandatory actual ZIP audit

**User-facing repaired owner ZIP ONLY**: `kneekura-alpha-existing-folder-overlay-java-fixed-20261009.zip`
- Verified final ZIP SHA256: `486dddd998895de91526e8acaebe68e65e072bdaa2ce21360d1746d127c5ac06`.
- Contains exactly 7 files. APK remains `9fc91ad09da1f242669404b86abbb53030aca133206f27c2cfb501a443a9ec3b` (no game-content changes).
- Source wrapper, nested installer and Java resolver are all UTF-8 BOM; null-safe JDK search, `-CheckJava` and `-CheckPrerequisites` before the optional USB `-Apply`.
- SHA256 of nested installer: `a2f6f8f011275296340fcaec15e49eb498e0f4bd77096ce92ad8d5ee59c08bc4`; Java helper: `6f9ab5a9164f9ce1005c9cb961cc2e1c61bfc13b24cd29ba74c9fd44d9fbedbf`; outer wrapper: `9023beed724e8763916797a9ee54cc3af1b7e5c392b06571c74700d070bb55fe`.
- Before handing any future ZIP to the owner, **run the packaged artifact auditor on that exact ZIP, after the final byte change**, not just source unit tests:

```powershell
python -m tools.base_mod.audit_owner_overlay_zip .\kneekura-alpha-existing-folder-overlay-java-fixed-20261009.zip
```

This is a read-only audit only. It must pass ZIP integrity, all manifest SHA digests, actual nested PowerShell BOM, JAVA_HOME-null regression, no-uninstall contract and outer-wrapper digest pinning. Windows 5.1 parser/JDK resolver CI is an additional gate. Failure means **NO RELEASE**. The completed Android device install remains a separate owner USER_GATE.

### Release correction: exact shipped ZIP audit (2026-10-09)

The initial JAVA_HOME-fix ZIP still had a stale outer SHA256 pin for the Java resolver. This **was detected by running** `tools/base_mod/audit_owner_overlay_zip.py` on the actual distribution ZIP (the prior source-only tests did not catch it). The bad intermediate ZIP is WITHDRAWN. Use only `kneekura-alpha-overwrite-verified-v3-20261009.zip` (SHA256 `486dddd998895de91526e8acaebe68e65e072bdaa2ce21360d1746d127c5ac06`).

Release verification actually performed on this exact ZIP: ZIP CRC PASS, seven entry SHA256 digests PASS, three PowerShell UTF-8 BOM headers PASS, APK original digest unchanged, nested installer a2f6f8... and keytool resolver 6f9ab5... pinned in the OUTER entrypoint. The exact wrapper matches the GitHub tracked source blob `7cb832abb76320ae8dde6da02653ed36426cc5b4`, resolver matches blob `4200d83974e06b8f1fcb5f8f7bb4476a683777be`.

This static check does **not** prove successful USB install. All future releases must include the ZIP-level auditor result, not just PowerShell parser/CI PASS.
