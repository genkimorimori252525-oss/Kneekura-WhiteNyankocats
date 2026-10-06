"""Build a tiny data-only Super Kneekura Rare Gacha prototype set.

This tool does NOT patch an APK by itself. It emits four plaintext DataLocal
replacement files plus a ledger. The output can be passed to
patch_installpack_data.py.

Preservation constraints:
- append one new Rare Gacha set instead of replacing an original set;
- unit ids must already appear in at least one exact local R1 set;
- explicit test/cheat ids are rejected;
- no rarity probability vector is invented here;
- R2/R3 remain empty for the appended prototype;
- option metadata is cloned from an existing original set.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.battlecats_source import BattleCatsExport


EXACT_EXPORT_SHA256 = (
    "38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56"
)

R1 = "GatyaDataSetR1.csv"
R2 = "GatyaDataSetR2.csv"
R3 = "GatyaDataSetR3.csv"
OPTION = "GatyaData_Option_SetR.tsv"

EXPLICIT_EXCLUDED_UNIT_IDS = {673}
MAX_PROTOTYPE_POOL = 10


def _text(payload: bytes) -> str:
    return payload.decode("utf-8-sig", "replace")


def _normalized_lines(payload: bytes) -> list[str]:
    return _text(payload).splitlines()


def _dataset_units(line: str) -> list[int]:
    result: list[int] = []
    for cell in line.split(","):
        cell = cell.strip()
        if not cell:
            continue
        value = int(cell)
        if value == -1:
            break
        result.append(value)
    return result


def _r1_union(lines: list[str]) -> set[int]:
    return {
        unit_id
        for line in lines
        for unit_id in _dataset_units(line)
    }


def build_replacements(
    r1_payload: bytes,
    r2_payload: bytes,
    r3_payload: bytes,
    option_payload: bytes,
    *,
    clone_option_set: int,
    unit_ids: list[int],
    banner_on: int | None = None,
) -> tuple[dict[str, bytes], dict]:
    r1_lines = _normalized_lines(r1_payload)
    r2_lines = _normalized_lines(r2_payload)
    r3_lines = _normalized_lines(r3_payload)
    option_lines = _normalized_lines(option_payload)

    if not r1_lines:
        raise ValueError("R1 dataset is empty")
    if len(r1_lines) != len(r2_lines) or len(r1_lines) != len(r3_lines):
        raise ValueError(
            "R1/R2/R3 row counts differ; refusing to append an unaligned set"
        )
    if len(option_lines) != len(r1_lines) + 1:
        raise ValueError(
            "option table must contain one header plus one row per dataset set"
        )

    new_set_id = len(r1_lines)
    if clone_option_set < 0 or clone_option_set >= new_set_id:
        raise ValueError(
            f"clone option set {clone_option_set} outside 0..{new_set_id - 1}"
        )

    if not unit_ids:
        raise ValueError("prototype unit pool is empty")
    if len(unit_ids) > MAX_PROTOTYPE_POOL:
        raise ValueError(
            f"prototype pool is intentionally capped at {MAX_PROTOTYPE_POOL} units"
        )
    if len(set(unit_ids)) != len(unit_ids):
        raise ValueError(
            "prototype pool contains duplicate ids; weighting by duplication "
            "has not been approved"
        )

    local_union = _r1_union(r1_lines)
    excluded = sorted(set(unit_ids) & EXPLICIT_EXCLUDED_UNIT_IDS)
    if excluded:
        raise ValueError(
            f"prototype includes explicit excluded test/cheat ids: {excluded}"
        )

    unproven = sorted(set(unit_ids) - local_union)
    if unproven:
        raise ValueError(
            "prototype ids are not present in the exact local R1 union: "
            + ", ".join(str(value) for value in unproven)
        )

    clone_cells = option_lines[clone_option_set + 1].split("\t")
    if not clone_cells:
        raise ValueError("clone option row is empty")
    try:
        clone_id = int(clone_cells[0])
    except ValueError as exc:
        raise ValueError("clone option row does not begin with set id") from exc
    if clone_id != clone_option_set:
        raise ValueError(
            f"option row index/id mismatch: index {clone_option_set}, id {clone_id}"
        )

    new_option_cells = list(clone_cells)
    new_option_cells[0] = str(new_set_id)
    if banner_on is not None:
        if banner_on not in (0, 1):
            raise ValueError("banner_on must be 0 or 1")
        if len(new_option_cells) <= 1:
            raise ValueError("option row lacks BannerON_OFF column")
        new_option_cells[1] = str(banner_on)

    new_r1_line = ",".join(str(value) for value in unit_ids) + ",-1"
    new_option_line = "\t".join(new_option_cells)

    replacements = {
        R1: ("\n".join(r1_lines + [new_r1_line]) + "\n").encode("utf-8"),
        R2: ("\n".join(r2_lines + ["-1"]) + "\n").encode("utf-8"),
        R3: ("\n".join(r3_lines + ["-1"]) + "\n").encode("utf-8"),
        OPTION: (
            "\n".join(option_lines + [new_option_line]) + "\n"
        ).encode("utf-8"),
    }

    ledger = {
        "schema_version": 1,
        "mode": "super-kneekura-data-prototype",
        "new_set_id": new_set_id,
        "clone_option_set": clone_option_set,
        "prototype_unit_ids": unit_ids,
        "prototype_pool_size": len(unit_ids),
        "all_units_present_in_exact_local_r1_union": True,
        "explicit_exclusions_checked": sorted(EXPLICIT_EXCLUDED_UNIT_IDS),
        "r2_empty": True,
        "r3_empty": True,
        "banner_on_override": banner_on,
        "option_row_before": option_lines[clone_option_set + 1],
        "option_row_after": new_option_line,
        "rarity_probability_vector_defined": False,
        "visibility_schedule_defined": False,
        "original_rows_replaced": False,
        "warning": (
            "This prototype proves only an original-format appended data set. "
            "It does not prove banner visibility, draw rates, Cat Food cost, "
            "or acquisition/save behavior until exercised in the original scene."
        ),
    }
    return replacements, ledger


def build_from_export(
    export_zip: Path,
    output_dir: Path,
    *,
    clone_option_set: int,
    unit_ids: list[int],
    banner_on: int | None = None,
) -> dict:
    with BattleCatsExport(
        export_zip,
        region="jp",
        expected_sha256=EXACT_EXPORT_SHA256,
    ) as export:
        data = export.pack("DataLocal")
        payloads = {
            name: data.read(name)[0]
            for name in (R1, R2, R3, OPTION)
        }

    replacements, ledger = build_replacements(
        payloads[R1],
        payloads[R2],
        payloads[R3],
        payloads[OPTION],
        clone_option_set=clone_option_set,
        unit_ids=unit_ids,
        banner_on=banner_on,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in replacements.items():
        (output_dir / name).write_bytes(payload)
    (output_dir / "super-kneekura-prototype-ledger.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return ledger


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export_zip", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--clone-option-set", required=True, type=int)
    parser.add_argument("--unit", action="append", type=int, required=True)
    parser.add_argument("--banner-on", type=int, choices=[0, 1])
    args = parser.parse_args()

    ledger = build_from_export(
        args.export_zip.resolve(),
        args.output.resolve(),
        clone_option_set=args.clone_option_set,
        unit_ids=args.unit,
        banner_on=args.banner_on,
    )
    print(json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
