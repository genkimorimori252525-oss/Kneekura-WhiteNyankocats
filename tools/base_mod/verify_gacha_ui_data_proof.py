"""Verify the exact JP 15.7.1 tiny Rare Gacha original-UI overlay proof.

The preservation-first proof leaves the built-in DataLocal.list/.pack bytes
untouched and appends four complete override files to the existing
DownloadLocal overlay pack.

The verifier proves:
- DataLocal.list and DataLocal.pack are byte-identical to the exact source;
- every original DownloadLocal payload is preserved;
- the four gacha override files exist only in DownloadLocal;
- each override equals the exact original table plus one append-only set 1089.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile

from tools.battlecats_pack import PackReader
from tools.base_mod.patch_installpack_downloadlocal import (
    DATALOCAL_LIST,
    DATALOCAL_PACK,
    DOWNLOADLOCAL_LIST,
    DOWNLOADLOCAL_PACK,
    INSTALLPACK_SPLIT,
)
from tools.base_mod.super_gacha_data_prototype import OPTION, R1, R2, R3


EXPECTED_SET_ID = 1089


def _reader(
    apk: Path,
    family: str,
    manifest_name: str,
    pack_name: str,
) -> PackReader:
    with zipfile.ZipFile(apk, "r") as archive:
        manifest = archive.read(manifest_name)
        pack = archive.read(pack_name)
    return PackReader(
        family,
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
    original_apk = original_dir / INSTALLPACK_SPLIT
    modified_apk = modified_dir / INSTALLPACK_SPLIT

    with zipfile.ZipFile(original_apk, "r") as before, zipfile.ZipFile(
        modified_apk, "r"
    ) as after:
        if after.read(DATALOCAL_LIST) != before.read(DATALOCAL_LIST):
            raise ValueError("DataLocal.list changed in overlay proof")
        if after.read(DATALOCAL_PACK) != before.read(DATALOCAL_PACK):
            raise ValueError("DataLocal.pack changed in overlay proof")

    original_data = _reader(
        original_apk,
        "DataLocal",
        DATALOCAL_LIST,
        DATALOCAL_PACK,
    )
    original_download = _reader(
        original_apk,
        "DownloadLocal",
        DOWNLOADLOCAL_LIST,
        DOWNLOADLOCAL_PACK,
    )
    modified_download = _reader(
        modified_apk,
        "DownloadLocal",
        DOWNLOADLOCAL_LIST,
        DOWNLOADLOCAL_PACK,
    )

    original = {
        name: _lines(original_data, name)
        for name in (R1, R2, R3, OPTION)
    }
    override = {
        name: _lines(modified_download, name)
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
        if len(override[name]) != len(original[name]) + 1:
            raise ValueError(f"{name}: overlay must contain exactly one appended row")
        if override[name][:-1] != original[name]:
            raise ValueError(f"{name}: overlay changed an original row")

    if len(override[OPTION]) != len(original[OPTION]) + 1:
        raise ValueError("option overlay must contain exactly one appended row")
    if override[OPTION][:-1] != original[OPTION]:
        raise ValueError("option overlay changed an original row")

    appended_units = _parse_units(override[R1][-1])
    if appended_units != expected_units:
        raise ValueError(
            f"appended R1 pool drift: {appended_units} != {expected_units}"
        )
    if override[R2][-1].strip() != "-1":
        raise ValueError("appended R2 row is not empty")
    if override[R3][-1].strip() != "-1":
        raise ValueError("appended R3 row is not empty")

    if clone_option_set < 0 or clone_option_set >= expected_set_id:
        raise ValueError("clone option set outside exact original range")
    clone_cells = original[OPTION][clone_option_set + 1].split("\t")
    appended_cells = override[OPTION][-1].split("\t")
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

    # Existing DownloadLocal content must survive unchanged at payload level.
    for entry in original_download.entries:
        before_payload, _ = original_download.read(entry.name)
        after_payload, _ = modified_download.read(entry.name)
        if after_payload != before_payload:
            raise ValueError(
                f"original DownloadLocal payload changed: {entry.name}"
            )

    return {
        "schema_version": 2,
        "mode": "gacha-original-ui-downloadlocal-overlay-proof",
        "new_set_id": expected_set_id,
        "prototype_unit_ids": expected_units,
        "clone_option_set": clone_option_set,
        "original_r1_rows": len(original[R1]),
        "overlay_r1_rows": len(override[R1]),
        "original_rows_preserved": True,
        "appended_rows_per_table": 1,
        "r2_empty": True,
        "r3_empty": True,
        "banner_on": True,
        "option_metadata_cloned": True,
        "datalocal_byte_identical": True,
        "downloadlocal_original_payloads_preserved": True,
        "overlay_entries": [R1, R2, R3, OPTION],
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
