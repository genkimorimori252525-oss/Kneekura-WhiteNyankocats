# にーくら大戦争 — ローカル運営室 / Jolly LiveOps Charter v1

**計画・運営担当:** Jolly (GitHubで運営データ・コードを作成、レビュー・更新履歴を残す)  
**最終ゲーム環境:** 完全オフライン、KNEEKURA_SAVE_V1が唯一のプレイヤー進行原本。  
**現状:** ソース・ドラフトスケジュール・Python検証エンジンのみ実装。**Androidゲーム本体への接続・公開は未完了**。

この文書は既存の docs/architecture/kneekura-post-eoc-liveops.md の設計を継承し、**2026-10-09以降の「ゼロ外部通信、独立セーブ」方針を上位にする**。旧文書の「オンライン時にGitHubから自動ダウンロード」は端末側の正式な動作として**廃止**。PCで手動取得/編集・検証したデータのみを端末へオフラインインポートする。ゲーム起動時のHTTP問い合わせ、広告SDK、公式ログイン/クラウド保存は不要。

## 1. PONOSの主な運営業務と、にーくらでの引継ぎ

以下は**機能カテゴリ**の比較であって、PONOSの非公開の内部運営手順を知っているという意味ではない。元ゲームの開催予定を模倣したり、古いイベント告知を2026年の開催情報と偽って流用したりしない。

| 本家の公開機能・運営業務 | Kneekura LiveOps担当 | 管理データ / 現段階 |
| --- | --- | --- |
| ガチャバナー、各レアリティ/排出テーブル、確定/限定ガチャ告知 | ガチャ運営 | local pool定義/開催枠/抽選比率/保証規則、**排出処理・実確率は未実装** |
| イベント・コラボ期間、キャンペーン告知 | シーズン運営 | event schedule / season / notice。外部コラボ素材は所有者ローカルに限定 |
| 常設・日替わり・曜日・月次・期間限定ステージ | ステージ運営 | stage map metadata / visible window / prerequisites / first clear ledger (**開催とクリアは別**) |
| ログインボーナス・ログインスタンプ | ログイン担当 | 5つのキャンペーン枠とshuffle-bag循環、次日から補充、ユーザーローカル日付基準、実際の報酬付与は後続実装 |
| メイン・スペシャル・ウィークリー・マンスリーミッション | ミッション担当 | permanents/limited claim rules、weekly=JST月曜0:00更新、monthly=月初0:00更新、実際の条件判定/付与は別エンジン |
| 統率力回復と時刻による要素 | ローカル時刻担当 | Android elapsedRealtimeと保存済みUTC/JST基準、時刻後退はローカル修復であり利用停止ではない |
| 宝物フェス・経験値やドロップ率増加、トレジャー・マタタビ催事 | 育成イベント担当 | modifier schedule、効果対象と倍率上限、実戦ロジックと未接続なら公開不可 |
| ステージ報酬・ログイン配布・キャンペーン報酬・受信箱 | 経済・報酬担当 | local item catalog、grant ledger、idempotent claim、バックアップから復旧可能 |
| 新キャラ/敵/能力・育成上限・バランス修正 | コンテンツ・戦闘担当 | unit/enemy atlas、Versioned balance JSON、正確なLv範囲、回帰テスト |
| お知らせ・予告・開催中表示 | 告知担当 | local notices、JST発行時刻、status draft/published、**プッシュ通知やオンラインニュースなし** |
| ネコ道場・ランキングの間 | ローカル記録担当 | 自分の記録/ベストスコアのみ。外部送信、他プレイヤーとの全国順位、ランキング報酬を偽装しない |
| アップデート配信、不具合修正、データ移行、問い合わせ | リリース/保全担当 | Github履歴、ローカルpackバージョン、変更差分検査、KNEEKURA_SAVE_V1バックアップ/復元、オフラインエラー説明 |
| 広告配信・広告SDK・実課金ショップ・アカウント追跡 | **担当しない** | 完全撤廃。ガチャはローカルのみ、現金課金は一切実装しない |

参考となるPONOS公開情報：
- 日本語公式ヘルプ: https://ponosgames.com/information/appli/battlecats/help/index.html — イベントカレンダー/ガチャ/編成UI。
- にゃんこミッション公式説明: https://ponosgames.com/information/appli/battlecats/mission/index.html — メイン/スペシャル/週次/月次、週月の更新タイミング。
- イベント例（日時別マタタビ・道場）: https://ponosgames.com/information/appli/battlecats/event/20190118.html — あくまで歴史的な開催例。2026年の開催予定ではない。
- にゃんこ大戦争FAQ: https://ponosgames.com/information/appli/battlecats/faq/qa.html — 通信・時刻依存の統率力/イベント問題。

### 追加で扱う生活・成長サブシステム

PONOS公式HELPに基づき、以下も運営の範囲として把握する。ただし現行v1共通カレンダーは7種までなので、未実装機能を公開済みと扱わない。

- **ガマトト探検隊**：探検エリア・所要時間・探索報酬・ネコビタン短縮・隊員/EXP・期間限定探検先。Jollyのローカル探検プランとして運営し、将来は local-expedition controller へ。ゲームサーバー時刻不要。
- **通常にゃんこガチャ／レアガチャ／イベントガチャ／プラチナ・レジェンド系**：券種・通貨・ガチャの種類は別々に定義。排出率、確定・天井・11連、XP/NP変換は明示したローカル規則だけを使う。*現金課金・広告視聴による無料ガチャは採用しない*。
- **キャラ貯蔵庫・アイテムショップ・にゃんこ神社**：ローカル経済、アイテムの在庫/交換ルール、神社・経験値交換、装備/進化資源。現金決済を伴わないゲーム内運営として管理。
- **にゃんこメダル、レアステージ・EXステージ、遠征、難易度指定編成の挑戦**：ローカル達成条件と永続勲章。獲得済みフラグは公開データとは別のセーブ領域。
- **ネコ道場・ランキングの間**：スコアチャレンジ自体はローカルで可能。ただし全国順位、他人の記録、通信ランキング報酬は完全独立版では提供しない。
- **にゃんこクラブのオンライン会員/商品・課金アイテム販売、SNS特典、他ゲーム連動報酬**：依存する外部認証や金銭決済は対象外。必要なゲーム内利便性のみ、誰でも使える設定へ分離する。

根拠の範囲：PONOS公開ゲームガイド https://ponosgames.com/information/appli/battlecats/help/index.html 。これはPONOSの運営組織やバックエンドを逆算した資料ではなく、ゲーム中で提供されている機能の棚卸しである。

## 2. 既存の重要な設計を維持

**Post-EoCコンテンツ方針（2026-10-07設計）**
- 日本編1〜3章を完了、最高のお宝、レジェンド等は未クリアから遊ぶ、というゲーム初期状態を将来の**独立KNEEKURA_SAVE_V1**へ投影する。拒否された元のSAVE_DATAを復元・利用するわけではない。
- ガチャ/collabの開始所持は独立プロフィールの選択事項。ステージ報酬キャラは実クリアで獲得。資源MAXはローカルの難易度オプションとして提供可能。
- 限定ステージの**開催/表示/挑戦可能**は、そのステージの**クリア回数/報酬受取/所持キャラ**を変更してはならない。
- ログインは最大5キャンペーン枠、データbag内で循環。キャンペーンの終了で1枠だけ再抽選、追加分は次のローカル日まで受取不可。時計の後退で同日重複受取はしないが永久ペナルティやBANをしない。

**新しい最優先条件**
- オフラインの元データ・運営データ・セーブ状態の3つは別々に保存。
- アプリはINTERNET権限、公式サービス、第三者SDKへ依存しない。
- GitHubはJollyの**制作/履歴管理**用。端末はGitHubへ接続しない。更新パックをPC/USB/ローカルファイル取り込みで渡す。
- 既存オフライン時刻モジュールはPC/Pythonで検証する参考実装。Android実装では同一起動中の時間経過に単調時計を使用し、再起動後の壁時計との差分規則を別途検証する。

## 3. Jolly Operation Pack v1

GitHub:
- スケジュール原本: ops/seasons/2026-autumn-prototype.json（**下書き**。実際にPONOSが開催するイベントでもプレイ可能なゲームデータでもない）
- 時刻解決/公開可能性チェック: tools/localcore/ops_calendar.py
- CLI: tools/localcore/opsctl.py
- 5枠スタンプ循環: tools/localcore/login_rotation.py

### 構造

- pack: channel、revision、season、status(draft/published)、JST timezone、ゼロ通信ポリシー
- catalog: gacha / stage / event / login / mission / notice / modifier の7カテゴリー。内容にはstable id、title、source:kneekura-local、**ready:真偽**を必須とする。
- schedule: id、content_id、kind、slot、priority、rule(once/daily/weekly/monthly)、ローカル攻略前提条件
- recurring weekdays: 0=月〜6=日、monthdays:1〜31、開始/終了は[JST start, JST end)で重複しない。深夜越えを許容。
- 同じ種類の同じ表示枠に同優先度の開催が重なったらCIエラー。異なる優先度なら高いほうを選ぶ。
- **ready=false**の素材未作成・未検証企画はカレンダー候補には残るが**公開/プレイ対象にはならない**。
- pack.status=draftでは準備済みコンテンツもpreviewにしか載せない。公開版として扱うには別途資産/Android/ローカルセーブ連動の実機ゲートが必要。
- gacha抽選処理、stage battle、mission payout、ログイン報酬反映は**別の機能**。時刻の管理がそのまま報酬やクリア履歴を書き込むことはない。
- content-addressed digestは更新内容が変わったか判定するもので、暗号署名や信頼済みリリースの証明ではない。

### 現時点で使える静的コマンド（PC）

リポジトリルート、Python3.12+。通信しない。何もデバイスに書き込まない。

~~~powershell
python -m tools.localcore.opsctl validate --pack ops/seasons/2026-autumn-prototype.json
python -m tools.localcore.opsctl preview --pack ops/seasons/2026-autumn-prototype.json --at 2026-10-09T19:00:00+09:00
python -m tools.localcore.opsctl calendar --pack ops/seasons/2026-autumn-prototype.json --from-date 2026-10-09 --days 14
~~~

※ この段階のcalendarは静的に検証する**予定表データ**。アプリで実際にガチャ・ステージを開催する機能ではない。

## 4. 運営の仕事の流れ

| 担当業務 | Jollyが行うもの | 公開ブロッカー |
| --- | --- | --- |
| 企画 | 日本時間で週/月/シーズンの内容と優先度を作成、マップ/キャラ素材と照合 | ローカル素材の不足、未承認の排出確率/報酬 |
| 設計 | stable ID、開催日時、必要進行、表示枠、reward_intentを定義 | ID重複、時刻重複、ストーリーの偽クリア |
| 検証 | 14〜90日展開、境界時刻、優先度、5枠、一日一回報酬、ゼロ通信CI | asset/game ready=false、イベントが表示だけになってしまう |
| 承認 | ゲーム挙動・バランス・特殊なコラボ用途を記録して変更履歴確定 | 実際のエンジンに接続できない状態 |
| リリース | GitHubで更新パックとSHA、回帰結果を保存。端末には所有者がオフライン取り込み | 元のデータ更新によるプレイヤー進行喪失、Androidゼロ通信未検証 |
| 運営継続 | 次版JSONを追加、過去の内容をアーカイブ、旧版へ巻戻し | 開催時刻/ログイン報酬の重複、キャラ所持履歴の再設定 |

### 月次の標準管理カレンダー（提案・正式ゲーム未適用）

- **毎日0:00 JST** ローカルログイン日判定・日替わり開催窓の切替。
- **毎週月曜0:00 JST** 週次ミッションの期間切替、週替わりステージの可用性検査。
- **毎月1日0:00 JST** 月次ミッションの期間切替と季節パック互換性検査。
- **企画ごとの指定日時** レアガチャ/イベント開始・終了、曜日ステージや期間限定モディファイア。
- **パック更新時のみ** 端末への手動オフラインインポート。自動ネットワーク通信・オンラインサービス照会はなし。

これらは現地JSTの設計時刻であり、PONOSの今日/今週の実際の開催予定の転載ではない。

## 5. 未実装と完成判定

初期段階で元PONOSの素材・確率・開催スケジュールを端末から直接同期しない。本人が所有する元素材を一度取り込み、Kneekura運営は独自の内容・時間を発行する。

次に必要な開発:
1. KNEEKURA_SAVE_V1に安定したstage clear ledger / once-per-reward grant ledger / ミッション週月状態を追加。とくに同一キャンペーンの再開催で報酬が二重付与されない設計。
2. stage enemy/wave/animation importをコンテンツAtlasで検証し、catalog.readyを真にできる証拠を用意する。未確認の原作イベントを「プレイ可能」とは表示しない。
3. gacha unit pools/weight/rarity/保証抽選をローカルで実装し、抽選報酬はKNEEKURA_SAVEへアトミック反映。リアルマネー決済を実装しない。
4. Android側のカレンダー/ガチャ/イベント画面へローカルproviderを接続。INTERNET権限無しで初回起動から正常表示・保存・再起動できることを確認。
5. Jolly運営用の公開ワークフローを専用CLIに拡充: draft→QA→承認→checksum署名→USBインポート→前版と比較→ロールバック。すべて接続不要・ローカル。
6. 以前のpost-eoc-liveops.mdのオンラインGitHubダウンロード構想は研究・制作PC側へ移し、完成版アプリには実装しない。

**最重要な誠実性:** Python CIが通っても、独立Androidに予定が表示・戦闘/ガチャが起きた証明にはならない。現段階のrelease statusは **DRAFT / NOT PLAYABLE**。
