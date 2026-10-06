"""Static audit for the disposable Phase-C research trace split set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile

from tools.base_mod.package_flavor import (
    FLAVOR_PACKAGES,
    LAUNCHER_CLASS,
)
from tools.base_mod.verify_parity import (
    _lief_binary,
    _split_diff,
)
from tools.base_mod.inject_shim import (
    NATIVE_ENTRY,
    SHIM_ENTRY,
    SHIM_SONAME,
)
from tools.base_mod.inject_research_gadget import (
    GADGET_CONFIG_ENTRY,
    GADGET_ENTRY,
    GADGET_SONAME,
    TRACE_SCRIPT_ENTRY,
)
from tools.base_mod.binary_axml import string_values


RESEARCH_FLAVOR = "research"


def verify_research_trace_set(
    original_dir: Path,
    modified_dir: Path,
) -> dict:
    package_name = FLAVOR_PACKAGES[RESEARCH_FLAVOR]
    split_names = [
        "base.apk",
        "split_config.arm64_v8a.apk",
        "split_config.en.apk",
        "split_config.ja.apk",
        "split_config.xxhdpi.apk",
        "split_InstallPack.apk",
    ]

    reports: list[dict] = []
    for name in split_names:
        original = original_dir / name
        modified = modified_dir / name
        if not original.is_file() or not modified.is_file():
            raise FileNotFoundError(f"missing split for research audit: {name}")
        diff = _split_diff(original, modified)

        if diff["removed"]:
            raise ValueError(
                f"{name}: research build removed original entries: {diff['removed']}"
            )

        if name == "base.apk":
            changed = set(diff["changed"])
            dex = [
                item
                for item in changed
                if item.startswith("classes") and item.endswith(".dex")
            ]
            expected = {"AndroidManifest.xml", "resources.arsc", *dex}
            if len(dex) != 1 or changed != expected or diff["added"]:
                raise ValueError(
                    f"research base.apk surface drifted: diff={diff}"
                )
        elif name == "split_config.arm64_v8a.apk":
            expected_changed = {"AndroidManifest.xml", NATIVE_ENTRY}
            expected_added = sorted(
                [
                    SHIM_ENTRY,
                    GADGET_ENTRY,
                    GADGET_CONFIG_ENTRY,
                    TRACE_SCRIPT_ENTRY,
                ]
            )
            if set(diff["changed"]) != expected_changed:
                raise ValueError(
                    f"research arm64 changed surface drifted: {diff['changed']}"
                )
            if sorted(diff["added"]) != expected_added:
                raise ValueError(
                    f"research arm64 added surface drifted: {diff['added']}"
                )
        else:
            if set(diff["changed"]) != {"AndroidManifest.xml"} or diff["added"]:
                raise ValueError(
                    f"{name}: only package manifest may differ in research build"
                )

        reports.append({"name": name, **diff})

    with zipfile.ZipFile(modified_dir / "base.apk", "r") as base:
        values = string_values(base.read("AndroidManifest.xml"))
        if package_name not in values:
            raise ValueError("research package missing from base manifest")
        if LAUNCHER_CLASS not in values:
            raise ValueError("original Battle Cats launcher disappeared")
        if package_name + ".MyActivity" in values:
            raise ValueError("research package accidentally renamed Java launcher")
        if "jp.kneekura.whitenyankocats.MainActivity" in values:
            raise ValueError("verification-harness Activity leaked into research APK")

    with zipfile.ZipFile(
        original_dir / "split_config.arm64_v8a.apk", "r"
    ) as original_arm, zipfile.ZipFile(
        modified_dir / "split_config.arm64_v8a.apk", "r"
    ) as research_arm:
        original_native = original_arm.read(NATIVE_ENTRY)
        research_native = research_arm.read(NATIVE_ENTRY)
        trace_script = research_arm.read(TRACE_SCRIPT_ENTRY)
        config = research_arm.read(GADGET_CONFIG_ENTRY)

    before_elf = _lief_binary(original_native, "original.so")
    after_elf = _lief_binary(research_native, "research.so")
    if set(before_elf["exports"]) != set(after_elf["exports"]):
        raise ValueError("research build changed original libnative export surface")
    if SHIM_SONAME not in after_elf["libraries"]:
        raise ValueError("research libnative missing Kneekura shim dependency")
    if GADGET_SONAME not in after_elf["libraries"]:
        raise ValueError("research libnative missing Frida Gadget dependency")

    if b"KNEEKURA_TRACE " not in trace_script:
        raise ValueError("research trace script marker missing")
    if b"libbc_script.js.so" not in config:
        raise ValueError("research gadget config does not point at trace script")

    installpack = next(
        row for row in reports if row["name"] == "split_InstallPack.apk"
    )
    if installpack["changed"] != ["AndroidManifest.xml"]:
        raise ValueError("research build changed InstallPack game payload")

    return {
        "schema_version": 1,
        "flavor": RESEARCH_FLAVOR,
        "package": package_name,
        "research_only": True,
        "launcher": LAUNCHER_CLASS,
        "original_scene_host_preserved": True,
        "verification_harness_ui_absent": True,
        "libnative_export_surface_preserved": True,
        "kneekura_shim_dependency_present": True,
        "frida_gadget_dependency_present": True,
        "installpack_game_payload_preserved": True,
        "trace_script_present": True,
        "split_diffs": reports,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_dir", type=Path)
    parser.add_argument("modified_dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = verify_research_trace_set(
        args.original_dir.resolve(),
        args.modified_dir.resolve(),
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
