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
