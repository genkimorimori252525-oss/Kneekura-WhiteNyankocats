"""Build an owner-local disposable JP 15.7.1 research trace split set.

This builder produces the isolated research package only.  It never downloads
or publishes Battle Cats or Frida Gadget bytes; both are explicit local inputs.
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
from tools.base_mod.inject_shim import patch_split_set as inject_kneekura_shim
from tools.base_mod.inject_research_gadget import inject_research_split_set
from tools.base_mod.package_flavor import patch_split_set as apply_package_flavor, FLAVOR_PACKAGES, LAUNCHER_CLASS
from tools.base_mod.repack import baseline_resign
from tools.base_mod.verify_research_trace import verify_research_trace_set


RESEARCH_FLAVOR = "research"


def build_owned_research_trace(
    export_zip: Path,
    *,
    kneekura_shim: Path,
    frida_gadget: Path,
    trace_script: Path,
    keystore: Path,
    alias: str,
    storepass: str,
    output_dir: Path,
    keypass: str | None = None,
    zipalign: str | None = None,
    apksigner: str | None = None,
) -> dict:
    export_zip = export_zip.resolve()
    kneekura_shim = kneekura_shim.resolve()
    frida_gadget = frida_gadget.resolve()
    trace_script = trace_script.resolve()
    keystore = keystore.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    work = output_dir / ".research-work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    original = work / "original-splits"
    bootstrap = work / "bootstrap-splits"
    traced = work / "research-injected-splits"
    flavored = work / "research-flavored-splits"
    signed = output_dir / "research-signed-splits"
    if signed.exists():
        shutil.rmtree(signed)

    source_ledger = extract_owned_splits(export_zip, original)
    bootstrap_ledger = inject_kneekura_shim(
        original,
        bootstrap,
        kneekura_shim,
    )
    research_ledger = inject_research_split_set(
        bootstrap,
        traced,
        gadget_path=frida_gadget,
        trace_script_path=trace_script,
    )
    flavor_ledger = apply_package_flavor(
        traced,
        flavored,
        flavor=RESEARCH_FLAVOR,
    )
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
    parity = verify_research_trace_set(original, signed)

    ledger_files = {
        "source-split-ledger.json": source_ledger,
        "bootstrap-patch-ledger.json": bootstrap_ledger,
        "research-patch-ledger.json": research_ledger,
        "package-patch-ledger.json": flavor_ledger,
        "parity-report.json": parity,
    }
    for file_name, payload in ledger_files.items():
        (signed / file_name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    package_name = FLAVOR_PACKAGES[RESEARCH_FLAVOR]
    instructions = f"""Kneekura Phase-C disposable research trace build

Package: {package_name}
Launcher: {LAUNCHER_CLASS}
Source export SHA-256: {EXPECTED_EXPORT_SHA256}

This build is RESEARCH ONLY.  Do not use it as Personal MAX or Practice Clean.

Install all split APKs together:
  adb install-multiple -r *.apk

Launch the original Battle Cats activity:
  adb shell am start -n {package_name}/{LAUNCHER_CLASS}

Expected Frida behavior:
  - libfrida-gadget.so loads from the ARM64 split
  - libfrida-gadget.config.so loads libbc_script.js.so
  - the script calls all observed methods through unchanged
  - sanitized metadata lines begin with:
      KNEEKURA_TRACE

Capture:
  adb logcat -c
  # launch/navigate one low-risk network action
  adb logcat -d | grep 'KNEEKURA_TRACE' > kneekura-trace.log

Summarize:
  python -m tools.base_mod.summarize_service_trace \
    kneekura-trace.log --output kneekura-trace-summary.json

Then repeat once in airplane mode.

Do not promote a hook from this trace until:
  1. original UI/scene behavior is unchanged,
  2. request and response lifecycle is observed,
  3. failure/unrecognized fallback is known,
  4. exact JP 15.7.1 patch ledger entry can be written.
"""
    (signed / "TRACE-INSTRUCTIONS.txt").write_text(instructions, encoding="utf-8")

    shutil.rmtree(work)
    return {
        "schema_version": 1,
        "mode": "owner-local-research-trace",
        "package": package_name,
        "launcher": LAUNCHER_CLASS,
        "signed_split_dir": str(signed),
        "signer_certificate_sha256": signing_ledger[
            "signer_certificate_sha256"
        ],
        "static_research_parity": parity,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export_zip", type=Path)
    parser.add_argument("--shim", required=True, type=Path)
    parser.add_argument("--frida-gadget", required=True, type=Path)
    parser.add_argument(
        "--trace-script",
        type=Path,
        default=Path("research/frida/trace_service_bridge.bundle.js"),
    )
    parser.add_argument("--keystore", required=True, type=Path)
    parser.add_argument("--alias", required=True)
    parser.add_argument("--storepass", required=True)
    parser.add_argument("--keypass")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--zipalign")
    parser.add_argument("--apksigner")
    args = parser.parse_args()

    result = build_owned_research_trace(
        args.export_zip,
        kneekura_shim=args.shim,
        frida_gadget=args.frida_gadget,
        trace_script=args.trace_script,
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
