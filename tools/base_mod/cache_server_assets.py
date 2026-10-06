"""Build a verified local cache of the original JP 15.7.1 server assets.

The exact owned export supplies all download_*.tsv file names, sizes and MD5
integrity values plus the native per-lane game-version vector. This command
uses those tables as the authority.

No Battle Cats payload is committed to Git. The cache is owner-local.

Network mode intentionally delegates CloudFront cookie generation to the pinned
TBCML implementation instead of copying its signing material into this
repository.

Install the optional dependency when network download is required:

    python -m pip install \
      "git+https://github.com/fieryhenry/tbcml.git@9bb62d99b2b1e0da113c5592685a47f720bf7a4d"

The downloaded zip for each lane is verified against the exact archive size and
MD5 from download_<lane>.tsv. Every extracted file is also size/MD5 verified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request
import zipfile

from tools.base_mod.analyze_server_download_gate import analyze_export


PINNED_TBCML_COMMIT = "9bb62d99b2b1e0da113c5592685a47f720bf7a4d"
TBCML_INSTALL_HINT = (
    "python -m pip install "
    f"\"git+https://github.com/fieryhenry/tbcml.git@{PINNED_TBCML_COMMIT}\""
)


def md5_file(path: Path) -> str:
    # MD5 is used only to match the original game's published integrity table,
    # not as a security primitive.
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
        "lanes": [
            {
                "lane": row["lane"],
                "game_version": row["game_version"],
                "url": row["url"],
                "archive_size": row["archive_size"],
                "archive_md5": row["archive_md5"],
                "entry_count": row["entry_count"],
            }
            for row in gate["lanes"]
        ],
    }


def _cloudfront_cookie() -> str:
    try:
        from tbcml.server_handler import CloudFront  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "Pinned TBCML is required only for server download. Install it with: "
            + TBCML_INSTALL_HINT
        ) from exc
    return CloudFront().generate_signed_cookie(
        "https://nyanko-assets.ponosgames.com/*"
    )


def download_lane(
    lane: dict,
    target: Path,
    *,
    cookie: str,
    progress: bool = True,
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_suffix(target.suffix + ".part")
    if part.exists():
        part.unlink()

    request = urllib.request.Request(
        lane["url"],
        headers={
            "Accept-Encoding": "identity",
            "Connection": "keep-alive",
            "Cookie": cookie,
            "Range": "bytes=0-",
            "User-Agent": (
                "Dalvik/2.1.0 "
                "(Linux; U; Android 9; Pixel 2 Build/PQ3A.190801.002)"
            ),
        },
    )

    downloaded = 0
    with urllib.request.urlopen(request, timeout=120) as response, part.open("wb") as out:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
            downloaded += len(chunk)
            if progress:
                print(
                    f"lane {lane['lane']:02d}: "
                    f"{downloaded}/{lane['archive_size']} bytes",
                    end="\r",
                )
    if progress:
        print()

    if not file_matches(
        part,
        size=lane["archive_size"],
        md5=lane["archive_md5"],
    ):
        actual_size = part.stat().st_size if part.exists() else -1
        actual_md5 = md5_file(part) if part.exists() else "<missing>"
        part.unlink(missing_ok=True)
        raise ValueError(
            f"lane {lane['lane']:02d} archive integrity mismatch: "
            f"size {actual_size}/{lane['archive_size']} "
            f"md5 {actual_md5}/{lane['archive_md5']}"
        )
    part.replace(target)


def verify_archive_members(archive_path: Path, lane: dict) -> dict[str, bytes]:
    expected = {row["name"]: row for row in lane["entries"]}
    payloads: dict[str, bytes] = {}
    with zipfile.ZipFile(archive_path, "r") as archive:
        names = {
            name
            for name in archive.namelist()
            if name and not name.endswith("/")
        }
        missing = sorted(set(expected) - names)
        if missing:
            raise ValueError(
                f"lane {lane['lane']:02d} archive is missing TSV entries: "
                + ", ".join(missing[:12])
            )
        for name, row in expected.items():
            payload = archive.read(name)
            if len(payload) != row["size"]:
                raise ValueError(
                    f"lane {lane['lane']:02d}/{name}: size mismatch"
                )
            md5 = hashlib.md5(payload).hexdigest()
            if md5 != row["md5"]:
                raise ValueError(
                    f"lane {lane['lane']:02d}/{name}: MD5 mismatch"
                )
            payloads[name] = payload
    return payloads


def build_server_cache(
    export_zip: Path,
    cache_dir: Path,
    *,
    keep_archives: bool = False,
    lane_filter: set[int] | None = None,
) -> dict:
    gate = analyze_export(export_zip)
    lanes = gate["lanes"]
    latest = latest_file_map(lanes)

    cache_dir = cache_dir.resolve()
    archives_dir = cache_dir / "archives"
    files_dir = cache_dir / "files"
    archives_dir.mkdir(parents=True, exist_ok=True)
    files_dir.mkdir(parents=True, exist_ok=True)

    if lane_filter is not None:
        unknown = sorted(lane_filter - {row["lane"] for row in lanes})
        if unknown:
            raise ValueError(f"unknown lane(s): {unknown}")

    cookie: str | None = None
    lane_rows: list[dict] = []

    for lane in lanes:
        lane_no = lane["lane"]
        if lane_filter is not None and lane_no not in lane_filter:
            continue

        final_entries = [
            entry
            for entry in lane["entries"]
            if latest[entry["name"]]["lane"] == lane_no
        ]
        already_valid = all(
            file_matches(
                files_dir / entry["name"],
                size=entry["size"],
                md5=entry["md5"],
            )
            for entry in final_entries
        )
        if already_valid and final_entries:
            lane_rows.append(
                {
                    "lane": lane_no,
                    "status": "cached",
                    "final_entry_count": len(final_entries),
                }
            )
            continue

        archive_path = archives_dir / f"lane-{lane_no:02d}.zip"
        if not file_matches(
            archive_path,
            size=lane["archive_size"],
            md5=lane["archive_md5"],
        ):
            if cookie is None:
                cookie = _cloudfront_cookie()
            print(
                f"Downloading lane {lane_no:02d}/{len(lanes)-1:02d} "
                f"({lane['archive_size']} bytes)"
            )
            download_lane(lane, archive_path, cookie=cookie)

        payloads = verify_archive_members(archive_path, lane)
        for entry in final_entries:
            path = files_dir / entry["name"]
            path.parent.mkdir(parents=True, exist_ok=True)
            temp = path.with_suffix(path.suffix + ".part")
            temp.write_bytes(payloads[entry["name"]])
            if not file_matches(temp, size=entry["size"], md5=entry["md5"]):
                temp.unlink(missing_ok=True)
                raise RuntimeError(
                    f"post-write integrity failure: {entry['name']}"
                )
            temp.replace(path)

        lane_rows.append(
            {
                "lane": lane_no,
                "status": "downloaded-and-verified",
                "final_entry_count": len(final_entries),
            }
        )
        if not keep_archives:
            archive_path.unlink(missing_ok=True)

    # Full final-cache verification when all lanes were requested.
    verified_final_files = 0
    verified_final_bytes = 0
    complete = lane_filter is None
    if complete:
        for name, row in latest.items():
            path = files_dir / name
            if not file_matches(path, size=row["size"], md5=row["md5"]):
                raise ValueError(f"final server cache verification failed: {name}")
            verified_final_files += 1
            verified_final_bytes += row["size"]

    ledger = {
        "schema_version": 1,
        "mode": "jp-15.7.1-owner-local-server-cache",
        "source_export_sha256": gate["source_export_sha256"],
        "lane_count": gate["download_lane_count"],
        "expected_archive_bytes": gate["total_archive_bytes"],
        "complete": complete,
        "verified_final_files": verified_final_files,
        "verified_final_bytes": verified_final_bytes,
        "files_dir": str(files_dir),
        "keep_archives": keep_archives,
        "lanes": lane_rows,
        "note": (
            "Owner-local cache only. No Battle Cats server payload is committed "
            "to the repository."
        ),
    }
    (cache_dir / "server-cache-ledger.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return ledger


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export_zip", type=Path)
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--keep-archives", action="store_true")
    parser.add_argument("--lane", action="append", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.plan_only:
        result = build_cache_plan(args.export_zip)
    else:
        result = build_server_cache(
            args.export_zip,
            args.cache,
            keep_archives=args.keep_archives,
            lane_filter=set(args.lane) if args.lane else None,
        )

    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
