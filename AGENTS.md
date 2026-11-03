# AGENTS.md — にーくら大戦争 AI作業入口

## 恒久的な検証分担（所有者指定・2026-10-13）

- 運営開発は所有者指定の「一括実装・一括検証・一括修正」を採用する。関連する機能を一つのバッチとして設計・実装し、PCでまとめて検証して、見つかった不具合をまとめて修正する。機能ごとにAPK作成・実機確認を反復しない。修正後は失敗箇所と影響範囲を確認し、追加の変更・失敗・未解決の懸念がある場合だけ検証を広げる。
- AIはPC内でビルド、変更に関連するテスト、必要な原作UIの動作・保存を検証する。品質と進行速度を両立するため、変更の影響に応じて検証を選び、新しい変更・失敗・未解決の懸念がない限り、同じ検証や全試験を繰り返さない。
- スマホへ渡した後のゲーム動作は、所有者が目視で検証する。AIによるスマホの起動・画面操作・育成／進化試験・再起動・画面／ログ取得・SAVE読取りを、標準の受渡し後検証として実行しない。追加の端末調査は、所有者がその作業を明示的に依頼した場合に限る。
- 依頼された転送・導入に必要な対象package／署名／データ保持の確認と、スマホでのゲーム動作検証を区別する。導入処理の成功を動作確認済みと記載しない。
- PCの必要な検証が通れば受渡しへ進む。所有者のスマホ目視確認が未報告の項目は「本人確認待ち」と記録し、AIによるスマホ検証を受渡しの追加条件にしない。PCで確認した範囲と、本人が確認した範囲を分けて報告する。
- この分担は、以下や過去の文書にある「AIが実機UI／再起動を検証してから渡す」手順に優先する。既存の署名・秘匿・データ保護・品質基準は維持し、未確認項目を成功扱いにしない。

## 任意のAndroid逆解析スキル：REA（通常OFF）

- APK/DEX/Smali/JNI/ネイティブコードの**具体的な逆解析が必要なときだけ**、[REAスキル](.agents/skills/rea-android-analysis/SKILL.md)を選択肢として検討する。既存ツールで十分なら使わない。
- 普段の実装・テスト・運営作業ではREAのSkill詳細読込、インストール状況の確認、依存導入、MCP起動・登録を行わない。REAは必須ではなく、採用・不採用は根拠と負担で判断する。

**FIRST: READ [CURRENT.md](CURRENT.md).** That file is the ONLY design entry point and links to [PRODUCT_IDENTITY.md](PRODUCT_IDENTITY.md) and the [four-feature active implementation roadmap](docs/roadmap/2026-10-09-original-battle-cats-delivery.md). Do **not** search all older design docs, open a new foundational spec series, continue the standalone lookalike Alpha as product work, or hand over an APK whose only achievement is passing basic CI. **The next implementation task is the first real original-game UI level-cap vertical slice, with full offline engineering investigated in parallel.**

**OWNER WINDOWS PATHS ARE NOT GUESSWORK:** Read the “オーナーWindows開発環境 — 実測固定パス” section of [CURRENT.md](CURRENT.md) before proposing any Android SDK, adb, PowerShell, ZIP, or signing instructions. The confirmed SDK root is `C:\Users\genki\AppData\Local\Android\Sdk`, ADB is `platform-tools\adb.exe` below that root, project checkout is `C:\Users\genki\Downloads\Kneekura-WhiteNyankocats`, original owned ZIP is under `Downloads\にーくらにゃんこ\`, and the research kit is under `Downloads\kneekura-original-owner-trial-kit`. Use dynamic `adb devices` for current connection state; NEVER hardcode a device serial, fake `C:\PATH\TO` path, or infer the currently opened PowerShell directory is the repo. Exact current paths and Build-tools evidence are centralized in CURRENT.md; update there, not in new parallel rules.

This repository contains device-facing PowerShell and Android tooling where an incorrect command can waste a long device/debug cycle. Coding agents must use the repository validation harness before handing terminal commands to a human.

## 2026-10-11 原作6分割・黒画面実機障害と研究用ビルドの現行ゲート

- 本人Androidで原作JP15.7.1の別パッケージ `jp.kn.local.battlecats` 6分割インストールが成功したが、黒画面と短時間のプロセス再起動を実測。所有者の04:04のプライベートなログを厳格に再集計すると **研究アプリ起動86件／死亡85件／古いShadowHook初期化失敗85件**（古い「87起動・87死亡」報告には他アプリ混入あり）。フックエラーと死亡の因果・SIGSEGV発生PCは未確定。
- 旧ダウンロードキット `kneekura-original-owner-trial-kit/BUILD-ORIGINAL-RESEARCH.ps1` に含まれた単独 `libshadowhook.so` 組込みを、再検証目的でそのまま使わない。現行ビルドは **同一公式Maven 2.0.1 AARから `libshadowhook.so` と `libshadowhook_nothing.so` の両方をハッシュで検証**し、必ず同じARM64 splitへ同梱する。片方しかない候補はFAIL CLOSED。
- 研究用候補の作成は `tools/base_mod/BUILD-OWNER-RESEARCH-PAIR.ps1`（**build-only**、既存プライベート署名鍵を再利用、virgin SAVE writerなし）。実機更新**前**に `tools/base_mod/CHECK-OWNER-RESEARCH-DEVICE-SIGNER.ps1` が呼ぶ `tools/base_mod/preflight_original_device_update.py` で、**実際にAndroidへインストール済みの研究版** `base.apk` と新候補6本の証明書を照合する。古いPC上の署名済みAPKと一致しても実機署名一致とは言えない。
- これら2つは勝手にアプリを更新しない。本人の明示的な端末更新判断が別途必要。元PONOSアプリとSAVEには触れず、アンインストール・データ消去・root化・別署名インストールは禁止。公式APKやSAVEの中身をGit/ChatGPTへ出さない。
- 現在のPASSはCI/合成パック/Windows構文/公式AAR照合まで。**元ゲーム初回起動、Lv60/XP/MAX、原作SAVEの生成・読込、基地i運営、まどか/ゴジラ実戦、全通信ゼロの実機受入は未達**。手順・原因・証拠の詳細は [Issue #12](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/12) と並行 [#15 OFFLINE](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/15)。新しい基礎ロードマップ・別ゲームAlphaを作らず、原作実起動ゲートに集中する。



## P0 OWNER PRODUCT IDENTITY — NEVER SUBSTITUTE A LOOKALIKE

**READ THIS BEFORE ANY CODING, RELEASE, INSTALLER, USER ANSWER OR AGENT HANDOFF:** [PRODUCT_IDENTITY.md](PRODUCT_IDENTITY.md). Owner explicitly re-confirmed on 2026-10-09: **「俺が遊びたいのはにゃんこ大戦争だ。絶対に間違えないで。」**

- The requested product is the genuine **Battle Cats game experience**, based on the owner's original JP15.7.1 game assets, UI, animation, battle rules, units/enemies, stages, gacha and progression, with Kneekura customizations. **NOT a lookalike, demo, generic cat tower defense, or independent Stage Fidelity Alpha substituted for the actual game.**
- **Both hard constraints are required**: exact original-game **fidelity** AND full **offline/network-independent** operation. Network independence NEVER authorizes simplifying/omitting Battle Cats gameplay. If the original runtime cannot be used safely, an independent compatibility engine is only a research path until it proves Battle Cats-grade parity. No silent change of product identity.
- The repository's small Java Android `app/` and `jp.kneekura.whitenyankocats` packages currently represent an **engineering/test harness**, **not** the owner's intended playable Battle Cats. Do **not** promote them as a completed 1.01 or hand them to the owner as a substitute even if APK build, Android INTERNET-permission test, or i-button screens PASS.
- Retain original JP15.7.1 gameplay data and original scene/animation feel wherever technically feasible, while preventing all external communication and requiring a private Kneekura save. No official account reconnect, no rejected JP SAVE_DATA reimport, no source assets or owner signing keys in GitHub.
- Mandatory owner-approved changes must ultimately work **in the same real-equivalent game**: official per-unit max Lv cap (60/50/etc), Ultimate Madoka form3, Godzilla No703 form1, EoC1-3 + Future1 complete/Superior treasures, **all formerly approved XP/Cat Food/NP/tickets/items/materials START MAX**, and **Jolly operates the original-base i notices, gacha/event/stage schedules, five-slot login, missions and rewards**. The four core tracks in CURRENT.md integrate MAX via LEVEL/local save and operations via OFFLINE/original UI; neither may be forgotten, deferred out of final acceptance, or replaced by a new lookalike. Separate research scripts and demo UI do not satisfy this.
- Before calling anything "playable", "release", "full game", or "complete", check [product-identity-gates.json](docs/architecture/product-identity-gates.json): UI, original graphics/animations, actual battle, stage flow, character roster, gacha, custom performance, no-network, persistence and explicit owner acceptance. Missing evidence => research only, disclose gaps.
- Older lines in `design-philosophy.md` or offline audit that permit an independent engine are **conditional research routes, not permission to ship a different game**. Source-of-truth precedence: `PRODUCT_IDENTITY.md` > all prior specs and tool convenience. **Changing this priority requires new explicit owner instruction.**

## GODZILLA source availability — no unnecessary USB recollection (2026-10-10)

Owner Windows acquisition of JP15.7.1 source files MNumberServer.list/.pack and WImageDataServer.list/.pack reported 4/4 **exact size + source TSV MD5 match**. They are available **on the owner's local PC only**, not inside this public repo. If working on the owner's machine, import from the pre-existing recovery-kit cache with `python -m tools.base_mod.fetch_godzilla_server_assets --from-dir <OWNER_CACHE_DIRECTORY>`; in an independently authorized environment, the same tool supports `--download` via the historical BCData mirror. Store verified bytes strictly under gitignored `private/server-jp1571/godzilla/` and then run the existing `tools.base_mod.extract_godzilla_owner_rig` for seven `550_e` private assets. **Full commands and original MD5s: [Godzilla implementation handoff](docs/updates/godzilla-source-acquisition-handoff.md), [Issue #14](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/14).** Remote/cloud agents cannot see owner PC files automatically. Do not upload copyrighted original art/pack bodies to GitHub, even when the user requests the implementation AI have access. No rig conversion or Android playable confirmation is implied.

## Owner Android device / ADB preflight: mandatory before USB instructions (2026-10-10)

**Owner-confirmed problem and future setup-ZIP tracker: [Issue #16 — ADB初期診断・オーナー向け初期セットアップZIP](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/16).** Every AI/agent that asks the owner to run `adb`, collect Server packs, or install an app MUST preflight first and explain access limitations. This is an engineering tooling rule, **not a new product roadmap**.

1. Run `Get-Command adb -ErrorAction SilentlyContinue` before suggesting `adb devices`. If absent, locate an **existing** `adb.exe` in `$env:LOCALAPPDATA\Android\Sdk\platform-tools`, `$env:ANDROID_SDK_ROOT\platform-tools`, or `$env:ANDROID_HOME\platform-tools` only after checking env variables are nonempty and paths exist. For the current PowerShell session only, append its directory to `$env:Path`; if unavailable, guide installation via Android Studio SDK Manager or the official Google SDK Platform-Tools download. Do NOT require manual persistent PATH edits as the first step.
2. Run `adb version` and `adb devices`. Explain `unauthorized` (unlock phone/approve RSA prompt), `offline` (reconnect/restart adb), no device (cable/USB debug), or several devices (explicit serial selection). Only proceed when the intended device is `device`. Keep device serials out of GitHub.
3. For stock `jp.co.ponos.battlecats`, check read-only `adb shell pm path jp.co.ponos.battlecats`, `adb shell run-as jp.co.ponos.battlecats id`, and `adb shell ls -la /sdcard/Android/data/jp.co.ponos.battlecats/files/` where accessible. **Never imply a successful ADB connection grants access to `/data/user/0/.../files`.** The owner observed `su` missing, `run-as: package not debuggable`, and an empty external files folder: normal non-root ADB cannot read this application's private Server packs under those conditions.
4. Device-to-PC collection must be read-only and permitted by actual file permissions. If blocked, record `BLOCKED` and use owner-held prior archives / verified manifest or distribution metadata as alternative evidence. Do NOT root, unlock bootloader, clear data, uninstall/reinstall, modify PONOS SAVE, or bypass account/BAN restrictions. No device identifiers or copyrighted pack bytes in Git.
5. Before any user-facing ZIP, validate Windows PowerShell 5.1, UTF-8 BOM for Japanese scripts, paths containing Japanese characters, missing SDK and null environment values, `adb` missing from PATH, mock `unauthorized/offline/multiple` responses, and no-mutation `-CheckPrerequisites` / `-CheckDevice` gates. Future owner setup ZIP (NOT YET BUILT) must default to diagnostics; optional read-only collection requires an explicit action. Keep distribution format consistent with existing project-root overlay policy.

## Windows owner environment: mandatory compatibility contract

**Treat this as a release-blocking contract for every new assistant/Codex session.** The owner uses Windows 11 with `powershell.exe` **5.1**, a Japanese-path project at `C:\Users\genki\Downloads\にーくらにゃんこ`, an existing Java 17 + Android SDK environment where `JAVA_HOME` can be missing, and prefers only **ZIP-overwrite into the existing project root + one `-Apply` command**. Read [the historic failure record](docs/research/failure-repair-history.md) before any installer edit.

- **PowerShell names are case-insensitive.** Do not assign to `$home` (read-only `$HOME`), `$host`, `$pid`, `$pshome`, or other automatic/reserved variables. A successful syntax parse does not mean assignment is legal at runtime.
- Use Windows PS5.1 with BOM in every shipped `.ps1`. Resolve optional `JAVA_HOME`, `JDK_HOME`, `LOCALAPPDATA`, `TEMP` with explicit null checks. Never call `Join-Path` on a null variable.
- **Test the missed execution branch, not just the happy path**: in CI isolate PATH so `keytool.exe` cannot be found, set only a fake `JDK_HOME\bin\keytool.exe`, unset `JAVA_HOME`/`LOCALAPPDATA`, and run `tools/agent_terminal/check_windows_owner_jdk.ps1` with Windows PowerShell 5.1. A PATH-provided keytool may otherwise hide `$HOME` collisions.
- For any owner installer ZIP, validate the **actual nested installer**, BOM, all file hashes, manifests and privacy constraints after the last edit using `python -m tools.base_mod.audit_owner_overlay_zip <exact-final-zip>`. Never silently skip absent nested scripts in source-only CI or claim that a source-only PASS proves the shipped ZIP has been executed.
- Respect legacy failures from the old 89-page handoff: missing optional SAVE_DATA4 must not cause PowerShell native-command aborts; StrictMode optional fields require existence checks; Japanese ADB path needs ASCII staging; game SAVE reserialization changes size/time, so semantic validation outranks fixed historic SHA/length.
- Keep **installer behavior** separate from the independent game runtime. The user's `-CheckJava` must not sign, install, connect ADB, mutate a save or change a private keystore.
- **Owner USB readiness must be explained before asking for -Apply:** enable USB debugging, connect data-capable cable, unlock phone and approve computer RSA/USB debugging prompt. Run the *actual* nested `INSTALL-ALPHA.ps1 -CheckPrerequisites` to check Java keytool, adb, aapt, apksigner, zipalign (no device mutation). Check `adb devices`: exactly one entry with state `device` => automatic selection with NO `-DeviceSerial`; none/unauthorized/offline => fix the connection first; several => specify `-DeviceSerial` using a literal returned serial. The older level-cap runner instead used `-Device`; NEVER mix these option names. Initial APK signing also requires the owner to choose/reuse the local signing password.
- **User's provided baseline ZIP** `kneekura-level60-native-cap-update.zip` (118 entries) is a different `jp.kn.trace.battlecats` SAVE-cap runner. It proves the user's familiar project-root `tools/base_mod` overlay layout, NOT that the new standalone Alpha is a level-60 or final game build. Current independent Alpha overlay has 7 files and target `jp.kneekura.whitenyankocats`, and does not need the old level-cap ZIP or the original asset ZIP for ordinary APK installation. Full exact runbook: `docs/updates/independent-alpha-existing-folder-overwrite.md`.
- A red CI or incomplete ZIP audit blocks distribution. Owner USB hardware, keystore password, physical game UI and restarts are explicit `USER_GATE` until proven; do not spend their time as a replacement for your own tests.

## Required behavior

1. **Validate before handoff.** For repository-local commands, run the command
   through `python -m tools.agent_terminal.verify run ... -- <argv>` or add it
   to `.agent-validation/plan.json` and run the plan.
2. **Use argv, not a shell string, when possible.** The harness deliberately
   executes with `shell=False` so quoting errors are exposed instead of hidden.
3. **Treat exit code, stdout and stderr as evidence.** A failed command is not a
   candidate for user handoff. Diagnose it, repair it, and rerun validation.
4. **Do not fake unavailable dependencies.** A physical Android device, the
   owner-only Battle Cats export, a signing key/password, or another unavailable
   external dependency is a `USER_GATE`. Validate every static/repository-local
   part first, then make only the irreducible user gate explicit.
5. **Never put secrets in reports.** Prefer environment variables. When a
   command may echo a secret already held in an environment variable, pass
   `--secret-env NAME` to the harness. Do not commit passwords, tokens, APKs,
   decrypted game assets, or device saves.
6. **PowerShell changes require Windows parsing.** The validation workflow runs
   every `tools/base_mod/*.ps1` through the PowerShell parser on `windows-latest`.
7. **PASS is scoped.** A CI PASS proves the command/tooling in the validation
   environment. It does not claim that an Android device interaction happened.
8. **Preserve failure knowledge.** Repeated or design-relevant failures belong
   in `docs/research/failure-repair-history.md`, with a regression check where
   practical.

## P0 full-local product safety gate (2026-10-09)

- **Zero external egress is a release requirement, not a future feature flag.** A build with `android.permission.INTERNET`, original `super.newHttpRequest(...)` fallthrough, unvetted analytics/advertising SDK initializers or untested native transport must not be called complete offline.
- **No modified official SAVE_DATA as the local game's authority.** The redesigned game must own a separate versioned local schema and must not rely on original account/inquiry tokens, client/server legality flags or official-save checks.
- Run the read-only `tools/base_mod/audit_offline_egress.py` against owner source/artifacts. Its findings reflect capability, **not proof that data was sent or that a ban was server-enforced**. A static clean result does not replace first-run device egress/IPC testing.
- **Both original Battle Cats fidelity AND strict offline are hard product requirements** per CURRENT.md/PRODUCT_IDENTITY.md. The original UI/native host is a first-choice technical candidate only where it passes offline isolation; if impossible, investigate another implementation as a compatibility research path, but do NOT substitute the separate Java lookalike Alpha for the user's game or bypass original account restrictions.
- [Authoritative investigation/architecture reset](docs/architecture/2026-10-09-complete-local-offline-audit.md), [tracker issue #5](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/5). No owner screenshot/account metadata in public GitHub.

## Jolly offline operations / LiveOps management (2026-10-09)

- Before building another event/gacha/stage/login/mission schedule, read `docs/architecture/kneekura-offline-operations-charter.md` **and** previous `docs/architecture/kneekura-post-eoc-liveops.md`; preserve the five-slot login bag and stage-available-vs-cleared separation.
- Author versioned operator data only in `ops/seasons/` with stable local IDs and JST times; validate with `python -m tools.localcore.opsctl validate --pack ...` and calendar preview before GitHub review.
- `draft` and catalog `ready=false` are strictly non-playable. Neither a schedule listing nor a stamp/mission claim intent may grant a reward, clear a stage, or mutate player state. Rewards require an independent atomic, idempotent local save transaction.
- No official live PONOS date/odds/collab claim without verified source. No advertising, analytics, paid transactions, cloud accounts, game-to-GitHub network polling or online leaderboards in Kneekura.
- Unit/stage assets and owner game archives stay under private local storage, not in public GitHub. GitHub is authoring/review/version history only; player imports approved content locally.
- Current `ops/seasons/2026-autumn-prototype.json` is a **test/draft**, not a 2026 release or verified PONOS calendar. `tools/localcore/ops_calendar.py`, `login_rotation.py`, and `mission_cycles.py` are offline reference code until Android integration passes strict zero-egress Issue #5 and LiveOps Issue #6.

## Operator-announcement editorial contract (2026-10-09)

- The owner wants the familiar **base top-right i button → notices** flow. Jolly authors all Kneekura-specific news as part of the operating duties. See `docs/architecture/kneekura-offline-notices.md`.
- Every new season, playable event/gacha/stage, balance patch, maintenance or bug fix needs accurately dated notice in `catalog.notice` with a local `schedule` window, or a recorded reason why no player news is appropriate.
- Do not claim unfinished stages, unsigned patches or fictitious PONOS calendars shipped. `ops/seasons/2026-autumn-prototype.json` is DRAFT.
- Notices require Japanese editorial category, title, body, JST publication date, optional pinned flag; no ads, personal identifiers, account sync, external URLs or remotely fetched images.
- Preview authored notices using `python -m tools.localcore.opsctl notices --pack ops/seasons/2026-autumn-prototype.json --at 2026-10-09T10:30:00+09:00`; verify immutable content IDs, ready flag, revision and signing before publication.
- Independent Android `MainActivity` has an i button opening `NoticeActivity`: 3 bundled introductory articles are shown until a separately trusted signed LiveOps content pack is imported. This is NOT the original PONOS WebView and not a final full base scene.
- Content updates must not alter independent player SAVE, stage clears, inventory or gacha draws. Signed content validity and actual game functionality require different release gates.

## Owner-facing distribution format: always project-root overlay ZIP (2026-10-09)

- The owner has a settled, explicitly preferred update process: download ZIP, extract/overwrite **directly into the existing `にーくらにゃんこ` project root**, run exactly one PowerShell command from that root (`powershell -ExecutionPolicy Bypass -File .\tools\base_mod\<runner>.ps1 -Apply`). This is the default for all future owner-side release kits unless they explicitly request something else.
- Do **not** unexpectedly switch to a separate self-contained folder, custom start.cmd flow, unrelated APK installer UI, or force re-uploading previously supplied assets. Keep new runner names descriptive and the archive's `tools/` tree rooted at ZIP top level (no extra parent directory).
- Every user kit must include all owner-visible binaries/scripts needed for the advertised command; preserve existing `.venv`, original source archives, private signing keys and SAVE_DATA. NEVER put private artifacts into a public GitHub commit.
- Default runner without `-Apply` should be preflight-only where possible. With `-Apply`, validate input fingerprints, existing app/package signing, owner device and backup constraints. NEVER uninstall or clear app data to get around a signing mismatch.
- Distinguish the independent offline Android Stage Fidelity Alpha (`jp.kneekura.whitenyankocats`) from historical patched `jp.kn.*` builds and from any fully playable 1.01 release. An overlay delivery *format* does not prove feature completeness or device QA.
- Current owner ZIP format is documented in `docs/updates/independent-alpha-existing-folder-overwrite.md` and entrypoint `tools/base_mod/run_independent_alpha_update.ps1`. The actual APK belongs in owner-only delivery ZIP under `tools/base_mod/independent_alpha_20261009/`, not in the public source repository.
## Never repeat PS5.1 / JAVA_HOME failures (2026-10-09)

**MANDATORY release gate for all future AI sessions.** The owner twice encountered failures from an apparently validated ZIP: a Japanese Windows PowerShell 5.1 script without UTF-8 BOM, then a nested installer calling Join-Path on unset JAVA_HOME. Treat both as engineering errors, NOT owner errors.

1. Validate the **actual ZIP-contained entrypoint AND nested installer**, not only a copied GitHub wrapper. Every distributed .ps1 must use UTF-8 BOM (EF BB BF) if it contains non-ASCII, and MUST pass the real Windows PowerShell 5.1 parser.
2. JAVA_HOME, JDK_HOME, LOCALAPPDATA, TEMP, ANDROID_HOME, ANDROID_SDK_ROOT and all tool locations may be missing. Guard all path operations before Join-Path. Do NOT assume PATH includes Java/keytool or Android SDK. Use the shared resolve_java_keytool.ps1 and fail with an actionable message if no JDK is found.
3. Windows CI MUST reproduce the original defect with JAVA_HOME **unset** and then with JAVA_HOME+LOCALAPPDATA unset. Check Java and Android tool preflight with **no device mutations** before letting the user run -Apply.
4. Compare SHA256 of the exact shipped APK, installer and resolver against the outer wrapper; verify ZIP CRC and manifest content after the LAST edit. **MANDATORY command before distribution:** `python -m tools.base_mod.audit_owner_overlay_zip <final-owner-overlay.zip>` against the actual exported ZIP, and record its PASS and ZIP SHA256. The bundled installer must also pass Windows PowerShell 5.1 `-CheckJava` with `JAVA_HOME` unset. No audit or CI PASS on unrelated/older source is a substitute for validating the final ZIP bytes.
5. Owner distribution format is fixed: overwrite-extract the ZIP into the existing にーくらにゃんこ project root, then one PowerShell -Apply. Do not require new folders/scripts when avoidable.
6. USB hardware, owner keystore, password and actual Android startup are USER_GATE until run by the owner. Never claim the installed game passed or that an untested ZIP is proven on the device.
7. Never uninstall, clear app data, overwrite owner original SAVE_DATA or bypass a signing mismatch. On any failure, update docs/research/failure-repair-history.md, this rule and a CI regression BEFORE reissuing another ZIP.

Current shared source: tools/base_mod/resolve_java_keytool.ps1; strict Windows CI: .github/workflows/agent-terminal-validation.yml; repaired overlay: docs/updates/independent-alpha-existing-folder-overwrite.md.

## Owner-approved local starting chapters (2026-10-09)

- **Current independent game seed (latest)**: Empire of Cats / 日本編 chapters 1–3 **plus Into the Future / 未来編 chapter 1** are all complete, all **48 stages each**, all **Superior treasure rank 3**. No Future chapters 2–3, Cosmos or SoL chapter is initially marked complete.
- The exact legacy JP15.7.1 main-story slot mapping is EoC 0/1/2, historical reserved 3, **ItF1 = 4**. In the independent app use semantic keys `eoc1/eoc2/eoc3/itf1`, not raw PONOS SAVE offsets.
- Canonical independent policy lives in `app/src/main/assets/kneekura-story-bootstrap-v2.json`; local Android storage is `StoryProgressStore.java` and the Python KNEEKURA_SAVE_V1 prototype is `tools/localcore/story_checkpoint.py`. All future owner builds must preserve this checkpoint without wiping existing units/resources/story progress or awarding stage drops without gameplay.
- `docs/architecture/kneekura-post-eoc-liveops.md` previously said Future1 starts uncleared; that is a **superseded historical design**, not the latest owner instruction. Read `docs/architecture/kneekura-independent-story-checkpoint-v2.md` for the authoritative new behavior.
- A stateless preview or `all_stages_unlocked=true` is NOT sufficient to claim chapter clears/treasures. Actual independent per-stage records and Android persistence are mandatory. Do not alter official `SAVE_DATA` or reintroduce original-account checks.

## Standard commands

Harness self-test:

```text
python -m tools.agent_terminal.verify self-test
```

Run the committed repository plan:

```text
python -m tools.agent_terminal.verify plan .agent-validation/plan.json
```

Validate one command before presenting it to the user:

```text
python -m tools.agent_terminal.verify run --name example -- python -m tools.base_mod.phase_c_preflight --help
```

If a command cannot be executed because it needs a device or private material,
report it as `USER_GATE` rather than `PASS` or an invented successful result.

<!-- CCG_CONTINUITY_START -->
## Codex Continuity Guard (行動指針)

1. **原初目標と制約の維持**: `docs/ai-continuity/PROJECT_CHARTER.md` に記載された原初目標と禁止事項を遵守する。AIの判断で勝手に変更してはならない。
2. **要件変更の承認管理**: ユーザーからの明示的な変更指示があった場合は、`docs/ai-continuity/AMENDMENTS/` に記録し、承認された変更として管理する。
3. **検証証拠の重視**: テストを実行せずに「成功」と報告してはならない。検証結果は `docs/ai-continuity/EVIDENCE_INDEX.md` に客観的な証拠とともに記録する。
4. **コンテキスト圧縮・再開時**: 作業状態が不足する場合は `continuity-guard` Skill の restore 操作で状態を確認し、現在タスクと整合性をとって作業を再開する。
<!-- CCG_CONTINUITY_END -->
