# KNEEKURA WhiteNyankocats — 低負担・差分アップデート構想

Status 2026-10-09: **JSON-driven static preview implemented. In-app updater and original battle hooks are NOT implemented.**

## 原本4ファイルは「設定」ではなく素材保管庫

MNumberServer.list / MNumberServer.pack と WImageDataServer.list / WImageDataServer.pack は**読取専用の元データ**。初回にPCの private/ 内へSHA-256付きで保存し、必要なPNG/imgcut/mamodel/maanimだけ抽出する。毎回これを書き換えたり再取得するのは誤り。素材不足、新規キャラ、原作のバージョン変更などの際だけ追加取得を判断する。元素材はGitHubへ上げない。

## 将来の更新クラス

| 内容 | 更新方法 | APK再インストール |
| --- | --- | --- |
| 既存の攻撃力・射程・コスト等 | バージョン付きJSONで変更差分だけ指定 | 原作ゲームに設定読込層を**一度実装・実機検証した後は**不要にできる。現状はまだ要確認 |
| 新しいアニメーション | キャッシュから素材を抽出し、味方モデルへ変換、追加データだけ配布 | 元の描画エンジンと読込層次第。素材を保管する4ファイルは原則不変 |
| 新しい特殊能力 | 初回に汎用フック実装→以降は能力の対象・数値をJSONで制御 | ネイティブフック追加・変更時は同一署名のAPK更新が必要 |
| レベル上限の先行解放 | 既存の加算式SAVEマイグレーションを一度実行 | 以降の普通の更新で二重に実行しない |

Android署名済みAPKは中のpackだけ直接編集して更新できるわけではない。初回の拡張をAPKとして導入するには既存署名鍵・パッケージIDの一致が必要。現在の DownloadLocal 先勝ち規則やH01なしの実機動作も未検証。

## 実装した「一つの設定ファイル」入口

- docs/updates/manifests/update-1.01.json はJP15.7.1の原本SHA、元の各キャラCSVのSHA、対象フォーム・変更列、ユーザー確定値、安全条件、未完了の実機ゲートを含む**設定原本**。
- tools/base_mod/prepare_update_manifest.py はこのJSONと所有済み元ZIPから、対象フォームのみ変更したCSVと検証記録を private/ に出力。原本 DataLocal / 4つのServer pack / SAVE_DATA / APK / 端末は変更しない。
- tests/test_prepare_update_manifest.py は既存1.01ビルダーと設定値の整合性、改変対象フォーム、原本検証、危険な出力先と変更拒否を検証する。

リポジトリ直下で、開発用の静的プレビューだけを作るコマンド（**インストールはしない**）:

~~~powershell
python -m tools.base_mod.prepare_update_manifest --manifest docs/updates/manifests/update-1.01.json --owned-export nyanko_battlecats_2026-10-06.zip --output private/update-1.01-preview
~~~

requirements-tooling.txtの依存関係が必要。端末や原本Serverアーカイブの再提出はこの静的変更プレビューには不要。

## 到達させたい最終形

1. **一度だけ** JP15.7.1の厳密なデータ読込・戦闘ダメージ確定のフック、JSON読込層、モデル変換・キャッシュ機能を構築し、原作UI・機能OFF時の無変更を実機検証する。
2. 以後の能力調整はupdate-1.02.jsonのようなファイルを一つ更新し、既存更新との差分だけ生成。変更なしのアセットを再梱包・再取得しない。
3. 端末上の設定ファイルを扱う仕組みが原作エンジンに入れば、データ変更はAPK再署名なしで適用できる。**現段階ではその仕組みは未実装**。
4. APK更新が必要なら先にSAVE_DATAとインストール済みAPK6本をローカルに退避、SHA・JP salted-MD5・署名・package/version一致を照合。同一署名の更新のみ許可。アンインストール、データ消去、元SAVEの上書きはしない。
5. 原作UIの戦闘/アニメ/3連撃の敵城ダメージ1・再起動での保存継続を検証し、元へ戻せる証拠が揃った更新だけ公開済みと呼ぶ。

現在のC版battle101は機能OFFの判断関数で、本家ダメージ確定処理と未接続。ゴジラ元モデルの味方変換も未実装。したがって、**1.01はいまJSONだけを書き換えれば遊べる状態ではない**。この作業は今後の設定変更の手間を削減するための安全な第一段階や。
