"""Metadata-only Godzilla animation gate for KNEEKURA Update 1.01.

Input format: existing tools.build_server_manifest_index schema=1 JSON.
Read-only: does not import texture bytes, rename models, inject game files,
or claim enemy-to-cat animations work just because filenames exist.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

TARGET_STEM = "702_f"  # confirmed cat No.703 first form ONLY.
REQUIRED_MOTIONS = ("00", "01", "02", "03")
# Discovery candidates ONLY. Do not assume enemy No.552 = a visual asset ID.
ENEMY_STEM_CANDIDATES = ("550_e", "551_e", "552_e")


def required_names(stem: str) -> tuple[str, ...]:
    return (f"{stem}.png", f"{stem}.imgcut", f"{stem}.mamodel",
            *(f"{stem}{m}.maanim" for m in REQUIRED_MOTIONS))


def inspect_index(document: dict[str, Any], *, enemy_stem: str | None = None) -> dict[str, Any]:
    if document.get("schema_version") != 1 or not isinstance(document.get("entries"), list):
        raise ValueError("expected server filename index schema_version=1 and entries")
    by_name: dict[str, set[tuple[str, str]]] = {}
    for entry in document["entries"]:
        if not isinstance(entry, dict):
            raise ValueError("index entries must be objects")
        name, source, family = entry.get("name"), entry.get("source"), entry.get("family")
        if not all(isinstance(s, str) and s for s in (name, source, family)):
            raise ValueError("server entry must contain valid name, source, family")
        by_name.setdefault(name, set()).add((source, family))
    if enemy_stem and any(s in enemy_stem for s in ("/", "\\", ".")):
        raise ValueError("enemy stem must be a simple filename stem")
    candidates = (enemy_stem,) if enemy_stem else ENEMY_STEM_CANDIDATES
    examined = []
    for stem in candidates:
        names = required_names(stem)
        missing = [n for n in names if n not in by_name]
        examined.append({
            "enemy_stem_candidate": stem, "source_rig_present": not missing,
            "present_count": len(names) - len(missing),
            "required_count": len(names), "missing": missing,
        })
    matches = [x for x in examined if x["source_rig_present"]]
    cat_names = required_names(TARGET_STEM)
    cat_missing = [n for n in cat_names if n not in by_name]
    if len(matches) == 1:
        selected = matches[0]["enemy_stem_candidate"]
        state = "SOURCE_RIG_METADATA_PRESENT_CONVERSION_AND_DEVICE_PROOF_REQUIRED"
        mapping = dict(zip(required_names(selected), cat_names))
        provenance = {
            name: [{"source": s, "family": f} for s, f in sorted(by_name[name])]
            for name in required_names(selected)
        }
    elif matches:
        selected = None
        state = "AMBIGUOUS_ENEMY_RIG_SOURCE_FAIL_CLOSED"
        mapping = {}
        provenance = {}
    else:
        selected = None
        state = "ENEMY_RIG_MISSING_FROM_PROVIDED_INDEX"
        mapping = {}
        provenance = {}
    return {
        "schema_version": 1,
        "mode": "godzilla-first-form-animation-metadata-gate",
        "status": state,
        "source_enemy_no": 552,
        "source_enemy_stem_evidenced": selected,
        "source_candidates": examined,
        "target_catalog_no": 703,
        "target_asset_id": 702,
        "target_form_index": 0,
        "target_stem": TARGET_STEM,
        "target_preexisting_rig_metadata_complete": len(cat_missing) == 0,
        "target_missing_metadata": cat_missing,
        "source_to_target_filenames_only_NOT_a_conversion": mapping,
        "source_provenance": provenance,
        "immutable_forms": ["702_c", "702_s", "702_u"],
        "known_limitations": [
            "Enemy-to-cat rig orientation/mirror and timing cannot be achieved by renaming alone.",
            "Texture pixels, imgcut coordinates, mamodel hierarchy and maanim frames not inspected.",
            "No visual animation injected into original Android battle engine.",
            "Indexes are metadata; actual owner-held server asset bytes are required.",
            "The second form 702_c and Madoka special death animation must be preserved.",
        ],
        "ready_to_install": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--enemy-stem")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = inspect_index(json.loads(args.index.read_text(encoding="utf-8")),
                               enemy_stem=args.enemy_stem)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(result["status"])
    return 0 if result["source_enemy_stem_evidenced"] else 3


if __name__ == "__main__":
    raise SystemExit(main())