---
current_task: "OPS-BATCH-001"
status: "IN_PROGRESS"
branch: "codex/pc-local-lab-2026-10-12"
commit_head: "b2d9daeb56986e540553157879e55edad8b749d1"
updated_at: "2026-10-14"
purpose: "別AIへの実装引き継ぎ。承認済みの運営バッチを継続する"
---

# 運営バッチ1 引き継ぎ

この文書は、別のAIがこのプロジェクトを引き継ぎ、既存の承認を根拠に実装を開始できるよう、目的、制約、作業ツリー、設計、検証状況、未解決事項をまとめたものです。**実装は未完了です。APK候補、原作UI受入、スマホ受入はまだありません。**

## 1. まず読むもの

作業を始める前に、次の順で確認してください。

1. リポジトリの `AGENTS.md`（作業規則）
2. `docs/ai-continuity/PROJECT_CHARTER.md`、`REQUIREMENTS.md`、`CURRENT.md`、`EVIDENCE_INDEX.md`
3. `docs/ai-continuity/DECISIONS/2026-10-13-ops-batch1-approved.md`（所有者の承認記録）
4. `docs/roadmap/2026-10-09-original-battle-cats-delivery.md` の「運営バッチ1」節と既存運営計画
5. この文書に列挙したソースとテスト

現在の継続タスクは `OPS-BATCH-001`、状態は `IN_PROGRESS` です。CCG（Continuity Guard）の `restore --brief` でチャーターを復元し、変更や中断時は既存の作業記録を保ってcheckpointを更新してください。Hooksは有効化しないでください。

## 2. 所有者の目的と承認範囲

所有者は、一括実装・一括検証・一括修正を希望しています。運営バッチ1では、PONOSの公式運営ではなく、所有者専用のローカルゲームを既存の原作画面で運営することが目的です。承認の根拠は所有者の「うん。やってくれ」と `DECISIONS/2026-10-13-ops-batch1-approved.md` です。別途、今回の引き継ぎ文書作成も依頼されています。

今回の一括対象は次のとおりです。

- レアガチャの開催予定と原作ガチャ画面への接続
- 既存の原作ステージ／イベントの開催予定と選択・挑戦可能性
- 原作のログイン5枠、日付更新、翌日補充
- 基地右上の「i」お知らせ
- 既存計画にある週・月ミッションと運営期間表示
- 同じビルドで上記をまとめてPC検証し、失敗をまとめて修正

自作ステージ、ステージエディタ、別エンジンの運営画面は今回の対象外です。開催を有効にすることとステージクリア／報酬受け取りは別です。クリア済み状態、キャラクター所持、報酬を捏造しないでください。

### 恒久制約

- **AIの動作検証はPC内で行う。** スマホへ渡した後の画面・ゲーム動作は所有者が目視確認する。AIはADB経由でスマホを起動・操作・撮影・ログ採取したり、スマホのSAVEを読む／更新したりしない。このプロジェクトの従来のスマホ試験許可は、今回の恒久指示で置き換わっている。
- 所有者が現在遊んでいるスマホの進行、育成、消費済みデータを保持する。初期MAX、初期所持、初期お宝等の初回プロファイル処理をアップデートで再適用しない。
- 元の原作UI、抽選、獲得、戦闘、クリア報酬、保存経路を可能な限りそのまま使う。変更は必要最小限にする。
- 元のアプリ／アカウント、PONOSサービス、公式SAVE、外部通信に依存しないローカル動作を維持する。公式アプリ `jp.co.ponos.battlecats` は対象外。研究版のpackageは `jp.kn.local.battlecats`。
- 原作素材の存在を確認できないものを開催可能と扱わない。所有者独自の予定を公式PONOS予定と表現しない。
- 既存のユーザー承認をもう一度求めない。端末の消去、データ初期化、秘密鍵の変更・読出し、git状態の破棄、不要な外部公開など、本指示で承認されていない不可逆操作をしない。

## 3. 作業場所と作業ツリー

現行の隔離linked worktreeを再利用します。新しいworktreeを作ったり、primary checkoutへ差分を移したりしないでください。

- 作業リポジトリ: `C:\Users\genki\Documents\Codex\2026-10-12\615mb-393-2-http-0-97\work\kneekura-pc-lab`
- branch: `codex/pc-local-lab-2026-10-12`
- 開始HEAD: `b2d9daeb56986e540553157879e55edad8b749d1`
- 元のprimary checkout: `C:\Users\genki\Downloads\Kneekura-WhiteNyankocats`
- GitHub draft PR #17: <https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/pull/17>
- PR #17の既存タイトルは前段階のものです。必要なら最終実装に合わせて説明を更新します。**mergeは承認されていません。**

開始時の作業ツリーには、本タスク用の追跡ファイル変更・新規ファイルに加えて、保護対象の未追跡 `AGENTS.md.bak` がありました。これは削除せず、stageにも含めず、内容を不用意に表示・公開しないでください。開始時の状態を `git status --short` で照合してから作業してください。`CURRENT.md` や `EVIDENCE_INDEX.md` にすでにある未コミット変更も消さないでください。

### ローカル開発環境

- Android SDK: `C:\Users\genki\AppData\Local\Android\Sdk`
- Java 17: `C:\Program Files\Java\jdk-17`
- Ghidra用Java 21: `C:\Program Files\Android\Android Studio\jbr`
- NDK: `27.2.12479018`
- CMake: `3.22.1`
- Android Build Tools: `35`
- API: `35`
- Python: `py -3.12`（Crypto/LIEFあり）
- ARM64/Unicornテスト環境: `state\runtime\native-test-venv\Scripts\python.exe`
- PC AVD: `kneekura-pc-api35`。前回のserialは `emulator-5580`。実行前に `tools/pc_lab.py` のidentity/対象確認を使い、別端末へ誤接続しないこと。
- owner-only元データ／検証済み原作server cache: primary checkoutの `private\pc-lab` と `private\original-jp1571-verified-server-cache`。原作の未加工データ、SAVE、APK、ログ、秘密鍵は公開リポジトリへ追加しない。

環境上の補足: `context-mode` のPython 3.10にはCryptoがなく、APK保護処理では使えません。CodeGraphはこのrepoのrootに `.codegraph/` がないため利用対象外です。Git autocrlfがLF→CRLF警告を出すことがあります。設定変更で解消しないでください。

## 4. 差分・ファイルの現状

実装途中の新規／変更ソースは主に次です。開始時に実ファイルとdiffを確認し、既存の変更を上書きしないでください。

- Protocol/calendar/bundle/source binding: `tools/liveops/original_schedule.py`、`original_ops_bundle.py`、`original_calendar.py`、`original_catalogue.py`
- 既存owner-mode識別: `tools/localcore/ops_calendar.py`
- Java bridge/runtime: `bridge/java/MyActivity.java.in`、`KneekuraOriginalOps.java.in`、`KneekuraOriginalLogin.java.in`、`KneekuraLoginRotation.java.in`、`KneekuraOriginalNews.java.in`、`KneekuraPcAgeWebView.java.in`
- Native read-only login receipt: `native/kneekura-shim/src/kneekura_original_ops_login.h`、`kneekura_original_scene_witness.c`
- Build/asset pinning: `tools/base_mod/inject_java_http_bridge.py`、`prepare_original_research_presign.py`、`verify_static_http_bridge.py`、`tools/pc_lab.py`
- New contract tests: `tests/test_original_ops_protocol.py`、`test_original_ops_bundle.py`、`test_original_ops_calendar.py`、`test_original_ops_bridge.py`、`test_original_login_runtime.py`
- Existing shared system: `tools/localcore/ops_calendar.py`、`notice_feed.py`、`login_rotation.py`、`offline_update_bundle.py`、`ops/seasons/`

CLIからbundleを安全に作る運営者用コマンドや、最初のソース照合済みseason packはまだ完成していません。APK候補もまだ作っていません。

## 5. 実装済みの技術契約

### 5.1 原作TSVのprotocol

`tools/liveops/original_schedule.py` は、JP 15.7.1原作の `sale.tsv`、`gatya.tsv`、`item.tsv` のwire形式を生成する純粋なPython層です。SAVE・通信・UI操作はしません。

- Game version: `150701`（原作Android versionCode `1507010` を10で割った値）
- schedule時刻はtimezone-aware、JST運用、分単位、開始を含み終了を含まない半開区間。
- 共通ヘッダーは8整数: `[開始日YYYYMMDD, 開始時HHMM, 終了日YYYYMMDD, 終了時HHMM, 150701, 150701, platform=0, filterCount=0]`。
- ガチャは原作type `2`、count `1`、set id、cost、進行値を原作形式で出力し、rarity順の5組（基本、レア、超激、超激/Uber、伝説相当の各chance/guarantee）とmessageを保持する。確率合計は10000、guaranteeは0/1、0確率へのguaranteeは禁止。
- stage行はcountとavailability IDのみ。クリア・報酬を合成しない。
- item行はevent ID、item/template ID、数、title、message、progress、flags、daily/once flag。
- 不正な整数、制御文字、改行注入、重複ID、未対応filter、空／逆転期間をfail closedで拒否する。stream総量は2MiB、bundleは8MiBまで。
- `prepare_login_day` は提案stateを返すだけで、original SAVEやgrantを更新しない。

External protocol cross-checkとして、private source referenceのBCSFE/PackPack実装を読みました。外部実装のコードや依存はAPKに取り込みません。

### 5.2 Immutable bundleとsource binding

`tools/liveops/original_ops_bundle.py` がasset `assets/kneekura-original-ops-v1.json` を生成・検証します。

- Source original ELF SHA-256 pin: `333d2974ab2ff881fd70087fd62dea7d12d82addbc55cab2f2a675ad67e3a7e2`
- bundleはschema/version/owner mode/window/revision/3つのTSVを固定し、重複JSON key、余分なstream、Base64不正、非canonical TSVを拒否。
- `sale.tsv`、`gatya.tsv`、`item.tsv` の正確な3 streamだけを含む。SHAをDex側の期待値とpresign/ZIP検査側の値で照合する。
- 5枠ログインrotationは固定rotation id、適格template pool、各bagがpoolの重複なし置換になることを検証。`build_login_rotation` は既存shuffle-bagに基づき、32 cycleを事前生成可能。
- Noticeはbounded listで、時間窓と文面を検証する。
- assetを追加する関数は元APK entriesを保って `base.apk` に1 assetだけ追加し、receiptにSHAとUI/SAVE未受入を記録する。

**サポート境界:** 現状のencoder/validatorが表現できることだけを「安全に原作接続できる」とみなさないでください。実ソースにないgacha rarity/banner、mission gate、stage prerequisitesは元データとの照合後に扱います。

### 5.3 実データ照合

`tools/liveops/original_catalogue.py` は、owner original export SHA pin（`38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56`）と検証済みserver cacheを照合して、実際にあるmap/gacha/login/mission bindingsを作ります。

最後に実行された照合結果:

- 53,849 asset names
- 1,096 map bindings
- 127 gacha minimum-roster bindings
- 57 通常ログインのitem-only template候補
- weekly mission `8000`、monthly mission `17000` のsource定義を確認
- `S000`/`S006`/`C002` の例としてmap IDs `1000`/`1006`/`2002` はsource bindingあり。`4002` は現catalogueでbindingなしなので使わない。
- Rare gacha set `49` のR1に最低限 `[236,235,234,233,232]` があり、rarity 2/3/4とticket `21` を確認。R2/R3は別poolではなく、**同じ行を後段で拡張**する。現在のcatalogueはR1最低限だけなので「全排出poolを検証済み」と言わない。原作のR2/R3抽選とeligibilityを変更しない。
- login candidate poolは通常item-onlyのみ。system/comeback用の900/901/902系列やstage-earned rewardは含めない。template文面・背景assetが実在することも必要。
- map category/file-family mappingは実際のsourceから確認済み（例: category 1=`S`, 2=`C`; category 11=`R`はUL側）。ステージ名は`resLocal`にあり、`DataLocal`のmapデータと混同しない。

source catalogueは素材存在の証拠であり、ゲーム内の選択・描画・戦闘の受入証拠ではありません。private cacheの各server fileは元owner manifestのsize+MD5照合済みですが、358 memberは393取り込み全数と同じ概念ではありません。数を混同しないでください。

### 5.4 Calendar compiler

`tools/liveops/original_calendar.py` は既存calendarを原作のimmutable bundleへ投影します。

- packのstatusは現在 `published` を要求し、source bindingのないentry、未対応の追加動的`requires` gateをfail closedにする。
- 時間窓とpriority winnerを分割し、同じ連続winnerはmergeする。最大90日をcompile。
- gacha→`gatya.tsv`、stage/event/mission→`sale.tsv`、login→`item.tsv`、notice→notice records。
- source bindingは`bind_catalogue(pack, catalogue)`を使ってowner sourceから作る。呼出側の任意dictを信用してrelease-readyを主張しない。

現状の重大な未完成点: noticeの `published_at` がcalendar windowに反映されていません。preview/draft packのPC candidate扱いも未設計です。`published`を単純に偽装して通したり、予定時刻前にnoticeを出したりしないでください。最初のseasonを追加する場合、原作source照合済みであることとPC候補であることを状態として区別してください。

### 5.5 Java bridge、ローカルHTTP応答、基地i

`MyActivity.java.in` の新ブロックは `ORIGINAL_OPS_BEGIN/END` 内にあり、既定OFFです。選択された研究buildだけで追加classとbundle SHAを注入します。

- 元のrequest registry、request handle、原作GL callback、`newResponse` の6引数形式を使う。
- `allocateDirect` bufferを用い、元のHTTP request URL/queryをログに書かず、networkを呼ばずに応答する。
- Original endpoint: HTTPS host `nyanko-events.ponosgames.com`、path `/battlecats_production/{sale,gatya,item}.tsv`。GET、timeout/headers/body/flagsは実測済みshapeに一致させる。URL queryはopaque扱い。未知host/pathを広く横取りしない。
- Bridgeのlocal operations機能は`local-boot`とbundle SHA pinがある時だけ許可し、original/通常network buildで有効化しない。
- `KneekuraOriginalOps.java.in` はassetのschema/version/window/SHAを検証。notice pageはowner noticeデータだけをHTML escapeして表示し、外部JS/CSS/imageをロードしない。
- Base-i host/pathは `nyanko-announcement.ponosgames.com/v1/notices`。Queryにopaque値が多い。調査で確認したnative helperはURL formatterであり、REST response parserとして扱わない。
- `KneekuraOriginalNews` はoriginal `gViewMap`/`cn1` とcustom clientを保ち、原作の `ponos-api://` delegateだけ許し、他のnavigation/resourceを制限する。元のclose/native UI callbackを残す。
- `prepare_original_research_presign.py` と `verify_static_http_bridge.py` は追加bundleを正確なassetとして許し、SHA一致を確認する。`tools/pc_lab.py` は必要なliveops/localcore sourceをbuild archiveに含める。

**PCで未証明:** 新しいJava classのDexコンパイル、実際の元UIからの3 endpoint request shape（特にgacha/item）、ガチャ画面、ステージ画面、基地iの表示・閉じる動作、mission画面。static source guardは実UI合格の代わりになりません。

### 5.6 ログインのassignmentとoriginal receipt

設計上、元のgame item/templateで原作のログイン報酬を付与し、にーくら側sidecarはslot assignment/offer stateだけ持ちます。HTTPを返しただけでは受取済みとしません。

- `KneekuraLoginRotation.java.in`: 5 active slots、template/event key/observed original count/eligible day/offered day、事前生成shuffle bags。same-day offerは同じkeyを再提示し、時計後退時は新規offerを出さず、日付が飛んでも複数日分を一括grantしない。完了slotのreplacementは翌日から。
- `KneekuraOriginalLogin.java.in`: `kneekura-login-assignments-v1.json`をAndroid `AtomicFile`で保存。5つの原作item rowを動的生成して`item.tsv`へ足す。Native original progress countsだけで受取完了を判定する。SAVE fieldの読み書きはしない。
- 原作runtime `0x62e154`（Ghidra image base `0x100000`を足した表示では`0x72e154`）がtemplate/rewardを処理する。Context `+0x333510`に `std::map<int,int>` があり、node size 40 bytes、key offset +28、count offset +32。要求するにーくらevent keysは700000以上。JNIはsource witness、original GL thread、context rangeを確認し、`process_vm_readv`相当の安全な読み出しだけで値を返す。
- JNI getterは `kneekura_original_scene_witness.c` にあり、原作の既存getter/runtime-load-bias/source-build identity gatesに依存する。勝手な絶対address、node write、grant、SAVE writeはしない。
- 既存server/item loaderはitem template IDs 900–999等または35000以上を受けるが、900 system/comeback flagsは通常ログインslotに使わない。

## 6. 最重要の未解決設計課題

これらは「あとで注意」ではなく、候補を配る前に解決してPCで証拠を取る必要があります。

### A. Original SAVEとsidecarのcrash整合性（最優先）

現在のkernelは元SAVE内のprogress countがsidecarの前回観測値より小さいと拒否します。しかし原作SAVEがまだdiskにflushされる前にprocessが落ちると、正当な再起動でもcountが下がり得ます。また、メモリ上の完了を見てslotを入れ替えた直後にクラッシュすれば、元SAVEには古いslotの未完了状態が残り、assignmentだけ失う可能性があります。現状の「count rollbackでpermanent 503」は長期運用として不可です。

解決はoriginal SAVEを唯一の進行原本のまま保ってください。推奨調査方向は、sidecarにbounded assignment lineage/historyを持ち、再起動時に現slotと直近の旧slot keysのoriginal countsをreadonly照会し、未完了original assignmentを復元することです。key/query総数はboundedにし、元の未完了報酬を見失わず、重複grantしないことをcontract testで示してください。簡易にcountをゼロへ戻す、成功扱いにする、元SAVEを生成／書換える、unknown原作save関数を呼ぶ、古いslotを無条件破棄する実装は禁止です。

### B. JNIのthreadingとearly loading

現状のJava `appendRows()`からnative progress getterを直接呼びますが、そのgetterはoriginal GL threadを要求します。元requestがworker threadで来れば常に503になり得ます。さらに `System.loadLibrary` は元`super.onCreate`の後なので初期通信より遅い可能性があります。

PCで本当のthread/orderを観測し、必要なら安全なhelperを追加します。GL thread外から読む場合は既存GLSurfaceViewへのbounded `queueEvent`＋timeout等で実装し、GL thread自身を待たせないこと。library未bind/observer未readyは速やかに一時unavailableとして返してretry可能にし、JNI `LinkageError`やsidecar例外をprocess crashへ漏らさないこと。thread safetyを満たさず常にGL検査を緩める修正はしないでください。

### C. 壊れたlogin sidecarで全運営機能が止まらないこと

`KneekuraOriginalOps`のconstructorでlogin sidecar不正がops provider全体をunavailableにする可能性があります。login破損はlogin endpointをunavailableにして診断し、gacha/stage/noticesの読み取りを継続できるよう分離します。`LinkageError`、AtomicFile例外、bundle不正の境界を明示し、状態を勝手に消して成功扱いしないでください。

### D. 時計／日次受け取りとの整合

新login/calendarはJSTを想定します。OS timezone、original native daily cutoff、日付巻き戻し・大幅進行、original last-date guard（sourceで48h/時刻差チェックがある）を同一PCで検証してください。Android/JVMとPython compilerのhalf-open boundary、Date header、JST day boundaryが一致する根拠が要ります。時計を飛ばしてstampを付与するテストは禁止し、元engineが拒否した場合はそれを正しく反映します。

### E. Calendar/notices、gacha poolのsource proof

- noticeの `published_at` と優先順位を正しく投影する。
- 追加 `requires` / user-progress gateを無視してはならない。完全な原作gateへのmappingがないなら、そのentryを公開候補にしない。
- Gacha set 49のR2/R3情報やbanner/cost/rare ratesを原作sourceで確認し、R1最小rosterを全排出poolだと誤表示しない。
- stage/eventは確実に存在するsource assetを選ぶ。候補例のmap IDはcatalogueで再照合し、実戦可能性、背景、enemy/waves、schedule gatingを同じPC候補で検査する。
- Mission source IDの存在だけで原作mission selectorへの接続を証明しない。base-i URL formatterだけでnotice bodyの形式を証明したことにしない。

### F. Diagnosticsと候補生成

- `MyActivity.java.in`のOps callback後に、一般boot/backupの「enqueued」診断を出す分岐が残っている可能性があります。Opsのrequest/response/queue診断をboot/backup markerから分離し、ログにURL/query、SAVE、個人値を出さないこと。
- CLIからowner export/cacheを読んでcatalogueをbindし、source-proven season packをcompileし、bundle SHA/receiptを保存するoperator flowが未完成。任意のJSON bindingをrelease-readyにしない。ユーザーが内容を編集してauditできるschedule sourceと、生成物を再現する手順を用意する。
- Bundle asset追加の失敗時一時ZIPのcleanup、既存asset/duplicate/atomic replaceもまとめて検証する。

## 7. 現在の検証証拠と正しい表現

下記は実際に実行された部分結果です。異なるrunを合算して「全tests PASS」と言わないでください。新たな変更が入れば影響範囲を一括再検証し、`EVIDENCE_INDEX.md`を更新します。

- 最初のRED runはimplementation前に新module/CLI optionがないことを確認する意図的FAIL。private logs `work/original-ops-{protocol,bridge,bundle}-red.log`。GREEN前のテスト結果として扱わない。
- Foundation batch: **57 tests、2 ERROR、1 SKIP、54 success**。2 ERRORは新calendar test fixtureのfield名を`type`としたため。実schemaは`mode`で、production compilerのFAILではない。
- Fixture修正後 `tests.test_original_ops_calendar`: **3 tests PASS**。
- `state\runtime\native-test-venv\Scripts\python.exe -m unittest tests.test_original_login_runtime.OriginalLoginArm64Tests`: **2 ARM64 header tests PASS**（Unicorn synthetic tree; original app bytesには触れていない）。
- owner source/cache catalogue read: **PASS**。結果は本書 §5.3。素材一覧の生成はUI受入ではない。
- Java kernelはfoundation run内で動作し、assignment/offer、count証明、時計後退・進行、翌日replacement、copy/reloadなどをテストした。ただしcurrent rollback rejection behaviorは上記§6Aの設計欠陥として要修正。
- native JNI wrapperのNDK build/run、Java全helperのDex compile、同一APKの原作PC UI/実戦シナリオは**NOT_RUN**。
- latest known `git diff --check`: **FAIL**は `docs/ai-continuity/CURRENT.md` の末尾blank lineだけ。未解消なら、その行を確認し文書diffを整えてから再実行する。
- `EVIDENCE_INDEX.md`はまだOPS-RED-001をFAIL、runtimeをNOT_RUNと記録し、GREENを反映していない。実行ログを確認し、実証した範囲だけ更新する。以前のbaseline test suite/CI PASSはこの差分のPASSではない。
- この差分から作ったcandidate APKはまだありません。スマホ更新・スマホでの検証は今回しません。

既知のrun logsはtask rootの `work/` 下にあります（repoの外であり公開対象ではありません）。必要なら存在を確認し、raw private source/SAVE/logsをgitへ追加しないでください。

## 8. 実装を再開する順序

一括方針を維持しつつ、危険な中核不整合を先に解消してください。個々のfeatureごとにAPKや端末受入を繰り返す運用に戻さず、契約が固まった後に一回のbuildと全体PCシナリオへ合流します。

1. `git status --short`と差分を確認、`AGENTS.md.bak`を保護。`CURRENT.md`/CCGを最新の事実に合わせる。
2. Login lineage/restart整合、JNI GL-thread/early-load/LinkageError、login sidecar障害の分離、Ops診断、JST/native receipt、notice publication/priorityの契約をまとめて確定。修正前に関連して読むnative/Java sourceを確認し、現kernel testsを新しいrecoverable semanticsに更新する。
3. Existing owner dataからsource-backed first season/calendarとoperator commandを追加。例えば2026秋の既存曜日・メタル系候補と確認済みevent/gacha/missionを組み、適切なassets/banners/reward templatesを出典付きで固定する。source未確認entryを除外し、dynamic prerequisiteを落とさない。
4. Source catalogue binding→calendar compile→bundle JSON→asset SHA pin→APK buildの全経路を再現可能にする。公開用repoにowner original assetsやcacheは入れない。
5. Related unit/contract checks、Java compile/Dex、native NDK compile、6-split APK static receiptをまとまった1回のvalidation groupで実施し、原因を一括修正して影響checkを再実行する。旧baseline全suiteを理由なく繰り返さない。
6. **一つの同じPC candidate**で、原作画面と元処理を一括受入する: offline初回起動、gacha表示/排出確率/開催期間、stage/event一覧・選択・入場・戦闘、5 login slotsの当日・翌日・same-day restart・cold restart・clock rollback/jump、original progress count/actual awarded stock、base-i表示/close/navigation、weekly/monthly mission selector、SAVE保持・再起動、外部通信なし。観測ログはrequestの役割別に厳密に分類し、URL query/player dataを収集しない。
7. すべての未実施をPASSにせず `EVIDENCE_INDEX.md`とCCG checkpointを更新。`/goal`は本タスクでは新規作成されていないため、勝手に開始／完了扱いしない。
8. 最後にwhole-branch reviewを一度行い、GitHub history/roadmap/PR説明を実装と証拠に合わせて更新。GitHubへpush/PR変更は、所有者のリポジトリ運用指示と現在の認証範囲を確認してから扱う。mergeはしない。
9. スマホへcandidateを渡す場合、所有者が自分で目視検証する。AIは端末操作や結果の代理判定をしない。

## 9. 最初に使う関連コマンド

Windows PowerShellでは作業repoに移動して実行します。

```powershell
git status --short
git diff --check
py -3.12 -m unittest tests.test_original_ops_protocol tests.test_original_ops_bridge tests.test_original_ops_bundle tests.test_original_ops_calendar tests.test_original_login_runtime tests.test_offline_ops_calendar tests.test_static_http_bridge tests.test_prepare_original_research_presign
& state\runtime\native-test-venv\Scripts\python.exe -m unittest tests.test_original_login_runtime.OriginalLoginArm64Tests
```

これは開始時の参考コマンドです。修正後に必要な関連testを選び、run logを残し、実行結果と対象commit/diffを対応させてください。上記一括テストは過去runで2つfixture ERRORが出た後にfixtureが修正されたため、現headで実行していない限りPASSとして引用できません。

## 10. 完了判定

本バッチは、原作UIが同じPC候補で必要な運営機能を実際に使え、original gameplay/save authorityを保ち、外部通信なし、login/restart/時計境界に一貫性があり、静的・native・Java・PC UI証拠が揃った時点で初めてPC検証完了です。素材一覧、unit test、起動ロゴ、HTTP応答だけでは完了になりません。

スマホでの最終受入は所有者が行います。AIが「スマホで正常に動いた」と主張しないでください。
