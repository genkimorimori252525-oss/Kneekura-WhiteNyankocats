# にーくらアップデート1.01 — セーブ保護

このページは、プレイデータを失わないための実行可能なバックアップ手順や。これは完成版の1.01ゲーム本体をインストールする手順ではない。

既存アプリを保存して終了し、USBデバッグでAndroidを接続して、既存のにーくらにゃんこプロジェクトのルートから以下を実行する。

    powershell -ExecutionPolicy Bypass -File .\tools\base_mod\run_update_101_safe_backup.ps1

必要なツール：Python、ADB、Android SDK Build Tools（aapt、apksigner）。

個人用なら既定の jp.kn.white.battlecats。研究用でプレイ中なら -Package jp.kn.trace.battlecats を付ける。Practiceなら jp.kn.clean.battlecats。

成功時、private/kneekura-101-backups/backup-日付時刻/ に端末の現在SAVE_DATAと元の6本のAPKを保存し、それぞれのSHA256、JP15.7.1 salted-MD5、Android APK署名証明書、package ID/versionCodeを検証する。

元SAVE_DATAが読めない、MD5検証に失敗する、端末内のAPKの署名が一致しない、アプリが起動中、Android SDKが不足する、などの場合には何もインストールせず中止する。事前バックアップに既存データを上書きもしない。

署名済み更新候補6本をすでに所有している場合は -SignedSplits path を付ければ現在のアプリと同一署名・同一パッケージ/バージョンかチェックできる。異なる署名のためのアンインストールやデータ消去は行わない。

バックアップとその中に入っている署名情報、セーブ、元APKは他人に渡さず、GitHubへアップロードしない。private/ は .gitignore に設定済み。

現在は本家ネイティブの攻撃・敵城HP減算箇所への接続と敵ゴジラの味方アニメ移植が未検証なので、上記はあくまでデータを守るための第一段階。完成していないAPKを1.01正式リリースと呼ばない。