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

## Access attempts

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

## Current conclusion

The release metadata and expected digest are confirmed. **The asset bytes have not yet been inspected in this session.**

Therefore none of the following are currently claimed as fact:

- exact split APK filenames/count
- exact `.pack/.list` locations
- exact character/animation/UI asset presence
- whether every historical collaboration asset is present

The local inventory tool is the next evidence-producing step once the ZIP bytes are available to a local process or another supported binary-access path.
