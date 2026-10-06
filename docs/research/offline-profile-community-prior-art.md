# Offline MAX Profile — Community / Prior-Art Reconnaissance

Status: step-001 evidence, 2026-10-07.

## Scope and authority

This document records public prior art useful for the JP 15.7.1 offline profile
bootstrap. Community tools are treated as reconnaissance and independent
corroboration only. Exact JP 15.7.1 owned binaries, owned game data and the
resulting local SAVE_DATA remain authoritative.

The target is the isolated research package. Modified account state must not be
uploaded to PONOS services as part of this project.

## Strongest prior art: BCSFE-Python

Primary reference:

- https://github.com/fieryhenry/BCSFE-Python
- canonical upstream is linked by that mirror as
  https://codeberg.org/fieryhenry/BCSFE-Python
- inspected GitHub mirror revision:
  `85fb94cbf00c6a74dbef58932610fb94ec8f7495`

BCSFE is especially useful because it is not merely a table of offsets. It has a
version-aware SAVE_DATA parser/writer, game-data-backed cat metadata, resource
editors, tutorial clearing, save hashing and device pull/push helpers.

Its changelog records a JP 15.3.0 parsing fix in 3.3.0 (2026-04-01), making it a
much closer modern reference for JP 15.7.1 than older fixed-offset editors.

### License boundary

BCSFE declares GPL-3.0-or-later and its README explicitly discusses derivative
programs using the editor. Therefore this project does not copy BCSFE
implementation code into Kneekura sources.

Allowed research use here:

- compare structure and behavior;
- use values as hypotheses;
- reproduce independently verified facts from exact JP 15.7.1;
- optionally use an external BCSFE installation as a disposable oracle during
  research, without making it a shipping runtime component.

## SAVE_DATA architecture corroborated by BCSFE

BCSFE's Android/root helpers look for:

`/data/data/<package>/files/SAVE_DATA`

Its SaveFile parser serializes the game state and then regenerates a save hash.
The current writer uses a salted MD5 path for save integrity.

This is distinct from the `.pack/.list` integrity path that previously produced
H01. The offline profile work should therefore avoid touching DataLocal merely
to change player state.

Architectural implication for Kneekura:

- prefer a SAVE_DATA bootstrap / transform;
- keep the original data packs untouched;
- back up the entire existing save before mutation;
- regenerate/validate the normal save integrity data rather than bypassing it.

## Tutorial clear: prior-art minimal mutation

BCSFE does not clear the entire main story merely to escape the tutorial.

Its `StoryChapters.clear_tutorial` raises a small group of tutorial/UI state
values and ensures the first EoC stage is cleared if needed. In simplified
behavioral terms it:

- raises `tutorial_state` to at least 1;
- raises the Korea superior-treasure/tutorial state to at least 2;
- raises one UI state to at least 1;
- initializes two tutorial dialog entries to at least 2;
- clears only EoC chapter 1 stage 1 when it is still uncleared.

This is a better model for the research profile than marking every story chapter
complete. The exact JP 15.7.1 fields still need independent confirmation.

## Cat ownership model

BCSFE's current Cat representation independently indicates that ownership is
not one monolithic flag. Relevant state includes:

- `unlocked`;
- `gatya_seen`;
- base/plus upgrade level;
- current form;
- unlocked forms;
- Cat Guide collected state;
- fourth-form state;
- talents and catseye use.

Its normal unlock operation sets the cat's ownership and gacha-seen state and
also maintains dependent drop/equipment-menu state.

For the requested first-form baseline, the candidate neutral contract is:

- `unlocked = 1`;
- `gatya_seen = 1`;
- `current_form = 0`;
- do not force true/fourth form;
- preserve a normal low/base upgrade state until the exact JP save semantics are
  verified.

Do not simply set every integer in the cat arrays to 1.

## Enumerating real / obtainable cats

BCSFE uses exact game data rather than assuming that every integer ID is a
playable unit.

Two useful sources are:

- `DataLocal/nyankoPictureBookData.csv`: BCSFE's
  `get_obtainable_cats()` filters on the Cat Guide display flag;
- `DataLocal/unitbuy.csv`: provides unit metadata, rarity, version gating,
  form/evolution fields and upgrade limits.

Kneekura should derive its candidate owned-unit set from the exact JP 15.7.1
tables and then intersect it with the already-audited unit assets. Placeholder,
test and structurally incomplete rows stay excluded.

## Community cap candidates

BCSFE's current default max-value helper gives the following values.

These are **reference candidates, not yet JP 15.7.1 proof**:

| Resource | BCSFE default maximum candidate |
| --- | ---: |
| Cat Food | 45,000 |
| XP | 99,999,999 |
| Normal Tickets | 2,999 |
| Rare Tickets | 299 |
| Platinum Tickets | 9 |
| Legend Tickets | 4 |
| NP | 9,999 |
| Leadership | 9,999 |
| Battle Items | 9,999 |
| Catamins | 9,999 |
| Catseyes | 9,999 |
| old catfruit representation | 128 |
| newer catfruit representation | 998 |
| Base Materials | 9,999 |
| Talent Orbs | 998 |
| Event Tickets | 9,999 |
| Treasure Chests | 9,999 |

The BCSFE catfruit editor switches from the old maximum model to the new model
at game version 11.4, so JP 15.7.1 belongs to the newer representation.

BCSFE's own editor warns that Cat Food and premium tickets are server-managed /
ban-sensitive when used with live accounts. Old community discussions disagree
about historical online thresholds. Those online anti-cheat thresholds are not
used as our storage truth. The project remains offline/isolate-first and will
derive exact local representation and UI/storage constraints before selecting
final caps.

## Other prior art

### MCMi460/Battle-Cats-Save-File-Editor

Repository:

https://github.com/MCMi460/Battle-Cats-Save-File-Editor

The older editor independently contains edit modules for Cat Food, XP, NP,
tickets, catseyes, catfruit, leadership, battle items, base materials, obtaining
cats, evolving cats and save-file patching.

It is mainly useful as historical corroboration that these categories are
stored/editable save state. Its older offsets and version assumptions must not
be imported into JP 15.7.1.

### csehydrogen/BattleCatsHacker and beeven/battlecats

These older projects are useful for historical SAVE_DATA / hash-layout
reconnaissance and explain why fixed byte offsets are fragile across game
versions. They are not authoritative for 15.7.1.

### Battle Cats Complete / TBCML

Battle Cats Complete remains valuable for data-format corroboration and TBCML
for APK/data modification behavior, but neither substitutes for the exact
15.7.1 player-save proof.

## Chosen architecture after prior-art review

The initial implementation direction is now:

1. **SAVE_DATA before native live hooks.**
   Transform a real save at rest where possible instead of permanently
   intercepting resource setters at runtime.
2. **Backup first.**
   Hash and copy the original research-package SAVE_DATA before any mutation.
3. **Minimal tutorial bypass.**
   Reproduce only the exact fields needed to escape the tutorial after
   independently confirming them.
4. **Exact-data unit enumeration.**
   Picture-book display flag + unit metadata + asset completeness, not a guessed
   contiguous ID range.
5. **First-form ownership only.**
   Ownership and visibility dependencies are updated, but no forced true/fourth
   forms.
6. **Version-pinned caps.**
   The table above is a hypothesis set. Exact JP 15.7.1 binary/data and
   round-trip save validation decide the final numbers.
7. **One-time bootstrap sentinel.**
   Once a valid modified save is installed, later game launches must not reset
   user changes.
8. **No server synchronization.**
   Modified premium currency/account state is not intentionally uploaded to
   live PONOS endpoints in this offline research lane.
9. **No DataLocal mutation for player state.**
   This keeps the already-learned H01 pack/list integrity boundary separate from
   SAVE_DATA work.

## Immediate next evidence

Step-002 should prove, against the exact owned JP 15.7.1 artifacts:

- research `getFilesDir()` mapping and reachable SAVE_DATA location;
- save header/version/hash wrapper;
- exact cat-array count and ownership/form field ordering;
- tutorial field mapping;
- XP/Cat Food/tickets/NP/leadership/material arrays and storage widths;
- exact caps/validation sites where recoverable;
- whether a BCSFE 3.6.x round trip can parse and re-emit an untouched 15.7.1
  research SAVE_DATA byte-semantically without destructive drift.

No mutating device run is allowed until the baseline backup/result manifest is
implemented.
