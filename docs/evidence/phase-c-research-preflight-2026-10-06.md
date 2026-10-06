# Phase C Research Preflight — 2026-10-06

Status: repository-side preflight **READY**.  
Runtime observation on the owner's device is the next evidence gate.

## Exact anchors

The preflight fails closed unless all of these remain unchanged:

- JP versionCode: `1507010`
- exact ARM64 native SHA-256:
  `333d2974ab2ff881fd70087fd62dea7d12d82addbc55cab2f2a675ad67e3a7e2`
- GNU build ID:
  `8cb3815648eb9642da10bfb039d71bff7a3519bd`
- exact base.apk SHA-256:
  `60e5e9df891b7be487abc4590fb3ca2e98218225efedbe4ba26b39dc10ce5c9a`
- exact `MyActivity.newHttpRequest` instruction SHA-256:
  `14f896e5b42b8e5b8ab50f756bdc79ad44614325eb153ab99ffcdafb98c70a80`

Preferred original service seam:

`MyActivity.newHttpRequest`

Unknown requests must continue through the exact original method.

## Research package

Disposable package:

`jp.kn.trace.battlecats`

It is neither Personal MAX nor Practice Clean and its save sandbox is not
authoritative progression state.

The owner-local research builder requires:

- exact user-owned JP 15.7.1 export;
- built `libkneekura.so`;
- user-supplied AArch64 `libfrida-gadget.so`;
- local signing key.

No Frida binary is downloaded or stored by the repository.

## Observation harness

`research/frida/trace_service_bridge.js`:

- hooks only the exact original `MyActivity` bridge methods;
- calls every original implementation unchanged;
- does not replace network availability;
- does not copy ByteBuffer body contents;
- does not log header values;
- redacts URL query values;
- emits sanitized `KNEEKURA_TRACE` records.

`tools/base_mod/summarize_service_trace.py` then reduces those records into:

- method catalog;
- request handles;
- response callback order;
- per-request lifecycle summaries;
- thrown errors.

## Login evidence frozen before runtime observation

The exact local fallback remains:

- template id: **949**
- cycle: **7 days**

Its original Battle Cats reward row remains authoritative. The shim does not
duplicate the XP/ticket quantities.

Original resource/data anchors for login text, background and comeback stamp
animation are already pinned.

## Gacha evidence frozen before runtime observation

Exact local JP 15.7.1 R1 union:

**495 unique original Rare-Gacha unit ids**

This is the compatibility seed, not the final pool.

The exact standard Rare Capsule probability vector remains deliberately
unresolved. The project must observe an exact original banner/event/draw
decision before freezing that vector.

A tiny append-only original-format structural set can already be generated:

- new set id: 1089
- no original set row replaced;
- R2/R3 empty;
- pool restricted to original local-R1 ids;
- explicit cheat/test unit 673 rejected.

It is not promoted until the original gacha scene proves it can consume the
set safely.

## Data patch path

The Phase-C preflight includes a deterministic DataLocal writer:

- preserves original manifest entry order;
- copies untouched encrypted chunks byte-for-byte;
- re-encrypts only explicit changed entries;
- rebuilds offsets;
- decrypts the rebuilt output again and verifies payload hashes;
- changes only `assets/DataLocal.list` and `assets/DataLocal.pack` inside
  InstallPack at the APK data-patch stage.

This is the preferred extension path before any native/gameplay hook.

## Automated audit

Run:

```bash
python -m tools.base_mod.phase_c_preflight
```

The audit verifies that:

- exact native/base/HTTP hashes still match;
- research package identity remains isolated;
- trace stays call-through;
- template 949 / 7-day cycle remains pinned;
- R1 seed remains 495;
- rarity-rate evidence gate has not been bypassed;
- research/data patch tools are present.

Expected status:

`ready_for_owner_device_observation`

## Patch-kit artifact

Latest source-free patch kit validated during the handoff:

- Actions run: `37456324529`
- artifact id: `11409783326`
- artifact SHA-256:
  `2c0dde319ac22f6cd9913cb9964f75f29f5704f728973b7b426ebc3d29aba842`

It contains no Battle Cats APK payload.

## Next gate

One original low-risk request must be observed twice:

1. normal connectivity;
2. airplane mode.

Required evidence:

- original screen/action;
- sanitized URL path and method;
- returned request handle;
- `newResponse/onResponseCodeHeaders/onResponseData/onResponseFinish` ordering;
- response code/body length metadata;
- failure behavior in airplane mode;
- confirmation that tracing itself did not alter the scene.

No product HTTP patch is enabled before this evidence exists.
