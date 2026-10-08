"""Analyze the exact JP 15.7.1 additional-download gate.

This is a read-only owner-export audit. It reads the download_*.tsv tables from
split_InstallPack.apk and the native download-version vector from the ARM64
split. It does not contact PONOS servers and it does not modify an APK.

The primary purpose is to distinguish:
- a missing server-asset bootstrap/download gate; from
- a later gacha/event visibility decision.

For exact JP 15.7.1 the 35 archive sizes sum to the ~615 MiB prompt shown by the
original game on a fresh isolated package.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
import zipfile


EXPECTED_EXPORT_SHA256 = (
    "38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56"
)
EXPECTED_LANE_COUNT = 35
EXPECTED_TOTAL_ARCHIVE_BYTES = 645_599_537
EXPECTED_NATIVE_VERSIONS = [
    5,
    5,
    5,
    7_000_000,
    7,
    5,
    5,
    7_000_001,
    1,
    7_000_000,
    7_010_000,
    8_070_001,
    9_000_003,
    9_040_000,
    9_090_000,
    10_000_001,
    10_030_000,
    10_030_001,
    10_090_000,
    10_090_001,
    11_010_000,
    11_010_001,
    11_050_000,
    11_090_000,
    12_060_000,
    12_060_001,
    13_040_000,
    13_070_000,
    13_070_001,
    14_020_000,
    14_040_000,
    14_040_001,
    14_050_000,
    14_060_000,
    15_040_000,
]

VERSION_VECTOR_ANCHOR = [5, 5, 5, 7_000_000]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_download_tsv(payload: bytes, lane: int) -> dict:
    text = payload.decode("utf-8-sig", "replace")
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError(f"download_{lane}.tsv is empty")

    header = lines[0].split("\t")
    if len(header) < 3 or header[0].strip():
        raise ValueError(f"download_{lane}.tsv first row shape drift")
    try:
        archive_size = int(header[1])
    except ValueError as exc:
        raise ValueError(f"download_{lane}.tsv archive size is invalid") from exc
    archive_md5 = header[2].strip().lower()
    if len(archive_md5) != 32:
        raise ValueError(f"download_{lane}.tsv archive MD5 shape drift")

    entries: list[dict] = []
    for row_no, line in enumerate(lines[1:], start=2):
        cells = line.split("\t")
        if len(cells) < 3:
            raise ValueError(
                f"download_{lane}.tsv row {row_no} has fewer than 3 columns"
            )
        name = cells[0].strip()
        if not name:
            raise ValueError(f"download_{lane}.tsv row {row_no} has empty name")
        try:
            size = int(cells[1])
        except ValueError as exc:
            raise ValueError(
                f"download_{lane}.tsv row {row_no} has invalid size"
            ) from exc
        md5 = cells[2].strip().lower()
        if len(md5) != 32:
            raise ValueError(
                f"download_{lane}.tsv row {row_no} has invalid MD5 shape"
            )
        entries.append({"name": name, "size": size, "md5": md5})

    return {
        "lane": lane,
        "archive_size": archive_size,
        "archive_md5": archive_md5,
        "entry_count": len(entries),
        "extracted_bytes": sum(row["size"] for row in entries),
        "entries": entries,
    }


def derive_native_download_versions(native: bytes, lane_count: int) -> list[int]:
    anchor = struct.pack(
        "<" + "I" * len(VERSION_VECTOR_ANCHOR),
        *VERSION_VECTOR_ANCHOR,
    )
    hits: list[int] = []
    cursor = 0
    while True:
        found = native.find(anchor, cursor)
        if found < 0:
            break
        hits.append(found)
        cursor = found + 1
    if len(hits) != 1:
        raise ValueError(
            f"native download-version anchor expected once, got {len(hits)}"
        )

    start = hits[0]
    required = lane_count * 4
    if start + required > len(native):
        raise ValueError("native download-version vector is truncated")
    return list(struct.unpack_from("<" + "I" * lane_count, native, start))


def build_lane_url(lane: int, game_version: int) -> str:
    project = "battlecats"
    if game_version < 1_000_000:
        stem = f"{project}_{game_version}_{lane}"
    else:
        stem = (
            f"{project}_{game_version // 100:06d}_"
            f"{lane:02d}_{game_version % 100:02d}"
        )
    return (
        "https://nyanko-assets.ponosgames.com/iphone/"
        f"{project}/download/{stem}.zip"
    )


def analyze_export(export_zip: Path) -> dict:
    export_zip = export_zip.resolve()
    digest = sha256_file(export_zip)
    if digest != EXPECTED_EXPORT_SHA256:
        raise ValueError(
            f"owner export SHA drift: expected {EXPECTED_EXPORT_SHA256}, got {digest}"
        )

    with zipfile.ZipFile(export_zip, "r") as outer:
        installpack_bytes = outer.read("apk/split_InstallPack.apk")
        arm64_bytes = outer.read("apk/split_config.arm64_v8a.apk")

        shared_prefix = "shared/jp.co.ponos.battlecats/files/"
        shared_files = [
            name
            for name in outer.namelist()
            if name.startswith(shared_prefix)
            and name != shared_prefix
            and not name.endswith("/")
        ]

    with zipfile.ZipFile(io.BytesIO(installpack_bytes), "r") as installpack:
        lanes: list[dict] = []
        lane = 0
        while True:
            name = f"assets/download_{lane}.tsv"
            try:
                payload = installpack.read(name)
            except KeyError:
                break
            lanes.append(parse_download_tsv(payload, lane))
            lane += 1

    if len(lanes) != EXPECTED_LANE_COUNT:
        raise ValueError(
            f"download lane count drift: expected {EXPECTED_LANE_COUNT}, got {len(lanes)}"
        )

    with zipfile.ZipFile(io.BytesIO(arm64_bytes), "r") as arm64:
        native = arm64.read("lib/arm64-v8a/libnative-lib.so")

    versions = derive_native_download_versions(native, len(lanes))
    if versions != EXPECTED_NATIVE_VERSIONS:
        raise ValueError("native download-version vector drift")

    total = sum(row["archive_size"] for row in lanes)
    if total != EXPECTED_TOTAL_ARCHIVE_BYTES:
        raise ValueError(
            "download archive total drift: "
            f"expected {EXPECTED_TOTAL_ARCHIVE_BYTES}, got {total}"
        )

    for lane, game_version in zip(lanes, versions):
        lane["game_version"] = game_version
        lane["url"] = build_lane_url(lane["lane"], game_version)

    largest = max(lanes, key=lambda row: row["archive_size"])
    return {
        "schema_version": 1,
        "mode": "jp-15.7.1-server-download-gate-audit",
        "source_export_sha256": digest,
        "download_lane_count": len(lanes),
        "total_archive_bytes": total,
        "total_archive_mib": total / (1024 * 1024),
        "total_archive_mb_decimal": total / 1_000_000,
        "fresh_export_shared_files_count": len(shared_files),
        "fresh_export_contains_preseeded_server_files": bool(shared_files),
        "largest_lane": {
            "lane": largest["lane"],
            "archive_size": largest["archive_size"],
            "archive_md5": largest["archive_md5"],
            "entry_count": largest["entry_count"],
        },
        "lanes": lanes,
        "conclusion": {
            "gate_classification": "missing_original_server_asset_archives",
            "matches_615_mib_prompt": 615.0 <= total / (1024 * 1024) < 617.0,
            "gacha_schedule_inference_allowed": False,
            "reason": (
                "The exact 35 original download tables sum to the observed "
                "~615 MiB prompt, while the owned export contains no preseeded "
                "files under the app files directory. The Rare Gacha scene was "
                "therefore not reached, so banner visibility cannot yet prove "
                "or disprove a gacha schedule provider."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export_zip", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = analyze_export(args.export_zip)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
