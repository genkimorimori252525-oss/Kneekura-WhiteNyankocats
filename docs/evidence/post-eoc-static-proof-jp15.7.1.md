# Post-EoC static proof — JP 15.7.1

Status: **static candidate complete; device mutation not yet performed.**

The mainline Kneekura profile is now distinct from the earlier all-unit MAX
research save.

## Exact candidate

Built from the real clean JP 15.7.1 baseline captured before the MAX bootstrap:

- size: 497,580 bytes;
- SHA-256: `ed4c7089af27181a13fd96e6dc16df6f02c8b4a23fcabbd9e888334ae81dde03`;
- JP salted-MD5: `908db3c81636002e7baef9ad10567b7f`;
- pinned research parser: PASS;
- parser reserialization: byte-for-byte identical;
- forward-compatible remaining-data: 332 bytes.

No device has received this candidate yet.

## Post-EoC story state

Empire of Cats chapters 1–3 are set to:

- 48 / 48 progress;
- every stage cleared at least once;
- all 48 valid treasures at level 3 (Superior).

Future / Cosmos story chapters remain zero-progress / zero-clear / zero-treasure.

The EoC-1 completion flag is enabled because event visibility depends on
clearing Empire of Cats Chapter 1.

## Acquisition state

The previous generic "own all 835" grant is refined rather than discarded.

Exact JP 15.7.1 selection:

- 835 guide-visible/playable units;
- 158 of those are classified as **stage rewards** because exact
  `drop_chara.csv` has a non-negative `stageDropCharaID`;
- those 158 remain unowned so SoL/Tower/event/etc. rewards are earned by play;
- the remaining **677 units are pre-owned**.

Important regression anchors:

- Madoka ID 289 is pre-owned;
- Homura ID 290 is pre-owned;
- Saber ID 363 is pre-owned;
- Hatsune Miku ID 536 is pre-owned;
- all **18 JP 15.7.1 Legend Rare** units (rarity=5) are pre-owned.

All 400 stage-drop save flags remain zero, so stage reward settlement still
belongs to the original game.

This matches the product rule: **gacha/collab/Legend Rare units are available
immediately; stage-earned characters such as SoL/Tower/event rewards are not.**

## Event unlock-only state

One-field differential serialization against the pinned parser independently
binds the event layout:

- selected-stage type-0 base: 24,450;
- clear-progress type-0 base: 34,450;
- stage-clear type-0 base: 68,450;
- chapter-unlock-state type-0 base: 284,450.

Each event type has 500 map slots and four star slots. Stage-clear blocks use
12 stages per star.

Exact JP 15.7.1 DataLocal contains:

- 436 `MapStageDataS_*.csv` normal-event maps;
- 277 `MapStageDataC_*.csv` collaboration maps.

Post-EoC policy:

- SoL: only map 0 / first star unlocked; no clear state;
- normal event: all 436 exact maps first-star unlocked, clear/progress zero;
- collaboration: all 277 exact maps first-star unlocked, clear/progress zero.

This is **availability without completion**. It does not pre-claim rewards.

A separate offline scheduler is still required to surface events whose original
UI visibility is controlled by a live/server schedule.

## Economy

The low-friction economy layer is retained from the already verified MAX
resource transformer. This intentionally separates grind reduction from content
progression.

## Research boundary

BCSFE-Python pinned commit
`85fb94cbf00c6a74dbef58932610fb94ec8f7495` is used only as a disposable
GPL research oracle for parsing, exact round-trip and one-field differential
mapping.

The shipping Post-EoC transformer/verifier do not import or copy BCSFE code.
