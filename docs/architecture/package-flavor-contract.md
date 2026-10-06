# Package Flavor Contract — Personal / Practice

Approved package identities:

- Personal MAX: `jp.kn.white.battlecats`
- Practice Clean: `jp.kn.clean.battlecats`

Both are intentionally 22 ASCII bytes, exactly matching
`jp.co.ponos.battlecats`.

## Why equal length matters

The exact JP 15.7.1 build contains a stripped native runtime and compiled binary
Android XML.  A same-length application-id replacement lets the project patch a
small set of exact string-pool values without moving binary XML offsets.

It also allows the single plain `jp.co.ponos.battlecats` DEX string used by
`MyActivity.openNotificationSettings` to be replaced in place.  The DEX
SHA-1 signature and Adler-32 checksum are repaired afterward.

## What changes

Every split manifest:

- manifest package `jp.co.ponos.battlecats` -> flavor package.

Base manifest only:

- package-scoped custom permission;
- package-scoped provider authorities.

Base DEX:

- the one exact plain-package string anchored in JP 15.7.1.

## What must *not* change

The Java/native class namespace remains:

`jp.co.ponos.battlecats.*`

In particular the launcher remains:

`jp.co.ponos.battlecats.MyActivity`

This matters because `libnative-lib.so` exports JNI symbols with that exact
class namespace.  Renaming the Java class package would break the preservation
contract and likely JNI binding.

## Pipeline

```bash
python -m tools.base_mod.package_flavor private/jp-15.7.1/splits \
  --flavor personal \
  --output private/jp-15.7.1/personal-unsigned

python -m tools.base_mod.repack private/jp-15.7.1/personal-unsigned \
  --output private/jp-15.7.1/personal-signed \
  --keystore private/kneekura.p12 \
  --alias kneekura \
  --storepass YOUR_LOCAL_PASSWORD
```

Use `--flavor practice` for the clean-progression package.

The package patch emits `package-patch-ledger.json`.  The signing pass emits
`patch-ledger.json`.

## Fail-closed rules

- incomplete six-split input -> fail;
- non-equal-length package id -> fail;
- expected package/authority strings missing -> fail;
- original `MyActivity` class string missing -> fail;
- accidental flavor-package `MyActivity` class string -> fail;
- exact plain-package DEX string count not equal to one -> fail;
- signer mismatch between splits -> fail.

This is a version-pinned JP 15.7.1 patch, not a generic search-and-replace tool.