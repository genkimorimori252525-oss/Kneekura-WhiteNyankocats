---
current_task: "OPS-BATCH-001"
active_agent: "Codex"
branch: "codex/pc-local-lab-2026-10-12"
commit_head: "73e17cb21e6cbeeedf1b0c67835193344290f99a"
status: "IN_PROGRESS"
evidence_ref: "docs/research/2026-10-23-native-stage-policy.md"
updated_at: "2026-10-23T08:25:41.424123+00:00"

---

# Current Progress State

## 2026-10-23：原作開催区分へ修正、4000個一度配布、受渡し準備

- ネコビタン入口が17:18に出ないとの本人報告：r14署名済み候補の全47対象が一律毎日0〜8時であることが直接原因。境界・native射影2 tests `93653795` PASS。ただし原作全対象への同一時刻適用の正当性は未確定。狂乱・大狂乱のB系原本あり、Game8には狂乱一度挑戦後に常設・A2個でいつでも挑めるとの説明あり。全対象0〜8時が原作仕様とする説明を訂正。常設再挑戦枠／時間指定資源枠の分離が修正案、全対象分類・実装修正は未実施として[調査履歴](../research/2026-10-23-native-stage-policy.md#同日1718にネコビタン入口が出ないとの報告)に保持。コード・予定・APK・スマホは今回変更なし。
- 本人目視：4000個受取成功。初回の未配布報告を「ログインボーナスの後もういっかい開きなおしたらもらえた」と訂正。開き直しの内部原因は未特定、追加調査／修正は終了。他の運営機能の全受入やスマホの重複受取試験まで成功扱いにしない。[本人確認記録](../research/2026-10-23-native-stage-policy.md#同日本人による4000個の受取確認)。
- 所有者が全件照合・経験値追加・ネコフラワー特殊開催・4000個配布・データ保持更新を承認し、さらに「原作の区分を優先し、自由交代20枠は廃止する」と指定。[承認](AMENDMENTS/2026-10-23-native-stage-policy.md)。旧20件指定より優先。週4・月2、ガチャ構成は維持。
- revision14：EX月例、フラワー2/22 14:22〜14:24、神判20〜21、狂乱もねこ28、記念日22等を分離。経験値5種に毎日9/15/21時の各1時間をローカル追加。[開催表](../operations/2026-10-23-native-stage-policy.md)。原作解放・消費・回数保持。191 unique maps、136 bindings、最終48 tests PASS `c69c6588`。
- [全件台帳](../operations/2026-10-23-stage-policy-audit.json)：開催可能1096件、元マップ定義1278件。公開索引988一致／108直接未一致。全条件解明／全攻略は未達。極悪9現行日程・狂乱祭の各日対象はUNKNOWNとして残す。
- r13 PC実UIでネコカン10000→14000、原作MySale受取済み・再起動後重複なし。フラワー未クリア拒否／クリア済み有効表示／2分後終了拒否まで。開催中の入場・戦闘はNOT_RUN。時刻巻戻りでPCにHGT02を出した経緯も保持し、保護コードは変更しない。原PC SAVEはSHA一致復元、時計復帰、停止。詳細は[技術台帳](../research/2026-10-23-native-stage-policy.md)。
- 最終PC build `20261022T213246Z-9570d5f3` はr13とのnative/DataLocal・item/gacha/login・flower開催行一致、導入済み6SHA・元SAVE・時計・停止を確認。最終実command `78dac9b8` PASS。本人の接続連絡後、スマホ候補 `phone-20261022T213509Z-794bc2d5` を研究版へデータ保持更新。導入前の現行6SHA・署名／候補6SHA、導入後の6SHA・UID/dataDir保持を照合。private `PHONE-OPS-UPDATE.json` と[技術台帳](../research/2026-10-23-native-stage-policy.md#2026-10-23-スマホへのデータ保持更新)に記録。スマホの起動・画面／SAVE・ログ取得なし。次手順は本人の目視結果。旧FAIL／UNKNOWN・Charter承認不足は維持。

## 2026-10-23：ステージカテゴリ拡充、PC確認・更新候補作成済み

- [本人指定](AMENDMENTS/2026-10-23-stage-programme.md)に基づくrevision11。20件／2hは42件を週ごとに組替え、週4・月2に、狂乱／大狂乱／ちび、暴風、降臨、超獣、Catamin等206専用ruleを追加。[開催概要](../operations/2026-10-23-stage-programme.md)と[全時間枠](../operations/2026-autumn-stage-timetable.md)。原作の解放・消費・地図取得／鑑定を維持。今季は11/30 00:00まで。
- 関連33 tests PASS、354 source bindings、6split build。PC実UIでちびトカゲ、Catamin入口／A1消費／戦闘、大狂乱トカゲ一覧／ステージ選択を確認。全報酬・地図取得から鑑定・全条件分岐はNOT_RUN。仮バナー4件除去、過去日fixture FAIL、ADB stdin復元FAILと修正を[原因・証拠](../research/2026-10-23-stage-programme.md)へ保存。
- 最終PC `20261022T195407Z-f01c9867`、スマホ候補 `phone-20261022T201342Z-b7b42258`。PCの元SAVEはSHA一致で復元、PC時刻もホストへ復帰、アプリ停止済み。ガチャ／既存nativeコード変更なし。最終復元・候補作成receipt `583adb4b` PASS。
- スマホは前回r9のまま。次手順は本人への開催表説明と、本人の更新指示に応じたデータ保持更新。スマホ目視は本人、追加操作・ログ／SAVE取得なし。旧FAIL／UNKNOWN・Charter承認不足を維持。Hooks OFF、原本・SAVE・鍵はprivate。

## 2026-10-20：季節・曜日の運営修正とスマホ更新済み

- 最新PC `20261020T131246Z-cca69482`、スマホ `phone-20261020T131439Z-86d1bb23`。署名・導入後6SHA・UID/dataDir保持で更新成功。完全反転＋指定キャラ写真も含む。スマホの起動・画面／ログ／SAVE取得なし、本人目視待ち。
- revision9は通常シリーズ11種を3時間交代2枠、季節／オールスター／低頻度コラボを週間1枠。常設通常2枠は維持。20一般交代＋週間4＋月間2に、曜日・時刻／月日指定の82rulesを追加。Halloween／運動会→11月勤労感謝／文化祭。予定は11/30 00:00まで。Luna調査、公式2026予定の複製ではない。
- 関連25 tests、197 bindings compile、6split build、PC10秒capture PASS。初回test fixture FAILと特別ticket候補拒否は修正前履歴として[記録](../research/2026-10-20-seasonal-liveops.md)。ログインrotationはv7と一致、初期MAX再適用なし。旧FAIL／UNKNOWN・Charter承認不足は維持。
- 次手順は本人の目視結果／次の運営指示。追加スマホ調査を自動実行しない。原作素材・原画・鍵・SAVE・rawログはprivate。

## 2026-10-20：所有者指定のキャラ写真

- No.703第1形態の出撃・育成・入手用PNG3点を、指定原画から原作寸法・枠を保持して変換。private原画＋公開ハッシュ／変換コード。元の戦闘rig・CSV9点はv5とbyte一致。詳細は[画像差し替え記録](../research/2026-10-20-godzilla-portrait.md)。
- 関連24 tests、6 split build・導入SHA照合PASS。PC原作編成画面で出撃アイコン確認。育成・入手PNGは画像確認＋枠外画素一致、両実画面はNOT_RUN。PC一時SAVEは元bytesへ復元、停止済み。
- 最新PC `20261020T123613Z-556bd0a8`、最新スマホ候補 `phone-20261020T124348Z-e45a2eb7`。スマホ導入・本人確認待ち。前回の完全反転＋味方config修正を含む。追加のスマホ操作・ログ・SAVE取得なし。過去FAIL／UNKNOWNとCharter外部承認不足は保持。

## 2026-10-20：シンゴジラの完全反転・味方用座標設定

- 最初の横倍率だけの修正は本人の画面でFAIL。旧版の姿勢をPCでも再現。最新要求は[実描画確認を含む受入条件](AMENDMENTS/2026-10-20-godzilla-visual-verification.md)。初回21 tests／build PASSを見た目の合格に読み替えない。
- 初期角度と4動作の回転trackも反転。609フレーム・375,144頂点の左右対称誤差0。元画像・frame／easing・移動・能力値を保持。PC実戦で別途発見したconfig1件→味方が要求する2件への不足も修正。中間版native crashのFAILは保持。
- 関連23 tests PASS、build `20261020T082803Z-c0206218`、phone候補 `phone-20261020T083338Z-b8c65002`。原作PCで敵と味方の同時描画、左向き歩行・対向する攻撃・完全勝利まで確認。36観測／約158秒で追加native crashなし。元のPC SAVEはSHA一致で復元。スマホは初回版のまま（USB端末なし）。詳細は[原因・検証記録](../research/2026-10-20-godzilla-complete-reflection.md)。

## 初回の味方向き候補（本人のFAIL受領、上記で修正中）

- 本人の最小修正・最小検証指定。`702_f.mamodel` root Xだけ `1790 → -1790`、他8 payload同一。converter・pin・cache版・既存回帰を更新。関連21 tests／6split build PASS。
- PC build `20261019T184640Z-35b3aee8`、phone候補 `phone-20261019T184729Z-525a825b` 作成済み。本人のUSB再接続後、同署名・全6SHA一致・UID/dataDir保持でスマホ更新成功。起動・画面・ログ・SAVE取得は行わず、実描画は本人確認待ち。詳細は[不具合台帳](../research/failure-repair-history.md#2026-10-20--味方シンゴジラの表示方向)。SAVE・運営予定に変更なし。

## OPS-BATCH-001：レア3枠・通常常設2枠、スマホ更新済み／本人確認待ち

- 最新人間指定は[ガチャ追加](AMENDMENTS/2026-10-15-gacha-rotation.md)。レア3時間交代2＋週特選1、にゃんこガチャ通常＋マタタビ入り常設2。通常の黄色字幕・期限表示なし。前のステージ20／2h＋週4／月2は維持。AIはPC確認、スマホ目視は本人。Hooks OFF、自作ステージ・初期MAX再適用・公式アプリ操作なし。
- 現行pack `ops/seasons/2026-autumn-liveops.json` revision7、選定原本 `2026-autumn-gacha-selection.json`。source照合118 bindings、private bundle SHA `2f088c496d84ba15c537516faa4dd8987533ff6fca3f3bb3a4c77414fee86f02`。通常N0/N3はticket20・元抽選／保存。レア・stageは11/15まで、常設通常の長期期間と区別する。
- PC build `20261014T181055Z-4b304f94`、capture `20261014T181438Z-db518317`。Java/Dex/NDK/署名6split/static PASS、関連27＋timezone回帰1 PASS。実UIレア3・通常2、通常字幕／期限なし。マタタビ入り1抽選XP5000、ticket2998→2997、rare299・catfood45010・元貯蔵庫保持。全候補／全機能合格ではない。
- revision6では週特選だけ表示／通常無効のFAIL。AVDのGMTとJST予定不一致を同一候補のJST冷起動で切分け。専用AVDは現在Asia/Tokyo、ホスト／スマホ時計は未変更。今後ops captureはJST以外なら端末変更前停止。週特選内容は週内維持、残り時間は同一行の3時間区間表示という限界を記録。
- phone `phone-20261014T181623Z-daa89a6f` を既存署名・Android -rで更新済み。初回USB offlineで導入前停止後、本人の「接続した」を受けて再実行成功。実署名一致・全6SHA一致・UID/dataDir保持。スマホ起動／UI／ログ／SAVE取得なし。本人確認待ち。machine receipt `OPS-BATCH-001_0f43d377955a4e3e93f1208b98d4b0e4.json`。
- 既存HGT00のFAILは保持：phone完全hookをPC JNI専用readinessが拒否→item503。共通GL readiness（full hook1／PC JNI2、元描画帰還・隔離・source・同一GL TID）へ最小修正済み。ARM64関連4件とPC通常refetch PASS。今回限定の既存スマホログ許可を一般化しない。
- 未解決／未実施を保持：月次残り29日UNKNOWN、未準備基本ネコbattle敗北FAIL（stamina40／Nekobon1消費、未補充）、全SDK／IPC egress、全イベント報酬、時計後退／gapはNOT_RUN。旧58件3FAIL・START barrier FAIL・cache literal名FAILの原証拠も履歴に保持。追加の全面プレイ検証へ広げない。
- 次手順：本人の目視結果・次の運営指示に従う。追加のスマホ調査を開始しない。公開Gitはコード・予定・台帳のみ。private/work/assets/raw/AGENTS.md.bakは追加しない。
- 公開後の初回CIは旧backup試験のguard期待値／JVM原作stub不足で2fail。テストのみ追随し、503/error・元super送信0とgetTimeのHDFを含む関連10件をJDK17でPASS。導入済みAPK変更なし。CI全体はGitHub Actionsのcode commitで確認し、初回FAILを履歴に保持。

詳細と原証拠：[運営履歴](../research/2026-10-14-original-liveops-batch1.md)、[EVIDENCE_INDEX](EVIDENCE_INDEX.md)、過去HANDOFFSを参照。Charter承認receipt不足を自己承認で埋めない。
