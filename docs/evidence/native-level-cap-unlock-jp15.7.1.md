# Native Level-Cap Unlock — JP 15.7.1 static proof

Status: additive SAVE migration foundation complete; device application pending.

## Goal

Allow the current Kneekura Post-EoC profile to raise supported units to their
official JP 15.7.1 native level cap **without clearing New/Uncanny Legend
progress** and without resetting the player's current save.

This is not an "all cats become level 60" patch.

The exact `unitbuy.csv` hard caps are preserved:

- 323 eligible units have native cap **60**;
- 493 eligible units have native cap **50**;
- 11 eligible units have native cap **20**;
- 8 eligible units have native cap **1**.

So Madoka 289, Homura 290, Saber 363 and Hatsune Miku 536 can reach level 60,
while units whose official JP15.7.1 data hard-caps at 50 remain at 50.

## SAVE_DATA field

One independently mapped JP15.7.1 section stores each Cat's unlocked upgrade
cap increment:

- i32 count at offset **306,330** = 882;
- records start at **306,334**;
- 882 records;
- each record is four bytes: `u16 plus_increment, u16 base_increment`.

The same count/offset remains valid in the observed 507,164-byte original-game
runtime rewrite, because the known variable-length growth occurs later in the
save.

## Cap formula

The research parser computes the effective base-level cap from the unit's
official data plus the saved cap increment and clamps it to the unit's official
Catseye hard max.

Kneekura therefore applies:

```text
desired = min(60, unitbuy.native_catseye_hard_max)
required_increment = max(0, desired - unitbuy.original_base_max)
stored_base_increment = max(existing, required_increment)
```

The `max(existing, ...)` rule makes the migration monotonic: an already higher
player cap is never lowered.

## Exact clean-baseline differential

Source clean save:

`66ba4d8825cf270cca92c031141d19ea940d480a89113f3fe4602c3f3be4ebf3`

After applying only this migration:

- output SHA-256:
  `132f31ecc8baf330b54473d07bd31047bd7c0ac2d360e2799fe1ccdf264aaf35`;
- JP salted-MD5:
  `91878a897f41b3fb66828c0d6fb87868`;
- 816 of the 835 eligible records changed from the clean zero-cap state;
- every non-hash byte difference is inside the max-upgrade record section.

The other 19 eligible units already have a native cap equal to their original
base cap (1 or 20), so no cap increment is needed.

## Preservation boundary

The migration deliberately does **not** change:

- current Cat levels;
- Cat ownership;
- forms/talents;
- Stories of Legend / Uncanny Legend / Zero Legend progression;
- event progression;
- stage-reward claim flags;
- Catseye-consumption history;
- plus-level cap increment.

This is exactly the non-destructive update model intended for Kneekura:
unlock the requested convenience feature without falsifying unrelated story
progress.
