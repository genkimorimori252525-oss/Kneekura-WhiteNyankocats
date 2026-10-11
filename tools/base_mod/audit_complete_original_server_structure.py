"""Structural audit for all 93 exact owner JP15.7.1 Server.list/.pack pairs.

Only operate on the complete MD5-verified owner-private extracted member cache.
Decrypt .list INDEX METADATA with the existing Battle Cats manifest parser and
validate every declared member's .pack offset/bounds/non-overlap. Never export
or decrypt image/model/animation payloads, player SAVE, account or SDK data.

This proves file layout, not 35 ZIP archive MD5, game source-index registration,
or native scene97 loader acceptance. Does not run ADB, network or APK install.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import json

from tools.battlecats_pack import parse_manifest
from tools.base_mod.audit_scene97_offline_readiness import (
    audit_scene97, _private_path,
)
from tools.base_mod.recover_offline_original_server_cache import (
    OfflineOwnerCacheBlocked, owner_manifest,
)

EXPECTED_PAIR_FAMILIES = 93
EXPECTED_TOTAL_INTERNAL = 33_780


def audit_pack_structure(*, repo: Path, candidate: Path, cache: Path) -> dict:
    repo = repo.resolve(strict=True)
    candidate = _private_path(repo, candidate, exists=True)
    cache = _private_path(repo, cache, exists=True)
    provenance = audit_scene97(repo=repo, candidate=candidate, cache=cache)
    if provenance["all_original_extracted_members_verified"] is not True:
        raise OfflineOwnerCacheBlocked(
            "ORIGINAL_PACK_STRUCTURE_BLOCKED_INCOMPLETE_358_SOURCE_MEMBERS"
        )
    expected = owner_manifest(candidate / "split_InstallPack.apk")
    families = sorted(
        filename[:-5] for filename in expected if filename.endswith(".list"))
    if len(families) != EXPECTED_PAIR_FAMILIES or any(
        family + ".pack" not in expected for family in families
    ):
        raise OfflineOwnerCacheBlocked("expected original 93 Server pairs missing")

    extensions = Counter()
    inner_total = 0
    total_ciphertext_spans = 0
    per_family = []
    for family in families:
        manifest_file = cache / (family + ".list")
        packed_file = cache / (family + ".pack")
        if manifest_file.is_symlink() or packed_file.is_symlink():
            raise OfflineOwnerCacheBlocked("original server member symlink prohibited")
        if not manifest_file.is_file() or not packed_file.is_file():
            raise OfflineOwnerCacheBlocked("original server pair missing")
        try:
            declared, entries = parse_manifest(manifest_file.read_bytes())
        except (OSError, UnicodeError, ValueError) as exc:
            raise OfflineOwnerCacheBlocked(
                "original encrypted Server.list manifest failed integrity parse") from exc
        if declared != len(entries) or len({e.name for e in entries}) != len(entries):
            raise OfflineOwnerCacheBlocked("duplicate original inner resource name")
        pack_bytes = packed_file.stat().st_size
        previous_end = 0
        for entry in sorted(entries, key=lambda x: (x.offset, x.size)):
            if (entry.offset < 0 or entry.size < 0
                or entry.offset + entry.size > pack_bytes):
                raise OfflineOwnerCacheBlocked("original pack ciphertext span overflow")
            # Zero-byte entries can share a file offset; nonempty spans cannot overlap.
            if entry.size and entry.offset < previous_end:
                raise OfflineOwnerCacheBlocked("overlapping original resource ciphertext spans")
            if entry.size:
                previous_end = entry.offset + entry.size
            extensions[Path(entry.name).suffix.lower() or "(none)"] += 1
            total_ciphertext_spans += entry.size
        inner_total += declared
        per_family.append({
            "family": family,
            "declared_inner_resources": declared,
            "encrypted_pack_size": pack_bytes,
            "all_internal_offsets_within_pack": True,
            "nonzero_ciphertext_spans_do_not_overlap": True,
        })
    if inner_total != EXPECTED_TOTAL_INTERNAL:
        raise OfflineOwnerCacheBlocked("exact original JP15.7.1 internal resource count drift")
    return {
        "schema": "kneekura-owner-jp1571-complete-server-index-structure-v1",
        "status": "ORIGINAL_93_PACK_INDEX_STRUCTURES_VERIFIED_NOT_NATIVE_ACCEPTANCE",
        "source_members_size_md5_verified": provenance[
            "member_bytes_and_md5_verified_count"],
        "exact_list_pack_pairs": len(families),
        "decrypted_original_list_indexes": len(per_family),
        "declared_internal_resource_entries": inner_total,
        "internal_resource_type_counts": dict(sorted(extensions.items())),
        "total_declared_encrypted_pack_resource_spans_bytes": total_ciphertext_spans,
        "all_original_server_pack_offset_ranges_verified": True,
        "original_35_compressed_archive_md5_verified": False,
        "original_native_source_index_registered": False,
        "scene97_original_game_cache_accepted": False,
        "device_or_SAVE_written": False,
        "raw_original_asset_payloads_exported": False,
        "family_metadata_private_only": per_family,
    }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", required=True, type=Path)
    p.add_argument("--candidate", required=True, type=Path)
    p.add_argument("--cache", required=True, type=Path)
    args = p.parse_args()
    try:
        report = audit_pack_structure(
            repo=args.repo, candidate=args.candidate, cache=args.cache)
    except (OSError, OfflineOwnerCacheBlocked) as exc:
        p.error(str(exc))
    print(json.dumps({
        k: v for k, v in report.items() if k != "family_metadata_private_only"
    }, sort_keys=True))
