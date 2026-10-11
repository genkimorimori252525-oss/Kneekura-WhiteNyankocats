# PC追試：文字列例外と素材所有者の修正

2026-10-12 JST。PC専用仮想端末・開発鍵・破棄可能データでの継続作業は所有者承認済み。原本ZIP、公式アプリ、スマホ、既存鍵、他のAVDは変更しない。APKと素材と生ログはprivate以下だけに保存する。

## 原因と最小修正

旧実行 `20261011T172454Z-114adf90` のJavaスタックは `ReceiverInitAlarm.onReceive` → `MyActivity.cancelNotification` → `createIntent` → `localize` → `Resources.getString(0)`。原作DEXの `localize` は `getIdentifier(name, "string", Context.getPackageName())` を使用する。隔離manifestは `jp.kn.local.battlecats` だが、aapt2が示すリソースのパッケージは `jp.co.ponos.battlecats` だった。

元の `package_flavor.py` はbaseのUTF-8アンカーだけを変更し、Androidが参照するUTF-16の `ResTable_package.name` を残していた。base/en/ja/xxhdpiの4表の固定nameフィールドを変更する。JP15.7.1のtable/package header、単一package ID `0x7f`、元のnameとゼロ埋めを検証し、不一致なら停止する。ID・値・その他プールは動かさない。通常・trace・HTTP bridgeの3検証器は、元表から許可された変換を適用した期待バイト列と最終表の完全一致を要求する。

旧処理で4分割のnamespace不一致を再現する回帰テストが失敗し、修正後成功した。別プールの同じUTF-16文字列は保持し、追加変更・元namespace・壊れた表・未知UIDを拒否するテストも追加した。

もう1件はAPI35の素材所有者だった。ADB側では393件MD5が一致していても、アプリ自身のinstrumentationでは393件すべて `isFile() == false`。下層ファイルの所有者がshellで、対象アプリUIDへ変更後にアプリ自身で393件のサイズ・MD5一致を確認した。PCランナーは専用AVD確認後だけuserdebugのadbd rootを利用し、インストール済み研究パッケージのuser0 UIDを厳密取得する。所有者変更は `/data/media/0/Android/data/jp.kn.local.battlecats/files/kneekura-original-jp1571-stage` に限定し、393所有者とMD5を確認する。PC内の使い捨て研究素材への処理であり、スマホ用導入経路は変更しない。

## 実APKの結果

PCビルド `20261011T174225Z-14e68432` はNDK ARM64コンパイル、原作保全・通信権限検査、PC鍵の6分割署名・実端末SHA-256照合を通過した。署名前後のペイロードは同一。実Androidのtarget contextでは `getIdentifier("app_name", "string", isolatedPackage) = 0x7f100020`、元namespaceでは0となった。検査APKは別のPC用パッケージで同じPC鍵を利用し、SAVEの内容を読まない。

| 実行ID | 実測 |
| --- | --- |
| `20261011T174254Z-31a08da2` | 修正APK起動、Java例外0、死亡0。取り込み `invalid-stage` を捕捉。 |
| `20261011T174353Z-94516e04` | 再起動、Java例外0、死亡0。 |
| `20261011T174528Z-8b761175` | 起動後Android全画面案内を確認して閉じる。615MB原作ダイアログを表示。入力は `KNEEKURA_PC_ACTION` の固定イベントで記録。 |
| `20261011T174925Z-1366b3a1` | 新所有者処理を含む `Run -Install`。アプリが393元MD5検証→ `completed-393`。 |
| `20261011T175034Z-a2b7cdb6` | 再起動で `already-complete`、TSV35存在、backup失敗callback帰還2件、Java例外0・死亡0。原作読み込み中に「ネットワークにアクセスできません。」。 |
| `20261011T180235Z-4280f565` | 検査APKの実験後に研究APKを再起動。取り込み済み・TSV35・callback帰還2件・起動時致命Java例外0・死亡0を再確認し、証拠の全SHA-256を照合。 |

すべて `COMPLETE_BOUNDED_CAPTURE`。判定は取得区間の成立だけを示す。起動要求・開始終了バリア・画面・PID・全バッファ・時刻・出所・最終ファイルSHAを確認する。無記録の内部呼出し、ネイティブscene97、基地、完全通信ゼロの合格を意味しない。

## ネイティブ観測の境界と次の検証

`hook-init-status=12` は続いている。[公式ShadowHook v2.0.1](https://github.com/bytedance/android-inline-hook/blob/v2.0.1/shadowhook/src/main/cpp/sh_linker.c) はリンカーのELFアーキテクチャ、内部symbol、constructor/destructorフック、companionロード等を初期化で検査する。研究プロセスの実マッピングには `e_machine=62` のx86_64版と `183` のARM64版両方の `linker64` があるため、ホストリンカーの存在だけで失敗原因を断定しない。API35のARM変換と公式エミュレーターのARM64 AVD拒否は別の制約として残す。

独立したARM64検査APKで公式ShadowHookのdebuggable=trueによる初期化も12となった。元ゲームの起動は失敗再現の必須条件ではない。ただしログは初期化結果までで、内部のどの検査が失敗したかは未同定。元ゲーム対象の別検査ではBOOT_COMPLETED receiverのANRが発生したため、この検査成功を本体互換と扱わない。検査のAPK・C/Java・結果・全バッファ・ANR記録はprivateの `probe-linker-native-v1/v2/v3` に保持する。独立probe v3は元ゲームと別のsandboxなので、その393件missingは元ゲームへの取り込み失敗を示さない。

代替候補は、原作のstatic `appUpdateDraw()V` に対するJNIの明示登録を用い、元関数を必ず先に呼んだ後、同じGLスレッドでsceneと35分類だけを観測する経路。独立probe v3ではARM64関数を `RegisterNatives` で登録し、Javaから期待値41が帰ったことを確認した。**原作への経路は未実装・未検証**。前述のANRを切り分け、元のclass初期化・ロード順序・GLスレッドとの整合を検証してから採用する。元BuildID・命令・VMA・class/method・隔離package一致を必須にし、scene専用観測をLEVEL/SAVEフック成功と混同しない。既存フックのinstalledを偽らず、バックグラウンドから原作可変contextを無保証で読む方法は使わない。

基地・独立SAVE・LEVEL・まどか・シンゴジラ・原作ガチャ・運営・ゼロ通信の受入は未合格。今回は研究環境と不具合の修正で、プレイヤー向け更新を配布していないためゲーム内お知らせは追加しない。将来のAI制作運営ツールは既存ロードマップの予定のまま維持する。

## 検証

- 全体：734件実行、724成功・10スキップ・失敗0。
- Agent terminal self-test、Windowsのplan、PowerShell5.1静的パース：PASS。
- リソース・PC所有者回帰：旧処理の失敗を確認後、修正で成功。
- 独立した最終レビュー：重要な指摘なし。関連57件成功。実ゲームの受入はレビュー対象外。
- GitHubへのpush・私的素材公開なし。最新ソースはローカル開発ブランチに保持する。
