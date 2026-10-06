# Research-only Frida traces

These scripts are **not product runtime dependencies**.

They exist only to promote an exact JP 15.7.1 candidate boundary from static
evidence to observed call-contract evidence before a static Kneekura hook is
written.

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
