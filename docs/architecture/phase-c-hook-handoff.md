# Phase C Handoff — Exact Original Runtime Hook Proof

Status: ready after Phase-B provider/service foundation.

## Scope

Phase C is the first phase allowed to connect Kneekura semantics to original JP
15.7.1 runtime decisions. It must **not** redesign screens.

The goal is to promote one candidate at a time from evidence to a version-pinned
hook contract while preserving the original Battle Cats UI/scene flow.

Anchor:

- JP 15.7.1 / versionCode 1507010
- ARM64 `libnative-lib.so`
- SHA-256 `333d2974ab2ff881fd70087fd62dea7d12d82addbc55cab2f2a675ad67e3a7e2`
- GNU build ID `8cb3815648eb9642da10bfb039d71bff7a3519bd`
- original launcher `jp.co.ponos.battlecats.MyActivity`

Primary evidence:

- `docs/references/native-service-map-jp15.7.1.{md,json}`
- `docs/references/hook-candidate-matrix-jp15.7.1.{md,json}`
- `docs/architecture/provider-abi-contract.md`
- `docs/architecture/clock-sidecar-profile-contract.md`

## Phase-C order

### C1 — network request lifecycle

Leading seam:

- Java `MyActivity.newHttpRequest(...): int`
- Java `MyActivity.isNetworkAvailable(): boolean`
- existing JNI response ingress:
  - `newResponse`
  - `onResponseCodeHeaders`
  - `onResponseData`
  - `onResponseFinish`

Research procedure:

1. build the owner-local Personal or Practice boot smoke;
2. keep Kneekura feature mask zero;
3. use temporary research instrumentation to log:
   - URL/path;
   - HTTP method;
   - returned request id;
   - response callback order;
   - response code;
   - body length;
4. exercise one low-risk original request;
5. repeat in airplane mode;
6. identify whether a local response can be injected through the same callback
   chain without changing scene code;
7. record exact method/bytecode/native anchors.

Promotion criterion:

- one original request can be locally satisfied with original caller/scene
  unchanged;
- feature OFF follows the original request path;
- failure to recognize a request falls through to original behavior.

Fallback if bridge is unsuitable:

- inspect the native `MyActivity_request` dispatcher next;
- do not drop immediately to socket/TLS interception.

### C2 — original event/stage availability

Candidate data:

- `/event.json`
- `eventDisplayData.json`
- `Map_option.csv`
- `Stage_option.csv`

Goal:

return a local event snapshot through the proven request/provider seam so the
**original stage-selection UI** surfaces locally imported event/collaboration
content.

Pass examples:

- a Legend map remains normal;
- 狂乱/大狂乱 appears through original event/stage UI;
- a historical collaboration present in local exact data appears without a
  live server schedule;
- original active/local story progression is not hidden.

No custom stage list is accepted as product evidence.

### C3 — gacha data-only proof first

Exact data anchor:

`EventGatya_Setting.csv`

Battle Cats Complete independently reconstructs each gacha row as:

`gacha id -> repeated (group, unit, value)`

First attempt:

1. add a test-only permanent local gacha definition;
2. keep original gacha scene/assets/buttons;
3. verify original capsule/result animation and acquisition path;
4. do not yet use the complete Super Kneekura pool;
5. prove a tiny safe two/three-unit test pool first.

Then:

- derive exact JP 15.7.1 original Rare Capsule rarity vector;
- build compatibility-safe pool;
- apply provider cost policy:
  - single 150 Cat Food;
  - eleven 1500 Cat Food.

Fallback:

only trace result/provider logic if original data alone cannot register the
permanent entry or cost behavior.

### C4 — login stamp original scene

Exact data anchor:

`DailyLoginEventGrade.json`

Target:

- preserve original stamp UI;
- inject local-day/claim eligibility only after exact wall-clock and claim
  boundaries are proven.

Approved local-day semantics already exist in the provider core:

- one claim per newly observed day;
- rollback grants nothing;
- large forward jump grants one next stamp;
- last stamp wraps to first.

Do not connect `appUpdateDraw` / `steady_clock`.

### C5 — first-clear Cat Food

The provider table is implemented but pure/unconnected.

Target path:

1. observe original win settlement;
2. identify stable stage identity + star/difficulty variant;
3. grant after original clear commit succeeds;
4. mark Kneekura sidecar claim atomically;
5. display through original reward/result presentation if possible.

Approved table:

- 1–3 -> 1
- 4–6 -> 2
- 7–8 -> 3
- 9–10 -> 5
- 11 -> 8
- 12+ -> 10

Replay must not farm the one-time bonus.

## Profile integration order

### Practice Clean first

Use original new-game initialization and preserve original tutorial/starter
state. Do not synthesize a fake fresh save.

### Personal MAX second

Only after exact save/inventory APIs are mapped safely:

- apply MAX values through known original state fields/functions;
- keep original serializer authoritative;
- never mutate the official PONOS package sandbox.

The separate package identity remains the isolation boundary.

## Temporary instrumentation rule

Allowed for research:

- Frida;
- logcat;
- Java method logging;
- temporary native probes.

Not allowed in shipping artifact:

- Frida gadget/runtime dependency;
- debug server;
- localhost HTTP requirement;
- general-purpose hook framework left enabled.

Every research hook must be replaced by a narrowly version-pinned static patch
or removed.

## Failure/repair discipline

For every promoted hook, record:

- exact input binary hash/build id;
- original bytes/method hash;
- patch bytes or method transformation;
- expected input/output contract;
- feature-off path;
- feature-on path;
- unrecognized/failure fallback;
- device evidence;
- regression test.

If a hook crashes or changes an unrelated original screen, revert it and record
the failure rather than adding compensating patches blindly.

## Device evidence template

For each Phase-C experiment capture:

- build flavor/package;
- source export SHA;
- patch ledger SHA;
- device Android version/ABI;
- launch result;
- original screen used;
- action taken;
- expected original behavior;
- Kneekura extension behavior;
- airplane-mode result;
- relevant logcat excerpt;
- PASS / FAIL / INCONCLUSIVE.

## Exit criterion

Phase C is successful when the first real Kneekura behavior is visible **inside
an unchanged original Battle Cats scene** and can be disabled back to the
original path with one feature gate.

That is the proof that this project is modifying Battle Cats rather than
building another game beside it.
