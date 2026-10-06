# Phase C Research Preflight — JP 15.7.1

Status: **promoted past transport observation; ready for original-UI data proof.**

This document is the single repository-side checklist that ties the Phase C
research evidence together before any larger original-UI content proof is
attempted.

## Exact runtime anchor

Pinned original application:

- JP 15.7.1 / versionCode 1507010
- base.apk SHA-256:
  `60e5e9df891b7be487abc4590fb3ca2e98218225efedbe4ba26b39dc10ce5c9a`
- ARM64 libnative SHA-256:
  `333d2974ab2ff881fd70087fd62dea7d12d82addbc55cab2f2a675ad67e3a7e2`
- build id:
  `8cb3815648eb9642da10bfb039d71bff7a3519bd`

Pinned HTTP Java-path instruction hashes:

- `MyActivity.newHttpRequest`:
  `14f896e5b42b8e5b8ab50f756bdc79ad44614325eb153ab99ffcdafb98c70a80`
- `La32.run`:
  `b1a8679be3ccf9deadf5a5ef6eca2730220c4414ef08064e12b3f1220ef547e7`
- `Lz22.run`:
  `ad74dcde42dcfa2533de3f57b1b86a04d46326ce5c2c90ac46b4db3c9a669d7a`
- `Lz22.a` offline fallback:
  `b03f69b5a8187bee470b7fdbcee8416e3a01b667f080f37a2042786e3efd1abe`

Any drift fails closed.

## Research package and observation path

Disposable research package:

`jp.kn.trace.battlecats`

Research-only tools:

- `research/frida/trace_service_bridge.js`
- bundled Frida-17 Java bridge agent
- `tools/base_mod/capture_service_trace.py`
- `tools/base_mod/summarize_service_trace.py`

The trace contract is metadata-only:

- request method;
- redacted URL path/host;
- request id;
- timeout;
- null/empty shape metadata;
- thread name;
- sanitized callback sequence;
- response status/body length only.

No raw response body or response-header values are required.

## Transport proof status

The transport proof is complete.

The owner-device run established:

- original `newHttpRequest` is live;
- returned int is the callback correlation id;
- request-handle/map state matches exact static code;
- callbacks are delivered on the GLThread path;
- unknown requests can remain on exact original transport;
- first local replay can use the exact original offline fallback semantics.

The Frida-free static bridge has also passed the owner-device smoke:

```text
package_alive      true
local_replay_seen  true
frida_seen         false
fatal_seen         false
```

Therefore Frida is no longer part of the product-path design.

## Static bridge preservation contract

Shipping-oriented static bridge:

- flavor MyActivity subclasses original MyActivity;
- bridge lives in appended `classes5.dex`;
- original `classes4.dex` `newHttpRequest` body stays unchanged;
- exact recognized backup request may be handled locally;
- feature OFF and every classifier miss call `super.newHttpRequest`;
- static product path contains no Frida runtime;
- original `extractNativeLibs=false` behavior is preserved.

## Original login anchors

The preflight requires the exact original runtime/data anchors already pinned in:

`docs/evidence/original-login-gacha-runtime-anchors-jp15.7.1.json`

Relevant original assets/loaders include:

- `DailyLoginEventData.csv`
- `DailyLoginEventGrade.json`
- `StampData.csv`
- original `DailyLoginUpdate` RTTI/resource region

Comeback template selection remains pinned to event **949**, seven days.

No custom login screen is authorized by this preflight.

## Original gacha anchors

Exact original gacha loader region:

`0x5ed65c`

It consumes:

- `GatyaDataSet%@1.csv`
- `GatyaDataSet%@2.csv`
- `GatyaDataSet%@3.csv`
- `GatyaData_Option_Set%s.tsv`

The local R1 union currently supplies 495 conservative Rare-through-Legend
candidate ids.

The exact rarity probability vector remains intentionally unresolved. This is a
hard gate: no invented live-like probability vector is accepted.

## Tiny data-only gacha prototype

The reproducible tiny prototype tool is:

`tools/base_mod/super_gacha_data_prototype.py`

Its preservation rules are:

- append one new set instead of replacing an original row;
- use only unit ids already present in exact local R1;
- reject explicit test/cheat id 673;
- reject duplicate ids so duplicate weighting cannot appear silently;
- keep R2/R3 empty;
- clone existing original option metadata;
- do not define a rarity probability vector;
- do not claim banner visibility, acquisition or save behavior is proven.

This is deliberately a data-format proof, not yet a finished Super Kneekura
Gacha.

## One-command repository preflight

Run:

```powershell
python -m tools.base_mod.phase_c_preflight --root . --output phase-c-preflight.json
```

PASS means the repository agrees on:

- exact HTTP anchors;
- research package identity;
- call-through trace semantics;
- trace summarizer;
- static Frida-free bridge;
- original login/gacha anchors;
- tiny append-only gacha prototype;
- rarity-rate unresolved gate.

## Next gate

The next Phase C proof is not more transport tracing.

It is one **original-UI data proof**:

- append a tiny safe original-format set or local event snapshot;
- feed it through the existing original data path;
- make it visible in unchanged original Battle Cats UI;
- keep feature OFF / unknown data behavior unchanged;
- only then expand toward the full local event catalogue or Super Kneekura pool.
