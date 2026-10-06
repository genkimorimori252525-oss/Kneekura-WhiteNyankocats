"""Extract the exact six APK splits from the verified user-owned export."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile


EXPECTED_EXPORT_SHA256 = (
    "38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56"
)

EXPECTED_SPLITS = {
    "base.apk": {
        "size": 25913924,
        "sha256": "60e5e9df891b7be487abc4590fb3ca2e98218225efedbe4ba26b39dc10ce5c9a",
    },
    "split_config.arm64_v8a.apk": {
        "size": 15369082,
        "sha256": "3beb6c5096b5b9715873f3cfa4dc933fb641288cb97e7ca5af446496704cf213",
    },
    "split_config.en.apk": {
        "size": 49362,
        "sha256": "e93fbaade0e868134260a142fa49ebd8d06714370657077fd4b368582def4d59",
    },
    "split_config.ja.apk": {
        "size": 24786,
        "sha256": "1e557b1b203370d6e3836e774a83b1abc2f86babc42bdc0091907a2326ff819a",
    },
    "split_config.xxhdpi.apk": {
        "size": 239918,
        "sha256": "2948f5ff34ac441d9efab0060da91d04ebec0e30b7b586850c4e27defa8b2c90",
    },
    "split_InstallPack.apk": {
        "size": 132290560,
        "sha256": None,
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_owned_splits(export_zip: Path, output_dir: Path) -> dict:
    actual_export = sha256_file(export_zip)
    if actual_export != EXPECTED_EXPORT_SHA256:
        raise ValueError(
            "export SHA-256 mismatch: "
            f"expected {EXPECTED_EXPORT_SHA256}, got {actual_export}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []

    with zipfile.ZipFile(export_zip, "r") as outer:
        by_basename: dict[str, list[zipfile.ZipInfo]] = {}
        for info in outer.infolist():
            if info.is_dir():
                continue
            by_basename.setdefault(Path(info.filename).name, []).append(info)

        for name, expected in EXPECTED_SPLITS.items():
            matches = by_basename.get(name, [])
            if len(matches) != 1:
                raise ValueError(
                    f"expected exactly one {name}, found {len(matches)}"
                )
            info = matches[0]
            if info.file_size != expected["size"]:
                raise ValueError(
                    f"{name} size mismatch: expected {expected['size']}, "
                    f"got {info.file_size}"
                )

            target = output_dir / name
            with outer.open(info, "r") as reader, target.open("wb") as writer:
                shutil.copyfileobj(reader, writer, 1024 * 1024)

            digest = sha256_file(target)
            expected_digest = expected["sha256"]
            if expected_digest is not None and digest != expected_digest:
                raise ValueError(
                    f"{name} SHA-256 mismatch: "
                    f"expected {expected_digest}, got {digest}"
                )
            rows.append(
                {
                    "name": name,
                    "outer_path": info.filename,
                    "size": target.stat().st_size,
                    "sha256": digest,
                }
            )

    ledger = {
        "schema_version": 1,
        "source_export_sha256": actual_export,
        "splits": rows,
    }
    (output_dir / "source-split-ledger.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return ledger


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export_zip", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    ledger = extract_owned_splits(
        args.export_zip.resolve(),
        args.output.resolve(),
    )
    print(json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())