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

## このファイルの後に読むもの（最大限絞る）

**普段の新規AIセッション：** このファイル → PRODUCT_IDENTITY.md → 実装ロードマップの「実行順序と次の担当者向け開始地点」→ 今動かす1タスクのソース/証拠だけ。毎回すべてのdocs/を巡回する必要はない。

| 作業分野 | 当面追加で読む一次資料だけ |
|---|---|
| レベル上限 | `tools/base_mod/level_cap_unlock.py`、`tests/test_level_cap_unlock.py`、実JP15.7.1 `unitbuy.csv`/元ネイティブ育成接点 |
| まどか | `docs/updates/manifests/update-1.01.json` の `madoka`、`tools/base_mod/prepare_update_manifest.py`、`native/kneekura-shim/src/kneekura_battle101.c`、本家実ダメージ・攻撃/演出接点 |
| シン・ゴジラ移植 | 同1.01 JSONの `godzilla`/source_assets、`tools/base_mod/collect_update_101_server_assets.py`、`kneekura_battle101.c`、所有者privateの `550_e` 元素材/味方 `702_f`。**Server実体回収は [2026-10-10 原本照合付き取得調査](docs/research/2026-10-10-original-server-archive-acquisition.md)**（現状URL応答・原本回収は未検証） |
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
