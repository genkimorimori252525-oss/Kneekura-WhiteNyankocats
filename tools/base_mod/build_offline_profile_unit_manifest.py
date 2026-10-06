"""Build a version-pinned offline-profile unit selection manifest.

The manifest is metadata-only. It reads the user-owned JP 15.7.1 DataLocal
tables and produces the exact unit IDs that are both roster-playable and shown
in the Cat Guide. Hidden/internal/test/regional slots stay excluded.

No SAVE_DATA bytes are read or modified by this tool.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
from typing import Any

from tools.battlecats_source import BattleCatsExport


ANCHOR_REGION = "jp"
ANCHOR_VERSION = "15.7.1"
ANCHOR_VERSION_CODE = 150700
ANCHOR_EXPORT_SHA256 = "38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56"
EXPECTED_UNIT_ROWS = 882
EXPECTED_GUIDE_VISIBLE = 835
KNOWN_HIDDEN_TEST_OR_NONSTANDARD = {673, 740, 788}


def _rows(payload: bytes, *, delimiter: str = ",") -> list[list[str]]:
    text = payload.decode("utf-8-sig", "replace")
    return list(csv.reader(io.StringIO(text), delimiter=delimiter))


def _int(row: list[str], index: int, default: int = 0) -> int:
    if index >= len(row):
        return default
    value = row[index].strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def parse_unit_selection(
    *,
    unitbuy_payload: bytes,
    picturebook_payload: bytes,
    game_version_code: int = ANCHOR_VERSION_CODE,
) -> dict[str, Any]:
    unitbuy = _rows(unitbuy_payload)
    picturebook = _rows(picturebook_payload)

    if len(unitbuy) != len(picturebook):
        raise ValueError(
            f"unit table length mismatch: unitbuy={len(unitbuy)} picturebook={len(picturebook)}"
        )

    units: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []

    for asset_id, (buy, book) in enumerate(zip(unitbuy, picturebook)):
        guide_visible = _int(book, 0, 0) != 0
        limited = _int(book, 1, 0) != 0
        total_forms = _int(book, 2, 0)
        hint_display_type = _int(book, 3, 0)

        position_order = _int(buy, 14, -1)
        playable = position_order >= 0
        rarity = _int(buy, 13, -1)
        gatya_rarity = _int(buy, 17, -1)
        second_form_unlock_level = _int(buy, 21, 0)
        tf_id = _int(buy, 23, 0)
        uf_id = _int(buy, 24, 0)
        max_upgrade_no_catseye = _int(buy, 49, 0)
        max_upgrade_catseye = _int(buy, 50, 0)
        max_plus_upgrade = _int(buy, 51, 0)
        unit_game_version = _int(buy, 57, 0)
        np_sell_price = _int(buy, 58, 0)
        egg_value = _int(buy, 61, -1)
        egg_id = _int(buy, 62, -1)

        reasons: list[str] = []
        if not guide_visible:
            reasons.append("catguide_hidden")
        if not playable:
            reasons.append("not_roster_playable")
        if unit_game_version > game_version_code:
            reasons.append("introduced_after_anchor")

        record = {
            "asset_id": asset_id,
            "catalog_unit_no": asset_id + 1,
            "guide_visible": guide_visible,
            "limited": limited,
            "total_forms": total_forms,
            "hint_display_type": hint_display_type,
            "playable": playable,
            "position_order": position_order,
            "rarity": rarity,
            "gatya_rarity": gatya_rarity,
            "second_form_unlock_level": second_form_unlock_level,
            "tf_id": tf_id,
            "uf_id": uf_id,
            "max_upgrade_no_catseye": max_upgrade_no_catseye,
            "max_upgrade_catseye": max_upgrade_catseye,
            "max_plus_upgrade": max_plus_upgrade,
            "unit_game_version": unit_game_version,
            "np_sell_price": np_sell_price,
            "egg_value": egg_value,
            "egg_id": egg_id,
        }

        if reasons:
            excluded.append({**record, "excluded_reasons": reasons})
            continue

        units.append(
            {
                **record,
                "bootstrap_state": {
                    "owned": True,
                    "gacha_seen": True,
                    "current_form": 0,
                    "unlocked_forms": 0,
                    "force_true_form": False,
                    "force_fourth_form": False,
                    "force_talents": False,
                    "force_upgrade_level": False,
                    "note": (
                        "first-form ownership contract only; exact SAVE_DATA field binding "
                        "is deferred to the device baseline"
                    ),
                },
            }
        )

    return {
        "schema_version": 1,
        "mode": "offline-profile-static-unit-selection",
        "anchor": {
            "region": ANCHOR_REGION,
            "game_version": ANCHOR_VERSION,
            "game_version_code": game_version_code,
        },
        "source_tables": {
            "unitbuy.csv": {
                "sha256": _sha256(unitbuy_payload),
                "rows": len(unitbuy),
            },
            "nyankoPictureBookData.csv": {
                "sha256": _sha256(picturebook_payload),
                "rows": len(picturebook),
            },
        },
        "selection_contract": {
            "eligible": "catguide_visible AND position_order>=0 AND unit_game_version<=anchor",
            "first_form_current_form": 0,
            "first_form_unlocked_forms": 0,
            "set_owned": True,
            "set_gacha_seen": True,
            "do_not_force_true_form": True,
            "do_not_force_fourth_form": True,
            "do_not_force_talents": True,
            "do_not_force_upgrade_level": True,
        },
        "summary": {
            "catalog_rows": len(unitbuy),
            "eligible_count": len(units),
            "excluded_count": len(excluded),
            "guide_visible_count": sum(_int(row, 0, 0) != 0 for row in picturebook),
            "playable_count": sum(_int(row, 14, -1) >= 0 for row in unitbuy),
            "guide_visible_but_not_playable_count": sum(
                (_int(book, 0, 0) != 0) and (_int(buy, 14, -1) < 0)
                for buy, book in zip(unitbuy, picturebook)
            ),
            "playable_but_guide_hidden_count": sum(
                (_int(book, 0, 0) == 0) and (_int(buy, 14, -1) >= 0)
                for buy, book in zip(unitbuy, picturebook)
            ),
        },
        "eligible_units": units,
        "excluded_units": excluded,
    }


def apply_asset_audit_gate(manifest: dict[str, Any], audit: dict[str, Any]) -> None:
    source = audit.get("source", {})
    if source.get("export_sha256") != ANCHOR_EXPORT_SHA256:
        raise ValueError("asset audit source export SHA-256 does not match JP 15.7.1 anchor")

    result = audit.get("result", {})
    if result.get("unit_count") != EXPECTED_UNIT_ROWS:
        raise ValueError("asset audit unit count does not match expected 882 rows")

    residuals = audit.get("residuals", [])
    incomplete_ids = {int(item["asset_id"]) for item in residuals}
    eligible_ids = {int(item["asset_id"]) for item in manifest["eligible_units"]}
    overlap = sorted(incomplete_ids & eligible_ids)
    if overlap:
        raise ValueError(f"eligible units overlap asset-incomplete residuals: {overlap}")

    manifest["asset_gate"] = {
        "source_export_sha256": source.get("export_sha256"),
        "complete_unit_count": result.get("complete_unit_count"),
        "incomplete_unit_count": result.get("incomplete_unit_count"),
        "incomplete_asset_ids": sorted(incomplete_ids),
        "eligible_overlap": overlap,
        "passed": not overlap,
    }


def build_manifest(
    export: Path,
    *,
    expected_sha256: str = ANCHOR_EXPORT_SHA256,
    asset_audit: Path | None = None,
) -> dict[str, Any]:
    with BattleCatsExport(
        export,
        expected_sha256=expected_sha256,
        region=ANCHOR_REGION,
    ) as source:
        data = source.pack("DataLocal")
        unitbuy_payload, unitbuy_provenance = data.read("unitbuy.csv")
        picturebook_payload, picturebook_provenance = data.read("nyankoPictureBookData.csv")

    manifest = parse_unit_selection(
        unitbuy_payload=unitbuy_payload,
        picturebook_payload=picturebook_payload,
    )

    manifest["source_export_sha256"] = expected_sha256
    manifest["source_provenance"] = {
        "unitbuy.csv": {
            "family": unitbuy_provenance.family,
            "entry": unitbuy_provenance.entry,
            "payload_sha256": unitbuy_provenance.payload_sha256,
        },
        "nyankoPictureBookData.csv": {
            "family": picturebook_provenance.family,
            "entry": picturebook_provenance.entry,
            "payload_sha256": picturebook_provenance.payload_sha256,
        },
    }

    summary = manifest["summary"]
    if summary["catalog_rows"] != EXPECTED_UNIT_ROWS:
        raise ValueError(
            f"unexpected JP 15.7.1 unit row count: {summary['catalog_rows']}"
        )
    if summary["eligible_count"] != EXPECTED_GUIDE_VISIBLE:
        raise ValueError(
            f"unexpected eligible unit count: {summary['eligible_count']} != {EXPECTED_GUIDE_VISIBLE}"
        )
    if summary["guide_visible_but_not_playable_count"] != 0:
        raise ValueError("guide-visible unit is not roster-playable")

    eligible_ids = {item["asset_id"] for item in manifest["eligible_units"]}
    if eligible_ids & KNOWN_HIDDEN_TEST_OR_NONSTANDARD:
        raise ValueError("known hidden/test/nonstandard unit leaked into eligible selection")

    if asset_audit is not None:
        apply_asset_audit_gate(
            manifest,
            json.loads(asset_audit.read_text(encoding="utf-8")),
        )

    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("export", type=Path)
    parser.add_argument(
        "--asset-audit",
        type=Path,
        default=Path("docs/foundation/unit-asset-audit-summary-15.7.1.json"),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expect-sha256", default=ANCHOR_EXPORT_SHA256)
    args = parser.parse_args(argv)

    try:
        manifest = build_manifest(
            args.export,
            expected_sha256=args.expect_sha256,
            asset_audit=args.asset_audit,
        )
    except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"offline profile unit manifest failed: {exc}", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"eligible {manifest['summary']['eligible_count']} / "
        f"{manifest['summary']['catalog_rows']} -> {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
