---
current_task: "OPS-BATCH-001"
active_agent: "Codex"
branch: "codex/pc-local-lab-2026-10-12"
commit_head: "1cdf3b22aa554c2275788665234c5d84514af6c7"
status: "IN_PROGRESS"
evidence_ref: "docs/research/2026-10-20-godzilla-complete-reflection.md"
updated_at: "2026-10-20T08:50:21.816084+00:00"

---

# Current Progress State

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
