"""Version-pinned package separation patch for JP 15.7.1.

The package identifiers are deliberately the same byte length as the original
application id.  This allows narrowly targeted binary AXML/DEX string changes
without moving string pools or Java class namespaces.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from tools.base_mod.binary_axml import patch_equal_length_strings, string_values
from tools.base_mod.dex_strings import patch_exact_dex_string
from tools.base_mod.repack import (
    JP_15_7_1_SPLITS,
    payload_fingerprint,
    sha256_file,
)


ORIGINAL_PACKAGE = "jp.co.ponos.battlecats"
FLAVOR_PACKAGES = {
    "personal": "jp.kn.white.battlecats",
    "practice": "jp.kn.clean.battlecats",
}

_BASE_SUFFIXES = (
    "",
    ".DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION",
    ".IronsourceLifecycleProvider",
    ".applovininitprovider",
    ".androidx-startup",
    ".AudienceNetworkContentProvider",
    ".mobileadsinitprovider",
    ".firebaseinitprovider",
    ".adjust-lifecycle-provider",
)

LAUNCHER_CLASS = "jp.co.ponos.battlecats.MyActivity"


def _is_signature_entry(name: str) -> bool:
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


def _clone_info(info: zipfile.ZipInfo) -> zipfile.ZipInfo:
    cloned = zipfile.ZipInfo(info.filename, info.date_time)
    cloned.compress_type = info.compress_type
    cloned.comment = info.comment
    cloned.extra = info.extra
    cloned.create_system = info.create_system
    cloned.create_version = info.create_version
    cloned.extract_version = info.extract_version
    cloned.flag_bits = info.flag_bits & ~0x08
    cloned.volume = info.volume
    cloned.internal_attr = info.internal_attr
    cloned.external_attr = info.external_attr
    return cloned


def _rewrite_apk(
    source: Path,
    target: Path,
    replacements: dict[str, bytes],
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source, "r") as src, zipfile.ZipFile(
        target, "w", allowZip64=True
    ) as dst:
        names = {info.filename for info in src.infolist()}
        missing = sorted(set(replacements) - names)
        if missing:
            raise ValueError(
                f"{source.name}: replacement entries missing: {', '.join(missing)}"
            )

        for info in src.infolist():
            if info.is_dir():
                continue
            if _is_signature_entry(info.filename):
                continue
            out_info = _clone_info(info)
            replacement = replacements.get(info.filename)
            if replacement is not None:
                dst.writestr(out_info, replacement)
                continue
            with src.open(info, "r") as reader, dst.open(
                out_info, "w", force_zip64=True
            ) as writer:
                shutil.copyfileobj(reader, writer, 1024 * 1024)


def _patch_manifest(
    manifest: bytes,
    package_name: str,
    *,
    base: bool,
) -> bytes:
    if len(package_name.encode("utf-8")) != len(
        ORIGINAL_PACKAGE.encode("utf-8")
    ):
        raise ValueError("flavor package must preserve original byte length")

    if base:
        mapping = {
            ORIGINAL_PACKAGE + suffix: package_name + suffix
            for suffix in _BASE_SUFFIXES
        }
    else:
        mapping = {ORIGINAL_PACKAGE: package_name}

    patched, _ = patch_equal_length_strings(manifest, mapping)

    values = string_values(patched)
    if package_name not in values:
        raise ValueError("patched manifest does not contain new package")
    if base and LAUNCHER_CLASS not in values:
        raise ValueError("original MyActivity launcher class disappeared")
    if base and package_name + ".MyActivity" in values:
        raise ValueError("Java class namespace was accidentally renamed")
    return patched


def _patch_base_dex(entries: dict[str, bytes], package_name: str) -> tuple[str, bytes]:
    candidates: list[tuple[str, bytes, int]] = []
    for name, payload in entries.items():
        if not name.startswith("classes") or not name.endswith(".dex"):
            continue
        try:
            patched, count = patch_exact_dex_string(
                payload,
                ORIGINAL_PACKAGE,
                package_name,
            )
        except ValueError:
            continue
        if count:
            candidates.append((name, patched, count))

    total = sum(item[2] for item in candidates)
    if total != 1:
        raise ValueError(
            f"JP 15.7.1 anchor expects exactly one plain package DEX string, got {total}"
        )
    name, patched, _ = candidates[0]
    return name, patched


def patch_split_set(
    split_dir: Path,
    output_dir: Path,
    *,
    flavor: str,
) -> dict:
    package_name = FLAVOR_PACKAGES.get(flavor)
    if package_name is None:
        raise ValueError(f"unknown flavor: {flavor!r}")

    if len(package_name) != len(ORIGINAL_PACKAGE):
        raise AssertionError("approved flavor package length drifted")

    missing = [
        name for name in JP_15_7_1_SPLITS if not (split_dir / name).is_file()
    ]
    if missing:
        raise FileNotFoundError(
            "incomplete JP 15.7.1 split set; missing: " + ", ".join(missing)
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    split_rows: list[dict] = []

    for split_name in JP_15_7_1_SPLITS:
        source = split_dir / split_name
        target = output_dir / split_name
        replacements: dict[str, bytes] = {}

        with zipfile.ZipFile(source, "r") as archive:
            manifest = archive.read("AndroidManifest.xml")
            replacements["AndroidManifest.xml"] = _patch_manifest(
                manifest,
                package_name,
                base=split_name == "base.apk",
            )

            if split_name == "base.apk":
                dex_entries = {
                    info.filename: archive.read(info)
                    for info in archive.infolist()
                    if info.filename.startswith("classes")
                    and info.filename.endswith(".dex")
                }
                dex_name, dex_payload = _patch_base_dex(
                    dex_entries, package_name
                )
                replacements[dex_name] = dex_payload

        before = payload_fingerprint(source)
        _rewrite_apk(source, target, replacements)
        after = payload_fingerprint(target)

        split_rows.append(
            {
                "name": split_name,
                "input_sha256": sha256_file(source),
                "output_sha256_unsigned": sha256_file(target),
                "payload_sha256_before": before,
                "payload_sha256_after_unsigned": after,
                "changed_entries": sorted(replacements),
            }
        )

    ledger = {
        "schema_version": 1,
        "anchor": "jp-15.7.1",
        "mode": "package-flavor-patch",
        "flavor": flavor,
        "original_package": ORIGINAL_PACKAGE,
        "package": package_name,
        "launcher_class_preserved": LAUNCHER_CLASS,
        "java_namespace_preserved": ORIGINAL_PACKAGE,
        "splits": split_rows,
    }
    (output_dir / "package-patch-ledger.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return ledger


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("split_dir", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--flavor",
        required=True,
        choices=sorted(FLAVOR_PACKAGES),
    )
    args = parser.parse_args()
    ledger = patch_split_set(
        args.split_dir.resolve(),
        args.output.resolve(),
        flavor=args.flavor,
    )
    print(json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())