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

## 2026-10-12 — 初回XP育成更新の実装と検証環境の回帰

| 観測 | 確認した原因 | 修正・回帰 |
|---|---|---|
| 原作再構成でLv20停止 | SAVE上限加算だけでは原作の最終上限を変更できない | 個別col50に従うgetter/育成可否の2adapter。原作XP購入・履歴・通常保存は維持。実ARM64の境界/例外/無効状態テスト成功。実購入は本人待ち |
| 初回候補でruntime source-unavailable | builderをV2/10箇所/320bytesに変更し、runtime witnessがV1/8箇所/448bytesのままだった | 監視のfail closedは維持し、両ABIを一致。ソース整合回帰テストを追加。未接続候補は受渡ししない |
| PCの検証SAVEで読み込みエラーH04 | 私的fixtureがroot所有・アプリcategoryなしのSELinuxラベルだった。toybox非対応の--referenceを使い、後続mvが中間失敗を隠した | 専用AVD/自己packageを確認し、UIDと親directoryラベルを実測。明示chown/chmod/chcon、&&、公開後メタデータ/アプリUID読取り/SHA一致を検証。PCで原作画面へ復帰。phoneにはfixtureを移さない |
| ADB短時間tapを原作が取りこぼす | 同一点150msのDOWN保持では原作画面が応答。フレーム間取りこぼし以外の因果は未証明 | 私的PC操作補助で同一点swipe150msと画面遷移待ち。入力成功を画面で確認し、未反映クリックを育成成功に数えない |

全777テスト765成功/12skip、完成候補ARM64/私的原本ゲート14テスト、Agent terminal、独立レビューでP1/P2なし。同署名の初回スマホ更新は451保存ファイルの前後SHA保持を確認。所有者の追加指定で実購入/XP消費/育成後保持の受入は本人へ引継ぎ。詳細は[更新001](../updates/2026-10-12-update-001-xp-level-cap.md)。

## 更新001の本人検証で判明した未達とV3再調査

本人は正常プレイを確認した後、ランク1600のディオラムスLv30停止と、まどか第三進化非表示を報告。育成・進化受入は失敗として記録する。本人は元catseye消費を使う方法と、私的バックアップ後の研究状態初期化を承認。スマホ再導入はPC受入後に行う。

| 観測 | 確認した原因・未証明の範囲 | 修正・予防 |
|---|---|---|
| Lv30の旧XP adapterが拒否を解除しない | catseye分岐後のx20はunitではなくunit×256。元getter末尾も実UI inline経路では未呼出し | 元XP経路へ復元。元catseye eligibility/追加可用数のrank/stage条件のみ適応。実分岐命令・レジスタ・原本.text復元の回帰を追加 |
| まどか等32所有体の素材第三進化が未解放 | 元TF metadataは存在するが可用フラグ0。ディオラムス2との違いは進化済み状態。XP adapterがフラグを破壊した証拠はない | 元TF ID/Lv/XP/素材条件を満たす所有対象だけ初回0→1。選択形態・進化済み状態を付与せず、素材消費は元UIへ残す。実UI因果確認は別受入 |
| 完成NDKライブラリだけUnicornでaddress0x28読取り失敗 | 最小試験ライブラリと異なり、実ビルドにはAndroid TLS stack canaryがある | harnessでTPIDR_EL0とTLS+0x28を供給。製品のstack保護は外さず、実完成ライブラリも検証 |
| 大容量PCバックアップTARが途中切断 | `adb exec-out tar`の出力末尾がなく、archive検証で検出。recursive pullも途中終了した。後者の原因は未確定 | 削除前に個別file取得/SHA照合へ切替、完全TAR manifest一致後にのみ自己AVDをclear。部分取得をバックアップ成功にしない |
| 初期化後の615MB処理失敗 | `pm clear`で外部393stageも消え、通常runはstageを再配置しない。`stage-not-ready`を観測 | 元393size/MD5とguestUIDを再照合して再配置、import完了後の冷起動でタイトル到達確認。旧SAVE注入やnative download条件変更で隠さない |

V3全779テスト767成功/12skip、完成NDK/元ELFの関連21テスト、Agent terminal PASS。初期化PCの元起動・初期profile成功まで確認。原作UIの素材消費・育成・進化・冷起動保持とスマホ再導入は未完了として追跡する。[最新調査](2026-10-12-xp-only-level60-investigation.md)。

## 2026-10-13 — 更新002のPC受入・完全再導入・受渡し検証

前節のPC UI／スマホ未完了は当時の状態。更新002で実消費・境界拒否・まどかの単独フラグA/B・ほむら進化・冷起動保持を検証し、スマホへ承認済みのクリーン再導入を完了した。[検証範囲](../updates/2026-10-13-update-002-catseye-evolution.md)。

| 失敗／観測 | 根拠と限界 | 修復／運営原則 |
|---|---|---|
| PC画面の古い座標で別メニューへ入った | introのSKIPとtitleのinboxが同じ位置。撮影後の遅延やchapter selector省略を盲目的な連続tapが扱えなかった | 私的PC自動操作は直前画像で画面を照合し、未知画面で停止。inboxは未受入として残し、育成修正にUI待機問題を混ぜない |
| スマホprivateファイル名検証でSDK cacheを拒否 | 正当な名前に`+`と`#`がある | app-own範囲・path traversal拒否を維持したまま許容文字を修正。長いlogical名は平坦なhost objectに写し、元名はTARで保つ |
| スマホbackupの大きいraw catがtimeout | その失敗時はデータ削除前。完全コピーと判定しなかった | app-own base64取得へfallbackし、456件個別SHA／完全TAR一致後にのみ承認済み初期化 |
| APK receiptの読み取りがCP932で失敗 | 日本語labelを含むUTF-8 JSON。削除前guardで停止 | private helperも`encoding='utf-8'`を指定。検証未完了のまま削除しない |
| shellのpm clearをOEMが権限拒否 | ordinary ADB UID2000はCLEAR_APP_USER_DATAを許可されない。root・security設定変更はしなかった | appの実UIDとown cwdを照合後、本人承認範囲で自身UIDからOSのpm clearを実行しSuccessを確認。公式appには適用しない |
| PC recursive／個別pullが途中失敗 | 元エラー応答は汎用例外で失われ、直接原因は未確定。失敗位置付近の個別再取得はSHA一致 | `collect_pc_private_state`は個別pull・最大3retry・私的失敗JSONと全source SHA／TAR／phone SHAを使用。443件完了まで本番公開しない |
| findが個別sha256sumエラーを成功終了として返す | 独立レビューの合成再現で、一部stdout＋stderrでも不完全manifestを合格にした | 初回manifestのreturncode／stderrをpull前に検証。SHAエラー、破損copy、unsafe path、retry上限を恒久テストに追加 |

全785テスト773成功/12skip、関連21実ライブラリ／原本テスト、Agent terminal、独立再レビューを確認。スマホ起動と初回起動前の初期状態照合までの受入であり、全所有キャラ全UI／全戦闘やinbox機能を合格とした意味ではない。


## 2026-10-15 — 運営更新でHGT00、ログイン・開催内容が非表示

| 観測／原因 | 修正と確認範囲 |
|---|---|
| 本人のHGT00。既存診断ログでsale/gatya応答後にitemが503、native readinessはunavailable | 読取り専用JNIがPC JNI observer state=2だけに依存していた。スマホの既存完全native hook経路も、元描画帰還・source一致・同一GL TIDを確認して受け付ける。二重hook・SAVE書込みなし |
| APK6本の署名・hash一致だけでは実運営の回復を証明できなかった | 初回の導入整合性PASSと本人の機能FAILを別々に保持。修正版のARM64関連4件／build／PC通常再取得を確認し、同署名・データ保持で再更新。スマホ表示は本人確認待ち |
| 停止済みアプリの既存ログがring bufferから消えていた | 今回限定の読取り許可と本人による再現後、自アプリPID・固定イベントだけを取得。AIによるスマホ起動・画面操作・SAVE取得は追加しない |

詳細と候補識別は[運営バッチ履歴](2026-10-14-original-liveops-batch1.md)を参照。今後のreadonly readinessは、一方の診断backendの有無をゲームサービス全体の準備条件にしない。


## 2026-10-15 — ガチャ運営の表示・カテゴリ・PC日時

| 観測／原因 | 修正と再発防止 |
|---|---|
| 同時3レア／通常行を生成したが実PCでは週特選だけ表示 | AVDのGMTとJST予定の不一致。同一候補を専用AVDのAsia/Tokyoで再起動すると表示。epoch一致だけで開催判定の整合性を判断しない。ops captureにインストール／起動前のJSTゲートを追加 |
| にゃんこガチャに黄色字幕・季節期限を付けていた | 所有者指定で常設通常N0＋マタタビ入りN3へ変更。空メッセージとシーズン非連動の長期元reader期間。最終PCで2タブ・字幕／期限なし確認 |
| アイテム専用N3のsource照合を拒否 | 通常ガチャにもキャラ非空条件を課していた。通常は3元テーブルのどれかが非空であることとticket20で照合。レアのrarity検査は維持 |
| 新候補作成後、旧候補UI helperが6SHA不一致で停止 | 最新buildと導入済みを混同しない正常なゲート。旧候補の結果確定だけ既存PC-BUILDを固定して全6SHAを再照合。誤ラベルsnapshotを最終証拠にしない |
| スマホ更新preflightでUSB offline | APK更新前に停止。接続復帰待ち。installer Successや本人動作確認へ読み替えない |

上記offline停止後、本人の接続復帰を受けて再実行し、同署名・全6SHA一致・UID/dataDir保持で更新成功。offline失敗と導入整合性の成功、本人のゲーム動作確認待ちを別々に保持する。

GitHubの `1adc14a` ではTest tooling／Agent terminalがFAIL。既存の元backup合成試験が旧throw専用guardを文字列比較し、JVM原作stubには前工程で追加したindividual callback APIが欠けていた。現行のlocal-bootは未知要求へ元handleの503/errorを返すため、例外だけを拒否と認める旧期待値も更新した。503/error・原作super送信0の実行時検査は残し、getTimeのH→D→F順序・200・direct bodyを追加。ゲーム側は変更せず、関連10件をJDK17で実行してPASS。全CIの結果は当該commitのActionsで別管理し、以前のFAILを削除しない。

関連27 tests＋PC timezone回帰1 test、buildとPC表示／元抽選の範囲は[運営履歴](2026-10-14-original-liveops-batch1.md)を参照。最初の試験モジュール名誤記、private fixture違反、evidence runnerの相対path誤記も私的FAILログを保持した。
