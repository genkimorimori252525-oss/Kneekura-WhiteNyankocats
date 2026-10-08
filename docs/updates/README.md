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

## UGOD-001 — Godzilla-style replacement of player catalog No.703 (CONFIRMED form 0)

**User-confirmed target (2026-10-09):** official No.703 **first form = ゴジラにゃんこ**, `unit703.csv` form index **0** (SAVE/unitbuy asset 702). It is the only approved replacement target; the second form **シン・ゴジラにゃんこ** (index 1) remains unchanged. The supplied cropped Godzilla image is a local visual reference, not a Git asset or a claim of an implemented runtime texture.

Enemy source reference: enemy No.552 in `DataLocal/t_unit.csv` index 552, with raw 200 + 200 + 200 = 600 before stage magnification, strike timing 130f/170f/210f, 425f cycle, range 3,800, LD 2,300–3,800, speed 3, KB 1, raw HP 500 and x4 castle damage. These are **enemy reference values**, not an automatic approval to copy every stat (in particular 3,800 sensing, HP, LD, immunities, or enemy x4 castle modifier) onto the friendly cat.

| Metric | Latest user-approved target |
| --- | ---: |
| Replacement character and form | No.703, **ゴジラにゃんこ, form index 0 (confirmed)** |
| Lv reference for approved attack | **Lv30** |
| Cat production cost (EoC Ch.2) | **9,800** |
| Cat recharge | **500s = 15,000f** |
| Attack period (one full three-hit sequence) | **15s = 450f** |
| **Lv30** damage to ordinary enemy units, full 3-hit sequence | **150,000 total** |
| **Lv30** hit 1 | **50,000** |
| **Lv30** hit 2 | **50,000** |
| **Lv30** hit 3 | **50,000** |
| Strike timing from the original enemy | 130f, 170f, 210f |
| Damage to enemy castle **across the entire 3-hit sequence** | **1 total maximum**, not 1 per hit |

**Revision log — 2026-10-09:** The former provisional **1,200,000 total / 400,000 × 3** proposal was explicitly rejected as too strong and **superseded** by Lv30 **150,000 total / 50,000 × 3**. The user also positively confirmed the **first form**; it is no longer provisional. Git history retains the prior design for provenance but it must never remain the active target.

The castle rule remains **target-aware**: ordinary enemy-unit hits deal 50,000 apiece **at Lv30**, unless other explicitly verified engine modifiers apply. Against the enemy castle, the first landed castle hit in a given attack sequence deals 1, and later castle hits in that same 3-hit sequence deal **zero**; the castle budget resets to 1 at the start of the next attack sequence. This must be tracked **per deployed cat instance**, and must not reduce simultaneous damage to ordinary enemy units or affect other cats. Do not implement it by reducing the cat's own attack stat to 1, by using the original enemy's x4 castle multiplier, or by accidentally dealing 1 castle damage **on each strike**.

**Exact Lv30 damage caution:** native player unit attack data uses integer level-1 attack values; according to the JP15.7.1 baseline, Lv30 damage scales by 17. Since 50,000 / 17 is not integral, naïve raw 2,941 would yield **49,997** per hit at Lv30, not the approved 50,000. Actual engine rounding/multi-hit treatment must be verified, with the smallest scoped runtime correction if needed. Level growth outside Lv30 is **not yet specified** and must not be silently hard-coded at 50,000 forever.

**Still pending (NOT approved from enemy reference):** HP and growth, attribute targeting, special abilities/immunities, movement speed, sensing and long-distance reach transfer, exact LD target checks on allied side, use of owner-held animation/sprite files, and original-scene 450f cycle/castle damage hook behavior. Numeric design approval does **not** mean APK integration or on-device success.

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