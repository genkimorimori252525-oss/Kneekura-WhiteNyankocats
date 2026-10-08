# Draft Release access evidence — 2026-10-06

## Confirmed metadata

- Release: `Android export: Nyanko Battle Cats (2026-10-06)`
- Release ID: `404291917`
- State: draft
- Asset: `nyanko_battlecats_2026-10-06.zip`
- Asset ID: `614397353`
- Size: `156585000` bytes
- SHA-256 declared by GitHub: `38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56`

Release notes say the export contains installed split APKs and the app-owned shared-storage folder copied from the Android device. Standard ADB did not obtain `/data/user/0/jp.co.ponos.battlecats`.

## GitHub integration access attempts

### GitHub Actions run 37411794202

A workflow with `contents: read` attempted the release asset endpoint with the workflow's `GITHUB_TOKEN`.

Result:

- HTTP 403 before the ZIP was downloaded.
- Inventory code did not execute.

### GitHub Actions run 37411906997

A second workflow used `gh api` with the same repository-scoped workflow token.

Result:

- `Resource not accessible by integration (HTTP 403)`
- No asset bytes were obtained.

### Connected GitHub fetch path

The draft release metadata is readable, but the private draft asset's browser-download URL is not exposed as a fetchable binary through the connector path used here.

These failures describe the GitHub integration boundary only. They do not indicate that the release asset is corrupt or inaccessible to the repository owner.

## Resolution for analysis

The same-named export ZIP was later attached directly to the project/chat and became available to the local analysis runtime.

Direct verification of that attached copy produced:

- Size: `156585000` bytes
- SHA-256: `38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56`

Both values exactly match the Draft Release metadata above. The attached copy is therefore treated as the verified analysis source for this foundation pass.

The actual bytes have now been inspected read-only. Confirmed findings include:

- six installed APK splits, including `split_InstallPack.apk`
- the local `.list/.pack` families and their manifest entry counts
- 882 consecutive `unitNNN.csv` definitions
- 882 matching Japanese `Unit_ExplanationN_ja.csv` entries
- local imgcut/mamodel/maanim structures
- native evidence for additional downloaded `*Server.pack` families

The detailed evidence and current interpretation live in:

- `docs/foundation/android-export-15.7.1.md`

## Remaining boundary

The export still does not contain the app-private directory `/data/user/0/jp.co.ponos.battlecats`.

Accordingly, this analysis does **not** claim that `split_InstallPack.apk` alone contains every historical collaboration texture/animation. Native evidence indicates additional downloaded Unit/Image/Number/Map server-pack shards, and those may account for historical content that remains usable offline after it has been downloaded.

This distinction must remain explicit in future importer and asset-resolver work.
