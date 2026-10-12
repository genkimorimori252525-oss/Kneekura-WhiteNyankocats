# PC scene97: 35スロットとローカル起動サービス

既存 LEVEL / MADOKA / GODZILLA / OFFLINE 計画の起動障害調査。PCでは原作タイトル・年齢確認・長崎県ステージ・戦闘まで進行した。基地へ戻る追加試験は最新所有者指定で不要。後続の性能変更まで合格したという意味ではない。公式アプリ、本人スマホ、元SAVE、原本ZIP、既存スマホ署名鍵は変更しない。専用AVDと隔離研究アプリの捨て状態だけを使用する。

## 35個が0になる意味

固定原作JP15.7.1の `0x320be0` は検索データがサイズ条件を満たすと0、不足・サイズ不一致なら1、index等の取得失敗なら-1。ただし空の解析結果も0になり得る。

`context + 0x2fb8` の35個は生の返値とは限らない。`0x73cac0/0x73cac4` は `0xb20bdc` の符号付きeligibilityを読み、負のスロットを `0x73ca5c` で0に置換する。従来の「35個の生のresolver戻り値」という記述を訂正する。

PC実測はactive35 / disabled0、35zero、DownloadBatchTaskのcontext完了値1、所有タスク解放、キュー `download → create-account`。この実行はDownloadBatchTaskを越えている。35zero単独を素材読み込み・基地・ゲーム受入の証明には使わない。

scene97は `DownloadBatchTask → CreateAccountTask → GetConfigPubVendorsTask` を開始する。当初の停止は後続のアカウント初期化であり、以下の独自ローカルサービスを通して解消した。全体タスク完了値・画面遷移の強制修正は行わない。

## 原作応答契約

| 処理 | 原作の契約 | PC対応 |
|---|---|---|
| time | HTTP200、error=false、JSON success=true / timestamp | 実PC時刻のローカル応答 |
| create-account | HTTP200、error=false、success / accountId | 独自schemaのIDを原子的に保存・再利用 |
| register | statusCode=1、payload accountCode/password/passwordRefreshToken | 自分のローカルIDにのみ資格情報を発行 |
| tokens | statusCode=1、payload token | 自分のID・password照合、ローカルRS256 JWT。実APKで原作検証通過 |
| password refresh | POST、accountCode/passwordRefreshToken/nonce、statusCode=1 | 保存済みの独自ID/tokenを厳密照合し、既存資格情報を冪等に再発行 |
| managed-items | nonce、isPaid=false、原作4種のamount | 認証済み現在量を独自versioned ledgerへ原子的に保存。破損台帳・不正量・未知有料要求を拒否 |
| age assets | 原作年齢確認の6ファイル | 元サイズ・SHA固定の私的キャッシュから原作WebViewへ供給 |

共通応答検証 `0x32c524` はstatusCode=1で要求nonceの完全一致が必須。`0x32c918` は `Nyanko-Signature` を取得し、`0x32c348` が公開RSA4096鍵と `EMSA-PKCS1-v1_5(SHA-256)` で本文を検証する。省略・常時成功化はしない。

PC-only `-LocalBoot` では独自RSA4096鍵をWindowsユーザーDPAPIとowner-only ACLで保管。専用APKの `assets/nyanko-service-prd.pem` **1エントリーだけ**を独自公開鍵に置換し、他の素材変更を静的監査で拒否する。別途 `-Balance` を指定した場合だけ固定9素材をDownloadLocalへ追加し、DataLocal・既存DownloadLocal・対象外フォームの保持を照合する。原本ZIP・393素材manifestは無変更。秘密鍵はAVD隔離アプリprivateへstdinで配置、600 permission、SELinux context、guest SHA一致を要求。fingerprintはJava署名側とビルド側で一致必須。原作native署名検証は保持する。

応答originは `file:///kneekura-local/boot/...` と `X-Kneekura-Authority: local`。PONOSの成功や資格情報を主張しない。未知サービス、foreign ID/password、不正JSON、duplicate field、trailing bytes、不正UTF8、鍵不一致は拒否。ソケットを開かずAndroid INTERNET権限も付けない。ただしSDK/IPC全経路のゼロ通信受入は別の未完了条件。

`newResponse` (`0x46158c`) 自体が終端コールバックを配送する。booleanはerrorで、別の `onResponseFinish` 呼出は不要。

APK `20261011T195459Z-0ec54bf1`、採取 `20261011T195557Z-87a204d3` は途中のregister検証記録である。その後token・managed-items・年齢確認を実装して原作戦闘まで進行した。最新の素材導入版 `20261011T220702Z-68f5af86` と採取 `20261011T220914Z-7327ae55` は限定15秒の起動・元描画帰還・Java fatal 0・研究SIGSEGV 0・保存バイト照合Verifyを確認。これを全ゲーム受入とは扱わない。

## 再発防止と検証

- 原作JNI `0x461720` は各headerのJSON string getterを呼ぶ。配列では署名が空になる。空デコードのDataを `0x45d550` が参照し、ARM変換でsignal11→host SIGABRTを再現。単一stringへ修正、配送JVMテスト追加。
- Windows ADB binary stdinはCtrl-Zで切れた。raw exec-inも途中closeを観測。ASCII base64 stdinをframed shellで配送し、独立guest SHAが一致するまで起動しない。
- host鍵生成はWindowsプロセス間byte-range lock、fsync、atomic publication。独立reviewの2 thread / 4 process合成試験で生成1回・同一鍵・失敗0。directory fsyncがなく電源断時の耐久性は未保証。
- app identity/credentialsはapp-own versioned record、FileLock、checksum、atomic move。不正recordを上書きして成功へ変えない。
- ログscope v2はpadded libc/DEBUG tagを解析。crash dump PIDは当該研究PIDのheaderで照合しforeign dumpを除外。旧captureのVerifyはscope v1で保存互換。
- JWTの署名・issuer・subject・expiry、foreign password拒否、本文改ざん、不正JSON等を実Javaで検証。これらは基地到達の代用にはしない。
- 本人スマホへの移行で初回起動だけでは検出できないpassword refreshと初期MAX後の台帳不一致を修正した。資格情報更新と所持品の増減を回帰対象とし、SAVE削除・再補充は行わない。[実機受渡し記録](2026-10-12-owner-phone-handoff.md)と[継続台帳](failure-repair-history.md)を参照。

## 継続条件

起動障害の調査は原作戦闘への進行で次段階に移った。最新所有者指定に従い基地へ戻る追加試験を前提にせず、LEVEL/MAX・まどか・ゴジラの実装と必要な自動検証を進める。全体の直接プレイ試験は所有者が担当する。運営制作ツールは将来予定として既存ロードマップに残す。

その後のプロフィール・PC-only戦闘adapter統合、最終検証と本人操作の手順は[PC統合記録](2026-10-12-pc-native-balance-adapters.md)を参照する。本書のboot限定試験を全機能のゲーム受入に読み替えない。
