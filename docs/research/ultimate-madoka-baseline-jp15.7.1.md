# Ultimate Madoka — official JP 15.7.1 performance baseline

Status: **research baseline only**. No balancing patch or original game data mutation has been released.

## Identity and provenance

- Game: Battle Cats JP 15.7.1 as used by Kneekura.
- Display: No.289, third form **アルティメットまどか**.
- Unit pack entry: `DataLocal/unit289.csv`, third row (form index 2).
- Zero-based `unitbuy.csv`/picturebook index: **288** (this differs from the display number No.289). Do not silently interchange these identifiers in future code.
- Class: 超激レア.
- First/second/third form: 鹿目まどか / まどか＆ネコ / アルティメットまどか.
- Third form originally added in Ver14.1.1, corroborated by public sources.

Owned-install receipt:

- The outer owner ZIP mounted in this analysis session was incomplete at its tail and therefore failed central-directory extraction. Its already-complete embedded `apk/split_InstallPack.apk` was individually recovered and verified with an APK ZIP CRC full scan = PASS. Do not claim a SHA-256 match for the incomplete outer ZIP.
- `unit289.csv` decrypted from the intact embedded DataLocal pack, SHA-256:
  `e48bc212537fe7949c74527f0a8212874e8595fd9414f6d9bc2b7a1e3aee1a82`.
- `unitbuy.csv` SHA-256:
  `bc1adab2fc6ad79f3b8198a8a4d40786756d586af846fdbdeccdbaec55226daf`.
- `nyankoPictureBookData.csv` SHA-256:
  `bc3f233d2d8b7c3e69229464c1da4eb7d6dcd886de55feaccf44f0c6394f1aee`.
- `SkillAcquisition.csv` SHA-256:
  `866788d7ecb6a8c821086ed0f876fc5b294054799b1dfdd83db935513899b1c9`.
- The exact SkillAcquisition table contains no record for internal unit index **288**, so no native Madoka talents are defined in this anchor.
- `nyankoPictureBookData.csv` row 288 reports **three forms**, no fourth form.

## Exact local row: third form

The third row of `unit289.csv` has these relevant values:

| 0-indexed column | Raw | Meaning (independently corroborated) |
|---|---:|---|
| 0 | 3250 | Lv1 base HP |
| 1 | 4 | Knockback count |
| 2 | 20 | Movement speed |
| 3 | 1850 | Lv1 base attack damage |
| 5 | 550 | Standing / sensing range |
| 6 | 2900 | Raw cost (4,350 in EoC Chapter 2 battle) |
| 13 | 72 | Attack foreswing frames |
| 27 | 100 | Slow chance, percent |
| 28 | 90 | Slow duration, frames before treasure effects |
| 44 | 450 | LD minimum hit range |
| 45 | 350 | LD reach width (450–800 total) |

Community data independently describes the original third form as 271 frames per attack (9.03 s), respawn 4146 frames (~138.2 s), 72-frame foreswing, and the traits below.

## Original performance

No talents, Cat Combos or miscellaneous external battle modifiers are applied
to this table.

| Level | HP | Single attack damage | Base DPS |
|---:|---:|---:|---:|
| 30 | 55,250 | 31,450 | 3,482 |
| 40 | 71,500 | 40,700 | 4,506 |
| 50 | 87,750 | 49,950 | 5,530 |
| 60 | 104,000 | 59,200 | 6,554 |

Other original third-form parameters:

- KB: 4.
- Speed: 20.
- Standing range: 550.
- Long Distance Area: 450–800; enemies nearer than 450 are in the LD blind spot.
- Attack cycle: 271 frames / 9.03 s.
- Attack foreswing: 72 frames / 2.40 s.
- Recharge: 4146 frames / approximately 138 seconds.
- Cost: 4,350 in EoC Chapter 2 scaling.
- Primary attack: long-distance area; not an intrinsic multi-hit or an unlimited-range effect.

Original abilities:

- **超ダメージ** against Floating, Zombie, Relic/Ancient; x3–x4 according
  to applicable treasures, not unconditional x4 for all three categories.
- **100% Slow** against those same three attributes for 90 frames (=3 s)
  or 108 frames (=3.6 s) with corresponding treasures.
- **Zombie Killer**: prevents zombie revival on kill.
- **Witch Killer**: x5 Witch damage and x0.1 damage taken against Witches.
- **Curse Immune**: immunity to ancient/relic curse.
- Original third form has a distinctive death/disappearance animation. Keep it
  intact during Kneekura revisions.

### Second form / third form comparison (Lv.30)

| Metric | Second form (まどか＆ネコ) | Third form (Ultimate Madoka) |
|---|---:|---:|
| HP | 43,350 | 55,250 |
| Single attack | 28,050 | 31,450 |
| Base DPS | 3,463 | 3,482 |
| Attack cycle | 243f / 8.10s | 271f / 9.03s |
| Attack foreswing | 44f / 1.47s | 72f / 2.40s |
| Range | 550 / LD 450–800 | 550 / LD 450–800 |
| Target traits | Floating strong + 100% slow | Floating/Zombie/Ancient massive damage + 100% slow |

Conclusion: normal DPS barely changes while the attack cycle and foreswing
become slower. The improvement is chiefly in target coverage, resistances and
attribute-specific damage, not sustained damage against ordinary enemies.

## Balance-design diagnosis (not yet an update)

1. **2.40 s foreswing**: significant time to be interrupted before dealing damage.
2. **450–800 LD**: close-range blind spot for enemies that move inside 450;
   especially relevant to diving Zombies.
3. **9.03 s cycle**: confirmed 3–3.6-second Slow occupies only ~33–40%
   of one attack cycle before other modifiers.
4. **Base DPS only 3,482 at Lv30**: third-form DPS is nearly the same as
   second form despite the more elaborate third-form animation.
5. **No native talents** in this JP15.7.1 anchor: there is no official talent
   path to compensate for the above shortcomings.

Potential independent axes for the future **Kneekura Update** include shorter
foreswing, faster attack cycle, a narrower blind spot, longer Slow, additional
survivability/immunities, and selectively extended trait coverage. Every choice
needs gameplay/balance approval before implementation.

## Safe implementation boundaries

- Prefer preserving the original third-form graphics, frame timing surfaces,
  on-death special animation and untouched first/second forms.
- Do not overwrite original `DataLocal.list`/`DataLocal.pack` merely to change
  parameters: earlier original H01 integrity failures are recorded in
  `docs/research/failure-repair-history.md`.
- Investigate the smallest original-format `DownloadLocal` overlay or another
  explicitly validated data provider before changing any shipping APK.
- A proposed update, implemented patch and device-accepted update are separate
  states. Never mark a balance update 'released' until original-UI acceptance
  and persistence checks pass.
- Keep player SAVE_DATA and all unlocked progress untouched; a balance update
  should not require bootstrap or save deletion.
- Before any future user command, use the existing
  `tools/agent_terminal/verify.py` harness and its Windows PowerShell parser
  according to `AGENTS.md`. Physical-device checks remain `USER_GATE`.

## Public corroboration

- https://battlecats-db.com/unit/289.html
- https://wikiwiki.jp/bccharadata/鹿目まどか
- https://game8.jp/battlecats/666055

Community pages corroborate player-facing mechanics; this JP 15.7.1
DataLocal extraction is the numeric source anchor for the Kneekura build.
