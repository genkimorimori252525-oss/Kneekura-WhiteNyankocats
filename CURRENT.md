# CURRENT.md — にーくら大戦争 唯一の作業入口

**ACTIVE / 初めてのセッションでもこのファイルから始める。** どの開発エージェントも設計書を片っ端から読んで「本当の原則」を探してはいけない。設計の下位文書は実装時の参照資料であり、プロダクトを変更する権限を持たない。

## 現在の作業位置

**[親Issue #11 — 実装進捗](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/11)** が唯一の「いま何をしているか」の入口。**直近の次のコード差分は [#12 LEVEL — 本家育成画面のレベル上限](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/12)**。**[#15 OFFLINE — 元ゲーム保持＋通信ゼロ](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/15)** は同時進行。次に **[#13 MADOKA](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/13)**、**[#14 GODZILLA](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/14)**。この順序・実装担当のために新しい基本計画を作らない。

## 原則の優先順位（不一致ならこの表で決定）

| 優先 | 原本 | 説明と変更権限 |
|---|---|---|
| 0 | **オーナーの最新の明示的な指示** | 本家『にゃんこ大戦争』のゲーム体験が必要。別ゲーム・簡易Alphaは不許可。仕様変更はオーナーの明示指示だけ |
| 1 | [PRODUCT_IDENTITY.md](PRODUCT_IDENTITY.md) | **製品とは何か/何ではないか**の絶対条件。本家のシーン・UI・アニメ・戦闘・キャラ/ステージ/ガチャを忠実に保ち、外部通信もゼロ。2軸とも必須 |
| 2 | **この CURRENT.md** | どれを読むか、どの計画を実行するか、過去の矛盾をどう扱うかを一元管理 |
| 3 | [実装中の単一ロードマップ](docs/roadmap/2026-10-09-original-battle-cats-delivery.md) | **いまやる順序と、各成果物・受入テスト**。レベル→まどか→ゴジラ、完全オフラインは並行。この文書以外に並列の「current roadmap」を作らない |
| 4 | [1.01数値原本](docs/updates/manifests/update-1.01.json)、[受入ゲート](docs/architecture/product-identity-gates.json) | **ユーザーが承認した数値・状態と実証条件**。前者 `PREVIEW_ONLY_NOT_INSTALLABLE` は実装完了を意味しない |
| 5 | [AGENTS.md](AGENTS.md) | **コード作業/検証/Windows配布の手続き**。製品の意味やゲームの仕様を変更できない |
| 6 | 1次証拠・過去の文書・研究ハーネス | 特定タスクの技術参照**だけ**。本表の上位と矛盾した内容は旧設計/研究履歴として扱う |

## オーナーWindows開発環境 — 実測固定パス（2026-10-11 明示依頼）

**以後すべてのAI・Codex・端末案内で先に参照する。** オーナーが繰り返し提供した既存環境。環境構築のために勝手に別のSDKや仮パス `C:\\PATH\\TO` を指示しない。実機は接続状態が変わるため、毎回動的に確認する。本人が環境を変更した場合はこの節を更新する。

| 項目 | オーナー環境での場所・実測 |
|---|---|
| Windowsユーザーフォルダ | `C:\\Users\\genki` |
| Android SDK **正本** | `C:\\Users\\genki\\AppData\\Local\\Android\\Sdk`（PowerShellは `$env:LOCALAPPDATA\\Android\\Sdk`） |
| Android ADB **正本** | `C:\\Users\\genki\\AppData\\Local\\Android\\Sdk\\platform-tools\\adb.exe`（ADB 37.0.0 動作確認済み） |
| Android build-tools | **34.0.0 / 36.1.0 / 37.0.0** で `zipalign.exe`、`apksigner.bat`、`d8.bat` が存在することを実測。**35.0.0** も2026-10-11 `sdkmanager "build-tools;35.0.0"` で追加され、専用ビルドスクリプトの `zipalign.exe` / `apksigner.bat` / `d8.bat` 存在チェックを通過して**keytool署名鍵作成のパスワード画面まで到達済み**（実行ログが根拠） |
| Android API 35 | `C:\\Users\\genki\\AppData\\Local\\Android\\Sdk\\platforms\\android-35\\android.jar` 存在確認済み |
| SDK Manager | `$env:LOCALAPPDATA\\Android\\Sdk\\cmdline-tools\\latest\\bin\\sdkmanager.bat`。SDK XML v3/v4の警告は一度観測（終了後は実ファイル・終了コードを確認） |
| GitHub作業リポジトリ | `C:\\Users\\genki\\Downloads\\Kneekura-WhiteNyankocats`（`CURRENT.md` と `tools\\base_mod\\build_owned_static_http_bridge.py` 存在確認済み） |
| **所有原本JP15.7.1 ZIP** | `C:\\Users\\genki\\Downloads\\にーくらにゃんこ\\nyanko_battlecats_2026-10-06.zip` |
| 原作Android実機研究キット | `C:\\Users\\genki\\Downloads\\kneekura-original-owner-trial-kit`（`BUILD-ORIGINAL-RESEARCH.ps1` 存在確認済み） |
| Python | `py -3.12`、`lief==0.17.6` と `pycryptodome==3.24.0` インストール済みの本人出力 |

**AIが出すコマンドの最小規則：** PowerShellから `$sdk = Join-Path $env:LOCALAPPDATA 'Android\\Sdk'`、`$adb = Join-Path $sdk 'platform-tools\\adb.exe'` を使用。通常は `$repo = Join-Path $HOME 'Downloads\\Kneekura-WhiteNyankocats'`、`$zip = Join-Path $HOME 'Downloads\\にーくらにゃんこ\\nyanko_battlecats_2026-10-06.zip'`、`$kit = Join-Path $HOME 'Downloads\\kneekura-original-owner-trial-kit'`。**研究版をビルドする時は `-RepositoryRoot $repo -OwnerExportZip $zip -PublicKitDirectory $kit` を必ず指定**する。カレントディレクトリだけでリポジトリを決定しない。 `zipalign.exe` はBuild-toolsの実在版を事前確認し、必要な35.0.0がなければバージョンを確認して追加インストールを案内。

**実機安全条件：** `adb devices` が空なら端末を再接続しUSBデバッグ認証を確認する。過去に`device`表示があっても、接続中と断定しない。端末固有シリアルは永続記録しない。原作公式アプリ `jp.co.ponos.battlecats` / 元SAVEは `uninstall` / `pm clear` / 上書きの対象にしない。実験対象は別パッケージ `jp.kn.local.battlecats` のみ。**2026-10-11 実機更新（所有者の一次端末ログ）：** 元JP15.7.1の別パッケージ `jp.kn.local.battlecats` を原作6分割APKでビルド・署名し静的検証PASS。新規インストールで `adb install-multiple --no-streaming` は **`Success`**、`adb shell pm path jp.kn.local.battlecats` で6分割すべて検出。`adb shell am start -n jp.kn.local.battlecats/jp.kn.local.battlecats.MyActivity` は起動リクエスト受理（`Starting`）したが、**端末画面は黒のまま**。初回読み取り専用観測 `py -3.12 -m tools.base_mod.collect_original_local_first_boot --output private/original-first-process.json` は **`read-only adb command could not finish`** で停止し、元アプリが実際に動いたこと・本物の初回SAVEが生成されたことは未証明。**絶対に「起動PASS」「PLAYABLE」と宣言しない**。既存の公式アプリとSAVEを消さない。次に行うこと：現在接続中のPID/Android Activity状態と、`KNEEKURA_STATIC_HTTP` 固定タグのlogcatをADBで安全に診断する。端末シリアルは恒久保存しない。パスワード・秘密鍵をコミット/チャットに提出しない。

### 2026-10-11 追跡更新 — 黒画面の実ログ、ShadowHook補助ライブラリと次の実機ゲート

- 本人の `20261011-040424` プライベートlogcatを研究用パッケージID/PIDで再集計し、**研究版プロセス起動86、死亡85、`original-native-scene-hook-v1 hook-initialization-failed` 85**を確認。古い「87/87」には無関係な他アプリ起動が混入していたので訂正。SIGSEGV履歴と具体的な終了バックトレースの因果はまだ特定できていない。公式元ゲームの起動・SAVE生成・Lv60は未合格。
- 原因候補の一つとして、旧研究版へのShadowHook 2.0.1 `libshadowhook.so` だけの同梱漏れを発見。現行PR#4では公式Maven AAR 1個から `libshadowhook.so` と `libshadowhook_nothing.so` を**両方必須**とし、AARと個別のSHA-256、原本ARM64実行命令を検証する。公式ヘッダーのinit UNIQUE=1 / hook UNIQUE flag=2は正しい。**ライブラリの同梱修正は静的CI PASSで、黒画面の実機修復PASSではない。**
- 次の所有者PC側作業は `tools/base_mod/BUILD-OWNER-RESEARCH-PAIR.ps1` による**既存研究用署名鍵・CIのPASSIVE（virgin SAVE writer OFF）ARM64 `libkneekura.so`＋SHA受領書・本人ZIP・公式ShadowHook 2本**でのソース保全付き6分割再ビルド。署名パスワードはコマンド引数に載せず、プロセス内で一時的に環境変数へ渡して終了時削除する。署名/ソース一致を満たさなければ中断。
- このビルドと端末アップデートは別工程。実機上の研究版 `jp.kn.local.battlecats` の実際のインストール済み証明書と候補6本を `tools/base_mod/CHECK-OWNER-RESEARCH-DEVICE-SIGNER.ps1`（内部の `preflight_original_device_update.py`）で**読み取り専用照合**するまで、`-r` インストールはしない。さらに候補 `libkneekura.so` はCIコンパイル済みの `PASSIVE_SHIM_BUILD_SOURCE_RECEIPT.json` のSHAと一致必須。
- それらのゲートが実機で通った場合だけ、本人が明示的に選んで研究版6分割を上書き更新し、`CAPTURE-OWNER-ORIGINAL-CRASH.ps1` で研究版を1回のみ起動、`summarize_original_crash_capture.py` で機密抜きの集計JSONを生成する。古い単独ShadowHook研究キットを再実行しない。**公式 `jp.co.ponos.battlecats` やSAVEの削除・再利用・H01/BAN回避なし。** 具体的なコード/テストと成果は既存 [Issue #12](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/12) に一本化。

### 2026-10-11 続報 — Android実ツール署名確認と更新実行の安全な単一ゲート

- **合成ではあるが実Android SDKによる実署名が成功。** `.github/workflows/real-apksigner-env-smoke.yml` はWindows/Linux両方で `aapt2` による合成APK生成、`zipalign`、実`keytool`の一時秘密鍵、`apksigner`による原作と同じ6分割名の署名/検証を実行。パスワードの`env:`渡しと内容保持を検証、元ゲームAPK・公式SAVEは未使用。[実SDK検証](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/actions/runs/38083892128) 両OS PASS。ただし所有者実キーでの原作ゲーム署名・実起動ではない。
- **本人が明示承認した場合だけ研究版を6分割で1回更新する実コード**：`tools/base_mod/INSTALL-OWNER-RESEARCH-PAIR.ps1` → `tools/base_mod/update_original_isolated_research.py`。既存 `preflight_original_device_update.py` による本人端末に現存する**研究用パッケージだけ**のread-only署名/ネイティブ証明確認に合格後、研究版が動いておらず同じUSB端末・6本ハッシュが維持されている時だけ `adb install-multiple --no-streaming -r`。失敗・タイムアウト時は自動再試行せず、公式アプリやSAVE領域へ介入しない。再インストール・初期化・署名違いでの置換をしない。
- **更新後の実バイト照合**：署名一致だけではShadowHook修正がインストールされた証拠にならないため、privateの一時領域で研究版の`base.apk`と`split_config.arm64_v8a.apk`を読み取り、新候補とSHA-256一致を要求（残り4分割は導入確認・署名検証のみ）。一時コピーは削除、出力レシートには端末ID/証明書/SAVE/APK本文を保存しない。実機での同一鍵ビルド・更新・起動はいずれも **OWNER_GATE / 未実施**。
- 実Android署名のCI成功＋合成ADB更新テストは、**原作の黒画面解消・初回SAVE・Lv60/MAX・運営i/まどか/ゴジラ/完全オフラインの受入PASSではない**。次の現物試験は本人Windowsで既存研究用署名鍵を使い`BUILD-OWNER-RESEARCH-PAIR.ps1`により原作所有ZIPからPrivate候補を作り、read-only signer gateを通過後にのみ本人の明示操作で更新・一度だけログ採取。旧一個だけのShadowHook `.so`を含むトライアルを再実行しない。

## このファイルの後に読むもの（最大限絞る）

**普段の新規AIセッション：** このファイル → PRODUCT_IDENTITY.md → 実装ロードマップの「実行順序と次の担当者向け開始地点」→ 今動かす1タスクのソース/証拠だけ。毎回すべてのdocs/を巡回する必要はない。

| 作業分野 | 当面追加で読む一次資料だけ |
|---|---|
| レベル上限 | `tools/base_mod/level_cap_unlock.py`、`tests/test_level_cap_unlock.py`、実JP15.7.1 `unitbuy.csv`/元ネイティブ育成接点 |
| まどか | `docs/updates/manifests/update-1.01.json` の `madoka`、`tools/base_mod/prepare_update_manifest.py`、`native/kneekura-shim/src/kneekura_battle101.c`、本家実ダメージ・攻撃/演出接点 |
| シン・ゴジラ移植 | 同1.01 JSONの `godzilla`/source_assets、`tools/base_mod/collect_update_101_server_assets.py`、`kneekura_battle101.c`、所有者privateの `550_e` 元素材/味方 `702_f`。**Server原本4ファイルは所有者PCで原本MD5 4/4照合成功**。[GODZILLA実装AIへの回収・抽出手順](docs/updates/godzilla-source-acquisition-handoff.md)、`tools/base_mod/fetch_godzilla_server_assets.py`（Gitにはスクリプトと照合値だけ。実体はprivate/のみ）、[詳細証拠](docs/research/2026-10-10-original-server-archive-acquisition.md)。元画像7件→味方No703第1形態702_fの**非インストール用プレビュー生成コード**は実装・合成暗号化パック試験PASS（`tools/base_mod/prepare_godzilla_ally_preview.py`、`--prepare-ally-preview`）。所有者PC側の回収バイナリは未転送だが、**原本JP15.7.1のサイズ・MD5に一致する公開アーカイブ4ファイルをGitHub Actions一時領域で実取得し、実物550_e 7件を復号、702_f変換・WImageDataServer候補の暗号化再読込までPASS**。[原本実パック検証証拠](docs/evidence/jp15.7.1-godzilla-real-mirror-proof.md)（元素材はCI終了前に破棄）。原作Server登録順（WImageDataServer index4→QNumberServer index27）の先着キー保持を踏まえた**非インストール用WImageDataServer 702_f読込候補**も実装（`tools/base_mod/prepare_godzilla_native_resource_preview.py`）。元`702_c`と無関係な暗号化資産は不変、**4ファイル照合→7件抽出→702_fプレビュー→WImageDataServer候補**の一括コマンド（`--prepare-native-resource-candidate`）と暗号化合成パックの全工程テストまでPASS。**フル一括時は4工程を一時領域で検証してから公開、遅い失敗時は中途出力を巻戻し**（Windows/Linux合成テストPASS、電源断時の4ディレクトリ原子性は非保証）。所有者PCの回収ファイル4件のSHA-256独立照合、改変候補の原作ダウンロード表MD5適合、原作Android実機資産選択・描画・戦闘は未完了 |
| 完全オフライン | `docs/evidence/jp15.7.1-offline-egress-static-receipt.json`、`docs/references/native-service-map-jp15.7.1.md`、`docs/architecture/2026-10-09-complete-local-offline-audit.md`（**証拠**として）、`bridge/java/MyActivity.java.in` |
| MAX資源・育成/アイテム | `docs/updates/manifests/full-max-start-jp15.7.1.json`、`tools/base_mod/build_offline_max_save.py::MAX_VALUES`、`tools/localcore/full_max_resources.py`（**ローカルセーブ実装、元のゲームUIへの接続は未了**） |
| iボタン/運営予定表 | `tools/localcore/ops_calendar.py`、`notice_feed.py`、`login_rotation.py`、`ops/seasons/2026-autumn-prototype.json`、`docs/architecture/kneekura-offline-notices.md` |
| 共通の配布/再発防止 | `docs/research/failure-repair-history.md`、`AGENTS.md` のWindows部分（**ゲームが実装できた後だけ** owner ZIPを発行） |
| USB/ADB初期診断と将来の初期セットアップZIP | [Issue #16 — Device preflight](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/16)、`AGENTS.md` の「Owner Android device / ADB preflight」（**手順改善の追跡のみ。新たな本体計画やZIP完成ではない**） |

## 旧設計を読む場合の明確な区別

- `docs/architecture/design-philosophy.md`：**原作維持の方針と技術根拠**。冒頭にあるオーナー最新判断以外は歴史的な記述を含む。
- `docs/architecture/current-design.md`、`base-preserving-android-mod.md`：**元エンジン候補の設計・検証資料**。これは本書に代わる新規の実装計画ではない。
- `docs/architecture/2026-10-09-complete-local-offline-audit.md`：**不十分な通信遮断の一次静的証拠と危険箇所**。かつて独立ホストに言及した部分は「原作との一致を免除する」という意味ではない。
- `docs/architecture/kneekura-post-eoc-liveops.md`：**旧設計の履歴**。未来編1章未クリア、ゲーム内ネットからの自動更新等の古い案は現在不採用。
- `docs/architecture/kneekura-independent-story-checkpoint-v2.md`：**初期章状態だけ**を扱う。Stage Fidelity Alphaの実装を本家と呼ばない。
- `app/` Stage Fidelity Alpha、`android/local_update`：**試作・テスト専用**。元ゲームとは異なる。CI PASSでも製品の完成とは無関係。
- `docs/architecture/kneekura-offline-operations-charter.md` 等の運営室設計：**将来の実ゲーム運営の詳細**。この4機能の実装を放置してUI/告知の新規ハーネスを作る根拠にはならない。

**未列挙の設計書は、リンクが関連タスクから求められるまで** `REFERENCE_ONLY`。ファイル名が`current`、`final`、`approved`であっても、本書を上書きできない。

## 4つの中核実装＋2つの必須横断仕様（削除不可）

**LEVEL** 公式データ内のLv60/50/20/1キャップを本家育成/実戦で使う。**MADOKA** 原作第3形態のLv30実攻撃28,000/感知750/費用4,550/再生産155秒。**GODZILLA** ゴジラにゃんこ第1形態（敵シン・ゴジラrig転用）のLv30三連撃50,000×3/2950/9800/500秒/城への一連撃最大1。**OFFLINE** 原作ゲーム体験のままサーバー/広告SDK/公式SAVE依存なし。

**初期状態はこれまでどおり資源もMAX（ユーザー再確認）**：XP 99,999,999、ネコカン45,000（旧研究エディタ採用値／ゲーム内部上限は要確認）、NP9,999、各種チケット、マタタビ、キャッツアイ、ネコビタン、統率力回復アイテム、城素材、本能玉等の**研究版全20カテゴリ**。唯一の数量原本は `docs/updates/manifests/full-max-start-jp15.7.1.json`（以前の `build_offline_max_save.py::MAX_VALUES` を再利用）。新規ローカルセーブには初回MAX、既存セーブは非破壊で一度だけ加算移行し、使用後は毎回勝手に補充しない。原作の育成/所持品UIへ実接続できるまでは完了扱いにしない。

**ジョリーがPONOSに代わり運営する業務も必須（今回改めて確定）**：本家基地**右上i**からジョリーのお知らせ（日時・カテゴリ・本文）を読む、ガチャと排出内容の更新、限定/曜日/月次ステージ、イベント、ログイン5枠循環、ミッションと報酬、育成イベントの倍率・お知らせ・変更履歴。既存 `ops/seasons/`, `tools/localcore/ops_calendar.py`, `notice_feed.py`, `login_rotation.py`, `docs/architecture/kneekura-offline-operations-charter.md`, `kneekura-offline-notices.md` を**継続**。現在は運営データと試作のi画面が存在するが、原作ゲームの基地/ガチャ/ステージ/UI連動は未実装。**Stage Fidelity Alphaでiが表示できたことは本家での完成を意味しない**。

**日本編1〜3章＋未来編1章クリア/最高のお宝**も共通の既定初期値。現在の中核工程はLEVEL→MADOKA→GODZILLA、OFFLINEを並行。**MAXはLEVEL/保存・育成経路の一部、運営業務はOFFLINE/本家UIとの統合の一部として実装**し、どちらも最終受入れから除外しない。別ゲームや新しい運営UIハーネスを作り直す仕事へ逸れない。

## 実装上の厳禁

- `Phase 0`/基礎設計/整理のやり直しを完了基準にしない。**次のコード作業は本家育成レベル上限への一本の縦割り実装**。元エンジンとの接点はこの作業の一部。完全オフラインの調査は同時進行。
- 原作に接続されていないCSVプレビュー、native判定関数、テスト用ゲームUIを「実装完了」と数えない。各タスクに原作の画面・実戦・再起動の証拠が必要。
- 元本家のクライアント/サーバーBAN判定を解除したり不正SAVEを再接続したりしない。危険なネット接続が残る元ゲームを「完全オフライン」と言わない。
- ユーザーの秘密鍵、SAVE、所有済み画像/音声/packをGitHubへコミットしない。上書きZIPとUSB作業は完成を立証する段階でのみ。
- 具体的な技術的失敗が出たら`BLOCKED`と証拠、進められる別機能を記録する。**「別の簡易にゃんこ風ゲームを配ればよい」は解決ではない**。

## 一つの作業セッションの終了条件

直前の実装タスクについて、`現状→変更箇所→実行した検証と出力→未達・障害→次に書く1個のコード差分`をそのタスクのIssueに書く。次のAIはこの CURRENT.md と**そのIssue**だけで再開する。新しい原則ノート・チェックリスト・新しい計画を増やさない。

**このCURRENT.md自身を変える場合は、オーナーの新指示と、その理由を同じPR/Issueに紐づける。**
