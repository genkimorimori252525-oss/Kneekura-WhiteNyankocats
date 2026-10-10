# JP15.7.1 Server archive recovery — 2026-10-10 source evidence

**Status: METADATA / OFFLINE UNIT TEST VERIFIED; CDN LIVE AVAILABILITY AND PACK BYTES NOT YET CONFIRMED.**
Not a new product roadmap. CURRENT.md remains the single entry point; original-game LEVEL → MADOKA → GODZILLA and OFFLINE retain precedence.

## Real owner device (stock PONOS package)
- Windows Android SDK `adb.exe` was present but not on PATH; temporary session PATH repair succeeded.
- One authorized `device` was connected, `pm path jp.co.ponos.battlecats` found the original base and split APKs.
- `su -c id` -> `su: inaccessible or not found`.
- `run-as jp.co.ponos.battlecats id` -> `package not debuggable`.
- `/sdcard/Android/data/jp.co.ponos.battlecats/files/` was empty.
- Thus stock ADB cannot obtain original app-private Server files under current permissions; **never request root/reinstall/clear data just to obtain these files**. Device preflight improvement: Issue #16 and AGENTS.md.

## Verified exact owner's export
`nyanko_battlecats_2026-10-06.zip` SHA256:
`38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56`

`split_InstallPack.apk/assets/download_0.tsv` through `download_34.tsv` contain 35 archive size/MD5 headers and **358 file entries** (includes audio), of which **186 are Server.list/pack files (93 pairs)**. The 35 expected original ZIPs total **645,599,537 bytes (615.69 MiB)**. Version vector decoded from the owner's ARM64 via `tools/base_mod/analyze_server_download_gate.py`. The source reconstruction of native registration has **92 pairs** (see `original_server_registry_rows.py`); do not misrepresent all 93 TSV names as runtime-registered. One naming count difference remains subject to exact runtime mapping.

URL builder pinned in repo `analyze_server_download_gate.py::build_lane_url`:
`https://nyanko-assets.ponosgames.com/iphone/battlecats/download/battlecats_{major:06d}_{lane:02d}_{minor:02d}.zip` for numeric version >= 1,000,000; older versions have a second format. **This is a reconstructed historical URL, not independently verified availability today.** Do not defeat authentication or rate limits.

### Narrowest original Godzilla animation asset acquisition
The four exact required private source files live in 2 historical archive lanes:

| lane | reconstructed URL suffix | ZIP bytes | ZIP MD5 |
|---|---|---:|---|
| 18 | `battlecats_100900_18_00.zip` | 14,958,447 | `bafd06ff9b68715f0d5d7b739a77d578` |
| 33 | `battlecats_140600_33_00.zip` | 72,992,457 | `f900d8385f95b58621f9c1c974577642` |

Expected uncompressed member sizes/MD5:
- `MNumberServer.list` 2,832 / `34219ad4ddebe715ddaa3af4244697b1`
- `MNumberServer.pack` 10,637,344 / `0c23c4defa077d2e97fbbb1b28a0de4d`
- `WImageDataServer.list` 451,888 / `1ddee28c515a52ebd0a09d655745945c`
- `WImageDataServer.pack` 79,788,272 / `cebd0898a2c9d68fa3c7631afa9dd0d2`

## User-side source-only handoff
Conversation attachment (not put into public Git) was prepared:
`kneekura-server-official-cdn-probe-jp1571.zip`; SHA256 `44222d4481578649e70732811327ba437ddfc46e0b5c4a16c9df3d1a5d60b01c`.

Contains `kneekura_server_recovery/download_official_server.py`, `server_archives_jp1571.json` metadata, `SERVER-DOWNLOAD-README.md`, and `test_download_official_server.py`. It is an **add-on** to prior owner read-only USB recovery ZIP, not a game updater or replacement APK.

Owner runs in existing `kneekura_server_recovery` folder:
```powershell
py -3 .\download_official_server.py --probe --focus godzilla
# only if endpoint responds and archive retrieval is allowed:
py -3 .\download_official_server.py --download --focus godzilla
```

Results are saved **only on owner PC** under `server_archive_cache/archives/` and `server_archive_cache/files/`. MD5+byte-count verifies the archive itself AND extracted `.pack/.list` members; no file is silently overwritten and no unverified data is accepted. `--focus all` covers all 35 lanes after a narrow positive proof. **No account credential, altered PONOS SAVE, device root, or online account reconnection used.**

Local test evidence 2026-10-10: `python -m unittest discover -s kneekura_server_recovery -p test_download_official_server.py -v` => 6 tests PASS (mocked download, archive/file hash enforcement, no silent overwrite, traversal block, 35-lane manifest). This does **not** establish live CDN access or exact real pack bytes downloaded. User must report HTTP status/MD5 receipt as USER_GATE.

## Fallback if historical URL denies access
Retain exact hash manifest. Search owner-held caches, past explicitly distributable archives or known-authorized channels. Public TBCML/BCData are research leads but raw game asset bytes must remain private and match original checksums; a similarly named newer or different-region pack is not an exact substitute. Do not circumvent access controls. Device private path remains inaccessible over non-root ADB.

## Gates
- [x] Exact original ZIP source fingerprint / original `download_*.tsv` metadata
- [x] Candidate historical URLs derived for all lanes and 2-file-focused set
- [x] Local mocked transfer + extraction rejection tests (6/6)
- [x] Owner-specific probe/add-on ZIP bytes audited
- [ ] Owner PC actual HEAD/GET endpoint response
- [ ] Original archive MD5 and four member MD5 comparisons on returned real content
- [ ] Owner-private Godzilla 550_e rig decoding + original game UI integration


## 2026-10-10 owner real HTTP test and rediscovered historical mirror

**Live proof:** Owner Windows PC probed and attempted GET on both reconstructed historical PONOS CDN ZIP URLs; **both returned HTTP 403** (`battlecats_100900_18_00.zip`, `battlecats_140600_33_00.zip`). There was **no archive downloaded or validated**. A 403 is a denial for these requests, not proof of permanent removal. Do not fabricate CDN success or suggest bypassing its authentication.

**New, independently observed metadata:** [fieryhenry/BCData `jp_server`](https://github.com/fieryhenry/BCData/tree/main/jp_server) includes four original-filename candidates **with byte sizes that exactly match the source JP15.7.1 download manifest**:

| Name | GitHub mirror byte size | Owner JP15.7.1 expected MD5 |
|---|---:|---|
| MNumberServer.list | 2,832 | `34219ad4ddebe715ddaa3af4244697b1` |
| MNumberServer.pack | 10,637,344 | `0c23c4defa077d2e97fbbb1b28a0de4d` |
| WImageDataServer.list | 451,888 | `1ddee28c515a52ebd0a09d655745945c` |
| WImageDataServer.pack | 79,788,272 | `cebd0898a2c9d68fa3c7631afa9dd0d2` |

Mirror file contents and their **MD5 are NOT yet verified in any real download**. Public availability of the mirror at the owner's PC is also USER_GATE. The third-party mirror is not an authorized PONOS CDN endpoint; only copy for owner-local private research, do not redistribute copyrighted file bodies in Git.

**Owner fallback add-on ZIP:** `kneekura-server-bcdata-recovery-jp1571.zip`, SHA256 `6c73f57e942e998d996b5b50f117bf425054c071b4e9b439e0fa9ca7c4bc3b23`. This is source/tooling only, not a pack-byte archive. Overlay onto prior `kneekura-server-recovery-jp1571` directory and run from `kneekura_server_recovery`:

```powershell
py -3 .\download_bcdata_server.py --download
py -3 .\download_bcdata_server.py --verify-only
```

The script fetches four literal historical mirror filenames via raw.githubusercontent.com; checks exact byte count + MD5 using the user's 35-lane owner-manifest; stages in temporary .part files, atomically promotes verified content, never replaces a conflicting existing file, and stores a **metadata-only verification receipt** under `server_archive_cache/files`. No ADB/root/install/network-account/SAVE manipulation.

**Local validation completed**: 7 unittest cases PASS, Python syntax PASS, ZIP CRC PASS, unpacked ZIP tests PASS; actual mirror HTTP access and real four MD5 matches remain OPEN. The offline `--verify-only` properly rejects a missing file set. Status: **POTENTIAL ASSET SOURCE IDENTIFIED, USER DOWNLOAD + FOUR MD5 VERIFICATION REQUIRED**.
