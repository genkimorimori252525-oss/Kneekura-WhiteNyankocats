# Android Export Foundation Map — JP 15.7.1

Evidence date: 2026-10-06  
Source: user-owned Android export attached to the project/chat.  
Policy: read-only analysis. No APK, decrypted asset payload, image, audio, or pack body is committed to this repository.

## 1. Source identity

- Package: `jp.co.ponos.battlecats`
- Export-declared version: `15.7.1`
- Export ZIP: `nyanko_battlecats_2026-10-06.zip`
- Size: `156,585,000` bytes
- SHA-256: `38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56`
- The digest exactly matches the private Draft Release asset metadata.

The outer ZIP contains 22 files under:

- `apk/`
- `shared/`
- `manifest.csv`
- `README.md`

The embedded README records that standard ADB could not read `/data/user/0/jp.co.ponos.battlecats` because the package is not debuggable. Therefore this export does **not** contain the app-private downloaded-data/save area.

## 2. Installed APK split set

| APK | Size | Role observed from contents |
| --- | ---: | --- |
| `base.apk` | 25,913,924 | Android/Java layer, 5 DEX files including audience-network DEX, SDK resources |
| `split_config.arm64_v8a.apk` | 15,369,082 | 9 ARM64 native libraries, including the 11.6 MB game `libnative-lib.so` |
| `split_config.en.apk` | 49,362 | language resources |
| `split_config.ja.apk` | 24,786 | Japanese language resources |
| `split_config.xxhdpi.apk` | 239,918 | Android drawable/resources split |
| `split_InstallPack.apk` | 132,290,560 | 199 `assets/` entries containing the Battle Cats local pack set |

`shared/` in this export is overwhelmingly Unity Ads/Vungle cache. No Battle Cats content pack was found there.

## 3. InstallPack local pack families

The encrypted `.list` manifests were successfully decoded and parsed as `name,offset,size` tables. The counts below are from the actual JP 15.7.1 export.

| Family | Entries | Pack size | Main observed payload |
| --- | ---: | ---: | --- |
| `DataLocal` | 8,955 | 8,771,248 | 8,733 CSV, 182 JSON, 30 TSV, 10 preset |
| `DownloadLocal` | 6 | 9,904 | PNG + imgcut + mamodel + maanim |
| `HtmlLocal` | 0 | 0 | empty |
| `ImageDataLocal` | 8,725 | 18,760,304 | 6,240 imgcut, 1,814 maanim, 671 mamodel |
| `ImageLocal` | 583 | 37,510,976 | 583 PNG |
| `MapLocal` | 608 | 22,832,048 | 608 PNG |
| `NumberLocal` | 166 | 9,246,688 | 166 PNG |
| `UnitLocal` | 159 | 1,133,008 | 159 PNG |
| `resLocal` | 1,158 | 2,097,328 | 982 CSV, 176 TSV |

### Interpretation

- `DataLocal` is the highest-priority gameplay/config source.
- `resLocal` is the highest-priority Japanese localization/name/description source.
- `ImageDataLocal` is the highest-priority model/animation metadata source.
- `ImageLocal`, `NumberLocal`, and `UnitLocal` hold texture/icon subsets.
- `MapLocal` is strongly map/stage-image oriented.

The repository importer must treat these names as evidence-backed roles, but individual files still require parser/behavior evidence before semantic field names are frozen.

## 4. Character catalog is locally present

`DataLocal` contains exactly:

- `unit001.csv`
- ...
- `unit882.csv`

There are **882 consecutive unit definition files with no gaps**.

`resLocal` contains exactly:

- `Unit_Explanation1_ja.csv`
- ...
- `Unit_Explanation882_ja.csv`

There are also **882 consecutive Japanese unit explanation/name files**, and the ID set matches the unit-definition set exactly.

This means JP 15.7.1's installed local data contains the complete 1–882 unit-definition/name catalog even when a unit is not currently obtainable.

Verified examples from the local data include historical collaborations such as:

- Madoka Magica: unit 289 (`鹿目まどか`), 290 (`暁美ほむら`), etc.
- Fate: unit 363 (`セイバー`) and related units.
- Evangelion: units 403–415 plus later additions such as 488, 552, 704, 711, 815.
- Hatsune Miku: unit 536 (`初音ミク`) plus later variants.
- Street Fighter: unit 511+ family.
- Ranma 1/2: unit 597+ family.
- Godzilla-related units are also present.

This evidence supports automatic catalog import. It does **not** by itself prove that every historical unit's complete texture/animation payload is bundled in `split_InstallPack.apk`.

## 5. Example decoded gameplay/localization evidence

`unit001.csv` decodes to three stat rows, with the first row commented `ネコ`.

`Unit_Explanation1_ja.csv` resolves the three forms:

- ネコ
- ネコビルダー
- ネコモヒカン

`Unit_Explanation401_ja.csv` resolves unit 401 as the `イモウト` collaboration unit.

`Enemyname.tsv` resolves the enemy-name table beginning with `わんこ`, `にょろ`, `例のヤツ`, etc.

For importer design, numeric `unitNNN.csv` columns remain **raw indexed fields** until their semantics are independently mapped and tested. Do not prematurely name columns from memory.

## 5.1 Catalog parser constraints observed across all 882 units

A full read-only pass over all 882 `unitNNN.csv` files produced these form-row shapes:

- 832 units: 3 stat rows / 3 text rows
- 24 units: 1 stat row / 1 text row
- 23 units: 4 stat rows / 4 text rows
- 3 units: 2 stat rows / 3 text rows

The three form-count mismatches are unit IDs `737`, `739`, and `816`. Their third localized text row duplicates an earlier form name while no third stat row exists. The importer therefore keeps text forms and stat forms independently rather than assuming a strict 1:1 row count.

Observed stat-row field counts are not fixed. Across the current data they range from 52 to 119 fields, with many intermediate layouts. Two observed rows also contain an empty field. Therefore:

1. raw stat fields are preserved positionally;
2. empty fields become explicit nulls rather than shifting columns;
3. parsers must not reject a row merely because it is shorter/longer than another unit;
4. typed semantic views are layered on top only after each column/version relationship is evidenced.

This is now a hard importer contract.

## 6. Animation/model format evidence

Representative `ImageDataLocal` chunks are directly readable text structures:

- `.imgcut` starts with `[imgcut]`
- `.mamodel` starts with `[modelanim:model]`
- `.maanim` starts with `[modelanim:animation]`

This makes a first-party animation parser practical without requiring image OCR or video reconstruction.

Observed direct-name animation families include patterns such as:

- `401_u.imgcut`, `401_u.mamodel`, `401_u00.maanim`...
- `723_s...`
- recent `831_c...` / `831_f...`
- enemy-like `750_e...` families

The meaning of suffixes `u/s/c/f/e` must be derived from source/runtime behavior before becoming schema names.

## 7. Texture/UI evidence

Decoded PNG validation succeeds for entries from `ImageLocal`, `NumberLocal`, `UnitLocal`, and `MapLocal`.

Representative UI/content evidence:

- many backgrounds are width 770 pixels
- gacha banners are commonly 860×240
- gacha button strips are commonly 225×54
- enemy icons observed are 64×64
- `gatya_UI_1.png` is 1024×604
- map-name images are commonly 256×64

These dimensions are asset dimensions only. They do **not** establish the game's logical screen/canvas size.

## 8. Native runtime evidence

ARM64 `libnative-lib.so` exports JNI entry points including:

- `MyActivity_appUpdateDraw`
- `MyActivity_gfxInit`
- `MyActivity_gfxResize`
- `MyActivity_getDrawableWidth/Height`
- `MyActivity_getWindowWidth/Height`
- `MyActivity_getSizeWidth/Height`
- `MyActivity_appTouch`
- `MyActivity_appKey`

Disassembly of `appUpdateDraw` shows:

- use of `steady_clock::now`
- nanosecond delta converted to seconds
- OpenGL viewport query
- update/draw calls afterward

Therefore render/update timing currently appears to receive real elapsed time. This does **not** yet prove whether battle simulation itself uses a fixed or variable internal tick.

Disassembly of `appTouch` shows distinct paths for action values 0, 1, and 2, and the move path tracks previous pointer coordinates to derive delta. This supports the planned platform-input → logical-touch adapter.

## 9. Important correction: APK vs downloaded server packs

The native game library explicitly contains many server-pack family names, including paired `.list/.pack` names for letter-sharded families such as:

- `AUnitServer.pack` ... `VUnitServer.pack`, `XUnitServer.pack`
- `ImageServer.pack` and letter-sharded `CImageServer...` through later families
- `ANumberServer...` through later families
- `MapServer...` and letter-sharded map families

Direct-name searches inside the bundled `ImageDataLocal` do not show obvious unit animation families for some historical collaboration IDs whose definitions/names definitely exist locally (for example several older Madoka/Fate/Miku/Ranma IDs).

Current evidence therefore supports this model:

```text
Installed APK / InstallPack
  ├─ complete or near-complete gameplay definitions + localization catalog
  ├─ common/core assets
  ├─ some current/recent content assets
  └─ server-pack naming/routing logic in native code

App-private downloaded data (not captured)
  └─ likely additional Unit/Image/Number/Map Server pack shards
     needed for already-downloaded historical/event content
```

This explains how an already-downloaded collaboration unit can remain usable offline without requiring every historical visual asset to live inside the base APK.

**Do not claim full visual-asset completeness until the app-private server-pack cache is inventoried or another complete local source is provided.**

## 9.1 External JP server archive recovery evidence

The standard-ADB export does not contain the app-private downloaded server cache, but a public historical BCData archive contains the same JP server-pack families referenced by the 15.7.1 native library.

The archived `jp_server` tree contains 174 Unit/Image/Number/Map server list/pack files (87 pairs), including A–V shards plus base server families. It also contains:

- `WImageDataServer.list`
- `WImageDataServer.pack`

The latter is the missing animation/model-data tier.

A read-only manifest scan of those public `.list` files found 32,882 archived asset entries. Historical collaboration units that were not obvious in the bundled InstallPack are explicitly present in the archive.

Verified examples:

- unit 289 (Madoka): `gatyachara_289_f.png`, `uni289_c00.png`, `289_c.imgcut`, `289_c.mamodel`, `289_c00.maanim` and additional form/enemy animations
- unit 290 (Homura): corresponding PNG/imgcut/mamodel/maanim families
- unit 363 (Saber / Fate): corresponding PNG/imgcut/mamodel/maanim families
- Evangelion unit family 403–415: corresponding PNG/imgcut/mamodel/maanim families
- unit 488: corresponding PNG/imgcut/mamodel/maanim families
- unit 511 (Street Fighter family): corresponding PNG/imgcut/mamodel/maanim families
- unit 536 (Hatsune Miku): corresponding PNG/imgcut/mamodel/maanim families
- unit 552: corresponding PNG/imgcut/mamodel/maanim families
- unit 597 (Ranma family): corresponding PNG/imgcut/mamodel/maanim families
- unit 704 and 711: corresponding PNG/imgcut/mamodel/maanim families

This materially changes the recovery assessment: older collaboration visuals and animation metadata are not lost merely because they are absent from the current InstallPack.

One tested recent ID, 815, was not present in this older public archive. That does **not** establish that the asset is unavailable: the current 15.7.1 native library also references newer `XUnitServer`, `XImageServer`, `XNumberServer`, `XMapServer` families that are newer than the archived A–V snapshot.

The next completeness task is therefore not device-root extraction. It is:

1. derive the current server-file manifest/version routing from the user's own 15.7.1 APK;
2. obtain the current server-file set through the same download path used by the game/tooling;
3. merge current server assets with the historical archive;
4. compute per-unit completeness across definitions, texture sprites, icons, imgcut, mamodel, and maanim;
5. only declare the project blocked if units still lack required assets after both sources are exhausted.

## 10. Importer priority order

### P0 — Catalog importer

Immediately implementable from this export:

1. `DataLocal.list/.pack`
2. `resLocal.list/.pack`
3. join `unitNNN.csv` ↔ `Unit_ExplanationN_ja.csv`
4. preserve numeric columns as raw indexed values
5. emit normalized unit identity/forms/names plus raw stat records

Expected coverage: 882/882 units for identity and definition data.

### P1 — Animation metadata

Parse:

- imgcut
- mamodel
- maanim

Build a renderer-independent animation document model.

### P2 — Texture resolver

Resolve matching PNGs across:

- ImageLocal
- NumberLocal
- UnitLocal
- MapLocal where relevant
- future Server pack sources

The resolver must tolerate missing asset families and record provenance.

### P3 — Enemy/stage import

Use:

- `Enemyname.tsv`
- enemy-related DataLocal tables
- MapData / MapStageData families
- MapLocal imagery

### P4 — Original-compatible UI/runtime behavior

Use:

- UI PNG/imgcut/model/animation assets
- native JNI/runtime evidence
- measured screen transitions/touch regions
- no guessed logical resolution

## 11. Foundation rule

Every imported record carries provenance:

```text
source export digest
APK split
pack family
manifest entry
offset
length
decryption mode
payload digest
parser version
```

This allows future Battle Cats updates to be diffed without mutating or redistributing the original content.
