# 2026-10-20 シンゴジラの完全な左右反転

## 障害と原因

本人の更新後画面で、横倍率だけを変更した第1形態の姿勢が崩れ、後ろ向きに歩くように見えた。旧候補 `20261019T184640Z-35b3aee8` の関連21テスト・署名・build PASSは、見た目の合格ではなかった。前回の確認不足としてFAILを保持する。

描画は親から継承する符号付きサイズと回転を別に適用する。横倍率だけの反転は `R(θ) Mx`、必要な全体の反転は `Mx R(θ) = R(-θ) Mx`。シンゴジラの初期角度が非ゼロの部品69個、および4動作の回転track135個／key981個を含めて反転する必要がある。

参考実装：[BCU EPart.java](https://github.com/battlecatsultimate/BCU_java_util_common/blob/master/util/anim/EPart.java)、[Part.java](https://github.com/battlecatsultimate/BCU_java_util_common/blob/master/util/anim/Part.java)。参考実装との比較を原作Android描画の証明に読み替えない。

## 最小修正

`tools/base_mod/pc_balance_assets.py` の検証済み第1形態の組立工程で、modelの角度列とmaanimの回転track（type11）の値だけを符号反転する。前工程のroot X反転と合わせる。frame番号・補間／easing・移動・pivot・倍率の大きさ・opacity・重なり順・画像・imgcut・能力値・元攻撃時刻は維持する。敵550と第2形態702_cは変更しない。

### PC実戦で発見した、味方用の座標設定不足

回転修正だけの中間候補 `20261020T075455Z-3855fac1` は実戦で左向き移動／攻撃を描画したが、その後SIGABRT。translationの `Cannot process signal 11` と、元native内の座標変換先頭で不正ポインターを観測した。単なる表示PASSで完了にしない。

原本照合では敵550のmodel末尾はconfig1件、元の味方702_f／702_cは2件。元nativeの呼出しは `flags & 1` を添字に、32バイト間隔でconfigを取得する。1件のままでは2件目を範囲外から読み取る。この差は前回のroot-only版にも残っていた。

元の敵のconfig0（描画原点）は保持し、元の味方と同じneutral config1 `(0,0,0,0,5,0)` をrootに追加する。敵の1件だけのfooterをそのまま維持する方針を、味方の必須形式に合わせて修正した。元native命令・SAVE・第2形態を変える修正ではない。footerの形式やrootが想定と異なる場合は停止する。旧cacheは保持し、最終候補を `approved-v5` とする。

## 検証

- 回転するspriteの四隅が反転後も一致する回帰と、味方のconfig0/1を両方参照できる回帰を追加。それぞれ旧処理でFAIL、新処理で関連23テストPASS。既存の改ざん拒否・PC trust gateは保持。
- 所有者PCの元550_eと候補702_fを独立した描画計算で比較。歩行181、待機116、攻撃311、KB1、合計609フレーム・375,144個のsprite頂点で、X符号反転／Y不変の誤差0。画像・切出し矩形も元と同一。旧root-only候補は同じ比較で大きな誤差があり、回帰を検出できる。
- privateの歩行・攻撃contact sheetを目視。胴体・足・尻尾・光線を含めた左右対称を確認。これらの元素材・画像は公開しない。
- 最終6split build `20261020T082803Z-c0206218`、phone候補 `phone-20261020T083338Z-b8c65002` PASS。中間版の原作PC起動capture `20261020T075750Z-7b183a27` PASSと、実戦のnative crash FAILは別々に保持。最終版の原作内確認は下に追記する。

private証拠は `pc-lab/liveops-investigation/godzilla-facing/` の `red-test.json`、`all-frame-reflection.json`、`compare_rig.py` とcontact sheet。独立計算の全フレーム一致と原作内の動作確認は別の証拠として扱う。PCの一時編成は元SAVEをバックアップして使用し、スマホのSAVEを取得・変更しない。

お知らせpackの再生成は行わず、表示修正の記録を本書と不具合台帳に残す。

## 最終候補の原作PC確認

- `謎の巨大生物現る` に、PC専用の一時編成でNo703第1形態を投入。画面内で元の敵と味方を同時に確認し、胴体・足・尻尾・口からの光線が対向する正常な姿勢で描画された。左への歩行、攻撃、完全勝利まで確認した。
- 36観測・約158秒の範囲でアプリは生存し、追加のnative crashなし。実行receipt [c67606c4](../ai-continuity/verification-receipts/OPS-BATCH-001_c67606c43b984a3387cbefdbe2d74d20.json)。全ステージ・全状態の安定性まで保証する試験ではない。
- 旧root-only版はPCでも本人画像と同じ傾いた姿勢になった。旧版の今回の観測ではアプリは生存しており、範囲外参照によるcrashが毎回発生するとは主張しない。config不足の形式差・native添字と、中間版で実際に出た不正ポインターを修正根拠とする。
- private最終証拠 `godzilla-facing/FINAL-PC-ACCEPTANCE.json`、`battle-20261020T082803Z-c0206218/frame-07.png`（敵味方同時攻撃）、`frame-12.png`（味方の姿勢）、`frame-34.png`（完全勝利）。元素材・画面・SAVE・native逆コンパイル本文は公開しない。
- 一時編成と資金用のPC試験設定は元SAVEを保持して作成し、終了後にbyte単位で復元。元SAVE SHA-256 `2f65346e49e86492ce3044ada10bf6ad93707d49afae27ec4778e298443ad01c`。スマホへのデータ初期化やMAX再適用はない。
- 端末一覧は専用AVDのみ。スマホ候補は準備済みだが再更新は未実施で、スマホ目視は本人が担当する。

試験準備時の失敗もprivate記録に保持する。編成の保存値はcat index+2で、最初のindex直書きは別キャラを選んでいた。PC試験の資金上限も初期値では不足するため一時設定で用意。native Androidの既存オフライン購入エラーはUI階層の実button boundsを確認してtapで閉じ、ゲームへの長押しと区別した。試験補助のactivity名誤記、復元receiptの命名衝突も修正し、最終SAVE復元を別途SHA照合した。これらをゲーム動作の合格には含めない。
