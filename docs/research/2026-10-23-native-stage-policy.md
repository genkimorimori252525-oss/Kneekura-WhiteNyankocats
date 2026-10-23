# 開催区分・原作条件の全件台帳とお詫び配布

## 所有者の判断と修正

[承認記録](../ai-continuity/AMENDMENTS/2026-10-23-native-stage-policy.md)。旧42候補に月例EX、季節、銀週キャンペーン、進行試練等が混在していた。所有者は常時20件より原作の区分を優先すると明示し、自由交代を廃止した。原作の解放条件を突破する指示ではない。

EX開眼14種を月内の各2日へ戻し、ネコフラワー1148は2日・22日14:22〜14:24、神判1112は20〜21日、大乱闘狂乱1208は1日。季節の開眼1092／1093は10月／11月の後半に限定。ヴァルキリー／ムート大試練は進行解放・クリア後終了を維持する常設対象へ分離。他の旧交代候補は、根拠なく件数合わせで再開催しない。

経験値5種に毎日9〜10・15〜16・21〜22時の**ローカル追加開催**を設定。原作の定期枠・難度ごとの条件も維持。原作が毎日この3枠で開催するとの主張はしない。今季は11月30日0時まで。

## 全件照合の範囲

Lunaが公開DB95索引と定期表を収集。初回v1は共通ナビの混入で日本編にコラボ等を誤分類したためFAILとしてprivateに保持。v2は主要表の最初のplayable linkとsection境界で抽出し、日本編・狂乱・コラボ・フラワー・神判の5fixtureを検査した。ステージ階層の子ページ4445件とマップ1096件を区別し、件数を個別条件の解析完了数と誤認しない。

所有原本の開催可能1096マップを[台帳](../operations/2026-10-23-stage-policy-audit.json)へ全件列挙。公開索引の直接ID一致988、未一致108。Cataminの別familyなど、一覧から直接一致しないものを含む。全1278のMapStageData定義のSHAも保持し、レジェンド等の原作管理分を直接sale.tsvへ追加しない。個々の原作条件は保持したが、すべての条件分岐を解読・実プレイ検証したものではない。未知の規則はUNKNOWNのまま、新たな自由開催の根拠に使わない。

最終候補の `DataLocal.list`／`.pack` は所有原本とbyte一致。全1278マップ定義・MapConditions・Map_option・Stage_optionを含む。元ゲーム本体 `libnative-lib.so` も前候補r11とbyte一致。receipt `77b3509c` PASS。初回検証helperのimport path不足FAIL `a8fcaed9`は保持。

## 4000個配布の不具合と修正

原作 `item.tsv` に一度限りの配布を投影。event/category keyは固定20261023、毎日フラグ0、2026/10/23 0時〜12/2 0時。calendar再生成で開始日やkeyを変えない。SAVEへの直接加算や独自の受取済み台帳は実装しない。

初回r12は通常 `GatyaitemName.csv` の22を配布IDと誤認し、PCで10000のまま・未配布となった。実受取検査FAIL `356af215`。Lunaが一次公開辞書 [BCU item ID](https://github.com/battlecatsultimate/bcu-resources/blob/master/resources/calendar/item%20ID.txt)の配布ID **200 = Cat Food** を確認し、r13へ修正。通常アイテムIDとserver drop IDは別名前空間。

修正版PCで原作「ネコカン＋4000」の受取画面、10000→14000を確認。再起動後も14000、nativeの `mysale.dict_1[20261023]=2`／`dict_2=true` を確認し重複なし。receipt `550bab4a` PASS。先行fixtureが受取記録をdaily loginの辞書へ誤照会したFAIL `d1bb7792`を保持し、原作のMySale領域へ照合先を修正した。製品に別の台帳を足した修正ではない。

## 検証と限界

最終関連48 tests PASS `f2ba4ff7`。フラワー14:21:59／14:22／14:23:59／14:24、EX開催日、季節境界、自由交代再導入拒否、毎日の経験値追加、gift再生成後の同一key／全受取期間／毎日配布拒否を確認。r12の先行48 tests `2bce9a48`も保存。入力生成の終了前にビルドを呼んだFileNotFound FAIL `dcb4ab1a`は、生成完了を待って修正した。

bundle revision13、134 source bindings、SHA `c9c3e1b0c745092c51c03b010f3e63ad0bb201a62adf2521dadbfa14170d1a28`。最終PC `20261022T205757Z-f500177a`、6split build/static/signingと導入後SHA照合。build receipt `0bb48ff5` PASS、起動capture `20261022T205917Z-ffe0b302`。r12先行build `261d5f91`は配布の成功に読み替えない。

PCの未来編3章未クリア状態では、2分開催中でもネコフラワーは灰色となり、押下で原作の「未来編第3章をクリアする必要があります」を確認。クリア済み比較はPC使い捨てfixtureのみ。実画面・SAVE・元原本・鍵・rawログはprivateに保つ。全ステージの攻略・全報酬・未一致108件の全規則解明は未実施。過去FAIL／UNKNOWN・既存Charter承認不足を維持する。

比較中に同日14:22へ戻した操作で原作HGT02が作動した。製品の時刻検知を変更せず、次の開催日11/22へ進めた。未来編3章クリア済みfixtureでは同ステージの白文字・難度星つき有効表示を確認。その後のクリック時には2分間が経過しており、原作の「イベント期間が終了しています」を確認した。したがって条件達成後の表示有効化と期間終了拒否は実UI確認済み、開催中のステージ選択／戦闘はNOT_RUNとして区別する。試験による追加章クリア・自動解放・HGT02状態は製品に含めない。

最終照合で1161狂乱のもねこ（28日）、1209にゃんにゃん記念日（22日）が抜けていたためrevision14へ追補。極悪9の現行開催日・狂乱祭の日別対象は追加確認待ちとして公開台帳から追えるよう記録し、推定日程を配信しない。関連48 testsは最終 `c69c6588` PASS。最終bundleは136 bindings、SHA `f9195e157ccd24d3bd08049775b0689aaa48e5b7de518279eb8e814ae80bb28b`。r13とのitem.tsv／gatya.tsv／login rotation／ゲーム本体・条件データ一致を確認して、実UI証拠の適用範囲を明確にする。

元のPCファイルはprivate tarから復元し、元SAVEのSHA一致・ホスト時刻への復帰・アプリ停止を検証。実復元receipt `2f6ebef1` PASS。ここまでの時計変更・SAVE取得は専用PC仮想端末のみ。スマホのSAVE・起動・ログ取得なし。

最終r14 build `20261022T213246Z-9570d5f3` はreceipt `c5f29fda` PASS。最終処理でAPK内の実bundleとr14入力の一致、r13とのitem.tsv／gatya.tsv／login／flower行・ゲーム本体／DataLocal一致を確認した。同署名PC導入後6SHA・元SAVE SHA・JST／ホスト時刻・停止を照合し、スマホ候補 `phone-20261022T213509Z-794bc2d5` を作成。receipt `78dac9b8` PASS。helperの初回はbuild metadataの不存在keyを参照してFAIL `8ee71746`、実APK内asset検査へ修正した。判定を緩めた修正ではない。スマホは未接続・未導入として別工程に残す。

## 2026-10-23 スマホへのデータ保持更新

本人の「できた」をUSB接続完了の連絡として受け、ADBで認可済みの実機1台と研究版 `jp.kn.local.battlecats` を確認。導入前に、現行6分割APKのSHA-256が前回の導入receiptと一致し、r14候補6本が `PHONE-BUILD.json` と一致、APK内の運営bundleがrevision14のSHA-256 `f9195e15…bb28b` と一致することを確認した。実機の研究版署名と候補6本の署名も照合した。

署名照合後、Android `install-multiple --no-streaming -r` は `Success`。導入後の6分割APKのSHA-256が候補と一致し、研究版のUIDとdataDirが更新前と同一であることを確認した。private証拠は `phone-builds/phone-20261022T213509Z-794bc2d5/PHONE-OPS-UPDATE.json` と同ディレクトリの `stage-policy-r14-update-preflight/INSTALL-RESULT.json`。研究版のアンインストール・データ消去・SAVE読取り・起動・画面操作・ログ取得は行っていない。ゲーム画面と4000個受取の本人目視はPENDING。

最初の実行は、旧導入スクリプトをメモリ上でr14に適合させる際、PowerShellからPythonへの複数行文字列の引用を誤り `SyntaxError: unterminated string literal` で終了した。Python本体の実行前なのでスマホ操作・ファイル更新は0件。次の実行ではコードを `-c` の単一引数として渡し、同じ事前条件・署名・導入後照合を通した。以後、既存スクリプトのメモリ実行ではコードを追加の引用文字列へ埋め込まない。
