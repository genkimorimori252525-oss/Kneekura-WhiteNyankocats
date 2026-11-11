# シンゴジラ第1形態のキャラ画像差し替え

2026-10-20、所有者指定画像へNo.703第1形態の写真を変更。原画そのものを縮小・切り抜きし、描き直し・能力変更はしない。以前の完全反転・味方config修正を保持する。

| 対象 | 原作PNG寸法 | 保持する部分 |
| --- | --- | --- |
| `uni702_f00.png` | 128×128 | 出撃枠と余白 |
| `udi702_f.png` | 512×128 | 育成カードの枠、レベル表示、透明部分 |
| `gatyachara_702_f.png` | 128×128 | 入手用画像の外周 |

原画SHA-256は `1bf03b97a7bd0327990101dcfdc112850d37cb51960f3f277b1faaea94a2af65`。原画と原作素材はprivateのみ。公開Gitには変換コードとハッシュだけを保存する。`tools/base_mod/godzilla_portrait.py` が所有原本QUnitServer／QImageServerの対象3画像を照合し、Lanczos縮小・枠内への配置を行う。PNG寸法と出力SHAも固定し、不一致を拒否する。

再ビルド時の原画入力は、PC stateの `balance-cache/godzilla-portrait/owner-source.png`。原本575×402 PNGを置く。既存 `approved-v5` を残し、3画像を加えた12ファイルを `approved-v6` とする。元の9ファイル（戦闘rig7件・能力CSV2件）はbyte単位でv5と一致。第2形態・敵画像は変更対象外。

検証結果：関連24 tests PASS、6 split build／署名・導入後SHA照合PASS。PC build `20261020T123613Z-556bd0a8` の原作編成画面で新しい出撃アイコンの表示を目視確認。育成用・入手用PNGはローカルで画像確認、枠外全画素・元寸法の一致を機械照合。育成用・入手用の実画面表示は今回未実施。戦闘データ不変のため前回の609フレーム検証を繰り返していない。

private証拠はstateの `liveops-investigation/godzilla-portrait/PIXEL-PROOF.json`、`resume-ui/20261020T123613Z-556bd0a8/portrait-formation-hint-three.png`、`godzilla-portrait/portrait-scenario-v1/RESTORED-FINAL.json`。編成表示用の一時PC SAVEは元のbytesへ復元しアプリ終了。スマホSAVEへの転送なし。

スマホ向け候補 `phone-20261020T124348Z-e45a2eb7` 作成済み、スマホ導入・本人目視確認は未実施。前回の反転不具合の本人FAIL、旧native crash、未解決事項は既存台帳に保持する。
