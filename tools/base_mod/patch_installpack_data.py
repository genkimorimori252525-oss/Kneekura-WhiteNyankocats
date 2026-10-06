"""Patch decrypted DataLocal entries inside split_InstallPack.apk.

The tool is data-first and intentionally narrow:
- only assets/DataLocal.list and assets/DataLocal.pack are replaced;
- all other InstallPack ZIP entries are copied unchanged;
- DataLocal entry order is preserved;
- unchanged encrypted DataLocal chunks are copied verbatim;
- a ledger names every changed decrypted entry.

APK signing/package separation remain separate later stages.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import zipfile

from tools.base_mod.battlecats_pack_writer import rebuild_pack
from tools.base_mod.package_flavor import _rewrite_apk
from tools.base_mod.repack import JP_15_7_1_SPLITS, sha256_file


INSTALLPACK_SPLIT = "split_InstallPack.apk"
DATALOCAL_LIST = "assets/DataLocal.list"
DATALOCAL_PACK = "assets/DataLocal.pack"


def patch_installpack_apk(
    source_apk: Path,
    target_apk: Path,
    replacements: dict[str, bytes],
) -> dict:
    with zipfile.ZipFile(source_apk, "r") as archive:
        names = set(archive.namelist())
        for required in (DATALOCAL_LIST, DATALOCAL_PACK):
            if required not in names:
                raise ValueError(
                    f"{source_apk.name}: missing required {required}"
                )
        manifest = archive.read(DATALOCAL_LIST)
        pack = archive.read(DATALOCAL_PACK)

    new_manifest, new_pack, pack_ledger = rebuild_pack(
        "DataLocal",
        manifest,
        pack,
        replacements,
        region="jp",
    )

    _rewrite_apk(
        source_apk,
        target_apk,
        {
            DATALOCAL_LIST: new_manifest,
            DATALOCAL_PACK: new_pack,
        },
    )

    return {
        "schema_version": 1,
        "mode": "datalocal-entry-patch",
        "input_apk_sha256": sha256_file(source_apk),
        "output_apk_sha256_unsigned": sha256_file(target_apk),
        "changed_apk_entries": [DATALOCAL_LIST, DATALOCAL_PACK],
        "changed_datalocal_entries": sorted(replacements),
        "pack_ledger": pack_ledger,
    }


def patch_split_set(
    split_dir: Path,
    output_dir: Path,
    replacements: dict[str, bytes],
) -> dict:
    missing = [
        name for name in JP_15_7_1_SPLITS if not (split_dir / name).is_file()
    ]
    if missing:
        raise FileNotFoundError(
            "incomplete JP 15.7.1 split set; missing: " + ", ".join(missing)
        )
    if not replacements:
        raise ValueError("at least one DataLocal replacement is required")

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
                replacements,
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
        "mode": "datalocal-split-set-patch",
        "changed_datalocal_entries": sorted(replacements),
        "splits": split_rows,
        "installpack": installpack_ledger,
    }
    (output_dir / "datalocal-patch-ledger.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return ledger


def _parse_replacement(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError(
            "replacement must use ENTRY_NAME=/path/to/plaintext"
        )
    name, raw_path = value.split("=", 1)
    name = name.strip()
    if not name:
        raise argparse.ArgumentTypeError("replacement entry name is empty")
    return name, Path(raw_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("split_dir", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--replace",
        action="append",
        required=True,
        metavar="ENTRY=FILE",
    )
    args = parser.parse_args()

    replacements: dict[str, bytes] = {}
    for raw in args.replace:
        name, path = _parse_replacement(raw)
        if name in replacements:
            raise SystemExit(f"duplicate replacement: {name}")
        replacements[name] = path.read_bytes()

    ledger = patch_split_set(
        args.split_dir.resolve(),
        args.output.resolve(),
        replacements,
    )
    print(json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
