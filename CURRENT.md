# CURRENT.md — にーくら大戦争 唯一の作業入口

**ACTIVE / 初めてのセッションでもこのファイルから始める。** どの開発エージェントも設計書を片っ端から読んで「本当の原則」を探してはいけない。設計の下位文書は実装時の参照資料であり、プロダクトを変更する権限を持たない。

## 現在の作業位置

**[親Issue #11 — 実装進捗](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/11)** が唯一の「いま何をしているか」の入口。**直近の次のコード差分は [#12 LEVEL — 本家育成画面のレベル上限](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/12)**。**[#15 OFFLINE — 元ゲーム保持＋通信ゼロ](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/15)** は同時進行。次に **[#13 MADOKA](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/13)**、**[#14 GODZILLA](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/14)**。この順序・実装担当のために新しい基本計画を作らない。

## 原則の優先順位（不一致ならこの表で決定）

| 優先 | 原本 | 説明と変更権限 |
|---|---|---|
| 0 | **オーナーの最新の明示的な指示** | 本家『にゃんこ大戦争』のゲーム体験が必要。別ゲーム・簡易Alphaは不許可。仕様変更はオーナーの明示指示だけ |
| 1 | [PRODUCT_IDENTITY.md](PRODUCT_IDENTITY.md) | **製品とは何か/何ではないか**の絶対条件。本家のシーン・UI・アニメ・戦闘・キャラ/ステージ/ガチャを忠実に保ち、外部通信もゼロ。2軸とも必須 |
| 2 | **この CURRENT.md** | どれを読むか、どの計画を実行するか、過去の矛盾をどう扱うかを一元管理 |
| 3 | [実装中の単一ロードマップ](docs/roadmap/2026-10-09-original-battle-cats-delivery.md) | **いまやる順序と、各成果物・受入テスト**。レベル→まどか→ゴジラ、完全オフラインは並行。この文書以外に並列の「current roadmap」を作らない |
| 4 | [1.01数値原本](docs/updates/manifests/update-1.01.json)、[受入ゲート](docs/architecture/product-identity-gates.json) | **ユーザーが承認した数値・状態と実証条件**。前者 `PREVIEW_ONLY_NOT_INSTALLABLE` は実装完了を意味しない |
| 5 | [AGENTS.md](AGENTS.md) | **コード作業/検証/Windows配布の手続き**。製品の意味やゲームの仕様を変更できない |
| 6 | 1次証拠・過去の文書・研究ハーネス | 特定タスクの技術参照**だけ**。本表の上位と矛盾した内容は旧設計/研究履歴として扱う |

## オーナーWindows開発環境 — 実測固定パス（2026-10-11 明示依頼）

**以後すべてのAI・Codex・端末案内で先に参照する。** オーナーが繰り返し提供した既存環境。環境構築のために勝手に別のSDKや仮パス `C:\\PATH\\TO` を指示しない。実機は接続状態が変わるため、毎回動的に確認する。本人が環境を変更した場合はこの節を更新する。

| 項目 | オーナー環境での場所・実測 |
|---|---|
| Windowsユーザーフォルダ | `C:\\Users\\genki` |
| Android SDK **正本** | `C:\\Users\\genki\\AppData\\Local\\Android\\Sdk`（PowerShellは `$env:LOCALAPPDATA\\Android\\Sdk`） |
| Android ADB **正本** | `C:\\Users\\genki\\AppData\\Local\\Android\\Sdk\\platform-tools\\adb.exe`（ADB 37.0.0 動作確認済み） |
| Android build-tools | **34.0.0 / 36.1.0 / 37.0.0** で `zipalign.exe`、`apksigner.bat`、`d8.bat` が存在することを実測。**35.0.0** も2026-10-11 `sdkmanager "build-tools;35.0.0"` で追加され、専用ビルドスクリプトの `zipalign.exe` / `apksigner.bat` / `d8.bat` 存在チェックを通過して**keytool署名鍵作成のパスワード画面まで到達済み**（実行ログが根拠） |
| Android API 35 | `C:\\Users\\genki\\AppData\\Local\\Android\\Sdk\\platforms\\android-35\\android.jar` 存在確認済み |
| SDK Manager | `$env:LOCALAPPDATA\\Android\\Sdk\\cmdline-tools\\latest\\bin\\sdkmanager.bat`。SDK XML v3/v4の警告は一度観測（終了後は実ファイル・終了コードを確認） |
| GitHub作業リポジトリ | `C:\\Users\\genki\\Downloads\\Kneekura-WhiteNyankocats`（`CURRENT.md` と `tools\\base_mod\\build_owned_static_http_bridge.py` 存在確認済み） |
| **所有原本JP15.7.1 ZIP** | `C:\\Users\\genki\\Downloads\\にーくらにゃんこ\\nyanko_battlecats_2026-10-06.zip` |
| 原作Android実機研究キット | `C:\\Users\\genki\\Downloads\\kneekura-original-owner-trial-kit`（`BUILD-ORIGINAL-RESEARCH.ps1` 存在確認済み） |
| Python | `py -3.12`、`lief==0.17.6` と `pycryptodome==3.24.0` インストール済みの本人出力 |

**AIが出すコマンドの最小規則：** PowerShellから `$sdk = Join-Path $env:LOCALAPPDATA 'Android\\Sdk'`、`$adb = Join-Path $sdk 'platform-tools\\adb.exe'` を使用。通常は `$repo = Join-Path $HOME 'Downloads\\Kneekura-WhiteNyankocats'`、`$zip = Join-Path $HOME 'Downloads\\にーくらにゃんこ\\nyanko_battlecats_2026-10-06.zip'`、`$kit = Join-Path $HOME 'Downloads\\kneekura-original-owner-trial-kit'`。**研究版をビルドする時は `-RepositoryRoot $repo -OwnerExportZip $zip -PublicKitDirectory $kit` を必ず指定**する。カレントディレクトリだけでリポジトリを決定しない。 `zipalign.exe` はBuild-toolsの実在版を事前確認し、必要な35.0.0がなければバージョンを確認して追加インストールを案内。

**実機安全条件：** `adb devices` が空なら端末を再接続しUSBデバッグ認証を確認する。過去に`device`表示があっても、接続中と断定しない。端末固有シリアルは永続記録しない。原作公式アプリ `jp.co.ponos.battlecats` / 元SAVEは `uninstall` / `pm clear` / 上書きの対象にしない。実験対象は別パッケージ `jp.kn.local.battlecats` のみ。**2026-10-11 実機更新（所有者の一次端末ログ）：** 元JP15.7.1の別パッケージ `jp.kn.local.battlecats` を原作6分割APKでビルド・署名し静的検証PASS。新規インストールで `adb install-multiple --no-streaming` は **`Success`**、`adb shell pm path jp.kn.local.battlecats` で6分割すべて検出。`adb shell am start -n jp.kn.local.battlecats/jp.kn.local.battlecats.MyActivity` は起動リクエスト受理（`Starting`）したが、**端末画面は黒のまま**。初回読み取り専用観測 `py -3.12 -m tools.base_mod.collect_original_local_first_boot --output private/original-first-process.json` は **`read-only adb command could not finish`** で停止し、元アプリが実際に動いたこと・本物の初回SAVEが生成されたことは未証明。**絶対に「起動PASS」「PLAYABLE」と宣言しない**。既存の公式アプリとSAVEを消さない。次に行うこと：現在接続中のPID/Android Activity状態と、`KNEEKURA_STATIC_HTTP` 固定タグのlogcatをADBで安全に診断する。端末シリアルは恒久保存しない。パスワード・秘密鍵をコミット/チャットに提出しない。

### 2026-10-11 追跡更新 — 黒画面の実ログ、ShadowHook補助ライブラリと次の実機ゲート

- 本人の `20261011-040424` プライベートlogcatを研究用パッケージID/PIDで再集計し、**研究版プロセス起動86、死亡85、`original-native-scene-hook-v1 hook-initialization-failed` 85**を確認。古い「87/87」には無関係な他アプリ起動が混入していたので訂正。SIGSEGV履歴と具体的な終了バックトレースの因果はまだ特定できていない。公式元ゲームの起動・SAVE生成・Lv60は未合格。
- 原因候補の一つとして、旧研究版へのShadowHook 2.0.1 `libshadowhook.so` だけの同梱漏れを発見。現行PR#4では公式Maven AAR 1個から `libshadowhook.so` と `libshadowhook_nothing.so` を**両方必須**とし、AARと個別のSHA-256、原本ARM64実行命令を検証する。公式ヘッダーのinit UNIQUE=1 / hook UNIQUE flag=2は正しい。**ライブラリの同梱修正は静的CI PASSで、黒画面の実機修復PASSではない。**
- 次の所有者PC側作業は `tools/base_mod/BUILD-OWNER-RESEARCH-PAIR.ps1` による**既存研究用署名鍵・CIのPASSIVE（virgin SAVE writer OFF）ARM64 `libkneekura.so`＋SHA受領書・本人ZIP・公式ShadowHook 2本**でのソース保全付き6分割再ビルド。署名パスワードはコマンド引数に載せず、プロセス内で一時的に環境変数へ渡して終了時削除する。署名/ソース一致を満たさなければ中断。
- このビルドと端末アップデートは別工程。実機上の研究版 `jp.kn.local.battlecats` の実際のインストール済み証明書と候補6本を `tools/base_mod/CHECK-OWNER-RESEARCH-DEVICE-SIGNER.ps1`（内部の `preflight_original_device_update.py`）で**読み取り専用照合**するまで、`-r` インストールはしない。さらに候補 `libkneekura.so` はCIコンパイル済みの `PASSIVE_SHIM_BUILD_SOURCE_RECEIPT.json` のSHAと一致必須。
- それらのゲートが実機で通った場合だけ、本人が明示的に選んで研究版6分割を上書き更新し、`CAPTURE-OWNER-ORIGINAL-CRASH.ps1` で研究版を1回のみ起動、`summarize_original_crash_capture.py` で機密抜きの集計JSONを生成する。古い単独ShadowHook研究キットを再実行しない。**公式 `jp.co.ponos.battlecats` やSAVEの削除・再利用・H01/BAN回避なし。** 具体的なコード/テストと成果は既存 [Issue #12](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/12) に一本化。

### 2026-10-11 続報 — Android実ツール署名確認と更新実行の安全な単一ゲート

- **合成ではあるが実Android SDKによる実署名が成功。** `.github/workflows/real-apksigner-env-smoke.yml` はWindows/Linux両方で `aapt2` による合成APK生成、`zipalign`、実`keytool`の一時秘密鍵、`apksigner`による原作と同じ6分割名の署名/検証を実行。パスワードの`env:`渡しと内容保持を検証、元ゲームAPK・公式SAVEは未使用。[実SDK検証](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/actions/runs/38083892128) 両OS PASS。ただし所有者実キーでの原作ゲーム署名・実起動ではない。
- **本人が明示承認した場合だけ研究版を6分割で1回更新する実コード**：`tools/base_mod/INSTALL-OWNER-RESEARCH-PAIR.ps1` → `tools/base_mod/update_original_isolated_research.py`。既存 `preflight_original_device_update.py` による本人端末に現存する**研究用パッケージだけ**のread-only署名/ネイティブ証明確認に合格後、研究版が動いておらず同じUSB端末・6本ハッシュが維持されている時だけ `adb install-multiple --no-streaming -r`。失敗・タイムアウト時は自動再試行せず、公式アプリやSAVE領域へ介入しない。再インストール・初期化・署名違いでの置換をしない。
- **更新後の実バイト照合**：署名一致だけではShadowHook修正がインストールされた証拠にならないため、privateの一時領域で研究版の`base.apk`と`split_config.arm64_v8a.apk`を読み取り、新候補とSHA-256一致を要求（残り4分割は導入確認・署名検証のみ）。一時コピーは削除、出力レシートには端末ID/証明書/SAVE/APK本文を保存しない。実機での同一鍵ビルド・更新・起動はいずれも **OWNER_GATE / 未実施**。
- 実Android署名のCI成功＋合成ADB更新テストは、**原作の黒画面解消・初回SAVE・Lv60/MAX・運営i/まどか/ゴジラ/完全オフラインの受入PASSではない**。次の現物試験は本人Windowsで既存研究用署名鍵を使い`BUILD-OWNER-RESEARCH-PAIR.ps1`により原作所有ZIPからPrivate候補を作り、read-only signer gateを通過後にのみ本人の明示操作で更新・一度だけログ採取。旧一個だけのShadowHook `.so`を含むトライアルを再実行しない。

### 2026-10-11 Windows実測・原作所有ZIPから署名前6分割再構築PASS（秘密情報非公開）

- **接続済み Chat On Steroids Core で本人のWindowsローカル環境を実行検証。** 保護対象 `C:\\Users\\genki\\Downloads\\Kneekura-WhiteNyankocats` は現行 `jolly/balance-madoka-godzilla-2026-10-09` にfast-forward、作業ツリーを清潔に維持。Windows Python 3.12.10 で `unittest discover -s tests -p test_*.py` **640件実行、633成功・7スキップ・0失敗**。GitHub公開Linux側も同じソースで [Test tooling #38087269968](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/actions/runs/38087269968) **640件／639成功・1スキップ**、[Agent terminal #38087269990](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/actions/runs/38087269990) PASS。
- Windows固有に実測された不具合3点を修正済み：`tests/test_base_preserving_repack.py` のPythonシバン実行がWinError 193→`.cmd`起動、`tools/localcore/opsctl.py`のcp932 UnicodeEncodeError→ASCII-escaped JSON（`json.loads`で元日本語完全復元）、NTFS大文字小文字同一ファイルへの同名二重manifest試験→同一inode/ケースfold対応。CIだけでなく**実Windowsで再検証PASS**。
- 本人Windowsで公開SDK35（`aapt2`/`zipalign`/`apksigner`）＋Android Studio同梱JBR `keytool` を用い、**一時的な合成6分割APK・一時鍵のみの実署名6/6 PASS**。所有者鍵・公式アプリ・SAVEを使用しない。検証プログラムは `tools/base_mod/ci_real_apksigner_env_smoke.py`。`keytool.exe`がPATHになくてもインストール済みAndroid Studio JBRから検出する。
- 本人の所有ZIP SHA256 `38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56` を**一切変更せず実際に読み込んで**、新規 `tools/base_mod/prepare_original_research_presign.py` で秘密鍵・ADBなしの原作JP15.7.1研究版6分割APKを構築。GitHub Actions [native scene研究用PASSIVE ARM64成果物 #38079740747](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/actions/runs/38079740747) のSHA受領書と実`libkneekura.so`を照合し、同じ公式ShadowHook 2.0.1 AAR（Main + `nothing` 2本のSHA固定）を使った。`verify_staged_original_scene_before_signing`が `PINNED_REPACKAGED_JP1571_ORIGINAL_SCENE_VMA_AND_EXPORT_VERIFIED`、原作vs研究版の`verify_static_http_bridge`・通信権限なし・ネイティブの静的合格、**6つの署名前APK SHA256を個別にgitignored `private/`のJSONへ記録**。原作の6分割APKと派生バイトはGitHub/チャットに出していない。
- **合格したのは署名前、かつ静的原作コード保全まで。** 現物研究版は `Android_APK_signed=false` / `Android_game_installed_or_launched=false`。元原作UI表示・黒画面解消・初回本物SAVE・育成Lv60/MAX・操作i/ガチャ/運営・まどか/シンゴジラ・真の外部通信ゼロはいずれも**実機受入未合格**。次に必要なオーナー側操作は、本人の秘密研究用署名鍵のパスワード入力を伴う候補署名と、実機上の現存署名一致を読み取り確認した後の**明示的な**研究版更新／1回の収集。本人の許可なしに署名・端末上書き・SAVE変更はせえへん。
- 再現・検証の一次ソースは既存 `tools/base_mod/BUILD-OWNER-RESEARCH-PAIR.ps1`、`CHECK-OWNER-RESEARCH-DEVICE-SIGNER.ps1`、`INSTALL-OWNER-RESEARCH-PAIR.ps1`、`CAPTURE-OWNER-ORIGINAL-CRASH.ps1`。追加の署名前工程・合成テストは `prepare_original_research_presign.py` と `tests/test_prepare_original_research_presign.py`。旧ShadowHook単独`.so`トライアルに戻さない。

### 2026-10-11 OWNER-READY — 署名ビルドだけ本人操作へ移管できる状態

- 本人Windows privateに**原作JP15.7.1の署名前6分割APK（実物約166MiB、6/6個別SHA記録）**、公式ShadowHook 2本入りAAR、GitHub実NDKコンパイルのPASSIVE `libkneekura.so`＋公開SHA受領書を配置済み。原本ZIP・元SAVE・公式アプリは一切書き換えず、派生APK/秘密鍵の本文はGitHubへ出していない。
- 新しい **`tools/base_mod/OWNER-READY-TO-SIGN.ps1`** は本人PCで実行確認済み。**既定は読み取り専用**。実原本SHA、補助AAR SHA、実コンパイルCライブラリSHAとancestor、既存研究用署名鍵ファイルの存在、以前の署名済み研究用`base.apk`（読み取り専用実`apksigner verify`）、原作6分割の静的命令保持PASSを確認し、`OWNER_PRIVATE_ORIGINAL_BUILD_INPUTS_READY_NO_DEVICE_OR_KEY_USED`と表示。Javaの無害なstderr警告をPowerShell5.1が致命的エラーにする不具合も修正し、アプリ更新・署名・パスワード取得なしの実Windows検証PASS。
- **次の本人が必要な最小操作（現時点では未実施）：** `powershell -NoProfile -ExecutionPolicy Bypass -File "$HOME\\Downloads\\Kneekura-WhiteNyankocats\\tools\\base_mod\\OWNER-READY-TO-SIGN.ps1" -DoBuild` を本人のPowerShellで明示的に実行し、**既存研究用の署名鍵エイリアスとパスワードを端末内だけで入力**。これでも署名候補を作るだけで端末へは入れない。次に別のread-only installed signer gateを通り、本人承認の1回の原作研究版更新＋実機クラッシュ観測。チャットへパスワードやAPK/SAVEを送らない。
- 新規ソースのテストも含む**本人Windows Python3.12.10の641件実行、634 PASS・7 skip・0 failure**、GitHubの [Test tooling #38087627686](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/actions/runs/38087627686) および [Windows/Ubuntu #38087627670](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/actions/runs/38087627670) PASS。**実原作アプリの初回起動・本当のSAVE/LEVEL/MAX・運営・まどか/シンゴジラ・完全通信ゼロはまだ未検証**。PR#4はDRAFT。
- 技術原因と引継ぎは親 [Issue #12](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/12) に記録。別系統Alphaへ置換しない。

### 2026-10-11 本人署名実行ログ — `apksigner sign` exit=2、原因の前倒し分類と復旧

- 本人が `OWNER-READY-TO-SIGN.ps1 -DoBuild` を実行し、既存研究用鍵エイリアス（本人入力）とマスクされたパスワードを端末で入力した。準備段階 `OWNER_PRIVATE_ORIGINAL_BUILD_INPUTS_READY_NO_DEVICE_OR_KEY_USED` は PASS。その後最初の**研究版 `base.apk` の `apksigner sign` が終了コード2で失敗**。`tools/base_mod/repack.py::_run` がJava標準出力・エラーをバッファしていたため、過去ログだけから「エイリアス違い」「ストア/鍵パスワード違い」「JDK/PKCS12問題」のどれかは**断定できない**。**APKの署名成功・Android更新・黒画面修正は未実施**。
- 原因分類のため**既存研究用鍵を一切変更しない** `tools/base_mod/verify_original_research_signer.py` を実装。PowerShellが今まで通りパスワードを1回ローカル入力してプロセス環境変数に保持し、原作166MBのパッケージ変換や署名の**前に**JDK `keytool -list` と `-exportcert` を `-storepass:env` 方式で実行する。PKCS12ストアを開けるか、指定エイリアスが存在して公開X.509証明書を取り出せるか、その証明書SHAが従来の署名済み研究版`base.apk`の`apksigner verify --print-certs`と一致するかを検証する。出力は英数字のみの**固定安全コード**（パスワード/alias/証明書/パスそのものは表示もファイル出力もしない）。誤った鍵は**署名ビルド前に拒否**。
- `BUILD-OWNER-RESEARCH-PAIR.ps1` でこの事前検査を組み込み、**検査成功前には次の署名ビルド用フォルダを作らない**。署名ツールがさらに失敗しても `repack.py` は raw Javaエラーやpath/alias情報を例外出力せず、`RESEARCH_SIGNING_BLOCKED: ...` の固定分類コードに変換。ストア/鍵パスワードの生値をCLIに載せない旧契約は維持。
- 一回目失敗で `private/official-shadowhook-pair-passive-*` 内に署名前作業用 `base.apk` が複数残り、`OWNER-READY-TO-SIGN.ps1` の基準APK検索が `Expected exactly one ... (found 6)` で誤停止するWindows固有の現物を実測。**前回の作業フォルダを検索から除外**して、本人PCのread-only準備確認を再実行すると `OWNER_PRIVATE_ORIGINAL_BUILD_INPUTS_READY_NO_DEVICE_OR_KEY_USED` **PASS**。利用者の過去ファイルは勝手に削除していない。
- **検証**：本人のWindows Python3.12の全648テストは **641合格/7 skip/0 fail**。模擬Java/PKCS12失敗ケース（パスワード・alias・既存証明書不一致）をテスト済み。本人Windowsの実JDK17/SDK35を使う**一時合成鍵と6分割APKだけの実試験**で、keytoolの公開証明書一致／間違いaliasの拒否／Android署名を PASS。GitHub Actionsの [Windows/Linux 実Android署名＋JDK検証](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/actions/runs/38109809851) も両OS PASS（リンクのオーナーは常に `genkimorimori252525-oss`）。実鍵のパスワード自体はAIへ送らず、新しい鍵も発行しない。
- **次の本人操作**：ローカルの更新済みリポで従来と同じ `OWNER-READY-TO-SIGN.ps1 -DoBuild` を一度実行し、本人だけが研究用署名鍵のaliasとパスワードを端末入力する。最初に固定ステータス `PASS_EXISTING_RESEARCH_KEYSTORE_ALIAS_PASSWORD_AND_CERT_MATCH` が出なければ処理は止まり、**その固定エラーコードだけ**をチャットへ送ってもらう。研究版の実機インストール・SAVE・公式アプリには触れない。署名PASS後も別のread-only 実機署名照合と本人明示の単発更新が必要。

### 2026-10-11 署名事前検証のJDK実パス修正（本人Windows／keytool未発見）

- 本人の再試行 `OWNER-READY-TO-SIGN.ps1 -DoBuild -SigningAlias "252525"` はPREPAREDまでPASS、パスワードはローカル入力されたが、**実鍵の署名・証明書検査より前に** `Required owner-private file is missing: existing local JDK keytool` で停止した。**パスワード、alias、研究用キーストアが不正だという証拠ではない。** 研究版インストール・SAVEは無変更。
- Chat On Steroidsが実Windowsを検査：PATHの`javac.exe`はOracleの共通 `C:\\Program Files\\Common Files\\Oracle\\Java\\javapath` にあり、同ディレクトリに`keytool.exe`はない。既存の正本 `tools/base_mod/resolve_java_keytool.ps1::Resolve-JavaKeytool` は**既設 `C:\\Program Files\\Java\\jdk-17\\bin\\keytool.exe`**を解決でき、同階層 `javac.exe` は実測 `javac 17.0.12`。Android Studio JBRにも両ツールが存在するが、今回は既設JDK17を選ぶ。
- `tools/base_mod/BUILD-OWNER-RESEARCH-PAIR.ps1` でOracle javapath `Get-Command javac`からkeytoolの場所を推定していた誤契約を削除。`Resolve-JavaKeytool` を先に利用し、同じ完全JDK17内の `keytool.exe` と `javac.exe` をセットで、**秘密パスワード入力前に**チェック。失敗時は固定`EXISTING_JDK17_JAVAC_KEYTOOL_PAIR_REQUIRED_NO_SIGNING_ATTEMPT`、成功時 `EXISTING_JDK17_JAVAC_KEYTOOL_PAIR_VERIFIED_NO_KEY_USED`。本家原本ZIP/SAVE/署名鍵を開かない時点で実パス解決を検証。
- **検証** 本人Windows PS5.1パースPASS、実JDK17ペア解決PASS、Python3.12全**650テスト中643 PASS・7 skip・0 fail**。現行GitHub [Test tooling #38110656002](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/actions/runs/38110656002) と [Windows/Ubuntu Agent #38110656042](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/actions/runs/38110656042) PASS。**実研究用キーストアによる署名は未再実行**。本人だけが同じコマンドでalias/パスワードを端末入力して継続する。証明書と旧研究版の整合が通っても黒画面修正や実機Lv60を意味しない。

### 2026-10-11 署名鍵のエイリアス不一致 → 旧研究版証明書と一致する鍵を自動解決

- 本人の `OWNER-READY-TO-SIGN.ps1 -DoBuild -SigningAlias "252525"` は `EXISTING_JDK17_JAVAC_KEYTOOL_PAIR_VERIFIED_NO_KEY_USED` までPASS。実鍵のローカルパスワード入力後、`verify_original_research_signer.py` の `keytool -list` は成功し、その後指定の `252525` の `keytool -exportcert` が失敗して `EXISTING_RESEARCH_KEY_ALIAS_NOT_FOUND_OR_NO_CERTIFICATE` で停止。**署名成功ではない。** P12を開く段階のパスワード/形式チェックは通ったが、エイリアス不在以外の証明書取得失敗の可能性は排除しきれない。
- 新しい `verify_original_research_signer.py` は、パスワード1回を一時プロセス環境変数から読み、本物のJDK17 `keytool -list -v`（英語ロケールを固定）で **PrivateKeyEntry だけ**のaliasを列挙（件数/文字種を制限）。全候補の公開DER証明書SHA-256を、**以前から署名済みの本人の独立研究版 `base.apk`** の `apksigner verify --print-certs` 証明書SHA-256と比較し、一致が**厳密に1個のみ**の場合に限り採用する。どのalias/証明書/パスワードもコンソールやGitには出さない。0個または2個以上の一致は `EXISTING_RESEARCH_SIGNING_CERTIFICATE_NO_UNIQUE_PRIVATE_KEY_MATCH` でFAIL CLOSED。
- `BUILD-OWNER-RESEARCH-PAIR.ps1` は秘密情報なしの固定成功マーカー `PASS_EXISTING_RESEARCH_SIGNING_CERT_MATCH_ALIAS_AUTO_RESOLVED` を受け、短命な `private/transient-research-alias-*.txt` で実際の一致エイリアスだけを受け渡し、**その一時ファイルをビルド前に削除**。異常終了時もfinallyで削除する。新規署名鍵は作らず、本人の既存鍵を再利用。旧研究版と一致しない証明書を使って上書き更新する経路は許可しない。
- 前回の編集中にPowerShellスクリプト末尾が重複して構文エラーになったため、**既知の正常版 `6404db3` に戻して安全に組み直し**。本人PC Windows PowerShell 5.1の構文検証PASS。Python全**655件／648成功・7スキップ・失敗なし**、JDK/Android SDK実物＋一時合成鍵で間違ったaliasの自動解決と、異なる証明書の拒否を検証PASS。[Tooling CI](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/actions/runs/38111313012)、[Agent validation](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/actions/runs/38111312957) も現行ソースでPASS。
- **本人のP12/パスワードによる実auto-alias照合と署名はまだ未実施。** 同じ `OWNER-READY-TO-SIGN.ps1 -DoBuild -SigningAlias "252525"` を本人の端末から一度実行し、固定判定だけ確認してもらう。署名後も研究版の実機インストールは別ゲート。原作起動/初回SAVE/Lv60/MAX/i運営/まどか/ゴジラ/完全外部通信ゼロは未合格。

### 2026-10-11 本人実鍵で原作6分割署名ビルドPASS → 端末接続待ち

- **本人からの実行ログが初めて `PASS_EXISTING_RESEARCH_SIGNING_CERT_MATCH_ALIAS_AUTO_RESOLVED` と `BUILD_ONLY_PASS; PROVIDED_PREVIOUS_SIGNED_BASE_CERT_MATCHED` を記録。** 既存の研究用PKCS12を本人PCで開き、旧研究版の署名証明書と一致するPrivateKeyEntryを特定し、別鍵を作らず**原作JP15.7.1の署名済み6分割APK候補**を構築する工程が成功した。秘密のalias/P12パスワードはGitHubやチャットには記録しない。
- 本人PCの非公開成果物は `private/official-shadowhook-pair-passive-57f4daaee89e4affb0ca6cd3771cac01/local-research-static-http-signed-splits`（約166MiB・原作6本、Gitignore管理）。Chat On Steroids接続を使い、**実際の6本すべてに`apksigner verify --print-certs`をかけ、6/6 PASS、全員同一署名証明書PASS。** さらに `tools/base_mod/preflight_original_device_update.py::_candidate` の**原作コード・研究用Shim/ShadowHook2本・署名前後Parity・INTERNETなし**静的制約をPC上で再検証PASS。スマホ・SAVE・公式アプリへのADB読み書きはこの確認で未実行。
- 続く**実機にインストール済みの `jp.kn.local.battlecats`** との署名照合は、現時点で `adb devices`の認可済みAndroid端末が**0台**で止めた。**前にPCへ残っている研究版 `base.apk` と同じ証明書だとしても、今実機に入っている研究版との一致はまだ未証明。** 実機の黒画面修正や最初のSAVE/Lv60/MAX/運営/まどか/シンゴジラ/通信ゼロは未検証。署名済みビルドは原作PLAYABLE PASSではない。
- 次の本人操作はUSBデバッグ許可済みのスマホをPCへ接続するだけで十分。検査担当が `tools/base_mod/CHECK-OWNER-RESEARCH-DEVICE-SIGNER.ps1` の `-CandidateSignedSplitDirectory` に上記6分割成果物フォルダを渡し、**実際にインストール済みの独立研究版との署名**をread-onlyで確認する。異なる署名・構成不足・ADB切断はFail Closed。PASS後も別の本人承認なしに `INSTALL-OWNER-RESEARCH-PAIR.ps1` や原作ゲーム起動・Android状態変更を実行しない。今までの失敗作業フォルダや署名鍵を削除しない。
- 技術証拠と受入未完了の境界は既存Issue #12へ追記。原作GAME BOOTブロッカーの解決を優先し、別アプリAlpha/新規ロードマップを作らない。

### 2026-10-11 本人Androidで同一署名上書き成功・ShadowHook導入成功／原作scene97追加データ境界が残る

- **現物Android一台の実受入**：Chat On Steroidsのread-only `CHECK-OWNER-RESEARCH-DEVICE-SIGNER.ps1` が **`ACTUAL_INSTALLED_RESEARCH_SIGNER_MATCHED_BUILD_ONLY`** PASS。本人のこの会話での明示許可に基づいて **一度だけ** `INSTALL-OWNER-RESEARCH-PAIR.ps1 -ApproveUpdateOfIsolatedResearchApp` を実行し、元の別パッケージ `jp.kn.local.battlecats` の6分割APKを `-r` 更新。**`SIX_SPLIT_UPDATE_CONFIRMED_BASE_ARM64_BYTES_NOT_GAMEPLAY` PASS**。更新後の端末から `base.apk` と `split_config.arm64_v8a.apk` をprivate一時コピーし、新候補との**バイト完全一致**を検証。アンインストール、`pm clear`、ダウングレード、新鍵発行、公式 `jp.co.ponos.battlecats` 操作は一切しない。残る4分割の**全バイト一致は未確認**（署名/6本存在は検証済み）。
- 続けて **1回のみ研究版起動**：`CAPTURE-OWNER-ORIGINAL-CRASH.ps1` で18秒の非公開logcatを取得し、`summarize_original_crash_capture.py` で識別子を残さず集計。**研究版プロセス開始1件／死亡0件／`original-native-scene-hook-v1 installed` 1件／旧フック初期化失敗0件／SIGSEGVバックトレース0件**。以前の本人Android同一研究版は18秒中「起動86・死亡85・フック初期化失敗85」だった。**少なくともこの観測窓でShadowHook初期化失敗・急速なプロセス再起動ループは再発していない**（因果の断定はまだ不可）。
- 原作の**実native固定イベント**：同じPID内で `original-native-scene-v1 id=102`, `id=101`, `id=97` の遷移を順に各1件確認。`original-native-app-launch-save-read-v1 accepted` 1件（原作readerのstatusビットを観測。**実ファイル永続化・オフライン独立SAVE生成・Lv60成功を証明しない**）。研究用ルート有効、`original-local-denied-http-v1` 2件。USBからのread-only `pidof` と `dumpsys` で研究版1プロセス生存・前面window/resumed状態を確認。
- **画面描画は未受入**：研究版前面を確認した上で、非保存のAndroid画面`screencap`をPython上のメモリだけで色比率分析。約2400x1080のランドスケープ画面中央サンプルでほぼ黒（RGB各最大値12未満）**76.6%**、暗色（38未満）**82.2%**。元ゲームの基地画面やゲームプレイが見えたとは言えず、実画面黒問題は継続調査。
- **有力な次の原作offlineブロッカー**：シーン `97` は原作ソースで `DownloadBatchTask` 構築に対応。固定native file-presenceログは**`download_0.tsv` ～ `download_34.tsv` の私有ルート存在0/35、欠落35/35、unsafe0**。ただし同じ本人APKの `split_InstallPack.apk/assets/`には**35 TSV全部（約20,432 bytes）存在**。APK内蔵TSVとアプリ私有ルート上のloose TSVは別であり、原作約615.69MiBの追加Serverアーカイブ（93候補pair、native登録92）も現在このアプリにそろった証拠はない。**35 TSV不在だけが黒画面の唯一の原因とは断定しない**。端末のHTTPは明示的に2回拒否されており、外部ネット経由で自然回復する状態とは限らない。
- 外部アーカイブの本人PCの非認証・read-only `HEAD` 試験は元公式公開URLのlane18とlane34が両方 **HTTP403**。認証回避・別アカウント・無制限再試行はしない。所有者の旧回収ディレクトリには `MNumberServer/WImageDataServer` **実Server4ファイル＝2ファミリーのみ**、35 lane全部を補うものではない。前回の実Server 4/4 MD5一致・ゴジラ候補プレビューPASSと、**追加615MB全部の原作オフライン化**を混同しない。
- 以上のプライベート生ログ、端末ID、画面画像、署名証明書、元アプリAPK/SAVE本文はGitHubには公開しない。**次のソース実装作業**は、本人保有`split_InstallPack.apk`の35 TSV、本人保有・正規に回収可能な追加archiveのサイズ/MD5、原作scene97の配布/ローカル読み込みの整合性とprivate root受渡しを原本証拠で確定し、勝手に原作ダウンロードゲートを飛ばさない／H01処理を無効化しない。Lv60/MAX・まどか/シンゴジラ・基地i運営・実通信ゼロの合格は別ゲートで継続。

### 2026-10-11 原作scene97追加データ：所有原本358件の照合と非公開の部分回収

- 先の**実Android研究版の同一署名6分割上書き成功**・旧ShadowHook初期化失敗ループ改善・原作ネイティブscene102→101→97/reader accepted確認は変わらない。ゲーム画面は未受入で、native scene97追加データ読込境界に留まる疑い。端末内loose `download_0.tsv..download_34.tsv` は0/35だったが、**同じ所有APKのInstallPackアセット内には35件全部**存在する。元の約615.69MiB追加アーカイブと別物であり、TSV単独コピーで画面修復と見なさない。
- 本人原本の35 TSVの全358ファイルの**ファイル名・バイト数**と、歴史的な公開ミラー `fieryhenry/BCData` の `jp_server` 348ファイルをGitHub APIで比較：**348/358件がファイル名とサイズ完全一致、サイズ相違0、X系Server 10件（`XImageDataServer`, `XImageServer`, `XMapServer`, `XNumberServer`, `XUnitServer` のlist/pack）が不足、計15,661,776 bytes**。348件の対応はサイズ一致だけで、まだ全MD5一致の証明ではない。
- 非認証公開ミラーからの小サイズサンプル`ANumberServer.list`、`CImageServer.list`、`BUnitServer.list` 3/3は元原本の**サイズ・MD5完全一致**。他を自動検証する私有ツール `tools/base_mod/recover_offline_original_server_cache.py` を実装し、元`split_InstallPack.apk`の35 TSVで正本358件を読み取って、許可された私有フォルダにしか元のMD5/サイズに一致したバイナリを保存しない。対応する合成テスト5件PASS。0バイトの正規元ファイル1件も原本MD5で扱う。
- 公開ミラーの一括回収実行は途中でツール安全チェックによって停止。**本人PC `private/original-jp1571-verified-server-cache/` に元サイズ・MD5完全一致の254ファイル／394,559,432 bytesを保存**し、オフライン再検査 `--mode verify` で**254 verified／104 missing／`PARTIAL_ORIGINAL_SERVER_CACHE_NOT_INSTALLABLE`**。残る104件の中にはミラー自体が持たないX系10件を含む。中断した4個の`.part`だけをprivateルート確認後に削除、**同時回収プロセス0件**。実元ゲーム/研究版/Android/SAVEはこの追加データ作業では書き換えなし。安全チェックを迂回した継続取得はしない。
- 本人Windows Python3.12全**660件中653成功/7 skip、失敗0**、GitHub [Test tooling #38112978208](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/actions/runs/38112978208) と[Agent terminal #38112978195](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/actions/runs/38112978195) PASS。**必要358件、現在254件取得済み、104件不足**。原作の615MBアーカイブ`battlecats_*.zip`がそのまま回収できたわけではない（MD5照合済みは抽出メンバ254件）。
- 次の実装焦点は、元Server assets残り104件の正当な入手/元TSV size・MD5厳密検証と原作scene97/DownloadBatchTaskが実際に使用する私有ファイル配置、元native integrity/H01/SAVE保全の確証。**不完全キャッシュの実機インポート・パッケージ上書き・追加ゲーム起動は行っていない**。原作UI/Lv60/XP/MAX/運営i/まどか/シンゴジラ/完全外部通信ゼロは引き続き未合格。別ゲームAlphaへ逃がさない。

### 2026-10-11 615MB画面を維持してscene97の35区分を原本MD5で監査（実スマホ操作なし）

- ユーザーは原作の「最新ゲームデータ615MBをダウンロード」画面を維持して休息中。**スマホへの追加タップ、ダウンロード開始、再起動、APK更新、SAVE変更、機内モード操作はいずれも行っていない**。スマホ通信を切る必要はないが、端末内の研究版に`INTERNET`権限がないという既存実証と、完全なSDK/IPCゼロ通信を未証明であることは区別。
- 本人PCの原作研究用`split_InstallPack.apk/assets/download_0.tsv`～`download_34.tsv`と、`private/original-jp1571-verified-server-cache`の元MD5/長さ検証済みファイルを**完全ローカル・read-only再走査**。`35`区分のうち**20区分の全構成ファイルがそろい、15区分で未取得**。合計 **254/358原本ファイル／394,559,432バイトがサイズ・MD5一致、104件／273,426,832バイトが未取得**。区分34ではX系10件がすべて不足。20区分完了は元ZIPアーカイブ20本のMD5復元を意味せず、元エンジンによる読込・表示成功でもない。
- `tools/base_mod/audit_scene97_offline_readiness.py` を追加。**35個の原本TSV**からlaneごとのファイル数・不足名・MD5一致数・元アーカイブMD5（メタデータのみ）とTSV SHAを固定し、**358/358でなければ`require_complete_source`は必ず拒否**。全358ファイルが将来一致しても、元35 ZIPアーカイブのMD5、元nativeのsource-index `0x321138`登録、resolver `0x320be0`の成功、scene97 DownloadBatchTaskによる実ロード、原作Android UIの受入は**別の未証明ゲート**。ソース監査はAndroidへのインポートを許可しない。欠落ファイル名を含むレポートは本人のgitignored `private/`のJSONにのみ保存。再実行した監査は`SCENE97_ORIGINAL_358_MEMBER_SOURCE_INCOMPLETE_NO_ANDROID_IMPORT`、`android_import_authorized=false`。ネット通信・ゲームAPK/SAVE/設定変更を実装しない。
- 合成テスト（35 TSV／358ファイル、0バイトファイル、誤MD5、外部パス・シンボリックリンク、重複TSV、private一意レポート、完全でもnative受入とはしない）**6件PASS**。本人Windowsの既存全**666テスト実行・659成功／7スキップ**、[Test tooling #38114324404](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/actions/runs/38114324404) は **666件／665成功／1スキップ**、[Agent terminal #38114324384](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/actions/runs/38114324384) PASS。
- **次の実装する1差分：** 原作JNI source resolver`0x320be0`が`0x321138`で照会するsource-indexの正規登録経路を、本人JP15.7.1 ELF/元Javaの一次証拠と突き合わせて特定。APK内蔵35 TSV、loose TSV（前回のprivate root存在0/35）、ミラー照合済254件のどこから元resolverが読み込むのかを証明するまでは、古いH01/アセット整合性を壊す投機的なcopy・完全オフライン合格宣言・Androidインポートをしない。

### 2026-10-11 615MB一回取得・差分提案への現物調査：旧研究版に元追加ファイル358/358が残存

- 本人の提案は「原作から一度615MBを取得し、取得前後の全差分を観測してから完全オフライン化」。正しい実証方針だが、**現在615MB画面にいる`jp.kn.local.battlecats`は`INTERNET`権限なし・非debuggableで`run-as`が使えず、同じパッケージで今ダウンロードボタンを押しても正常な取得/差分を観測できない**。この画面と既存SAVEは今回**一切変更しなかった**。Android API31でのADB読取検査で確認。
- **決定的な現物発見**：本人Androidには別の研究版`jp.kn.trace.battlecats`がインストール済み、こちらは`INTERNET`宣言あり・`debuggable`なしだが、`/sdcard/Android/data/jp.kn.trace.battlecats/files`にADB読み取りアクセスができた。**原本JP15.7.1の35 TSVで宣言された358個と同じファイル名が全358個存在**。この別研究版の外部キャッシュを**ADBのread-only `md5sum`で358/358原本MD5一致**検証。X系10件を含む。その他の非対象20エントリは**名前数だけ計測し、SAVE/アカウント等のファイル内容は一切開かず、コピーもしていない**。
- 以前PC側`private/original-jp1571-verified-server-cache`に**原本一致254件**が存在。端末の別研究版に存在した不足**104件だけ**を、**ADB pull（端末read-only）→private一時ファイル→個別元サイズ/MD5確認→新規ファイルへの昇格**という手順で取得。その後PC側の**358/358ファイルを全件再照合**、抽出ファイル総計 **667,986,264 bytes**、元の35 TSVとの長さとMD5が**全件一致**。新たな615MBダウンロード、公式オンラインアプリの起動、端末へのアップロード・上書き、`pm clear`、SAVE内容アクセスは**ゼロ**。
- 既存`tools/base_mod/audit_scene97_offline_readiness.py --require-complete`が本人PCで**`SCENE97_ORIGINAL_MEMBER_BYTES_COMPLETE_NATIVE_LOADER_UNVERIFIED`**、35/35区分・358/358ファイル・欠落0・`android_import_authorized=false`を返すことを実測。**完全なのは元の抽出ファイルのサイズ/MD5**であり、元の35本の圧縮ZIPアーカイブ本体MD5・native source index `0x321138`登録・scene97による受入・基地画面移行・H01無しは未検証。
- **93組の暗号化`Server.list/pack`構造の現物解析**：本人PCの完全キャッシュから93/93の`.list`をAES復号し、対応する93`.pack`に対する**33,780個の内部ファイル・オフセット・境界をすべて検査**。サイズ超過・非ゼロエントリの重複領域0件。内部内訳：PNG **17,615**、maanim **10,795**、imgcut **2,685**、mamodel **2,685**。これらの数字は暗号化済み元データのINDEXを読んだ**メタデータ**であり、各PNG/モデル/アニメーションの意味付けや原作ロード完了を意味しない。 `tools/base_mod/audit_complete_original_server_structure.py` を追加して再現可能にした。
- ユーザーの「ダウンロード前後を比較する」方針のため、`tools/base_mod/compare_original_download_snapshots.py` を追加。所有元TSVが指定する**358件のゲーム追加データだけ**について、明示的にPRIVATEに準備された前後スナップショットを差分（追加/変更/削除/同一）として比較し、元サイズ/MD5を検証。SAVE・SDK/アカウント・それ以外のファイルは**読まない**。合成テスト6件は実行。**旧研究版の取得「前」の実スナップショットは存在しないため、過去の実通信順序や圧縮35ZIPの取得差分そのものを遡って復元したとは主張しない**。
- **本人Windows Python3.12全677件実行・669成功/8スキップ**、[Test tooling #38115440186](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/actions/runs/38115440186) と[Agent terminal validation #38115440178](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/actions/runs/38115440178)はPASS。ファイル実体、端末のログ、署名/SAVE、秘密情報をGitHubへアップロードせず、`CURRENT.md`とIssue #15/#12は結果の数値メタデータのみ。
- **次に書く実コード**：原作シーン97の`0x320be0`・`0x321138`によるSource Index形成と、既に整合性が確認できた358ファイルの**独立研究版内プライベートルートへの一度限りの安全な導入**を結ぶ。ただし今の`jp.kn.local.battlecats`は非debuggableで内部rootにADB直接コピー不可。再署名やパッケージ変更を伴う実装は元SAVE/原作コード等の不変性と受入テストを作ってから**別途明示的に実行**。当面615MB画面のままでよい。機内モード不要。旧`jp.kn.trace`のデータ/SAVEも改変しない。

## このファイルの後に読むもの（最大限絞る）

**普段の新規AIセッション：** このファイル → PRODUCT_IDENTITY.md → 実装ロードマップの「実行順序と次の担当者向け開始地点」→ 今動かす1タスクのソース/証拠だけ。毎回すべてのdocs/を巡回する必要はない。

| 作業分野 | 当面追加で読む一次資料だけ |
|---|---|
| レベル上限 | `tools/base_mod/level_cap_unlock.py`、`tests/test_level_cap_unlock.py`、実JP15.7.1 `unitbuy.csv`/元ネイティブ育成接点 |
| まどか | `docs/updates/manifests/update-1.01.json` の `madoka`、`tools/base_mod/prepare_update_manifest.py`、`native/kneekura-shim/src/kneekura_battle101.c`、本家実ダメージ・攻撃/演出接点 |
| シン・ゴジラ移植 | 同1.01 JSONの `godzilla`/source_assets、`tools/base_mod/collect_update_101_server_assets.py`、`kneekura_battle101.c`、所有者privateの `550_e` 元素材/味方 `702_f`。**Server原本4ファイルは所有者PCで原本MD5 4/4照合成功**。[GODZILLA実装AIへの回収・抽出手順](docs/updates/godzilla-source-acquisition-handoff.md)、`tools/base_mod/fetch_godzilla_server_assets.py`（Gitにはスクリプトと照合値だけ。実体はprivate/のみ）、[詳細証拠](docs/research/2026-10-10-original-server-archive-acquisition.md)。元画像7件→味方No703第1形態702_fの**非インストール用プレビュー生成コード**は実装・合成暗号化パック試験PASS（`tools/base_mod/prepare_godzilla_ally_preview.py`、`--prepare-ally-preview`）。所有者PC側の回収バイナリは未転送だが、**原本JP15.7.1のサイズ・MD5に一致する公開アーカイブ4ファイルをGitHub Actions一時領域で実取得し、実物550_e 7件を復号、702_f変換・WImageDataServer候補の暗号化再読込までPASS**。[原本実パック検証証拠](docs/evidence/jp15.7.1-godzilla-real-mirror-proof.md)（元素材はCI終了前に破棄）。原作Server登録順（WImageDataServer index4→QNumberServer index27）の先着キー保持を踏まえた**非インストール用WImageDataServer 702_f読込候補**も実装（`tools/base_mod/prepare_godzilla_native_resource_preview.py`）。元`702_c`と無関係な暗号化資産は不変、**4ファイル照合→7件抽出→702_fプレビュー→WImageDataServer候補**の一括コマンド（`--prepare-native-resource-candidate`）と暗号化合成パックの全工程テストまでPASS。**フル一括時は4工程を一時領域で検証してから公開、遅い失敗時は中途出力を巻戻し**（Windows/Linux合成テストPASS、電源断時の4ディレクトリ原子性は非保証）。所有者PCの回収ファイル4件のSHA-256独立照合、改変候補の原作ダウンロード表MD5適合、原作Android実機資産選択・描画・戦闘は未完了 |
| 完全オフライン | `docs/evidence/jp15.7.1-offline-egress-static-receipt.json`、`docs/references/native-service-map-jp15.7.1.md`、`docs/architecture/2026-10-09-complete-local-offline-audit.md`（**証拠**として）、`bridge/java/MyActivity.java.in` |
| MAX資源・育成/アイテム | `docs/updates/manifests/full-max-start-jp15.7.1.json`、`tools/base_mod/build_offline_max_save.py::MAX_VALUES`、`tools/localcore/full_max_resources.py`（**ローカルセーブ実装、元のゲームUIへの接続は未了**） |
| iボタン/運営予定表 | `tools/localcore/ops_calendar.py`、`notice_feed.py`、`login_rotation.py`、`ops/seasons/2026-autumn-prototype.json`、`docs/architecture/kneekura-offline-notices.md` |
| 共通の配布/再発防止 | `docs/research/failure-repair-history.md`、`AGENTS.md` のWindows部分（**ゲームが実装できた後だけ** owner ZIPを発行） |
| USB/ADB初期診断と将来の初期セットアップZIP | [Issue #16 — Device preflight](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/16)、`AGENTS.md` の「Owner Android device / ADB preflight」（**手順改善の追跡のみ。新たな本体計画やZIP完成ではない**） |

## 旧設計を読む場合の明確な区別

- `docs/architecture/design-philosophy.md`：**原作維持の方針と技術根拠**。冒頭にあるオーナー最新判断以外は歴史的な記述を含む。
- `docs/architecture/current-design.md`、`base-preserving-android-mod.md`：**元エンジン候補の設計・検証資料**。これは本書に代わる新規の実装計画ではない。
- `docs/architecture/2026-10-09-complete-local-offline-audit.md`：**不十分な通信遮断の一次静的証拠と危険箇所**。かつて独立ホストに言及した部分は「原作との一致を免除する」という意味ではない。
- `docs/architecture/kneekura-post-eoc-liveops.md`：**旧設計の履歴**。未来編1章未クリア、ゲーム内ネットからの自動更新等の古い案は現在不採用。
- `docs/architecture/kneekura-independent-story-checkpoint-v2.md`：**初期章状態だけ**を扱う。Stage Fidelity Alphaの実装を本家と呼ばない。
- `app/` Stage Fidelity Alpha、`android/local_update`：**試作・テスト専用**。元ゲームとは異なる。CI PASSでも製品の完成とは無関係。
- `docs/architecture/kneekura-offline-operations-charter.md` 等の運営室設計：**将来の実ゲーム運営の詳細**。この4機能の実装を放置してUI/告知の新規ハーネスを作る根拠にはならない。

**未列挙の設計書は、リンクが関連タスクから求められるまで** `REFERENCE_ONLY`。ファイル名が`current`、`final`、`approved`であっても、本書を上書きできない。

## 4つの中核実装＋2つの必須横断仕様（削除不可）

**LEVEL** 公式データ内のLv60/50/20/1キャップを本家育成/実戦で使う。**MADOKA** 原作第3形態のLv30実攻撃28,000/感知750/費用4,550/再生産155秒。**GODZILLA** ゴジラにゃんこ第1形態（敵シン・ゴジラrig転用）のLv30三連撃50,000×3/2950/9800/500秒/城への一連撃最大1。**OFFLINE** 原作ゲーム体験のままサーバー/広告SDK/公式SAVE依存なし。

**初期状態はこれまでどおり資源もMAX（ユーザー再確認）**：XP 99,999,999、ネコカン45,000（旧研究エディタ採用値／ゲーム内部上限は要確認）、NP9,999、各種チケット、マタタビ、キャッツアイ、ネコビタン、統率力回復アイテム、城素材、本能玉等の**研究版全20カテゴリ**。唯一の数量原本は `docs/updates/manifests/full-max-start-jp15.7.1.json`（以前の `build_offline_max_save.py::MAX_VALUES` を再利用）。新規ローカルセーブには初回MAX、既存セーブは非破壊で一度だけ加算移行し、使用後は毎回勝手に補充しない。原作の育成/所持品UIへ実接続できるまでは完了扱いにしない。

**ジョリーがPONOSに代わり運営する業務も必須（今回改めて確定）**：本家基地**右上i**からジョリーのお知らせ（日時・カテゴリ・本文）を読む、ガチャと排出内容の更新、限定/曜日/月次ステージ、イベント、ログイン5枠循環、ミッションと報酬、育成イベントの倍率・お知らせ・変更履歴。既存 `ops/seasons/`, `tools/localcore/ops_calendar.py`, `notice_feed.py`, `login_rotation.py`, `docs/architecture/kneekura-offline-operations-charter.md`, `kneekura-offline-notices.md` を**継続**。現在は運営データと試作のi画面が存在するが、原作ゲームの基地/ガチャ/ステージ/UI連動は未実装。**Stage Fidelity Alphaでiが表示できたことは本家での完成を意味しない**。

**日本編1〜3章＋未来編1章クリア/最高のお宝**も共通の既定初期値。現在の中核工程はLEVEL→MADOKA→GODZILLA、OFFLINEを並行。**MAXはLEVEL/保存・育成経路の一部、運営業務はOFFLINE/本家UIとの統合の一部として実装**し、どちらも最終受入れから除外しない。別ゲームや新しい運営UIハーネスを作り直す仕事へ逸れない。

## 実装上の厳禁

- `Phase 0`/基礎設計/整理のやり直しを完了基準にしない。**次のコード作業は本家育成レベル上限への一本の縦割り実装**。元エンジンとの接点はこの作業の一部。完全オフラインの調査は同時進行。
- 原作に接続されていないCSVプレビュー、native判定関数、テスト用ゲームUIを「実装完了」と数えない。各タスクに原作の画面・実戦・再起動の証拠が必要。
- 元本家のクライアント/サーバーBAN判定を解除したり不正SAVEを再接続したりしない。危険なネット接続が残る元ゲームを「完全オフライン」と言わない。
- ユーザーの秘密鍵、SAVE、所有済み画像/音声/packをGitHubへコミットしない。上書きZIPとUSB作業は完成を立証する段階でのみ。
- 具体的な技術的失敗が出たら`BLOCKED`と証拠、進められる別機能を記録する。**「別の簡易にゃんこ風ゲームを配ればよい」は解決ではない**。

## 一つの作業セッションの終了条件

直前の実装タスクについて、`現状→変更箇所→実行した検証と出力→未達・障害→次に書く1個のコード差分`をそのタスクのIssueに書く。次のAIはこの CURRENT.md と**そのIssue**だけで再開する。新しい原則ノート・チェックリスト・新しい計画を増やさない。

**このCURRENT.md自身を変える場合は、オーナーの新指示と、その理由を同じPR/Issueに紐づける。**
