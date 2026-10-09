# にーくら大戦争 — Post-EoC / Offline-First LiveOps Design

> **2026-10-09 OFFLINE OPERATIONS SUPERSESSION:** The content/progression policy below remains useful (Post-EoC play, stage-reward truth, login five-slot rotation, unlock-only event stages), but any proposal to automatically download a signed content channel at runtime is **deprecated**. The [new operator charter](kneekura-offline-operations-charter.md) and [zero-egress/local-save P0 policy](2026-10-09-complete-local-offline-audit.md) take precedence. GitHub is Jolly's authoring/approval/history service on the PC, **never an endpoint queried by the final offline Android game**. `KNEEKURA_SAVE_V1` replaces original JP SAVE_DATA for independent gameplay; only manual content import is allowed.


Status: current mainline product direction as of 2026-10-07.

## Product identity

The project is no longer defined as an "all cats / all resources MAX save".
That profile remains only as recovery/research evidence.

The main playable product is **にーくら大戦争**:

- the player starts immediately after completing Empire of Cats (日本編) 1–3;
- all valid Empire of Cats treasures are Superior;
- Stories of Legend and later story progression remain genuinely uncompleted;
- existing JP 15.7.1 non-stage-reward units (including gacha/collab/Legend Rare)
  are pre-owned for convenience;
- stage-earned characters remain locked until the player actually earns them;
- non-SoL event content can be made available without marking it cleared;
- the player does the playing, while Kneekura content packs define schedules,
  login campaigns, gacha pools and new stages.

## Post-EoC profile contract

### Story state

Empire of Cats uses StoryChapters 0, 1 and 2.

For each of those three chapters:

- progress = 48;
- stage clear count for stages 0–47 >= 1;
- valid treasure stages 0–47 = 3 (Superior);
- selected-stage/UI bookkeeping may be normalized by the original game.

Chapter index 3 is the historical non-real slot and is untouched.

Future (Into the Future) and Cats of the Cosmos chapters are not force-cleared.

### Progression reward truth

Ownership is no longer "all guide-visible units with no acquisition
distinction", but it is still intentionally generous.

Exact JP 15.7.1 ownership rule:

1. all guide-visible/playable units that are **not** stage rewards are pre-owned;
2. story-stage rewards (SoL / later story) are initially locked;
3. Tower/dojo-style and event-stage rewards are initially locked;
4. all existing JP 15.7.1 gacha/collab-gacha units are pre-owned;
5. all 18 existing Legend Rare units are pre-owned;
6. hidden/test/regional rows are never granted generically;
7. future/upstream/Kneekura-added units can use the later gacha/login/event
   LiveOps providers without rewriting this historical acquisition rule.

The exact JP 15.7.1 `drop_chara.csv` is the primary stage-reward source.
A non-negative `stageDropCharaID` marks a guide-visible unit as stage-earned.

Version-pinned counts:

- 835 eligible guide-visible/playable units;
- 158 exact stage-reward units left unowned;
- 677 pre-owned non-stage-reward units.

Regression anchors include Madoka (catalog No.289 / asset ID 288), Homura
(No.290 / asset 289), Saber (No.363 / asset 362) and Hatsune Miku
(No.536 / asset 535) as pre-owned, plus all 18 Legend Rare units.

This preserves the reason to clear SoL/Tower/event stages without forcing the
player to reacquire the ordinary/collaboration gacha catalog.

### Economy assist

Economy and progression are separate concepts.

The default Kneekura profile may keep "low-friction" economy values (XP,
materials, Cat Food, tickets, etc.) high so the user does not have to grind,
while acquisition-gated cats/stages remain real progression.

This lets the game remain convenient without deleting the reason to play
stories, event stages, login campaigns and gacha.

## Non-SoL event policy: unlock-only

For event systems, **available** and **cleared** are separate states.

The target state for normal events, collaboration stages, Crazed/Manic-style
stages and other supported event families is:

- map/subchapter visible/enterable;
- chapter unlock state enabled;
- clear_progress = 0;
- per-stage clear count = 0;
- first-clear reward claimed state = false;
- stage-drop cats remain unowned until obtained.

Stories of Legend is excluded from this global unlock-only policy so it can be
played as normal progression from the beginning.

Availability in the UI may also depend on live/server schedules. Therefore the
long-term solution includes an offline event scheduler rather than trying to
encode every availability rule in SAVE_DATA.

## Five-slot login scheduler

The runtime maintains exactly five active player-facing login campaigns.

State machine:

1. Build an eligible pool from exact local `DailyLoginEventData.csv`,
   `DailyLoginEventGrade.json`, `StampData.csv`, reward-item validity and
   required assets.
2. Exclude internal/test/system-only definitions.
3. Shuffle the eligible IDs into a bag.
4. Fill five active slots from the bag.
5. Each active campaign advances at most one stamp on a newly observed local
   day.
6. When one campaign finishes, mark it completed and fill that single empty
   slot with the next bag entry.
7. A newly inserted campaign becomes claimable starting on the next eligible
   local day, preventing same-day chain completion.
8. When the bag is exhausted, reshuffle the eligible pool while avoiding an
   immediate repeat when practical.

Clock policy:

- same local day: no second claim;
- clock rollback: no claim;
- large forward jump: one next stamp only, no skipped-day multiplication.

The existing exact JP 15.7.1 login foundation remains relevant:
`DailyLoginEventData.csv` has 159 rows and `StampData.csv` has 31 rows.
The former 949-only comeback policy is superseded by this multi-campaign
scheduler, though template 949 remains a validated campaign definition.

## Offline-first Kneekura LiveOps

A permanently online game server is **not required** for the first production
architecture.

Use a signed content channel:

```text
Kneekura channel manifest
  ├─ season / revision
  ├─ start/end schedule
  ├─ active event definitions
  ├─ login campaign pool
  ├─ gacha pool/schedule
  ├─ custom stage packs
  ├─ optional asset packs
  ├─ upstream Battle Cats compatibility
  └─ signature
```

The client downloads a new channel revision when connectivity is available,
verifies it, and stores it as the last-known-good pack.

After that, all scheduling and gameplay operate locally. Losing network access
does not make already downloaded seasons disappear.

This provides the experience of "Kneekura runs the game" without requiring a
24/7 stateful backend.

### Initial transport

The simplest control plane is a static signed manifest plus immutable release
artifacts (for example the existing private GitHub/release workflow).

A dedicated server becomes useful only if a later feature truly needs mutable
online state, such as:

- cross-device accounts/cloud saves;
- server-authoritative rankings;
- multiplayer;
- per-user experiments;
- real-time economy;
- server-authoritative gacha/account ledgers.

None of those are required for event rotation, login campaigns, scheduled
gacha or custom stage releases.

## Content-pack contract

Each pack should be immutable and versioned.

Suggested top-level schema:

```json
{
  "schema_version": 1,
  "channel": "kneekura-main",
  "revision": 1,
  "game_anchor": "jp-15.7.1",
  "season": {},
  "events": [],
  "login": {},
  "gacha": {},
  "stages": [],
  "assets": [],
  "upstream": {},
  "signature": {}
}
```

The currently installed pack is always cached locally. A bad or incompatible
new pack must never replace the last-known-good revision.

## Custom stage roadmap

Kneekura-created stages should be data packs, not hard-coded save hacks.

A stage pack carries:

- map/subchapter metadata;
- enemy lineups and timing;
- stage rules/restrictions;
- rewards/drop definitions;
- text/background/music references;
- compatibility requirements.

That allows new "Legend Story" style chapters or seasonal events to be
published without rebuilding the entire client.

## Upstream Battle Cats updates

When PONOS updates the base game:

1. import the owned new version;
2. generate a data/asset/schema delta against the current anchor;
3. refresh unit/event/stage manifests;
4. explicitly classify new units into acquisition classes;
5. migrate the Kneekura content channel to the new anchor;
6. keep the previous known-good revision available for rollback.

New official cats are therefore incorporated as upstream content, not manually
recreated.

## Gacha

The deferred Rare Gacha project becomes one LiveOps provider.

Gacha should read its banners/pools/schedules from the Kneekura content pack
and grant units into the same local acquisition ledger used by story/event/login
rewards.

The original Battle Cats UI remains the preferred presentation layer.

## Preservation rules

- player SAVE_DATA remains local-first;
- never require network to load an already valid local save;
- never silently clear story progress or reward history during a content update;
- content-pack updates are atomic and rollbackable;
- save migrations create a backup before mutation;
- hidden/test units remain excluded unless a specific pack deliberately opts in;
- stage availability must not imply stage cleared;
- owning assets must not imply owning the corresponding unit.

## Immediate implementation order

1. Post-EoC story + Superior treasure bootstrap.
2. Acquisition-class manifest: pre-own all non-stage-reward units while
   preserving exact story/Tower/event stage rewards for play.
3. Non-SoL event unlock-only layer.
4. Five-slot login scheduler.
5. Kneekura signed content-channel manifest.
6. Deferred gacha provider on that channel.
7. Custom Kneekura stage packs.


## Non-destructive evolution rules

Kneekura content updates must not require deleting the player's save or
restarting from a clean profile.

Core rules:

- existing SAVE_DATA is always treated as player-owned state;
- new systems use additive sidecar state or versioned migrations where
  possible;
- a migration reads old state, creates a backup, writes a new revision and
  validates it before promotion;
- content updates never reset story clear counts, reward claims, login progress,
  gacha history or custom-season history merely because the schema changed;
- stable IDs are never recycled for unrelated content;
- retired content is archived/hidden, not destructively removed from history;
- every migration is idempotent and records its applied schema revision;
- last-known-good content pack and pre-migration save remain rollback targets.

A feature that can only be introduced by deleting SAVE_DATA is considered an
architecture failure unless the underlying original game itself makes
migration impossible.

## Content / player-state separation

Kneekura keeps four kinds of truth separate:

1. **Base game data** — official JP assets, units, enemies and maps for the
   anchored Battle Cats version.
2. **Kneekura content data** — seasons, custom stages, event schedules, login
   campaigns and gacha definitions.
3. **Player progression state** — clears, claims, acquired units, pity/history,
   medals and campaign progress.
4. **Runtime cache** — derived indexes, downloaded art, temporary schedule
   expansion and other rebuildable data.

Only category 3 is irreplaceable player state. Categories 1, 2 and 4 may be
updated/rebuilt without wiping progression.

## Future authoring environment

To make Jolly-authored stages fast and repeatable, stage design should be
data-driven rather than hand-edited directly in SAVE_DATA.

### Enemy Atlas

Every official and Kneekura enemy should receive stable metadata tags such as:

- trait / attribute;
- movement speed;
- attack range and effective reach;
- single/area/multi-hit;
- attack cycle and foreswing;
- knockback count;
- health / damage bands;
- special effects;
- target behavior;
- spawn pressure;
- role tags: wall, rusher, backliner, pusher, burst, attrition, disruptor,
  boss, support, gimmick;
- counterplay tags;
- dangerous combinations with other roles.

This is not meant to replace exact source values. The Atlas is an authoring
index built from exact data, native behavior evidence and controlled gameplay
observations.

### Stage authoring model

A Kneekura stage should be expressible as a small declarative definition:

- stage identity and presentation;
- enemy spawn timeline / money thresholds;
- spawn limits and recurrence;
- boss triggers;
- stage rules / restrictions;
- base HP / enemy magnification;
- rewards and drop tables;
- prerequisite / availability policy;
- difficulty target and author notes.

The authoring tool can then validate the stage before it reaches the player.

### Validation and simulation

Future tooling should be able to flag:

- impossible/empty spawn schedules;
- accidental infinite spawns;
- unreachable rewards;
- duplicate or missing IDs;
- unsupported enemy/assets for the anchored game version;
- suspicious difficulty spikes based on Enemy Atlas roles;
- content-pack references that would break older saves.

A lightweight simulator does not need to perfectly solve a Battle Cats stage.
It only needs to help the author spot obvious composition/timing mistakes before
device testing.

## Update philosophy

The project should prefer:

```text
old client + old save
        ↓
new signed content pack
        ↓
small migration if required
        ↓
same player history, more content
```

over:

```text
new feature
   ↓
delete save
   ↓
re-bootstrap everything
```

This is the architectural definition of flexibility for Kneekura.


## Native level-cap convenience migration

The Post-EoC profile may receive a non-destructive convenience migration that
unlocks each eligible unit to its exact JP 15.7.1 native base-level hard cap
without changing story progression.

The requested convenience ceiling is 60, but official DataLocal remains the
authority:

- 323 eligible units are native level-60 units;
- 493 are native level-50 units;
- 11 are native level-20 units;
- 8 are native level-1 units.

The migration updates only each Cat's saved `max_upgrade_level.base` increment
and the SAVE hash. Current levels, ownership, forms, stage progress, reward
claims and Catseye-consumption history remain untouched.

This specifically avoids the bad alternative of marking New/Uncanny Legend
stages cleared merely to unlock a power-up UI condition. Progression truth and
convenience unlocks remain separate.
