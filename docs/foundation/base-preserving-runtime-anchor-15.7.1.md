# Base-Preserving Runtime Anchor — JP 15.7.1

Evidence date: 2026-10-06  
Target: exact user-owned JP 15.7.1 Android installation/export.  
Purpose: freeze the binary/runtime identity before any base-preserving patch is allowed.

## Source identity

Authoritative full-export identity from the earlier complete read-only pass:

- outer export: `nyanko_battlecats_2026-10-06.zip`
- size: **156,585,000 bytes**
- SHA-256: `38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56`
- package: `jp.co.ponos.battlecats`
- versionName: `15.7.1`
- versionCode: `1507010`

The Project file service currently caps raw materialization at 100 MiB. A fresh container-side materialization therefore exposes only a prefix copy. That prefix still contains the first five installed APK splits completely and the beginning of `split_InstallPack.apk`. The prior full-file SHA/size and InstallPack analysis remain the authority for the full export; this document does not pretend the capped container prefix is a complete replacement.

## Installed split topology

Full-export foundation evidence fixes six installed APKs:

1. `base.apk`
2. `split_config.arm64_v8a.apk`
3. `split_config.en.apk`
4. `split_config.ja.apk`
5. `split_config.xxhdpi.apk`
6. `split_InstallPack.apk`

The current prefix re-check recovered the first five byte-for-byte and reached the sixth local ZIP entry before the platform materialization cutoff.

### Recovered split hashes

| Split | Uncompressed bytes | SHA-256 |
| --- | ---: | --- |
| `base.apk` | 25,913,924 | `60e5e9df891b7be487abc4590fb3ca2e98218225efedbe4ba26b39dc10ce5c9a` |
| `split_config.arm64_v8a.apk` | 15,369,082 | `3beb6c5096b5b9715873f3cfa4dc933fb641288cb97e7ca5af446496704cf213` |
| `split_config.en.apk` | 49,362 | `e93fbaade0e868134260a142fa49ebd8d06714370657077fd4b368582def4d59` |
| `split_config.ja.apk` | 24,786 | `1e557b1b203370d6e3836e774a83b1abc2f86babc42bdc0091907a2326ff819a` |
| `split_config.xxhdpi.apk` | 239,918 | `2948f5ff34ac441d9efab0060da91d04ebec0e30b7b586850c4e27defa8b2c90` |

The full previous pass fixes `split_InstallPack.apk` at 132,290,560 uncompressed bytes and 199 asset entries. Its current full SHA is intentionally not invented here because the capped re-materialization does not contain all of its bytes.

## Manifest anchor

Binary AndroidManifest parsing of the exact recovered `base.apk` gives:

- package: `jp.co.ponos.battlecats`
- versionName: `15.7.1`
- versionCode: `1507010`
- minSdkVersion: `29`
- targetSdkVersion: `36`
- compileSdkVersion: `36`
- launcher activity: `jp.co.ponos.battlecats.MyActivity`
- launcher action: `android.intent.action.MAIN`
- launcher category: `android.intent.category.LAUNCHER`

`MyActivity` is therefore the presentation/runtime host that the product must preserve. The modified product must not substitute the repository's verification-harness `MainActivity`.

The base manifest currently requests `android.permission.INTERNET`. Removal is deferred until the local-service/native-shim route proves that no required startup path still depends on it. The preservation rule is to remove dependencies before removing the permission, not to break boot for the sake of an early static checkbox.

## Package-separation hazards

Changing only the manifest package is insufficient.

The manifest contains package-scoped values that would collide with the official installation if left unchanged, including:

- custom permission `jp.co.ponos.battlecats.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION`
- provider authority `jp.co.ponos.battlecats`
- IronSource lifecycle provider authority
- AppLovin init provider authority
- AndroidX startup provider authority
- Audience Network provider authority
- Mobile Ads provider authority
- Firebase init provider authority
- Adjust lifecycle provider authority

However, **Java/native class namespaces must not be blindly renamed**. The original native library exports JNI symbols such as:

- `Java_jp_co_ponos_battlecats_MyActivity_appInit`
- `..._appUpdateDraw`
- `..._gfxInit`
- `..._appTouch`
- `..._request`
- `..._newResponse`

The safe separation design is therefore:

- change Android application/package identity and collision-prone authorities/permissions;
- keep original Java class namespace `jp.co.ponos.battlecats.*` unless exact JNI registration evidence proves a different safe route;
- audit every package-prefixed manifest value by semantic role before patching.

## Native runtime anchor

Exact recovered ARM64 game library:

- path: `lib/arm64-v8a/libnative-lib.so`
- size: **11,639,200 bytes**
- SHA-256: `333d2974ab2ff881fd70087fd62dea7d12d82addbc55cab2f2a675ad67e3a7e2`
- GNU build ID: `8cb3815648eb9642da10bfb039d71bff7a3519bd`
- ELF: AArch64, shared object
- SONAME: `libnative-lib.so`

Observed native dependencies include Android, JNI graphics, GLESv3, OpenSLES, log, libm, libdl and libc.

The library still exports a useful JNI surface despite stripped internal symbols. That surface is a high-value version-pinned anchor for the base-preserving shim investigation.

## Signing identity anchor

Every recovered split contains `stamp-cert-sha256` with:

`3257d599a49d2c961a471ca9843f59d341a405884583fc087df4237b733bbd6d`

This is treated as the original distribution certificate stamp identity for split-consistency checks. A Kneekura build will necessarily be re-signed with a different local key; all splits in one install set must then be signed consistently.

## Product parity gate

Before a product patch is accepted:

1. launcher remains original `MyActivity`;
2. original Java/native class namespace is not renamed casually;
3. original game packs/scenes/assets are unchanged unless a documented feature requires a specific data edit;
4. every changed manifest authority/permission/package field is enumerated in the patch ledger;
5. `libnative-lib.so` base SHA/build ID are checked before applying any native patch;
6. unknown target SHA/build ID fails closed;
7. extension-disabled native shim path must return control to original behavior immediately.

This runtime anchor is the baseline against which every later Personal MAX and Practice Clean artifact is compared.