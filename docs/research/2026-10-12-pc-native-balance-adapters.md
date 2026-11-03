# PC専用のまどか・シンゴジラ統合と本人検証

2026-10-12の最新所有者指定を優先する。LEVEL / MADOKA / GODZILLA / OFFLINEの実装候補を同じ原作JP15.7.1の6-split研究APKへ統合した。原作タイトルから戦闘へ進む起動障害は解消済み。基地への戻り試験は不要。自動検証と本人によるゲーム内受入を区別し、実装候補の受渡しで今回のgoalを終了する。運営制作ツールは既存ロードマップの後続予定である。

## 初期プロフィール

`pc_initial_profile.py`と`pc_profile_install.py`はPC専用の原作生成SAVEを形式・JP hash・バイト完全roundtripで検証する。旧固定オフセットのSAVE配置を流用しない。外部の私的なBCSFE-Python 3.6.0はcommitとtree SHAを固定し、読込み時のsocketを禁止する。

- 日本編1〜3章・未来編1章のみ、48ステージずつクリア・最高お宝。SAVEの章indexは0/1/2/4。他の章、レジェンド、イベント履歴は不変。
- 元の835体の入手可能集合からステージ専用報酬158体を除外し、677体を所持。指定章の報酬であるヴァルキリー・ムートは含む。所持はフォーム進化や本能の解放を意味しない。
- 育成上限は原作`unitbuy.csv` col18 + 保存されたbase incrementとcol50の小さい方。元835体の上限分布は1:8 / 20:11 / 50:493 / 60:323。伝説レア18体は50。現在レベル・＋値・フォーム・本能を一律変更しない。ネイティブgetter `0x53b2bc` の対応命令と保存読込み経路を静的照合する。
- 既存20区分の資源MAX表を適用する。XP=99,999,999、NP=9,999、素材・アイテム・各種チケット等を含む。ネコカン45,000は従来の暫定研究値であり、公式上限の確認済み値ではない。指定外のお宝は対象外。
- 専用SAVEのバックアップ、SHA、停止確認、fsync、guest SHA、所有者/SELinux、atomic publication、復旧journal、プロセス間lockを使う。一度適用した後は`PC_PROFILE_ALREADY_APPLIED_NO_REFILL`となり、消費後に補充しない。

## 原作素材への最小差分

`-LocalBoot -Balance`のPCビルドのみ、DownloadLocalに固定9エントリーを追加する。元6エントリー・DataLocal・対象外行とフォームは完全保持。敵550_eの7ファイルを本人所有素材から味方702_fへ変換し、画像等をGitへ格納しない。

| 対象 | 固定仕様と接続 |
|---|---|
| No.289 / asset288 / form2 | Lv30で元growthの11,200 × 指定最高攻撃お宝2.5 = 28,000。感知750、元遠方範囲/能力/死亡演出保持。日本編2章基準4,550円、再生産基準4,650f |
| No.703 / asset702 / form0 | 敵シン・ゴジラrig、感知2,950。Lv30 growthの丸めを19,999→20,000に限定補正し、指定お宝で50,000×3。第2形態は不変 |
| ゴジラの時刻 | 元敵テーブルの攻撃開始130/170/210fに一致。元頻度処理の241fにより、通常連続攻撃の最終hit210 + 間隔241 − 1 = 450f。停止/KB等は原作処理 |
| ゴジラの価格/再生産 | 日本編2章基準9,800円、再生産基準15,000f。原作の本能・コンボ・ステージ個別処理は後段に残す |
| ゴジラの敵城ダメージ | 実敵城へのpending damage加算箇所で、各個体の三段攻撃につき最初の正ダメージを1、残りを0。最初の段が空振りの場合や複数個体も独立に扱う |

approved-v2は元敵rigに合わせたCSV timingを含む。旧approved-v1は削除せず保持する。CSVだけではLv30のゴジラが49,997に丸められ、初期研究Lv0では再生産基準にもならないため、以下の限定adapterを加えた。

再生産の基準値は対象2フォームで固定する。元research差分をこの基準まで補正し、原作の本能、研究コンボ、最小60f、ステージ上書きは維持する。他のフォーム/キャラの研究効果には介入しない。指定数値は原作の戦闘補正をすべて無効化する意味ではない。

## PC-only native adapter

`KNEEKURA_RESEARCH_PC_BALANCE`はdefault OFF。隔離PCパッケージとPC JNI observerが必須で、通常研究版/スマホ版の元.text完全保持ゲートは維持する。原本native SHA256 `333d2974...` / BuildID `8cb381...` を固定する。

| 原作source VMA | 元命令 | 接続内容 |
|---|---|---|
| 0x99c4e0 | TBZ w23 | 成長計算後・お宝等の前のゴジラ限定補正 |
| 0x5e5178 | BL 0x99833c | 敵城への最終damage加算前に合計1へ制限 |
| 0x990f54 | STR w19 | 元frame setterを1回実行し、攻撃frame0でbudgetを更新 |
| 0x8ee878 | BL 0x990f1c | 元spawnのside/slot/unit/formを記録 |
| 0x99cb94 | LDR w22 | 対象form0の元頻度値を241へ |
| 0x99ce18 | MUL w25 | 指定2フォーム・日本編2章のみ基準価格+100円 |
| 0x488b78 | MADD w8 | 同じframe pointerの対象queryだけ再生産基準を補正 |
| 0x488b30 | BL 0x99d088 | 元queryのunit/formをframe pointer別に記録 |

各adapterはx0〜x30、Q0〜Q31、NZCV、SPを保持し、置換したload/store/MADD/MUL/callを1回だけ実行する。独自RX4,096 bytesとRW GOT importだけを追加し、元8語を戻した.text SHA256 `c696e730...`の一致を要求する。RX全byte再生成、branch先、importのundefined GLOBAL FUNC DEFAULT、GOT0、重複relocation、元export、LOAD permissionsを照合する。

ゴジラの同時個体・spawn再利用・空振りを区別する。未知のwave/surge遅延generatorを検出した城攻撃はfail closedで0とし、上限超過を許さない。元form0のCSVとtalent条件では当該generatorは0。城HPを後から書き戻す処理は使わない。

ShadowHookはARM変換下でstatus12が残るため、このadapterはShadowHookに依存しない。PC observerのみ、既知markerを持つ唯一の追加RXと8分岐を認める。元実行LOAD一本、原作BuildID、17anchors、唯一のuniform rebaseを引き続き要求し、未知RXは拒否する。

## 長期ログとPC操作

`pc-native-balance-v1`は8接点のcall件数・castle credit/zero・遅延generator拒否・query容量拒否の12集計値だけを記録する。SAVE・ファイル内容・アカウント情報を出さない。`CAPTURE.json`へ保存し、`Verify`で元ログから再集計。未観測は0と断定せず不明とする。counterは実プレイ受入の代用ではない。

`PC-LAB.ps1 -Action Play -ObserveSeconds 1800`は専用AVDに限定してscrcpy画面を開き、同じ起動の全logcat buffers、PID、UTC、ビルド/ソースZIPとSHA、定期PNG、当該PID/期間のcrash/ANRを30分取得する。300秒超の画像間隔は60秒。原作SAVEを初期化・補充しない。通常の再生開始のため専用アプリだけを一度停止/再起動する。

viewerは公式Genymobile/scrcpy v5.0.1のwin64 ZIPをSHA256 `b12a2c4ee8be317422451fc7dcf8ee20a71b5ea7ef9ad73ddd825a25316227a5`で固定する。ZIPとインストール全ファイルの集合/byte一致、symlink/junction拒否を起動前に確認し、追加DLLも拒否する。clipboard同期とaudio転送は無効。専用GUIの操作に承認・パスワード・スマホ接続は不要。

## 自動検証と未受入の境界

- Windows全体768テスト実行、756成功・12skip・失敗0。関連18テスト成功。agent terminal self-test成功。
- 実NDK ARM64 shimをUnicornで実行し、8adapter全register/displaced命令、C dispatch、三段/空振り/複数個体/再利用、対象外フォーム、query frame分離、ELF tamperゲートを検証。私的fixture指定で11テスト成功。Unicornはprivate test venvに限り、APK/通常toolingへ新規依存を追加しない。
- APK `20261011T231838Z-2676f172` / capture `20261011T232012Z-6b9d3b78`は20秒の起動ログ取得完了、errors空、Java fatal0・SIGSEGV0、JNI attachment/元GL帰還あり、保存証拠Verify成功。戦闘接点counterは未実行の0であり、この起動だけで実ダメージ/育成/描画を合格としない。
- 最終reviewの追加DLL拒否指摘を修正し、P1/P2なし。最終候補のbuild/capture ID・SHAと受渡しはPC出力kitのreceiptを正とする。

本人確認は、指定章/宝・対象キャラ/除外報酬・育成個別上限・資源、まどか第3形態とゴジラ第1形態の実戦を確認する。まどかの進化前やレベル30未満では指定Lv30値にならない。新規6-splitだけを他端末へ入れてもこのPCの初期SAVEは移動しない。スマホへの移行・端末別動作・イベント全経路の受入は今回の本人PC検証の後に扱う。
