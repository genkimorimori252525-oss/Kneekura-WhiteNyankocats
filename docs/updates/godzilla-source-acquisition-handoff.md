# GODZILLA #14 — JP15.7.1 Server file handoff (2026-10-10)

**First read [CURRENT.md](../../CURRENT.md).** This is a Godzilla task handoff, not a new roadmap.

## Actual owner acquisition result

The owner downloaded the four files from the public historical [fieryhenry/BCData jp_server](https://github.com/fieryhenry/BCData/tree/main/jp_server) mirror, and the owner-side tool reported **4/4 exact byte count + original JP15.7.1 download-table MD5 matches**. Official historical CDN probes failed with HTTP 403. The owner-local files have not been independently inspected by another agent.

| Source file | Original bytes | Original MD5 |
|---|---:|---|
| MNumberServer.list | 2,832 | 34219ad4ddebe715ddaa3af4244697b1 |
| MNumberServer.pack | 10,637,344 | 0c23c4defa077d2e97fbbb1b28a0de4d |
| WImageDataServer.list | 451,888 | 1ddee28c515a52ebd0a09d655745945c |
| WImageDataServer.pack | 79,788,272 | cebd0898a2c9d68fa3c7631afa9dd0d2 |

**Original pack/list/art bytes must NEVER enter GitHub, PR attachments, or CI artifacts.** This repository is public; existing .gitignore excludes all .pack, .list and private/ paths. Only scripts, metadata, documentation and tests are committed.

## Acquire private files inside the implementation workspace

From the repository root, prefer reusing the owner's existing local cache if Codex runs on the owner's Windows PC:

~~~powershell
$owned = Join-Path $env:USERPROFILE 'Downloads\kneekura-server-recovery-jp1571\kneekura_server_recovery\server_archive_cache\files'
py -3 -m tools.base_mod.fetch_godzilla_server_assets --from-dir "$owned"
~~~

Otherwise, on an environment where access to the public historical mirror is permitted:

~~~powershell
py -3 -m tools.base_mod.fetch_godzilla_server_assets --download
~~~

Both modes check exact original MD5 and file sizes, with an independent SHA256 receipt. Output is always owner/private local storage:

~~~text
private/server-jp1571/godzilla/
  MNumberServer.list
  MNumberServer.pack
  WImageDataServer.list
  WImageDataServer.pack
  godzilla-server-source-receipt.json
~~~

Offline revalidation and tests:

~~~powershell
py -3 -m tools.base_mod.fetch_godzilla_server_assets --verify-only
py -3 -m unittest tests.test_fetch_godzilla_server_assets -v
~~~

A cloud-based AI cannot see the owner's Windows cache merely because GitHub has the script. If the mirror is blocked or an owner-local path is not available, report BLOCKED / USER_GATE, never invent source data.

## Use existing rig extractor immediately

From repository root after private files are verified:

~~~powershell
py -3 -m tools.base_mod.extract_godzilla_owner_rig --m-number-list private/server-jp1571/godzilla/MNumberServer.list --m-number-pack private/server-jp1571/godzilla/MNumberServer.pack --w-imagedata-list private/server-jp1571/godzilla/WImageDataServer.list --w-imagedata-pack private/server-jp1571/godzilla/WImageDataServer.pack --output private/godzilla-550_e-original
~~~

Expected 7 private source assets: 550_e.png, 550_e.imgcut, 550_e.mamodel, and 550_e00.maanim through 550_e03.maanim. Existing code tools/base_mod/extract_godzilla_owner_rig.py already uses tools.battlecats_pack.PackReader, rejects overwrites of a nonempty art directory, and issues SHA256 receipts.

Then convert the original enemy Shin Godzilla rig **550_e** into allied Cat No.703 **FIRST FORM** 702_f, preserving second form 702_c. Owner-approved performance remains Lv30 **50,000 x3 / range 2950 / cost 9800 / respawn 500s / cycle 450 frames / enemy castle no more than 1 HP for a complete triple-hit attack**. Real renderer, frame sync, native integration and Android battle proof remain OPEN.

Evidence: [2026-10-10 source recovery research](../research/2026-10-10-original-server-archive-acquisition.md). Existing work ticket: [Issue #14](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/14).

## Verification status

- [x] 4 exact MD5 + size matches reported by owner Windows console.
- [x] New repository-side source recovery/import script and 7 mock tests pass locally.
- [ ] Agent in its own target workspace has acquired and checked the actual files.
- [ ] Original 7 asset bytes extracted and verified via existing extractor.
- [ ] Original-compatible Android battle and approved Godzilla stats proven on-device.
