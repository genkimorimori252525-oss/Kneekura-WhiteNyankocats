# Phase C H01 Integrity Gate — JP 15.7.1

Status: **root cause narrowed; preservation-first remediation implemented.**

## Owner-device observation

The first set-1089 research build completed the original 615.69 MiB server
bootstrap and then immediately stopped at the original **H01 data-read/loading
error** screen.

That build had one important property:

- it rewrote `assets/DataLocal.list` and `assets/DataLocal.pack` in
  `split_InstallPack.apk` to append the test gacha set.

The network/bootstrap path itself had completed before H01 appeared.

## External corroboration

Historical Battle Cats modding tooling independently documents H01 as a
`.pack` / `.list` integrity failure:

- repository: `dukart913/Battle-Cats-Game-Modder`
- the README states that removing the libnative MD5 check for `.pack` and
  `.list` files avoids **Data Read Error H01**;
- the same guide says modified downloaded server packs must also have their
  matching `download.tsv` size/hash metadata updated.

This is corroboration, not the authority for JP 15.7.1.

A newer independent implementation, **Battle Cats Complete** commit
`5a5096c8fa75f837d3e9a314e8fd4ce4813ec811`, uses a different preservation
strategy for APK mods:

- packed mod files are emitted into `DownloadLocal.pack/.list`;
- built-in game-data containers are not rewritten for each modded file.

That behavior is implemented in:

`kore/src/domains/mods/export/apk.rs`

where packed mod contents are sent to the `DownloadLocal` family.

## Project interpretation

The evidence is sufficient to stop using direct DataLocal rewrites for the
set-1089 runtime proof.

The project deliberately **does not** adopt the historical native MD5-bypass
patch. Bypassing the integrity check would widen the native mutation surface and
would hide accidental pack corruption.

Instead the proof now follows the original overlay model:

```text
exact DataLocal.list/.pack
        |
        | byte-identical
        v
original loader
        ^
        |
DownloadLocal overlay adds only:
  GatyaDataSetR1.csv
  GatyaDataSetR2.csv
  GatyaDataSetR3.csv
  GatyaData_Option_SetR.tsv
```

## New hard gates

The H01-safe proof requires:

- exact source `DataLocal.list` unchanged byte-for-byte;
- exact source `DataLocal.pack` unchanged byte-for-byte;
- existing six DownloadLocal entries preserved;
- exactly four gacha override files appended to DownloadLocal;
- each override equals the exact original table plus only set 1089;
- no native MD5/checksum bypass;
- no original gacha/capsule/result scene replacement.

The existing downloaded server cache is preserved across same-signature
`adb install -r`, so the owner should not need another 615.69 MiB bootstrap
unless the original game itself decides the cache is incomplete.

## Next device question

After installing the H01-safe overlay build over the existing research package:

1. confirm H01 no longer appears;
2. confirm the normal original UI is reached;
3. open the normal Rare Gacha scene;
4. do not draw yet;
5. observe whether set 1089 is exposed.

Only after step 3 is reached can banner scheduling be evaluated.
