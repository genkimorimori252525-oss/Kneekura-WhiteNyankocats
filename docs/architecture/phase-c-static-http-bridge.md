# Phase C Static HTTP Bridge — JP 15.7.1

Status: **Frida-free bridge implementation present; repository CI green; final owner-device smoke remains before step-003 promotion.**

## Why this exists

Phase C device tracing proved that the exact JP 15.7.1 Java method

`jp.co.ponos.battlecats.MyActivity.newHttpRequest(...): int`

is the narrow service boundary we wanted. The original UI and native callers can
remain unchanged while one recognized request family is satisfied locally.

Temporary Frida instrumentation established the runtime contract. It is not a
shipping dependency.

## First promoted request family

Only the exact observed backup request shape is eligible:

- HTTP method: `GET`
- scheme: `https`
- host: `nyanko-backups.ponosgames.com`
- path: `/`
- default HTTPS port only
- no userinfo / fragment
- timeout: `10.0f`
- request header map: empty
- request body: null
- String[]: empty
- flags: `false, false`

The query is deliberately not interpreted. The classifier is narrow on the
non-sensitive request contract that was stable in both normal and airplane
captures.

Anything outside that exact shape falls through to the original
`super.newHttpRequest(...)`.

## Observed offline replay

The first local proof replays only behavior already observed on-device in
airplane mode. It does **not** invent a successful server payload.

For the exact backup request:

1. read current `mNextRequestHandle`;
2. increment it exactly once;
3. construct the original request class `a32`;
4. add it to original `mRequestHandles`;
5. queue the callback on original `mGLView`;
6. call original native ingress:

```text
MyActivity.newResponse(
    requestId,
    0,
    requestUrl,
    "{}",
    null,
    true
)
```

The stable device trace showed the same request-side state transition:

```text
mNextRequestHandle  1 -> 2
mRequestHandles     0 -> 1
thread              GLThread
```

The event-sale request remains untouched.

## Static implementation

Shipping-oriented proof files:

- `bridge/java/MyActivity.java.in`
- `bridge/java/stub/jp/co/ponos/battlecats/MyActivity.java`
- `tools/base_mod/inject_java_http_bridge.py`
- `tools/base_mod/build_owned_static_http_bridge.py`
- `tools/base_mod/verify_static_http_bridge.py`

The implementation compiles a flavor-specific subclass such as:

`jp.kn.trace.battlecats.MyActivity`

which extends the original:

`jp.co.ponos.battlecats.MyActivity`

The subclass is injected as **`classes5.dex`**. The original
`classes4.dex` `newHttpRequest` body is not rewritten.

The manifest launcher string is replaced with the equal-length flavor subclass
name. Existing original lifecycle/UI behavior is inherited from the original
activity.

## Feature OFF and unknown-request behavior

Feature OFF:

```text
flavor MyActivity.newHttpRequest
    -> super.newHttpRequest
    -> exact original JP 15.7.1 transport
```

Unknown request while feature ON:

```text
classifier miss
    -> super.newHttpRequest
    -> exact original JP 15.7.1 transport
```

If reflection or replay setup drifts at runtime, the implementation fails
closed and calls `super.newHttpRequest`.

## Version pins and parity

The verifier pins the original method instruction SHA-256:

`14f896e5b42b8e5b8ab50f756bdc79ad44614325eb153ab99ffcdafb98c70a80`

Static audit requires:

- original `newHttpRequest` code unchanged;
- only expected package/launcher/base-DEX surfaces changed;
- bridge added only as `classes5.dex`;
- original native exported-function surface preserved;
- Kneekura shim dependency present;
- no Frida Gadget/config/script present.

CI additionally compiles both feature-OFF and feature-ON bridge DEX variants
with Java 17 + Android d8.

## Current verification status

Repository CI:
- Python contract/regression tests: PASS
- Java bridge javac compile: PASS
- d8 generation for OFF variant: PASS
- d8 generation for ON variant: PASS
- patch-kit generation: PASS

Remaining step-003 gate:
- one owner-device smoke of the Frida-free static bridge;
- verify original screen still boots;
- verify process remains alive;
- verify unknown/event request behavior remains original;
- verify exact backup request can take the local replay path;
- then record the final patch ledger evidence.

No more routine normal/airplane tracing is planned.


## Exact DEX corroboration for the replay internals

The owned exact JP 15.7.1 `classes4.dex` was re-read after the device trace.

Original request object `La32;` / runtime class `a32`:

```text
<init>(
    int,
    String,
    java.net.URL,
    float,
    java.util.HashMap,
    java.nio.ByteBuffer,
    String[]
) -> void
code_off = 0x1f18e4
```

Exact `MyActivity` instance fields used by original `newHttpRequest`:

```text
mGLView            android.opengl.GLSurfaceView
mNextRequestHandle int
mRequestHandles    java.util.Map
```

The only original Java method that accesses `mNextRequestHandle` and
`mRequestHandles` is `MyActivity.newHttpRequest`; no separate Java-side map
removal path was found. This supports reproducing the original allocation/store
steps before local completion.

The exact `Lz22.a()` fallback body at `code_off 0x1f1120` also resolves the
previously redacted two-character response-header block without capturing it
from the device:

```text
new org.json.JSONObject()
-> JSONObject.toString()     # "{}"
-> request URL.toString()
-> status = 0
-> body = null
-> final flag = true
-> MyActivity.newResponse(...)
```

For the observed false request flag, the fallback is queued through the
original `GLSurfaceView.queueEvent(...)` path. This matches the stable device
trace where the native response ingress was observed on the GLThread.

Therefore the first static replay's `"{}"`, null body, status 0 and true flag
are exact JP 15.7.1 fallback semantics, not invented payload values.
