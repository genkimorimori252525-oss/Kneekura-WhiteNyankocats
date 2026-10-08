# Base-Preserving Battle Cats Mod — Repository Survey (2026-10-06)

Status: design evidence for the Android product-direction pivot.

## Rule

The original JP 15.7.1 APK/export remains the runtime ANCHOR. Public repositories are used to locate formats, functions and modification seams; they do not override observed behavior in the exact target build.

The product goal is not to recreate Battle Cats screens. It is to keep the original app/scene/UI/battle runtime wherever practical and replace only the minimum data/service/behavior seams needed for an offline personal mod.

## TBCML — primary APK/data patch pipeline

Repository: `fieryhenry/tbcml`.

Its published functionality explicitly includes:

- downloading/extracting APKs and server/event files;
- decrypting/encrypting Battle Cats pack files;
- parsing and modifying game data;
- modifying APK assets;
- Frida gadget hooking;
- smali injection and Java-to-smali conversion;
- patching `libnative-lib.so`;
- repacking and signing modified APKs;
- changing app/package name;
- custom encryption key/IV support;
- importing BCU packs.

This makes TBCML the best existing **packaging and patch-transport reference** for the base-preserving Android path.

Important constraint: its own documentation warns that script/native modification becomes harder in later versions because symbols/class names have been stripped. For JP 15.7.1, static bytecode/native addresses must therefore be anchored to the exact binary, not copied from older versions.

Recommended use:
1. TBCML pack/data parser and APK repack/sign concepts.
2. Frida only during research to discover stable call sites/state transitions.
3. Convert proven hooks to a version-pinned static native/smali shim for the final offline APK.
4. Never depend on Frida being installed on the player's phone.

## BCData — historical/server evidence

Repository: `fieryhenry/BCData` (GitHub is now historical; project notes point to a newer self-hosted repository).

Useful for:
- old server pack history;
- content/version comparisons;
- legacy collaboration evidence;
- filename/provenance cross-checks.

It is not a runtime architecture. Exact target-version files and the verified JP export take precedence.

## Battle Cats Ultimate (BCU)

Repositories:
- `battlecatsultimate/BCU_Android`
- `battlecatsultimate/BCU-java-PC`

TBCML itself credits BCU for CSV field meanings and animation rendering knowledge. BCU exposes mature concepts for:
- unit/enemy/stage data models;
- battle-rule interpretation;
- animation playback;
- custom packs and custom entities.

Recommended use: **behavioral oracle and schema reference**, especially when an original field is unclear.

Not recommended as the product host: BCU has its own UI/application runtime, while the product requirement is the original Battle Cats UI/scene flow.

## Battle Cats Complete (BCC)

Repository: `omochikaeri15/battle-cats-complete`.

This is currently the most useful public **native-engine behavior map** found for the new direction. Its emulator source contains named engine-level functions and state for areas directly relevant to the planned mod, including:

- `load_gacha_setting_csv` / `EventGatya_Setting.csv`;
- `load_daily_login_grade_json` / `DailyLoginEventGrade.json`;
- `battle_check_login_bonus`;
- `now_seconds` and a system-clock wrapper;
- `request_save_data`;
- game win/lose scene paths;
- map/stage loaders and stage result state;
- gacha/item/lineup data loaders.

Recommended use:
- symbol/behavior hypothesis source for the stripped JP 15.7.1 native binary;
- identify the smallest original function boundaries to intercept;
- understand which features already have original UI scenes and only need local backing data/state.

BCC must not be assumed byte-identical to JP 15.7.1. Every function mapping still requires exact-binary confirmation.

## Architecture options

### A. Data-only modified packs

Modify original pack/list/CSV/JSON entries and let the original app consume them.

Pros:
- highest UI/runtime fidelity;
- smallest behavior change;
- easiest to compare against original.

Cons:
- cannot by itself replace all online/time/save dependencies;
- cannot add every novel rule if no original data field exists.

Use for:
- permanent stage visibility where data-driven;
- gacha pool/banner/item definitions where original tables support them;
- names/text/images;
- custom units/stages when the original registry format can accept them.

### B. Java/smali-only patch

Patch Android-side Java/smali calls.

Pros:
- easier than native code when a target lives above JNI;
- good for package/bootstrap/storage glue.

Cons:
- much of Battle Cats gameplay/state logic is native;
- insufficient as the only modification layer.

Use for:
- loading the Kneekura native shim;
- private file/profile selection;
- Android-local storage/clock bridge;
- optional package/bootstrap changes.

### C. Minimal native hook/shim inside the original APK — recommended

Inject a small version-pinned native shim and hook only confirmed functions in `libnative-lib.so`.

Pros:
- original scenes/UI/rendering/battle loop remain the host;
- can redirect time/save/gacha/event/network decisions without recreating screens;
- hook count can be audited and kept small.

Cons:
- exact-version fragile;
- stripped symbols require careful binary anchoring;
- every upgrade needs a compatibility audit.

Use for:
- local offline service decisions;
- gacha transaction/result source;
- login-bonus day/claim state;
- stage-clear custom Cat Food reward;
- network availability/server-result replacement only at narrow wrappers.

### D. Localhost HTTP server/domain redirect

Redirect original requests to a localhost server.

Pros:
- can mimic remote APIs while leaving callers untouched.

Cons:
- TLS/certificate pinning/domain assumptions;
- keeps network permission and a network-shaped failure mode;
- harder to guarantee truly self-contained behavior.

Verdict: useful as a research prototype only, not the preferred final Android design.

### E. Standalone reimplementation

Current Java Android screen/battle harness belongs here.

Verdict: **not a product path**. Keep only for parser/rule regression tests.

## Recommended final stack

```text
Original JP 15.7.1 APK
  |
  +-- original resources / scenes / UI / native battle engine
  |
  +-- patched original pack data
  |      +-- local persistent stage availability
  |      +-- Super Kneekura Gacha definitions/assets
  |      +-- custom content registry entries
  |
  +-- tiny Android bootstrap patch
  |      +-- load Kneekura native shim
  |      +-- expose app-private local profile files
  |
  +-- version-pinned Kneekura native shim
         +-- OfflineClock
         +-- LocalSave/Profile overlay
         +-- LocalEvent/Gacha provider
         +-- LoginBonus cycle state
         +-- StageReward extension
         +-- network/service wrapper stubs
```

The key design metric is **original code left untouched**. A feature is preferred when it can be expressed by data; second choice is one narrow original function hook; rebuilding a scene is the last resort.

## Research sequence for each hook

1. Identify the user-visible original scene/function in BCC/TBCML/BCU.
2. Observe the exact JP 15.7.1 binary and call path.
3. Prove inputs/outputs with a temporary Frida research hook.
4. Record exact binary fingerprint and signature.
5. Replace the temporary hook with a static version-pinned shim/patch.
6. Regression-test original behavior with the extension disabled.
7. Verify no live PONOS endpoint is required in offline mode.

This sequence is the basis for keeping the original game intact instead of gradually turning the mod into a separate clone.