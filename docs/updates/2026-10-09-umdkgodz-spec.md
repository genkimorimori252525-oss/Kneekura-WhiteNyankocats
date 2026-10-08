# KNEEKURA Balance Update — UMDK-001 / GODZ-001 (2026-10-09)

Status: **targets recorded; no native gameplay update applied or released**. JP **15.7.1** only. Approved numerical requests must not be reinterpreted as an invitation to rebalance other abilities.

## Source receipts and safety

- User-owned JP 15.7.1 split_InstallPack.apk, DataLocal read-only AES extraction.
- unit289.csv SHA-256: e48bc212537fe7949c74527f0a8212874e8595fd9414f6d9bc2b7a1e3aee1a82.
- unit703.csv SHA-256: 8caeff21c1c02918da708d06095def423d05f9df14da63b741ac78994b57dbad.
- t_unit.csv SHA-256: d4fe8661e39a8f489e7549f03b5de4020acb6d7f8560438bdbb9490ec2f8cb04.
- No extracted proprietary CSV, .pack/.list, original APK, save or third-party sprites may be committed. **The repository API reported this repository PUBLIC on 2026-10-09.**
- Preserve all current Post-EoC SAVE_DATA, upgrades, owned units, story/event progress, the original game UI, and original application scene/animation behavior.

## UMDK-001 — Ultimate Madoka, approved target

Identity: public cat No.289, asset/save ID 288, DataLocal/unit289.csv form index **2** only.

| Lv30/reference item | Original | Approved target |
|---|---:|---:|
| HP | 55,250 | unchanged |
| Attack (no traits) | 31,450 | **28,000** |
| Standing/sensing range | 550 | **750** |
| Long-distance damage range | 450–800 | unchanged |
| Attack cycle | 271f / 9.03s | unchanged |
| Attack foreswing | 72f / 2.40s | unchanged |
| Speed / KB | 20 / 4 | unchanged |
| Deploy cost, EoC Chapter 2 basis | 4,350 | **4,550** |
| Recharge | ~138.2s (4146f) | **155s (4650f)** |

Unchanged: Floating/Zombie/Relic Massive Damage and 100% Slow, Zombie Killer, Witch Killer, Curse Immunity; first/second forms and unique death/disappearance animation. A range 750 standing position with LD minimum 450 keeps the near blind spot by design; only the tendency to approach too closely is addressed.

### Exact native representation gate

Observed original CSV row (zero-based columns): HP 0=3250, attack 3=1850, standing 5=550, raw cost 6=2900, recharge 7=2200, LD min 44=450, LD width 45=350. Independent current data corroborates Lv30 attack = raw attack *17 and EoC Ch2 cost = raw cost *3/2.

- Range 750 is directly representable in column 5.
- Under the reference research/treasure configuration, original recharge 2*2200-254=4146f. Target 4650f maps to raw recharge **2452**. Validate this mapping in the native scene before shipping.
- **28,000 Lv30 attack cannot equal 17 × an integer raw damage** with otherwise unchanged growth: raw 1647 gives 27,999; raw 1648 gives 28,016. The approved **28,000** is not silently replaced with either.
- **4,550 Chapter 2 cost cannot equal integer raw cost × 1.5 before UI rounding**: raw 3033 gives 4549.5; raw 3034 gives 4551. Determine actual runtime rounding or use a narrowly validated hook before claiming UI displays exactly 4,550.
- Do not edit shared growth tables or the first/second form to hide this precision issue.

## GODZ-001 — Enemy-inspired playable Godzilla first form

**Clarify native names rather than conflating IDs**:

- Enemy No.552 is called ゴジラ in JP catalog; equivalent English description is Shin Godzilla. Exact source is DataLocal/t_unit.csv **row 552** (no enemy552.csv).
- Playable cat No.703 first form (form index 0, asset/save ID702) is **ゴジラにゃんこ**. Original **second form** is named **シン・ゴジラにゃんこ**. Owner requested the **first form** only; leave second/other forms untouched.
- Original No.703 first form Lv30: 5,440 HP; 8,160 total 3-hit attack; range 310; cost 660; recharge about 9.5s (public sources vary with treasure/research baseline).
- User-approved playable replacement production parameters: **cost 9,800** (EoC Ch2) and **recharge 500s**. Under the same reference mapping, recharge 15,000f suggests raw 7627, pending native verification; raw cost 9800/1.5 is fractional, hence exact UI rounding remains a gate.

### Exact enemy basic stats (100% strength)

| Enemy property | No.552 |
|---|---|
| HP | 500 |
| Total attack | 600, three hits of 200 each |
| Sense / effective long-distance range | 3800 / 2300–3800 |
| Attack period | 425f / 14.17s |
| Hits | 130f, 170f, 210f |
| Movement / KB | 3 / 1 |
| Attack targeting | Area |
| Base Destroyer | x4 against enemy castle |
| Immunities | Knockback, Freeze, Slow, Weaken |
| Attribute | Enemy traitless; not a transferable playable-cat trait |

**Enemy stage magnification is external; 500 HP / 600 total attack is not the high-boss encounter.**

| Named encounter | HP multiplier | Attack multiplier | Actual HP | Actual total hit damage |
|---|---:|---:|---:|---:|
| 謎の巨大生物現る | 100% | 30% | 500 | 180 |
| 災害対策本部設置 | 8,000% | 200,000% | 40,000 | 1,200,000 |
| ネコによる最終決戦 | 18,600% | 5,000% | 93,000 | 30,000 |
| 最強の破壊神 | 26,000% | 200,000% | 130,000 | 1,200,000 |

The owner has **not** selected a stage's HP/attack magnification, which would be a massive difference in the playable version. Do not fabricate a choice; cost and recharge are approved, not HP/attack. Enemy-specific attributes and castle multiplier require independent player-unit field semantics and collision/targeting testing, not raw CSV column copying.

### Appearance and animation

The attached owner-cropped Shin Godzilla face image is the **approved visual reference**, but must not be committed to this public Git repository. It is a still image, not a complete native Battle Cats sprite atlas/model/animation set. Preserve the user's selected composition in local-only art work; confirm enemy sprite/mamodel/maanim assets and playable side hit/event/move/KB/death compatibility separately before claiming an animated first form exists.

## Release implementation boundary

1. Build reproducible player-form-specific **candidate** overrides from locally owned data only; pin base SHA and fail closed if it differs. The JSON alongside this document is a versioned intent contract, **not a patch**.
2. H01 was observed after rewriting built-in DataLocal packs. Prefer an exact DataLocal-preserving DownloadLocal override or narrowly verified provider; do not quietly disable MD5 or rewrite all APK packs.
3. Static before/after compare: only Madoka form 2, Godzilla form 0 and explicitly approved companion visuals may change. No stages, existing enemy #552, unit ownership, levels, progression, SAVE_DATA, gacha, other forms, or original animations.
4. Run tools/agent_terminal/verify.py and Windows PowerShell syntax validation before handing device commands to the owner. Never mark local CI as device PASS.
5. Device acceptance (USER_GATE): backup current save, original game launches without H01, unit pages show expected fields, native battles demonstrate attack/LD target alignment, cropped Godzilla art animates correctly if desired, offline restart persists, and exact rollback succeeds.
6. Only after original UI + device validation may the update be tagged **RELEASED**. At present **not implemented / not shipped**.

Public cross-references:
- https://battlecats-db.com/enemy/552.html
- https://battlecats-db.com/unit/313.html/703.html
- https://wikiwiki.jp/bccharadata/鹿目まどか
- https://battle-cats.fandom.com/wiki/Shin_Godzilla_(Enemy)
- https://github.com/dukart913/Battle-Cats-Game-Modder (H01 risk corroboration only)