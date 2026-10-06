# Phase-B Native Shim Audit — 2026-10-06

Audited workflow run: `37443539383`  
Functional head: `3b634d75c7bdafe781f4b710aaf51739cf567f1d`

## Result

The ARM64 `libkneekura.so` build passed:

- exact target/version ABI exports;
- Clock/Sidecar/Profile native tests;
- provider ABI with feature mask OFF;
- provider ABI with a test-only enabled feature mask;
- native dependency-injection tests;
- static no-network/no-dynamic-hook import audit.

Artifact: `11401977577`.

Artifact digest:

`sha256:dac001a971e4b1d6c95b6500bc71b44927a65776f11af891aed197a90f220338`

## Import audit

The generated `shim-import-audit.json` reports:

- exported functions: **22**
- imported functions: **19**
- DT_NEEDED:
  - `libc.so`
  - `libdl.so`
  - `libm.so`
- forbidden network/dynamic-hook imports: **absent**
- `JNI_OnLoad`: **absent**
- forbidden SSL/cURL/Cronet libraries: **absent**

The audit checks imported symbols, not merely source text. In particular the
built library has no imported `socket`, `connect`, `getaddrinfo`,
`send/recv`, `SSL_*`, `curl_*`, `dlopen` or `dlsym`.

`libdl.so` being listed as an Android toolchain dependency is not treated as a
hook by itself; the symbol-level audit confirms no `dlopen/dlsym` import.

## Provider semantics currently compiled but disconnected

Feature mask defaults to zero.

The library contains tested semantics for:

- local event visibility union;
- Super Kneekura Gacha cost:
  - 1 draw = 150 Cat Food
  - 11 draws = 1500 Cat Food
- cyclic one-per-observed-day login claim;
- stage first-clear Cat Food table;
- versioned/CRC checked/atomic sidecar;
- Personal MAX and Practice Clean sidecar profile modes.

None of those providers is currently connected to original Battle Cats runtime
decision points.

## Why this is a pass

Phase B is allowed to define local service semantics, but it is not allowed to
guess a hook.

The binary audit confirms the shipping-default shim remains inert:

- no network client;
- no dynamic hook loader;
- no JNI registration;
- no scene/UI code;
- no automatic sidecar I/O;
- no original save write.

The next phase is therefore runtime **observation**, not more speculative
patching.
