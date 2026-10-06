# Baseline Repack / Sign Contract

This tooling exists to prove the first preservation property before any real mod
feature is injected:

> re-signing/repacking must not silently change Battle Cats payload content.

## Commands

Generate a private local signing key once:

```bash
python -m tools.base_mod.keygen private/kneekura.p12 \
  --storepass YOUR_LOCAL_PASSWORD
```

The keystore and password are local secrets and must never be committed.

Prepare a complete exact JP 15.7.1 split directory and baseline-sign it:

```bash
python -m tools.base_mod.repack private/jp-15.7.1/splits \
  --output private/jp-15.7.1/baseline-signed \
  --keystore private/kneekura.p12 \
  --alias kneekura \
  --storepass YOUR_LOCAL_PASSWORD \
  --source-export-sha256 38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56
```

The tool requires all six exact split names and refuses a partial set. It locates
`zipalign` and `apksigner` from PATH or Android SDK build-tools.

## Content invariant

APK signing and ZIP alignment legitimately change container bytes, so comparing
whole-file hashes before/after would always report a difference.

Instead, the tool computes a content fingerprint over every non-signature ZIP
entry using:

- entry name;
- uncompressed entry length;
- uncompressed entry bytes.

Only standard `META-INF` signing records are excluded.

For baseline mode, every split must have an identical payload fingerprint before
and after. Any payload change fails closed.

The emitted `patch-ledger.json` records:

- anchor/version lane;
- required split set;
- optional source-export digest;
- signer certificate digest;
- input/output file hashes and sizes;
- before/after payload fingerprints;
- content-invariance verdict.

Later feature patchers extend this ledger with an explicit list of intended
changed entries. Baseline mode permits none.