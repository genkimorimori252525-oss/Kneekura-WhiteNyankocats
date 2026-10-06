# Foundation evidence

This directory records evidence about the locally owned Android export without committing game assets.

Current known source:

- Repository release: `Android export: Nyanko Battle Cats (2026-10-06)`
- Release ID: `404291917`
- Release state: draft
- Asset: `nyanko_battlecats_2026-10-06.zip`
- Asset ID: `614397353`
- Size: `156585000` bytes
- SHA-256: `38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56`
- Export note: installed split APKs plus app-owned shared-storage data were copied from the connected Android device.
- Private app data under `/data/user/0/jp.co.ponos.battlecats` was not available through standard ADB permissions.

## Evidence rule

Do not infer a file format or game role from a filename alone. Record raw path/size/hash evidence first, then promote an interpretation only after parser, code, or behavior evidence supports it.

Game assets, APKs, extracted textures/audio, and `.pack/.list` payloads stay outside Git.
