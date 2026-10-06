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

The final Phase C research proof appends exact Rare Gacha set **1089** using
only original-format DataLocal tables.

Pinned exact derived proof:

- set id: 1089
- unit ids: 37 (Rare), 30 (Super Rare), 34 (Uber Rare)
- visible option clone: set 49
- original rows replaced: false
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
8. ask one manual original Rare Gacha UI question.

The manual check does **not** ask the owner to draw. It only determines whether
the unchanged original schedule already exposes the appended set.

If an additional/duplicate banner is visible, the original schedule already
selects the appended data and Phase C can close.

If no additional banner is visible, static/data proof still passes; the result
is evidence that the next narrow implementation must be a local
**gacha-visibility schedule provider**. It is not a reason to replace the
original gacha scene.

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
