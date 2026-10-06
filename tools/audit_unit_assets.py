"""Metadata-only completeness audit for Battle Cats unit assets.

The audit never exports original artwork or animation bytes. It joins the unit
catalog in the supplied Android export with filename manifests from InstallPack
and optional historical/current server manifest indexes.
"""

from __future__ import annotations

import argparse
import collections
from dataclasses import dataclass
import json
import pathlib
import re
import sys
from typing import Any, Iterable

from tools.battlecats_source import BattleCatsExport
from tools.import_battlecats_catalog import build_catalog


FORM_CODES = ("f", "c", "s", "u")
LOCAL_ASSET_FAMILIES = (
    "ImageDataLocal",
    "ImageLocal",
    "NumberLocal",
    "UnitLocal",
)
STANDARD_MOTIONS = ("00", "01", "02", "03")
MAANIM_RE = re.compile(r"^(?P<base>.+?)(?P<suffix>(?:\d+|_[^.]+))\.maanim$", re.IGNORECASE)


@dataclass(frozen=True)
class AssetProvenance:
    source: str
    family: str


class AssetIndex:
    def __init__(self) -> None:
        self._items: dict[str, set[AssetProvenance]] = collections.defaultdict(set)

    def add(self, name: str, *, source: str, family: str) -> None:
        self._items[name].add(AssetProvenance(source=source, family=family))

    def has(self, name: str) -> bool:
        return name in self._items

    def provenance(self, name: str) -> list[dict[str, str]]:
        return [
            {"source": item.source, "family": item.family}
            for item in sorted(self._items.get(name, ()), key=lambda item: (item.source, item.family))
        ]

    def names(self) -> Iterable[str]:
        return self._items.keys()

    def motions(self, base: str) -> list[str]:
        found: set[str] = set()
        for name in self._items:
            if not name.startswith(base) or not name.lower().endswith(".maanim"):
                continue
            match = MAANIM_RE.fullmatch(name)
            if not match or match.group("base") != base:
                continue
            found.add(match.group("suffix"))
        return sorted(found)


@dataclass(frozen=True)
class UnitBuyRow:
    guide_order: int
    true_form_id: int
    ultra_form_id: int
    egg_id_normal: int
    egg_id_evolved: int

    @property
    def playable(self) -> bool:
        return self.guide_order >= 0


def _int_at(columns: list[str], index: int, default: int) -> int:
    if index >= len(columns):
        return default
    try:
        return int(columns[index].strip())
    except ValueError:
        return default


def parse_unitbuy_rows(payload: bytes) -> dict[int, UnitBuyRow]:
    """Parse only the columns needed by the completeness contract.

    Rows are keyed by the game's zero-based asset id. Blank rows retain their
    original line index, matching the game's table layout.
    """
    text = payload.decode("utf-8-sig", "replace")
    rows: dict[int, UnitBuyRow] = {}
    for line_index, raw_line in enumerate(text.splitlines()):
        if not raw_line.strip():
            continue
        columns = [value.strip() for value in raw_line.split(",")]
        rows[line_index] = UnitBuyRow(
            guide_order=_int_at(columns, 14, -1),
            true_form_id=_int_at(columns, 23, 0),
            ultra_form_id=_int_at(columns, 24, 0),
            egg_id_normal=_int_at(columns, 61, -1),
            egg_id_evolved=_int_at(columns, 62, -1),
        )
    return rows


def animation_base(asset_id: int, form_index: int, unitbuy: UnitBuyRow) -> str:
    if form_index == 0 and unitbuy.egg_id_normal >= 0:
        return f"{unitbuy.egg_id_normal:03d}_m"
    if form_index == 1 and unitbuy.egg_id_evolved >= 0:
        return f"{unitbuy.egg_id_evolved:03d}_m"
    return f"{asset_id:03d}_{FORM_CODES[form_index]}"


def icon_name(asset_id: int, form_index: int, unitbuy: UnitBuyRow) -> str:
    if form_index == 0 and unitbuy.egg_id_normal >= 0:
        return f"uni{unitbuy.egg_id_normal:03d}_m00.png"
    if form_index == 1 and unitbuy.egg_id_evolved >= 0:
        return f"uni{unitbuy.egg_id_evolved:03d}_m01.png"
    return f"uni{asset_id:03d}_{FORM_CODES[form_index]}00.png"


def banner_name(asset_id: int, form_index: int, unitbuy: UnitBuyRow) -> str:
    if form_index == 0 and unitbuy.egg_id_normal >= 0:
        return f"udi{unitbuy.egg_id_normal:03d}_m00.png"
    if form_index == 1 and unitbuy.egg_id_evolved >= 0:
        return f"udi{unitbuy.egg_id_evolved:03d}_m01.png"
    return f"udi{asset_id:03d}_{FORM_CODES[form_index]}.png"


def gacha_candidates(asset_id: int, unitbuy: UnitBuyRow) -> list[str]:
    names = [f"gatyachara_{asset_id:03d}_f.png", f"gatyachara_{asset_id:03d}_z.png"]
    if unitbuy.egg_id_normal >= 0 or unitbuy.egg_id_evolved >= 0:
        names.append(f"gatyachara_{asset_id:03d}_m.png")
    return names


def _source_summary(index: AssetIndex) -> dict[str, int]:
    counts: collections.Counter[str] = collections.Counter()
    for name in index.names():
        for item in index.provenance(name):
            counts[item["source"]] += 1
    return dict(sorted(counts.items()))


def load_server_index(path: pathlib.Path, asset_index: AssetIndex) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema_version") != 1:
        raise ValueError(f"unsupported server manifest index schema in {path}")

    entries = document.get("entries")
    if not isinstance(entries, list):
        raise ValueError(f"server manifest index {path} has no entries list")

    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError(f"invalid server index entry in {path}")
        name = entry.get("name")
        source = entry.get("source")
        family = entry.get("family")
        if not all(isinstance(value, str) and value for value in (name, source, family)):
            raise ValueError(f"invalid server index metadata in {path}: {entry!r}")
        asset_index.add(name, source=source, family=family)

    return document


def _asset_result(index: AssetIndex, name: str) -> dict[str, Any]:
    return {
        "name": name,
        "present": index.has(name),
        "provenance": index.provenance(name),
    }


def _form_result(
    index: AssetIndex,
    *,
    asset_id: int,
    form_index: int,
    unitbuy: UnitBuyRow,
) -> dict[str, Any]:
    base = animation_base(asset_id, form_index, unitbuy)
    rig_names = [f"{base}.png", f"{base}.imgcut", f"{base}.mamodel"]
    icon = icon_name(asset_id, form_index, unitbuy)
    banner = banner_name(asset_id, form_index, unitbuy)
    found_motions = index.motions(base)

    if unitbuy.playable:
        motion_policy = "standard-00-03"
        missing_motions = [motion for motion in STANDARD_MOTIONS if motion not in found_motions]
        motion_complete = not missing_motions
    else:
        motion_policy = "internal-at-least-one"
        missing_motions = [] if found_motions else ["<any>"]
        motion_complete = bool(found_motions)

    rig = [_asset_result(index, name) for name in rig_names]
    rig_complete = all(item["present"] for item in rig)
    icon_result = _asset_result(index, icon)
    # Internal/conjured units are not roster entries and may intentionally have no deploy icon.
    icon_required = unitbuy.playable
    icon_complete = icon_result["present"] if icon_required else True

    required_missing = [item["name"] for item in rig if not item["present"]]
    if icon_required and not icon_result["present"]:
        required_missing.append(icon)
    required_missing.extend(f"{base}{motion}.maanim" for motion in missing_motions if motion != "<any>")
    if missing_motions == ["<any>"]:
        required_missing.append(f"{base}<any>.maanim")

    return {
        "form_index": form_index,
        "form_code": FORM_CODES[form_index],
        "animation_base": base,
        "motion_policy": motion_policy,
        "rig": rig,
        "motions": {
            "found_suffixes": found_motions,
            "missing_required_suffixes": missing_motions,
            "complete": motion_complete,
        },
        "deploy_icon": {**icon_result, "required": icon_required},
        "evolution_banner": {**_asset_result(index, banner), "required": False},
        "complete": rig_complete and motion_complete and icon_complete,
        "missing_required": required_missing,
    }


def build_audit(
    export_path: pathlib.Path,
    *,
    server_indexes: Iterable[pathlib.Path] = (),
    expected_sha256: str | None = None,
    region: str = "jp",
) -> dict[str, Any]:
    catalog = build_catalog(
        export_path,
        expected_sha256=expected_sha256,
        region=region,
    )

    asset_index = AssetIndex()
    loaded_server_indexes: list[dict[str, Any]] = []

    with BattleCatsExport(
        export_path,
        expected_sha256=expected_sha256,
        region=region,
    ) as source:
        for family in LOCAL_ASSET_FAMILIES:
            try:
                pack = source.pack(family)
            except KeyError:
                continue
            for entry in pack.entries:
                asset_index.add(entry.name, source="installpack", family=family)

        data = source.pack("DataLocal")
        unitbuy_payload, unitbuy_provenance = data.read("unitbuy.csv")
        unitbuy_rows = parse_unitbuy_rows(unitbuy_payload)

    for path in server_indexes:
        loaded_server_indexes.append(load_server_index(path, asset_index))

    units: list[dict[str, Any]] = []
    missing_counter: collections.Counter[str] = collections.Counter()
    complete_units = 0
    complete_playable_units = 0
    playable_units = 0
    total_forms = 0
    complete_forms = 0
    form_shape_mismatches: list[dict[str, int]] = []

    for catalog_unit in catalog["units"]:
        unit_no = int(catalog_unit["id"])
        asset_id = unit_no - 1
        unitbuy = unitbuy_rows.get(asset_id)
        if unitbuy is None:
            raise ValueError(f"unitbuy.csv has no row for asset id {asset_id} / unit {unit_no}")

        stat_forms = [form for form in catalog_unit["forms"] if form.get("stats_raw") is not None]
        form_count = len(stat_forms)
        if form_count < 1 or form_count > len(FORM_CODES):
            raise ValueError(f"unit {unit_no} has unsupported stat form count {form_count}")

        declared_count = 2
        if unitbuy.true_form_id > 0:
            declared_count = 3
        if unitbuy.ultra_form_id > 0:
            declared_count = 4
        if unitbuy.playable and declared_count != form_count:
            form_shape_mismatches.append(
                {
                    "unit_no": unit_no,
                    "asset_id": asset_id,
                    "stat_forms": form_count,
                    "unitbuy_declared_forms": declared_count,
                }
            )

        forms = [
            _form_result(
                asset_index,
                asset_id=asset_id,
                form_index=form_index,
                unitbuy=unitbuy,
            )
            for form_index in range(form_count)
        ]
        total_forms += len(forms)
        complete_forms += sum(1 for form in forms if form["complete"])
        unit_complete = all(form["complete"] for form in forms)
        if unit_complete:
            complete_units += 1

        if unitbuy.playable:
            playable_units += 1
            if unit_complete:
                complete_playable_units += 1

        for form in forms:
            for missing in form["missing_required"]:
                if missing.endswith(".png") and missing.startswith("uni"):
                    kind = "deploy_icon"
                elif missing.endswith(".png"):
                    kind = "battle_png"
                elif missing.endswith(".imgcut"):
                    kind = "imgcut"
                elif missing.endswith(".mamodel"):
                    kind = "mamodel"
                elif missing.endswith(".maanim"):
                    kind = "maanim"
                else:
                    kind = "other"
                missing_counter[kind] += 1

        gacha = [_asset_result(asset_index, name) for name in gacha_candidates(asset_id, unitbuy)]
        units.append(
            {
                "unit_no": unit_no,
                "asset_id": asset_id,
                "key": catalog_unit["key"],
                "name": next(
                    (
                        form.get("name")
                        for form in catalog_unit["forms"]
                        if form.get("name")
                    ),
                    None,
                ),
                "playable": unitbuy.playable,
                "guide_order": unitbuy.guide_order,
                "egg_ids": {
                    "normal": unitbuy.egg_id_normal,
                    "evolved": unitbuy.egg_id_evolved,
                },
                "stat_form_count": form_count,
                "unitbuy_declared_form_count": declared_count,
                "forms": forms,
                "gacha_art": gacha,
                "complete": unit_complete,
            }
        )

    summary = catalog["summary"]
    return {
        "schema_version": 1,
        "contract": {
            "unit_number_to_asset_id": "asset_id = unit_no - 1",
            "form_codes": list(FORM_CODES),
            "playable_motion_policy": list(STANDARD_MOTIONS),
            "internal_motion_policy": "at least one maanim",
            "rig_required": ["png", "imgcut", "mamodel"],
            "deploy_icon_required_for_playable": True,
            "gacha_and_evolution_art": "reported but not universal gate requirements",
        },
        "source": catalog["source"],
        "unitbuy_provenance": {
            "family": unitbuy_provenance.family,
            "entry": unitbuy_provenance.entry,
            "payload_sha256": unitbuy_provenance.payload_sha256,
        },
        "server_index_count": len(loaded_server_indexes),
        "asset_name_counts_by_source": _source_summary(asset_index),
        "summary": {
            "unit_count": summary["unit_count"],
            "playable_unit_count": playable_units,
            "internal_unit_count": summary["unit_count"] - playable_units,
            "complete_unit_count": complete_units,
            "incomplete_unit_count": summary["unit_count"] - complete_units,
            "complete_playable_unit_count": complete_playable_units,
            "incomplete_playable_unit_count": playable_units - complete_playable_units,
            "expected_form_count": total_forms,
            "complete_form_count": complete_forms,
            "incomplete_form_count": total_forms - complete_forms,
            "missing_required_by_kind": dict(sorted(missing_counter.items())),
            "form_shape_mismatch_count": len(form_shape_mismatches),
            "form_shape_mismatches": form_shape_mismatches,
            "strict_gate_passed": complete_units == summary["unit_count"],
            "playable_gate_passed": complete_playable_units == playable_units,
        },
        "units": units,
    }


def write_audit(audit: dict[str, Any], output: pathlib.Path) -> pathlib.Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit Battle Cats unit visual/animation completeness without exporting asset bytes."
    )
    parser.add_argument("export", type=pathlib.Path)
    parser.add_argument(
        "--server-index",
        action="append",
        type=pathlib.Path,
        default=[],
        help="Metadata-only JSON produced by build_server_manifest_index.py (repeatable).",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=pathlib.Path("reports/private/unit-asset-completeness.json"),
    )
    parser.add_argument("--expect-sha256", default=None)
    parser.add_argument("--region", default="jp", choices=["jp"])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        audit = build_audit(
            args.export,
            server_indexes=args.server_index,
            expected_sha256=args.expect_sha256,
            region=args.region,
        )
        output = write_audit(audit, args.output)
    except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"asset audit failed: {exc}", file=sys.stderr)
        return 2

    summary = audit["summary"]
    print(
        f"units {summary['complete_unit_count']}/{summary['unit_count']} complete; "
        f"playable {summary['complete_playable_unit_count']}/{summary['playable_unit_count']}; "
        f"forms {summary['complete_form_count']}/{summary['expected_form_count']} -> {output}"
    )
    return 0 if summary["strict_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
