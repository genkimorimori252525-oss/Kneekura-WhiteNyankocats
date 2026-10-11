# PC研究環境の実測結果

2026-10-12 JST。所有者が専用PC仮想端末・ビルドツール・開発鍵・破棄可能データでの非対話試験を承認した。新しい開発経路は `tools/PC-LAB.ps1`、本体は `tools/pc_lab.py`。

**追試が最新:** 以下は初回環境構築時の記録。[PC追試](2026-10-12-pc-resource-repair.md)で文字列ID0例外とAPI35の素材所有者を修正し、393取り込み・35TSV・例外なしの再起動まで進めた。ShadowHook初期化12と原作読み込み中のネットワークエラー、基地未到達は残っている。

## 用意した環境

- Windows 11 / Intel x86_64 / WHPX、Android Emulator 36.5.11。
- 専用AVD `kneekura-pc-api35`、API35 Google APIs x86_64、ARM64変換 `libndk_translation.so` 0.2.3。
- NDK 27.2.12479018、CMake 3.22.1、Android build-tools 35、JDK17、Python3.12。
- PC専用PKCS12鍵。パスワードはDPAPIで暗号化し、同じWindowsユーザーで自動再利用する。鍵フォルダはそのユーザー専用ACL。
- ソースは `2dbbc88d8aa8ef2c0fb1e5c712980f6136e02004` から分離した作業領域。ローカル変更は各実行の差分と未追跡ソースのハッシュで記録する。

SDK管理ツールのNDKダウンロードが進まなかったため、公式配布アーカイブを取得し、Googleのrepository XMLに記載されたSHA1 `ac5f7762764b1f15341094e148ad4f847d050c38` と一致を確認して導入した。CMakeの公式アーカイブSHA1は `292778f32a7d5183e1c49c7897b870653f2d2c1b`。ビルド出所は `local-pc-research-passive-shim-v1` として公開CI出所と区別する。スマホの既存署名ゲートは既定のまま維持する。

## 実行と証拠

ローカルARM64診断ライブラリのコンパイル、既存の原作再構築ゲート、6分割APKの自動署名が成功した。署名前後のゲームペイロード一致、原作実行コード、INTERNET権限なし、受領書SHAを既存関数で確認した。導入後は端末の6APKそれぞれの実SHA-256も照合した。外部393素材は元のサイズ・MD5で検証して専用研究パッケージ内だけに格納した。

| 実行ID | 収集結果 | 実測 |
| --- | --- | --- |
| `20261011T170727Z-94511f28` | 初版では取得判定未合格 | 初回画面を表示。UTCオフセットを既存解析器が読めない問題と、IPCの `dropped` を欠落と誤判定する問題を発見。元証拠は上書きせず保持。 |
| `20261011T171050Z-3af53ba8` | `COMPLETE_BOUNDED_CAPTURE` | 起動前後バリア、4画面、PID履歴、全バッファログ、終了情報を保存。ShadowHook初期化12、原作receiverのJava例外と終了を捕捉。 |
| `20261011T171546Z-fea40498` | `COMPLETE_BOUNDED_CAPTURE` | 3画面を保存。Java例外の型・文字列リソースID0・receiverを秘密メッセージなしで要約し、同じ終了を再現。 |
| `20261011T172133Z-7c9381f6` | `COMPLETE_BOUNDED_CAPTURE` | Windows PowerShell5.1の `Update` を非対話実行し、同一PC署名で再ビルド・更新・収集を確認。 |
| `20261011T172454Z-114adf90` | `COMPLETE_BOUNDED_CAPTURE` | 最終実装で再度 `Update`。全証拠のSHA-256一致と、収集コード3ファイルの実バイトスナップショットを確認。 |

`COMPLETE_BOUNDED_CAPTURE` は、この実行区間の開始・終了ログ到達、起動要求、画面取得、取得エラーなし、観測されたログ欠落なしを表す。アプリが終了しても収集が成立した場合はこの判定になる。Androidがそもそも記録していない内部状態や、すべてのネイティブ呼出しの捕捉を保証しない。全生ログ・画面・端末情報・署名受領書はgitignored `private/pc-lab` 以下にあり、GitHubへ公開しない。

## ゲーム側の未解決点

1. ARM変換下のShadowHook初期化が `12` で失敗する。公式[ShadowHook v2.0.1 header](https://github.com/bytedance/android-inline-hook/blob/v2.0.1/shadowhook/src/main/cpp/include/shadowhook.h) の `SHADOWHOOK_ERRNO_INIT_LINKER` に一致する。これだけでゲームのシーン97停止原因やJava例外の原因を断定しない。
2. 再起動時に `jp.co.ponos.battlecats.ReceiverInitAlarm` が `android.content.res.Resources$NotFoundException: String resource ID #0x0` で終了する。原作リソース検索と隔離パッケージ名の関係を次に調べる。フック失敗と同一原因だとは未証明。
3. 本WindowsエミュレーターはARM64 AVDを `System image must match the host architecture` として拒否した。エンジン直接起動も試したが、ARM64端末の起動成功は確認できなかった。
4. native scene97 / resolver 35分類、にゃんこ基地、原作セーブ・育成・まどか・シンゴジラのゲーム内受入、SDKを含む通信ゼロは未合格。ゲストWi-Fi/data無効とアプリのINTERNET権限なしは、製品全体の無通信試験の代用にしない。

## 再実行

```powershell
.\tools\PC-LAB.ps1 -Action Run -ObserveSeconds 30
.\tools\PC-LAB.ps1 -Action Update -ObserveSeconds 30
.\tools\PC-LAB.ps1 -Action Check
```

`Run` は既存候補の起動・収集、`Update` は専用端末起動→ローカルビルド→同じPC鍵で署名→研究版更新→393素材照合→起動・収集を行う。登録済みの元ZIP/AARの場所とPC鍵を自動利用する。専用名とシリアル以外の端末を選択しない。スマホへの適用は含まない。

原作ゲームが正常に起動したとの判定はまだ行わない。現在の成果は、PCだけでAPKのビルド・導入・起動・障害の記録を再現できる研究環境である。

## 最終検証

- `py -3.12 -B -m unittest discover -s tests -p 'test_*.py'`：730件実行、720成功・10スキップ・失敗0。
- `tests.test_pc_lab`：11件成功。起動対象・端末内APKの改変・出所・UTC・過去バッファ混入・ログ欠落・Java例外の秘密保持・ビルド失敗時ログの保存を確認。
- Android ARM64 C11 / `-Wall -Wextra -Werror` のローカルNDKビルド、署名前原作ゲート、同一PC鍵の自動再利用、6分割APKの実導入・ハッシュ照合、393素材の実MD5照合を確認。
- Windows PowerShell5.1の入口を非対話で実行し、収集終了バリア・画面・受領書・ソーススナップショットのハッシュを確認。
- 独立した最終レビュー：Critical / Important 指摘なし。Minorのビルド失敗ログ未保存は回帰テストのRED→GREENで修正した。
- `git diff --check`：成功。GitHubへ原作APK・SAVE・鍵・私的ログは送信していない。今回のソース差分もローカルの独立ブランチに保持する。
