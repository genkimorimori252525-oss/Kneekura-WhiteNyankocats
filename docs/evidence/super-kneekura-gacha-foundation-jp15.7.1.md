# Super Kneekura Gacha Foundation — exact JP 15.7.1

Status: data layer mapped; rarity-rate vector deliberately **not frozen yet**.

Machine-readable evidence:
`super-kneekura-gacha-foundation-jp15.7.1.json`.

## Exact local gacha tables

The verified JP 15.7.1 `DataLocal` pack contains:

- `GatyaDataSetR1.csv`
- `GatyaDataSetR2.csv`
- `GatyaDataSetR3.csv`
- `GatyaData_Option_SetR.tsv`
- `EventGatya_Setting.csv`
- `GatyaData_Option_ChanceAnimation.tsv`
- `unitbuy.csv`

Battle Cats Complete independently reconstructs the same structure:

- `GatyaDataSetR1/R2/R3` become three unit-list vectors per gacha set;
- `GatyaData_Option_SetR.tsv` supplies banner/ticket/animation/series metadata;
- `EventGatya_Setting.csv` is parsed as
  `gacha id -> repeated (group, unit, value)` triples.

That is strong evidence that a **data-first permanent gacha entry** is the right
first experiment. It is not evidence that we should invent a replacement gacha
screen.

## Exact unit rarity population

`unitbuy.csv` column 13 is the unit rarity field.

JP 15.7.1 has:

| Rarity | Rows |
| --- | ---: |
| Normal | 10 |
| Special | 208 |
| Rare | 194 |
| Super Rare | 105 |
| Uber Rare | 344 |
| Legend Rare | 21 |

Raw Rare-through-Legend population: **664 rows**.

This is only the raw compatibility search space. It is **not** the final Super
Kneekura pool.

The approved pool rule still applies:

1. original gacha acquisition/duplicate path must be safe;
2. explicit test/cheat units are excluded;
3. placeholders/unreleased/non-JP rows are not silently treated as real units;
4. Normal/Special/story-only units are added only after their nonstandard
   acquisition semantics are proven.

For example, exact row/unit ID 673 is user-facing unit 674,
**ネコチーター**, rarity Uber Rare. It is explicitly excluded.

## Rare gacha set structure

The exact R-family contains **1089** rows.

- R1 non-empty sets: 1088
- R1 maximum row population: 174 units
- R2 non-empty sets: 0
- R3 non-empty sets: 0
- option rows excluding header: 1089

So JP 15.7.1 currently expresses its rare-gacha unit membership primarily in
R1, with matching per-set option metadata.

This is useful for constructing a Kneekura set without changing the original
loader.

## Exact EventGatya_Setting.csv

The local table is only two rows:

```text
55,0,776,3
55,0,504,3
```

We record it exactly, but do not over-interpret its semantic meaning beyond the
BCC-confirmed `group/unit/value` structure.

## Important non-result: rarity probability is not proven here

`GatyaData_Option_ChanceAnimation.tsv` is **chance-animation metadata**.
Its weights are not accepted as Rare/Super Rare/Uber/Legend draw rates.

Likewise, a list of units in `GatyaDataSetR1.csv` does not by itself prove the
rarity probability vector used by a live Rare Capsule banner.

Therefore the project will **not** hard-code a remembered internet rate such as
"X% Rare, Y% Super Rare..." and call it exact.

The user approved "本家を参考". Under the preservation-first philosophy that
means:

> capture one exact original JP 15.7.1 Rare Capsule banner/event configuration
> or its runtime draw decision, then freeze that exact original vector with
> provenance.

Phase C network/event tracing is now the evidence gate for the rate vector.

## Super Kneekura first experiment

Once the original gacha scene is observed safely:

1. create a tiny test-only original-format rare gacha set;
2. keep the original gacha screen/capsule/result scene;
3. use only a few acquisition-safe units;
4. prove single and 11-draw transactions through the original acquisition path;
5. only then expand to the compatibility-filtered all-character pool;
6. freeze 150 / 1500 Cat Food using the already tested provider policy.

No full 664-row pool is injected before this small original-scene experiment
passes.

## Reproducibility

`tools/analyze_gacha_foundation.py` reproduces the local-table hashes, row
counts, rarity counts and unresolved-rate verdict from the owner's exact export.


## Local original R1 membership union

The exact local `GatyaDataSetR1.csv` rows contain **495 unique unit ids**.

Their rarity distribution is:

| Rarity | Unique ids present in local R1 sets |
| --- | ---: |
| Rare | 69 |
| Super Rare | 88 |
| Uber Rare | 320 |
| Legend Rare | 18 |

This is a much stronger starting point than simply taking every rarity 2–5 row
from `unitbuy.csv`.

Why:

- every one of these 495 ids is already referenced by at least one original
  JP 15.7.1 Rare Gacha data set;
- the original loader is therefore known to accept the id as R-set content;
- explicit cheat/test unit id 673 (ネコチーター) is **not** present in the
  local R1 union.

There are **169** Rare-through-Legend ids in `unitbuy.csv` that do not occur in
the local R1 union:

- Rare: 125
- Super Rare: 17
- Uber Rare: 24
- Legend Rare: 3

Those 169 are not automatically "unsafe"; many may be story/event rewards or
historical units whose relevant banner set is not present in the local install.
But their absence means the local R1 table alone cannot prove original Rare
Gacha membership.

### Approved seed-pool policy

The first Super Kneekura prototype should therefore begin from the exact
**495-id local R1 union**, then narrow further to a tiny observed-safe test pool.

Expansion beyond that union requires one of:

1. exact historical/server R-set evidence;
2. direct original acquisition/duplicate-path proof in Phase C.

Normal/Special/story-only units remain outside v1 until their nonstandard
acquisition semantics are proven.

This keeps "all characters" as the destination without using save corruption as
a shortcut.
