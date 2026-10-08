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