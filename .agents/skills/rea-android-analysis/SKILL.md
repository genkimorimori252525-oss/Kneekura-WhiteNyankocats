---
name: rea-android-analysis
description: Optional evidence-based Android APK/DEX/JNI/native reverse-engineering with REA. Use only when it provides value over existing tools for the specific investigation; never install, launch, or probe REA as a default step.
---

# REA Android解析（任意スキル）

**REAは選択肢の一つであり、必須工程でも優先ツールでもない。** このSkillは使いどころを伝える軽量な指針であって、REA本体・MCP・JADXエンジンを同梱、導入、常駐させるものではない。

- 普通の実装、ビルド、テスト、ゲーム運営、文書作成、調査準備では **このSkillの詳細を読んだりREAの有無を確認したりしない**。
- APK/DEX/Smali/JNI/ネイティブライブラリの挙動・呼出し関係などを、根拠付きで調べる具体的な必要が生じた場合だけ候補にする。
- **REAを使わない判断も正解**。対象、既に得ている証拠、解析の深さ、コストから最小限の手段を選ぶ。既存の方法で十分なら新しい道具を増やさない。

## 解析手段の選択（軽いものから必要に応じて）

| 目的 | まず検討する手段 | REAを選ぶ場面 |
| --- | --- | --- |
|既知のゲームデータ・設定・CSV・差分・ハッシュ | リポジトリ既存の `tools/` と証拠ファイル | 原則不要 |
| APKの権限・ファイル一覧・構成 | 既存のインベントリ、aapt/Apktoolなど | Manifestからクラス・参照を段階的に追う必要がある |
| DEX/Java由来の処理・難読化メソッド | JADX、Smali、既存のDEX調査ツール | クラス/メソッド検索、呼出し元の追跡、同一APKに紐づくEvidenceが役立つ |
| C/C++由来の `.so`・JNI | ELF調査、既存のGhidra/逆アセンブラ、シンボル・ログ | ネイティブ解析プロバイダーと統合して追跡する利点がある |
| 実行時の不具合・挙動 | PC上の既存ログ・安全なデバッガ・限定的なFrida観測 | 静的解析で不十分で、独立の実行時調査が適切なときのみ |

選定前に「何を確かめたいか」「既存の証拠では何が足りないか」を明確にする。毎回全ツールを探索・比較したり、装備のためだけに依存をインストールしたりしない。

## REAを選択した場合だけ

1. 対象が所有者の権限内にあるローカルAPK/ネイティブバイナリで、解析によって既存の製品・SAVE・署名・端末を変更しないことを確認する。オリジナルAPKや生の著作物をリポジトリ/チャットへアップロードしない。
2. **既にREAが使える環境であれば** `rea --help` で利用可能な機能を確認する。無ければ既存のJADX等で続行できるか先に判断する。インストールすること自体をタスクにしない。
3. REAによるAPK静的解析には、対応版Node.js、フルJDK 17以上、REAが指定する `jadx-headless-mcp` のJAR等が必要。特にWindowsではREAパッケージ側の対応状況も確認する。環境が揃わなければ無理に起動しない。
4. 必要になった新規インストール、`npx rea-agents setup`、MCPの常時登録、グローバル設定やPATHの変更、外部ダウンロードは、変更内容と出所を確認して所有者の明示的な承認を得た場合にのみ行う。公式情報は [morluto/rea](https://github.com/morluto/rea)、[Android解析ガイド](https://github.com/morluto/rea/blob/main/docs/android-analysis.md)、[導入ガイド](https://github.com/morluto/rea/blob/main/docs/installation.md) を参照する。
5. 機能の存在を確認した環境では必要な範囲だけ実行する。例（`<PRIVATE_APK>` は個別の実在ファイルへ置換）：

   ```text
   rea inspect-android-package "<PRIVATE_APK>"
   rea search-android-classes "<PRIVATE_APK>" MyActivity
   rea inspect-android-class "<PRIVATE_APK>" jp.co.ponos.battlecats.MyActivity
   rea inspect-android-method "<PRIVATE_APK>" jp.co.ponos.battlecats.MyActivity newHttpRequest
   rea trace-android-references "<PRIVATE_APK>" jp.co.ponos.battlecats.MyActivity
   ```

   利用中のREA版が対応するCLI/MCP操作名だけ使う。機能不足なら通常の逆解析ツールへ戻る。

## にーくら固有の境界

- このSkillは **解析専用**。元のPONOSアプリ、正規SAVE、端末内データ、Kneekuraのビルド成果物には書き込まない。署名・導入・ゲーム本体の変更は別の指示と既存ゲートに従う。
- 6分割APKなどは、単一の `base.apk` を調べただけで全体を解析したことにしない。個々の実在するsplit/ABI/DEX/ELF、版、SHA-256を区別する。REAのAndroid APK解析はsplit APK集合やAAB全体をそのまま解析・統合する機能ではない。
- 静的逆コンパイルで見えた呼出し候補は **実際に呼ばれた証明ではない**。JNI・反射・難読化、ロードされる別の `.so`、原作ランタイムとの対応は根拠と未確認点を区別する。結果の採用には既存の検証・根拠基準を守る。
- 原則PC上で完結する読み取り専用解析を選ぶ。本人スマホの起動・操作・画面/ログ収集・SAVE読取り等は、`AGENTS.md` の所有者指定どおり、当該作業の明示依頼なしには行わない。
- REA/追加エンジンのダウンロードURL、バージョン、ハッシュは実際の公式資料に照合する。出所不明バイナリを実行しない。APKや保存データ、個人情報、端末識別子を公開レポートへ含めない。
- 調査結果には対象のSHA-256、選んだ手段、その理由、確認できた事実、推測、未検証事項を簡潔に残す。**REAを不採用にしたことは失敗扱いしない**。

このSkillは `CURRENT.md`、`PRODUCT_IDENTITY.md`、`AGENTS.md` の権限・安全性・製品要件を上書きしない。
