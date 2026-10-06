# Kneekura Bootstrap / Native Shim Contract

Phase: base-preserving Android Phase A.

## Loading seam

TBCML's native injection path was inspected before choosing the bootstrap
mechanism.

Its `Lib.add_library()` delegates to LIEF's ELF
`Binary.add_library()`, and TBCML's package layer then places the new shared
library beside the original game library. In ELF terms this adds a `DT_NEEDED`
dependency to `libnative-lib.so`.

Kneekura follows the same **mechanism**, but not TBCML's Frida runtime.

Final Phase-A path:

```text
original MyActivity
  -> Android loads original libnative-lib.so
       -> DT_NEEDED libkneekura.so
            -> tiny ELF constructor
                 -> records bootstrap initialized
                 -> feature mask remains 0
                 -> installs no hooks
       -> original libnative-lib.so continues normally
```

This avoids a replacement Activity and avoids injecting a second Java UI path.

## Exact anchor gate

The injector refuses any native library except:

- SHA-256:
  `333d2974ab2ff881fd70087fd62dea7d12d82addbc55cab2f2a675ad67e3a7e2`
- GNU build ID:
  `8cb3815648eb9642da10bfb039d71bff7a3519bd`
- architecture: AArch64

These identify the recovered JP 15.7.1 `libnative-lib.so`.

Unknown builds fail closed.

## Shim Phase-A behavior

`libkneekura.so` currently:

- has a constructor solely to prove the bootstrap loaded;
- exports its ABI version and target anchor identity;
- exposes bootstrap-initialized state;
- exposes a feature mask;
- returns feature mask **0** at compile time;
- performs no function hook;
- performs no filesystem access;
- performs no socket/network access;
- calls no original Battle Cats symbol.

Therefore "extensions disabled" is not a simulated compatibility mode: there
are simply no behavior hooks installed yet.

## Injection mutation

Only the ARM64 native split is affected by bootstrap injection:

- `lib/arm64-v8a/libnative-lib.so`: adds `DT_NEEDED libkneekura.so`
- `lib/arm64-v8a/libkneekura.so`: new library

The injector verifies that LIEF preserves the original exported-function name
set while adding the dependency.

The APK is then zipaligned and signed by the separate baseline signing
pipeline. Native libraries are stored uncompressed before zipalign.

## Why not Frida in the final APK?

Frida remains valuable for temporary research because it makes call-site
discovery fast. It is not the product bootstrap because:

- it adds a large general-purpose runtime;
- its script engine is unnecessary once a hook is understood;
- it broadens the permanent patch surface;
- it makes "what did Kneekura change?" harder to audit.

Research sequence remains:

1. use Frida only to prove an exact JP 15.7.1 hook when necessary;
2. record the exact function/signature/state behavior;
3. implement the smallest equivalent static shim hook;
4. remove the research hook from the product build.

## Next feature rule

Every future feature must allocate a feature bit and default OFF until the
feature's exact original boundary and regression tests exist.

The first planned real features are local clock/save/event/gacha service
boundaries. None are activated by this bootstrap milestone.