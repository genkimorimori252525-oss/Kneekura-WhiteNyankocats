**2026-10-13 更新002再導入完了:** 所有者はキャッツアイ方式への変更とバックアップ後の研究データ初期化を明示承認。旧456ファイルの完全私的バックアップ後、自身UIDからOS初期化、実署名一致の6split更新、非fixture初期443ファイルの全source/TAR/phone SHA移行を完了。初回起動前SAVEはPC初期profileと完全一致。スマホ起動と原作基地背景を確認。起動後の読み取りSAVEには2体のLv60／消費履歴があり、追加clear・再起動・プレイ試験は本人の終了指定に従い行わない。[更新002](../updates/2026-10-13-update-002-catseye-evolution.md)。以下の新規導入／更新001データ保持手順と件数は当時の履歴。公開`deploy-new`／`resume-empty`は既存SAVE上書き・clearを導入せず、承認済み今回のclearは私的helperで実施した。

# 本人のUSBスマホへのPC候補受渡し

所有者がPC検証済み候補をスマホでプレイすると依頼した。今回だけ本人のUSB接続ARM64/Android12端末を受渡し先に使用し、通常の開発/更新/長期デバッグはPC専用AVDを継続する。CoSは使用しない。原作公式`jp.co.ponos.battlecats`と公式SAVEは対象外。

## 同じ性能と別の表示名

`phone_manifest.py`は検証済みPC候補のmanifestへdebuggableと任意の表示名だけを追加する。スマホ上の表示名は「にーくらホワイトにゃんこ」、packageは既存の隔離`jp.kn.local.battlecats`。root不要のrun-asでアプリ自身のprivate領域へ配置できる。APKの他の全payloadをentry/byte照合し、同じPC開発署名を使用する。PC候補のnative 8 adapters、CSV/rig、原作テキスト復元ゲートとローカル公開鍵は変更しない。INTERNET権限はない。

アルティメットまどか第3形態の計画値はLv30・指定最高攻撃お宝で28,000、感知750、日本編2章基準4,550円、再生産基準4,650f。原作の遠方範囲/能力/専用死亡演出と対象外フォームは保持する。ゲーム内の本能/コンボ/ステージ補正は元処理であり、指定値は全補正の無効化ではない。本人の実戦受入は別である。

## 新規導入の安全条件

現在のAndroidユーザーのpackage一覧だけでは不十分だった。過去の研究版が別のAndroidユーザーに残り、package全体の署名で新しい開発署名との不一致になった。現在のユーザーでは未インストールでも`INSTALL_FAILED_UPDATE_INCOMPATIBLE`が発生する。全体`dumpsys package`も検査する回帰テストを追加した。

所有者が「削除していいよ」と明示した後に、古い**研究packageだけ**を全ユーザーから削除した。自動のclear/uninstall/既存署名上書きはhandoffツールへ組み込まない。公式アプリのインストールpathを前後で照合し、そのdataにはアクセスしない。serialを公開ソースへ固定しない。

`phone_handoff.py prepare`はPC6-splitの出所/各SHAからmanifest変更と同じ開発署名を検査する。`deploy-new`はglobal package不存在が必要。`resume-empty`は同じ候補6-splitの完全SHA一致、run-as可能、既存SAVE不存在が必要で、再インストールしない。端末のrootを要求しない。

## 状態と素材の転送

元PC研究アプリを共用lock下で停止し、独立ローカル`files`と`shared_prefs`だけを読み取る。元スマホSAVEの解析/移行は行わない。初期MAXの再適用もせず、PCでの現在の消費/進行をそのまま移す。

- private host workspaceをowner-only ACLで作り、ADBが長いファイル名を扱えるよう短いpathにする。
- 大きな一括stdout exportの不完全取得と、通常の圧縮pullでの失敗を検出した。`pull -Z`で個別ファイルを取得し、元PCファイルの全SHAと照合する。
- TARを検査して許可rootを`files/shared_prefs`に限定し、absolute/traversal/symlink/hardlink/正規化重複を拒否、件数/総容量も制限する。host private状態にはキーが含まれるため公開成果物へ入れない。
- phone側はrun-asのunique private stageにファイル単位でASCII base64 stdinを渡す。共有tmpやDownloadへ状態を出さない。stage/filesとstage/shared_prefsは空でも事前作成する。
- stage全SHA一致後、app停止とtarget空を確認して`mv -T`で公開し、公開後の全SHAも検査する。既存の非空targetを消去しない。公開は2ディレクトリ間の単一transactionではなく、電源断時の完全な原子性は未保証。

## 検証と証拠

manifestの実package属性・raw/typed一致/一意性、UTF8/UTF16 pool、表示名、TAR範囲・リンク・重複、別ユーザーのpackage保持のテストを実行。7関連テスト成功。最終775件全体テストは763成功・12skip。実Java3テスト、Agent terminal validation、独立レビューも成功し、P1/P2指摘なし。

本人用成果物はPCの`outputs/phone-play-2026-10-12`へ保存し、最新の導入・起動結果は同kitのreceiptを参照する。APK ZIPは6分割一式で、秘密鍵/SAVE/生ログを含まない。ZIPを開くだけで他端末へ同じ初期状態が作られるわけではない。実戦/描画/育成の最終確認は所有者が行う。

## 起動停止の原因と修正

移行後の原作scene97では35スロットがzero、DownloadBatchTask完了、後続CreateAccountTask未完了だった。Wi-Fi不良や素材欠落とは判定しない。独立ローカル時刻応答の帰還後、`auth-password`が拒否されていた。

1. **既存アカウントの資格情報更新が未対応。** 初回register/tokensは通っていたが、原作の後続起動は`POST /v1/user/password`を要求する。固定JP15.7.1の要求生成`0x32e6b0`と応答解析を私的に確認し、`accountCode/passwordRefreshToken/nonce`の厳密な3フィールドを検証して独自ローカル資格情報を再発行する処理を追加した。実機でrefresh-password→tokensの応答受理と原作保存処理の帰還を確認した。今回のログだけから「JWT期限切れが更新要求の唯一の原因」とは断定しない。
2. **MAX化後のSAVEと旧所持品台帳が不一致。** 旧managed処理は初回スナップショット以外の差分を拒否し、プロフィール変更後の起動に対応できなかった。ローカルJWT・`isPaid=false`・4量の厳密な集合/非負int範囲を検証し、正当な現在量をFileLock/fsync/atomic replaceで保存する。旧台帳はowner・checksum・構造・int範囲を検証し、不正な台帳は上書きしない。SAVEの変更、自動補充、未知の有料要求の受理は行わない。

資格情報は応答喪失やPCからの状態コピーで不一致にならないよう冪等に再発行する。原作nonce/RSA検証、`Nyanko-Signature`、ローカルoriginを保持する。実Javaテストで署名、nonce、異なるID/token、不正JSON/重複/未知フィールド、method/URL envelope、所持品増減、破損台帳の保持を検証した。

## 実機結果と保証範囲

- 最終PC元候補：`20261012T062624Z-7cdc7c13`。スマホ6-split：`phone-20261012T062758Z-2583a0e9`。監視ライブラリ名を変えた診断候補は不採用で、通常のShadowHook構成を復元した。
- 初回転送450ファイルの全SHA一致。最終同署名更新前後453ファイルの全SHA一致（起動中に原作が作成したファイルを含む）。公式package path保持、スマホroot不使用。
- スマホ採取`20261012T062855Z-c32c4878`は30秒区間のJava fatal0/研究SIGSEGV0、原作SAVE読み取りaccepted。短時間採取末尾は画面遷移中で、単独では操作可能性を証明しない。
- その後、所有者が「うまくいった」と直接確認。研究アプリが前面であることを確認した読み取り専用観測でも、原作パワーアップ画面、Lv11の表示、所持XPとネコカン45000を確認した。画面・端末ID・アカウント・生ログはGitHubへ公開しない。
- PCの同修正版採取`20261012T062915Z-8572ddac`も20秒完全採取と保存証拠再集計Verify成功。本人のスマホ操作は停止/初期化しない。

これはスマホ起動・操作画面の到達確認である。全キャラのLv60 UI、まどか/ゴジラの全戦闘条件、長時間再起動、SDK/IPC全経路のゼロ通信を一括して合格とはしない。通常開発はPC専用AVDを継続する。

## 次の運営での確認順

1. `CURRENT.md`の最新欄と[失敗・修復台帳](failure-repair-history.md)を読み、採用候補のbuild/source/archive/6-split SHAを照合する。
2. 起動停止はscene/taskと要求分類・応答帰還で切り分ける。35zero、プロセス生存、30秒の無例外だけで成功としない。
3. 初回登録後の冷起動、資格情報更新、初期MAX後・所持品消費後の再起動を受入項目に含める。台帳不一致をSAVE削除やMAX再適用で隠さない。
4. 実機は自己研究packageのrun-as/JDWP/LLDBだけを使用。必要なnativeデバッグはINTERNETなしでもAF_UNIX abstract socketで可能。`debuggerd -b`のroot要求を迂回しない。通常開発の入口は`PC-LAB.ps1 -Action Play`と`-Action Verify`。
5. 詳細ログの収集先はprivateファイルを使い、長時間の未読stdout PIPEで収集器を詰まらせない。集計と本人の操作可能な画面確認を別々に保存する。

本件は本人用の私的候補更新で、公開ゲーム用の運営お知らせ配信は行わない。旧独立Alphaのnotice/catalogへの未検証な配信も行わない。修正の公開記録は本書・台帳・PRに集約する。
