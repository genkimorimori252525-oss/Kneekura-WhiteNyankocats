# KNEEKURA Update 1.01 — delivery/readiness ledger (JP15.7.1)

**Intent:** one offline, original-scene-preserving user update combining verified existing native level-cap unlocking, user-approved third-form Ultimate Madoka adjustment, and Godzilla No.703 first-form update. This document is a design/build-readiness ledger, **not proof of delivery or installation**.

## User-approved changes

| Unit / feature | Approved exact spec | Game/runtime status |
|---|---|---|
| Native level-cap unlock (existing) | 323 eligible -> max60; 493 -> max50; 11 -> max20; 8 -> max1, preserve player progress | Implementation exists, repo tests pass; owner-device USER_GATE for any new run |
| No.289 / Ultimate Madoka, form2 | Lv30 attack **28,000**, sensing **750**, EoC2 cost **4,550**, recharge **155s/4650f**; preserve LD450–800, abilities and special death animation | Approved spec only; no installed override / user-device proof |
| No.703 / Godzilla cat, **confirmed form0** | Lv30 **150,000** damage in three hits **50,000×3**, sensing **2,950**, EoC2 cost **9,800**, recharge **500s/15000f**, attack cycle **15s/450f**; enemy castle total **1 HP per whole attack sequence** | Approved spec only; no installed override / user-device proof |

## Why 1.01 cannot honestly be called an installed update yet

- The source `DataLocal/unit289.csv` row2 and `unit703.csv` row0 contain native **integer Lv1 attack values**. At Lv30 their direct 17× scale cannot represent 28,000 or each 50,000 exactly. Closest straightforward integer preview yields Madoka **27,999** and Godzilla **49,997×3 = 149,991**; runtime correction is required for exact user values. EoC2 requested costs also imply half-unit raw results, so UI-rounding needs actual engine proof.
- The raw Godzilla attack-period candidate is near **449f** (not certified 450f) with the original friendly 41/65/90f hit animation. The enemy source 130/170/210f timing cannot simply be injected into a different friendly animation without verification/replacement.
- **Enemy castle damage** is now implemented as a compiled, feature-OFF-by-default native C **decision module** (kneekura_battle101.c, ABI v1). It enforces exact Lv30 Madoka 28,000 and Godzilla 50,000 per hit, and a battle-scoped one-HP-per-three-hit castle budget with replay/cat isolation. Native C tests OFF/ON pass. The **original battle-engine hook and combat callsite are NOT connected**; no game damage has changed. Python reference logic alone was insufficient, and this C module now fills that policy gap.
- A `DownloadLocal` overlay can preserve the original `DataLocal` pack (important because direct DataLocal changes caused H01), but static encryption/roundtrip proof does **not** prove original game's `unitNNN.csv` override precedence or native battle acceptance.
- The user-selected cropped Godzilla image is still not a native animation rig. The historical Server index identifies enemy visual source **550_e**, with exact seven-file provenance: PNG in MNumberServer, cut/model/four maanim motions in WImageDataServer; the existing first-form target is **702_f**. An owner-local encrypted Server extractor exists, and encrypted pair roundtrip tests are now covered. Neither source game art bodies nor a verified mirrored/converted friendly rig have been supplied or installed. The second form 702_c is untouched.
- We have no physical owner Android device / matching personal keystore in this session. Installing a differently signed APK with uninstall/clear-data would violate the preserve-existing-save requirement.

## Packaging contract

An owner-local, source-only **1.01 preflight kit** can inspect the pinned export, generate isolated two-unit CSV and `DownloadLocal` overlay *candidates*, and call the existing native-level-cap runner only with deliberate explicit user action. This **must be labeled PREVIEW/NOT INSTALLABLE**; no automatic APK install or balance `-Apply` flag is allowed until original UI, H01, source SHA, native damage hook and rollback are verified.

Release acceptance: strict per-form diff, exact Lv30 attacks, exact castle 1 total on every attack sequence, original visuals intact, no change to player SAVE_DATA except optional vetted level-cap migration, same-signer incremental Android installation, offline battle, original UI, forced stop/restart, verified rollback. Only then mark 1.01 RELEASED.

Authoritative numeric spec: [kneekura-balance-2026-10-09.json](kneekura-balance-2026-10-09.json). Related [Issues #2](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/2), [#3](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/3), draft [PR #4](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/pull/4).
## 2026-10-09 continuation: native code built, extraction tests validated

Status: **DEVELOPMENT PROGRESS, NOT RELEASED**. Existing native shim ABI2 remains unchanged; the separate battle101 policy ABI1 introduces feature bit 7, disabled with default feature mask zero. Code under native/kneekura-shim uses a per-battle bounded tracker (max256 deployed cat IDs), attack-sequence IDs, hit masks, a single castle damage credit, and strict invalid-context protection. Both source-level native feature-OFF and feature-ON tests, Android NDK build, Linux Python tests and Windows/Ubuntu terminal tests passed in GitHub Actions. The original stripped JP15.7.1 ARM64 library SHA256 333d2974ab2ff881fd70087fd62dea7d12d82addbc55cab2f2a675ad67e3a7e2 matches the pinned shim; **no original castle HP subtraction function has been identified/connected**.

Animation: server index artifact ID 11391338442 identifies exact enemy stem 550_e and cat form0 stem 702_f, with families MNumberServer and WImageDataServer. New owner-only extractor tools/base_mod/extract_godzilla_owner_rig.py is covered by both mock and synthetic real-encrypted-Server tests. Actual owner-held Server pack bytes are needed for conversion; no conversion or gameplay overlay has been installed.

Next integration gates: verify DownloadLocal priority for unit CSV in original UI, identify exact native base-hit and castle HP-debit paths, ensure exact 450-frame attack cycle and requested EoC2 cost display, build/test enemy model orientation and 130/170/210 timing for allied animation, then test backup-preserving same-signature Android updates. See docs/evidence/update-1.01-native-combat-animation-gates.md and docs/evidence/godzilla-enemy-no552-asset-receipt-jp15.7.1.md.