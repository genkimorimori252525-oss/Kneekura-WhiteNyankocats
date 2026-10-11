"""Private checksum-gated recovery of EXACT owner JP15.7.1 original server data.

Reads owner-private signed original `split_InstallPack.apk` download_0..34.tsv.
Uses PUBLIC historical mirror ONLY for files whose names/byte lengths
match that owner manifest. ALL bytes must match owner original size/MD5
before retaining them. Never modify owner export, Android/SAVE, publisher
app or GitHub. Does not claim playable/offline without all 358 originals.

Default `plan` is read-only and makes no HTTP requests. `download`
is an explicit local-PC operation; `verify` is offline/read-only.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
from urllib import request, error
from zipfile import ZipFile

from tools.base_mod.analyze_server_download_gate import parse_download_tsv
from tools.base_mod.fetch_godzilla_server_assets import (
    SOURCE, stage_verified, verify,
)

ORIGINAL_DOWNLOAD_ARCHIVE_BYTES = 645_599_537
ORIGINAL_MEMBER_COUNT = 358
ORIGINAL_TSV_COUNT = 35
PUBLIC_MIRROR_METADATA = (
    "https://api.github.com/repos/fieryhenry/BCData/contents/jp_server?ref=main"
)
PUBLIC_MIRROR = "fieryhenry/BCData (archived public historical mirror, NOT official)"
DEFAULT_OUT = Path("private/original-jp1571-verified-server-cache")
ENTRY_NAME = re.compile(r"[A-Za-z0-9_-]+\.(?:list|pack|ogg|caf)\Z")
MAX_WORKERS = 4


class OfflineOwnerCacheBlocked(ValueError):
    pass


def owner_manifest(apk: Path) -> dict[str, tuple[int, str]]:
    if not apk.is_file() or apk.is_symlink():
        raise OfflineOwnerCacheBlocked("exact owner InstallPack APK unavailable/unsafe")
    try:
        with ZipFile(apk) as archive:
            names = archive.namelist()
            files = {}
            archive_total = 0
            for index in range(ORIGINAL_TSV_COUNT):
                name = f"assets/download_{index}.tsv"
                if names.count(name) != 1:
                    raise OfflineOwnerCacheBlocked("original 35 TSV assets missing/duplicated")
                row = parse_download_tsv(archive.read(name), index)
                archive_total += row["archive_size"]
                for item in row["entries"]:
                    member = item["name"]
                    if (not ENTRY_NAME.fullmatch(member) or member in files
                        or not 0 < item["size"] <= 100_000_000
                        or not re.fullmatch(r"[a-f0-9]{32}", item["md5"])):
                        raise OfflineOwnerCacheBlocked(
                            "invalid or duplicate owner original download member")
                    files[member] = (item["size"], item["md5"])
    except (OSError, ValueError) as exc:
        if isinstance(exc, OfflineOwnerCacheBlocked):
            raise
        raise OfflineOwnerCacheBlocked("original InstallPack manifest unreadable") from exc
    if len(files) != ORIGINAL_MEMBER_COUNT or archive_total != ORIGINAL_DOWNLOAD_ARCHIVE_BYTES:
        raise OfflineOwnerCacheBlocked("original JP15.7.1 manifest shape/count drift")
    return files


def public_mirror_inventory(*, opener=request.urlopen) -> dict[str, int]:
    req = request.Request(
        PUBLIC_MIRROR_METADATA,
        headers={"User-Agent": "Kneekura-owner-private-original-cache-check/1.0"},
    )
    try:
        with opener(req, timeout=30) as response:
            if getattr(response, "status", 200) != 200:
                raise OfflineOwnerCacheBlocked("public historical mirror inventory HTTP failure")
            body = response.read(600_001)
            if len(body) > 600_000:
                raise OfflineOwnerCacheBlocked("public mirror metadata unusually large")
        result = json.loads(body)
    except (OSError, error.URLError, ValueError) as exc:
        if isinstance(exc, OfflineOwnerCacheBlocked):
            raise
        raise OfflineOwnerCacheBlocked("public historical mirror inventory unavailable") from None
    if not isinstance(result, list) or not 0 < len(result) <= 1000:
        raise OfflineOwnerCacheBlocked("public mirror inventory invalid")
    names = {}
    for record in result:
        if not isinstance(record, dict):
            raise OfflineOwnerCacheBlocked("mirror inventory member shape invalid")
        name, size = record.get("name"), record.get("size")
        if record.get("type") != "file" or not isinstance(name, str):
            continue
        if (ENTRY_NAME.fullmatch(name) is None or type(size) is not int
            or not 0 <= size <= 100_000_000 or name in names):
            raise OfflineOwnerCacheBlocked("mirror name/size unsafe")
        names[name] = size
    return names


def recover(*, repo: Path, candidate: Path, output: Path, mode: str = "plan",
            max_workers: int = MAX_WORKERS, opener=request.urlopen) -> dict:
    if mode not in {"plan", "download", "verify"}:
        raise OfflineOwnerCacheBlocked("unknown recovery mode")
    if type(max_workers) is not int or not 1 <= max_workers <= MAX_WORKERS:
        raise OfflineOwnerCacheBlocked("unsafe public mirror request concurrency")
    repo = repo.resolve(strict=True)
    root = repo / "private"
    if not root.is_dir() or root.is_symlink():
        raise OfflineOwnerCacheBlocked("owner-private root unavailable")
    root = root.resolve(strict=True)
    if output.is_symlink() or not output.resolve().is_relative_to(root):
        raise OfflineOwnerCacheBlocked("recovery output must be owner-private")
    if output.exists() and not output.is_dir():
        raise OfflineOwnerCacheBlocked("recovery destination unsafe")
    candidate = candidate.resolve(strict=True)
    if not candidate.is_relative_to(root):
        raise OfflineOwnerCacheBlocked("source signed original APK must be owner-private")
    manifest = owner_manifest(candidate / "split_InstallPack.apk")
    available: dict[str,int] = {}
    if mode == "download":
        mirror = public_mirror_inventory(opener=opener)
        available = {
            name: manifest[name][0] for name, sz in mirror.items()
            if name in manifest and manifest[name][0] == sz
        }
        if not available:
            raise OfflineOwnerCacheBlocked("historical mirror lacks exact sized source assets")
        # No network or disk write if owner machine does not have sufficient
        # headroom for the largest possible incomplete cache.
        required = sum(size for name, (size, _) in manifest.items()
                       if name in available and not (output / name).is_file())
        if shutil.disk_usage(root).free < required + 512 * 1024 * 1024:
            raise OfflineOwnerCacheBlocked("private disk free space insufficient")
        output.mkdir(parents=True, exist_ok=True)

        def download_one(name: str) -> tuple[str, bool]:
            target = output / name
            try:
                stage_verified(target, manifest[name], opener=opener)
                return name, True
            except (OSError, ValueError, error.URLError):
                return name, False

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            jobs = {pool.submit(download_one, name): name for name in sorted(available)}
            for task in as_completed(jobs):
                task.result()
    # Verification is LOCAL and must not fetch a substituted version.
    verified = []
    corrupt = []
    for name, info in sorted(manifest.items()):
        file = output / name
        if not file.exists():
            continue
        if file.is_symlink():
            corrupt.append(name)
            continue
        try:
            verify(file, info)
        except (OSError, ValueError):
            corrupt.append(name)
        else:
            verified.append(name)
    if corrupt:
        raise OfflineOwnerCacheBlocked("local cache contains mismatched or unsafe game assets")
    missing = sorted(set(manifest) - set(verified))
    count = len(verified)
    receipt = {
        "schema": "owner-private-jp1571-checksum-gated-server-cache-v1",
        "mode": mode,
        "status": ("EXACT_ORIGINAL_SERVER_CACHE_COMPLETE_NOT_INSTALLED"
                   if not missing else "PARTIAL_ORIGINAL_SERVER_CACHE_NOT_INSTALLABLE"),
        "expected_original_download_members": len(manifest),
        "verified_original_members": count,
        "missing_original_members": len(missing),
        "missing_names": missing,
        "verified_original_bytes": sum(manifest[name][0] for name in verified),
        "expected_extracted_original_bytes": sum(x[0] for x in manifest.values()),
        "original_35_download_archives_total_bytes": ORIGINAL_DOWNLOAD_ARCHIVE_BYTES,
        "all_original_member_MD5_proven": len(missing) == 0,
        "original_Android_runtime_assets_loaded": False,
        "APK_installed_or_SAVE_modified": False,
        "original_game_boot_verified": False,
        "mirror_bytes_committed_to_GitHub": False,
    }
    if mode == "download":
        (output / "PRIVATE-METADATA-ONLY-RECEIPT.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--mode", choices=("plan", "download", "verify"), default="plan")
    parser.add_argument("--workers", type=int, default=MAX_WORKERS)
    args = parser.parse_args()
    try:
        report = recover(
            repo=args.repo, candidate=args.candidate,
            output=args.out or args.repo / DEFAULT_OUT,
            mode=args.mode, max_workers=args.workers,
        )
    except (OfflineOwnerCacheBlocked, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps({
        k:v for k,v in report.items() if k != "missing_names"
    }, sort_keys=True))
    print("Owner original assets remain PRIVATE; no Android/SAVE changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
