"""Privately extract the 7 original enemy Godzilla animation files from owned server packs.

Exact JP15.7.1: 550_e.png belongs to MNumberServer, and cut/model/4 tracks
belong to WImageDataServer. This does NOT rename/mirror/convert or install.
Never commit the owner-source PNG, .imgcut, .mamodel or .maanim to Git.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
from tools.battlecats_pack import PackReader

SOURCE_STEM = "550_e"
TARGET_STEM = "702_f"  # cat No703 first form only
PNG_FAMILY = "MNumberServer"
ANIM_FAMILY = "WImageDataServer"
PNG_FILE = "550_e.png"
ANIM_FILES = ("550_e.imgcut", "550_e.mamodel",
              "550_e00.maanim", "550_e01.maanim",
              "550_e02.maanim", "550_e03.maanim")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def read_verified(reader: PackReader, name: str) -> bytes:
    if not reader.has(name):
        raise ValueError("missing required original owner Server asset: " + name)
    raw, _ = reader.read(name)
    if not raw or len(raw) > 64 * 1024 * 1024:
        raise ValueError("suspicious file size in owner Server asset: " + name)
    if name.endswith(".png") and not raw.startswith(PNG_SIGNATURE):
        raise ValueError("original owner Server sprite is not PNG: " + name)
    return raw


def stage_owner_rig(png_reader: PackReader, anim_reader: PackReader) -> dict[str, bytes]:
    """Fully validate input before touching the chosen output directory."""
    out = {PNG_FILE: read_verified(png_reader, PNG_FILE)}
    for name in ANIM_FILES:
        out[name] = read_verified(anim_reader, name)
    return out


def export_owner_rig(png_reader: PackReader, anim_reader: PackReader,
                     output: Path, *, source_fingerprints: dict[str, str]) -> dict[str, Any]:
    assets = stage_owner_rig(png_reader, anim_reader)
    if output.exists() and any(output.iterdir()):
        raise ValueError("refusing to overwrite a nonempty owner art directory")
    output.mkdir(parents=True, exist_ok=True)
    for name, blob in assets.items():
        (output / name).write_bytes(blob)
    receipt = {
        "schema_version": 1,
        "status": "EXTRACTED_OWNER_ONLY_NOT_MIRRORED_OR_INSTALLED",
        "enemy_no": 552, "source_stem": SOURCE_STEM,
        "cat_no": 703, "cat_form_index": 0, "target_stem": TARGET_STEM,
        "families": {"png": PNG_FAMILY, "animation": ANIM_FAMILY},
        "sources": source_fingerprints,
        "art": {
            name: {"size": len(blob), "sha256": hashlib.sha256(blob).hexdigest()}
            for name, blob in sorted(assets.items())
        },
        "needs_original_model_orientation_proof": True,
        "has_runtime_sprite_override": False,
        "has_animation_frame_sync": False,
        "save_data_modified": False,
        "original_apk_modified": False,
        "ready_to_install": False,
    }
    (output / "rig-receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt


def main(argv: list[str] | None = None) -> int:
    # Imported at invocation only: the one-step recovery module imports
    # export_owner_rig, so a module-level reverse import would create a
    # circular dependency and break both original extraction and preview.
    from tools.base_mod.fetch_godzilla_server_assets import (
        FILES as EXPECTED_JP1571_SERVER_FILES,
        verify as verify_exact_owner_server_file,
    )
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--m-number-list", type=Path, required=True)
    p.add_argument("--m-number-pack", type=Path, required=True)
    p.add_argument("--w-imagedata-list", type=Path, required=True)
    p.add_argument("--w-imagedata-pack", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args(argv)
    files = (a.m_number_list, a.m_number_pack,
             a.w_imagedata_list, a.w_imagedata_pack)
    try:
        if {x.name for x in files} != set(EXPECTED_JP1571_SERVER_FILES):
            raise ValueError("Godzilla source filenames do not match JP15.7.1 exact pairs")
        # Never extract from similarly named different-region/newer Server
        # archives. The four exact size+historical JP15.7.1 MD5 claims are
        # independently rechecked against the local owner files here.
        verified_sources = {
            x.name: verify_exact_owner_server_file(
                x, EXPECTED_JP1571_SERVER_FILES[x.name]
            )
            for x in files
        }
        hashes = {name: row["sha256"] for name, row in verified_sources.items()}
        png = PackReader(PNG_FAMILY, a.m_number_list.read_bytes(),
                         a.m_number_pack.read_bytes(), region="jp")
        anim = PackReader(ANIM_FAMILY, a.w_imagedata_list.read_bytes(),
                          a.w_imagedata_pack.read_bytes(), region="jp")
        result = export_owner_rig(png, anim, a.output, source_fingerprints=hashes)
        result["original_server_file_sha_and_MD5_verified_before_extraction"] = True
        result["exact_owner_server_source_receipts"] = verified_sources
        (a.output / "rig-receipt.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError, KeyError) as exc:
        p.error(str(exc))
    print(result["status"], len(result["art"]), "files (owner-local only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())