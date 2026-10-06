# Base-Preserving Boot Smoke

This checkpoint produces **the original JP 15.7.1 Battle Cats split set with
only the minimum Phase-A mutations**:

1. inert `libkneekura.so` bootstrap dependency;
2. separate Personal/Practice Android application id;
3. re-signing with one disposable smoke-test certificate.

It does not activate gameplay extensions.

## Expected static diff

### base.apk

Only:

- `AndroidManifest.xml`
- `resources.arsc`
- one `classes*.dex`

The resource-table package name is updated because the exact base resources
contain one dotted application-id occurrence.

The DEX anchor contains exactly two package-bearing strings:

- the plain application id;
- `<package>.NotificationChannel.`

Java class descriptors remain `jp/co/ponos/battlecats/...`.

### split_config.arm64_v8a.apk

Only:

- `AndroidManifest.xml`
- `lib/arm64-v8a/libnative-lib.so`
- added `lib/arm64-v8a/libkneekura.so`

The original native library has one dotted application-id string. It is changed
to the flavor application id after the exact-hash DT_NEEDED bootstrap mutation.

The original JNI/export symbol surface must remain unchanged.

### Other splits, including InstallPack

Only `AndroidManifest.xml`.

In particular every `split_InstallPack.apk/assets/*` entry must remain
byte-identical to the source.

## Smoke build signing

The CI boot-smoke artifact uses a **disposable 30-day CI signer**. This is
intentional: the checkpoint tests boot/package isolation without storing a
private signing credential in GitHub.

Do not build progression on that artifact. A later stable build must use a
user-controlled local signing key. Installing a future differently signed build
requires uninstalling the smoke build first.

## Device smoke procedure

Install all six APKs in one command:

```bash
adb install-multiple -r *.apk
```

Launch:

Personal:
```bash
adb shell am start -n jp.kn.white.battlecats/jp.co.ponos.battlecats.MyActivity
```

Practice:
```bash
adb shell am start -n jp.kn.clean.battlecats/jp.co.ponos.battlecats.MyActivity
```

Pass condition:

- original Battle Cats boot and base screen;
- original UI navigation;
- one original stage can be entered/exited;
- no verification-harness Activity;
- airplane-mode reboot/navigation does not immediately fail;
- feature mask remains 0, so no Kneekura gameplay features are expected yet.

A static CI pass is not reported as a successful real-device boot. Device
evidence remains a separate gate.