# 原作ローカル運営バッチ1：接続・ログ収集の修正記録

状態は実装中。運営バッチ1は所有者承認済みで、PC検証のみを行う。スマホ上の目視確認は所有者が行う。

## 発生した問題と技術的原因

### 原作ガチャ画面に開催内容が表示されない

旧追加実装は、原作HTTPのすべてのローカル応答を6引数の `newResponse` で返していた。JP15.7.1の元Dexを確認すると、`a32.run(view, flag1, flag2)` の `flag1` はindividual callback方式を選び、該当する要求には `onResponseCodeHeaders` → `onResponseData` → `onResponseFinish` を使う。

原作native側も一括応答とindividual応答に別のrequest registryを使う。一括応答を送っただけの固定ログは本文の受領証明にならず、旧PC画像のレアガチャは開催枠が空だった。元の更新callbackはsaleの本文を検証後にgatya、itemを順に取得するため、saleの本文が渡らなければ後続も進まない。

修正は原作要求フラグに従って元のcallback方式を選ぶもの。元registry、handle、GL queueを使い、原作の解析・抽選・報酬・保存処理は保持する。診断は要求の役割とregistry登録状態だけを記録し、URL query、header値、通知本文やSAVEは出力しない。修正版の実UI受入は別途必要。

最初の修正後、実PCでsale→gatya→itemの3取得を確認したが、ガチャ画面はHGT00で停止した。運営更新が最後に行うgetTimeもindividual要求で、既存backup照合の`flag1=false`条件に拒否されていた。固定診断のmaskは3回とも`0x7df`で、`0x7ff`との差はfirst-flag-false bit `0x20`だけだった。変更はlocal-boot内で、同じ厳密なURI・GET・空body等の条件と`action=getTime`を満たすfirst flag variantだけを受けるもの。全backup操作の条件緩和や時刻検査の無効化は行わない。

### 再起動時のログインassignment消失

sidecarの前回観測countは、diskに保存された原作countより新しい場合がある。旧追加履歴処理は古いslotを復元する時、後から発行したslotをactiveから削除し、履歴にも残していなかった。すでに受領countがあるassignmentを失う経路も再現した。

修正は全発行keyをboundedな履歴に残し、原作countから未完了の古いassignmentを選び直す。復元で押し出された後続assignmentも残し、再び選ばれた時は同じkeyと原作countを使う。HTTP配信を受領扱いにせず、原作SAVEへ新しいwriterを追加しない。合成Java stateとARM64 readonly tree検証は実行済みだが、実ゲーム内の5枠受取・cold restartは別の受入項目。

### logcat開始barrierが見つからない

最初の候補試験ではSTART markerを確認できず、アプリ起動前に `INCOMPLETE_CAPTURE` とした。collector起動直後に一度だけ送るmarkerは、ADB/logcatの購読開始より先に送られ、tail指定から落ちることがある。

修正は時間上限内で同じ一意markerを再送し、実際のcollector出力で確認するもの。無条件の待ち時間や「起動したはず」で確認を置換しない。markerを観測できない場合やcollector終了時は失敗を維持する。修正後の実captureでSTART/END確認とアプリ起動を記録した。

## 検証上の原則

- 「Opsログが存在する」だけでゲーム内運営をPASSにしない。
- 「拒否されたHTTPログがゼロ」だけでegressゼロと判定しない。
- source catalogue、TSV生成、Java/NDK/署名/静的検査、原作UI/受取/SAVEの証拠を区別する。
- 失敗したrunと未実施項目を保持し、修正後のPASSで上書きしない。

実行結果と候補識別は `docs/ai-continuity/EVIDENCE_INDEX.md` と `CURRENT.md` を参照。元APK・原作データ・raw log・SAVE・鍵はprivate storageへ保持する。

## PC候補での更新完了と残る不具合

`20261014T101413Z-3ef68595` はJava/Dex/NDK/6split署名・静的検査に合格。対応capture `20261014T101913Z-f59ad543` はbounded captureを完了した。これらは運営機能全体の合格を意味しない。

原作の更新完了callbackはsale→gatya→item→getTimeに続いてad-control JSONを読み、`ad_control` arrayの確認後に更新完了を発行する。ローカル側は広告配信なしの `{"ad_control":[]}` を返す。原作の完了flagを直接書き換えない。この候補で5枠すべての原作ログインカード、1日目のスタンプ、伝説の罠+1・XP+5000・レアチケット+1・XP+50000などの原作報酬画面を確認した。冷起動後の重複抑止・翌日進行・SAVE保持は引き続き未確認。

基地右上のiからローカルのお知らせ本文を表示できた。レアガチャは従来のHGT00から「ガチャイベントエラー」へ変わったが、開催枠が空で抽選は未成立。お知らせを閉じた後の一部基地ボタンが反応しない事象も調査中。原作開催データの解釈とWebView lifecycleの証拠を確認してから修正する。全機能完了・配布可能とは判定しない。

私的UI証拠は `liveops-investigation/resume-ui/20261014T101413Z-3ef68595/` の301～333画像と、候補SHA照合・操作時刻付きreceiptに保持する。

## 開催区分・週月ミッション・更新キャッシュの修正

通常レアガチャのwire区分は1。旧追加実装の2は初回レア向けで、PackPackの「それ以外はRARE」という分類だけでは区別できなかった。固定BCSFEの`get_first_rare_flag()`も2を初回区分としている。通常区分を1に変更し、bundle validatorと期待wireベクトルを統一した。

週次8000は実在するが、原作`unlock_condition_id=15`により日本編3章クリア後は非表示。8000～8004は同じ条件、8005～8011は3章クリア後の対象なので、12件を開催対象とし、表示・達成・受取は原作条件に任せる。月次17000は元の月間選択群。週は月曜0時、月は1日0時で窓を分割する。初回期間は10月14日から。compilerは隣接するmission窓を併合せず、途中の日付から再生成しても元の開始・終了を保持する。期間途中の優先順位による分断は未対応として拒否する。

原作updater（runtime offset `0x31b1c0`）は最大39600秒のcacheを使用し、1件でも欠損すれば通常の再取得経路へ戻る。実ファイル名は`MD5("event_0") + ".dat"`等の3件で、literal `event_0.dat`ではない。最初のcache移行候補は名前が相違し再取得せず、失敗として保持した。修正後はAPK内バンドルSHAまたはJST日付変更時にこの3件のみを私的archiveへrenameし、原作の取得・検証を再実行する。SAVE、進捗・報酬count、原作の更新完了flagは変更しない。

候補 `20261014T130938Z-56e679c2` はJava/Dex/NDK/6split署名・静的検査PASS。実PCでsale/gatya/item再取得、5枠の受領countがすべて1のまま保持されること、レアガチャ開催バナー・期間・消費チケットの表示を確認した。抽選演出開始後の結果・保存は引き続き確認中。

未対応HTTPをhandle発行前にthrowすると、原作の待機画面に終了callbackが返らない。local-bootでは外部通信を行わず503/errorを原作handleへ非同期で返すようにした。既定OFFの旧research拒否動作は保持。該当bridge/runner回帰39件PASS。ガチャ／週月／login修正のまとめ試験は24件中23成功・native依存1skip（nativeの変更はなく前工程の3件実行結果を保持）。

原作SAVEの読取り専用・連続2回一致・既存hash検証を行い、700001～700005の5countが冷起動およびAPK更新後も各1であることを確認した。私的 `resume-save-evidence/` に元bytesと結果を保持し、公開台帳にSAVE内容や識別情報は出さない。

基地ボタン無反応という初期観察はWebView破損の確定ではない。仮想端末の短いtapと画面遷移中の操作が混在していたため、押下時間・遷移後の待ち時間を確保し、実際にミッション／戦闘開始画面へ復帰することを確認した。ゲームの入力処理は変更していない。


## 所有者追加指定：通常20枠＋週4枠＋月2枠（2026-10-14）

所有者の「検証は不要」を受け、追加の実プレイ・時計変更・スマホ検証を中止した。通常はイベント一覧の20マップ枠をJST偶数時に入れ替え、特選の週4・月2を加える。クリア済み状態や初期MAXを独自に書き戻す処理は追加しない。原作固有の回数制限・進入条件・報酬処理は原作に委ねる。

`stage_rotation.py` は選定JSONから既存のweekly/once規則を展開する。通常60候補を素材等6／挑戦7／開眼7に分け、84個の曜日・2時間ブロックを生成。特選IDは通常poolから除外し、週月間でも同時開催重複を拒否する。原作sale.tsvの1行で20mapを指定するため、原作ゲーム側へ新しいcalendar形式や専用SAVE形式を追加しない。Javaは元の3hashed cacheを退避する期間keyをJST2時間単位に変更し、39600秒cacheが新しい入替を妨げる経路へ対応した。反映は元メニューの更新機会で、バトルへ強制割込みしない。

現行packは `2026-autumn-ops-rotation.json` revision 5、選定原本は `2026-autumn-stage-selection.json`。初週はまどか・ケリ姫・メルクストーリア、翌週はゴジラ中心。10月は秋だよ運動会！と文化祭グルメ戦争、11月は勤労感謝スペシャル！と謎の宅配便。収録期間は10/14 00:00～11/15 00:00 JSTで、期限前の次期運営更新が必要。

生成時の所有原本/cache照合・94件binding・canonical bundle生成はPASS。bundle SHA256 `7c704360f8bfd74481717ac653cb264e24591cd37761b7a47ced971497c496c1`。候補 `20261014T145031Z-3bce4fd1` のJava/Dex/NDK/署名6split/static buildはPASS。今回の追加プレイ試験・時計変更試験・端末導入は実施していない。

### 直前の観測の補足（旧記述を成功へ読み替えない）

- 原作抽選で神徒スルズを貯蔵庫へ格納し、ticket299と格納unit234を冷起動および次APK更新後も保持した。私的 `v7-cadence-and-storage` の元SAVE読取りで照合した。
- revision4のcanonical月期を収録しても、実月次UIは残り29日だった。「旧途中periodの保持が原因」という初期推測では解決を説明できず、原因はUNKNOWN。個人開始型の原作期間かどうかも未確定である。
- 代表イベントクリアの試行は、基本ネコだけの未準備編成で調査中に敗北した。stamina40・Nekobon1の原作消費は行われたが、実クリア・報酬受取は未達。製品の戦闘不具合とは確定していない。継続用ネコカンは支出せず、追加操作を中止した。
- 翌日5枠／補充、clock rollback/gap、実クリア／報酬、全SDK/IPC通信監査等は追加未実施のまま保持する。所有者の追加検証停止を、技術的PASSや未知原因の解消として記録しない。


## 2026-10-15 JST：所有者依頼によるスマホ上書き更新

所有者の「さっそく更新してほしい／ADB接続」を受け、PC元候補 `20261014T145031Z-3bce4fd1` からスマホ用manifestだけを調整し、既存の開発署名で6splitを作成した。元PC候補とのpayload照合、収録運営bundleのSHA一致、スマホへ実際にインストール済みの署名との一致を確認してから、Androidの `install-multiple --no-streaming -r` で更新した。installer最終行はSuccess。導入後6splitすべての実SHAが候補に一致し、同一のアプリUID／dataDirを保持した。

データ消去・アンインストール・初期MAX再適用・PCデータ移入は行わない。Androidのデータ保持更新を使用し、元SAVEの内容やbytesは読取り／比較していない。スマホroot、ゲーム起動、画面操作、スクリーンショット、logcat、SAVE取得も行っていない。原作のプレイ・保存内容の受入は所有者の目視確認待ちとする。

私的phone候補 `phone-20261014T150621Z-01ec6fff`、`PHONE-OPS-UPDATE.json` と `latest-phone-ops-update.json` に導入receiptを保持する。公開台帳には端末ID、署名鍵、SAVE、元APK、raw logを載せない。過去の「新候補は未導入」はこの更新より前の状態である。


## 2026-10-15 JST：初回運営更新後のHGT00と描画監視経路の相違

本人がHGT00・ログインボーナス／イベント／ガチャ非表示を報告した。APK導入の整合性確認は成功していたが、原作運営機能の受入成功ではなかった。PC canonicalとスマホ向けAPKはmanifest調整以外のgame payloadを保持し、同じローカル公開鍵hashも含んでいた。PCではガチャ表示まで進んだため、スマホ固有の状態・経路の調査へ進んだ。

所有者が今回だけ既存診断ログの読取りを許可した。最初はプロセス終了・ring buffer上書きにより自アプリの起動停止記録しか残らず、原因の証拠にならなかった。本人にHGT00を再表示してもらい、その自アプリPIDだけの既存固定ログを取得した。スマホの起動・画面操作・再起動・SAVE取得はAIから行っていない。

再現ログではsale/gatya各3回の応答に対しitem成功がなく、Ops stream failureが3回、native request readiness unavailableが10回だった。最初のgetTimeにはローカル成功応答が返っており、今回のHGT00を前回のgetTime envelope不一致と同一原因とは扱わない。

直接の欠陥は、`kneekuraOriginalGlState`／`kneekuraOriginalLoginProgress` が `gPcSceneObserverState == 2` だけを準備済み条件にした点。既存の完全ShadowHook経路ではPC JNI observerの二重登録を防ぐためattacherが拒否する。従って、スマホで元の描画監視が動作していても、ログイン読取りは未準備となりitemを503で返す。運営updaterはsale→gatya→item→時刻→ad-controlを完了できず、個別の開催内容が反映されない。

最小修正は共通の元描画proxyが原作へ転送・帰還した後にoperations用GL TIDを記録するもの。readinessは隔離process・元source準備・完全hook=1またはPC JNI observer=2・確認済みGL threadを要求する。原作mapのbounded read-only snapshotは維持し、二重の描画hook、SAVE書込み、ログインcount初期化、報酬の直接付与は追加しない。

ARM64の関連4件（完全phone hook、PC JNI、未準備／部分状態、別threadのreadinessを含む）に合格。元heapが書き換わらない条件も維持した。候補 `20261014T154800Z-5ec0ba86` はJava/Dex/NDK/署名6split/static build PASS。PC cache markerだけを私的退避して通常の再取得を起こしたcapture `20261014T155358Z-3d44ff1a` で、native GL ready、sale/gatya/item/ad-control各1回、Ops stream failure0を確認した。PC用branchの取得確認であり、スマホの表示確認を代替しない。

phone候補 `phone-20261014T155048Z-0307ca04` を同じ署名の `install-multiple -r` で再更新した。導入前実署名一致・導入後全6SHA一致・同一UID/dataDir保持を確認。スマホがHGT00表示中でもAndroidの通常更新に停止を委ね、別のforce-stop、データ消去、起動、初期MAX再適用、SAVE読取りは行わない。実表示の回復は本人確認待ち。私的ログ・APK・receipt・端末IDは公開しない。
