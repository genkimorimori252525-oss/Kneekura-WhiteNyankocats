# Kneekura WhiteNyankocats — Design Philosophy

Status: approved by project owner on 2026-10-06.

## The principle

**The mod succeeds when it still feels like The Battle Cats.**

Kneekura is not trying to replace The Battle Cats with a lookalike application. The original JP game is the host. Its scenes, menus, transitions, battle renderer, animation system, stage browser, gacha presentation, upgrade screens, save behavior and moment-to-moment interaction are preserved whenever technically possible.

Original Kneekura features should appear as though they naturally belong inside the game.

A feature that is technically easier to implement by replacing an original screen is not automatically acceptable. The default question is:

> Can the original Battle Cats screen, data format or engine path be made to support this feature with a smaller change?

If yes, use the original path.

## 1. Preserve first, extend second

Implementation priority is:

1. unchanged original behavior;
2. original data-driven extension;
3. one narrow original-function hook;
4. one narrow decision-branch patch;
5. a new custom scene only when the original runtime genuinely cannot represent the feature.

This order is mandatory for product work.

The current standalone Java Android UI/battle app is a verification harness. It may prove parsers and rules, but it is not permission to replace the original Battle Cats UI.

## 2. Exact-build evidence beats assumptions

Primary anchor:

- JP 15.7.1 exact verified user-owned APK/export.

Evidence priority:

1. exact JP 15.7.1 binary and pack data;
2. exact historical/current Battle Cats server data with provenance;
3. readable reverse-engineering references that can be mapped back to the exact binary;
4. community/wiki/player-facing evidence as reconnaissance;
5. inference, clearly marked as inference.

TBCML, BCData, Battle Cats Ultimate and Battle Cats Complete are references and accelerators. None of them override conflicting behavior observed in the exact target build.

Never copy native offsets, symbols or patch bytes from another version and assume compatibility.

## 3. Keep the original code surface large and the patch surface small

A good patch changes a small, auditable boundary.

Every product patch must record:

- target APK/native hash;
- target file/function/data record;
- original signature;
- modified signature;
- reason;
- behavior with extension disabled;
- behavior with extension enabled;
- regression evidence.

The project should be able to answer: **what exact parts of Battle Cats did we touch?**

If that answer becomes vague, the design has drifted too far from the preservation goal.

## 4. Data before hooks

When Battle Cats already has a data format for something, prefer feeding the original engine compatible data over replacing its logic.

Examples:

- stage definitions;
- map metadata;
- names/text;
- gacha definitions and pool data;
- local event availability snapshots;
- unit/enemy definitions;
- animation/model assets.

Native/smali hooks exist to bridge gaps such as offline service responses, custom persistence and decisions that cannot be expressed by data alone.

## 5. Original UI is part of compatibility, not decoration

Compatibility includes:

- which original scene is used;
- transition order;
- original touch flow;
- original visual timing;
- original reward/result presentation;
- original capsule/gacha animation;
- original login-stamp presentation;
- original battle scene.

A feature is not considered finished merely because equivalent information appears on a new custom screen.

## 6. Offline means locally authoritative

The final mod must remain useful with external networking unavailable.

Live-service concepts are converted into local state/providers while preserving original callers and scenes as much as possible.

Local providers include:

- clock/day state;
- profile/save extension state;
- local event availability;
- gacha pool/result source;
- login-bonus cycle;
- Kneekura stage-clear rewards.

The final product should not require a localhost HTTP server or Frida process. Those are allowed only as research tools.

## 7. Preserve the official installation

Modified APKs are re-signed, so they cannot be treated as official PONOS-signed updates.

Approved package/profile policy:

- keep the official Battle Cats installation untouched;
- ship Kneekura under separate package identities;
- initially ship **Personal MAX** and **Practice Clean** as separately isolated flavors/packages;
- never write to the official app's private save.

This is preferred over an early custom profile-selector screen because Android's own sandbox gives stronger isolation without changing the original Battle Cats flow.

## 8. Two profiles, two purposes

### Personal MAX

Owner sandbox:

- all safe real playable units unlocked;
- Cat Food/XP/NP/tickets/materials/items MAX;
- locally imported stages available;
- event/collaboration schedule gating disabled locally.

### Practice Clean

Real progression:

- initialize using the original new-game path;
- preserve original tutorial/starter progression;
- no artificial "looks like a new save" reconstruction;
- Kneekura additions participate in a real local economy.

MAX convenience must never silently leak into Practice.

## 9. Super Kneekura Gacha philosophy

The original gacha scene is mandatory unless proven impossible.

Approved first version:

- permanent **スーパーにーくらガチャ**;
- 1 draw = 150 Cat Food;
- 11 draws = 1500 Cat Food;
- original capsule and result presentation;
- rarity distribution copied from an exact JP 15.7.1 original Rare Capsule definition with provenance;
- pool initially includes every real playable unit proven safe through the original gacha acquisition/duplicate path;
- placeholder/regional-empty rows and explicit test/cheat units are excluded;
- Normal/Special/story-only units are added only after their acquisition/duplicate semantics are proven safe.

"All characters" means compatibility-safe breadth first, then verified expansion. It does not mean corrupting the save to satisfy a headline number.

## 10. Login bonus philosophy

Reuse the original comeback/login-stamp presentation.

Approved offline clock policy:

- phone local calendar day is the source;
- one reward on a newly observed day;
- moving time backward grants nothing;
- a large forward jump grants one next reward, not every skipped day;
- after the final stamp, the next eligible day wraps to stamp 1.

This is a stability guard, not an aggressive anti-cheat system.

## 11. Stage availability and historical content

The original stage-selection UI remains the host.

Locally available event/collaboration content should not vanish solely because a live server schedule is absent.

Historical stage provenance order:

1. exact local/install data;
2. exact historical/current server data;
3. clearly labeled reconstruction from community evidence only when exact data is absent.

Never silently present reconstruction as extracted original data.

## 12. Stage Cat Food reward philosophy

Practice Clean receives an additional one-time first-clear Cat Food reward, tracked separately from original drops.

Approved starting table:

| Difficulty | First-clear Cat Food |
| --- | ---: |
| 1–3 | 1 |
| 4–6 | 2 |
| 7–8 | 3 |
| 9–10 | 5 |
| 11 | 8 |
| 12+ | 10 |

Rules:

- first clear only per stable stage/difficulty variant;
- original rewards are not replaced;
- use the original victory/reward presentation when possible;
- keep the table configurable rather than hard-coded into native logic.

## 13. Save philosophy

The original Battle Cats save remains authoritative for original state.

Kneekura-only state goes into a small sidecar unless a proven original field is semantically appropriate.

Never overload unknown original fields merely because space exists.

Sidecar writes must be atomic, versioned and recoverable.

## 14. Reversibility

Every extension should have a disable path.

With Kneekura extensions disabled, the modified build should behave as close to the anchored original JP 15.7.1 build as the necessary offline/package patches allow.

Where exact parity is impossible, document the reason instead of hiding it.

## 15. Research discipline

Temporary tools are allowed to be ugly. Product patches are not.

Frida, custom viewers, standalone harnesses, community databases and debug overlays may be used to learn.

Before a research result becomes product code:

1. map it to exact JP 15.7.1;
2. record evidence;
3. minimize the hook;
4. test extension-off behavior;
5. test offline behavior;
6. record failure/repair history.

## 16. Long-term direction

Android is the proving ground for **modifying without replacing**.

The future PC version should inherit the evidence, normalized data and compatibility rules learned here. It should not become an excuse to abandon original behavior prematurely.

The skill this project is meant to develop is:

> **How far can original Battle Cats be extended while still remaining recognizably, structurally and behaviorally Battle Cats?**

That preservation-first question outranks implementation convenience.