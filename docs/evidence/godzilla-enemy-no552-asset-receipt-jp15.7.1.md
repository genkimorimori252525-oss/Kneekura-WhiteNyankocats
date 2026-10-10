# JP 15.7.1 — Shin Godzilla enemy art provenance (2026-10-09)

Metadata **only**. Never commit the owner-original game assets.

Evidence: authenticated inspection of historical/current server filenames in GitHub Actions run 37417655457, artifact ID 11391338442, server-manifest-index.json. Original owned JP DataLocal/t_unit.csv SHA256 d4fe8661e39a8f489e7549f03b5de4020acb6d7f8560438bdbb9490ec2f8cb04 has two zero/reserved initial rows. Enemy data row552 (Godzilla, 500 HP / 200 x3, standing 3800) maps to enemy visual 550_e through the two-row offset, not 552_e.

| Asset filename | Historical server family |
| --- | --- |
| 550_e.png | **MNumberServer** |
| 550_e.imgcut | WImageDataServer |
| 550_e.mamodel | WImageDataServer |
| 550_e00.maanim | WImageDataServer |
| 550_e01.maanim | WImageDataServer |
| 550_e02.maanim | WImageDataServer |
| 550_e03.maanim | WImageDataServer |

Confirmed target friendly cat first form No703 visual stem **702_f**: 702_f.png is in **QNumberServer** and cut/model/00..03 motion tracks in WImageDataServer. Second form 702_c also exists and must remain entirely unchanged.

An owner-local encrypted Server pack extractor can use these two source family pairs to stage the *seven original enemy art files* privately, fingerprint each, and prepare a review of mirroring / rig interpolation. It must NOT put source PNG/model/animation files in public Git or pretend that filename renaming alone makes an allied animation.

Actual owner 150 MB APK export contains local packs, NOT the required downloaded MNumberServer/WImageDataServer body pairs, so the model conversion and original-Android device proof are still gated.

## 2026-10-10 original native priority and preview-only loading plan

User-owned JP15.7.1 native Server registration order was independently
verified in \`original_server_registry_rows.py\`:
WImageDataServer zero-index **4**, QNumberServer zero-index **27**,
MNumberServer zero-index **43**. The exact original native resource map
\`0x34d3b0 → 0x34d484\` retains the first successfully inserted same-name
resource key; this is a static conditional precedence witness, not observed
Android runtime source selection.

The user reported **four** original list/pack files whose sizes/MD5 match
JP15.7.1 owner-manifest metadata. The user-owned encrypted files themselves
remain only in private Windows storage. Their raw bytes and original Godzilla
art do not belong in this Git repository.

Code checkpoints:
- \`tools/base_mod/prepare_godzilla_ally_preview.py\` checks cut/model/
  animation grammar, original model indices and signed/negative keyframes,
  preserving original 4 animation tracks exactly and second form \`702_c\`.
- \`tools/base_mod/prepare_godzilla_native_resource_preview.py\` builds a
  **non-installable** separate WImageDataServer candidate with six model/cut/
  animation replacements and one additional earlier-name \`702_f.png\`.
  The original 702_c and all other original entries must decode unchanged.
  Generic encrypted Source pack writer is already in
  \`battlecats_pack_writer.py\`; the candidate verifies its source first and
  refuses unexpected format, original pack gaps or owner-secret uploads.

**Negative release gates**: the new candidate does not match original archive
download-table MD5; the early native first-successful source precedence is
not a proven accepted real device winner; there is no source-accurate original
Android renderer, animation, castle1, Lv30 50k×3, independent player SAVE,
or strict zero-SDK/IPC network runtime proof. No APK or device is patched.


## 2026-10-10 — Source-owned JP15.7.1 image-less bones and full encrypted pipeline

The original owner-supplied JP15.7.1 InstallPack's \`ImageDataLocal\` (not
downloaded Server archives) was reexamined READ ONLY. Across 671 source
\`.mamodel\` files, 4 legitimate model-node rows have atlas/image ID=-1
**and** cut/sprite ID=-1, all within \`000_g00_1.mamodel\`. They represent
image-less control bones. The first-form converter now allows exactly this
sentinel pair in nonroot nodes, while still rejecting cut ID=-1 for an
atlas-backed image. Both variants are verified by synthetic tests; no
copyrighted original model rows or image bytes were uploaded.

The existing Godzilla owner-only one-command acquisition tool gained the
strictly opt-in \`--prepare-native-resource-candidate\` flag, chained AFTER
\`--extract-original-godzilla-rig\` AND \`--prepare-ally-preview\`.
This combines **four source-MD5 checks → 7 original encrypted rig assets →
7 converted 702_f first-form assets → WImageDataServer 702_f candidate**,
with each stage confined to NEW Git-ignored \`private/\` directories and
never modifying user assets, SAVE, APK or account. All four stages were
exercised end-to-end using independent self-created synthetic encrypted
JP-style \`.list/.pack\` pairs in
\`tests/test_godzilla_full_private_pipeline.py\`. The tests cover stage
ordering, source and second-form 702_c byte immutability, candidate
decryption/readback, source MD5 mismatch abort and required opt-in flags.

**What this does not prove:** 4 actual owner-recovered Server file bytes
remain on the owner's Windows PC, not in this execution environment. The
synthetic test is NOT evidence that their actual 550_e rig was extracted,
that original game source precedence selected 702_f, or that changing a
Server pack passes the original download-table MD5. The actual native
original Android renderer, 50,000×3 attack, 1 castle HP damage, SAVE,
Lv60/MAX and network isolation remain unverified.
