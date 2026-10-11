# JP15.7.1 energy, calendar, gacha and game-stop evidence — 2026-10-09

Status: **direct original-package data inspection completed; original native callsite and device network trace remain unconfirmed.** Source SHA256 `38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56`, owner's previously uploaded `nyanko_battlecats_2026-10-06.zip`. No modified original SAVE_DATA needed for this audit.

## Owner observed behavior

- Natural cat-energy (統率力) refresh appeared to fail under poor/no server communication.
- Event calendar and gacha information remained visible.
- The game later showed the Japanese invalid-save restriction dialog.

These observations do not establish that all network connectivity was blocked, that calendar data was freshly downloaded, or whether the restriction was decided locally versus by a remote service.

## PONOS primary evidence

PONOS official JP FAQ (`https://ponosgames.com/information/appli/battlecats/faq/qa.html`) states that energy recharge, login bonus and event-time-based features can be influenced by both device clock and server connectivity. Its 2017 server incident notice (`https://ponos.s3.dualstack.ap-northeast-1.amazonaws.com/information/appli/battlecats/news/en/release/20170822.html`) reports energy, events, gacha and time-dependent features failing during service trouble.

**Therefore energy failing is expected for some types of time-sync/network failure, but cannot prove a complete firewall or identify a save restriction's origin.**

## Direct owner-original pack findings

Inspect original `split_InstallPack.apk`, decrypt local manifest/packs read-only:

- `DataLocal.list` contains **8,955** assets. `eventDisplayData.json` (47,336 bytes) has `MapSet` with **152** defined entries. This describes event display presentations, not necessarily live event dates.
- `GatyaData_Option_SetR.tsv` has **1,089 configuration rows**, in addition to other local gacha tables. Showing a gacha screen can thus succeed with already installed definitions.
- `Map_option.csv`, `Stage_option.csv`, `DailyLoginEventData.csv` and `DailyLoginEventGrade.json` are present.
- A live `event.json` or `gatya.tsv` is **not in bundled DataLocal** (other server-side or cached downloaded files might exist on the device; no conclusion about those caches is justified).
- The original `DownloadLocal` in the supplied InstallPack has only six generic download art entries; it is not the complete downloaded event schedule.
- `resLocal/localizable.tsv` includes separate UI keys:
  - `gamestop`, line 565: invalid save data warning matching the supplied screenshot.
  - `gamestop_device`, line 566: save in use on another device.
  - `gamestop_base`, line 567: account use suspension.
  - `calendar_error`, line 852: server disconnected or device clock out of alignment.
  - `receive_energy`, line 43 and `receive_energy_full`, line 47: energy replenishment notifications.
- The original `libnative-lib.so` includes all three `gamestop` string identifiers. This shows original native UI/service code can reference the local translations, not how it chooses the error case. **Do not call the screenshot proof of permanent account-ban or proof of local/remote enforcement.**

The `gamestop` warning is a *different localizable UI category* from an explicit account suspended (`gamestop_base`) warning. Client checks, a previously persisted restriction flag, or an incoming response remain competing hypotheses.

## Investigations ranked by diagnostic value

| Evidence | What it could prove | What it would NOT prove |
| --- | --- | --- |
| Actual network trace on disposable test package with OS egress blocked | Which app UID attempted to reach which host and whether any request was permitted | Which callsite caused a particular SAVE_DATA warning without a correlated trace |
| Compare calendar/gacha screen on clean offline first launch vs after online-derived cache | Whether previously downloaded calendar/schedules are necessary for visibility | That everything visible is itself locally scheduled |
| Read-only native references for localizable `gamestop`, `calendar_error` and local TIME branch | Candidate native UI message selector and time-service dependencies | Whether remote vs local decision was authoritative unless runtime arguments/flow verified |
| Inspect exact owned Server asset/calendar/cache bundle and local stage-option metadata | What can be imported into a stand-alone `LocalEventCatalog` | That current PONOS live event slots are in the base archive |
| Build own isolated `KNEEKURA_SAVE_V1` with local energy and calendars (no official account/save) | Save/date logic can work deterministically without network and without blocking by original integrity | That original game UI/native code already uses the new local module |

**Privacy-safe rule:** Never re-submit or reconnect the flagged original SAVE_DATA to the original account service as a diagnostic. Do not upload inquiry/account IDs, server cookies, original proprietary pack bodies or private user logs to public GitHub.

## Architecture decisions (proposed)

- `LOCAL_CLOCK` uses Android monotonic elapsed time within a boot, plus explicitly bounded/specified wall-clock fallback after reboot. A backward device clock should not punish a local-only player or result in `gamestop`; a user's sandbox may choose timed or unlimited energy.
- `LOCAL_EVENT_CALENDAR` merges fixed recurring stage definitions, locally imported event lists and user-created schedules. Calendar display data ≠ fresh service availability data, and network failure has no bearing on the local scheduler.
- `LOCAL_GACHA` consumes only the locally available set definitions and approved authored activation windows. It must not require official account receipts or external result seeds.
- `KNEEKURA_SAVE_V1` is an independent app-private schema. Own CRC/SHA, schema migrations and snapshots detect accidental corruption but **never enforce a ban**; unsupported/corrupted files recover from local backups or initialize a new local profile with user consent.
- `APP_NET` no android.permission.INTERNET in final signed product, original HTTP fallthrough removed or original host replaced, no bundled SDK initializers capable of external telemetry; verify first install, cold boot, stage, gacha, calendar and persistence under deny-all egress.

This supersedes "hide the gamestop popup" as a solution: suppressing a message would not resolve invalid state, sync dependencies, or other original game checks. No original anti-cheat/integrity bypass is implemented here.

## Current status

**PROVED:** source local data/three distinct UI keys; official energy/time/network interdependence; partial HTTP bridge original fallthrough; static network permission/SDK surface from existing issue #5.

**NOT PROVED:** actual network packets in the affected session, server-side restriction, exact native call graph from `gamestop` to save validator, device cache content, original offline event schedule runnability, full Android self-contained independent runtime.

See P0 [issue #5](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/5), [offline audit](../architecture/2026-10-09-complete-local-offline-audit.md), and existing source-only [egress auditor](../../tools/base_mod/audit_offline_egress.py).
