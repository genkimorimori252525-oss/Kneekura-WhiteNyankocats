# KNEEKURA Update — UMDK-001 + UGOD-001 (JP 15.7.1)

Status: **USER-APPROVED NUMERIC DESIGN; NOT IMPLEMENTED; NOT RELEASED.**
Updated: 2026-10-09 (JST).
Machine-readable contract: [kneekura-balance-2026-10-09.json](kneekura-balance-2026-10-09.json).
This release plan is additive to the existing offline, base-preserving Android project. It **must not** rebuild the owner's SAVE_DATA, unlock story stages, replace the original game UI, or introduce live PONOS networking. Proprietary PNG/model/animation, APK and saves are not checked into Git.

## UMDK-001 — Ultimate Madoka, catalog No.289, form index 2

The user has **approved** these parameters (no design alternatives needed):

| Metric | JP15.7.1 original | Approved Kneekura |
| --- | ---: | ---: |
| Lv30 HP | 55,250 | 55,250 (keep) |
| Lv30 total attack | 31,450 | **28,000** |
| Standing / sensing range | 550 | **750** |
| Long-distance attack reach | 450–800 | 450–800 (keep) |
| Attack cycle | 271f (9.03s) | 271f (keep) |
| Foreswing | 72f (2.40s) | 72f (keep) |
| Movement | 20 | 20 (keep) |
| Knockbacks | 4 | 4 (keep) |
| Production cost (EoC Ch.2) | 4,350 | **4,550** |
| Recharge | ~4,146f (~138s) | **4,650f (155s)** |

Preserve all original special abilities/target traits, LD minimum, all 3rd-form animation assets including unique death animation, and both earlier forms.
Reason: keep the LD 450–800 identity, but stop Madoka automatically walking from a 550 sensing distance into the <450 close-range blind spot. Being knocked back or having enemies move inside 450 still creates a natural blind spot.
Source: user-owned `DataLocal/unit289.csv` form index 2, SHA-256 `e48bc212537fe7949c74527f0a8212874e8595fd9414f6d9bc2b7a1e3aee1a82`; [original baseline](../research/ultimate-madoka-baseline-jp15.7.1.md); [Issue #2](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/2).
Identity: public No.289 = asset ID 288, `unit289.csv` row 2.

**Accuracy gate:** Lv30 native stat = Lv1 raw attack × 17 in this dataset; 28,000 / 17 is non-integral. An ordinary integer CSV change would produce e.g. 27,999 rather than exactly 28,000. Do not claim an exact native 28,000 result without checking actual engine rounding or using a scoped runtime correction.

## UGOD-001 — Godzilla-style replacement of player catalog No.703

The owner's wording says “シン・ゴジラにゃんこの第1形態”; **the official No.703 first form is ゴジラにゃんこ (CSV row 0), while シン・ゴジラにゃんこ is the second form (CSV row 1)**. Until further clarification, index 0 is selected *only provisionally* from the explicit “第1形態” instruction, and no appearance or gameplay replacement is applied. Keep the second form unchanged.

Enemy reference: enemy No.552 in `DataLocal/t_unit.csv` index 552, official un-magnified base attack 200 + 200 + 200 = 600, attack hit timing 130f/170f/210f, 425f cycle, 3,800 sensing range, LD 2,300–3,800, speed 3, KB 1, enemy base HP 500 and x4 castle damage. The user explicitly selects the stronger **1,200,000** stage-magnified attack *distribution*, NOT raw 600; do not accidentally copy the low default stats.

| Metric | User-approved target |
| --- | ---: |
| Cat production cost (EoC Ch.2) | **9,800** |
| Cat recharge | **500s = 15,000f** |
| Attack period (one full three-hit sequence) | **15s = 450f** |
| Damage to ordinary enemy units, per sequence | **1,200,000 total** |
| Hit 1 | **400,000** |
| Hit 2 | **400,000** |
| Hit 3 | **400,000** |
| Strike timing from the original enemy | 130f, 170f, 210f |
| Damage to enemy castle **across the full three-hit sequence** | **1 total maximum**, not 1 per hit |

The castle rule is intentionally **target-aware**: regular enemy-unit hits remain 400,000 apiece. Against the enemy castle, the first landed castle hit in a particular attack sequence deals 1, and any later castle hits within that same sequence deal 0; this resets at the next attack sequence. It does not alter other cats, collaterally damage ordinary enemies, or change base defense. This is a post-target-classification and post-modifier **HP deduction** contract; do not implement it by setting the normal attack stat to 1, by applying an x4 castle modifier, or by treating three landed hits as 3 castle damage.

User-approved hit damage is exact in the contract; it is not yet assigned to a specific level-growth curve. Friendly No.703 originally uses integer Lv1 attack fields and Lv30 scales by 17: 400,000 / 17 is non-integral. Exact Lv30 400,000 each may require a narrow runtime correction. Also verify the game has no implicit min-1 HP deduction after an intended 0 castle damage hit.

**Still needing decisions and original-runtime verification:** whether to replace actual form 0 vs form 1, HP target and growth, Floating-only native traits and other ability transfer, exact reference level/scale, original sprites/effects availability, LD range and sensing behavior on the allied side, animations and native 450f cycle calibration. This file intentionally does **not** mark any of those unspecified gameplay changes approved.

Data provenance from the owner-supplied JP 15.7.1 APK (read-only extraction):
- `DataLocal/unit703.csv` SHA-256 `8caeff21c1c02918da708d06095def423d05f9df14da63b741ac78994b57dbad`.
- `DataLocal/t_unit.csv` SHA-256 `d4fe8661e39a8f489e7549f03b5de4020acb6d7f8560438bdbb9490ec2f8cb04`.
- Community corroboration: https://battlecats-db.com/enemy/552.html and https://battlecats-db.com/unit/313.html/703.html .

## Integration boundaries and acceptance gates

1. Keep original asset formats and original UI/animation scene. Build *overlay first*, never directly mutate the shipped `DataLocal.list`/`DataLocal.pack` blindly: prior changes triggered the H01 integrity error.
2. Never write player level, ownership, inventories, chapter/stage progress, or SAVE_DATA for a balance adjustment.
3. Before implementation, resolve exact native fields for attack frequency, cost, respawn and three-hit animation. Document exact byte/source receipts instead of guessing indices.
4. Use a tightly scoped native/runtime damage policy for castle HP deduction only if original format cannot express the “1 total for three hits” rule. Sequence identity must be per deployed cat instance, not a global flag.
5. Static tests only prove manifest invariants or reference algorithm. Original-game APK launch, battle checks with both enemy units and castle, restart/persistence, and rollback require separate **USER_GATE**.
6. Any device command provided to a person must first pass AGENTS.md terminal-validation checks, and any PowerShell changes require Windows parser CI.
7. Record a future implementation commit, original-game screenshots/videos, checks and rollback evidence before changing `status` to IMPLEMENTED or RELEASED.