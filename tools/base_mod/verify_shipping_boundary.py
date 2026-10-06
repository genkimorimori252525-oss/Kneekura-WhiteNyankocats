"""Audit the product/research boundary for Kneekura JP 15.7.1.

This verifier has two modes:

1. repository policy audit:
   proves Personal/Practice builders do not depend on the research Frida path
   and that research-only logging/injection remains isolated.

2. signed split audit:
   scans a built Personal/Practice split set for forbidden research payloads,
   validates package/launcher shape, and verifies the Kneekura shim does not
   depend on Frida/Gadget.

It never modifies an APK.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile

from tools.base_mod.binary_axml import string_values
from tools.base_mod.inject_java_http_bridge import BRIDGE_DEX_ENTRY
from tools.base_mod.inject_research_gadget import (
    GADGET_CONFIG_ENTRY,
    GADGET_ENTRY,
    TRACE_SCRIPT_ENTRY,
)
from tools.base_mod.inject_shim import SHIM_ENTRY
from tools.base_mod.package_flavor import (
    FLAVOR_PACKAGES,
    LAUNCHER_CLASS,
)
from tools.base_mod.repack import JP_15_7_1_SPLITS
from tools.base_mod.verify_parity import _lief_binary


PRODUCT_FLAVORS = ("personal", "practice")
RESEARCH_PACKAGE = FLAVOR_PACKAGES["research"]

FORBIDDEN_ENTRY_NAMES = {
    GADGET_ENTRY,
    GADGET_CONFIG_ENTRY,
    TRACE_SCRIPT_ENTRY,
}
FORBIDDEN_PRODUCT_SOURCE_TOKENS = (
    "inject_research_gadget",
    "libfrida-gadget",
    "frida-java-bridge",
    "TRACE_SCRIPT_ENTRY",
    "GADGET_CONFIG_ENTRY",
)
FORBIDDEN_BINARY_MARKERS = (
    b"libfrida-gadget",
    b"libbc_script.js.so",
    b"frida-java-bridge",
    b"jp.kn.trace.battlecats",
)


def audit_repository(root: Path) -> dict:
    root = root.resolve()
    failures: list[str] = []

    shipping_sources = {
        "boot": root / "tools/base_mod/build_owned_boot_smoke.py",
        "static_http": root / "tools/base_mod/build_owned_static_http_bridge.py",
        "gacha_ui": root / "tools/base_mod/build_owned_gacha_ui_proof.py",
    }
    for label, path in shipping_sources.items():
        if not path.is_file():
            failures.append(f"missing shipping builder: {path}")
            continue
        source = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_PRODUCT_SOURCE_TOKENS:
            if token in source:
                failures.append(
                    f"{label} shipping builder references research token {token}"
                )

    research_builder = (
        root / "tools/base_mod/build_owned_research_trace.py"
    ).read_text(encoding="utf-8")
    if "inject_research_gadget" not in research_builder:
        failures.append("research builder lost explicit Gadget injection")
    if 'RESEARCH_FLAVOR = "research"' not in research_builder:
        failures.append("research builder flavor isolation drift")

    injector = (
        root / "tools/base_mod/inject_java_http_bridge.py"
    ).read_text(encoding="utf-8")
    if '"true" if flavor == "research" else "false"' not in injector:
        failures.append("static bridge research-log flavor gate drift")

    template = (
        root / "bridge/java/MyActivity.java.in"
    ).read_text(encoding="utf-8")
    if "__KNEEKURA_DEBUG_LOG__" not in template:
        failures.append("static bridge debug placeholder missing")
    if "DEBUG_RESEARCH_LOG" not in template:
        failures.append("static bridge research log gate missing")
    if template.count("super.newHttpRequest(") < 2:
        failures.append("static bridge exact-original fall-through drift")

    package_flavor = (
        root / "tools/base_mod/package_flavor.py"
    ).read_text(encoding="utf-8")
    for flavor in PRODUCT_FLAVORS:
        package = FLAVOR_PACKAGES[flavor]
        if package not in package_flavor:
            failures.append(f"{flavor} package id missing")
        if package == RESEARCH_PACKAGE:
            failures.append(f"{flavor} package aliases research package")

    if failures:
        raise ValueError(
            "shipping boundary repository audit failed: " + "; ".join(failures)
        )

    return {
        "schema_version": 1,
        "mode": "shipping-boundary-repository-audit",
        "product_flavors": list(PRODUCT_FLAVORS),
        "research_package": RESEARCH_PACKAGE,
        "shipping_builders_reference_frida": False,
        "research_gadget_path_isolated": True,
        "research_log_compiled_only_for_research": True,
        "original_http_fallthrough_required": True,
    }


def _scan_apk_forbidden_markers(apk: Path) -> list[dict]:
    findings: list[dict] = []
    with zipfile.ZipFile(apk, "r") as archive:
        names = archive.namelist()
        for name in names:
            if name in FORBIDDEN_ENTRY_NAMES:
                findings.append({"entry": name, "reason": "research payload entry"})
            lowered = name.lower()
            if "frida" in lowered or "libbc_script" in lowered:
                findings.append({"entry": name, "reason": "research marker in entry name"})

        # Scan only executable/configuration surfaces. Large game assets are
        # irrelevant to the research-runtime boundary and need not be inflated.
        scan_names = [
            name
            for name in names
            if (
                name == "AndroidManifest.xml"
                or (name.startswith("classes") and name.endswith(".dex"))
                or name.startswith("lib/")
            )
        ]
        for name in scan_names:
            payload = archive.read(name)
            lower = payload.lower()
            for marker in FORBIDDEN_BINARY_MARKERS:
                if marker.lower() in lower:
                    findings.append(
                        {
                            "entry": name,
                            "reason": f"research marker {marker.decode('ascii', 'replace')}",
                        }
                    )
    return findings


def audit_signed_split_set(
    split_dir: Path,
    *,
    flavor: str,
    expect_static_bridge: bool,
) -> dict:
    if flavor not in PRODUCT_FLAVORS:
        raise ValueError(
            f"shipping artifact audit accepts only {PRODUCT_FLAVORS}, got {flavor!r}"
        )

    split_dir = split_dir.resolve()
    missing = [
        name for name in JP_15_7_1_SPLITS if not (split_dir / name).is_file()
    ]
    if missing:
        raise FileNotFoundError(
            "incomplete shipping split set: " + ", ".join(missing)
        )

    package = FLAVOR_PACKAGES[flavor]
    expected_launcher = (
        package + ".MyActivity"
        if expect_static_bridge
        else LAUNCHER_CLASS
    )

    findings: list[dict] = []
    for split_name in JP_15_7_1_SPLITS:
        findings.extend(
            {
                "split": split_name,
                **row,
            }
            for row in _scan_apk_forbidden_markers(split_dir / split_name)
        )
    if findings:
        raise ValueError(
            "shipping artifact contains research markers: "
            + json.dumps(findings, ensure_ascii=False)
        )

    with zipfile.ZipFile(split_dir / "base.apk", "r") as base:
        values = string_values(base.read("AndroidManifest.xml"))
        names = set(base.namelist())
        if package not in values:
            raise ValueError("product package missing from base manifest")
        if RESEARCH_PACKAGE in values:
            raise ValueError("research package leaked into product manifest")
        if expected_launcher not in values:
            raise ValueError(
                f"expected launcher {expected_launcher!r} missing from manifest"
            )
        if expect_static_bridge:
            if BRIDGE_DEX_ENTRY not in names:
                raise ValueError("static product bridge classes5.dex missing")
        elif BRIDGE_DEX_ENTRY in names:
            raise ValueError("feature-off boot artifact unexpectedly contains bridge dex")

    with zipfile.ZipFile(
        split_dir / "split_config.arm64_v8a.apk", "r"
    ) as arm:
        if SHIM_ENTRY not in arm.namelist():
            raise ValueError("Kneekura shim missing from product arm64 split")
        shim_bytes = arm.read(SHIM_ENTRY)

    shim = _lief_binary(shim_bytes, "libkneekura.so")
    research_libs = [
        name
        for name in shim.get("libraries", [])
        if "frida" in name.lower() or "gadget" in name.lower()
    ]
    if research_libs:
        raise ValueError(
            "product Kneekura shim depends on research library: "
            + ", ".join(research_libs)
        )

    return {
        "schema_version": 1,
        "mode": "shipping-boundary-artifact-audit",
        "flavor": flavor,
        "package": package,
        "launcher": expected_launcher,
        "static_bridge_expected": expect_static_bridge,
        "frida_payload_entries_present": False,
        "research_package_present": False,
        "shim_research_dependencies": [],
        "split_count": len(JP_15_7_1_SPLITS),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--split-dir", type=Path)
    parser.add_argument("--flavor", choices=PRODUCT_FLAVORS)
    parser.add_argument("--expect-static-bridge", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report: dict = {
        "repository": audit_repository(args.root),
    }
    if args.split_dir is not None:
        if args.flavor is None:
            parser.error("--flavor is required with --split-dir")
        report["artifact"] = audit_signed_split_set(
            args.split_dir,
            flavor=args.flavor,
            expect_static_bridge=args.expect_static_bridge,
        )

    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
