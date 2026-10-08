"""Plan or verify the exact JP 15.7.1 original server-asset cache.

This tool is deliberately network-free. It reads the authoritative
download_*.tsv tables from the owner-provided exact export and verifies a local
files directory produced by the original Battle Cats downloader.

The research package can redirect getFilesDir() to its app-specific external
files directory. That makes the original 615 MiB bootstrap download reusable
and inspectable over ADB without root, while the original downloader remains
responsible for authentication, transport, and integrity acquisition.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from tools.base_mod.analyze_server_download_gate import analyze_export


def md5_file(path: Path) -> str:
    # MD5 is used only to match the original game's published integrity table.
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_matches(path: Path, *, size: int, md5: str) -> bool:
    return path.is_file() and path.stat().st_size == size and md5_file(path) == md5


def latest_file_map(lanes: list[dict]) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for lane in lanes:
        for entry in lane["entries"]:
            latest[entry["name"]] = {
                **entry,
                "lane": lane["lane"],
            }
    return latest


def build_cache_plan(export_zip: Path) -> dict:
    gate = analyze_export(export_zip)
    latest = latest_file_map(gate["lanes"])
    return {
        "schema_version": 1,
        "mode": "jp-15.7.1-server-cache-plan",
        "source_export_sha256": gate["source_export_sha256"],
        "lane_count": gate["download_lane_count"],
        "archive_bytes": gate["total_archive_bytes"],
        "archive_mib": gate["total_archive_mib"],
        "final_file_count": len(latest),
        "final_file_bytes": sum(row["size"] for row in latest.values()),
        "acquisition": "original-battle-cats-downloader-only",
        "research_files_dir": (
            "/sdcard/Android/data/jp.kn.trace.battlecats/files"
        ),
        "note": (
            "This repository does not generate server credentials or download "
            "the proprietary archives. Use the unchanged original in-app "
            "download flow in the isolated research package."
        ),
    }


def verify_server_files(export_zip: Path, files_dir: Path) -> dict:
    gate = analyze_export(export_zip)
    latest = latest_file_map(gate["lanes"])
    files_dir = files_dir.resolve()

    missing: list[str] = []
    invalid: list[dict] = []
    verified = 0
    verified_bytes = 0

    for name, row in sorted(latest.items()):
        path = files_dir / name
        if not path.is_file():
            missing.append(name)
            continue
        if path.stat().st_size != row["size"]:
            invalid.append(
                {
                    "name": name,
                    "reason": "size",
                    "expected": row["size"],
                    "actual": path.stat().st_size,
                }
            )
            continue
        actual_md5 = md5_file(path)
        if actual_md5 != row["md5"]:
            invalid.append(
                {
                    "name": name,
                    "reason": "md5",
                    "expected": row["md5"],
                    "actual": actual_md5,
                }
            )
            continue
        verified += 1
        verified_bytes += row["size"]

    complete = not missing and not invalid
    return {
        "schema_version": 1,
        "mode": "jp-15.7.1-server-cache-verification",
        "source_export_sha256": gate["source_export_sha256"],
        "files_dir": str(files_dir),
        "expected_final_files": len(latest),
        "verified_final_files": verified,
        "verified_final_bytes": verified_bytes,
        "complete": complete,
        "missing_count": len(missing),
        "invalid_count": len(invalid),
        "missing_sample": missing[:20],
        "invalid_sample": invalid[:20],
        "acquisition": "original-battle-cats-downloader-only",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export_zip", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan-only", action="store_true")
    mode.add_argument("--files-dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.plan_only:
        result = build_cache_plan(args.export_zip)
    else:
        result = verify_server_files(args.export_zip, args.files_dir)

    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result.get("complete", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
