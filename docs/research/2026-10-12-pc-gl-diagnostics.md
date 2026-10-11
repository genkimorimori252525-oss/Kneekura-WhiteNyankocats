# PC原作GL診断と証拠の検証（2026-10-12）

## 目的と境界

所有JP15.7.1の原作描画と起動を維持し、専用PC端末から正確な内部状態を観測する。通常の更新・署名・起動・採取は入力待ちなし。スマホ、公式アプリ、既存署名鍵を変更しない。ステージ・ガチャ・イベントのAI制作環境は後続予定で、既存LEVEL/MADOKA/GODZILLA/OFFLINE計画を維持する。

## 初期化順序の証拠

検査v2のPID8682はANR(reason6)。専用端末の終了記録に紐付くANRで、mainはReceiverInitAlarm→MyActivity.<clinit>→Runtime.nativeLoad、検査threadはnativeProbeで待機していた。具体的なロック循環は未同定。v4ではrunOnMainSyncで原作クラスの初期化を先に完了させ、原作プロセスでJNI登録echo41、393件のsize/MD5一致、ShadowHook12を正常取得した。並行ロードを避ける順序を観測実装に採用した。ShadowHook12の内部失敗箇所は未解決。

## 観測契約

- 新規 `KNEEKURA_RESEARCH_PC_JNI_SCENE_OBSERVER` はdefault OFF。専用PCビルダーのみnative/Java双方を明示選択し、phone/public受領書でPCライブラリを受理しない。SAVE試行とは併用不可。
- `super.onCreate` 完了後、原作 `mGLView.queueEvent` から、exact原作class/static `appUpdateDraw()V` に1件の `RegisterNatives` を行う。constructorからJNI登録しない。
- 隔離process、原作BuildID `8cb3815648eb9642da10bfb039d71bff7a3519bd`、19個のARM64命令、唯一のtext mapping/source VMA shift、class一致を再照合。部分inline-hook rollbackや既存5フックとの二重取り付けを拒否。
- 元の描画関数を必ず先に呼び、帰還後に同じGL TIDでのみcontextを読む。異なるthreadでは描画をそのまま転送し、context観測を停止する。
- 診断は限定scene IDと35値の4分類だけ。SAVE内容・資産内容・アカウント・URL・生アドレスは集計しない。scene97の分布は変更時、最大4回。0は成功や失敗を意味するとまだ断定しない。
- PC scene専用観測はLEVEL/SAVEの5フック成功と独立。既存ShadowHook12や `native_hook_installed_events=0` を隠さない。

## 証拠の3段階

| 判定 | 意味 |
| --- | --- |
| `COMPLETE_BOUNDED_CAPTURE` | 開始終了バリア、起動要求、画面、全buffer採取等の取得区間が成立 |
| `observer_summary` | PID/TIDと順序の一致から、どの観測backendが実際に原描画帰還を取得したか |
| 原作ゲーム受入 | 基地・独立SAVE・LEVEL・まどか・シンゴジラ・原作ガチャ・ゼロ通信など。別の未達ゲート |

取得品質のPASSだけでゲーム合格を宣言しない。ログ欠落の検出は既知のlogd/chatty/EOF報告に限られ、報告されない欠落が絶対にない保証ではない。粗いPID観測の合間の短命processも、全bufferのStart procと終了ログで補う。

ビルド前にnative/bridge/build-tool/runnerソースを `BUILD-SOURCE.zip` に保存し、各SHA-256を記録する。ビルド前後の対象ソースSHAが変われば最新ビルドとして公開しない。各captureにも出所ZIPを保存し、インストール済み6分割の実SHAと候補を照合する。古い保存captureは出所ZIP未対応の場合があるため、その歴史上の証拠の範囲を拡張しない。

保存後の `Verify` は端末操作なしで全記録対象ファイルのSHA-256と、区間/PIDで絞った生ログから再集計したruntime/observer結果を照合する。これは意図しない変更の検出用で、CAPTURE.json自体を書き換えられる攻撃者に対する電子署名ではない。

ANRは今回観測PID、guest時計の取得区間、exact研究process、固定 `/data/system/procexitstore/anr_DATE.gz` パスが一致した終了記録のみ取得する。8MiB以下をprivateに保存し、取得不可ならcaptureの不備として残す。トレースはsystem由来の追加情報を含み得るので公開しない。共有用は固定カテゴリの集計と画面に限定する。

## 日常運用

```powershell
./tools/PC-LAB.ps1 -Action Update -ObserveSeconds 30
./tools/PC-LAB.ps1 -Action Run -ObserveSeconds 30
./tools/PC-LAB.ps1 -Action Verify
```

Updateは専用端末確認→ビルド→専用鍵で署名→6分割更新→393ファイル整合性/所有者確認→起動前からログ採取。Runは既存候補を再起動して独立区間を取得。Verifyは最新の保存区間を再検証する。履歴を消さず、各回のprivate記録を保持する。`-Action Check` は端末と候補のハッシュ確認で、保存ログ再検証とは別。

## 実測

最初のPC JNI観測capture `20261011T181627Z-83319502`：scene102→101→97、検索分布missing0/zero35/one0/other0、原作バックアップ失敗callback帰還2、HTTP拒否0、致命Java例外0、process死亡0。PID9528/TID9601で登録→元描画帰還が一致。シーン97で原作「ネットワークにアクセスできません。」画面を確認。スマホと同じsceneまで到達した証拠であり、内部の全状態が同一という証拠ではない。

| 取得区間 | 条件 | 結果 |
| --- | --- | --- |
| `20261011T182117Z-fd9e207a` | 出所ZIP・ANR取得対応版の更新 | scene102→101→97、35値0/35/0/0、例外・死亡0 |
| `20261011T182558Z-0c5f3bc2` | verifier修正後の最終Update | 同上、当該ANR記録なし |
| `20261011T182707Z-c6a55233` | 同じ6分割APKを更新せずRunで再起動 | 同上、同GL帰還、当該ANR記録なし |

4区間すべて保存証拠の再検証がPASS。最終ビルド `20261011T182516Z-eb512f3b` は126個の対象ソースと出所ZIPのSHAを保存。初回区間は出所ZIP未対応だったため、後続区間と区別する。

全体テスト739件実行、729成功・10スキップ・失敗0。Agent terminal self-test/Windows plan/PowerShell静的パースPASS。研究ARM64ビルドとdefault OFFのARM64ビルドが成功し、後者に観測マーカーが含まれないことも確認した。スキップはWindows上のホストCコンパイラ未導入・symlink条件等。独立レビューのP2指摘2件を修正し、追加回帰18件成功、再レビューで追加指摘なし。レビュー担当は実APK/端末を検証せず、実測は別証拠として扱った。

scene97の35値が全0だった原因、0の解釈、オフラインエラー条件は今後の切り分け対象。原作タスク完了・基地到達・ゼロ通信・製品受入は未合格。研究環境のみの変更でプレイヤー向け更新を配布していないため、ゲーム内お知らせは追加しない。
