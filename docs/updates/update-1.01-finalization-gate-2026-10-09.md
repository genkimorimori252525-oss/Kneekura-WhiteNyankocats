# KNEEKURA Update 1.01 — verified finalization gate (2026-10-09)

**Status: NOT RELEASED / NOT INSTALLABLE.** These are tested source/build milestones; this is not evidence of successful Android original-battle gameplay.

## Approved and immutable user constraints

| Feature | Approved JP15.7.1 target |
| --- | --- |
| Official native level ceilings | 323 eligible cats -> Lv60, 493 -> Lv50, 11 -> Lv20, 8 -> Lv1. Existing runner preserves current levels, roster, Legend and story progress. |
| Ultimate Madoka No289 form2 only | Lv30 attack 28,000; standing/sensing 750; EoC2 cost 4,550; recharge 155s. Preserve LD450–800, other forms, traits and unique death animation. |
| Godzilla cat No703 form0 only | Lv30 50,000 x3 = 150,000; sensing 2,950; EoC2 cost 9,800; recharge 500s; 450f/15s attack cycle; max **1 castle HP per whole triple-hit sequence**, not 1 per hit. Preserve form1. |

## Directly executed verification

1. Owner's exact JP 15.7.1 ZIP SHA256 38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56, full CRC PASS, six APK splits.
2. Source-original Madoka unit289.csv and Godzilla unit703.csv verified against pinned source SHA and changed only form2/form0 respective columns. No SAVE_DATA migration run.
3. Original six APK splits were reconstructed locally, and an **UNSIGNED research candidate** actually assembled. Original InstallPack preserves 199 ordinary files byte-for-byte, changing ONLY assets/DownloadLocal.list and assets/DownloadLocal.pack. Both original DataLocal files and the other five APK splits are byte-identical. Proprietary APK bytes remain private and are NOT in this public repository. Reproducible source: tools/base_mod/build_update_101_unsigned.py and tests/test_build_update_101_unsigned.py.
4. Original ARM64 libnative-lib.so SHA256 333d2974ab2ff881fd70087fd62dea7d12d82addbc55cab2f2a675ad67e3a7e2, GNU BuildID 8cb3815648eb9642da10bfb039d71bff7a3519bd. Native unwind search table has 23,086 function starts. Pinned literal data-source loader boundaries: DataLocal 0x714ae8..0x719044; DownloadLocal 0x71c408..0x71dcf4; t_unit 0x8a3624..0x8a3900; enemyCastleData0 0x553258..0x55378c. They are **data loaders, not identified native castle HP damage functions**. Read-only tool: tools/base_mod/audit_native101_loader_frames.py.
5. Separate C native policy kneekura_battle101.c resolves exact Lv30 hit values and a battle-local per-unit/per-attack-sequence maximum 1 castle damage. Cross-compiled and OFF/ON host regressions PASS. Still **not bound to the original Battle Cats engine**, feature OFF by default.
6. Exact enemy Godzilla asset filename stem 550_e verified in historical server metadata. Enemy rig requires PNG from MNumberServer and cut/model/four maanim tracks from WImageDataServer. Owner's Oct6 ZIP does NOT contain those downloaded Server pair bytes; only filename metadata is verified. tools/base_mod/extract_godzilla_owner_rig.py safely extracts owner-supplied pair bytes; no mirrored playable cat animation yet.
7. Read-only asset collection script tools/base_mod/collect_update_101_server_assets.py and gated owner wrapper tools/base_mod/run_update_101_owner_gates.ps1 are now available. Collection requires authorized physical device and explicit --pull / -CollectPrivateServerPacks. No server credentials or private assets in Git.

## Exact owner-side next input

From the user's originally downloaded files on the research-device cache (possible research root /sdcard/Android/data/jp.kn.trace.battlecats/files), obtain these FOUR original cached files locally via the read-only owner script:

- MNumberServer.list
- MNumberServer.pack
- WImageDataServer.list
- WImageDataServer.pack

If the research cache does not contain them, complete the unchanged original in-app download in the disposable research profile. Never attempt unsafe third-party proprietary archive redistribution. Private asset collection and converter inputs must never be committed to public GitHub.

## Blockers that still prevent an honest, user-installable 1.01

A. Prove typed, exact-JP15.7.1 original engine pre-trait/base-damage and target-specific post-modifier castle HP-debit callsites with observed device trace. Read-only loader function addresses are NOT valid game damage hook addresses.

B. Prove DownloadLocal takes precedence for unit289.csv and unit703.csv in original UI, original H01-free loading, and feature-OFF original battle parity.

C. Connect C policy only after (A,B), reconcile exact 28,000 / 50,000 x3 native integer rounding, production cost rounding, 450f cycle and original 130/170/210f strike animation timing.

D. Privately convert original Godzilla enemy 550_e model into allied 702_f using actual PNG/imgcut/mamodel/maanim bytes, demonstrate orientation and animation; preserve 702_c and Madoka special death.

E. Build same-signature owner Personal MAX APK, and demonstrate existing SAVE_DATA preservation, original UI, offline battle, forced stop/restart, persistent native level caps, and exact rollback on owner's physical Android.

**No signed or installed Android Update 1.01 has been verified.** Do not enable native bit7 in shipping, patch guessed offsets, use native pack-MD5 bypass, wipe/uninstall the existing app, or publish owner APK/asset/save/keystore. PR #4 remains draft; Issues #2/#3 remain open.

Links: https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/pull/4

A conversation-private engineering ZIP was created for the user with older preview scripts, source candidate and rig reference. Latest Python, PowerShell and native-code sources remain authoritative in the GitHub PR branch.