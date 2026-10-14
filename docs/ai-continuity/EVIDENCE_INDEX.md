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
