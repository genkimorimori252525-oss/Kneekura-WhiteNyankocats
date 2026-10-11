"""Read-only, per-lane original scene97 extra-data acceptance gate.

Anchored exclusively to 35 download_N.tsv members in the owner's **exact**
signed JP15.7.1 split_InstallPack.apk; validates *each* cached member against
its declared original byte length and MD5. Never fetches assets, writes to
Android, touches a SAVE, signs APKs or attempts to bypass DownloadBatchTask.

This is a SOURCE-COMPLETENESS gate, not proof of native source-index
registration, archive ZIP integrity, or original gameplay. Even 358/358
member verification does not authorize an Android import.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZipFile

from tools.base_mod.analyze_server_download_gate import parse_download_tsv
from tools.base_mod.fetch_godzilla_server_assets import verify
from tools.base_mod.recover_offline_original_server_cache import (
    OfflineOwnerCacheBlocked,
    ORIGINAL_DOWNLOAD_ARCHIVE_BYTES,
    ORIGINAL_MEMBER_COUNT,
    ORIGINAL_TSV_COUNT,
    owner_manifest,
)

STATUS_INCOMPLETE = "SCENE97_ORIGINAL_358_MEMBER_SOURCE_INCOMPLETE_NO_ANDROID_IMPORT"
STATUS_FULL = "SCENE97_ORIGINAL_MEMBER_BYTES_COMPLETE_NATIVE_LOADER_UNVERIFIED"


def _private_path(repo: Path, value: Path, *, exists: bool) -> Path:
    private = repo / "private"
    if not private.is_dir() or private.is_symlink():
        raise OfflineOwnerCacheBlocked("owner-private directory missing or unsafe")
    private = private.resolve(strict=True)
    original = value.absolute()
    current = original
    while current != current.parent and current != repo:
        if current.is_symlink():
            raise OfflineOwnerCacheBlocked("original data path contains symlink")
        current = current.parent
    result = original.resolve(strict=exists)
    if not result.is_relative_to(private):
        raise OfflineOwnerCacheBlocked("original data must remain owner-private")
    return result


def audit_scene97(*, repo: Path, candidate: Path, cache: Path) -> dict:
    """All read-only. No network, no Android operation, no source mutation."""
    repo = repo.resolve(strict=True)
    candidate = _private_path(repo, candidate, exists=True)
    cache = _private_path(repo, cache, exists=False)
    if not candidate.is_dir() or (cache.exists() and not cache.is_dir()):
        raise OfflineOwnerCacheBlocked("owner original APK/cache input type invalid")

    installpack = candidate / "split_InstallPack.apk"
    expected = owner_manifest(installpack)
    if len(expected) != ORIGINAL_MEMBER_COUNT:
        raise OfflineOwnerCacheBlocked("original InstallPack manifest member count drift")
    verified: set[str] = set()
    missing: set[str] = set()
    lane_receipts = []
    seen: set[str] = set()
    tsv_fingerprints = []
    archive_bytes = 0
    try:
        with ZipFile(installpack) as archive:
            names = archive.namelist()
            for index in range(ORIGINAL_TSV_COUNT):
                entry_name = f"assets/download_{index}.tsv"
                if names.count(entry_name) != 1:
                    raise OfflineOwnerCacheBlocked("original TSV missing or duplicated")
                tsv = archive.read(entry_name)
                if len(tsv) > 4 * 1024 * 1024:
                    raise OfflineOwnerCacheBlocked("oversized original TSV")
                lane = parse_download_tsv(tsv, index)
                tsv_fingerprints.append(sha256(tsv).hexdigest())
                archive_bytes += lane["archive_size"]
                ready = []
                absent = []
                for item in lane["entries"]:
                    name = item["name"]
                    if name in seen or expected.get(name) != (
                        item["size"], item["md5"]
                    ):
                        raise OfflineOwnerCacheBlocked("original lane member drift")
                    seen.add(name)
                    member = cache / name
                    if member.is_symlink():
                        raise OfflineOwnerCacheBlocked(
                            "untrusted symlink in original private cache")
                    if not member.is_file():
                        if member.exists():
                            raise OfflineOwnerCacheBlocked(
                                "invalid existing private original cache entry")
                        missing.add(name)
                        absent.append(name)
                        continue
                    # Original MD5 is a source-metadata integrity check, not
                    # a cryptographic authenticity assertion about its publisher.
                    try:
                        verify(member, (item["size"], item["md5"]))
                    except (OSError, ValueError) as exc:
                        raise OfflineOwnerCacheBlocked(
                            "existing original cache member byte/MD5 drift") from exc
                    verified.add(name)
                    ready.append(name)
                lane_receipts.append({
                    "lane": index,
                    "source_archive_declared_bytes": lane["archive_size"],
                    "source_archive_md5_from_original_tsv": lane["archive_md5"],
                    "source_download_tsv_sha256": tsv_fingerprints[-1],
                    "source_declared_members": len(lane["entries"]),
                    "member_verified_by_size_md5": len(ready),
                    "member_missing": len(absent),
                    "member_missing_names": absent,
                    "all_declared_members_verified": len(absent) == 0,
                    "original_archive_zip_bytes_verified": False,
                    "original_native_loader_accepted": False,
                })
    except (OSError, KeyError, ValueError) as exc:
        if isinstance(exc, OfflineOwnerCacheBlocked):
            raise
        raise OfflineOwnerCacheBlocked("original scene97 TSV audit could not complete") from exc

    if (seen != set(expected) or archive_bytes != ORIGINAL_DOWNLOAD_ARCHIVE_BYTES
        or len(lane_receipts) != ORIGINAL_TSV_COUNT
        or len(verified) + len(missing) != ORIGINAL_MEMBER_COUNT):
        raise OfflineOwnerCacheBlocked("original 35 lane counts or layout drift")

    is_complete = len(missing) == 0
    return {
        "schema": "kneekura-original-scene97-owner-private-readiness-v1",
        "status": STATUS_FULL if is_complete else STATUS_INCOMPLETE,
        "source": "owner signed JP15.7.1 split_InstallPack.apk / 35 original TSVs",
        "source_35_tsv_sha256": sha256(
            "".join(tsv_fingerprints).encode("ascii")).hexdigest(),
        "expected_lane_count": ORIGINAL_TSV_COUNT,
        "lanes_all_member_bytes_verified": sum(
            x["all_declared_members_verified"] for x in lane_receipts),
        "lanes_with_missing_members": sum(
            not x["all_declared_members_verified"] for x in lane_receipts),
        "expected_member_count": ORIGINAL_MEMBER_COUNT,
        "member_bytes_and_md5_verified_count": len(verified),
        "missing_member_count": len(missing),
        "missing_original_member_names": sorted(missing),
        "missing_original_member_total_bytes": sum(
            expected[n][0] for n in missing),
        "verified_original_member_total_bytes": sum(
            expected[n][0] for n in verified),
        "expected_original_member_total_bytes": sum(
            item[0] for item in expected.values()),
        "original_35_archives_declared_bytes": archive_bytes,
        "all_original_extracted_members_verified": is_complete,
        "original_35_archive_zip_md5_verified": False,
        "original_native_source_index_population_proven": False,
        "original_scene97_loader_accepted_data_proven": False,
        "device_install_or_SAVE_or_APK_mutated": False,
        "original_gameplay_offline_acceptance_proven": False,
        "android_import_authorized": False,
        "lanes": lane_receipts,
    }


def require_complete_source(audit: dict) -> None:
    """Hard stop for future original file import code; never authorize imports."""
    if (audit.get("status") != STATUS_FULL
        or audit.get("expected_member_count") != ORIGINAL_MEMBER_COUNT
        or audit.get("member_bytes_and_md5_verified_count") != ORIGINAL_MEMBER_COUNT
        or audit.get("missing_member_count") != 0
        or audit.get("all_original_extracted_members_verified") is not True):
        raise OfflineOwnerCacheBlocked(
            "SCENE97_IMPORT_BLOCKED_NOT_ALL_ORIGINAL_358_MEMBER_BYTES_PRESENT")
    # Completion merely unlocks investigating a separate native/ZIP mapping
    # proof. No Android import function exists in this module.


def save_private_metadata(*, repo: Path, destination: Path, report: dict) -> None:
    root = repo.resolve(strict=True)
    p = _private_path(root, destination, exists=False)
    if p.exists() or p.is_symlink() or p.parent.is_symlink():
        raise OfflineOwnerCacheBlocked("owner-private audit receipt already exists/unsafe")
    if not p.parent.is_dir():
        raise OfflineOwnerCacheBlocked("explicit owner-private report folder missing")
    try:
        with p.open("x", encoding="utf-8") as file:
            json.dump(report, file, indent=2, sort_keys=True, ensure_ascii=True)
            file.write("\n")
    except OSError as exc:
        raise OfflineOwnerCacheBlocked("owner-private audit receipt write failed") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--write-private-report", type=Path)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    try:
        report = audit_scene97(
            repo=args.repo, candidate=args.candidate, cache=args.cache)
        if args.write_private_report is not None:
            save_private_metadata(repo=args.repo,
                                  destination=args.write_private_report,
                                  report=report)
        if args.require_complete:
            require_complete_source(report)
    except (OSError, OfflineOwnerCacheBlocked) as exc:
        parser.error(str(exc))
    print(json.dumps({
        k: v for k, v in report.items()
        if k not in ("lanes", "missing_original_member_names")
    }, sort_keys=True))
    print("No game APK, Android app, original SAVE, or network was touched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
