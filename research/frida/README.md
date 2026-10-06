# Research-only Frida traces

These scripts are **not product runtime dependencies**.

They exist only to promote an exact JP 15.7.1 candidate boundary from static
evidence to observed call-contract evidence before a static Kneekura hook is
written.

## Frida Gadget compatibility

`trace_service_bridge.js` is the readable source and uses the pre-Frida-17 global `Java` bridge model.

The patch-kit CI also produces `trace_service_bridge.bundle.js`, which prepends an explicit `frida-java-bridge` import and compiles it with `frida-compile`. Use that bundled agent with current Frida 17.x Gadget.

Compatibility:

- Frida 17.x: use `trace_service_bridge.bundle.js`.
- Frida 16.7.19: the raw `trace_service_bridge.js` is also valid because the Java bridge is built into the runtime.

The bridge bundle is research-only and must never ship in Personal MAX or Practice Clean.

## trace_service_bridge.js

Targets the original class:

`jp.co.ponos.battlecats.MyActivity`

It catalogs and observes:

- `newHttpRequest`
- `isNetworkAvailable`
- `newResponse`
- `onResponseCodeHeaders`
- `onResponseData`
- `onResponseFinish`

Every hooked overload calls its original implementation unchanged.

Privacy/safety choices:

- URL query values are redacted;
- ByteBuffer contents are never copied/logged;
- HashMap values are never logged, only up to 32 key names;
- String-array contents are not logged;
- no return value is replaced;
- no network availability result is spoofed.

The output is intended to establish request id/callback order, overload
signatures and the minimal original lifecycle needed by a later local provider.

## Required evidence

A Phase-C network seam is not confirmed merely because the script loads.

Capture at least:

1. the emitted method catalog;
2. one original request enter/return pair;
3. corresponding response callback sequence;
4. the same action in airplane mode;
5. device/build/package/flavor and exact patch-ledger identity.

If original behavior changes while tracing, discard the run.

## Shipping rule

A successful trace is converted into a narrow static version-pinned patch.
Frida/Gadget must not remain in the final APK.


## Exact JP 15.7.1 method definitions

A dependency-free DEX definition pass over the exact base APK fixes these
`MyActivity` methods in `classes4.dex`:

- `newHttpRequest(String,String,float,HashMap,ByteBuffer,String[],boolean,boolean): int` — public Java instance method.
- `isNetworkAvailable(): boolean` — public Java instance method.
- `newResponse(int,int,String,String,ByteBuffer,boolean): void` — public static native.
- `onResponseCodeHeaders(int,int,String,String): void` — public static native.
- `onResponseData(int,ByteBuffer): void` — public static native.
- `onResponseFinish(int,boolean): void` — public static native.

The trace script treats the response methods as static and calls the original
native implementation through the class wrapper. The exact evidence is stored
in `docs/evidence/myactivity-service-methods-jp15.7.1.json`.

## Summarize a captured log

The trace emits one machine-readable line for every sanitized event:

`KNEEKURA_TRACE {json}`

After capturing Frida output:

```bash
python -m tools.base_mod.summarize_service_trace trace.log \
  --output service-trace-summary.json
```

The summarizer correlates `newHttpRequest` return ids with response callback
sequences without needing raw response bodies or header values.
