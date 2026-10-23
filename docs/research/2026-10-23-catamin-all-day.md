# ネコビタン47マップの24時間開催（revision15）

2026-10-23、所有者の[直接指定](../ai-continuity/AMENDMENTS/2026-10-23-catamin-original-policy.md)に基づくローカル運営変更。JP原作の全対象開催時刻は[調査上UNKNOWN](2026-10-23-catamin-source-audit.md)のまま保持する。解放条件・ネコビタンの消費・回数制限を原作に残し、開催時間だけを変更する。

## 変更内容と原因

- r14では現行47マップ `14005..14051` が全て毎日0〜8時だったため、本人の17:18の確認時には入口が出なかった。r15は毎日0時〜翌0時に変更。旧色マタタビ `14000..14004` は除外を維持する。
- 単に終了時刻を変えるだけでは、calendar compilerが隣接する終日開催を複数日1行に結合し、原作が参照する日次の開催開始日を失う。Catamin family14の開催をmissionと同様に元のoccurrence単位で分け、日次境界を保つ。途中の日から再生成しても当該日の行は一致する。
- 期間は従来のシーズン末尾2026/11/30 0時まで。10/23から38日分の別行を生成した。24時間は期間内での毎日の開催時間であり、未解放マップや当日上限済みまで遊べる意味ではない。
- 原作 `libnative-lib.so`、条件・消費・回数定義を含む `DataLocal.list/.pack` はr14とバイト一致。他の開催行、ガチャ、配布、ログインrotation、お知らせも一致。初期MAX・ステージクリアの再適用なし。

プレイヤー向けの別お知らせは追加しない。今回の入口時刻修正は本開催表と更新時の説明にまとめ、既存のお詫び・ログイン告知と配布IDを維持する。

## 一括検証の証拠

公開machine receiptは `docs/ai-continuity/verification-receipts/OPS-BATCH-001_<ID>.json/.log`。以下の短縮IDはその先頭。

| 検証 | 結果・範囲 |
| --- | --- |
| 変更前の回帰RED | `506c9011`：8時以後47件が消える旧設定を検出。`25087eb1`：24時間にしても2日分を結合するcompilerを検出 |
| 運営関連7モジュール | `213a8284` PASS、49 tests。0時・7:59:59・8時・17:18・23:59:59・翌0時の全47件、旧5件除外、日次行・途中再生成、既存運営の回帰 |
| 所有原本照合compile | `5e41c491` PASS。bundle SHA-256 `ab340dc5eb874f2e0d360d9024a40fa417fad85bc7b74b5b77d17fc604d0f656` |
| Android6分割build | `9972e61d` PASS。PC build `20261023T091149Z-7ee8fe90`。導入後6SHA照合も実施 |
| PC検証ガード回帰 | `fcbca717` RED → `7541c4f2` PASS、15 tests。運営bundleを持つ実metadataの階層へfixtureと検査を修正 |
| PC起動ログ | `66cc2e98`は起動captureとしてPASSだがGMTのためJST受入には使わない。JST修正後の `2170ae9c` PASS |

### PC検証環境の時差検出漏れ

専用AVDの自動時差検出がcold boot後にGMTへ戻り、夕方なのに残り約14時間と表示された。`tools/pc_lab.py` の既存JST guardはbundleの存在を誤って `native` から調べていたが、実metadataでは `presign` にあるため実ビルドを検査できていなかった。合成fixtureも誤った階層を再現していた。

実構造へ最小修正し、GMT/UTC/空値なら導入・起動前に拒否する15件のPC module試験をPASS。専用AVDだけ自動時差検出をOFF、手動 `Asia/Tokyo` に設定し、夕方の残り時間が翌0時まで約5時間と一致することを確認した。ホスト・スマホ設定は変更しない。これはPC側のguard変更で、既にbuildしたAPKのruntime payload変更はない。

### PC原作UIでの限定受入

私的証拠は `private/pc-lab/liveops-investigation/catamin-native-schedule/` と同buildの `resume-ui/`。元PC SAVEとfiles/shared_prefsは試験前に私的バックアップした。スマホのデータ・起動・画面・ログは扱わない。

- JST夕方に「開放中+」→ネコビタン→ゲリラ経験値「経験は蜜の味 初級」から戦闘開始まで到達。原作費用表示はA1。所持数A `9999→9998`、B/C不変。途中離脱後のクリア数は0、storyのserialized bytesも不変。
- 原作helpは「3回クリアすると再挑戦できなくなる」「クリアするまでは何度でも挑戦できます」と表示。したがってこのマップは挑戦回数でなくクリア回数制限。各マップ固有の回数を一律3へ書き換えてはいない。
- 専用PCの捨てfixtureだけ `chapter_completion_count[14011]=3` にすると、その日のゲリラ経験値が一覧から外れることを確認した。3回の実攻略を行った証拠ではない。

- PC時計を翌日00:01へ進め、原作の起動・ログインを経て、同マップの開始日が `20261023→20261024`、クリア数が `3→0` になり、「あと3回クリア可能」と再表示された。日次リセット処理を追加・迂回せず、別の開催行に原作が反応することを確認。
- `935500ce` PASS：元PC files/shared_prefsをバックアップから復元し、元SAVE SHA一致・時計復帰・停止を確認。修正済みの手動JST設定は維持。
- `e8056520` PASS：スマホ候補 `phone-20261023T093506Z-c6a29a1b` 作成。元PC buildからmanifestのlabel/debug設定だけ変更、他payload同一、6本署名検証、既存開発署名一致。**スマホ未導入**。
- `45e1e023` PASS：最終候補内bundleのSHA・47件×38日次行、r14ゲーム本体/DataLocal一致、実導入6SHA、私的消費／上限／翌日観測、元SAVE一致・時計復帰・JST・停止、候補6SHAと署名をまとめて照合。私的 `FINAL-ACCEPTANCE.json` は実画面4枚のSHAも保持。

全47件の実攻略・全解放条件分岐・全報酬の試験はNOT_RUN。原本とnativeの同一性による保持確認と、代表マップの実動作試験を区別する。スマホ更新後の目視確認は本人が行い、AIの追加端末操作を標準の受入工程に加えない。

## 試験helperの停止・失敗を保持

- 初回warmupは、既存4000個ギフトの未受取PC popupを知らず `UNKNOWN_UI` で停止。画像確認後にPCで既存ギフトを受け取り、別証拠フォルダで再開。配布内容・IDは変更しない。
- 翌日のwarmupもログインスタンプのアニメーション中に `UNKNOWN_UI` で停止。静止後の実画面で既存報酬popupを確認し、同じテンプレート認識を別フォルダで再実行して基地へ到達。未知画面へ盲目的にtapしない安全停止は維持する。
- 一時Pythonコードの複数行を別の文字列へ埋め込んだ際の `SyntaxError` は、コードを `-c` の独立引数として渡す形へ修正。最終確認helper初回 `66033870` はrepository外scriptの `sys.path` 不足により `ModuleNotFoundError: tools`。cwdを明示追加して `45e1e023` で実行成功。いずれもゲーム改変の不具合と混同しない。
- REDの3件、GMTでの初回capture、上記helper停止も原証拠を保持し、最終PASSで上書きしない。raw画像・SAVE・APK・鍵はprivate、公開Gitには実装・予定・台帳・receiptのみを追加する。
- Git staging後のSHA照合で、新receiptのWindows改行がGitの自動変換対象になっていることを検出。既存 `.gitattributes` の個別例外だけでは新logを保護できないため、receipt log全体へ `-text` を追加し、測定時のbytesのまま再stageする。receipt内のSHAを変換後の値へ書き換えず、全13件をindex内の実bytesで照合する。
- CCG auditは従来の `CHARTER_UNAPPROVED` と過去handoffの参照commit差異等を検出。旧Charterの機械承認receipt不足を解消したとしない。今回の作業根拠は記録した所有者の直接指示であり、project全体の自己承認は行わない。

## スマホ更新前に検出したCIの画像依存問題

本人のデータ保持更新指示を受けた導入前確認で、commit `4519063` の [Test tooling](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/actions/runs/39933465109) と [Agent terminal validation](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/actions/runs/39933465108) がFAILだった。全体試験の `test_pc_balance_assets` 読込みが、`godzilla_portrait` のtop-level Pillow importを経由して `ModuleNotFoundError: No module named 'PIL'` で止まった。PCではPillow導入済みで、前工程の関連64 testsにはこのmoduleが含まれていなかったため検出できていない。

画像処理を行わないmetadata参照／原画SHA拒否でもPillowを要求することが原因。新依存を追加せず、承認原画のSHA検証後、実変換の直前へimportを移動した。Pillowのimportを明示拒否した子プロセスでmetadata読取りと不正原画拒否を確認する回帰を追加。関連6 tests `53c0fa70` PASS。画像変換の出力・APK payloadは変更しないため、PC受入済みの同じ候補を使う。新CIの結果と端末更新結果は後続に記録する。

commit `efa1c33` の [Test tooling](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/actions/runs/39933933077) は839件実行・833成功・6 skip、[Agent terminal validation](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/actions/runs/39933933038) はUbuntu/Windowsとも成功。両workflowの完了を確認してからスマホ更新を開始した。旧CIのFAILは修正済み履歴として保持する。

## 同日：本人依頼によるスマホのデータ保持更新

本人の直接指示：「ADB接続したよ。今のスマホのデータを残したまま更新してくれ。あとの目視確認は俺がやるよ。」

認可済みの物理ARM64端末1台を動的に選び、研究版 `jp.kn.local.battlecats` の旧6APKが前回r14更新receiptと一致することを確認。候補 `phone-20261023T093506Z-c6a29a1b` の6SHA、APK内bundle SHA、インストール済みbaseと候補全6本の実署名を照合した。

Android `install-multiple --no-streaming -r` は `Success`。導入後の6APK SHAが候補と一致し、UID/dataDirは更新前と同一。実command receipt `990846c4` PASS。私的証拠は当該phone-buildの `PHONE-OPS-UPDATE.json` と `catamin-r15-update-preflight/INSTALL-RESULT.json`。

アンインストール・データ消去・初期profile再適用・SAVEの取得／書込みは行わず、Androidの置換更新で現データを保持した。SAVEの実bytes比較を行った証拠ではない。スマホの起動・強制終了・画面・ログ取得やプレイ検証は実施せず、ゲーム動作は本人目視確認待ち。端末の署名不一致を回避する処理や再インストールは行っていない。

### 同日：本人の動作成功報告

更新後、所有者からスマホで正常に動作しているとの報告を受領。今回のr15更新は `OWNER_CONFIRMED` として記録する。報告は今回の更新についての動作成功であり、全47件の攻略・全解放条件分岐・全日次上限を本人が個別確認した証拠には拡張しない。追加修正・試験・スマホ操作は行わず、次の運営指示を待つ。
