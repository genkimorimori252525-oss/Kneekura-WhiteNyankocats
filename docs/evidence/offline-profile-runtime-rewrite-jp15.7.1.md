# JP 15.7.1 original-game SAVE_DATA rewrite proof

Status: **original UI accepted MAX candidate; post-restart save growth explained.**

The 497,580-byte offline MAX candidate opened normally in the original Battle
Cats scene, then opened normally again after process restart while the user
visually confirmed the MAX profile remained present.

The original game then rewrote SAVE_DATA to 507,174 bytes. Its JP salted-MD5 is
valid, pinned BCSFE-Python parses it completely, and reserialization is
byte-identical. This is a normal original-game normalization, not corruption.

## Exact growth

The rewrite adds **9,594 bytes**. Parsed candidate/post-rewrite comparison
accounts for all of them exactly:

| Generated structure | Byte growth |
| --- | ---: |
| 835 cat `chara_new_flags` records | 6,680 |
| 115 mission clear-state records | 920 |
| 115 mission requirement records | 920 |
| 115 mission preparing-value records | 920 |
| 9 `uiid1` records + first list payload | 84 |
| 1 `uiid3` record | 5 |
| 6 unlock-popup records | 30 |
| 2 first-lock records | 10 |
| 1 stage-id record | 4 |
| 1 outbreak-stage record | 5 |
| forward-compatible remaining-data growth | 16 |
| **Total** | **9,594** |

The first four generated families alone explain 9,440 bytes. The remaining
154 bytes are normal UI/event bookkeeping plus the 16-byte tail extension.

## MAX state after original-game rewrite

Full parser inspection of the real 507,174-byte post-restart SAVE_DATA confirms:

- 835 units remain owned and gacha-seen;
- all 835 remain on first form;
- no true/fourth-form ownership was forced;
- Cat Food = 45,000;
- XP = 99,999,999;
- Normal/Rare/Platinum/Legend tickets = 2,999 / 299 / 9 / 4;
- Platinum Shards = 9;
- NP and Leadership = 9,999;
- all 29 evolution/Behemoth materials = 998;
- all 6 Catseyes = 9,999;
- all 3 Catamins = 9,999;
- all 16 base materials = 9,999;
- engineers = 5;
- all 55 event/lucky-ticket save slots = 9,999;
- all 4 labyrinth medals = 9,999;
- all 42 treasure-chest slots = 9,999;
- all 310 exact JP 15.7.1 Talent Orb types = 998.

## Runtime shift map

Relative to the 497,580-byte candidate layout, the original game's generated
records shift later fields by deterministic amounts in this rewrite:

- early cat/item fields through Catamins: +0;
- Base Materials / engineers: +6,725;
- event tickets / NP / Leadership: +9,485;
- Talent Orbs and all later known fields: +9,578;
- remaining-data itself then grows another 16 bytes at the end.

This map lets the independent verifier perform a complete semantic check on the
known 507,174-byte normalized form without depending on BCSFE at runtime.

## Previous rollback classification

The previous bootstrap runner rolled back only because its verifier required
SAVE_DATA size to remain exactly 497,580 bytes. Both original-UI acceptance
questions had already passed. That exact-size assumption is now classified as a
verifier bug and is being removed.
