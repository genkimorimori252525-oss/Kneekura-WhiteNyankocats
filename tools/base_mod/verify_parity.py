"""Static preservation audit for a signed Kneekura split set."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

from tools.base_mod.binary_axml import string_values
from tools.base_mod.inject_shim import NATIVE_ENTRY, SHIM_ENTRY, SHIM_SONAME
from tools.base_mod.package_flavor import (
    FLAVOR_PACKAGES,
    LAUNCHER_CLASS,
    ORIGINAL_PACKAGE,
)


def _import_lief():
    try:
        import lief  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "LIEF is required; install requirements-patching.txt"
        ) from exc
    return lief


_SIGNING_METADATA_ENTRIES = {
    "stamp-cert-sha256",
    "pinlist.meta",
}


def _is_signature_entry(name: str) -> bool:
    if name in _SIGNING_METADATA_ENTRIES:
        return True

    upper = name.upper()
    if not upper.startswith("META-INF/"):
        return False
    leaf = upper.rsplit("/", 1)[-1]
    return (
        leaf == "MANIFEST.MF"
        or leaf.endswith(".SF")
        or leaf.endswith(".RSA")
        or leaf.endswith(".DSA")
        or leaf.endswith(".EC")
    )


def _entry_hashes(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    with zipfile.ZipFile(path, "r") as archive:
        for info in archive.infolist():
            if info.is_dir() or _is_signature_entry(info.filename):
                continue
            result[info.filename] = hashlib.sha256(
                archive.read(info)
            ).hexdigest()
    return result


def _split_diff(original: Path, modified: Path) -> dict:
    before = _entry_hashes(original)
    after = _entry_hashes(modified)
    before_names = set(before)
    after_names = set(after)
    added = sorted(after_names - before_names)
    removed = sorted(before_names - after_names)
    changed = sorted(
        name
        for name in before_names & after_names
        if before[name] != after[name]
    )
    return {"added": added, "removed": removed, "changed": changed}


def _verify_allowed_diff(name: str, diff: dict) -> None:
    if diff["removed"]:
        raise ValueError(f"{name}: unexpected removed entries: {diff['removed']}")

    if name == "base.apk":
        changed = set(diff["changed"])
        if "AndroidManifest.xml" not in changed:
            raise ValueError("base.apk manifest did not change package")
        if "resources.arsc" not in changed:
            raise ValueError("base.apk resources.arsc package did not change")
        dex = [item for item in changed if item.startswith("classes") and item.endswith(".dex")]
        if len(dex) != 1:
            raise ValueError(
                f"base.apk expects exactly one changed DEX, got {dex}"
            )
        allowed = {"AndroidManifest.xml", "resources.arsc", dex[0]}
        if changed != allowed or diff["added"]:
            raise ValueError(
                f"base.apk change surface drifted: changed={sorted(changed)} "
                f"added={diff['added']}"
            )
        return

    if name == "split_config.arm64_v8a.apk":
        expected_changed = {"AndroidManifest.xml", NATIVE_ENTRY}
        if set(diff["changed"]) != expected_changed:
            raise ValueError(
                f"arm64 split changed entries drifted: {diff['changed']}"
            )
        if diff["added"] != [SHIM_ENTRY]:
            raise ValueError(
                f"arm64 split added entries drifted: {diff['added']}"
            )
        return

    if set(diff["changed"]) != {"AndroidManifest.xml"} or diff["added"]:
        raise ValueError(
            f"{name}: only AndroidManifest.xml may change; diff={diff}"
        )


def _lief_binary(data: bytes, name: str):
    lief = _import_lief()
    with tempfile.TemporaryDirectory(prefix="kneekura-parity-") as temp_name:
        path = Path(temp_name) / name
        path.write_bytes(data)
        binary = lief.parse(str(path))
        if binary is None:
            raise ValueError(f"LIEF could not parse {name}")
        # Return only stable copies, not the temporary binary object.
        return {
            "libraries": list(binary.libraries),
            "exports": sorted(
                {
                    getattr(function, "name", "")
                    for function in binary.exported_functions
                    if getattr(function, "name", "")
                }
            ),
        }


def verify_split_set(
    original_dir: Path,
    modified_dir: Path,
    *,
    flavor: str,
) -> dict:
    package_name = FLAVOR_PACKAGES.get(flavor)
    if package_name is None:
        raise ValueError(f"unknown flavor: {flavor}")

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
            raise FileNotFoundError(f"missing split for parity audit: {name}")
        diff = _split_diff(original, modified)
        _verify_allowed_diff(name, diff)
        reports.append({"name": name, **diff})

    with zipfile.ZipFile(modified_dir / "base.apk", "r") as base:
        manifest = base.read("AndroidManifest.xml")
        values = string_values(manifest)
        if package_name not in values:
            raise ValueError("final base manifest does not contain flavor package")
        if LAUNCHER_CLASS not in values:
            raise ValueError("original Battle Cats MyActivity launcher disappeared")
        if package_name + ".MyActivity" in values:
            raise ValueError("launcher class namespace was renamed")
        if "jp.kneekura.whitenyankocats.MainActivity" in values:
            raise ValueError("verification-harness Activity leaked into product APK")

        resources = base.read("resources.arsc")
        if ORIGINAL_PACKAGE.encode() in resources:
            raise ValueError("original application id remains in resources.arsc")
        if package_name.encode() not in resources:
            raise ValueError("flavor application id missing from resources.arsc")

    with zipfile.ZipFile(
        original_dir / "split_config.arm64_v8a.apk", "r"
    ) as original_arm, zipfile.ZipFile(
        modified_dir / "split_config.arm64_v8a.apk", "r"
    ) as modified_arm:
        original_native = original_arm.read(NATIVE_ENTRY)
        final_native = modified_arm.read(NATIVE_ENTRY)
        final_shim = modified_arm.read(SHIM_ENTRY)

    before_elf = _lief_binary(original_native, "original.so")
    after_elf = _lief_binary(final_native, "patched.so")
    shim_elf = _lief_binary(final_shim, "libkneekura.so")

    if set(before_elf["exports"]) != set(after_elf["exports"]):
        raise ValueError("original libnative exported-function surface changed")
    if SHIM_SONAME not in after_elf["libraries"]:
        raise ValueError("final libnative does not depend on libkneekura.so")
    if ORIGINAL_PACKAGE.encode() in final_native:
        raise ValueError("old dotted package id remains in final libnative")
    if package_name.encode() not in final_native:
        raise ValueError("flavor dotted package id missing from final libnative")

    required_shim_exports = {
        "kneekura_shim_abi_version",
        "kneekura_bootstrap_initialized",
        "kneekura_feature_mask",
        "kneekura_feature_enabled",
        "kneekura_target_native_sha256",
    }
    if not required_shim_exports.issubset(set(shim_elf["exports"])):
        raise ValueError("final shim export contract is incomplete")

    installpack_report = next(
        row for row in reports if row["name"] == "split_InstallPack.apk"
    )
    if installpack_report["changed"] != ["AndroidManifest.xml"]:
        raise ValueError("InstallPack game payload changed unexpectedly")

    report = {
        "schema_version": 1,
        "flavor": flavor,
        "package": package_name,
        "launcher": LAUNCHER_CLASS,
        "original_scene_host_preserved": True,
        "verification_harness_ui_absent": True,
        "libnative_export_surface_preserved": True,
        "shim_dependency_present": True,
        "installpack_game_payload_preserved": True,
        "split_diffs": reports,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_dir", type=Path)
    parser.add_argument("modified_dir", type=Path)
    parser.add_argument("--flavor", required=True, choices=sorted(FLAVOR_PACKAGES))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = verify_split_set(
        args.original_dir.resolve(),
        args.modified_dir.resolve(),
        flavor=args.flavor,
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())