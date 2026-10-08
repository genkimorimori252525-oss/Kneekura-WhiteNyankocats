# Kneekura WhiteNyankocats — Base-Preserving Android Mod Design

Status: proposed current architecture after the 2026-10-06 direction correction.

Target anchor: JP 15.7.1, exact verified user-owned APK/export.

## 0. North star

The Android product must feel like **The Battle Cats itself**, not a separately recreated game.

The product therefore keeps the original application's:

- native scene graph and screen transitions;
- Battle Cats UI layout and touch flow;
- battle renderer and animation system;
- stage list presentation;
- gacha scene and capsule-result presentation;
- unit/formation/upgrade screens;
- save/progression semantics wherever possible.

Kneekura code is judged by how little of the original runtime it has to replace.

The existing Java Android app in this repository is a verification harness only. It is useful for parser/rule tests but is not the final user interface.

## 1. Architecture

```text
           Exact JP 15.7.1 APK
                   |
      +------------+-------------+
      |                          |
original assets / packs      original native engine
      |                          |
      |                +---------+----------+
      |                |                    |
 patched data      tiny native shim     tiny bootstrap
      |                |                    |
      +---------+------+--------------------+
                |
      Kneekura local services
        |       |        |       |
      clock    save     gacha   events
        |       |        |       |
        +-------+--------+-------+
                |
        app-private local state
```

The hierarchy of preferred implementation mechanisms is:

1. express the feature through an original Battle Cats data file;
2. intercept one existing original engine boundary;
3. patch a small original decision branch;
4. add a new scene only as a last resort.

A recreated replacement screen is not acceptable when the original screen already exists.

## 2. Build pipeline

The build should be reproducible and version-pinned.

### Inputs

- exact JP 15.7.1 base APK/splits supplied locally by the user;
- locally imported historical/current server packs as required;
- Kneekura-only assets/config;
- patch manifest;
- signing key owned by the local project/user.

### Pipeline

1. fingerprint every APK split and native library;
2. unpack/decrypt required Battle Cats packs;
3. apply data-only changes first;
4. inject the Android bootstrap/native shim only if required;
5. apply exact-version native/smali patches by verified signature/offset;
6. rebuild packs;
7. rebuild APK;
8. sign with the Kneekura key;
9. verify patched hashes and hook ledger;
10. run offline/network-denial and original-scene regression tests.

TBCML is the primary implementation reference for the packaging layer because it already covers pack encryption, APK asset edits, smali/native patching, repackaging and signing.

## 3. Patch ledger / "do not break the base game" contract

Every modification must be represented by a patch-ledger entry:

- base APK/native SHA-256;
- target file/library;
- exact target version;
- function/data symbol hypothesis;
- original byte/data signature;
- modified byte/data signature;
- reason for the patch;
- original behavior with extension disabled;
- expected Kneekura behavior with extension enabled;
- regression test.

No broad binary rewrite is accepted when a narrow hook can do the same job.

The long-term target is a small, auditable hook set, not a forked engine.

## 4. Offline service layer

The original game expects some live-service state. Instead of rebuilding the UI, Kneekura supplies local answers to the original callers.

Conceptual service boundary:

```text
KneekuraLocalService
  Clock
  ProfileStore
  SaveBridge
  EventSchedule
  GachaProvider
  LoginBonusProvider
  StageRewardProvider
  NetworkGate
```

### Network policy

Final offline mode should not contact PONOS endpoints.

Preferred final state:

- no external socket use in normal play;
- original scene callers receive local results;
- no localhost HTTP server required;
- Android INTERNET permission may be removed once exact JP 15.7.1 proves no original startup path requires it after hooks are installed.

During reverse engineering, temporary Frida hooks/local test servers may be used, but they are not final dependencies.

## 5. Profiles

Two gameplay intents are required.

### 5.1 Personal MAX

Purpose: the owner's unrestricted personal build.

Initial state:

- all playable characters obtained;
- first form available by default;
- Cat Food MAX;
- XP MAX;
- NP MAX;
- tickets/materials/battle items/evolution resources MAX;
- all locally imported stages available;
- event/collaboration schedule gating disabled locally.

This profile can still use gacha and login bonus for fun, but resources remain effectively unrestricted.

### 5.2 Practice Clean

Purpose: a real progression run.

Rule: **do not hand-invent a fake starting save if the original game can initialize one.**

Preferred implementation:

1. call the original new-game/save-initialization path;
2. preserve the original tutorial and starter unlock state;
3. add only the offline service flags and Kneekura extension state;
4. let original progression unlock normal content.

This gives the clean mode the same starting composition as the base game rather than a manually maintained clone.

### 5.3 Physical isolation recommendation

Recommended first implementation: two build flavors / package IDs, both using the original Battle Cats UI:

- `Kneekura Personal MAX`
- `Kneekura Practice`

Reason:

- no custom profile-selection screen is needed;
- saves cannot accidentally contaminate each other;
- Personal MAX can be reset independently;
- Android app sandbox separation is automatic.

A one-APK profile selector can be added later only if there is a compelling reason.

## 6. Super Kneekura Gacha

### User-facing rule

The original gacha scene is the host.

Normal Cat Capsule remains available.

A permanent second gacha entry is added:

**スーパーにーくらガチャ**

Costs:

- 1 draw: 150 Cat Food
- 11 draw: 1500 Cat Food

There is no live schedule dependency.

### Implementation preference

Use the original rare/event gacha scene, buttons, capsule animation and result flow.

Prefer registering a local persistent gacha definition through original data such as the existing gacha/event-setting tables. Hook only the provider/result decision if a pure data entry is insufficient.

Do **not** draw a custom Kneekura gacha screen.

### Pool construction

The source pool is computed from imported unit metadata rather than written as a fragile hand list.

Default eligibility proposal:

- every real playable JP unit;
- collaboration units included even when the original collaboration is inactive;
- exclude JP placeholder/regional-empty slots;
- exclude explicit test/cheat units such as ネコチーター unless a separate debug flag enables them;
- eggs/forms resolve to their real unlock unit rather than becoming invalid duplicate IDs.

### Rarity rates

The rarity-vector must be **derived from an exact original JP 15.7.1 Rare Capsule definition** and frozen into the local config with provenance.

That means "based on the original game" is literal: Kneekura copies an original rarity distribution instead of guessing a new one.

Within each rarity bucket, Super Kneekura Gacha defaults to uniform probability across eligible units in that rarity.

Open design question: Normal/Special/story units do not naturally belong to the normal Rare Capsule rarity vector. See section 12.

### Duplicate handling

Use the original gacha acquisition/duplicate path whenever possible so:

- new-unit unlock flags;
- +levels;
- storage;
- XP/NP conversion;
- result animations

continue to behave like the original game.

If a nonstandard unit cannot safely travel through the original gacha result path, the build must exclude it until a compatibility adapter is proven. "All characters" does not justify corrupting the original save.

### First version recommendation

No guaranteed Uber rule and no rotating banners in v1.

One permanent Super Kneekura pool is easier to audit and gives the clean profile a stable economy.

## 7. Offline cyclic login bonus

### User-facing rule

Reuse the original comeback/login-stamp UI and assets.

One stamp may be claimed per local calendar day.

After the final stamp:

```text
last stamp -> next eligible day -> stamp 1
```

The cycle therefore repeats forever.

### Local state

Store separately from original live-service state:

- `last_claim_epoch_day`
- `cycle_index`
- `last_seen_epoch_day`
- schema/version

### Clock policy

Primary clock: Android local wall-clock date.

Recommended safeguards:

- grant at most one stamp per newly observed local day;
- moving the clock backward never grants an extra stamp;
- moving the clock forward many days grants one next stamp, not one for every skipped day;
- timezone changes do not retroactively grant multiple stamps.

This is not intended as hostile anti-cheat; it mainly prevents accidental repeated claims.

### Reward table

Preferred source: copy the original comeback-login reward sequence into a local Kneekura table while reusing the original display path.

If the original sequence includes a reward that is meaningless offline, replace only that reward entry while retaining the original sequence length/UI.

## 8. Offline event/stage availability

The original stage-selection scenes remain the host.

Goal: locally imported content should not disappear merely because an online event schedule is inactive.

### Local schedule policy

Practice Clean:
- story progression restrictions remain;
- event/collaboration maps present in the local data can be exposed through a permanent local schedule;
- stage-clear state still matters.

Personal MAX:
- all locally imported stage groups are visible/unlocked.

Preferred implementation:

1. preserve original stage/map definitions;
2. supply a local event-schedule snapshot to the original availability checks;
3. avoid changing the stage-list scene itself.

Crazed/Manic, Legend, collaboration and historical event maps therefore appear through the normal original stage UI.

### Historical content provenance

Availability priority:

1. exact user-owned local/install data;
2. exact imported historical/current server data;
3. community reconstruction only as explicitly marked fallback.

A reconstructed stage is never silently labeled as extracted original data.

## 9. Stage Cat Food rewards

Kneekura adds a new offline progression reward without replacing original drops.

### Rule

Each stage may award a **one-time first-clear Cat Food bonus** per Practice profile.

It is tracked independently so replaying the stage cannot farm Cat Food.

Original stage drops/rewards remain untouched.

### Reward source

Use the game's evidenced difficulty/rating field once its exact JP 15.7.1 semantics are fixed.

Proposed starting balance:

| Difficulty band | Cat Food first clear |
| --- | ---: |
| 1–3 | 1 |
| 4–6 | 2 |
| 7–8 | 3 |
| 9–10 | 5 |
| 11 | 8 |
| 12+ | 10 |

This is deliberately modest because thousands of local stages exist.

The table is Kneekura configuration, not hard-coded native logic.

### Original UI integration

Preferred order:

1. use an existing item/reward grant path capable of granting Cat Food;
2. use the original result/reward dialog to display it;
3. hook post-win settlement only to append the Kneekura bonus.

Do not create a separate victory screen.

State:
- bit/set keyed by stable stage identity + difficulty/star variant;
- reward is granted after original clear state commits successfully.

## 10. Save architecture

The original save serializer should remain authoritative wherever possible.

Kneekura adds a sidecar state file only for data the original save has no suitable field for:

```text
Original Battle Cats save
  - units
  - XP/Cat Food/inventory
  - stage clear
  - formations
  - normal progression

Kneekura sidecar
  - profile mode
  - login cycle index/day
  - Super Kneekura gacha config/version
  - first-clear Kneekura Cat Food claims
  - local event-snapshot version
  - extension feature flags
```

The sidecar should have:
- schema version;
- checksum;
- atomic temp-write + rename;
- backup of previous revision.

The original save is not repurposed as a dumping ground for custom state.

## 11. Package/signature strategy

Any modified APK must be re-signed.

That creates an unavoidable Android constraint: a build signed with a Kneekura key cannot update/coexist as though it were the Play Store build signed by PONOS.

Recommended development/product route:

- separate package identity;
- separate Android app sandbox;
- original UI/runtime/assets remain inside that package;
- never write the installed official app's private save.

This preserves the official installation and makes rollback safe.

If later testing proves package-name changes break native assumptions, use the original package name only on a dedicated test device after backing up/removing the official installation. That is a fallback, not the default.

## 12. Open questions before implementation

### Q1. What does "all characters" mean for Super Kneekura Gacha?

Recommended option A:
- all **real playable characters that can safely pass through the original gacha acquisition path**;
- Normal/Special/story-only units continue to use original unlock methods;
- collaboration Rare/Super Rare/Uber/Legend units are all included.

Aggressive option B:
- literally every real playable unit, including Normal/Special/story rewards;
- requires proving acquisition/duplicate behavior for those non-gacha classes.

Recommendation: start A, then expand to B only after save-compatibility tests.

### Q2. Package layout

Recommended:
- keep official Battle Cats installed;
- Kneekura uses a different package id;
- Personal MAX and Practice are initially two package flavors.

Alternative:
- one Kneekura package with two profiles.

Recommendation: two flavors first because it is much harder to damage the wrong profile.

### Q3. Clock changes

Recommended:
- trust local phone date;
- one stamp per observed new day;
- backward clock gives nothing;
- large forward jumps give only one stamp.

Alternative:
- fully trust every manually changed day and allow repeated clock-based farming.

### Q4. Stage Cat Food balance

The proposed 1/2/3/5/8/10 table is intentionally conservative.

It should be treated as configuration so it can be changed after a real Practice run without binary patching.

## 13. Development phases

### Phase A — exact original runtime boot

- reproduce/re-sign the exact JP 15.7.1 app;
- change package only if required for coexistence;
- boot to original base screen;
- verify no visual/scene changes.

### Phase B — network isolation

- identify original network/time/save wrapper boundaries;
- temporarily trace with Frida;
- redirect to local service;
- boot and play with external networking unavailable.

### Phase C — profiles

- original new-game initialization for Practice;
- Personal MAX overlay;
- separate save roots/build flavors.

### Phase D — stage schedule

- expose local historical/event stage data through original stage UI;
- verify Legend, Crazed/Manic and collaboration maps.

### Phase E — Super Kneekura Gacha

- register permanent original-style gacha;
- 150 / 1500 Cat Food;
- original capsule/result flow;
- exact original rarity vector;
- compatibility-filtered all-character pool.

### Phase F — login bonus

- reuse original comeback/login stamp scene;
- local day provider;
- cyclic rewards.

### Phase G — stage Cat Food reward

- one-time local claim state;
- original win/result UI;
- difficulty-based table.

### Phase H — regression/audit

For every patch:
- extension off == original scene behavior;
- extension on changes only intended state;
- no external PONOS dependency;
- no corruption when app is killed during save;
- clean reinstall/import path documented.

## 14. Definition of "success"

The user should be able to hand the phone to somebody familiar with Battle Cats and have them naturally navigate it as Battle Cats.

They should notice Kneekura because of **new content inside familiar screens**, not because the game has been replaced by a new interface.