"""Compare TWO owner-created, private copies of original game downloader files.

This tool does not create snapshots, start network downloads, use ADB, sign or
reinstall APKs, touch Android SAVE_DATA, or require root. It is meant for a
future *separate* opt-in capture experiment, NOT the currently installed
no-INTERNET local-research app.

Only 358 exact JP15.7.1 original download members named in the owner's signed
split_InstallPack.apk are read. Other files (including SAVE_DATA, account
identifiers, ad/SDK data and player state) are NOT READ OR HASHED.

For each original downloaded asset we report whether it appeared, disappeared
or changed between two private directories, and whether the AFTER copy
matches original size/MD5. Matching all 358 is NOT proof of original ZIP MD5
or source-index/scene97/gameplay success.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from tools.base_mod.recover_offline_original_server_cache import (
    OfflineOwnerCacheBlocked, owner_manifest, ORIGINAL_MEMBER_COUNT,
)

PRIVATE_SNAPSHOT_STATUS = "PRIVATE_ORIGINAL_DOWNLOAD_DIFF_ONLY_NOT_GAME_READY"


def _private_directory(repo: Path, location: Path, *, label: str) -> Path:
    root = repo / "private"
    if not root.is_dir() or root.is_symlink():
        raise OfflineOwnerCacheBlocked("owner-private root missing or unsafe")
    root = root.resolve(strict=True)
    if location.is_symlink():
        raise OfflineOwnerCacheBlocked(label + " symlink forbidden")
    resolved = location.resolve(strict=True)
    if not resolved.is_relative_to(root) or resolved == root or not resolved.is_dir():
        raise OfflineOwnerCacheBlocked(label + " must be existing owner-private directory")
    cursor = location.absolute()
    while cursor != root and cursor != cursor.parent:
        if cursor.is_symlink():
            raise OfflineOwnerCacheBlocked(label + " contains a symlink directory")
        cursor = cursor.parent
    return resolved


def _source_member(path: Path, *, expected_size: int) -> tuple[int, str] | None:
    if path.is_symlink():
        raise OfflineOwnerCacheBlocked("snapshot asset symlink forbidden")
    if not path.exists():
        return None
    if not path.is_file():
        raise OfflineOwnerCacheBlocked("snapshot original member is not a file")
    size = path.stat().st_size
    if not 0 <= size <= 100_000_000:
        raise OfflineOwnerCacheBlocked("oversized snapshot original member")
    md5 = hashlib.md5()  # Original publisher size/MD5 parity, not signing proof.
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            md5.update(block)
    return size, md5.hexdigest()


def compare_download_snapshots(
    *, repo: Path, candidate: Path, before: Path, after: Path,
) -> dict:
    """Read and checksum only downloaded game data from two staged directories."""
    repo = repo.resolve(strict=True)
    candidate = _private_directory(repo, candidate, label="original signed APK")
    before = _private_directory(repo, before, label="before snapshot")
    after = _private_directory(repo, after, label="after snapshot")
    if before == after:
        raise OfflineOwnerCacheBlocked("before and after snapshots must be distinct")
    if before.is_relative_to(after) or after.is_relative_to(before):
        raise OfflineOwnerCacheBlocked("nested before/after snapshots forbidden")
    expected = owner_manifest(candidate / "split_InstallPack.apk")
    if len(expected) != ORIGINAL_MEMBER_COUNT:
        raise OfflineOwnerCacheBlocked("owner original download manifest drift")
    # Only fixed original source file names are ever addressed. Unknown files,
    # including SAVE_DATA or private account/SDK state, are never opened.
    changes = []
    counts = {"added": 0, "removed": 0, "changed": 0,
              "unchanged": 0, "absent_both": 0}
    after_valid = 0
    after_invalid = 0
    present_before = 0
    for name, (size, md5) in sorted(expected.items()):
        old = _source_member(before / name, expected_size=size)
        new = _source_member(after / name, expected_size=size)
        if old is not None:
            present_before += 1
        if new is not None:
            if new == (size, md5):
                after_valid += 1
            else:
                after_invalid += 1
        kind = ("absent_both" if old is None and new is None else
                "added" if old is None else
                "removed" if new is None else
                "unchanged" if old == new else "changed")
        counts[kind] += 1
        if kind != "unchanged" or new != (size, md5):
            changes.append({
                "member": name,
                "kind": kind,
                "after_source_verified": new == (size, md5),
                "before_file_bytes": old[0] if old else None,
                "after_file_bytes": new[0] if new else None,
            })
    return {
        "schema": "owner-private-original-jp1571-before-after-download-diff-v1",
        "status": PRIVATE_SNAPSHOT_STATUS,
        "expected_original_download_member_count": len(expected),
        "before_present_original_members": present_before,
        "after_present_original_members": after_valid + after_invalid,
        "after_exact_size_and_md5_verified_members": after_valid,
        "after_present_but_mismatched_original_members": after_invalid,
        "after_missing_original_members": len(expected) - after_valid - after_invalid,
        "changes": counts,
        "changed_original_member_metadata": changes,
        "all_original_member_bytes_verified_after": after_valid == len(expected),
        "original_download_35_zip_archives_verified": False,
        "native_source_index_and_scene97_accepted": False,
        "SAVE_DATA_or_account_content_read": False,
        "other_unlisted_APP_files_read": False,
        "Android_game_install_or_data_changed": False,
        "original_gameplay_proven": False,
        "android_import_authorized": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--before", type=Path, required=True)
    p.add_argument("--after", type=Path, required=True)
    args = p.parse_args()
    try:
        result = compare_download_snapshots(
            repo=args.repo, candidate=args.candidate,
            before=args.before, after=args.after,
        )
    except (OSError, OfflineOwnerCacheBlocked) as exc:
        p.error(str(exc))
    safe = {k: v for k, v in result.items()
            if k != "changed_original_member_metadata"}
    print(json.dumps(safe, sort_keys=True))
    print("Read-only private comparison; no Android download or SAVE inspected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
