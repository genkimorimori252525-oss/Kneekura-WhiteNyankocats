# 2026-10-12 原作シーン97：「インターネットにアクセスできません」実機診断

この文書は [CURRENT.md](../../CURRENT.md) / [Issue #15](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/15) の実装補助であり、新しいロードマップではない。**本家の実画面・ゲームを維持**し、元PONOSアプリ/元SAVE/アカウント/ネットワークへアクセスしない。

## オーナーが確定した現物

1. 元JP15.7.1の615MB追加ダウンロード**要求ダイアログ自体は通過**した。
2. 後続の黒背景・ネコ・横長プログレスバーのロード画面で**「インターネットにアクセスできません」**と表示され、にゃんこ基地へ進めない。
3. 最後に本人署名を再利用した実機の隔離研究版`jp.kn.local.battlecats` は、原本393件MD5整合・内部再起動後import保持・loose TSV35件存在、元コードscene`102→101→97`、バックアップ原作失敗コールバックGL-thread帰還2件（うちタイムアウト違い1件）、HTTP拒否0件、プロセス死亡0件。
4. 研究パッケージはWi-FiがONでもアプリの`isNetworkAvailable()`を**false**にし、Android INTERNET権限もない。**この結果は端末のWi-Fi不良を証明しない。** 原作の「最新版確認」分岐との直接関係も、現時点で**不明**。

## 次の区別を追加実装

元JP15.7.1ソースから、scene97の`DownloadBatchTask`コンストラクタが`download_0.tsv`〜`download_34.tsv`を`0x320be0`で検索し、検索戻り値の符号付き整数35件をゲームcontext`+0x2fb8`に格納する`0x73cab0`を特定した。これらの値を**各ファイルのダウンロード完了フラグやタスク最終状態と断定してはいけない**。

隔離研究版の既存描画監視（元描画実行後、署名済み元libnativeのBuildID・命令語・実装VMA・隔離プロセス一致でのみ動作）のみを用いて、scene97で次の情報を最大4回記録する：

```text
original-native-scene97-resolver-v1 missing=N zero=N one=N other=N
```

4つは計35件、-1 / 0 / 1 / その他の集計のみ。原本ファイル名・実データ・SAVE・URL・端末識別子・通信本文はログに入らない。イベントが出なくても、nativeが資産を開かなかったと断定しない。既存の`original-local-file-access-v1`は**隔離getFilesDirだけ**のFileObserverで、APK内resourcesや元native index全体を網羅していない。

分析`tools/base_mod/audit_original_offline_boot_events.py`のオプション`--owner-observed-final-screen internet-unavailable`と`--owner-reported-615mb-request-passed`は、端末logcatから自動判断するものではない。本人の独立UI観測を後から併記するためのもの。新しいログで現物画面を再確認する前に、勝手に今回観測済みとして付与しない。

## 次の実機研究用署名に進む条件

- 署名前のソース/合成テスト、GitHubのTest tooling、Agent terminal、**real NDK ARM64** native research build、Android debug全てが合格。
- [ARM64の研究用ビルド #38154116390](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/actions/runs/38154116390) は**SOURCE/COMPILE ONLY**。そのArtifacts欄の`kneekura-arm64-scene-research-COMPILE-ONLY`（artifact #11707712363）のZIPは、原作APK/SAVE/秘密鍵を一切含まない。**ダウンロードするのはこの公開研究用アーティファクトだけ**。期限内に本人がログインしたブラウザからダウンロードする。ネットワークを使うのは本人PCのGitHub閲覧で、Androidゲーム側ではない。
- 公開署名対象ネイティブSHA256は`d420fada2073b67388af7a9cafd603809033ab66d5d0532ae4333e385034225a`、CI git commit`82b810fc4d437d79fc77a2f00484b1aee576565c`。`tools.base_mod.stage_scene97_public_research_artifact`はこのバイトSHA・receipt内容・ARM64・固定マーカー・ZIPの2ファイル構成を照合し、既定では**チェックのみ**。指定`--stage`時に限り`private/scene97-native-public-82b810fc`へ新規2ファイルを保存。別アーティファクト・同名既存不一致・ZIP内不正パスは拒否。

本人Windowsの作業フォルダはいつもどおり`$HOME\Downloads\Kneekura-WhiteNyankocats`。次の**例示コマンド**は、上記Artifactをブラウザでダウンロードし、`Downloads\kneekura-arm64-scene-research-COMPILE-ONLY.zip`に保存した場合のもの。実際の場所が違えばZIPのフルパスだけ置き換える。Gitのブランチと未コミット変更を確認し、`git pull --ff-only`が成功した場合のみ進める。本人秘密鍵をチャットに書かない。

```powershell
$repo = Join-Path $HOME 'Downloads\Kneekura-WhiteNyankocats'
$artifact = Join-Path $HOME 'Downloads\kneekura-arm64-scene-research-COMPILE-ONLY.zip'
$native = Join-Path $repo 'private\scene97-native-public-82b810fc'
git -C $repo status --short
git -C $repo pull --ff-only origin jolly/balance-madoka-godzilla-2026-10-09
Set-Location -LiteralPath $repo
py -3.12 -m tools.base_mod.stage_scene97_public_research_artifact --repo $repo --artifact-zip $artifact
# The previous line must report PASS_READ_ONLY_PUBLIC_CI_ARTIFACT_PINNED.
py -3.12 -m tools.base_mod.stage_scene97_public_research_artifact --repo $repo --artifact-zip $artifact --stage
# It must report STAGED_PUBLIC_RESEARCH_ONLY or ALREADY_STAGED_IDENTICAL.
powershell -NoProfile -ExecutionPolicy Bypass -File "$repo\tools\base_mod\OWNER-OFFLINE-615-ONE-SHOT.ps1" -OnlyPreflight -RequireScene97ResolverWitness -ResearchShimFolder $native
```

**Only after all those read-only/owner-private gates pass**, the single secure signed/installed study can be initiated with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$repo\tools\base_mod\OWNER-OFFLINE-615-ONE-SHOT.ps1" -RequireScene97ResolverWitness -ResearchShimFolder $native
```

This **requires the existing private research P12 password typed only at the owner's Windows non-echoing console**. It does NOT generate a new key. The script strictly verifies installed same certificate, exactly six signed splits, original source hashes and one authorized ADB device before any research-only app update; no clear/uninstall/official package operations. One startup and bounded private log only. If any condition fails, **stop**; do not rerun signing/install blindly. The default `OWNER-READY-TO-SIGN.ps1` and one-shot without the new explicit switch retain their old source-only behavior. **Nothing here is a current installed or playable offline game claim.**

## Result triage

| Runtime witness | Narrow conclusion, nothing beyond |
| --- | --- |
| `missing=35` or many -1 | 35 filename/index resolver likely failing. Inspect original native index precedence, direct APK TSV, and registered Server.list first (not simply missing source files). |
| `one=35` and no next scene | Filename resolver returned 1 for all; **not** proof task finished. Trace DownloadBatchTask future/status/UI error trigger vs offline connectivity branch. |
| Zeroes/others dominate | Return values need exact original per-result semantics, avoid guessed success. Capture bounded change snapshots and original scene events, inspect original native CFG. |
| No scene97 histogram | Observer not installed/compiled, context invalid or scene may have changed, or capture too short; do not infer resource failure. |
| Error UI persists with consistent 35 source returns | Prioritize exact error-dialog native string/caller, original network status gate and downstream provider lifecycle, rather than repeatedly downloading 615MB. |

No invention of publisher HTTP200, online service/token replay, DataLocal/H01 bypass or server-side SAVE; keep Draft PR#4 and all product-identity runtime acceptance gates **OPEN**.
