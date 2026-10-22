# Evidence Index

Only record verification that was actually performed.

| ID | Status | Description | Reference |
|---|---|---|---|

| DOC-OPS-001 | PASS | 2026-10-13: `git diff --check` exit=0、変更計画の相対参照4件が実ファイルへ解決 | `docs/roadmap/2026-10-09-original-battle-cats-delivery.md` の運営バッチ1、ルート`CURRENT.md` |
| CCG-INIT-001 | PASS | 2026-10-13: 明示目的／制約で `init --no-hooks --mission ... --constraints ...` 成功。UTF-8 Charter内容照合、`restore --brief`、`audit` は Healthy=True / Errors=0 / Warnings=0 / Infos=0。Hooksは登録せず | `docs/ai-continuity/PROJECT_CHARTER.md`、`HANDOFFS/handoff_20261013_044747_OPS-BATCH-001.md` |
| OPS-RED-001 | FAIL | 実装前の意図的RED。protocol module、bridge option、bundle moduleが未存在だったことを確認した記録で、現行実装の失敗を示すものではない | 私的 `work/original-ops-protocol-red.log`、`original-ops-bridge-red.log`、`original-ops-bundle-red.log` |
| OPS-FOUNDATION-001 | FAIL | まとめて57 testsを実行: 54 success、2 calendar fixture ERROR、1 SKIP。ERRORはtest fixtureのfield名`type`が実schemaの`mode`と不一致だったもの | 私的 `work/original-ops-foundation-batch.log` |
| OPS-CALENDAR-REPAIR-001 | PASS | fixtureを`mode`に修正後、`tests.test_original_ops_calendar` 3 tests PASS | 私的 `work/original-ops-calendar-repair.log` |
| OPS-LOGIN-ARM64-001 | PASS | 合成ARM64 treeに対するreadonly map header/lookup tests 2件PASS。original runtime bytesやSAVEは使っていない | 私的 `work/original-login-arm64-batch.log`、`tests/test_original_login_runtime.py` |
| OPS-SOURCE-CATALOGUE-001 | PASS | owner export/server cacheのsize+MD5照合とcatalogue生成PASS。53,849 asset names、1,096 map、127 gacha minimum-roster、57 ordinary login candidates。UI／battle acceptanceではない | 私的 `work/liveops-verified-catalogue-private.log`、`tools/liveops/original_catalogue.py` |
| OPS-RUNTIME-001 | NOT_RUN | 運営全機能の同一候補PC受入は未完了。過去handoff時点のbuild未実行状態から進展し、個別結果は後続行へ記録 | `docs/research/2026-10-14-original-liveops-batch1.md` |
| OPS-RESUME-CONTRACT-001 | PASS | 原作Ops/共通calendar/bridge/presign/login/barrierをまとめて60 tests実行、59成功・1 skip。skipしたnative環境は次行で個別に実行。後続のclock envelope変更は別のruntime受入が必要 | 私的 `liveops-investigation/resume-contract-stream-batch.log` |
| OPS-RESUME-ARM64-001 | PASS | 全履歴用のbounded tree snapshotを含む合成ARM64 lookup 3 tests PASS。元メモリ・SAVEへの書込みなし | `tests.test_original_login_runtime.OriginalLoginArm64Tests`、NDK27.2.12479018/Unicorn |
| OPS-LOG-START-001 | FAIL | PC候補fe221304の最初のcaptureはSTART barrier未確認でアプリ起動前に停止。失敗を合格へ読み替えない | 私的capture `20261014T093755Z-3af4b725` |
| OPS-LOG-START-REPAIR-001 | PASS | bounded marker再送の2 tests PASS。その後の実captureはSTART/END確認、原作起動を記録。ゲーム機能受入ではない | 私的capture `20261014T094056Z-c48e14c6`、`tests/test_pc_log_barrier.py` |
| OPS-STREAM-CONTRACT-001 | PASS | 元Dex/ELF照合とcallback修正後、実PCでsale→gatya→itemの取得・registered registry・3callback返却を確認。ガチャの抽選成功ではない | 私的build `20261014T094622Z-50b64f28`、capture `20261014T094841Z-8726ab5d` |
| OPS-GACHA-HGT-001 | FAIL | ガチャ画面にHGT00。運営getTimeの拒否maskは0x7df（first flagだけ相違）を3回確認。時刻要求の限定variant対応を追加し、次候補で検証中 | 私的build `20261014T095803Z-3e5eb4bf`、`resume-clock-current-pid.log` |
| OPS-CLOCK-ENVELOPE-BUILD-001 | PASS | getTime限定variantの修正版をJava/Dex/NDK/6split signing/static検証。実運営・UI/SAVE受入は未完了 | 私的build `20261014T100409Z-756048a4`、`resume-clock-envelope-build.log` |
| OPS-AD-CONTROL-BUILD-001 | PASS | 原作が更新完了前に要求するad_control arrayを広告なしのlocal JSONで返却。Java/Dex/NDK/6split署名・静的検査成功、bounded capture完了 | 私的build `20261014T101413Z-3ef68595`、capture `20261014T101913Z-f59ad543` |
| OPS-LOGIN-UI-001 | PASS | 同候補の原作UIで5枚のログインカード、1日目のスタンプと原作報酬画面を確認。cold restart/翌日/原作SAVE保持の合格を含まない | 私的UI 304～317、build `20261014T101413Z-3ef68595` |
| OPS-NEWS-UI-001 | PASS | 基地右上iからローカルのお知らせ本文を表示。close後のnative入力に未解決事象があり、lifecycle全体の合格ではない | 私的UI 324～333 |
| OPS-GACHA-EVENT-001 | FAIL | HGT00は出なくなったが開催枠が空。「ガチャイベントエラー」が出て実抽選未成立 | 私的UI 319～321 |
| OPS-GACHA-MISSION-CONTRACT-001 | PASS | 通常ガチャ区分1・週月period保持・login等をまとめて24 tests、23成功1native skip。native変更なし、前工程の3件結果を保持 | 私的 `resume-gacha-mission-batch.log` |
| OPS-DENIED-CALLBACK-CONTRACT-001 | PASS | local-bootの未対応HTTPを外部送信せず非同期503/errorへ完了する変更のbridge/runner回帰39件成功 | 私的 `resume-denial-callback-contract.log` |
| OPS-CACHE-NAME-001 | FAIL | literal event_0.dat等を対象にした初期cache移行は、原作のMD5名cacheに一致せず旧開催を保持した | build `20261014T121023Z-b08d447d`、私的UI370～371 |
| OPS-CACHE-REFETCH-001 | PASS | MD5(event_N)+.datの3cacheを退避する修正後、sale→gatya→item→getTime→ad-control再取得。SAVEの5受領countを各1で保持 | build `20261014T130938Z-56e679c2`、私的 `resume-save-evidence/v6-initial-save` |
| OPS-GACHA-DRAW-001 | PASS | 原作ガチャバナー/残り期間/1ticket表示、実抽選で神徒スルズ、原作貯蔵庫1/64へ格納。元SAVEでrare_tickets差分-1・catfood/XP差分0を確認。冷起動後の同結果保持は未完了 | 同候補、私的UI377～382と `v6-after-draw` |
| OPS-LOGIN-SAVE-001 | PASS | 原作SAVEを安定した2回読取り・hash検証・固定parserで読み、700001～700005を各1で確認。cold起動/APK更新で追加付与なし | 私的 `v3-before-gacha` / `v5-after-cache-migration` / `v6-initial-save` |
| OPS-WEEKLY-UI-001 | PASS | 原作週次tabに進行条件を満たすミッションと残り4日を表示。達成・報酬受取の合格は含まない | 同候補、私的UI385 |
| OPS-MONTHLY-OLD-PERIOD-001 | FAIL | 月次tabは原作に表示されたが、旧試験で作った途中開始のperiodを保持し残り29日。更新時の月/週identityを固定するauthor期間を修正中 | 私的UI386、season revision4へ更新 |

| OPS-GACHA-PERSIST-001 | PASS | 冷起動・次APK更新後、貯蔵庫unit234とticket299を元SAVEの安定読取りで保持確認 | 私的 `resume-save-evidence/v7-cadence-and-storage`、build `20261014T134126Z-3e6f0d95` |
| OPS-MONTHLY-V4-001 | UNKNOWN | canonical月期を収録したrevision4でも実UIは残り29日。旧途中periodが原因という初期推測は未確定のまま | 私的revision4の月次UI観測、build `20261014T134126Z-3e6f0d95`。原因未特定 |
| OPS-EVENT-CLEAR-ATTEMPT-001 | FAIL | 未準備の基本ネコ編成で調査中に敗北。代表クリア／報酬未達、製品不具合との因果未確定。原作stamina40／Nekobon1消費、未補充 | 私的UI398～399、同候補。所有者指定で追加操作停止 |
| OPS-ROTATION-AUTHOR-001 | PASS | 既存calendar形式へ通常20+週4+月2を展開、所有原本53849 assets/1096 maps照合、94 bindingsで32日bundleを生成 | 私的 `ops-stage-rotation-v5-compile.log`、bundle SHA `7c704360f8bfd74481717ac653cb264e24591cd37761b7a47ced971497c496c1` |
| OPS-ROTATION-BUILD-001 | PASS | Java/Dex/NDK/署名6split/static build成功。実ゲームの26枠表示／2時間切替を確認したという意味ではない | 私的 `ops-stage-rotation-v5-build.log`、build `20261014T145031Z-3bce4fd1` |
| OPS-ROTATION-PLAY-001 | NOT_RUN | 所有者の「検証は不要」に従い、追加プレイ／戦闘／時計変更／スマホ検証を実施しない。新候補の端末導入も未実施 | `AMENDMENTS/2026-10-14-stage-rotation-20.md` |

| OPS-PHONE-UPDATE-001 | PASS | 所有者の更新依頼により、実installed署名一致を確認して6splitを-r更新。installer Success、導入後全6SHA一致、同一UID/dataDir保持。SAVE bytes比較やプレイ合格は含まない | PC元候補 `20261014T145031Z-3bce4fd1`、私的phone候補 `phone-20261014T150621Z-01ec6fff` の `PHONE-OPS-UPDATE.json` |
| OPS-PHONE-VISUAL-001 | NOT_RUN | 恒久分担に従いスマホの起動／画面操作／ログ／SAVE取得なし。本人目視確認待ち | 2026-10-15 JSTの所有者による更新依頼。追加検証停止の指定を維持 |

| OPS-PHONE-HGT00-001 | FAIL | 初回運営更新後、本人がHGT00／ログイン・イベント・ガチャ非表示を報告。許可済み既存PID固定ログでsale/gatya後のitem失敗3回、native readiness unavailable10回を確認 | 私的 `hgt00-phone-reproduced-fixed.log`。初回導入整合性PASSとは別 |
| OPS-DUAL-GL-ARM64-001 | PASS | 完全phone hook／PC JNI／未準備・部分状態／別threadのゲートとbounded map readの関連4件成功、元heap非変更 | `OriginalLoginArm64Tests`、私的 `hgt00-gl-gate-after.log` |
| OPS-DUAL-GL-BUILD-001 | PASS | 新共通GL readinessのJava/Dex/NDK/署名6split/static build成功 | 私的候補 `20261014T154800Z-5ec0ba86`、`hgt00-dual-gl-build.log` |
| OPS-DUAL-GL-PC-REFETCH-001 | PASS | PC cache markerのみを退避して通常再取得。GL readyとsale/gatya/item/ad-control各1、Ops stream failure0 | 私的capture `20261014T155358Z-3d44ff1a` |
| OPS-HGT00-FIX-PHONE-UPDATE-001 | PASS | 実署名一致・-r更新・導入後6SHA一致・UID/dataDir保持。SAVE内容比較／スマホ実表示の合格は含まない | 私的phone `phone-20261014T155048Z-0307ca04` の `PHONE-OPS-UPDATE.json` |
| OPS-HGT00-FIX-PHONE-VISUAL-001 | NOT_RUN | AIはスマホを起動せず、修正版のHGT00解消／各運営表示は本人目視待ち | 恒久分担を維持。初回HGT00のFAILを消さない |

| OPS-GACHA-CONTRACT-002 | PASS | レア3時間2＋週1／通常2、カテゴリ別group、通常0とN3のみのsource、空字幕・常設期間の関連27件とAgent terminal成功 | 私的 `gacha-permanent-terminal.json`／bundle `2f088c496d84ba15c537516faa4dd8987533ff6fca3f3bb3a4c77414fee86f02` |
| OPS-GACHA-GMT-002 | FAIL | revision6の実PCで週特選のみ・通常無効。GMTの開催判定不一致を同一候補JST再起動で切分け | 私的 `gacha-v6-rare-three`／`gacha-v6-normal-fresh`、失敗証拠保持 |
| OPS-GACHA-JST-002 | PASS | 専用AVDのみAsia/Tokyo。JST以外のops captureを端末変更前に拒否する追加回帰1件成功 | 私的 `pc-gacha-timezone-terminal-fixed.json`。初回fixture違反FAILは別途保持 |
| OPS-GACHA-BUILD-002 | PASS | 最終候補のJava/Dex/NDK/署名6split/staticとPC bounded capture成功 | build `20261014T181055Z-4b304f94`、capture `20261014T181438Z-db518317` |
| OPS-GACHA-UI-002 | PASS | 最終PCでレア3タブ、通常＋マタタビ入りの2タブ、通常字幕／期限なし。マタタビ入り1抽選XP5000、ticket1消費、元SAVE／貯蔵庫保持 | 私的 `gacha-v7-rare-final`／`gacha-v7-normal-permanent`／`gacha-v7-item-result`／`gacha-v7-final-save` |
| OPS-GACHA-PHONE-002 | NOT_RUN | phone候補作成済みだがUSB offlineで導入前停止。旧スマホ内容を維持、接続復帰を依頼済み | 候補 `phone-20261014T181623Z-daa89a6f`、preflight FAIL receipt。スマホUI／ログ／SAVE取得なし |
| OPS-GACHA-PHONE-CONNECTED-002 | PASS | 本人の接続復帰後、既存署名照合・Android -r更新・導入後全6SHA一致・UID/dataDir保持。ゲームの本人目視は未確認 | 実導入 `phone-20261014T181623Z-daa89a6f`。receipt `OPS-BATCH-001_0f43d377955a4e3e93f1208b98d4b0e4.json`、private PHONE-OPS-UPDATE.json |
| OPS-GACHA-CI-FIRST-002 | FAIL | Test tooling／Agent terminalの既存backup試験が旧guard・throw拒否のみを期待し、JVM stubに元individual APIがなかった。816実行／2fail／6skip | GitHub commit `1adc14a`、Actions `38620529684`／`38620529712` |
| OPS-GACHA-CI-REGRESSION-002 | PASS | テストだけを現行の503/error完了とindividual callbackへ追随。JDK17で関連10件、元super送信0とgetTime HDF／200／direct body確認 | 私的 `gacha-ci-regressions-fixed.json`、Agent terminal PASS。ゲームAPK差分なし |
| OPS-BATCH-001 | PASS | Executed command exit=0 | docs/ai-continuity/verification-receipts/OPS-BATCH-001_e800831c76a2411c87a81d60d8966f44.json |

## 2026-10-20 — OPS-BATCH-001 Godzilla facing

- PASS: Agent terminal `godzilla-ally-facing`, 21 tests; report SHA-256 `1e9a00c09437de0162b3c959a24573831a6df0f917118f80363940e4f27fdbb1`.
- PASS: private approved-v2/v3 comparison: only `702_f.mamodel` root X `1790 -> -1790`; other 8 payloads identical.
- PASS: 6split build `20261019T184640Z-35b3aee8`, candidate `phone-20261019T184729Z-525a825b`; private proof `liveops-investigation/godzilla-facing-fix-proof.json`.
- NOT_RUN: actual renderer visual check and phone installation; minimal verification requested. Existing FAIL/UNKNOWN evidence remains applicable.
| OPS-BATCH-001 | PASS | Executed command exit=0 | docs/ai-continuity/verification-receipts/OPS-BATCH-001_67b8f8434e704708a0351e2648530901.json |

## 2026-10-20 — OPS-BATCH-001 完全反転の再検証

- FAIL: 本人画像と旧版PCでroot Xだけの変換が姿勢を崩すことを再現。初回21 tests／build PASSは保持するが、描画受入PASSではない。
- FAIL: 角度修正だけの中間版 `20261020T075455Z-3855fac1` は実戦後native crash。private `godzilla-facing/scoped-runtime.log`、`exit-info.txt`。敵config1件／味方は2件を要求する差を原本とnative呼出しで確認。
- PASS: 修正前に落ちる回転／config添字の回帰を追加後、関連23 tests。Agent terminal report SHA `753761cfcdcf5e42772ad2914a0b72d362d8dae045fff39b1a3486d26813a1ea`。
- PASS: 最終cache approved-v5、全609フレーム／375144頂点の左右対称誤差0。実command receipt [67b8f843](verification-receipts/OPS-BATCH-001_67b8f8434e704708a0351e2648530901.json)。独立描画計算であり、原作内確認とは別。
- PASS: 最終6split build `20261020T082803Z-c0206218`、phone候補 `phone-20261020T083338Z-b8c65002`。スマホ再更新は未実施。
| OPS-BATCH-001 | PASS | Executed command exit=0 | docs/ai-continuity/verification-receipts/OPS-BATCH-001_c67606c43b984a3387cbefdbe2d74d20.json |
- PASS: 最終原作PCで敵味方同時の左右反転描画、左向き歩行・攻撃・完全勝利。36観測／約158秒生存、追加native crashなし。[実command receipt c67606c4](verification-receipts/OPS-BATCH-001_c67606c43b984a3387cbefdbe2d74d20.json)。private `godzilla-facing/FINAL-PC-ACCEPTANCE.json` と実画面を確認。
- PASS: 元PC SAVEをbyte単位で復元、SHA `2f65346e49e86492ce3044ada10bf6ad93707d49afae27ec4778e298443ad01c`。
- NOT_RUN: スマホ再更新／本人の最終確認。接続端末は専用AVDのみ。旧版の今回観測は生存しており、毎回のcrash再現や全体安定性の証明にはしない。
# 2026-10-20 指定キャラ写真

- [実装・証拠の所在](../research/2026-10-20-godzilla-portrait.md)：関連24 tests PASS（agent terminal `godzilla-portrait-related`）、12 payloadのうち元9件byte一致、3 PNG原作寸法・枠外画素一致。原作PC編成画面で新しい出撃アイコンを確認。育成用・入手用はPNG画像確認まで、実画面NOT_RUN。
- PC `20261020T123613Z-556bd0a8` 6 split build／導入SHA一致。スマホ候補 `phone-20261020T124348Z-e45a2eb7` 作成、導入・本人確認NOT_RUN。PC試験用SAVE復元済み。以前のFAIL／UNKNOWNを変更しない。
| OPS-BATCH-001 | PASS | Executed command exit=0 | docs/ai-continuity/verification-receipts/OPS-BATCH-001_1428f4d5ffca4586b71f0e613c840cc6.json |
| OPS-BATCH-001 | PASS | Executed command exit=0 | docs/ai-continuity/verification-receipts/OPS-BATCH-001_0a84bbbc6ca14ba8bcdf74fc536583d9.json |
# 2026-10-20 季節・曜日の運営修正

- [日程・実装・検証記録](../research/2026-10-20-seasonal-liveops.md)：25 tests PASS、197 source bindings・revision9 compile、ログインrotation不変。初回fixture FAIL／特殊ticket候補拒否の原経緯を保持。
- 最終authoring baseを含む25 testsのmachine receipt `OPS-BATCH-001_20bd317bf25c498498c914e476c56b11`。PC build `20261020T131246Z-cca69482` の6split／10秒capture PASS。machine receipt `OPS-BATCH-001_1428f4d5ffca4586b71f0e613c840cc6`。
- スマホ `phone-20261020T131439Z-86d1bb23` 署名一致・6SHA一致・UID/dataDir保持更新PASS。machine receipt `OPS-BATCH-001_0a84bbbc6ca14ba8bcdf74fc536583d9`。本人ゲーム目視PENDING、AIスマホ操作／SAVE取得NOT_RUN。過去FAIL／UNKNOWNを変更しない。
| OPS-BATCH-001 | PASS | Executed command exit=0 | docs/ai-continuity/verification-receipts/OPS-BATCH-001_20bd317bf25c498498c914e476c56b11.json |
| OPS-BATCH-001 | PASS | Executed command exit=0 | docs/ai-continuity/verification-receipts/OPS-BATCH-001_07bdba14bc5b47e999162bb9188f8bd1.json |
| OPS-BATCH-001 | FAIL | Executed command exit=1 | docs/ai-continuity/verification-receipts/OPS-BATCH-001_67903f8bfcf3426da06ed8fa78839c3b.json |
| OPS-BATCH-001 | PASS | Executed command exit=0 | docs/ai-continuity/verification-receipts/OPS-BATCH-001_60b5d4ab981a450fb1b9f404667a9e94.json |
| OPS-BATCH-001 | PASS | Executed command exit=0 | docs/ai-continuity/verification-receipts/OPS-BATCH-001_fd764f8fd8b945a1be62eafe29343c6e.json |
| OPS-BATCH-001 | FAIL | Executed command exit=1 | docs/ai-continuity/verification-receipts/OPS-BATCH-001_ab024ba6d6af43c180dca56d9f3d8cce.json |
| OPS-BATCH-001 | PASS | Executed command exit=0 | docs/ai-continuity/verification-receipts/OPS-BATCH-001_583adb4b4b0e4f56954d12f36a44110d.json |

# 2026-10-23 ステージ開催カテゴリ拡充

- [原因・修正・実検証の範囲](../research/2026-10-23-stage-programme.md)。r9に狂乱／大狂乱／ちびの開催なし。r11で206の専用rule、週別20件デッキ、354原本bindings。最終33 tests PASS `60b5d4ab`。初回32 PASS `07bdba14`、過去日fixture FAIL `67903f8b`を保持。
- PC draftでCatamin A9999→9998／B/C維持／story不変、入口→戦闘→撤退の実画面。receipt `fd764f8f` PASS。最終nativeコード・消費処理は同一。10/23ちびトカゲ、最終10/24狂乱9クリアfixtureで大狂乱トカゲ一覧→ステージ選択を確認。全報酬・発掘取得から鑑定・未クリア比較分岐はNOT_RUN。
- 最終PC `20261022T195407Z-f01c9867`、10秒capture `20261022T195805Z-fc2c825e`。原PC SAVE SHA一致復元・PC時計復帰・アプリ停止・r9ガチャ不変・phone候補 `phone-20261022T201342Z-b7b42258` 作成の実コマンド `583adb4b` PASS。先行stdin復元FAIL `ab024ba6`を保持。画像・元SAVE・詳細proofはprivateのみ。
- NOT_RUN: 今回のスマホ導入／AIスマホ操作／スマホSAVE取得。旧FAIL／UNKNOWN、Charter承認不足を変更しない。
- CCG auditは既存の `CHARTER_UNAPPROVED` と旧handoff等により非正常。今回の作業への直接承認はAMENDMENTに原文を記録したが、Charter全体の承認は推定しない。コード検証のPASSと区別する。
| OPS-BATCH-001 | PASS | Executed command exit=0 | docs/ai-continuity/verification-receipts/OPS-BATCH-001_2bce9a48b84244c580b08bfc3f80603c.json |
| OPS-BATCH-001 | FAIL | Executed command exit=1 | docs/ai-continuity/verification-receipts/OPS-BATCH-001_dcb4ab1a2a44434f9ce32c4bf93ea568.json |
| OPS-BATCH-001 | PASS | Executed command exit=0 | docs/ai-continuity/verification-receipts/OPS-BATCH-001_261d5f9119fe4b66898c4639080d15b8.json |
| OPS-BATCH-001 | FAIL | Executed command exit=1 | docs/ai-continuity/verification-receipts/OPS-BATCH-001_356af215edd74d2f8235c614f2c151f9.json |
| OPS-BATCH-001 | PASS | Executed command exit=0 | docs/ai-continuity/verification-receipts/OPS-BATCH-001_f2ba4ff71006409080c61eb68b249c67.json |
| OPS-BATCH-001 | PASS | Executed command exit=0 | docs/ai-continuity/verification-receipts/OPS-BATCH-001_0bb48ff5dd514eb88b5158edc3f9b9bf.json |
| OPS-BATCH-001 | FAIL | Executed command exit=1 | docs/ai-continuity/verification-receipts/OPS-BATCH-001_d1bb779217f343fa939eea4149a17b52.json |
| OPS-BATCH-001 | PASS | Executed command exit=0 | docs/ai-continuity/verification-receipts/OPS-BATCH-001_550bab4a4fd0423c9a6f104eadf78777.json |
| OPS-BATCH-001 | FAIL | Executed command exit=1 | docs/ai-continuity/verification-receipts/OPS-BATCH-001_a8fcaed9f81a44d1b4d9cdeb94297d9c.json |
| OPS-BATCH-001 | PASS | Executed command exit=0 | docs/ai-continuity/verification-receipts/OPS-BATCH-001_77b3509cf345410db85595b2b0b150de.json |
| OPS-BATCH-001 | PASS | Executed command exit=0 | docs/ai-continuity/verification-receipts/OPS-BATCH-001_c69c6588bf444a71a64065300a7ea7e8.json |
| OPS-BATCH-001 | PASS | Executed command exit=0 | docs/ai-continuity/verification-receipts/OPS-BATCH-001_2f6ebef162e14cb5b1027da115f6e901.json |
| OPS-BATCH-001 | PASS | Executed command exit=0 | docs/ai-continuity/verification-receipts/OPS-BATCH-001_c5f29fdac1a245929a214287fadff0de.json |
| OPS-BATCH-001 | FAIL | Executed command exit=1 | docs/ai-continuity/verification-receipts/OPS-BATCH-001_8ee717464267422f82fa6d27b6cf3132.json |
| OPS-BATCH-001 | PASS | Executed command exit=0 | docs/ai-continuity/verification-receipts/OPS-BATCH-001_78dac9b85b2d4a42bebf47e0c1cde1d9.json |

# 2026-10-23 原作開催区分・4000個のお詫び

- [承認と技術履歴](../research/2026-10-23-native-stage-policy.md)。全1096候補／1278マップ定義の台帳、988公開索引一致／108未一致を区別。自由交代20件廃止を所有者が明示承認。最終48 tests `c69c6588`、r14 build `c5f29fda` PASS。極悪9現行日程・狂乱祭の各日割当はUNKNOWNを保持。
- r13原作PC UI：ネコカン＋4000、10000→14000、原作MySale受取済み、再起動後14000／再配布なし `550bab4a` PASS。初回item22の配布失敗 `356af215`、誤ったfixture照会先 `d1bb7792`を保持。server drop200へ修正、SAVE直接加算なし。
- フラワー：未来編3未クリアでは開催中も原作条件文で拒否。比較fixtureで白文字・難度星つき有効化。2分を過ぎた入場は終了文で拒否。開催中のステージ選択／戦闘はNOT_RUN。時計巻戻しによるPC HGT02の実画面はprivateに保持、native保護を変更しない。
- 原本DataLocal pair／1278定義・条件とr11ゲーム本体保持 `77b3509c` PASS。元SAVE SHA復元・時計復帰・停止 `2f6ebef1` PASS。r14の実APK内bundle・r13との同一gift/gacha/login/flower/native/DataLocal、導入6SHA／元SAVE／時計／停止／phone候補作成 `78dac9b8` PASS。
- その他のhelper／実行順序FAIL `dcb4ab1a`・`a8fcaed9`・`8ee71746`は原log/receiptを保持。Web抽出v1のナビ混入FAILもprivate原JSON＋履歴を保持。成功結果へ塗り替えない。既存Charter承認不足・旧FAIL／UNKNOWNを維持。
- NOT_RUN: スマホ更新／AIスマホ起動・UI・ログ／SAVE読取り、全ステージ攻略・全報酬。候補 `phone-20261022T213509Z-794bc2d5`、本人の接続後に承認済みデータ保持更新する。
