---
current_task: "EXTRA-STAGES-001"
active_agent: "Codex"
branch: "codex/pc-local-lab-2026-10-12"
commit_head: "2be9807c3e130ee73e17083d32ffd9c0ffa36d30"
status: "OWNER_VISUAL_PENDING"
evidence_ref: "docs/research/2026-11-11-extra-stage-rotation.md"
updated_at: "2026-11-11T09:34:30.400221+00:00"

---

# Current Progress State

## 2026-11-14：ユニット調整（スマホ更新済み／本人確認待ち）

- 本人指定でディオラムス第4形態・ガメレオン第3形態の超打たれ強い、第4形態の価格・再生産、まどか波動Lv5と進化前同性能、ほむら射程圏外縮小・確定妨害と進化前同性能、ガメレオン第3形態を+1,000円。画像差し替えは取りやめ。PCビルド `20261113T173007Z-b6dc32ac`（再生産2倍・まどか波動Lv5・狂乱のネコ親分・ジャラミ爆破50%。爆破・波動が出ない不具合を修正。スマホ更新済み＝候補 `phone-20261113T173426Z-8c4cad04`、データ保持）・導入起動45秒・関連テスト成功。実戦の数値・画像のゲーム内表示・スマホは未検証。同時召喚は所有者が中止。ディオラムス第4形態は価格7,600円（2章基準）・再生産と妨害率は元のまま。詳細は[記録](../updates/2026-11-14-unit-tuning.md)。スマホ更新済み（最終候補 `phone-20261113T160356Z-efa53b7e`、データ保持）。専用AVDは停止済み。

## 2026-11-11：追加イベントと週替わりコラボ

- 本人指定で毎時最大10件、コラボ全現行マップは週替わり別枠。原作の解放・報酬は保持。予定・旧方針との差は[運営予定](../operations/2026-11-11-extra-stage-schedule.md)／[変更指示](AMENDMENTS/2026-11-11-extra-stages.md)。
- r20の456時間生成・旧開催維持・時間境界テスト・６分割build PASS。PC旧版から同日更新し、コラボ５件・追加開催・日別お知らせの表示を確認。PC原データ551ファイル復元SHA一致。詳細とFAIL/UNKNOWNは[記録](../research/2026-11-11-extra-stage-rotation.md)。
- 本人の更新依頼・USB接続を受けて候補 `phone-20261111T081315Z-79dde32a` をデータ保持更新。旧APKと署名、導入後６分割SHA、UID・データ保存先を照合 `095439766f684857a960cf47032b3fde` PASS。SAVEの読取・書換えやスマホの起動／画面確認は行っていない。
- 現在一件：`OWNER_VISUAL_PENDING`。スマホ画面は本人が確認。全攻略・全自動時刻跨ぎ画面更新は未検証。配信期間11/30 0時まで。旧FAIL・UNKNOWN・Charter承認receipt不足を保持。

## 2026-11-10：お詫び画面が出ないため直接反映

- 本人は画面が出ないと報告。最新SAVEで20261110が未受取と確認、原SAVEのSHA一致バックアップ後、ネコカン40000と原作受取済み記録のみを原子的に反映。関連SAVEの全semantic差分、再読取、二重適用拒否 `c50b7340` と実機の反映後SHA `ac27dd73` PASS。APK再インストールなし、スマホの起動／画面検証は本人担当。`OWNER_VISUAL_PENDING`。
- 全ファイルの転送が途中停止したため部分tarを保管し、SAVE単体をSHA照合して退避。全ファイル完全バックアップは未取得。画面が出ない内部原因はUNKNOWN。[詳細](../research/2026-11-10-login-legend-repair.md#同日お詫び画面が出ないとの本人報告)。

## 2026-11-10：ログイン修正・レジェンド報酬・お詫び

- 本人報告：15.7.4更新後から毎日ログインボーナスが出ず、クリア済み報酬キャラがない。ログイン生成行が旧filter150701のままだったため、新版profile150704を反映。前回はクリアのみ付与して報酬キャラは除外したことが直接原因。対象ステージがクリア済みのウルルン・コニャンダム・ミーニャを補填し、XPは本人選択の原作上限99,999,999・NP9999、ネコカン40000は原作の一度限り配布。11/30 0時まで受取可能。
- PCでログイン／ネコカン+40000の実UI、3体・NP・XP、再起動保持／重複配布なし、元PC全ファイル復元を確認（`b5c9db74` / `408b6e8c`）。新版6split build成功。
- スマホ更新完了：本人の再接続・更新依頼で、最新599ファイルをバックアップ→最新SAVEから3体とNP・XPの補填候補を作成→既存署名で更新。6SHA・UID/dataDir、指定SAVE以外のファイル全件SHA一致（`6eb7c798` / `6bed25f5`）。公式SAVE・スマホ画面／ログ取得なし。`OWNER_VISUAL_PENDING`：本人の目視結果を待つ。
- 詳細・受取期間・PC導入失敗と修正は[調査記録](../research/2026-11-10-login-legend-repair.md)。過去のFAIL/UNKNOWN・Charter承認receipt不足は解決扱いにしない。

## 2026-11-03：公式15.7.4取り込み・恐ろし連邦までの進行指定

- 完了証拠：前回r15は[本人確認済み](../research/2026-10-23-catamin-all-day.md)。再ビルド・再試験・再導入しない。
- 2026-11-04取得済み：公式15.7.4/1507040の6APK・旧原本と署名一致、研究版停止後の私的全バックアップ／SAVE SHA一致 `29a05137`。公式SAVE／研究SAVE書込みなし。王冠1の231実ステージ候補は9 tests `7594fc56`＋実SAVE全semantic保持／再読込 `6101e11f` PASS、スマホ未反映。
- 完了証拠追加：旧版既定を保持した新版native/C/Python profile、37 anchors／data roots／12field群と旧新版の全text復元gateを照合。統合52 tests `a06da387`、15.7.4の6split build `20261103T154350Z-174caa2e`（`29b3194a`）PASS。[版対応・個別receipt・ビルド根拠](../research/2026-11-04-jp1574-native-port.md)。
- PC runtime：setup `469eeb13`、全バックアップ／6split導入／進行候補 `11a2eb6e`、初回capture `b5514d5c` 完了。native起動・運営ステージ・恐ろし連邦の王冠1 CLEAR、王冠2と次章は未クリア表示を確認（私的pc-runtime／resume-ui証拠）。実engine保存version150704対応のhost guardを追加、11 tests `cc60eb07` と実SAVE idempotence `63e3ef72` PASS。コードCI b20616cの2系統成功。
- PC受入完了：操作しやすいネコアイスのPC限定fixtureで闇2個→上限60 `b18d18cf`、XP育成→60／超過拒否 `bc8b7822`、再起動保持 `f8944bc9` PASS。レア3／通常2枠も目視。原PC全551ファイルSHA一致復元・時計同期・停止 `e7bcd7ef`。私的原証拠／失敗／UNKNOWNは詳細記録へ。
- スマホ更新完了：本人の「更新してくれ」により、候補 `phone-20261103T170131Z-78601523` を既存署名で導入。更新直前に現579ファイル全私的バックアップ、最新SAVEから進行候補を再生成 `01786da2`。導入後6SHA・UID/dataDir・SAVEと指定差分以外の全579ファイル集合/SHA一致 `0f3447a0` PASS。初期化／PC fixture転送／公式SAVEアクセスなし。
- 現在一件：`OWNER_VISUAL_PENDING`。アプリ停止状態で所有者の目視結果を待つ。AIはスマホ起動・画面／ログ・SAVE取得を追加実行しない。新不具合または本人の新指示がある場合だけ対象を限定して再開する。code ea0e285のTest tooling・Agent terminal Ubuntu/Windows成功。旧FAIL／UNKNOWN／Charter承認receipt不足は解決扱いにしない。

## 2026-10-23：ネコビタン47件24時間、スマホのデータ保持更新済み

- 更新後のスマホ動作は本人から成功報告を受領し `OWNER_CONFIRMED`。全47件攻略・全条件分岐の確認へ一般化しない。追加検証・端末操作なし。次は本人の運営指示。
- 最新直接指定は[全47件の24時間化](AMENDMENTS/2026-10-23-catamin-original-policy.md)。r15で14005〜14051を毎日0〜翌0時へ変更し、compilerで日次の開催行を保持。原作の解放・消費・回数と旧5件除外は維持。24時間化は所有者指定のローカル方針で、原作JP全件の時刻UNKNOWNは保持。
- [技術記録](../research/2026-10-23-catamin-all-day.md)：関連49＋PC module15 tests、compile・6split build・JST起動ログPASS。専用PC夕方出撃/A1消費、離脱でクリア数不変、当日3クリアfixtureの非表示、翌日3→0・再表示を確認。日次行結合RED、実metadata階層誤りによるJST検査漏れRED、warmup未知画面停止も保存。専用AVDは自動時差OFF・手動JST。
- PC `20261023T091149Z-7ee8fe90`、候補 `phone-20261023T093506Z-c6a29a1b`。最終PC検証 `45e1e023` PASS：候補bundle・47件×38日行、r14 native/DataLocal・他開催/gacha/gift/login保持、導入6SHA、元SAVE SHA復元・時計復帰・停止、候補6SHAと署名。
- 本人の明示依頼後、CIで画像変換用Pillowの不要なtop-level importを検出・変換直前へ修正。関連6 tests `53c0fa70`、code commit `efa1c33` のCI全839件（833成功/6 skip）・Agent terminal Ubuntu/Windows成功。APKは不変。同候補をスマホへデータ保持更新し、旧6SHA・実署名／候補6SHA・導入後6SHA／UID/dataDir保持を確認。実receipt `990846c4` PASS。スマホ起動・画面／ログ／SAVE取得なし。次は本人の目視結果・運営指示。追加の端末調査を自動実行しない。
- 期間は従来どおり11/30 0時まで。全47件実攻略・全条件分岐はNOT_RUN。旧FAIL/UNKNOWN・Charter承認receipt不足を保持。下記は各工程時点の履歴で、最新方針・候補は本節を優先する。

## 2026-10-23：原作開催区分へ修正、4000個一度配布、受渡し準備

- 最新指定：原作ならいつでも遊べる扱いに合わせたい、狂乱だけでなくLunaに全対象を調査。[直接指示](AMENDMENTS/2026-10-23-catamin-original-policy.md)。Lunaが[旧5件含む全52定義の表](../research/2026-10-23-catamin-source-audit.md)を作成。現行47件の費用・条件候補と資料間差異を整理したが、JP15.7.1の全対象開催時刻はUNKNOWN。公開JPイベントTSV履歴でも直接証拠なし。予定・コード・APKは未修正、部分先行修正なし。専用PCの事前バックアップと元SAVE SHA不変／アプリ停止を確認、スマホ操作なし。次は対象別開催時刻の根拠を確定してから原作準拠の修正・PC受入。原作条件の貫通や全件24hの無条件承認へ読み替えない。
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
