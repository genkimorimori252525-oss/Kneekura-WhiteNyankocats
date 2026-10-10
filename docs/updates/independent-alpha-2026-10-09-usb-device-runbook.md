# 独立Android Alpha — USB導入・iボタン実機検証（2026-10-09）

<!-- HISTORICAL_RESEARCH_ONLY_OWNER_NOT_PLAYABLE -->
> **IMPORTANT OWNER PRODUCT REQUIREMENT — 2026-10-09:** This document is a **historical research/test harness installation guide only**. The owner wants the **actual にゃんこ大戦争 game experience**, **NOT** the small independent Stage Fidelity Alpha lookalike. Previous conversation wording that promoted this APK as the desired playable game is withdrawn. **Do not hand this installer/APK to the owner as a finished or adequate Kneekura Battle Cats game.** It remains useful only when explicitly performing research/debug tests. The active target is original Battle Cats gameplay fidelity **AND** strict fully offline operation; see [PRODUCT_IDENTITY.md](../../PRODUCT_IDENTITY.md) and [Issue #10](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/10). Do not infer product acceptance from a CI PASS.


**目的:** 以前の本家セーブ不正表示と完全に切り離した `jp.kneekura.whitenyankocats` の独立AlphaをUSBデバッグで検証。現段階はStage Fidelity Alphaであり、原作同等の基地・戦闘を再現した完成版ではない。

## ビルドの出所

- GitHub Actions: [Android debug APK build 37874721255](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/actions/runs/37874721255)、成功、INTERNET権限なし検査合格。
- GitHub head: `2ffd09feac9ececc674765fc35d60b603efa5059`（3件の内蔵お知らせ・i入口）。
- Artifact ID: `11591713304`、APKを抽出したSHA256：`9fc91ad09da1f242669404b86abbb53030aca133206f27c2cfb501a443a9ec3b`（71,193 bytes）。
- ユーザーにはこの検証済みAPKと、GitHub artifactから抽出したAPKを**オーナー専用の固定鍵で再署名する**USB導入ZIPをChatGPT内で提供。ダウンロード用キットはGitHubには保存せず、オーナーPC上で署名・インストールする。
- AndroidアプリID：`jp.kneekura.whitenyankocats` / versionCode `4` / `0.3.0-verification-harness`。本家/旧改造元の `jp.kn.*` とは別アプリ。

## 帰宅後のテスト手順

1. WindowsにADB・Android SDK Build-Tools（aapt, apksigner, zipalign）・Java17があり、端末にUSBデバッグが許可されていることを確認。
2. 会話添付の `kneekura-independent-alpha-usb-kit-20261009.zip` をPCに展開。まず `README-START-HERE.txt` を読む。`START-USB-INSTALL.cmd` でローカルAPKに対してsource SHA256、パッケージ・バージョン、INTERNET権限不在、唯一のUSB端末をチェック。
3. 初回のみ、PCの `%LOCALAPPDATA%\Kneekura\OwnerSigning\` にオーナー専用署名鍵を作成。パスワードと秘密鍵は安全にバックアップし、GitHub/ChatGPTへはアップロードしない。以後この鍵を継続利用。
4. すでに同じ独立アプリが端末にある場合は元のAPKをPCに退避し、署名一致を確認。違えば**インストール中止**、アンインストール・データ初期化はしない。
5. 成功したら画面右上の `i` → お知らせ3件 → 詳細 → 戻るを試験。端末を再起動後も同様に確認。
6. 既存のオーナー用JP15.7.1 ZIPを使って追加のステージ素材読込を試す場合は、任意の `-OwnedExport` 引数で一致SHAの元ZIPをUSB転送し、独立アプリの「export ZIP読込」から選択する。APK/端末元SAVEを改造する動作ではない。

## 正確な保全・ブロッカー

- このキットで元ゲームのアプリ、元ゲームのSAVE_DATA、PONOS通信は使わない。
- 既存の独立版に不一致の署名で導入済みの場合、将来のゲーム内進行を保護するため**無理に上書きしない**。`android:allowBackup=false` のため、既存独立Alphaのアプリ内セーブがADBのみで必ず復元可能とはいえない。
- **ソース/CIはPASS、ユーザー実機でのUSBインストール・表示・署名更新・保存永続性は未確認。** 初期導入の失敗ログは署名・ADB・SDK・端末状態に絞って共有し、元SAVEや鍵を渡さないこと。
- 変更可能なのは開発中の独立ゲームのAPKのみ。「運営更新」はローカルの署名付きJSONパック取り込みとして別系統で、APKを更新する代替にはならない。
- 開発残件は [Issue #7](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/7) と [Issue #5](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/5)、[Issue #6](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/6) で継続管理。
