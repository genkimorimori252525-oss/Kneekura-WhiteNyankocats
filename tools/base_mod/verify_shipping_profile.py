"""Audit final Personal/Practice shipping-profile preservation.

This verifier consumes a locally built signed split directory from
build_owned_boot_smoke.py. It does not require the owned source APK bytes
because the directory already contains the exact-source parity and patch
ledgers produced during that build.

The audit fails closed if any research/Frida payload, flavor MyActivity bridge,
custom verification UI, or enabled Kneekura feature mask leaks into the
feature-OFF shipping profiles.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile

from tools.base_mod.binary_axml import patch_boolean_attribute, string_values
from tools.base_mod.package_flavor import FLAVOR_PACKAGES, LAUNCHER_CLASS


FORBIDDEN_ENTRY_TOKENS = (
    "frida",
    "libbc_script",
    "trace_service_bridge",
    "replay_backup_offline",
)

FORBIDDEN_BINARY_MARKERS = (
    b"KNEEKURA_TRACE",
    b"KNEEKURA_REPLAY",
    b"KNEEKURA_STATIC_HTTP",
    b"frida-java-bridge",
    b"libfrida-gadget",
)


def _read_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _apk_names(split_dir: Path) -> list[Path]:
    paths = sorted(split_dir.glob("*.apk"))
    if len(paths) != 6:
        raise ValueError(f"expected six signed split APKs, got {len(paths)}")
    return paths


def verify_shipping_profile(split_dir: Path, *, flavor: str) -> dict:
    if flavor not in {"personal", "practice"}:
        raise ValueError("shipping profile audit accepts personal/practice only")

    package_name = FLAVOR_PACKAGES[flavor]
    split_dir = split_dir.resolve()

    parity = _read_json(split_dir / "parity-report.json")
    bootstrap = _read_json(split_dir / "bootstrap-patch-ledger.json")
    package = _read_json(split_dir / "package-patch-ledger.json")

    if parity.get("flavor") != flavor:
        raise ValueError("parity report flavor mismatch")
    if parity.get("package") != package_name:
        raise ValueError("parity report package mismatch")
    for key in (
        "original_scene_host_preserved",
        "verification_harness_ui_absent",
        "libnative_export_surface_preserved",
        "shim_dependency_present",
        "installpack_game_payload_preserved",
    ):
        if parity.get(key) is not True:
            raise ValueError(f"shipping parity gate failed: {key}")

    arm64 = bootstrap.get("arm64", {})
    if arm64.get("feature_mask_default") != 0:
        raise ValueError("shipping shim feature mask is not zero")
    if arm64.get("extension_off_fallthrough") is not True:
        raise ValueError("shipping shim extension-off fallthrough is not pinned")

    if package.get("flavor") != flavor:
        raise ValueError("package ledger flavor mismatch")
    if package.get("package") != package_name:
        raise ValueError("package ledger package mismatch")
    if package.get("launcher_class_preserved") != LAUNCHER_CLASS:
        raise ValueError("original launcher was not preserved")
    if package.get("research_extract_native_libs") is not False:
        raise ValueError("research native extraction leaked into shipping profile")

    scanned_entries = 0
    scanned_marker_payloads = 0
    for apk in _apk_names(split_dir):
        with zipfile.ZipFile(apk, "r") as archive:
            for name in archive.namelist():
                lower = name.lower()
                if any(token in lower for token in FORBIDDEN_ENTRY_TOKENS):
                    raise ValueError(
                        f"research/Frida entry leaked into {apk.name}: {name}"
                    )
                scanned_entries += 1

            if apk.name == "base.apk":
                manifest = archive.read("AndroidManifest.xml")
                values = string_values(manifest)
                if LAUNCHER_CLASS not in values:
                    raise ValueError("original MyActivity launcher missing")
                flavor_launcher = package_name + ".MyActivity"
                if flavor_launcher in values:
                    raise ValueError("static research bridge launcher leaked into shipping")
                if "jp.kneekura.whitenyankocats.MainActivity" in values:
                    raise ValueError("verification harness Activity leaked into shipping")

                same, count = patch_boolean_attribute(
                    manifest,
                    element_name="application",
                    attribute_name="extractNativeLibs",
                    expected=False,
                    replacement=False,
                )
                if count != 1 or same != manifest:
                    raise ValueError("extractNativeLibs=false preservation drift")

                if "classes5.dex" in archive.namelist():
                    raise ValueError("research/static bridge classes5.dex leaked into shipping")

                for name in archive.namelist():
                    if name.startswith("classes") and name.endswith(".dex"):
                        payload = archive.read(name)
                        for marker in FORBIDDEN_BINARY_MARKERS:
                            if marker in payload:
                                raise ValueError(
                                    f"research marker {marker!r} leaked into {apk.name}/{name}"
                                )
                        scanned_marker_payloads += 1

            if apk.name == "split_config.arm64_v8a.apk":
                for name in (
                    "lib/arm64-v8a/libnative-lib.so",
                    "lib/arm64-v8a/libkneekura.so",
                ):
                    payload = archive.read(name)
                    for marker in FORBIDDEN_BINARY_MARKERS:
                        if marker in payload:
                            raise ValueError(
                                f"research marker {marker!r} leaked into {apk.name}/{name}"
                            )
                    scanned_marker_payloads += 1

    return {
        "schema_version": 1,
        "mode": "shipping-profile-parity",
        "flavor": flavor,
        "package": package_name,
        "original_launcher_preserved": True,
        "original_scene_host_preserved": True,
        "verification_harness_ui_absent": True,
        "feature_mask_default": 0,
        "extension_off_fallthrough": True,
        "extract_native_libs_preserved_false": True,
        "classes5_research_bridge_absent": True,
        "frida_gadget_absent": True,
        "research_trace_markers_absent": True,
        "installpack_game_payload_preserved": True,
        "signed_split_count": 6,
        "scanned_zip_entries": scanned_entries,
        "scanned_binary_payloads": scanned_marker_payloads,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("split_dir", type=Path)
    parser.add_argument(
        "--flavor",
        required=True,
        choices=["personal", "practice"],
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = verify_shipping_profile(
        args.split_dir,
        flavor=args.flavor,
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
