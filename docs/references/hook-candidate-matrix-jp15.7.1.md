# Phase-B Hook Candidate Matrix — JP 15.7.1

Anchor: exact JP 15.7.1 ARM64 `libnative-lib.so`.  
Policy: a public reverse-engineering repository may explain **what** a subsystem
does; only the exact anchored build decides **where** Kneekura may hook it.

Machine-readable companion: `hook-candidate-matrix-jp15.7.1.json`.

## Result

There is now a clear priority order for the offline conversion:

1. **network:** original Java `MyActivity.newHttpRequest` /
   `isNetworkAvailable` bridge;
2. **gacha/login/events:** original data loaders and scenes first;
3. **clock:** prove the exact wall-clock utility before interception;
4. **save:** do not hook the original serializer yet—use a Kneekura sidecar;
5. **transport:** retain the already proven exact-version `libkneekura.so`
   bootstrap.

No gameplay/service hook is activated in Phase B.

## Network — HIGH candidate

Exact JP 15.7.1 contains ordinary Java methods:

- `MyActivity.newHttpRequest(...): int`;
- `MyActivity.isNetworkAvailable(): boolean`.

The native binary references those method names and exports the response ingress
JNI functions `newResponse`, `onResponseCodeHeaders`, `onResponseData` and
`onResponseFinish`.

That is much better than intercepting raw TLS or rewriting every service URL.
It gives a plausible single seam where selected original requests can be
answered by a local provider while every caller and scene stays intact.

**Phase C test:** trace one harmless original request end-to-end and prove that
the Java bridge plus existing response callbacks fully describe its lifecycle.

## Clock — MEDIUM candidate

Battle Cats Complete reconstructs:

`now_seconds -> std_chrono_system_clock_now -> platform.system_clock_now`.

That aligns with the exact JP binary importing `system_clock::now`, `time`,
`localtime_r` and `mktime`.

The exact binary also proves a trap: `appUpdateDraw` uses
`steady_clock::now` for update/render elapsed time. Hooking it for daily
login would be architecturally wrong and could damage animation/battle timing.

The `0x4734xx–0x473cxx` local-date utility family remains a medium-confidence
candidate until a device trace connects it to login/event decisions.

## Login bonus — HIGH data / MEDIUM call-site

Exact JP has `DailyLoginEventGrade.json`; BCC independently reconstructs its
loader into stamp group, grade and condition data. BCC also models
`battle_check_login_bonus` as a scene-host action invoked from existing menu,
battle and return flows.

That supports the preservation-first design strongly:

- keep the original stamp assets/data parser;
- keep the original login scene;
- replace only day/claim state after the exact call path is proven.

No custom stamp UI is needed.

## Super Kneekura Gacha — HIGH data seam

Exact JP has `EventGatya_Setting.csv`; BCC independently parses each gacha id
as repeated `group, unit, value` triples.

Therefore the first implementation attempt for スーパーにーくらガチャ should
be **data-only**: register a permanent original-format gacha definition and let
the existing gacha scene consume it.

Only if a data-only prototype cannot produce the required permanent entry,
150/1500 Cat Food transactions or all-compatible-unit result pool should Phase C
trace the result/provider decision.

BCU remains useful for unit/rarity/animation semantics, but not as a product
runtime because BCU has its own Activities and screens.

## Save — sidecar first

BCC reconstructs `request_save_data` as a call to a host `request_save`
boundary and shows it participating in result/fade/battle flows.

Exact JP proves multiple save literals and local file I/O, but we do not yet
have one exact serializer hook with sufficient confidence.

So the approved order is:

1. original Battle Cats serializer remains authoritative;
2. Kneekura-only state uses an app-private versioned atomic sidecar;
3. hook/augment original save only if a later feature genuinely requires it.

This is safer and preserves the two isolated Android package sandboxes.

## Event/stage availability — MEDIUM/HIGH candidate

Exact JP contains `/event.json`, `eventDisplayData.json`,
`Map_option.csv` and `Stage_option.csv` anchors.

The working hypothesis is to answer the original event-availability request
through the common HTTP/provider seam with a local snapshot, leaving the stage
selection scene untouched.

Historical stage definitions still follow the existing provenance rule:
exact local > exact historical/server > labeled reconstruction.

## Patch transport — CONFIRMED

TBCML's public implementation supports native-library injection and version
scoped binary patches; its native injection pattern is consistent with the
Phase-A LIEF `DT_NEEDED` approach already tested in this repo.

Temporary Frida instrumentation remains acceptable for Phase-C discovery, but a
shipping build must use static version-pinned hooks and must not require Frida.

## What BCU contributes

Battle Cats Ultimate remains a strong semantic oracle for:

- unit/enemy/stage structures;
- animation behavior;
- custom content compatibility concepts.

It does **not** provide the desired host boundary: BCU Android exposes its own
`MainActivity`, `BattlePrepare`, `AnimationViewer`, etc. Using those
screens would turn Kneekura back into a clone, which the approved philosophy
forbids.

## Promotion rule

A candidate can move to product code only when all are true:

1. exact JP 15.7.1 call path observed;
2. input/output contract recorded;
3. original behavior with extension OFF verified;
4. failure path returns to original behavior;
5. one narrowly scoped regression test exists;
6. patch ledger records the exact mutation.

Until then it remains research evidence, not a hook.