"""Inject a user-supplied Frida Gadget into the disposable research flavor.

This module is intentionally separate from the product bootstrap.  It operates
only on an already Kneekura-bootstrap-injected split set and adds the TBCML-style
Frida Gadget config/script entries for temporary Phase-C observation.

No Frida binary is downloaded or committed by this project.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from tools.base_mod.elf_anchor import EM_AARCH64, elf_machine, gnu_build_id
from tools.base_mod.inject_shim import (
    NATIVE_ENTRY,
    SHIM_ENTRY,
    SHIM_SONAME,
    add_needed_dependency,
)
from tools.base_mod.repack import JP_15_7_1_SPLITS, sha256_file


ARM64_SPLIT = "split_config.arm64_v8a.apk"
GADGET_ENTRY = "lib/arm64-v8a/libfrida-gadget.so"
GADGET_SONAME = "libfrida-gadget.so"
GADGET_CONFIG_ENTRY = "lib/arm64-v8a/libfrida-gadget.config.so"
TRACE_SCRIPT_ENTRY = "lib/arm64-v8a/libbc_script.js.so"

GADGET_CONFIG = (
    b'{"interaction":{"type":"script","path":"libbc_script.js.so",'
    b'"on_change":"reload"}}'
)


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


def verify_gadget(gadget: bytes) -> dict:
    if elf_machine(gadget) != EM_AARCH64:
        raise ValueError("research Frida Gadget must be AArch64")
    return {
        "sha256": hashlib.sha256(gadget).hexdigest(),
        "size": len(gadget),
        "gnu_build_id": gnu_build_id(gadget),
        "machine": "AArch64",
    }


def inject_research_split(
    source_apk: Path,
    target_apk: Path,
    *,
    gadget_path: Path,
    trace_script_path: Path,
) -> dict:
    gadget = gadget_path.read_bytes()
    trace_script = trace_script_path.read_bytes()
    gadget_info = verify_gadget(gadget)

    if b"KNEEKURA_TRACE " not in trace_script:
        raise ValueError("trace script does not emit KNEEKURA_TRACE records")

    with zipfile.ZipFile(source_apk, "r") as archive:
        names = set(archive.namelist())
        if SHIM_ENTRY not in names:
            raise ValueError(
                "research injection expects libkneekura.so bootstrap first"
            )
        for entry in (
            GADGET_ENTRY,
            GADGET_CONFIG_ENTRY,
            TRACE_SCRIPT_ENTRY,
        ):
            if entry in names:
                raise ValueError(f"input research split already contains {entry}")

        native = archive.read(NATIVE_ENTRY)

    patched_native, mutation = add_needed_dependency(
        native,
        needed=GADGET_SONAME,
    )
    if SHIM_SONAME not in mutation["libraries_before"]:
        raise ValueError(
            "research injection expects libnative to depend on libkneekura.so first"
        )

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
            raise RuntimeError("native entry disappeared during research rewrite")

        def add_stored(name: str, payload: bytes) -> None:
            item = zipfile.ZipInfo(name, native_info.date_time)
            item.compress_type = zipfile.ZIP_STORED
            item.external_attr = native_info.external_attr
            item.create_system = native_info.create_system
            dst.writestr(item, payload)

        add_stored(GADGET_ENTRY, gadget)
        add_stored(GADGET_CONFIG_ENTRY, GADGET_CONFIG)
        add_stored(TRACE_SCRIPT_ENTRY, trace_script)

    return {
        "schema_version": 1,
        "mode": "research-frida-observation",
        "input_split_sha256": sha256_file(source_apk),
        "output_split_sha256_unsigned": sha256_file(target_apk),
        "gadget": gadget_info,
        "trace_script_sha256": hashlib.sha256(trace_script).hexdigest(),
        "trace_script_size": len(trace_script),
        "mutation": mutation,
        "added_entries": [
            GADGET_ENTRY,
            GADGET_CONFIG_ENTRY,
            TRACE_SCRIPT_ENTRY,
        ],
        "changed_entries": [NATIVE_ENTRY],
        "research_only": True,
    }


def inject_research_split_set(
    split_dir: Path,
    output_dir: Path,
    *,
    gadget_path: Path,
    trace_script_path: Path,
) -> dict:
    if not split_dir.is_dir():
        raise FileNotFoundError(split_dir)

    missing = [
        name for name in JP_15_7_1_SPLITS if not (split_dir / name).is_file()
    ]
    if missing:
        raise FileNotFoundError(
            "incomplete split set: " + ", ".join(missing)
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    arm64_ledger = None
    for split_name in JP_15_7_1_SPLITS:
        source = split_dir / split_name
        target = output_dir / split_name
        if split_name == ARM64_SPLIT:
            arm64_ledger = inject_research_split(
                source,
                target,
                gadget_path=gadget_path,
                trace_script_path=trace_script_path,
            )
        else:
            shutil.copy2(source, target)

    if arm64_ledger is None:
        raise RuntimeError("arm64 research split was not processed")

    ledger = {
        "schema_version": 1,
        "mode": "research-frida-observation",
        "research_only": True,
        "arm64": arm64_ledger,
    }
    (output_dir / "research-patch-ledger.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return ledger


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("split_dir", type=Path)
    parser.add_argument("--gadget", required=True, type=Path)
    parser.add_argument("--trace-script", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    ledger = inject_research_split_set(
        args.split_dir.resolve(),
        args.output.resolve(),
        gadget_path=args.gadget.resolve(),
        trace_script_path=args.trace_script.resolve(),
    )
    print(json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
