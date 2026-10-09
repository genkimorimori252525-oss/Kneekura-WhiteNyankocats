# Agent terminal validation contract

This repository contains device-facing PowerShell and Android tooling where an
incorrect command can waste a long device/debug cycle. Coding agents must use
the repository validation harness before handing terminal commands to a human.

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
- Any requirement to preserve original UI or native loader is subordinate to the hard offline contract. Where that contract fails, investigate independent local host rather than bypassing a restriction dialog or reconnecting edited saves to official services.
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
