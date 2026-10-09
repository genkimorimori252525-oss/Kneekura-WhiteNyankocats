# KNEEKURA — Complete Offline Boundary Audit and Architecture Reset (2026-10-09)

> **2026-10-09 PRODUCT-IDENTITY CORRECTION:** This audit correctly identifies the old game's network/save risks, but the owner **did not authorize a new lookalike game**. Strict offline isolation AND full original Battle Cats gameplay fidelity are simultaneous product requirements. The alternative independent-host suggestion below is research-only until original JP UI, battle, animation, unit/enemy/stage/gacha behavior is reproduced and the owner explicitly accepts it. The small `app/` Java "Stage Fidelity Alpha" **is a research harness, not the desired game**. Authoritative: [PRODUCT_IDENTITY.md](../../PRODUCT_IDENTITY.md) and [release gates](product-identity-gates.json). Original-engine-preserving research remains the default where safely achievable; no official server/account or flagged SAVE reconnect. Do not silently substitute a generic stand-alone simulator for the owner's Battle Cats experience.


**Status: FAIL / NOT A FULLY LOCAL BUILD.** JP15.7.1 original-owned source audit; this is not a confirmed server-side enforcement trace. Scope is the exact user-owned APK/export with SHA256 `38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56`. The observed Japanese UI text "不正なセーブデータを検知しました。利用規約に基づき、アプリの利用は継続できません。" only proves that the app displayed an invalid-save/restriction state. It does **not** identify whether the decision happened on-device or after external contact. Do not call this proven data exfiltration or a confirmed permanent account ban without a device network/decision trace.

## 1. Direct findings from owner-owned APK and repository source

| ID | Evidence, exact version | Certainty | Release consequence |
| --- | --- | --- | --- |
| P0-01 | The original `apk/base.apk` Android binary manifest **declares** `android.permission.INTERNET`, `ACCESS_NETWORK_STATE` and related network-state permissions (actual `uses-permission` elements, not merely loose DEX strings). | Confirmed static | No deny-at-OS network boundary. |
| P0-02 | `bridge/java/MyActivity.java.in` inherits `jp.co.ponos.battlecats.MyActivity` and invokes `super.newHttpRequest(...)` on all classifier misses, feature OFF and exception/fallback paths. The only narrowly replayed family is one recognized backup GET. `docs/architecture/phase-c-static-http-bridge.md` explicitly calls original transport on all other requests. | Confirmed static | Official request transport remains reachable; selective HTTP replay is **not** offline isolation. |
| P0-03 | Original manifest declares `com.google.firebase.provider.FirebaseInitProvider`, `com.adjust.sdk.SystemLifecycleContentProvider`, `com.applovin.sdk.AppLovinInitProvider`, `com.google.android.gms.ads.MobileAdsInitProvider` and other analytics/ads/transport services. Original classes.dex, classes3.dex and classes4.dex contain corresponding SDK class names. | Confirmed embedded code/components, not execution | Potential SDK-originated traffic beyond the narrow game HTTP hook; actual transmission unknown. Lifecycle providers can initialize before the subclass handles a game request. |
| P0-04 | `tools/base_mod/verify_shipping_profile.py` explicitly requires `feature_mask_default=0` and original activity parity; `docs/architecture/phase-c-shipping-parity.md` documents the original launcher/transport. The shim constructor does not install any offline network hook. | Confirmed static | A feature-OFF shipping parity PASS proves similarity to original, **not** independence from online services. |
| P0-05 | `tools/base_mod/build_offline_max_save.py` creates a player SAVE_DATA with local JP salted-MD5 integrity rewritten and arbitrary maximum inventory/ownership/resource changes (e.g. Cat Food 45,000, Rare Tickets 299, Battle Items 9,999). `docs/architecture/offline-local-profile-bootstrap.md` records live original UI accepting the MAX profile and rewriting it. | Confirmed source/device history | A valid local salted-MD5 proves file integrity/layout, **not** legitimacy against client/server integrity policies or acquisition-history checks. The MAX profile is a plausible trigger, not a proven root cause. |
| P1-06 | `tools/base_mod/run_phase_c_final_smoke.ps1` explicitly offers the **unchanged original** approximately 615 MiB server asset download after installing research splits; `docs/architecture/phase-c-shipping-parity.md` retains online gacha/event availability. | Confirmed design | Boot and content availability still depend on original service/data lifecycle. |
| P1-07 | `tools/base_mod/package_flavor.py` changes package identifiers and re-signs but keeps the original native game activity/libs and original packaged SDKs. | Confirmed design | Separate package ID is valuable for save isolation but does not automatically block egress or disable client validation. |

**No direct observation of this user's failed-session outbound packet, host, server response, banned user ID, or local decision function is available.** Each runtime allegation requires independent evidence. Android manifest network permission and SDK presence are capabilities, not a packet capture.

Local proof command (read-only; a report is emitted, not a modified APK):
~~~powershell
python -m tools.base_mod.audit_offline_egress --owner-export nyanko_battlecats_2026-10-06.zip --bridge bridge/java/MyActivity.java.in --output private/offline-egress-audit.json --report-only
~~~
`--report-only` is for analysis. Strict mode exits nonzero and **never claims fully local release** solely from a static audit. `network_transfer_observed` and `save_restriction_cause_confirmed` remain null if unobserved.

## 2. Why the original direction failed

Old top-level policy in `docs/architecture/design-philosophy.md` placed "original game/UI host" and "preserve original behavior" first, and treated offline as an intended future substitution of online services. In shipping verification, "no Frida", "original native exports unchanged" and "original requests fall through" were green checks. Those are preservation/security-in-one-sense checks, but they conflict with the newly explicit product guarantee: **the built game must operate independently with zero Internet egress**.

Root architectural error: network isolation was not an enforced platform/runtime invariant. It was one optional, incomplete feature among many research objectives. A game that merely *continues to run in airplane mode once* or *replays a single backup GET locally* cannot be certified as completely local.

SAVE_DATA is a distinct second problem. Even with zero packets, the unchanged original executable can reject a noncanonical inventory/history locally. Do not infer that a network request necessarily caused the Japanese invalid-save warning.

## 3. Reference implementations / external evidence (not exact JP15.7.1 authority)

- **TBCML / fieryhenry:** Python game pack import/patch/repack/signing and optional Frida/native hooks, useful for *offline data preparation*, not a zero-egress warranty. https://codeberg.org/fieryhenry/tbcml ; https://github.com/fieryhenry/tbcml (historical archive).
- **Battle Cats Complete / omochikaeri15:** local viewing of Cat/Enemy/stage/game textures and animation files supplied by the owner. Useful as an *asset-parser and animation-oracle*, not proof of a runnable original Battle Cats game. https://github.com/omochikaeri15/battle-cats-complete
- **BCU_Android / battlecatsultimate:** independent Android game simulation architecture shows an alternative when original executable cannot pass the zero-egress/save-isolation gate. Do not assume this repo is offline either: it includes a GitHub APK downloader; import only audited components and keep original game-owned art local. https://github.com/battlecatsultimate/BCU_Android
- **Battle Cats Private Server / B2M4B7R forkfrok:** service interception using Flask, TBCML, Frida and URL redirection; proves that redirecting game API calls is feasible but it is **not proof of zero external traffic**. Public tunnel examples must not be used as a shipping dependency. https://github.com/B2M4B7R/forkfrok
- **BCSFE-Python / fieryhenry:** save parsing and edit research; an editor's valid save hash does not mean original client/server will accept artificially created inventory histories. https://codeberg.org/fieryhenry/BCSFE-Python
- **PCAPdroid:** open-source no-root on-device network monitor/PCAP export with a *local VPN* (no remote relay) to observe per-app attempted connections. Use only a disposable test build. https://github.com/emanuele-f/PCAPdroid
- **NetGuard:** open-source Android per-app deny-all firewall; optional defense in depth on test devices. Without always-on VPN lockdown, firewall startup gaps remain possible. https://github.com/M66B/NetGuard ; https://developer.android.com/develop/connectivity/vpn
- **Reddit r/battlecats:** reports of similar restriction dialogs include both altered-save suspicion and apparent false positives subsequently resolved via support. These are anecdotal, conflicting and do not establish this user's exact failure cause. https://www.reddit.com/r/battlecats/comments/1sdswup/my_10_year_save_might_be_lost_because_i_tried_to/ ; https://www.reddit.com/r/battlecats/comments/1k3t4fe/

## 4. Revised architecture — separation of responsibilities

### Non-negotiable product contract: Zero Egress / Local Authority

1. Release APK for `jp.kn.white.battlecats` and any practice flavor must **not declare `android.permission.INTERNET`**. Verify final signed APK manifest, not only source template; no original fallthrough to external network. Remove or fully isolate ad/analytics, attribution, messaging, billing and network-dependent initializers/activities/services/providers.
2. Every original request family is classified: local deterministic response, locally retained error, or explicit unsupported/offline UI. **Unknown requests must never invoke original internet transport**. A technical research build may log attempted calls with network denied, never send data to PONOS/third parties. Android IPC to other apps/SDKs also requires inspection.
3. Bundle or import owner-held original assets *offline*, and require **zero runtime server downloads**, including on the very first cold launch and after cache deletion. No default host DNS queries, no hardcoded user account identifiers.
4. Separate `KNEEKURA_SAVE_V1` in app-private storage, with versioned schema + atomic backups/migrations, from original JP `SAVE_DATA`. New local sandbox starts from scratch with player-selected inventory; no original inquiry/user tokens, no JP salted-MD5 or remote account identity. **Never import the rejected/edited original SAVE_DATA into the new local model.**
5. Own local clock/event/gacha/catalog/achievement providers entirely. No official HTTP registration, cloud backups, push tokens, purchase receipt synchronization or telemetry. Mark every unimplemented offline replacement `BLOCKED`; do not silently pass through.
6. Preserve original UI and rendering where possible, **but not at the expense of the zero-egress/local-save contract**. If original JP15.7.1 native runtime cannot safely be decoupled from its server/save enforcement, stop treating that runtime as a shippable product and **research** an independent compatibility engine—but do not present it to the owner as the requested Battle Cats experience without verified UI, content, battle and animation parity and explicit owner approval. Visual parity then becomes an implementation goal, not an excuse to keep official network code.
7. Changes to native hooks require a tested app build. Normal future balance updates should be JSON/content diffs in Kneekura-owned local storage; the four Server `.pack/.list` originals are private immutable resources.

### Security boundaries

`Owned Original Asset Corpus` -> read-only import into `Kneekura Local Asset Store` (hash-pinned; no network) -> `Offline Data/Scene/Battle Host` -> `Kneekura SaveV1` and `Local Configuration`. The host may *not* address external URLs or create a network IPC service. Native feature-OFF must mean locally unsupported, **not original online fallback**.

Do not ship a product that still embeds an unvetted original signed-in online game as the execution authority. Do not use a private-server proxy as a way to contact/evade the original PONOS account service.

## 5. Release gates and acceptance evidence

| Gate | Requirement | Present status |
| --- | --- | --- |
| NET-STATIC | Final signed APK has no INTERNET declaration; analytics/ad/billing SDK lifecycle initialization removed; all original HTTP fallthrough gone | **FAIL** on audited owned original |
| NET-RUNTIME | Boot with real network available but strict OS egress deny-all; PCAP/counters show zero attempted external destinations from the app; no other-app IPC forwarding; test cold boot, battle, gacha, upgrades, save/restart, 24h clock change | **NOT RUN** |
| NET-OFFLINE | Test from **first installation** in airplane mode, clear data/cache, absent server corpus, repeated startup and battle. All assets must be manually supplied first, never fetched | **NOT RUN** |
| SAVE-LOCAL | Independent `KNEEKURA_SAVE_V1` created/read/written, deterministic MAX state optional, no official SAVE_DATA imports/validation flags; corruption restores Kneekura snapshot only | **NOT IMPLEMENTED** |
| ENGINE-LOCAL | All battle stats and target-aware castle 1-per-three-hits effective under verified original/independent battle scene | **NOT VERIFIED** |
| ART-LOCAL | All required assets including Godzilla 550_e -> allied 702_f in private owner store; unchanged 702_c; no runtime downloads | **NOT VERIFIED** |
| UPDATE-LOCAL | Versioned manifest import, checksum, rollback; no server polling; no external credentials, no APK reinstall for data-only tweaks after tested plugin architecture | **NOT IMPLEMENTED** |

**No new build should be called "complete offline" until these gates pass independently.** A passing Source CI test or single airplane-mode boot is insufficient.

## 6. Execution priorities

P0: Stop using the modified original SAVE_DATA as a game-state source. Preserve owner research files privately only if desired. Don't attempt account/server reconnection using that save. P0: Add static audit tool and mark original hosted builds "offline-unverified"; never release with super fallthrough. P1: Prove no-internet-permission cold boot in a disposable package and map all required original offline asset/service dependencies. P1: Start Kneekura-owned save format and local resources with no official identity. P2: Prioritize original JP15.7.1 UI/engine behavior; if researching an independent battle/animation host, keep it explicitly labeled a harness until verified against original gameplay and owner acceptance. P3: restore convenience updater from versioned JSON/asset cache only after engine and network gates pass.
