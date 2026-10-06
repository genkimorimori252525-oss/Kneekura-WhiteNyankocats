"""Append owner-local override entries to DownloadLocal inside InstallPack.

This preservation-first patch leaves DataLocal.list/DataLocal.pack completely
unchanged. It modifies only the existing DownloadLocal.list/.pack overlay pair,
preserving every original DownloadLocal entry byte-for-byte and appending new
encrypted files.

This follows the same overlay family used by modern Battle Cats mod exporters
instead of rewriting the built-in DataLocal container, which is associated with
the game's H01 pack/list integrity error.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import zipfile

from tools.base_mod.battlecats_pack_writer import append_pack_entries
from tools.base_mod.package_flavor import _rewrite_apk
from tools.base_mod.repack import JP_15_7_1_SPLITS, sha256_file


INSTALLPACK_SPLIT = "split_InstallPack.apk"
DOWNLOADLOCAL_LIST = "assets/DownloadLocal.list"
DOWNLOADLOCAL_PACK = "assets/DownloadLocal.pack"
DATALOCAL_LIST = "assets/DataLocal.list"
DATALOCAL_PACK = "assets/DataLocal.pack"


def patch_installpack_apk(
    source_apk: Path,
    target_apk: Path,
    additions: dict[str, bytes],
) -> dict:
    if not additions:
        raise ValueError("at least one DownloadLocal addition is required")

    with zipfile.ZipFile(source_apk, "r") as archive:
        names = set(archive.namelist())
        for required in (
            DOWNLOADLOCAL_LIST,
            DOWNLOADLOCAL_PACK,
            DATALOCAL_LIST,
            DATALOCAL_PACK,
        ):
            if required not in names:
                raise ValueError(
                    f"{source_apk.name}: missing required {required}"
                )
        download_manifest = archive.read(DOWNLOADLOCAL_LIST)
        download_pack = archive.read(DOWNLOADLOCAL_PACK)
        datalocal_manifest_before = archive.read(DATALOCAL_LIST)
        datalocal_pack_before = archive.read(DATALOCAL_PACK)

    new_manifest, new_pack, pack_ledger = append_pack_entries(
        "DownloadLocal",
        download_manifest,
        download_pack,
        additions,
        region="jp",
    )

    _rewrite_apk(
        source_apk,
        target_apk,
        {
            DOWNLOADLOCAL_LIST: new_manifest,
            DOWNLOADLOCAL_PACK: new_pack,
        },
    )

    with zipfile.ZipFile(target_apk, "r") as archive:
        if archive.read(DATALOCAL_LIST) != datalocal_manifest_before:
            raise RuntimeError("DataLocal.list changed during DownloadLocal overlay patch")
        if archive.read(DATALOCAL_PACK) != datalocal_pack_before:
            raise RuntimeError("DataLocal.pack changed during DownloadLocal overlay patch")

    return {
        "schema_version": 1,
        "mode": "downloadlocal-append-overlay",
        "input_apk_sha256": sha256_file(source_apk),
        "output_apk_sha256_unsigned": sha256_file(target_apk),
        "changed_apk_entries": [DOWNLOADLOCAL_LIST, DOWNLOADLOCAL_PACK],
        "added_downloadlocal_entries": sorted(additions),
        "datalocal_preserved_byte_identical": True,
        "pack_ledger": pack_ledger,
    }


def patch_split_set(
    split_dir: Path,
    output_dir: Path,
    additions: dict[str, bytes],
) -> dict:
    missing = [
        name for name in JP_15_7_1_SPLITS if not (split_dir / name).is_file()
    ]
    if missing:
        raise FileNotFoundError(
            "incomplete JP 15.7.1 split set; missing: " + ", ".join(missing)
        )
    if not additions:
        raise ValueError("at least one DownloadLocal addition is required")

    output_dir.mkdir(parents=True, exist_ok=True)
    split_rows = []
    installpack_ledger = None

    for split_name in JP_15_7_1_SPLITS:
        source = split_dir / split_name
        target = output_dir / split_name
        if split_name == INSTALLPACK_SPLIT:
            installpack_ledger = patch_installpack_apk(
                source,
                target,
                additions,
            )
            split_rows.append(
                {
                    "name": split_name,
                    "changed": True,
                    "input_sha256": installpack_ledger["input_apk_sha256"],
                    "output_sha256_unsigned": installpack_ledger[
                        "output_apk_sha256_unsigned"
                    ],
                }
            )
        else:
            shutil.copy2(source, target)
            split_rows.append(
                {
                    "name": split_name,
                    "changed": False,
                    "input_sha256": sha256_file(source),
                    "output_sha256_unsigned": sha256_file(target),
                }
            )

    if installpack_ledger is None:
        raise RuntimeError("InstallPack split was not processed")

    ledger = {
        "schema_version": 1,
        "anchor": "jp-15.7.1",
        "mode": "downloadlocal-overlay-split-set-patch",
        "added_downloadlocal_entries": sorted(additions),
        "datalocal_preserved_byte_identical": True,
        "splits": split_rows,
        "installpack": installpack_ledger,
    }
    (output_dir / "downloadlocal-overlay-ledger.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return ledger


def _parse_addition(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError(
            "addition must use ENTRY_NAME=/path/to/plaintext"
        )
    name, raw_path = value.split("=", 1)
    name = name.strip()
    if not name:
        raise argparse.ArgumentTypeError("addition entry name is empty")
    return name, Path(raw_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("split_dir", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--add",
        action="append",
        required=True,
        metavar="ENTRY=FILE",
    )
    args = parser.parse_args()

    additions: dict[str, bytes] = {}
    for raw in args.add:
        name, path = _parse_addition(raw)
        if name in additions:
            raise SystemExit(f"duplicate addition: {name}")
        additions[name] = path.read_bytes()

    ledger = patch_split_set(
        args.split_dir.resolve(),
        args.output.resolve(),
        additions,
    )
    print(json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
