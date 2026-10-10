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
py -3 -m unittest discover -s tests -p test_fetch_godzilla_server_assets.py -v
~~~

A cloud-based AI cannot see the owner's Windows cache merely because GitHub has the script. If the mirror is blocked or an owner-local path is not available, report BLOCKED / USER_GATE, never invent source data.

## Recommended one-command offline Godzilla source staging

The owner's recovery was **already 4/4 MD5+size verified** on Windows.
Once this repository has the latest source overlay, run this one command
from the repository root. It locally copies and revalidates four original
files, decrypts the verified archives and stages all seven 550_e source
rig files into separate git-ignored private directories. It never touches
the original game's APK, SAVE or account.

~~~powershell
$owned = Join-Path $env:USERPROFILE 'Downloads\kneekura-server-recovery-jp1571\kneekura_server_recovery\server_archive_cache\files'
py -3 -m tools.base_mod.fetch_godzilla_server_assets --from-dir "$owned" --extract-original-godzilla-rig
~~~

Expected private-only receipt:
private/godzilla-550_e-original/rig-receipt.json
(source assets NOT converted to cat first form 702_f). Output destinations
must be NEW: on a second run, use the existing private files directly or
choose a different empty rig destination instead of overwriting anything.

Separately, new tools/base_mod/audit_original_server_mirror.py can audit
all 35 owner manifest lanes against the historical GitHub TREE metadata.
The independent read-only comparison found **348/358 matching names/sizes**
(176/186 Server files and 172/172 audio), not MD5 verification of 348
content bodies. Five X family pairs are absent from the public mirror.
XImageDataServer.list/.pack can be recreated byte-exactly from the
original empty-list algorithm and checksum; eight X files still need an
authenticated source. See research/2026-10-10-original-server-archive-acquisition.md.

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


## No703 first-form private preview — one owner-local command (2026-10-10)

The four original JP15.7.1 Server files have matching sizes and MD5 on the
owner's Windows PC. Do **not** upload original .pack/.list/PNG/models/animations
to this repository, an issue, PR or CI.

The existing one-command recovery tool now supports a NON-INSTALLABLE allied
first-form preview after verifying the 4/4 sources:

~~~powershell
$owned = Join-Path $env:USERPROFILE 'Downloads\kneekura-server-recovery-jp1571\kneekura_server_recovery\server_archive_cache\files'
py -3 -m tools.base_mod.fetch_godzilla_server_assets --from-dir "$owned" --extract-original-godzilla-rig --prepare-ally-preview
~~~

After success, the private/ Git-ignored paths are:

~~~text
private/server-jp1571/godzilla/                 4 original Server files + MD5 receipt
private/godzilla-550_e-original/                7 unmodified enemy 550_e assets
private/godzilla-702_f-preview/                 7 No703 first-form preview files
private/godzilla-702_f-preview/
  rig-conversion-preview-receipt.json           metadata only
~~~

The converter changes the .imgcut PNG reference from 550_e to 702_f, rebases
the .mamodel original image ID from 550 to 702, and makes a negative root
horizontal scale positive if necessary for allied-facing. It preserves
the PNG **pixel bytes**, all 4 .maanim **keyframe bytes**, model geometry apart
from the two recorded fields, and original collision-footer data. It checks
PNG cut rectangles against actual IHDR dimensions, validates source model
part indices and animation track/keyframe counts, and refuses malformed
or unexpected model image IDs before writing anything. Every output SHA256
and all orientation assumptions are recorded in the conversion receipt.

The original owner ZIP's ImageDataLocal was used read-only to corroborate
the format: 671 model examples including original enemy 730_e and allied
799_f; 1,814 animation files with six legitimate zero-keyframe tracks.
**Those original sample bytes are not checked into Git.**

If a prior 550_e rig has already been extracted, do NOT rerun with the same
existing destination (the tool refuses overwrites). Use the dedicated step:

~~~powershell
py -3 -m tools.base_mod.prepare_godzilla_ally_preview --source private/godzilla-550_e-original --output private/godzilla-702_f-preview
~~~

Both commands refuse an existing candidate output. Do not delete the original
enemy rig or the second form 702_c to make the command pass; use a distinct
new private preview name if appropriate.

This is **not** native Android animation/render acceptance, not a rig
mirror guaranteed by the original runtime, and not an installable APK.
Original cat 702_c second form remains completely unchanged. Still open:
Godzilla 50,000x3 native damage, castle sequence HP debit max 1, 450-frame
cycle, in-game facing/animation frame sync, and full offline original engine
SAVE/battle confirmation. Separate extra 35 download_N.tsv payloads are not
made available by these two Server family pairs; never equate the two-pair
recovery with a complete 615 MiB original game local asset cache.


## WImageDataServer first-form resource-priority candidate (research only)

Static JP15.7.1 source confirms original Server registration indices:

| Original native family | Zero-based registration index | Meaning |
| --- | ---: | --- |
| WImageDataServer | 4 | Original 702_f model, cut and four animations |
| QNumberServer | 27 | Existing friendly 702_f.png texture source |
| MNumberServer | 43 | Original enemy 550_e.png texture source |

The source native code at \`0x34D3B0 → 0x34D484\` skips insertion
when a resource name already exists. **Only if the earlier Server pair is
actually registered and accepted at runtime**, a new 702_f.png key registered
from WImageDataServer at index 4 may be chosen before the existing texture at
QNumberServer index 27. This is a conditional research hypothesis, NOT a
proven original-game override, and a new archive necessarily fails the original
download-table MD5 until a legitimate fully local archive-acceptance path is
verified. Do not install this candidate into an APK or copy it over the
original cached pack.

After the separate 550_e → 702_f private conversion has been verified, the
following command writes an **additional private, non-installable** candidate:

~~~powershell
py -3 -m tools.base_mod.prepare_godzilla_native_resource_preview --original-server-dir private/server-jp1571/godzilla --ally-preview-dir private/godzilla-702_f-preview --output private/godzilla-wimagedata-702f-preview
~~~

It requires the owner's exact original WImageDataServer.list and .pack
**byte-size and MD5** values, all 7 preview SHA-256 receipts and the
original six 702_f slots. It refuses unexpected manifest CSV columns,
noncontiguous offsets, trailing pack data, an existing 702_f.png in the source
family or missing 702_c cut/model. It re-encrypts only the six 702_f model/cut/
animation slots, appends only the converted 702_f PNG to this *private*
WImageDataServer candidate, validates every source non-target asset unchanged,
and verifies the original 702_c second form byte-for-byte. Both original
WImageDataServer source files and the original 550_e art remain untouched.

Expected additional Git-ignored output:

~~~text
private/godzilla-wimagedata-702f-preview/
  WImageDataServer.list
  WImageDataServer.pack
  candidate-research-receipt.json
~~~

The files must **not** be redistributed, uploaded or substituted for the
official DownloadLocal/DataLocal cache without a separate source-accurate
runtime integrity and original Android proof. This research still lacks
original-game runtime asset selection, accepted archive MD5, rendered
orientation, attack synchronization, Lv30 50,000×3, castle HP sequence = 1,
and original app SAVE/restart/zero-external-network acceptance.

**Owned original JP15.7.1 ImageDataLocal grammar corroboration** (not a
runtime proof): 1,814 local animation files contain 127,224 tracks and
1,009,451 keyframes, including eight whole animations with zero tracks, six
tracks with zero keyframes, 22,960 negative-frame entries and six special -2
model-node references. The private converter permits these legitimate native
records but rejects malformed/unknown model-node references.
