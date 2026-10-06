"""Build one base-preserving JP 15.7.1 boot-smoke split set from an owned export.

This orchestrator never downloads Battle Cats.  The caller supplies the exact owned
export ZIP and a locally controlled signing key.  It wires together the already
version-pinned extraction, inert bootstrap injection, package flavor patch,
split signing and static parity audit.

Original APK bytes are not stored in this repository.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

from tools.base_mod.extract_owned_splits import (
    EXPECTED_EXPORT_SHA256,
    extract_owned_splits,
)
from tools.base_mod.inject_shim import inject_shim
from tools.base_mod.package_flavor import FLAVOR_PACKAGES, LAUNCHER_CLASS, apply_flavor
from tools.base_mod.repack import baseline_resign
from tools.base_mod.verify_parity import verify_split_set


def build_owned_boot_smoke(
    export_zip: Path,
    *,
    flavor: str,
    shim: Path,
    keystore: Path,
    alias: str,
    storepass: str,
    output_dir: Path,
    keypass: str | None = None,
    zipalign: str | None = None,
    apksigner: str | None = None,
) -> dict:
    if flavor not in FLAVOR_PACKAGES:
        raise ValueError(f"unknown flavor: {flavor}")
    export_zip = export_zip.resolve()
    shim = shim.resolve()
    keystore = keystore.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    work = output_dir / ".work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    original = work / "original-splits"
    bootstrap = work / "bootstrap-splits"
    flavored = work / "flavored-splits"
    signed = output_dir / f"{flavor}-signed-splits"
    if signed.exists():
        shutil.rmtree(signed)

    source_ledger = extract_owned_splits(export_zip, original)
    bootstrap_ledger = inject_shim(original, shim=shim, output_dir=bootstrap)
    flavor_ledger = apply_flavor(bootstrap, flavor=flavor, output_dir=flavored)
    signing_ledger = baseline_resign(
        flavored,
        signed,
        keystore=keystore,
        alias=alias,
        storepass=storepass,
        keypass=keypass,
        zipalign=zipalign,
        apksigner=apksigner,
        source_export_sha256=EXPECTED_EXPORT_SHA256,
    )
    parity = verify_split_set(original, signed, flavor=flavor)

    (signed / "source-split-ledger.json").write_text(
        json.dumps(source_ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (signed / "bootstrap-patch-ledger.json").write_text(
        json.dumps(bootstrap_ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (signed / "package-patch-ledger.json").write_text(
        json.dumps(flavor_ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (signed / "parity-report.json").write_text(
        json.dumps(parity, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    package_name = FLAVOR_PACKAGES[flavor]
    instructions = f"""Kneekura JP 15.7.1 base-preserving boot smoke

Flavor: {flavor}
Package: {package_name}
Launcher class: {LAUNCHER_CLASS}

Install every APK in this directory together:
  adb install-multiple -r *.apk

Launch the original Battle Cats activity:
  adb shell am start -n {package_name}/{LAUNCHER_CLASS}

Required smoke checks:
1. Original Battle Cats boot/logo/base screen appears.
2. No Kneekura verification-harness screen appears.
3. Navigate original base, unit and stage screens.
4. Enter one original stage and return.
5. Enable airplane mode, kill the app, relaunch, and repeat navigation.
6. If anything fails, capture:
   adb logcat -d > kneekura-smoke-logcat.txt

This Phase-A shim has feature mask 0.  No Super Kneekura Gacha, login bonus,
MAX profile or custom stage reward is expected yet.
"""
    (signed / "INSTALL-SMOKE.txt").write_text(instructions, encoding="utf-8")

    shutil.rmtree(work)
    return {
        "schema_version": 1,
        "flavor": flavor,
        "package": package_name,
        "launcher": LAUNCHER_CLASS,
        "source_export_sha256": EXPECTED_EXPORT_SHA256,
        "signed_split_dir": str(signed),
        "signer_certificate_sha256": signing_ledger[
            "signer_certificate_sha256"
        ],
        "static_parity": parity,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export_zip", type=Path)
    parser.add_argument("--flavor", choices=sorted(FLAVOR_PACKAGES), required=True)
    parser.add_argument("--shim", required=True, type=Path)
    parser.add_argument("--keystore", required=True, type=Path)
    parser.add_argument("--alias", required=True)
    parser.add_argument("--storepass", required=True)
    parser.add_argument("--keypass")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--zipalign")
    parser.add_argument("--apksigner")
    args = parser.parse_args()

    result = build_owned_boot_smoke(
        args.export_zip,
        flavor=args.flavor,
        shim=args.shim,
        keystore=args.keystore,
        alias=args.alias,
        storepass=args.storepass,
        keypass=args.keypass,
        output_dir=args.output,
        zipalign=args.zipalign,
        apksigner=args.apksigner,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())