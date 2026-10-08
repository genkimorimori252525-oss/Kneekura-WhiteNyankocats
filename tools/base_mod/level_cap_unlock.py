"""Additively unlock each JP15.7.1 unit's native base-level cap.

This migration changes only the per-cat max_upgrade_level.base field. It does
not change current levels, ownership, forms, user rank, story/event progress,
unit-drop claims, or Catseye-consumption history.

For exact JP 15.7.1:
- max_upgrade_levels count is an i32 at 306,330;
- 882 records follow at 306,334;
- each record is little-endian <HH> = (plus_cap_increment, base_cap_increment);
- unitbuy.csv column 18 is the original base max;
- unitbuy.csv column 50 is the native Catseye hard max.

The effective cap used by the research parser is:
    min(original_max + max_upgrade_level.base, native_catseye_hard_max)

We therefore set base_cap_increment to at least:
    min(requested_cap, native_hard_max) - original_max

The requested Kneekura cap is 60. Units whose exact official data hard-caps at
50/20/1 remain at those native caps rather than being modified beyond DataLocal.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
from typing import Any

from tools.battlecats_source import BattleCatsExport
from tools.base_mod.build_offline_max_save import (
    EXPORT_SHA256,
    _rewrite_hash,
    _verify_jp_hash,
)
from tools.base_mod.build_offline_profile_unit_manifest import build_manifest


GAME_VERSION = 150700
MAX_UPGRADE_COUNT_OFFSET = 306_330
MAX_UPGRADE_DATA_OFFSET = 306_334
MAX_UPGRADE_RECORD_SIZE = 4
EXPECTED_CAT_COUNT = 882
REQUESTED_CAP = 60

UNITBUY_ORIGINAL_BASE_COL = 18
UNITBUY_NATIVE_CATSEYE_CAP_COL = 50


def _read_u16(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def _write_u16(data: bytearray, offset: int, value: int) -> None:
    struct.pack_into("<H", data, offset, int(value))


def _read_i32(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from("<i", data, offset)[0]


def _derive_targets(export_zip: Path) -> tuple[dict[int, dict[str, int]], dict[str, Any]]:
    manifest = build_manifest(export_zip, expected_sha256=EXPORT_SHA256)
    eligible_ids = {int(item["asset_id"]) for item in manifest["eligible_units"]}

    with BattleCatsExport(
        export_zip,
        region="jp",
        expected_sha256=EXPORT_SHA256,
    ) as source:
        data_local = source.pack("DataLocal")
        unitbuy_payload, provenance = data_local.read("unitbuy.csv")

    rows = list(
        csv.reader(
            io.StringIO(unitbuy_payload.decode("utf-8-sig", "replace"))
        )
    )
    if len(rows) != EXPECTED_CAT_COUNT:
        raise ValueError(
            f"unexpected unitbuy row count: {len(rows)} != {EXPECTED_CAT_COUNT}"
        )

    targets: dict[int, dict[str, int]] = {}
    native_distribution: dict[int, int] = {}
    requested_distribution: dict[int, int] = {}

    for cat_id in sorted(eligible_ids):
        row = rows[cat_id]
        try:
            original_max = int(row[UNITBUY_ORIGINAL_BASE_COL])
            native_hard_max = int(row[UNITBUY_NATIVE_CATSEYE_CAP_COL])
        except (IndexError, ValueError) as exc:
            raise ValueError(f"invalid unitbuy level cap row for cat {cat_id}") from exc

        effective_target = min(REQUESTED_CAP, native_hard_max)
        required_increment = max(0, effective_target - original_max)

        targets[cat_id] = {
            "original_max": original_max,
            "native_hard_max": native_hard_max,
            "effective_target": effective_target,
            "required_increment": required_increment,
        }
        native_distribution[native_hard_max] = native_distribution.get(native_hard_max, 0) + 1
        requested_distribution[effective_target] = (
            requested_distribution.get(effective_target, 0) + 1
        )

    expected_distribution = {1: 8, 20: 11, 50: 493, 60: 323}
    if dict(sorted(requested_distribution.items())) != expected_distribution:
        raise ValueError(
            "JP15.7.1 eligible level-cap distribution drifted: "
            f"{dict(sorted(requested_distribution.items()))} "
            f"!= {expected_distribution}"
        )

    # Important user-facing regression anchors.
    for required_id in (289, 290, 363, 536):
        target = targets.get(required_id)
        if target is None or target["effective_target"] != 60:
            raise ValueError(
                f"required collab Uber {required_id} is not targetable to level 60"
            )

    evidence = {
        "eligible_count": len(targets),
        "requested_cap": REQUESTED_CAP,
        "effective_target_distribution": dict(sorted(requested_distribution.items())),
        "native_hard_cap_distribution": dict(sorted(native_distribution.items())),
        "unitbuy_sha256": provenance.payload_sha256,
        "required_level60_ids": [289, 290, 363, 536],
    }
    return targets, evidence


def validate_level_cap_layout(data: bytes) -> dict[str, Any]:
    stored_hash, expected_hash = _verify_jp_hash(data)
    if len(data) <= MAX_UPGRADE_DATA_OFFSET + EXPECTED_CAT_COUNT * MAX_UPGRADE_RECORD_SIZE:
        raise ValueError("SAVE_DATA is too small for max_upgrade_levels")
    if _read_i32(data, 0) != GAME_VERSION:
        raise ValueError("unexpected SAVE_DATA game version")

    count = _read_i32(data, MAX_UPGRADE_COUNT_OFFSET)
    if count != EXPECTED_CAT_COUNT:
        raise ValueError(
            f"max_upgrade_levels count mismatch: {count} != {EXPECTED_CAT_COUNT}"
        )

    return {
        "game_version": GAME_VERSION,
        "save_size": len(data),
        "jp_salted_md5": stored_hash,
        "jp_hash_valid": stored_hash == expected_hash,
        "max_upgrade_count": count,
        "max_upgrade_count_offset": MAX_UPGRADE_COUNT_OFFSET,
        "max_upgrade_data_offset": MAX_UPGRADE_DATA_OFFSET,
        "record_layout": "u16 plus_increment + u16 base_increment",
    }


def apply_native_level_cap_unlock(
    source: bytes,
    export_zip: Path,
) -> tuple[bytes, dict[str, Any]]:
    layout = validate_level_cap_layout(source)
    targets, target_evidence = _derive_targets(export_zip)

    out = bytearray(source)
    changed = 0
    already_sufficient = 0
    before_bases: dict[int, int] = {}
    after_bases: dict[int, int] = {}

    for cat_id, target in targets.items():
        record_offset = MAX_UPGRADE_DATA_OFFSET + cat_id * MAX_UPGRADE_RECORD_SIZE
        before_plus = _read_u16(out, record_offset)
        before_base = _read_u16(out, record_offset + 2)
        desired_base = max(before_base, target["required_increment"])

        before_bases[cat_id] = before_base
        after_bases[cat_id] = desired_base

        # Preserve plus-cap progression exactly.
        _write_u16(out, record_offset, before_plus)
        _write_u16(out, record_offset + 2, desired_base)

        if desired_base != before_base:
            changed += 1
        else:
            already_sufficient += 1

    new_md5 = _rewrite_hash(out)
    built = bytes(out)
    _verify_jp_hash(built)

    report = {
        "schema_version": 1,
        "mode": "kneekura-native-level-cap-unlock-v1",
        "anchor": "jp-15.7.1",
        "requested_cap": REQUESTED_CAP,
        "source": {
            "size": len(source),
            "sha256": hashlib.sha256(source).hexdigest(),
            "layout": layout,
        },
        "output": {
            "size": len(built),
            "sha256": hashlib.sha256(built).hexdigest(),
            "jp_md5": new_md5,
        },
        "target_contract": target_evidence,
        "mutation": {
            "eligible_records_considered": len(targets),
            "changed_records": changed,
            "already_sufficient_records": already_sufficient,
            "plus_increment_preserved": True,
            "current_level_untouched": True,
            "ownership_untouched": True,
            "forms_untouched": True,
            "story_event_progress_untouched": True,
            "unit_drop_claims_untouched": True,
            "catseyes_used_history_untouched": True,
        },
        "examples": {
            str(cat_id): {
                **targets[cat_id],
                "before_base_increment": before_bases[cat_id],
                "after_base_increment": after_bases[cat_id],
            }
            for cat_id in (289, 290, 363, 536)
            if cat_id in targets
        },
        "integrity": {
            "output_jp_hash_valid": True,
            "source_untouched": True,
        },
    }
    return built, report


def verify_native_level_cap_unlock(
    data: bytes,
    export_zip: Path,
) -> dict[str, Any]:
    layout = validate_level_cap_layout(data)
    targets, target_evidence = _derive_targets(export_zip)

    failures: list[str] = []
    satisfied = 0

    for cat_id, target in targets.items():
        record_offset = MAX_UPGRADE_DATA_OFFSET + cat_id * MAX_UPGRADE_RECORD_SIZE
        base_increment = _read_u16(data, record_offset + 2)
        effective_cap = min(
            target["original_max"] + base_increment,
            target["native_hard_max"],
        )
        if effective_cap < target["effective_target"]:
            failures.append(
                f"cat {cat_id} effective cap {effective_cap} "
                f"< target {target['effective_target']}"
            )
            if len(failures) >= 20:
                break
        else:
            satisfied += 1

    examples = {}
    for cat_id in (289, 290, 363, 536):
        if cat_id not in targets:
            continue
        target = targets[cat_id]
        record_offset = MAX_UPGRADE_DATA_OFFSET + cat_id * MAX_UPGRADE_RECORD_SIZE
        base_increment = _read_u16(data, record_offset + 2)
        examples[str(cat_id)] = {
            **target,
            "stored_base_increment": base_increment,
            "effective_cap": min(
                target["original_max"] + base_increment,
                target["native_hard_max"],
            ),
        }

    return {
        "schema_version": 1,
        "mode": "kneekura-native-level-cap-verification-v1",
        "verification_level": "full-semantic-level-cap",
        "anchor": "jp-15.7.1",
        "layout": layout,
        "target_contract": target_evidence,
        "satisfied_count": satisfied,
        "examples": examples,
        "failures": failures,
        "passed": not failures,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    apply_parser = sub.add_parser("apply")
    apply_parser.add_argument("save_data", type=Path)
    apply_parser.add_argument("owned_export", type=Path)
    apply_parser.add_argument("--output", type=Path, required=True)
    apply_parser.add_argument("--report", type=Path, required=True)

    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("save_data", type=Path)
    verify_parser.add_argument("owned_export", type=Path)
    verify_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(argv)

    try:
        if args.command == "apply":
            built, report = apply_native_level_cap_unlock(
                args.save_data.read_bytes(),
                args.owned_export,
            )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(built)
            args.report.write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(
                f"built level-cap migration: {report['output']['sha256']} "
                f"-> {args.output}"
            )
            return 0

        result = verify_native_level_cap_unlock(
            args.save_data.read_bytes(),
            args.owned_export,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["passed"] else 3

    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"level-cap operation failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
