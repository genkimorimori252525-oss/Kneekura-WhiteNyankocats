---
current_task: "OPS-BATCH-001"
active_agent: "Codex"
branch: "codex/pc-local-lab-2026-10-12"
commit_head: "30ee33ec236196b46a1145950e6b2aaf806d45f2"
status: "IN_PROGRESS"
evidence_ref: "docs/research/2026-10-14-original-liveops-batch1.md"
updated_at: "2026-10-14T15:59:32.095411+00:00"

---

# Current Progress State

## OPS-BATCH-001：運営更新をスマホへ導入・本人目視確認待ち

- 最新：初回運営更新の本人確認はHGT00でFAIL。本人再現＋今回限定の既存診断ログ許可で、sale/gatyaは返るがitem生成が3回失敗、readonly JNI準備状態がunavailableと判明。PCのみのstate=2ゲートがスマホの既存完全native hook経路を排除していた。
- 修正：元描画の完了後にoperations用GL TIDを記録し、隔離process・source準備・完全hook=1またはPC JNI=2・同一GL threadを要求する共通readinessへ変更。二重hook・SAVE writer・付与処理・原作の進入条件は追加しない。
- ARM64関連4 tests PASS。PC candidate `20261014T154800Z-5ec0ba86` のJava/Dex/NDK/署名6split/static PASS。PC専用cache markerだけを退避して通常再取得させたcapture `20261014T155358Z-3d44ff1a` はready＋sale/gatya/item/ad-control各1、Ops stream failure0。スマホ用の元候補の6SHA一致APKもPCへ入れて比較した。PC installedは現在修正版canonical。
- 同候補由来のphone `phone-20261014T155048Z-0307ca04` を既存署名・Android -rで再更新済み。実6SHA一致、UID/dataDir保持。スマホは起動せず、修正版の本人表示確認待ち。初回HGT00のFAILを消さない。下の初回候補・未導入記録は履歴として扱う。


- 最新指示は2026-10-14の「検証は不要／通常20枠を2時間交代＋週3～5件＋月1～3件」。追加プレイ・戦闘・育成・時計変更・スマホ検証を止める。[変更原文](AMENDMENTS/2026-10-14-stage-rotation-20.md)を優先する。Hooks OFF、初期MAX再適用・自作ステージ・公式アプリ操作は禁止。
- 現行は `ops/seasons/2026-autumn-ops-rotation.json` revision 5、選定原本 `2026-autumn-stage-selection.json`。60候補から通常20（素材等6／挑戦7／開眼7）、週4・月2を重複なしで開催。JST偶数時／月曜0時／1日0時で交代。期間10/14～11/15、期限前の運営更新が必要。
- Javaの元3hashed event cache退避をJST日単位から2時間単位へ変更。元のメニュー更新で再取得する。戦闘割込みやSAVE初期化、独自報酬リセットは追加しない。各イベントの原作進入条件・回数制限は原作へ委ねる。
- private bundle `ops-stage-rotation-v5.json` SHA256 `7c704360f8bfd74481717ac653cb264e24591cd37761b7a47ced971497c496c1`。元export/cache照合・94 binding・生成PASS。候補 `20261014T145031Z-3bce4fd1` はJava/Dex/NDK/署名6split/static PASS、追加テスト／起動／端末導入なし。直前PC installedは `20261014T134126Z-3e6f0d95` のまま。
- 既存機能：原作individual HTTP callbacks、getTime限定形状、ad_control空array、5枠login全key永続化とreadonly JNI、原作基地i、ガチャ／ミッション開催接続。callback throwによる未完了待機はlocal-bootで非同期503/errorへ変更。外部送信やnative完了flag直接操作はしない。
- 実PCで5ログインcount各1・原作ガチャ「神徒スルズ」実抽選／貯蔵庫格納・チケット1消費・冷起動/APK更新後の保持・基地i・週次条件に合う7件を確認済み。履歴はEVIDENCE_INDEXを参照。全機能の実プレイ合格ではない。
- 未解決：月次UIはrevision4でも残り29日。旧periodが原因との初期推測は未確定。原作の個人開始型期間かどうかを含め技術的原因はUNKNOWN。通常calendarの月替わりイベント選定と、この月次mission表示は別項目。
- 直前の水曜battleは基本ネコのみの未準備編成で放置中に敗北。初級クリア／報酬検証はFAIL/未達で、製品不具合とは未確定。stamina40・Nekobon1を消費、未補充。敗北continue画面を残したまま追加PC操作を中止。
- 翌日login・補充・時計後退/gap・イベント実クリア/報酬・月次期限・SDK/IPC全経路egressは未実施／未解決を保持。最新指定で追加受入を停止し、PASSへ変換しない。旧58件3FAIL、START barrier FAIL、cache literal名FAIL等の原証拠も保持。
- 2026-10-15：所有者がスマホ更新を明示依頼。PC元候補 `20261014T145031Z-3bce4fd1` → phone候補 `phone-20261014T150621Z-01ec6fff` を既存署名・install-multiple -rで更新。実installed署名一致／導入後6SHA一致／同一UID・dataDirを確認。SAVE読取り・データ消去・初期MAX再適用・root・スマホ起動／画面／ログ取得なし。スマホのプレイ確認は本人待ち。前項の「端末未導入」はこの更新以前の記録。
- 次の運営作業は所有者の指示に従う。候補と実導入を区別し、スマホ操作なし。公開Gitにはコード・予定・台帳のみ、private/work/assets/raw/AGENTS.md.bakは追加しない。旧handoffにある追加プレイ検証指示は最新変更で失効。
