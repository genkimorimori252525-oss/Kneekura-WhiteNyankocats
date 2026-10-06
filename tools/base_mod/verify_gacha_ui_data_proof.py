"""Verify the exact JP 15.7.1 tiny Rare Gacha original-UI data proof.

This verifier reads the encrypted DataLocal containers from the original and
modified InstallPack APKs. It proves that the four allowed gacha tables preserve
all original rows and append exactly one set.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile

from tools.battlecats_pack import PackReader
from tools.base_mod.patch_installpack_data import (
    DATALOCAL_LIST,
    DATALOCAL_PACK,
    INSTALLPACK_SPLIT,
)
from tools.base_mod.super_gacha_data_prototype import OPTION, R1, R2, R3


EXPECTED_SET_ID = 1089


def _data_reader(apk: Path) -> PackReader:
    with zipfile.ZipFile(apk, "r") as archive:
        manifest = archive.read(DATALOCAL_LIST)
        pack = archive.read(DATALOCAL_PACK)
    return PackReader(
        "DataLocal",
        manifest,
        pack,
        region="jp",
    )


def _lines(reader: PackReader, name: str) -> list[str]:
    payload, _ = reader.read(name)
    return payload.decode("utf-8-sig", "replace").splitlines()


def _parse_units(line: str) -> list[int]:
    values: list[int] = []
    for raw in line.split(","):
        raw = raw.strip()
        if not raw:
            continue
        value = int(raw)
        if value == -1:
            break
        values.append(value)
    return values


def verify_gacha_ui_data_proof(
    original_dir: Path,
    modified_dir: Path,
    *,
    expected_units: list[int],
    clone_option_set: int,
    expected_set_id: int = EXPECTED_SET_ID,
) -> dict:
    original_reader = _data_reader(original_dir / INSTALLPACK_SPLIT)
    modified_reader = _data_reader(modified_dir / INSTALLPACK_SPLIT)

    original = {
        name: _lines(original_reader, name)
        for name in (R1, R2, R3, OPTION)
    }
    modified = {
        name: _lines(modified_reader, name)
        for name in (R1, R2, R3, OPTION)
    }

    if len(original[R1]) != expected_set_id:
        raise ValueError(
            f"original R1 row count drift: {len(original[R1])} != {expected_set_id}"
        )
    if len(original[R2]) != expected_set_id:
        raise ValueError("original R2 row count drift")
    if len(original[R3]) != expected_set_id:
        raise ValueError("original R3 row count drift")
    if len(original[OPTION]) != expected_set_id + 1:
        raise ValueError("original option row count drift")

    for name in (R1, R2, R3):
        if len(modified[name]) != len(original[name]) + 1:
            raise ValueError(f"{name}: expected exactly one appended row")
        if modified[name][:-1] != original[name]:
            raise ValueError(f"{name}: an original row was modified")

    if len(modified[OPTION]) != len(original[OPTION]) + 1:
        raise ValueError("option table: expected exactly one appended row")
    if modified[OPTION][:-1] != original[OPTION]:
        raise ValueError("option table: an original row was modified")

    appended_units = _parse_units(modified[R1][-1])
    if appended_units != expected_units:
        raise ValueError(
            f"appended R1 pool drift: {appended_units} != {expected_units}"
        )
    if modified[R2][-1].strip() != "-1":
        raise ValueError("appended R2 row is not empty")
    if modified[R3][-1].strip() != "-1":
        raise ValueError("appended R3 row is not empty")

    if clone_option_set < 0 or clone_option_set >= expected_set_id:
        raise ValueError("clone option set outside exact original range")
    clone_cells = original[OPTION][clone_option_set + 1].split("\t")
    appended_cells = modified[OPTION][-1].split("\t")
    if len(appended_cells) != len(clone_cells):
        raise ValueError("appended option column count drift")
    if int(appended_cells[0]) != expected_set_id:
        raise ValueError("appended option set id drift")
    if int(appended_cells[1]) != 1:
        raise ValueError("appended option BannerON is not 1")
    if appended_cells[1:] != clone_cells[1:]:
        raise ValueError(
            "appended option metadata differs from selected visible clone"
        )

    return {
        "schema_version": 1,
        "mode": "gacha-original-ui-data-proof",
        "new_set_id": expected_set_id,
        "prototype_unit_ids": expected_units,
        "clone_option_set": clone_option_set,
        "original_r1_rows": len(original[R1]),
        "modified_r1_rows": len(modified[R1]),
        "original_rows_preserved": True,
        "appended_rows_per_table": 1,
        "r2_empty": True,
        "r3_empty": True,
        "banner_on": True,
        "option_metadata_cloned": True,
        "changed_data_files": [R1, R2, R3, OPTION],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_dir", type=Path)
    parser.add_argument("modified_dir", type=Path)
    parser.add_argument("--unit", action="append", type=int, required=True)
    parser.add_argument("--clone-option-set", type=int, required=True)
    parser.add_argument("--expected-set-id", type=int, default=EXPECTED_SET_ID)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = verify_gacha_ui_data_proof(
        args.original_dir.resolve(),
        args.modified_dir.resolve(),
        expected_units=args.unit,
        clone_option_set=args.clone_option_set,
        expected_set_id=args.expected_set_id,
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
