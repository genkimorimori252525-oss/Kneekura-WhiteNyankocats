# Failure / Repair History — Kneekura White Nyankocats

Purpose: prevent repeat mistakes. This file is part of the engineering contract,
not a changelog for cosmetic work.

## 2026-10-06 — H01 after original additional-data download

**Observed**

The research package reached the original ~615 MiB additional-data download,
then the original UI stopped with H01.

**Root cause class**

The original pack/list integrity path is sensitive to broad DataLocal /
DownloadLocal changes. A feature experiment had crossed the preservation
boundary.

**Repair**

- DataLocal is never modified for ordinary feature experiments.
- Research overlays use the narrowest possible DownloadLocal scope.
- H01/global-integrity bypasses are prohibited.
- Original pack/list acceptance remains a promotion gate.

**Regression rule**

A feature that requires disabling H01 or replacing original integrity logic
does not ship.

---

## 2026-10-07 — optional SAVE_DATA4 probe aborted PowerShell

**Observed**

The real `SAVE_DATA` was pulled successfully, but checking nonexistent
`SAVE_DATA4` produced an adb stderr line that PowerShell promoted to a
terminating error.

**Repair**

Optional sibling saves are tested with existence predicates and skipped when
absent. Their absence is not an error.

**Regression rule**

Optional Android paths must never be probed with a command whose expected
"not found" stderr can abort the runner.

---

## 2026-10-07 — original game rewrote 497,580-byte MAX save to 507,174 bytes

**Observed**

The MAX candidate opened in the unchanged original UI and survived restart.
The original game then normalized the save to 507,174 bytes. An exact-size
verifier rejected it and automatically rolled back.

**Root cause**

The verifier confused a valid variable-length original-game rewrite with
corruption.

**Repair**

- map the exact +9,594-byte normalization;
- recognize known candidate/runtime layouts separately;
- verify stable prefix for unknown valid growth rather than calling it corrupt;
- later add full semantic runtime-layout verification.

**Regression rule**

SAVE_DATA byte length is not a semantic identity. Integrity + version + parsed
state outrank one historical file size.

---

## 2026-10-07 — clean baseline SHA changed after original-game resave

**Observed**

The clean 496,340-byte baseline changed from
`cad00e84...` to `66ba4d88...` while remaining structurally valid.

**Root cause**

The bootstrap authorized one historical SHA-256 rather than the JP15.7.1 clean
baseline *family*. Volatile timestamps/bookkeeping legitimately change hashes.

**Repair**

The clean-baseline gate now validates:

- JP salted-MD5;
- game version 150700;
- exact structural counts;
- first-form safety;
- empty baseline Talent Orb section.

Rollback remains byte-exact against the backup captured immediately before a
mutation.

**Regression rule**

Use exact hashes for immutable artifacts and immediate rollback copies; use
semantic structure for mutable game saves.

---

## 2026-10-07 — Windows Japanese path corrupted adb APK argument

**Observed**

`adb install-multiple -r` received a mojibake version of the
`にーくらにゃんこ` host path and failed before installation.

**Repair**

All six signed APKs are copied to an ASCII-only
`C:\KneekuraAdbStage\...` directory, source/staged SHA-256 is compared,
and adb receives only staged ASCII paths.

**Regression rule**

Native Windows tools do not receive non-ASCII host paths when a deterministic
ASCII staging path is available.

---

## 2026-10-07 — persistence result writer assumed layout_profile existed

**Observed**

The same-signature `install-multiple -r` succeeded, original UI opened and
MAX state remained visible, but result JSON generation crashed because a
stable-prefix-only verifier result did not contain `layout_profile`.

**Root cause**

PowerShell StrictMode exposed an implicit schema assumption in the evidence
writer.

**Repair**

- verifier results always carry an explicit profile classification when known;
- result writer uses optional-property access;
- evidence records whether assurance is full-semantic or stable-prefix-only.

**Regression rule**

Evidence/reporting code must tolerate a lower assurance level without turning a
successful game operation into a false operational failure.

---

## 2026-10-07 — transient GitHub Android NDK archive failure

**Observed**

A patch-kit build failed in `sdkmanager` with an unknown/corrupt archive while
downloading NDK 27.2.

**Repair**

Android dependency installation retries with transient caches cleared between
attempts.

**Regression rule**

A network/package-manager transport failure is not treated as a product-code
failure until bounded retries have been exhausted.

---

## Current design consequences

These failures establish permanent project rules:

1. original UI/integrity first;
2. save mutation always has a pre-mutation rollback copy;
3. mutable saves are validated semantically, not by one historical hash/size;
4. reports are evidence, never the authority over visibly successful original
   runtime behavior;
5. feature state, player progression and downloaded content remain separable;
6. a new feature must not require deleting player history;
7. every new failure gets a root-cause entry plus an automated regression test
   where practical.


---

## 2026-10-07 — Post-EoC ownership was over-pruned to 11 units

**Observed**

The first Post-EoC implementation interpreted "leave progression-reward cats
unowned" too broadly and pre-owned only the nine normal Cats plus
Valkyrie/Bahamut. This incorrectly removed ordinary gacha, collaboration gacha,
Madoka/Homura/Saber/Miku and Legend Rare units from the intended convenience
profile.

**Root cause**

Acquisition classes were described conceptually, but the implementation used a
small positive allow-list instead of deriving the *negative* set that should be
withheld.

**Repair**

The ownership contract is now version-pinned from exact JP 15.7.1 data:

- start with all 835 guide-visible/playable units;
- parse exact `drop_chara.csv`;
- any eligible unit with non-negative `stageDropCharaID` is classified as a
  stage reward and left unowned;
- all remaining eligible units are pre-owned.

Exact JP 15.7.1 result:

- 158 stage-reward units left unowned;
- 677 non-stage-reward units pre-owned;
- Madoka 289, Homura 290, Saber 363 and Hatsune Miku 536 are explicit
  regression anchors;
- all 18 Legend Rare units must be in the pre-owned set.

The runtime-rewrite verifier uses the same derived ownership contract, avoiding
a split between candidate and post-restart verification.

**Regression rule**

When the user says "everything except category X", derive and verify category X
from exact acquisition data. Do not replace the complement with a hand-written
small allow-list.


---

## 2026-10-09 — catalog No.289 was confused with asset ID 289

**Observed**

Early acquisition/level-cap regressions labeled Madoka `289` directly as a
SAVE_DATA cat-array index. In the exact JP 15.7.1 pack, Madoka is
`unit289.csv` and has public/catalog No.289, but the zero-based SAVE_DATA
and `unitbuy.csv` array index is **288**. ID 289 instead represents Homura
(public No.290). Analogous off-by-one errors affected Saber (No.363 => asset
362) and Hatsune Miku (No.536 => asset 535).

**Impact boundary**

The earlier Post-EoC profile's 677-unit acquisition selection is derived from
all eligible `unitbuy.csv` asset indexes, so this mislabeled regression list
did not change the actual generated 677-unit save. The native cap migration
likewise reads the exact 0-based unitbuy rows for every eligible ID. However,
a future per-unit balance patch using the wrong name/ID correspondence could
have modified Homura instead of Madoka.

**Repair**

A central `tools/base_mod/unit_identifiers.py` contract now maps a public
1-based catalog number to the 0-based asset/SAVE array ID and separately maps
the public number to `unitNNN.csv`. Acquisition and level-cap regression
anchors use the derived internal IDs. A dedicated unit test pins:

- Madoka: No.289 => asset 288, `unit289.csv`;
- Homura: No.290 => asset 289;
- Saber: No.363 => asset 362;
- Hatsune Miku: No.536 => asset 535.

**Regression rule**

No public unit number may be used as a raw SAVE_DATA array index without an
explicit namespace conversion. Gameplay parameter filenames, public catalog
numbers, and cat-array IDs must all state their numbering convention.

---

## 2026-10-09 — Owner Alpha installer failed again (UTF-8 BOM, then missing JAVA_HOME)

**Real user log #1:** run_independent_alpha_update.ps1 displayed broken Japanese and PowerShell ParserError before executing because the UTF-8 source lacked BOM in Windows PowerShell 5.1. Corrected by shipping both entrypoint and nested installer with UTF-8 BOM.

**Real user log #2:** after BOM repair, the entrypoint passed APK SHA and manifest checks and delegated to independent_alpha_20261009/INSTALL-ALPHA.ps1, which failed around line 92: Join-Path received null Path from env:JAVA_HOME when Get-Command keytool.exe was unavailable. **No APK installation or game SAVE edit occurred in that failed command.**

**Actual root cause:** CI exercised repo entrypoint and Python tooling, but not all shipped nested PowerShell code and realistic Windows environment defaults. A default-unset JAVA_HOME is valid even on a machine that has Java installed.

**Permanent repair:** Shared UTF-8-BOM tools/base_mod/resolve_java_keytool.ps1 searches PATH keytool, JAVA_HOME, JDK_HOME, executable's JDK and guarded local Java installations. Nested owner-only installer now dot-sources resolver and has safe -CheckJava / -CheckPrerequisites with no USB writes. The entrypoint checks exact helper/installer/APK SHA. Existing program and SAVE_DATA remain unmodified, and mismatched signer is refused.

**Non-negotiable regression:** GitHub Windows PowerShell 5.1 CI with JAVA_HOME absent and LOCALAPPDATA absent; parse actual distributed scripts as PS5.1, and compare final packaged ZIP entry hashes. No CI green from an unrelated older script can be described as proof of the shipped installer. Device/password/USB remain USER_GATE.

**Distribution history:** Original overlay `kneekura-alpha-existing-folder-overlay-20261009.zip` failed BOM parsing; intermediate `kneekura-alpha-existing-folder-overlay-ps51-fixed-20261009.zip` corrected BOM but had null-JAVA_HOME defect; the new repaired owner overlay fixes both. Do NOT re-use either faulty ZIP or their recorded installer hashes.


**Additional release-verification catch:** The first JAVA_HOME fix had a stale SHA for `resolve_java_keytool.ps1` in the outer launcher. The new `tools/base_mod/audit_owner_overlay_zip.py` was executed against the actual ZIP, caught this before another USB attempt, and led to a repaired final distribution `kneekura-alpha-overwrite-verified-v3-20261009.zip` (SHA256 `486dddd998895de91526e8acaebe68e65e072bdaa2ce21360d1746d127c5ac06`). All outer/nested digests now match. Regression tests: `tests/test_audit_owner_overlay_zip.py` rejects stale hashes, null-JAVA_HOME code, missing BOM, missing nested helper and destructive commands. `AGENTS.md` mandates running this exact ZIP-level validator on every future handoff. No Android user device was connected during this static validation.

---

## 2026-10-09 — CRITICAL: shipped resolver assigned read-only `$HOME` through lowercase `$home`

**Real owner execution / actual environment**

- Shell: Windows PowerShell 5.1 launched via `powershell -ExecutionPolicy Bypass -File`, not PowerShell 7. PC project path `C:\Users\genki\Downloads\にーくらにゃんこ` contains Japanese characters; Java 17 and Android SDK tooling are installed, but `JAVA_HOME` is **not required to be set**.
- The owner extracted `kneekura-alpha-existing-folder-overlay-java-fixed-20261009.zip` into that existing project and invoked `tools/base_mod/independent_alpha_20261009/INSTALL-ALPHA.ps1 -CheckJava`.
- It failed at `Resolve-JavaKeytool` before any install: `変数 HOME は読み取り専用または定数であるため、上書きできません`.

**Exact cause**

The helper `tools/base_mod/resolve_java_keytool.ps1` assigned to `$home` in seven places. In PowerShell 5.1 **variable names are case-insensitive**, so `$home` is the built-in, read-only automatic `$HOME`. A static parser PASS cannot detect this runtime semantic failure. Prior CI with `JAVA_HOME` unset was insufficient because `keytool.exe` remained on PATH and the function returned BEFORE evaluating the bad `$home` statements. The user had already lost time to an earlier BOM ParserError and a null `JAVA_HOME` `Join-Path` failure on the same update.

**Permanent source repair**

- Rename **all seven** `$home` references to `$jdkInstallDirectory`; preserve BOM and unchanged APK and signer logic.
- `tools/agent_terminal/check_windows_owner_jdk.ps1`: execute a **real Windows PowerShell 5.1** test with empty `JAVA_HOME`, empty `LOCALAPPDATA`, tightly scoped PATH (no keytool), and an isolated fake `JDK_HOME/bin/keytool.exe` so the previously untested branch is definitely exercised. Scan assignment AST for common PowerShell automatic/reserved variable names.
- `tools/base_mod/audit_owner_overlay_zip.py` rejects any distributed outer/inner/helper script that assigns to `$home`, `$host`, `$pid`, `$pshome`, etc. `tests/test_audit_owner_overlay_zip.py` includes negative fixtures for lowercase HOME and uppercase HOST.
- SHA256 of the helper, wrapper, installer, original APK and both manifests must match the **final ZIP bytes**, not a past repository head. Run the actual ZIP auditor after the LAST edit.

**Environment compatibility contract for every future agent/session**

1. Read this history and the uploaded 89-page previous-session PDF if available **before** changing the installer. The PDF documents earlier H01, missing optional SAVE_DATA4, PowerShell StrictMode optional fields, Japanese ADB paths, variable SAVE sizes, and overaggressive fixed hash assumptions. Do not repeat those mistakes in the new independent client.
2. Windows PowerShell 5.1 + UTF-8 BOM for ALL distributed .ps1; search for read-only automatic variable name collisions case-insensitively. Do not use `$home`/`$host`/`$pid` as local variables.
3. `JAVA_HOME`, `JDK_HOME`, `LOCALAPPDATA`, `TEMP` can be unset; fallback must be explicit or stop with a useful error **before device mutation**, never call `Join-Path` on null.
4. Simulate the user's JDK discovery branch with no keytool on PATH, not just null `JAVA_HOME`; invoke the nested `-CheckJava` if the real nested installer is available in the distribution, never skip it silently.
5. Japanese project paths are expected. Stage tools/APK paths into an ASCII-only temporary directory only where ADB/SDK requires it, and preserve unchanged SHA-256.
6. The owner uses ONLY `ZIP extract-overwrite into existing にーくらにゃんこ root → one -Apply PowerShell command`. Never make the owner repeatedly search/download/reinstall tooling merely because CI did not exercise a predictable branch.
7. A successful helper unit test, Python build, or an unrelated Android build is **not** a passing owner installer end-to-end run. The actual physical USB/keystore test is explicitly USER_GATE. No uninstall, `pm clear`, SAVE_DATA rewrite, secret upload or unsigned different-key overwrite.
8. **Do not offer another owner ZIP while relevant CI is red**. Fix failures, rerun, audit exact published ZIP, and preserve the failure report.

This repair is on the independent app (`jp.kneekura.whitenyankocats`); the photographed original game's restricted save and the legacy `jp.kn.*` packages are out of scope. This `-CheckJava` error never reached `adb install` and did not alter the device.



---

## 2026-10-10 — Original research scene hook: signing order and target selection

**Observed**

The optional JP15.7.1 no-INTERNET research scene-witness packaging initially
checked the repackaged native JNI VMAs only in its post-sign parity audit. It
also used ShadowHook's basename-based hook_sym_name API; that API can register
a future-load hook, even though the original native ELF's entry VMA is known.

**Repair**

- verify_staged_original_scene_before_signing() now checks the final unsigned
  ARM64 split, including original Build ID, mapped executable instructions
  and its exact JNI dynsym VMA, before baseline_resign(). The post-sign parity
  gate stays in place as independent defense in depth.
- For the isolated no-INTERNET research package only, the source-pinned
  scene observer now calls shadowhook_hook_sym_addr() on the address from the
  unique loaded original ELF plus JNI VMA 0x31755c. Reviewed native dependency
  SHA and hook-init/hook-address/unhook API anchors are mandatory.
- Synthetic regression tests cover the unsigned APK gate and mismatches,
  optimized research-only native ELF identity, and optional hook packaging.
  The optimized host ELF test does not shell out to nm (a slow runner
  previously timed out). Actual ARM64 CI uses readelf for export checking.

**Regression rule**

Any native hook remains DEFAULT OFF and research-only. Original address drift
must block before signing. Source tests and unrelated Android debug APK success
must NEVER be described as a live original game/first-save/device pass.
No original owner APK, SAVE, asset, account or signing key is modified.

## 2026-10-12 — PC isolated resource namespace and API35 staging ownership

The PC research APK crashed in `ReceiverInitAlarm` because original
`MyActivity.localize` calls `getIdentifier` with the isolated Context package,
while the UTF-16 `ResTable_package.name` remained the publisher namespace.
The old byte patch changed only a base UTF-8 anchor. Patch only the fixed
package name in all four resource tables (base/en/ja/xxhdpi), preserve IDs and
other bytes, and require exact expected table bytes in all three parity gates.
The split fixture failed before repair; actual Android now resolves the local
string ID and repeated PC launches have zero Java exceptions.

API35 additionally hid all 393 shell-owned staged files from the app even
though ADB MD5 succeeded. A target-context probe observed missing393 before
and missing0/size0/MD5-errors0 after assigning the dedicated guest app UID.
The PC-only runner validates its dedicated userdebug AVD before root, pins the
exact installed isolated app UID, changes ownership only in its fixed staging
subtree, and checks all393 owners plus MD5. Wrong AVD/UID fails before copy.
Actual importer completed393 and reboot observed35 TSVs. No physical phone,
publisher app, source archive, SAVE contents or existing key was changed.

These repairs do not prove native scene97, original gameplay or zero egress.
ShadowHook status12 and the original network-unavailable loading screen
remain. See `2026-10-12-pc-resource-repair.md` for immutable capture IDs.


## 2026-10-12 — PC original GL observer and independent receipt verification

The original-process instrumentation v2 stalled with main in original
MyActivity class initialization/nativeLoad and the probe in nativeProbe.
The exit-info-linked ANR trace is private. Exact lock-cycle causality is
unproven; v4 serializes original class initialization first and completes
JNI registration echo41 plus all393 target-context MD5 checks. Do not
register JNI inside original loader constructors or infer NativeBridge
compatibility from a standalone process alone.

A separate default-OFF PC JNI scene observer registers exact static
appUpdateDraw()V from the original GL queue after super.onCreate. Keep exact
BuildID/19-word/VMA/class/package gates and original-draw-first forwarding.
Read scene/35 aggregate slots only on that GL TID; do not mark the failed
five LEVEL/SAVE inline hooks installed. Actual PC observed102->101->97 and
0/35/0/0 aggregate; ShadowHook12 remains, gameplay is unaccepted.

Independent review reproduced false offline verification with edited Java
crash count and incomplete artifact/barrier metadata. Add a failing synthetic
regression, then independently rederive native/Java crashes, actual barrier,
PNG set/count, log-loss and launch evidence. Require exact artifact set and
mandatory files. Valid actual captures still pass. Include bounded Start proc
PIDs when selecting current own-process ANR traces, not only polling PIDs.
Final review found both P2 findings resolved; actual ARM64 execution remains
the root agent's separate evidence, not the reviewer's claim.

## 2026-10-12 — 本人スマホ移行と初回起動後のローカル契約不足

詳細・候補ID・保証範囲は[本人スマホ受渡し記録](2026-10-12-owner-phone-handoff.md)。この節は今後の運営で再利用する失敗台帳であり、初期PC成功や途中の無例外をスマホ受入へ読み替えない。

| 観測した失敗 | 確認した原因・限界 | 修正・回帰ルール |
|---|---|---|
| 現在ユーザーでは研究版が未インストールでも`INSTALL_FAILED_UPDATE_INCOMPATIBLE` | 別Androidユーザーに旧署名の同じpackageが残っていた | 全体dumpsysも検査する回帰テスト。所有者の明示承認後に旧研究packageのみ削除。自動uninstallは実装しない |
| 大容量stdout TARが不完全、圧縮pullと長いWindowsパスで転送失敗 | 取得失敗をSHA不一致で検出。すべてのOS内部原因までは未同定 | owner-only ACLの短いprivate path、`pull -Z`、個別ASCII base64 stdin、全450ファイルの前後SHAで移行受入 |
| 空のshared_prefsを公開できない可能性をレビューで検出 | stage内の空rootを作成していなかった | files/shared_prefsを必ず先に作成。TARのroot/link/重複/容量テスト。非空targetの消去はしない |
| ShadowHook無効化の診断で`.so.off`がnative抽出エラー`res=-2` | 診断用エントリー名がAndroid native library形式から外れた | 有効な`.so`名で比較試験。A/Bだけで監視を原因と断定しない。最終候補は通常名と検証ゲートを復元 |
| ADBがoffline、`debuggerd -b`はroot要求、TCP LLDBは権限拒否 | USB再接続で復帰。研究版はINTERNETを持たない。接続断の原因は未証明 | ユーザーの再接続後、自己packageのrun-as/JDWP/AF_UNIX LLDBで診断。phone rootや公式SAVEアクセスを前提にしない |
| scene97/download完了後、CreateAccountTaskが未完了。時刻応答後`auth-password`拒否 | 初回register/tokensしか実装しておらず、既存ローカルアカウントのpassword refreshが未対応 | 原作の3要求フィールドと応答契約を確認。独自ID/token/nonceの厳密照合と署名付き冪等再発行。実Javaで正常/異なるtoken等を検証、実機でrefresh→tokens受理 |
| refresh修正後のmanaged応答がlocal-io | MAX化したSAVEと旧所持品台帳が不一致。初回以外の差分を一律拒否する設計だった | 認証済みpaid=falseの現在量をFileLock/fsync/atomic replaceで保存。増加・消費による減少・checksum破損保持を回帰検証。SAVE再初期化・自動補充はしない |
| 短時間採取で初期イベントが見えず、冷起動が止まったように見えた | 収集後に読むstdout PIPEには滞留・欠落の余地があり、実際の端末バッファには初期イベントがあった。全遅延の因果は未証明 | privateファイルへ継続出力。PIDで区間を限定して再確認。30秒の画面遷移中キャプチャと本人の後続操作画面確認を区別 |
| インストール引数・検証引数の入力誤り | 存在しないsplit名、未対応CLI flagを指定し、変更実行前に拒否された | split名は`JP_15_7_1_SPLITS`を正本とし、CLIは`--help`とAgent terminal validationで確認。架空の成功を報告しない |

**最終確認:** 775テスト、763成功/12skip。実Java3テスト、Agent terminal、2回の追加独立レビューにP1/P2なし。最終同署名更新で自己アプリ453ファイルのSHA保持、公式package path保持、root不使用。所有者がスマホ動作成功を報告し、読み取り専用の自己アプリ画面でも原作パワーアップ画面を確認した。画面・SAVE・秘密鍵・生ログ・端末IDは公開しない。

**次の受入条件:** 初回登録に加えて既存状態の冷起動・password refresh・初期MAX後/消費後の台帳同期を確認する。破損レコードの上書き、署名/nonce検証の省略、起動フラグの強制完了で停止を隠さない。キャラクターの全育成上限・全戦闘補正・SDK/IPC全経路のゼロ通信は別の未完了受入項目として保持する。

## 2026-10-12 — Lv60用SAVE増分が原作読込み後に消え、Lv20で停止

所有者のディオラムスLv20停止報告を、自己研究SAVEの読み取り専用調査で確認した。原作ハード上限60に対して保存加算0、実効20。初期生成候補・移行直前コピー・PC保存ファイルにはディオラムス40/まどか40/ゴジラ30、合計816体の非0増分があり、スマホの原作再保存後には全816体の増分が0だった。コピーの450ファイルSHA一致とparser bytes往復一致を確認。

原作SAVE parser `0x8a669c`はキャッツアイ使用履歴と受取済みユーザーランク報酬から上限を再構成する。max_upgrade_level.baseだけの変更は最終上限の保証にならない。既存getter/upgrade proxyは観測用の元返値保持で、XPのみの育成解放ではない。

**検証の不足:** 生成候補の上限分布と起動成功を、原作UIでのLv60育成確認と混同した。Lv60開放は未完了として記録する。

**修正方針と回帰:** 個別ハード上限を保持した独立ローカルXP育成ポリシーを上限表示・育成判定・購入へ接続する。履歴の偽装・MAX再適用は使わない。20→21、30→31、50→51、59→60、60超え/XP不足拒否、原作XP費用、素材不消費、伝説レア等の例外、冷起動後の保持を検証する。今回の調査ではAPK/SAVEを変更していない。[調査詳細](2026-10-12-xp-only-level60-investigation.md)。
