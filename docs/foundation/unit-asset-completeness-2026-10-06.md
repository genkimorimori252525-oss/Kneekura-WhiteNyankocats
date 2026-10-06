# Unit Asset Completeness Gate — 2026-10-06

Status: **real-data audit completed; strict catalog gate = 879 / 882, with all three residual slots explained.**

## Inputs fixed for this audit

- JP 15.7.1 Android export: `156,585,000` bytes.
- Export SHA-256: `38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56`.
- Local InstallPack catalog: 882 consecutive `unitNNN.csv` definitions and 882 matching Japanese explanation/name files.
- Historical public JP server manifests from BCData.
- Live current X-lane manifests fetched by Actions run `37417655457`.
- Current merged server index: **93 manifests / 33,780 filename entries**.
- X-lane fetch: HTTP 206, **15,366,935 bytes**, matching the lane-34 download table.

No APK, pack body, texture, model, or animation payload is committed to Git. The audit consumes only the user-owned local export plus filename/provenance metadata.

## Important contract correction

The first audit treated every stat row as a real visual form. That produced a false result of only 442 / 882 complete units because many unit CSVs contain trailing placeholder stat rows even when no corresponding True/Ultra form exists.

Public TBCML source independently identifies the relevant `unitbuy.csv` columns:

- position/order: column 14;
- second-form unlock level: column 21;
- True Form id: column 23;
- Ultra Form id: column 24;
- egg fields: columns 61 and 62.

The corrected visual gate therefore uses:

- one stat row -> one visual form;
- otherwise Normal `f` + Evolved `c` as the playable baseline;
- `tf_id > 0` adds True `s`;
- `uf_id > 0` adds Ultra `u`;
- internal/non-roster rows keep all stat-backed forms;
- catalog number is one-based while the visual stem is zero-based: `asset_id = unit_no - 1`.

This rule is implemented in `tools/audit_unit_assets.py` and covered by regression tests.

## Real JP 15.7.1 result

After applying the corrected form-presence rule to the verified export plus the historical/current manifest union:

- catalog units: **882**
- playable/order-bearing rows: **859**
- strict complete units: **879**
- strict incomplete units: **3**
- required visual forms: **2,178**
- complete visual forms: **2,173**
- incomplete visual forms: **5**
- missing battle PNGs: **5**
- missing `.imgcut`: **5**
- missing `.mamodel`: **5**
- missing deploy icons: **5**
- missing required `.maanim` tracks: **20**

Every ordinary unit outside the three residual cases has the required battle sheet, cut/model metadata, baseline animation tracks, and deploy icon in the union of InstallPack + historical server manifests + current X manifests.

## The only three residual catalog slots

### Catalog unit 674 / asset 673 — ネコチーター

The first form `673_f` is complete. The strict generic baseline asks for a second `673_c` form, but no such assets exist.

This is expected game semantics rather than an unexplained archive hole: Cheetah Cat is an unobtainable/cheat-only unit and is documented as having **no evolution** / only one real form. Its existing first-form visual set is therefore accounted for.

Strict missing set:

- `673_c.png`
- `673_c.imgcut`
- `673_c.mamodel`
- `673_c00.maanim` .. `673_c03.maanim`
- `uni673_c00.png`

### Catalog unit 741 / asset 740 — `741-1`

JP localization data itself uses placeholder names (`741-1`, `741-2`, etc.). Public cross-region records identify this numeric slot with content that exists outside the normal JP release line, while the JP script remains placeholder text.

Both strict `740_f` and `740_c` visual sets are absent from the JP corpus. This is therefore a **JP placeholder / regional-content slot**, not evidence that a normal JP cat asset was lost.

### Catalog unit 789 / asset 788 — `789-1`

The JP roster likewise exposes the placeholder-style `789-1` / `789-2` naming, and the ordinary JP database sequence jumps from the real unit at 788 to the Baki collaboration at 790.

Both strict `788_f` and `788_c` visual sets are absent from the JP corpus. Public cross-region data shows this slot has content in another localization, so it is treated as a **regional placeholder in JP**, not an unexplained missing JP download.

## Collaboration and late-ID coverage

The merged manifests cover the historical collaboration families that originally looked lost, including the Madoka Magica, Fate, Evangelion, Street Fighter, Hatsune Miku, and Ranma-era units.

Corrected examples:

- 鹿目まどか: catalog 289 -> asset 288.
- 暁美ほむら: catalog 290 -> asset 289.
- セイバー: catalog 363 -> asset 362.
- Evangelion catalog 403–415 -> assets 402–414.
- Street Fighter catalog 511 -> asset 510.
- 初音ミク catalog 536 -> asset 535.
- Ranma catalog 597 -> asset 596.
- catalog 815 -> asset 814, with current-X filenames present.

The earlier fear that old collaboration art was absent because it was not in the installed APK is therefore resolved: those assets are represented by the historical downloaded-server families, while newer assets are supplemented by the current X lane.

## Gate decision

Two statements must remain distinct:

1. **Raw strict catalog gate:** `879 / 882` — intentionally false because it does not special-case region placeholders or Cheetah Cat's one-form design.
2. **JP reconstruction assessment:** **GO** — there are no unexplained missing visual/animation sets among ordinary JP units. The three residual rows are explainable nonstandard slots: one documented single-form cheat unit and two JP regional/placeholder slots.

Do not rewrite the strict number as `882 / 882 COMPLETE`. If the project later chooses to import non-JP regional exclusives too, that is a separate cross-region acquisition scope.

Original APKs, pack bodies, textures, animation payloads, and downloaded proprietary assets remain outside Git.
