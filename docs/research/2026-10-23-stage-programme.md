# 大狂乱・ちび開眼・ネコビタンと開催カテゴリの拡充

## 原因

revision9の配布予定に狂乱・大狂乱・ちび開眼が含まれていなかった。全狂乱クリアの条件だけでは開催そのものは追加されない。通常S系だけの選抜では、B系のネコビタンやQ系の超獣討伐も開催できない。SAVE破損との根拠はなく、今回の原因は開催データの不足。

## 変更

`2026-autumn-stage-selection.json`からrevision11を生成。交代20件、週特選4件、月間2件に加え、狂乱／大狂乱／ちび、暴風、降臨、マタタビ、超獣、終末、女王の発掘調査、月間強襲、ネコビタンを月日・曜日・時刻で追加した。206の専用rule、stage catalogue324件、全schedule801件。重複catalogueを共有し既存上限400／1000以内に収めた。公開JSONは予定の生成結果であり、ゲーム原本やSAVEを含まない。

交代プール42件を週ごとの再現可能なデッキにし、2時間ごとに20件を選ぶ。strideはプール長と互いに素にする。42件にstride21を用いて2通りしか出ない退化を避ける。終了は11月30日0時、月間境界は1日11時。詳細は[本人向け開催表](../operations/2026-10-23-stage-programme.md)。

原作MapConditions・章条件・戦闘・出撃制限・消費・報酬を変更しない。ネコビタンは原作B系47マップ、毎日0〜8時。発掘のH系地図は配布／直接開催せず、通常の取得と鑑定を残す。女王の調査1〜5のみ原作の開催枠を追加した。すべてのマップが無条件に出現するという仕様ではない。

## Luna調査と原本照合

[DB定期開催](https://battlecats-db.com/schedule/regular.html)、[大狂乱](https://game8.jp/battlecats/208020)、[ちび開眼](https://game8.jp/battlecats/224520)、[ネコビタン](https://gamelinkplus.com/battlecats/bc-basic-info-nekobitan-stage/)、[終末](https://game8.jp/battlecats/392193)、[女王の調査](https://game8.jp/battlecats/519156)をLunaが調査した。2026年公式の期間限定開催表を複製したものではなく、定期規則とローカル選抜を組み合わせた運営予定。

旧5色マタタビはVer15.2で[統合](https://game8.jp/battlecats/763111)。所有JP15.7.1のMap1422「進化のマタタビ」を使い、定期表に残る旧5色や旧ネコビタン5色を復活させない。[現行マップ](https://battlecats-db.com/stage/s01422.html)の原作条件を保持する。

## 途中で見つけた不具合と教訓

- draft revision10の実画面で1144「KR7」、1153「その一」、1310「310」、1311「311」の仮バナーを発見。原本にCSVと画像が存在するだけでは公開可能なステージの証明にならない。4件を除外し1033・1034・1035・1070に差し替え、再混入を拒否する回帰を追加した。残り38候補の原本バナーも目視した。draftはスマホ未導入。
- revision11の初回追加testは開催開始日より前の10月19日を照会しFAIL。fixtureを10月23〜29日へ修正。原receipt `67903f8b`を保持し、最終33 tests PASS `60b5d4ab`と区別する。
- private UI warmupは報酬ボタンの高さと表示アニメーションに追従できず停止。nativeゲームの失敗と混同しない。未知画面を無条件操作せず、画面確認と位置差分への対応後に再開した。

## 証拠

関連33 tests PASS。calendar境界・曜日漏れ・全20件の一意性・翌週の変化・月間強襲11時境界・Catamin family14のsale.tsv射影・ガチャ不変・仮バナー拒否を確認。receipt `OPS-BATCH-001_60b5d4ab981a450fb1b9f404667a9e94.json`。初回32 tests PASS `07bdba14`も原記録として保持。

最終bundle revision11、354 bindings、SHA256 `c7f33e1a1059011da14e0c330cf41db8a9184071696bb58521d893401ee982dc`。所有原本53,849 assets／1,096 maps／127 gacha／57 loginを照合。PC build `20261022T195407Z-f01c9867`、6split build／署名／導入後SHA照合、10秒capture `20261022T195805Z-fc2c825e`。

draftと最終でnativeコード・消費処理は同一。draftのPC実画面でネコビタン入口→ゲリラ経験値→戦闘→撤退を確認し、元の消費によりAだけ9999→9998、B/C維持、storyシリアライズ不変を検査した。receipt `OPS-BATCH-001_fd764f8fd8b945a1be62eafe29343c6e.json`。10月23日のちびトカゲ開眼も一覧で確認。

全カテゴリの攻略・全報酬・発掘の地図取得から鑑定までの一巡はNOT_RUN。スマホ更新・目視は別工程。旧FAIL／UNKNOWNとCharter承認不足を保持する。原本画像・SAVE・鍵・raw端末ログはprivateのみ。

最終revision11では専用PCだけを10月24日に進め、狂乱9種クリアの使い捨てfixtureで「大狂乱のトカゲ降臨」一覧と「狂竜？ 極ムズ」のステージ選択画面まで入れることを確認した。クリア未達の比較ケース／同ステージの戦闘・勝利まではNOT_RUN。元条件ファイルの保持と実入口の確認を、全条件分岐の合格に読み替えない。

復元初回は約672MBのtarをADB stdinから展開できず `tar: EOF: Illegal seek` でFAIL（receipt `ab024ba6`）。privateローカルarchiveはtar検査・末尾ゼロ・SHAを検査し保持。専用AVDの一意なprivate一時ファイルへpushして転送後SHAを確認し、ファイルから順に復元する方法に修正した。元PC SAVEのSHA一致・ホスト時刻への復帰・アプリ停止を確認し、最終候補のboot keyを再配置。最終receipt `OPS-BATCH-001_583adb4b4b0e4f56954d12f36a44110d.json` は実復元と候補作成のコマンド証拠で、旧結果の包装ではない。転送用archiveは専用AVD内root権限600で残し、削除は行っていない。

同じ最終処理でガチャcatalogueとガチャruleのrevision9との完全一致を検査し、スマホ候補 `phone-20261022T201342Z-b7b42258` を作成。スマホ接続・導入・ログ／SAVE取得なし。private `stage-expansion/FINAL-ACCEPTANCE.json` にbundle SHAと実画面SHAを保持する。
