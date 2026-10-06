# Offline Local Profile Bootstrap — Current Priority

Status: bootstrap runtime accepted; original-game rewrite mapped; install-r persistence proof pending as of 2026-10-07.

## Why this now comes before Rare Gacha runtime proof

The exact JP 15.7.1 research build reaches the original Battle Cats stage-select
scene, but the original progression flow still expects tutorial completion and
online-derived state before Rare Gacha becomes convenient to validate.

The project therefore postpones Rare Gacha visibility/schedule work and first
creates a durable offline test profile that can be reused for later original-UI
verification.

## Primary goal

Create one local research profile that:

- persists across process restarts;
- persists across same-signature `adb install -r` updates;
- does not require replaying the tutorial for every test;
- contains every locally supported unit as already owned/unlocked;
- starts each owned unit at first form unless exact save semantics require
  another neutral representation;
- sets XP, Cat Food and progression materials/currencies to their exact
  supported storage/display caps;
- includes evolution/talent-related materials needed for unrestricted local
  experimentation;
- remains usable without relying on live gacha acquisition.

Rare Gacha, schedule emulation and draw/result verification remain separate,
deferred work.

## Persistence rule

Do **not** continuously overwrite the live profile on every launch.

Preferred design:

1. create/identify the native save profile once;
2. apply the bootstrap only when a dedicated Kneekura sentinel/version is absent;
3. write and flush the normal local save through the closest recoverable native
   persistence path;
4. record a local bootstrap schema/version marker;
5. on later launches, preserve the player's modified state;
6. maintain an explicit reset/re-bootstrap path for test recovery.

This makes the profile a durable test save rather than a permanent runtime cheat
hook.

## Cap rule

Do not use `INT_MAX` blindly.

For every currency/material, derive the exact JP 15.7.1 storage and UI cap from
native code/data and use that value. This avoids signed overflow, display
corruption, accidental wraparound and save-validator failures.

Target categories include at minimum:

- XP;
- Cat Food / Nekokan;
- Rare Tickets;
- Platinum Tickets;
- Legend Tickets where represented;
- NP / talent exchange currency;
- Leadership;
- Catseyes;
- Matatabi seeds/fruits and related evolution materials;
- Behemoth-style evolution materials where present in JP 15.7.1;
- battle/support items;
- other persistent progression materials discovered in the exact save schema.

## Exact-binary anchors already confirmed

Static string reconnaissance in the owned JP 15.7.1 `libnative-lib.so` has
already confirmed relevant native anchors, including:

- `SAVE_DATA`
- `SAVE_DATA4`
- `SAVE_DATA8`
- `BACKUP_SAVE_DATA`
- `getSavedRegister`
- `getSavedFloatRegister`
- `catfoodAmount`
- `setNekokan(%d,%f)`
- `rareTicketAmount`
- `platinumTicketAmount`
- `setItem(%d, %d)`
- `setItem('%@',%d)`
- `setTreasure`
- `setUserRank(%d)`
- `potential_exchange_np`
- `potential_exchange_np_set`
- `Matatabi.tsv`
- `unitexp.csv`
- `BcResCatsEyeLevelUp`
- `BcResLeadership`

These are reconnaissance anchors only; field offsets and write semantics still
require exact-version static tracing before mutation.

## Unit ownership rule

“All units owned” must be derived from the exact local unit catalog / asset
inventory, not from guessed contiguous IDs.

The bootstrap should:

- enumerate supported unit IDs from the exact JP 15.7.1 data;
- exclude known placeholders/test-only rows when proved by source evidence;
- set ownership/unlock state through the actual save representation;
- avoid inventing evolution state;
- verify that the original Cat Guide / Upgrade UI can enumerate the resulting
  units without crashes.

## Safety / recovery contract

Before the first mutating device test, capture a recoverable baseline of every
research-package file that can be accessed through the promoted research
storage path.

Every bootstrap run must emit a machine-readable result containing:

- package/version;
- bootstrap schema version;
- save source/target path or native persistence seam;
- pre/post hashes where available;
- number of unit ownership records changed;
- every resource category changed and chosen cap;
- verification result after process restart;
- whether a rollback snapshot was produced.

## Runtime promotion gate

This phase is considered successful only when one device run proves:

1. bootstrap profile is created;
2. app restarts normally;
3. profile survives a second launch;
4. same-signature `adb install -r` does not erase it;
5. original UI shows unlocked units/resources coherently;
6. no H01/integrity failure is introduced;
7. user progress made after bootstrap is not reset on next launch.

After that, Rare Gacha work can resume from a stable, already-equipped local
profile.

## Runtime proof status — 2026-10-07

The first guarded device mutation established more than static parser safety:

- the exact 497,580-byte MAX candidate was accepted by the unchanged original
  JP 15.7.1 scene;
- the original UI opened normally;
- after a normal process restart, the original UI opened normally again and the
  user confirmed the MAX profile remained present;
- the original game normalized SAVE_DATA to 507,174 bytes;
- that normalized SAVE_DATA has a valid JP salted-MD5, losslessly round-trips
  through the pinned research parser, and passes the independent full-semantic
  Kneekura verifier;
- the 9,594-byte growth is completely accounted for by generated cat-new flags,
  mission tables, UI/event bookkeeping and a 16-byte forward-compatible tail
  extension.

The prior rollback at this point was a verifier false positive caused by an
obsolete exact-size assumption. It was not an H01/data-read failure.

The corrected bootstrap accepts the known 507,174-byte normalized profile,
records its layout/verification level in the result JSON, and retains automatic
rollback for actual integrity or semantic failures.

The next device gate is therefore the same-signature six-split
`install-multiple -r` persistence proof, not further SAVE_DATA reverse
engineering.
