# Phase C Final Shipping Parity — JP 15.7.1

Status: final repository-side parity gate for Personal/Practice and the isolated
original-UI gacha proof.

## Product profiles

The shipping profiles remain:

- Personal MAX package: `jp.kn.white.battlecats`
- Practice Clean package: `jp.kn.clean.battlecats`

At the Phase C shipping-parity gate both profiles are deliberately **feature
OFF**. They preserve the original Battle Cats launcher:

`jp.co.ponos.battlecats.MyActivity`

and do not contain the research/static bridge launcher class.

## Product cleanliness audit

`tools/base_mod/verify_shipping_profile.py` audits one signed Personal or
Practice split set.

Required PASS conditions:

- exact-source `parity-report.json` says original scene host is preserved;
- verification-harness UI is absent;
- original libnative export surface is preserved;
- Kneekura shim dependency is present;
- InstallPack game payload is unchanged;
- shim patch ledger says feature mask default is zero;
- extension-OFF fallthrough is true;
- original `extractNativeLibs=false` remains intact;
- no `classes5.dex` research/static HTTP bridge leaks into feature-OFF product;
- no Frida Gadget/config/script entry exists;
- no `KNEEKURA_TRACE`, `KNEEKURA_REPLAY` or
  `KNEEKURA_STATIC_HTTP` research markers exist in product DEX/native payloads.

The exact-source manual CI workflow also invokes this verifier for both
Personal and Practice when the owner supplies the private source token.

## Already-proven static HTTP bridge

The isolated research package has already passed the Frida-free static bridge
Android smoke:

```text
package_alive      true
local_replay_seen  true
frida_seen         false
fatal_seen         false
```

The first promoted local request remains the exact observed backup GET family.
Every classifier miss and feature-OFF path calls original
`super.newHttpRequest`.

The offline fallback semantics are exact JP 15.7.1 behavior:

```text
newResponse(id, 0, url, "{}", null, true)
```

## Original-UI gacha proof

The final Phase C research proof appends exact Rare Gacha set **1089** through
the existing **DownloadLocal overlay** while keeping built-in
`DataLocal.list/.pack` byte-identical.

Pinned exact derived proof:

- set id: 1089
- unit ids: 37 (Rare), 30 (Super Rare), 34 (Uber Rare)
- visible option clone: set 49
- original DataLocal bytes changed: false
- original rows replaced: false
- DownloadLocal overlay additions: four gacha table files
- native pack/list MD5 bypass: false
- R2/R3: empty
- BannerON: 1
- rarity probability vector: intentionally undefined
- live visibility schedule: intentionally undefined

No original gacha/capsule/result scene code is patched.

## Final one-command smoke

Windows owner-device runner:

`tools/base_mod/run_phase_c_final_smoke.ps1`

It performs:

1. build Personal feature-OFF profile;
2. run shipping cleanliness audit;
3. build Practice feature-OFF profile;
4. run shipping cleanliness audit;
5. build exact set-1089 research gacha proof;
6. install the isolated research proof;
7. verify process liveness, Frida absence and fatal absence;
8. classify the exact 35-lane / 615.69 MiB original server-asset bootstrap;
9. if required, let the unchanged original Battle Cats downloader complete that
   one-time bootstrap in the isolated research package;
10. only after the normal UI is reachable, ask one manual original Rare Gacha
    visibility question.

The runner no longer uninstalls the research package between retries, so the
original downloader cache can survive same-signature `-r` upgrades.

The manual check does **not** ask the owner to draw. It only determines whether
the unchanged original schedule already exposes the appended set.

A result obtained before the Rare Gacha UI is reached is classified as a
**server-asset download gate**, not a schedule failure.

If the Rare Gacha UI is reached and an additional/duplicate banner is visible,
the original schedule already selects the appended data and Phase C can close.

Only if the Rare Gacha UI is reached and no additional banner is visible does
the result justify a narrow local **gacha-visibility schedule provider**. It is
not a reason to replace the original gacha scene.

## Completion rule

Phase C closes only when all of the following coexist:

- Personal/Practice shipping profiles contain no research runtime;
- feature-OFF parity preserves the original scene host;
- Frida-free selective HTTP bridge has real-device evidence;
- exact offline fallback is pinned;
- set-1089 original-format data contract is verified append-only;
- the final owner-device original Rare Gacha scene check is recorded.

This keeps the distinction clear between a proven static data extension and a
proven original-scene visibility decision.


## Research-only storage redirect

To cross the fresh-package 615.69 MiB bootstrap without root, the isolated
research gacha proof can override `getFilesDir()` to return its app-specific
external files directory. The original downloader and original UI remain
unchanged.

This redirect is build-time opt-in and is enabled only for the research gacha
proof. Personal/Practice feature-OFF shipping profiles preserve the platform's
normal internal `getFilesDir()` behavior.


## H01 checkpoint

The first runtime proof rewrote DataLocal and reached **H01 immediately after
the original 615.69 MiB server bootstrap completed**.

External Battle Cats modding references associate H01 with pack/list MD5
integrity checks. Rather than disable that integrity path, the proof has been
redesigned to use the game's existing DownloadLocal overlay family.

The final runner now refuses to reuse an older proof unless its ledger states:

- `datalocal_byte_identical=true`;
- exactly four `downloadlocal_overlay_entries`;
- research external-files cache mode enabled.

If H01 still appears under those conditions, it is recorded as a distinct
`data_read_error_h01` gate and no gacha-schedule inference is made.
