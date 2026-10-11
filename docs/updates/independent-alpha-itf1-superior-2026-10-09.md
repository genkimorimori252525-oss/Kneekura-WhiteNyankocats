# にーくら独立Alpha 0.3.1 — 未来編1章クリア・最高のお宝（2026-10-09）

<!-- HISTORICAL_RESEARCH_ONLY_OWNER_NOT_PLAYABLE -->
> **IMPORTANT OWNER PRODUCT REQUIREMENT — 2026-10-09:** This document is a **historical research/test harness installation guide only**. The owner wants the **actual にゃんこ大戦争 game experience**, **NOT** the small independent Stage Fidelity Alpha lookalike. Previous conversation wording that promoted this APK as the desired playable game is withdrawn. **Do not hand this installer/APK to the owner as a finished or adequate Kneekura Battle Cats game.** It remains useful only when explicitly performing research/debug tests. The active target is original Battle Cats gameplay fidelity **AND** strict fully offline operation; see [PRODUCT_IDENTITY.md](../../PRODUCT_IDENTITY.md) and [Issue #10](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/10). Do not infer product acceptance from a CI PASS.


## オーナー承認済みの初期データ

- 日本編1〜3章：各48ステージクリア／全48ステージ最高のお宝（ランク3）。
- **未来編1章：全48ステージクリア／最高のお宝48個**。
- 未来編2・3章、宇宙編1〜3章、SoLは**未クリア**のまま。
- 元JP15.7.1で未来編1章の章インデックスは`4`（日本編`0,1,2`、歴史的な`3`は予約領域）。独立版では`eoc1/eoc2/eoc3/itf1`の章IDを使用し、元ゲームのセーブ形式・オフセットは使わない。

初期状態は `app/src/main/assets/kneekura-story-bootstrap-v2.json`、永続化・一度限りの加算反映は `StoryProgressStore.java`。最新の独立 `KNEEKURA_SAVE_V1` Python参考実装でも同じ値を扱う。プレイ済み進行や資源・キャラ・他の章の記録はリセットせず、ステージが解放されていることとクリア/報酬受取は別扱い。

**実装境界**：ステージごとのクリア数と最高のお宝ランクは、独立Alphaのアプリ内ストーリー台帳に保存できる。ただし正式な原作風の未来編選択画面や、独立バトル勝利によるストーリー進行への書戻しはまだ開発途中。旧JP `SAVE_DATA`や運営アカウントを変更しない。

## 初期起動から使うAPKとオーナー配布方式

- 独立アプリパッケージ：`jp.kneekura.whitenyankocats`
- APK versionCode：`5`、versionName：`0.3.1-post-itf1-superior`
- ビルド元のGitHubコミット：`433e7d684b27f2d27e3b2250103521f996a4f5b9`
- GitHub Actions Android debug APK run：`37909028596`
- APK本体 SHA256：`491bf95fe1f494460c280ef1c253ccd25a303bfc31b5dd916f23564d4e30c3c1`
- オーナー向け配布 ZIP：`kneekura-alpha-itf1-superior-overlay-20261009.zip`
- **ZIP SHA256**：`01a1ea0a9991c8c01a413b13a13dc490b4588e2bd3dabe797b7c807c2bac6b27`
- 修正版 INSTALL-ALPHA.ps1 SHA256：`b7302c34b18f705bab5c374935572f250ce9e221ba400dfcc522ba7fa76186ec`
- 上書き入口 run_independent_alpha_update.ps1 SHA256：`30c2869fe685375a8e7742c623f9f6120ebd7e4069b4794bf813d2c84078f0a9`
- Java helper はPS5.1検証済み修正版を変更せず再利用（`d3f7f6c1af84690a444887d0b5dbeb85e3b4b4679cb31abcb7a47ae431472ac7`）。

従来の取り込み方を厳守：ZIPを **`C:\Users\genki\Downloads\にーくらにゃんこ`** に直接上書き展開（余計な親フォルダなし）、PowerShellで：

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\base_mod\independent_alpha_20261009\INSTALL-ALPHA.ps1 -CheckPrerequisites
adb devices
powershell -ExecutionPolicy Bypass -File .\tools\base_mod\run_independent_alpha_update.ps1 -Apply
```

`adb devices`で`device`が1台なら`-DeviceSerial`は不要。既存独立アプリへの更新は以前のPCオーナー署名鍵とパスワードを必ず再利用。署名が違えば**既存アプリを消さずにインストール拒否**。インストーラーはアンインストール・データ消去・元JPセーブ書込みを行わない。

Windows PowerShell 5.1、日本語パス、空の`JAVA_HOME`、PowerShell読取専用`$HOME`変数衝突の過去事故を避けるため、配布ZIP内の全PS1にUTF-8 BOM、ハッシュ/マニフェスト全照合、Windows CIを必要条件とする。

## 検証状態

- [x] GitHubの通常テスト/Windows・Ubuntuターミナル検証
- [x] AndroidデバッグAPKビルドとINTERNET権限なしCI
- [x] 発行ZIPのCRC、全ファイルSHA、PS1のBOM、元APKとの差分・ストーリー設定の静的検証
- [ ] オーナーWindows端末での`-CheckPrerequisites`実行
- [ ] `adb install -r`実機で署名一致・進行保持
- [ ] 章選択UIからの実際の最高のお宝表示と再起動保存（未来のゲーム画面側接続）

この段階は**独立Alphaの開発更新**であり、完全なにゃんこ大戦争再現版・正式1.01リリースではない。
