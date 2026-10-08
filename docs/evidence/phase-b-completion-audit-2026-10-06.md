# Phase B Completion Audit — 2026-10-06

Status: **complete; no speculative product hook enabled**.

## Final preservation state

The original JP 15.7.1 Battle Cats runtime remains the product host.

Shipping-default `libkneekura.so` still has:

- feature mask = 0;
- no `JNI_OnLoad`;
- no socket/connect/getaddrinfo/send/recv imports;
- no SSL/cURL/Cronet dependency;
- no `dlopen` / `dlsym` hook loader;
- no automatic sidecar I/O from bootstrap;
- no original Battle Cats save mutation;
- no custom scene/UI code.

The standalone Java Android app remains a verification harness only.

## Phase-B service foundation

Implemented but disconnected behind feature gates:

- Personal MAX / Practice Clean sidecar profile modes;
- local-day clock policy;
- atomic/versioned/CRC-checked sidecar;
- local event visibility provider;
- Super Kneekura Gacha cost provider:
  - 1 draw = 150 Cat Food
  - 11 draws = 1500 Cat Food
- login provider:
  - exact local comeback template id 949
  - exact cycle length 7
- first-clear stage Cat Food provider:
  - 1–3 -> 1
  - 4–6 -> 2
  - 7–8 -> 3
  - 9–10 -> 5
  - 11 -> 8
  - 12+ -> 10

Feature OFF always returns original/pass-through behavior.

## Exact original runtime seams now proven statically

### HTTP transport

`MyActivity.newHttpRequest(...)` is now statically resolved through:

```text
MyActivity.newHttpRequest
 -> java.net.URL
 -> request object La32
 -> Thread / Lz22
 -> URL.openConnection
 -> HttpURLConnection
 -> original MyActivity.onResponse* native callbacks
```

Exact code hashes are recorded for:

- `MyActivity.isNetworkAvailable`
- `MyActivity.newHttpRequest`
- `La32.run`
- `Lz22.run`
- `Lz22.a`

Preferred Phase-C network seam:

> intercept only recognized local-service requests at
> `MyActivity.newHttpRequest`; unrecognized requests fall through to the exact
> original method.

Raw TLS/socket interception is not the primary design.

### Login

Exact original data/runtime anchors are pinned for:

- `DailyLoginEventData.csv`
- `DailyLoginEventGrade.json`
- `StampData.csv`
- `DailyLoginEventText_%03d_%@.tsv`
- `loginbg_%03d.png`
- `loginbg.imgcut`
- `comeback_push_01`
- `comeback_stamp_push%02d`

Exact local event 949 is a seven-day comeback template with totals:

- Cat Ticket ×21
- Rare Ticket ×3
- XP 2,000,000

Reward values remain in original Battle Cats data; the shim contains only the
template/cycle semantic choice.

### Gacha

Exact original loaders are pinned for:

- `GatyaDataSetR1.csv`
- `GatyaDataSetR2.csv`
- `GatyaDataSetR3.csv`
- `GatyaData_Option_SetR.tsv`
- `EventGatya_Setting.csv`

The exact local R1 union contains 495 unique Rare-through-Legend ids already
accepted by original JP 15.7.1 R-set data.

A tiny append-only structural prototype for set 1089 has been proven without
overwriting original rows.

The project deliberately does **not** claim the exact live Rare Capsule rarity
probability vector yet. That remains a Phase-C runtime/event evidence gate.

## Data-first patch foundation

New patch primitives allow the project to extend original Battle Cats data
without rebuilding the UI:

- deterministic pack writer;
- unchanged encrypted chunks copied byte-for-byte;
- only explicit DataLocal entries re-encrypted;
- post-rebuild decrypted-payload hash verification;
- DataLocal-only InstallPack patch stage;
- append-only Super Kneekura prototype generator.

This is the preferred path whenever the original data format can express the
feature.

## Research-only runtime observation path

The isolated package:

`jp.kn.trace.battlecats`

exists only for Phase-C observation.

The repository includes:

- observation-only Frida service-bridge trace;
- sanitized `KNEEKURA_TRACE` log output;
- trace lifecycle summarizer;
- owner-local research split builder;
- static research parity verifier.

Frida/Gadget is never a Personal MAX or Practice Clean dependency.

## CI evidence

Native provider/default-inert validation:

- Build Kneekura native shim run `37455471904`: success.
- Earlier provider-selector-native run `37454256355`: success.

Current branch tooling validation:

- Test tooling push run `37456481053`: success.
- Test tooling PR run `37456483355`: success.
- Head: `2a5f328551329e400f537d0b37b458e802465040`.

Patch-kit validation after the Phase-C research tooling landed:

- Build base-preserving patch kit run `37456324529`: success.

No real-device runtime observation is claimed by these CI runs.

## Phase-C first gate

The first product-changing hook is not yet authorized by evidence.

Phase C must capture one real original request lifecycle in the unchanged
Battle Cats scene:

1. `newHttpRequest` call;
2. returned request handle;
3. response callback sequence;
4. same action in airplane mode;
5. extension OFF == original behavior.

Only then may a selective local provider wrapper be promoted.

Fallback if the Java bridge proves unsuitable:

1. inspect exact native `MyActivity_request` dispatcher;
2. keep the original response callback path;
3. do **not** jump directly to global socket/TLS interception.

## Phase-B exit decision

**GO to Phase C observation.**

Reason:

- local provider semantics are implemented and tested;
- exact original service/data boundaries are substantially mapped;
- patch/data tooling is fail-closed and auditable;
- shipping-default shim remains inert;
- the remaining uncertainty is runtime request/scene behavior, which static
  analysis should no longer guess.
