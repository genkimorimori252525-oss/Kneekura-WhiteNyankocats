# JP 15.7.1 Native Service Boundary Map

Status: exact-binary Phase-B foundation.  
Anchor: `libnative-lib.so` SHA-256 `333d2974ab2ff881fd70087fd62dea7d12d82addbc55cab2f2a675ad67e3a7e2`, GNU build ID `8cb3815648eb9642da10bfb039d71bff7a3519bd`.

Machine-readable companion: `native-service-map-jp15.7.1.json`.

## Purpose

This map identifies the narrow service boundaries that can let Kneekura remain
inside the original Battle Cats scenes instead of recreating UI.

Addresses below belong **only** to the exact JP 15.7.1 ARM64 binary. They are
not portable offsets.

## 1. Original Java/native request bridge

The exact native library exports these JNI boundaries:

| JNI boundary | VA | Observed role |
| --- | ---: | --- |
| `MyActivity_appInit` | `0x31748c` | native application init |
| `MyActivity_appUpdateDraw` | `0x31755c` | update/render bridge |
| `MyActivity_request` | `0x317b1c` | native → Java/service request bridge |
| `MyActivity_kill` | `0x317bb8` | shutdown |
| `MyActivity_newResponse` | `0x46158c` | response ingress |
| `MyActivity_onResponseCodeHeaders` | `0x461e30` | HTTP code/header ingress |
| `MyActivity_onResponseData` | `0x462204` | response body ingress |
| `MyActivity_onResponseFinish` | `0x4624ec` | request completion |

`MyActivity_request` converts the Java string and then calls an internal
dispatch candidate near `0x9c8c1c`. The internal function is stripped, so it
is a research lead, not a named contract yet.

The exact `classes4.dex` MyActivity also contains ordinary Java methods:

- `newHttpRequest(String,String,float,HashMap,ByteBuffer,String[],boolean,boolean): int`
- `isNetworkAvailable(): boolean`
- `createDefaults(): String`

Native string references for those method names exist at `0x19cf89`,
`0x19ac42`, and `0x19f925`, with native call/reference sites captured in
the JSON map.

### Recommendation

**The Java HTTP bridge is the leading offline-service seam.**

That is preferable to:

- intercepting raw sockets/TLS;
- rewriting every PONOS endpoint caller;
- keeping a localhost HTTP server as a product dependency.

If exact call-flow observation confirms it, Kneekura can leave the original
callers/scenes intact and satisfy selected requests locally at one narrow
boundary.

## 2. Exact service endpoint evidence

The binary contains direct endpoint strings for purchase, backup, ranking,
authentication, club, announcement, events, save, managed-item, items, assets
and receipts services.

The cluster of endpoint xrefs around `0x3279xx–0x327dxx` strongly suggests a
central endpoint/config initialization region. We do **not** name stripped
internal functions from that clustering alone.

The preservation rule is to hook a shared request/provider boundary, not to
patch these strings into fake domains.

## 3. Clock boundary

The exact binary imports:

- `steady_clock::now` at `0xad76f0`;
- `system_clock::now` at `0xad7db0`;
- `time` at `0xad7820`;
- `clock_gettime` at `0xad8f30`;
- `localtime_r` at `0xad9b50`;
- `mktime` at `0xad9b60`.

`appUpdateDraw` uses `steady_clock::now` for elapsed update/render timing.
That clock **must not** be repurposed for daily login logic.

A local date/time utility family around `0x4734xx–0x473cxx` calls
`time/localtime_r/mktime` and is the strongest current native candidate for
day-based behavior. It remains medium-confidence until runtime observation
ties it to login/event decisions.

### Recommendation

The Kneekura `OfflineClock` API may be implemented now, but it must remain
unhooked. Phase C should confirm the exact local-day call path before replacing
anything.

## 4. Save boundary

The binary imports ordinary file I/O and contains save-related literals such as
`SAVE_DATA`, `SAVE_DATA4`, `SAVE_DATA8`, `BACKUP_SAVE_DATA` and
`SaveDataTransfer`.

This proves local save plumbing exists but does not yet identify a single safe
serializer hook.

### Recommendation

Original Battle Cats save serialization stays authoritative. Kneekura-only
state uses a separate atomic sidecar file. We will not patch unknown save fields
simply because they are reachable.

## 5. Feature-data anchors

Exact data-loader strings exist for:

- `DailyLoginEventGrade.json` — login bonus data;
- `EventGatya_Setting.csv` — event/rare gacha setting;
- `Map_option.csv` and `Stage_option.csv` — map/stage policy;
- `/event.json` and `eventDisplayData.json` — event availability/display.

These are valuable because the original UI already knows how to present these
systems. Kneekura should feed those original systems compatible local state
instead of drawing replacements.

## 6. Confidence classes

- **high** — exact exported JNI method, exact Java method, literal/data anchor,
  or imported system function verified in JP 15.7.1.
- **medium** — exact call-site cluster whose semantic role is strongly suggested
  but not yet tied to a user-visible path by runtime observation.
- **low** — cross-version/public-source hypothesis only; not accepted as a
  product hook.

No medium/low candidate is activated merely because it resembles a function in
another repository.

## 7. Phase-B hook rule

At this checkpoint the correct implementation is intentionally asymmetric:

- build the local Clock/Sidecar/Profile/provider APIs now;
- keep feature mask zero by default;
- connect **zero** uncertain native hooks;
- use Phase C device tracing to promote one boundary at a time from candidate
  to exact contract.

That is how the project preserves the original game rather than letting reverse
engineering guesses become permanent runtime behavior.