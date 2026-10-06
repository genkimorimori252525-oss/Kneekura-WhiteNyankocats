# Phase C device lifecycle observation — 2026-10-07

Status: **device trace succeeded; first local-response candidate selected, online payload still intentionally uncaptured**

Target:
- JP 15.7.1
- research package: `jp.kn.trace.battlecats`
- original launcher: `jp.co.ponos.battlecats.MyActivity`
- observation-only Frida Gadget path
- no HTTP body capture
- response header values redacted

## Normal-connectivity capture

30-second startup capture:
- trace ready: true
- event count: 20
- request returns: 2
- response lifecycles: 2

### Request 1 — backup service root

Observed request:
- method: `GET`
- URL family: `https://nyanko-backups.ponosgames.com/`
- query: redacted
- timeout: `10.0`
- request header-map size: `0`
- body: `null`
- string-array length: `0`
- boolean flags: `false, false`
- returned request id: `1`

Observed response ingress:
- `newResponse`
- request id: `1`
- status: `200`
- response URL family: backup service root
- response header block: redacted, length `427`
- ByteBuffer: remaining `0`, capacity `40`
- final boolean argument: `false`

No `onResponseCodeHeaders`, `onResponseData`, or `onResponseFinish`
was observed for this request in the capture window.

### Network gate

Immediately after request 1:
- `isNetworkAvailable() -> true`

### Request 2 — event sale data

Observed request:
- method: `GET`
- URL family/path:
  `https://nyanko-events.ponosgames.com/battlecats_production/sale.tsv`
- query: redacted
- timeout: `10.0`
- request header-map size: `0`
- body: `null`
- string-array length: `0`
- boolean flags: `true, false`
- returned request id: `2`

Observed response ingress:
- `onResponseCodeHeaders`
  - request id: `2`
  - status: `401`
  - response header block: redacted, length `503`
- `onResponseFinish`
  - request id: `2`
  - boolean argument: `false`

No `onResponseData` was observed for request 2.

## Airplane-mode capture

30-second startup capture:
- trace ready: true
- event count: 14
- request returns: 1
- response lifecycles: 1

### Request 1 — same backup service request family

The request signature matches normal-connectivity request 1:
- method: `GET`
- URL family: `https://nyanko-backups.ponosgames.com/`
- query: redacted
- timeout: `10.0`
- request header-map size: `0`
- body: `null`
- string-array length: `0`
- boolean flags: `false, false`
- returned request id: `1`

### Network gate

- `isNetworkAvailable() -> false`

The event-sale request was not issued after this false result.

### Offline response ingress

Request 1 completed through `newResponse`:
- request id: `1`
- status: `0`
- response URL family: backup service root
- response header block: redacted, length `2`
- body buffer: `null`
- final boolean argument: `true`

## Confirmed runtime contract

1. `MyActivity.newHttpRequest` is a live request boundary on the owner device.
2. Its returned `int` is the response correlation id.
3. The exact backup-service request family is present in both normal and
   airplane captures with the same non-sensitive request signature.
4. The backup request uses the one-shot `newResponse` ingress in both
   success and offline failure cases.
5. Network state is checked after the backup request.
6. The event-sale request is gated by network availability in this startup path.
7. The event-sale request uses the streamed callback family
   `onResponseCodeHeaders -> onResponseFinish` for the observed 401 path.
8. No `onResponseData` was observed in either capture.
9. The observed callback order is the contract; guessed callback order must not
   replace device evidence.

## First local-response candidate

The backup-service root request is the preferred first experimental target.

Why:
- it is observed in both normal and offline conditions;
- its request signature is stable across both captures;
- it uses a single `newResponse` ingress instead of the streamed callback path;
- its offline fallback has no response body;
- the event-sale request is currently unsuitable because only a 401 streamed
  path has been observed in the isolated research package.

The online backup response body remains intentionally uncaptured. Therefore the
first local-response experiment must **not invent a 200 payload**.

## Next gate before behavioral promotion

A research-only local provider may first replay only the *observed offline
failure semantics* for the exact backup-service request family, behind a feature
flag and only after the following are proven:

- exact request-id allocation behavior around `mNextRequestHandle`;
- whether a local-complete request must participate in `mRequestHandles`;
- the exact meaning/classification of the redacted two-character offline header
  block without recording header values;
- callback scheduling context matching the original GL-thread/error path.

Static evidence already shows:
- `mNextRequestHandle` is an instance integer field;
- `mRequestHandles` is an instance `java.util.Map`;
- original `newHttpRequest` increments the next handle, stores the request,
  starts the request thread, and returns the handle.

Do not promote a product hook until the research replay preserves those
lifecycle semantics.

## Promotion rule

The first experiment remains selective:
- exact recognized backup request -> research-local replay only
- unknown request -> exact original `newHttpRequest`
- feature OFF -> exact original path
- original native response methods remain response ingress
- Personal MAX and Practice Clean remain free of Frida instrumentation


## Instrumentation stability note

A follow-up trace that added reflective reads of `mNextRequestHandle` and
`mRequestHandles` around every observed method caused the research build to
become unstable on-device.

Symptoms:
- normal capture showed two `script_loaded` / `trace_ready` sequences;
- no response callbacks were captured in that unstable run;
- the game process was observed to terminate/restart during the verification.

Policy:
- that run is **not** accepted as behavior-preservation evidence;
- the request-side state snapshots are useful only as corroboration of the
  already-proven static handle-allocation flow;
- reflective request-state reads are now restricted to
  `newHttpRequest` / `isNetworkAvailable`;
- static native response callbacks record thread metadata only.

The stable fixed6 normal/airplane lifecycle capture remains the authoritative
runtime callback evidence until a new behavior-preserving trace supersedes it.


## Static resolution of the redacted offline header block

The airplane trace intentionally recorded only that the response-header string
had length 2. Exact `classes4.dex` analysis resolves it without exposing a
captured header value:

- `Lz22.a()` constructs `org.json.JSONObject`;
- immediately calls `JSONObject.toString()`;
- passes that result to `MyActivity.newResponse`;
- passes status `0`, body `null`, final boolean `true`.

The resulting header string is therefore exactly `"{}"`.

The same exact DEX also confirms:
- `a32.<init>(int,String,URL,float,HashMap,ByteBuffer,String[])`;
- `mNextRequestHandle: int`;
- `mRequestHandles: java.util.Map`;
- `mGLView: android.opengl.GLSurfaceView`.

This closes the remaining local-replay contract using static exact-version
evidence rather than another device observation.
