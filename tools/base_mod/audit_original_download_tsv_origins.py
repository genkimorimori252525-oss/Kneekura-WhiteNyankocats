"""Exact original JP15.7.1 downloaded TSV source precedence evidence.

Read-only. Distinguishes 35 plain InstallPack APK assets from the native
Server.list/.pack catalogue, and identifies whether there are any competing
definitions of the original DownloadBatchTask `download_0..34.tsv` names.

Does NOT infer which resource is selected by the original game's *runtime*
source resolver, patch H01/DownloadLocal, update the phone or read SAVE.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from zipfile import ZipFile

from tools.battlecats_pack import parse_manifest
from tools.base_mod.audit_scene97_offline_readiness import audit_scene97, _private_path
from tools.base_mod.recover_offline_original_server_cache import (
    OfflineOwnerCacheBlocked, ORIGINAL_TSV_COUNT, owner_manifest,
)

TSV_PATTERN = re.compile(r"download_(?:[0-9]|[12][0-9]|3[0-4])\.tsv\Z")


def _indexes(path: Path) -> set[str]:
    if path.is_symlink() or not path.is_file():
        raise OfflineOwnerCacheBlocked("original list index missing or unsafe")
    try:
        _, entries = parse_manifest(path.read_bytes())
    except (OSError, ValueError, UnicodeError) as exc:
        raise OfflineOwnerCacheBlocked("original Server.list index unreadable") from exc
    return {row.name for row in entries if TSV_PATTERN.fullmatch(row.name)}


def audit_original_download_tsv_origins(
    *, repo: Path, candidate: Path, cache: Path
) -> dict:
    repo = repo.resolve(strict=True)
    candidate = _private_path(repo, candidate, exists=True)
    cache = _private_path(repo, cache, exists=True)
    verified = audit_scene97(repo=repo, candidate=candidate, cache=cache)
    if not verified["all_original_extracted_members_verified"]:
        raise OfflineOwnerCacheBlocked("source origin audit needs complete owner 358 cache")

    installpack = candidate / "split_InstallPack.apk"
    expected = {f"download_{i}.tsv" for i in range(ORIGINAL_TSV_COUNT)}
    local_manifest_sources: dict[str, list[str]] = {}
    with ZipFile(installpack) as archive:
        zipped = archive.namelist()
        direct = {x.rsplit("/", 1)[-1] for x in zipped
                  if x.startswith("assets/download_")
                  and TSV_PATTERN.fullmatch(x.rsplit("/", 1)[-1])}
        if direct != expected:
            raise OfflineOwnerCacheBlocked("original APK direct TSV set changed")
        for name in sorted(x for x in zipped
                           if x.startswith("assets/") and x.endswith(".list")
                           and x.count("/") == 1):
            try:
                _, entries = parse_manifest(archive.read(name))
            except (OSError, ValueError, UnicodeError) as exc:
                raise OfflineOwnerCacheBlocked("original local pack index unreadable") from exc
            for entry in entries:
                if TSV_PATTERN.fullmatch(entry.name):
                    local_manifest_sources.setdefault(entry.name, []).append(name)

    owned = owner_manifest(installpack)
    families = sorted(name[:-5] for name in owned if name.endswith(".list"))
    server_sources: dict[str, list[str]] = {}
    for family in families:
        for name in _indexes(cache / (family + ".list")):
            server_sources.setdefault(name, []).append(family)

    # Do not prohibit competing sources: record them to avoid assuming
    # precedence. A future native runtime witness must resolve the winner.
    provided_by_server = sorted(server_sources)
    provided_by_local = sorted(local_manifest_sources)
    return {
        "schema": "kneekura-jp1571-exact-download-tsv-source-matrix-v1",
        "status": "SOURCE_DIRECT_ASSETS_PRESENT_RUNTIME_PRECEDENCE_UNVERIFIED",
        "direct_InstallPack_asset_names": len(direct),
        "encrypted_local_pack_TSV_name_count": len(provided_by_local),
        "encrypted_server_pack_TSV_name_count": len(provided_by_server),
        "total_original_Server_list_families_checked": len(families),
        "all_35_download_tsv_plain_APK_assets": direct == expected,
        "all_358_original_downloaded_members_md5_verified": True,
        "all_35_source_TSV_parsed_by_original_native": False,
        "original_runtime_named_source_index_initialized": False,
        "loose_app_private_TSV_can_satisfy_resolver": False,
        "original_game_scene97_completed": False,
        "original_game_cat_base_accepted": False,
        "Android_apk_or_SAVE_modified": False,
        "nonempty_competing_sources": {
            "local_pack": provided_by_local,
            "Server_pack": provided_by_server,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--cache", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = audit_original_download_tsv_origins(
            repo=args.repo, candidate=args.candidate, cache=args.cache)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
