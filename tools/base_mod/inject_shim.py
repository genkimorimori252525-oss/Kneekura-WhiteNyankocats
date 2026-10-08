"""Inject the inert Kneekura bootstrap as a DT_NEEDED dependency.

This is deliberately version-pinned to the exact JP 15.7.1 ARM64
libnative-lib.so.  The shim itself defaults to feature mask 0 and therefore
changes no Battle Cats behavior in Phase A.

LIEF is used here because TBCML's own native-library injection path uses the
same ELF operation (Binary.add_library) before placing the dependency beside
libnative-lib.so.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import zipfile

from tools.base_mod.elf_anchor import EM_AARCH64, elf_machine, gnu_build_id
from tools.base_mod.repack import sha256_file


TARGET_NATIVE_SHA256 = (
    "333d2974ab2ff881fd70087fd62dea7d12d82addbc55cab2f2a675ad67e3a7e2"
)
TARGET_NATIVE_BUILD_ID = "8cb3815648eb9642da10bfb039d71bff7a3519bd"
NATIVE_ENTRY = "lib/arm64-v8a/libnative-lib.so"
SHIM_ENTRY = "lib/arm64-v8a/libkneekura.so"
SHIM_SONAME = "libkneekura.so"


def _import_lief():
    try:
        import lief  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "LIEF is required for native dependency injection. "
            "Install requirements-patching.txt."
        ) from exc
    return lief


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


def _export_names(binary) -> set[str]:
    names: set[str] = set()
    for function in binary.exported_functions:
        name = getattr(function, "name", "")
        if name:
            names.add(name)
    return names


def add_needed_dependency(
    native_bytes: bytes,
    *,
    needed: str = SHIM_SONAME,
) -> tuple[bytes, dict]:
    lief = _import_lief()

    with tempfile.TemporaryDirectory(prefix="kneekura-lief-") as temp_name:
        temp = Path(temp_name)
        source = temp / "libnative-lib.so"
        target = temp / "libnative-lib.patched.so"
        source.write_bytes(native_bytes)

        binary = lief.parse(str(source))
        if binary is None:
            raise ValueError("LIEF could not parse libnative-lib.so")

        before_libraries = list(binary.libraries)
        before_exports = _export_names(binary)
        if needed not in before_libraries:
            binary.add_library(needed)
        binary.write(str(target))

        patched = target.read_bytes()
        verified = lief.parse(str(target))
        if verified is None:
            raise ValueError("LIEF could not reparse patched libnative-lib.so")

        after_libraries = list(verified.libraries)
        after_exports = _export_names(verified)
        if needed not in after_libraries:
            raise RuntimeError("patched native library does not depend on shim")
        if before_exports != after_exports:
            missing = sorted(before_exports - after_exports)
            added = sorted(after_exports - before_exports)
            raise RuntimeError(
                "native export surface changed while adding DT_NEEDED; "
                f"missing={missing[:8]} added={added[:8]}"
            )

        return patched, {
            "needed": needed,
            "libraries_before": before_libraries,
            "libraries_after": after_libraries,
            "export_count": len(after_exports),
            "export_surface_preserved": True,
        }


def verify_anchor_native(native_bytes: bytes) -> dict:
    digest = hashlib.sha256(native_bytes).hexdigest()
    if digest != TARGET_NATIVE_SHA256:
        raise ValueError(
            "libnative-lib.so SHA-256 mismatch: "
            f"expected {TARGET_NATIVE_SHA256}, got {digest}"
        )
    build_id = gnu_build_id(native_bytes)
    if build_id != TARGET_NATIVE_BUILD_ID:
        raise ValueError(
            "libnative-lib.so GNU build ID mismatch: "
            f"expected {TARGET_NATIVE_BUILD_ID}, got {build_id}"
        )
    if elf_machine(native_bytes) != EM_AARCH64:
        raise ValueError("target native library is not AArch64")
    return {
        "sha256": digest,
        "gnu_build_id": build_id,
        "machine": "AArch64",
    }


def verify_shim(shim_bytes: bytes) -> dict:
    if elf_machine(shim_bytes) != EM_AARCH64:
        raise ValueError("libkneekura.so must be AArch64")
    return {
        "sha256": hashlib.sha256(shim_bytes).hexdigest(),
        "size": len(shim_bytes),
        "gnu_build_id": gnu_build_id(shim_bytes),
        "machine": "AArch64",
    }


def inject_split(
    source_apk: Path,
    target_apk: Path,
    shim_path: Path,
) -> dict:
    shim_bytes = shim_path.read_bytes()
    shim_info = verify_shim(shim_bytes)

    with zipfile.ZipFile(source_apk, "r") as archive:
        try:
            native_bytes = archive.read(NATIVE_ENTRY)
        except KeyError as exc:
            raise ValueError(
                f"{source_apk.name} does not contain {NATIVE_ENTRY}"
            ) from exc
        if SHIM_ENTRY in archive.namelist():
            raise ValueError("input split already contains libkneekura.so")
        anchor_info = verify_anchor_native(native_bytes)

    patched_native, mutation = add_needed_dependency(native_bytes)

    target_apk.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source_apk, "r") as src, zipfile.ZipFile(
        target_apk, "w", allowZip64=True
    ) as dst:
        native_info = None
        for info in src.infolist():
            if info.is_dir() or _is_signature_entry(info.filename):
                continue
            out_info = _clone_info(info)
            if info.filename == NATIVE_ENTRY:
                native_info = out_info
                dst.writestr(out_info, patched_native)
                continue
            with src.open(info, "r") as reader, dst.open(
                out_info, "w", force_zip64=True
            ) as writer:
                shutil.copyfileobj(reader, writer, 1024 * 1024)

        if native_info is None:
            raise RuntimeError("native entry disappeared during rewrite")

        shim_zip = zipfile.ZipInfo(SHIM_ENTRY, native_info.date_time)
        # Native libraries are stored; zipalign will enforce final alignment
        # before signing.
        shim_zip.compress_type = zipfile.ZIP_STORED
        shim_zip.external_attr = native_info.external_attr
        shim_zip.create_system = native_info.create_system
        dst.writestr(shim_zip, shim_bytes)

    return {
        "schema_version": 1,
        "anchor": "jp-15.7.1-arm64",
        "mode": "bootstrap-dt-needed",
        "input_split_sha256": sha256_file(source_apk),
        "output_split_sha256_unsigned": sha256_file(target_apk),
        "anchor_native": anchor_info,
        "patched_native_sha256": hashlib.sha256(patched_native).hexdigest(),
        "shim": shim_info,
        "mutation": mutation,
        "changed_entries": [NATIVE_ENTRY, SHIM_ENTRY],
        "feature_mask_default": 0,
        "extension_off_fallthrough": True,
    }


def patch_split_set(
    split_dir: Path,
    output_dir: Path,
    shim_path: Path,
) -> dict:
    if not split_dir.is_dir():
        raise FileNotFoundError(split_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    for source in sorted(split_dir.glob("*.apk")):
        target = output_dir / source.name
        if source.name == "split_config.arm64_v8a.apk":
            rows.append(inject_split(source, target, shim_path))
        else:
            shutil.copy2(source, target)

    if not rows:
        raise FileNotFoundError(
            "split_config.arm64_v8a.apk is required for shim injection"
        )

    ledger = {
        "schema_version": 1,
        "mode": "kneekura-bootstrap",
        "shim_soname": SHIM_SONAME,
        "target_native_sha256": TARGET_NATIVE_SHA256,
        "target_native_build_id": TARGET_NATIVE_BUILD_ID,
        "arm64": rows[0],
    }
    (output_dir / "bootstrap-patch-ledger.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return ledger


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("split_dir", type=Path)
    parser.add_argument("--shim", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    ledger = patch_split_set(
        args.split_dir.resolve(),
        args.output.resolve(),
        args.shim.resolve(),
    )
    print(json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())