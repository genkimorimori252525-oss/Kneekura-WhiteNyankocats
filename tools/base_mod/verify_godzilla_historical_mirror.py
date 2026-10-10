"""Ephemeral JP15.7.1 mirror verification; NEVER publish source pack bytes.

Explicit opt-in ONLY. Download four pinned historical public-archive files
(https://github.com/fieryhenry/BCData) to a temporary isolated directory,
verify the owner's JP15.7.1 historical byte-count/MD5, run the existing
encrypted 550_e -> 702_f -> WImageDataServer candidate *entirely there*,
and write one METADATA-ONLY JSON receipt after temporary data are deleted.

No original account, device, user SAVE, APK, signing key or installed game is
accessed. Candidate's game-side source priority/rendering and original
download-table integrity remain unverified; never install this preview.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Callable

from tools.base_mod import fetch_godzilla_server_assets as recovery
from tools.battlecats_pack import PackReader

SOURCE_REPOSITORY = "fieryhenry/BCData"
SOURCE_PATH = "jp_server"
SCHEMA = "jp15.7.1-historical-godzilla-mirror-ephemeral-metadata-v1"
KNOWN_SAFE_FILES = tuple(recovery.FILES)
RESULT_LIMIT = 100 * 1024
PINNED_MIRROR_BASE = (
    "https://raw.githubusercontent.com/fieryhenry/BCData/main/jp_server/"
)


def _sha(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _error_code(message: str) -> str:
    """Do not leak a URL, dynamic local path, binary or secret in receipts."""
    clean = re.sub(r"[^a-zA-Z0-9_]+", "_", message.casefold())
    # Known, stable implementation diagnostic category; not full messages.
    if "md5_mismatch" in clean or "oversized" in clean:
        return "ORIGINAL_SOURCE_SIZE_OR_MD5_MISMATCH"
    if "not_found" in clean or "http_error_404" in clean:
        return "PUBLIC_ARCHIVE_FILE_UNAVAILABLE"
    if "timeout" in clean or "urlerror" in clean:
        return "PUBLIC_ARCHIVE_NETWORK_UNAVAILABLE"
    if "missing" in clean or "lacks" in clean:
        return "REQUIRED_ORIGINAL_RESOURCE_NOT_PRESENT"
    if "model" in clean or "animation" in clean or "imgcut" in clean:
        return "ORIGINAL_RIG_FORMAT_NOT_SUPPORTED"
    if "manifest" in clean or "contiguous" in clean or "pack" in clean:
        return "ORIGINAL_PACK_FORMAT_NOT_SUPPORTED"
    return "UNKNOWN_SOURCE_OR_FORMAT_FAILURE"


def _private_original_model_root_summary(raw: bytes) -> dict[str, Any]:
    """Read-only sparse model metadata, NEVER output source model lines."""
    if not 0 < len(raw) <= 8 * 1024 * 1024:
        raise ValueError("original model outside bounded research input")
    try:
        rows = raw.decode("utf-8-sig").splitlines()
        if (len(rows) < 4
            or rows[0] not in ("[modelanim:model]", "[modelanim:model2]")
            or not 1 <= int(rows[2]) <= 30000):
            raise ValueError("original model header is not understood")
        count = int(rows[2])
        if len(rows) < count + 3:
            raise ValueError("original model nodes truncated")
        first = rows[3].split(",")
        if len(first) < 13 or [int(x) for x in first[:2]] != [-1, -1]:
            raise ValueError("original first model part is not root")
        scale = int(first[8])
        if scale == 0:
            raise ValueError("original model root horizontal scale is zero")
    except (UnicodeError, IndexError, TypeError, OverflowError) as exc:
        raise ValueError("original model numeric metadata unreadable") from exc
    return {
        "model_format": rows[0],
        "node_count": count,
        "horizontal_root_scale_sign": -1 if scale < 0 else 1,
        "horizontal_root_scale_abs": abs(scale),
        "raw_original_model_sha256": sha256(raw).hexdigest(),
    }


def _base_receipt() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "source": SOURCE_REPOSITORY + "/" + SOURCE_PATH,
        "historical_original_owner_archive_sha256":
            recovery.EXPORT_SHA256,
        "status": "BLOCKED_NOT_STARTED",
        "last_stage": "not-started",
        "source_download_opt_in": True,
        "ephemeral_original_source_bytes_uploaded_to_Git": False,
        "original_source_or_artifact_raw_bytes_retained": False,
        "original_game_artifacts_saved_or_committed": False,
        "original_publisher_network_or_account_contacted": False,
        "original_apk_or_player_SAVE_edited": False,
        "actual_original_Android_renderer_accepted": False,
        "original_archive_download_table_integrity_preserved_in_candidate": False,
        "first_game_save_or_native_cat_battle_accepted": False,
        "all_35_original_download_lanes_complete": False,
        "ready_to_install_or_ship": False,
    }


def verify_public_mirror_volatile(
    *,
    allow_mirror_download: bool,
    opener: Callable | None = None,
) -> dict[str, Any]:
    """Return metadata only; all binary resources live under TemporaryDirectory.

    Deliberately do not accept arbitrary input URLs, package names, account
    tokens, SSL-skip flags, local original path or mutable Server lists.
    """
    receipt = _base_receipt()
    if not allow_mirror_download:
        receipt.update(
            status="BLOCKED_EXPLICIT_NETWORK_OPT_IN_REQUIRED",
            last_stage="network-authorization",
        )
        return receipt
    if recovery.SOURCE != PINNED_MIRROR_BASE:
        receipt.update(
            status="BLOCKED_HISTORICAL_MIRROR_SOURCE_URL_DRIFT",
            last_stage="network-origin-validation",
        )
        return receipt

    # Every byte-bearing path is contained in a temporary working directory
    # outside the repository / CI checkout, including the 80 MB pack.
    with tempfile.TemporaryDirectory(prefix="kneekura-jp1571-volatile-") as t:
        private = Path(t) / "private"
        source = private / "mirror"
        output = {
            "server": private / "verified-four",
            "rig": private / "enemy-550e",
            "ally": private / "first-form-702f",
            "candidate": private / "wimage-candidate",
        }
        try:
            receipt["last_stage"] = "historical-source-download"
            if opener is None:
                downloaded = recovery.acquire("download", source)
            else:
                downloaded = recovery.acquire("download", source, opener=opener)
            files = downloaded["files"]
            if {row["name"] for row in files} != set(KNOWN_SAFE_FILES):
                raise ValueError("historical source file list drift")
            receipt["source_original_archives"] = {
                row["name"]: {
                    "bytes": row["size"],
                    "historical_MD5_matches": (
                        (row["size"], row["md5"]) == recovery.FILES[row["name"]]
                    ),
                    "sha256": row["sha256"],
                }
                for row in files
            }
            if not all(row["historical_MD5_matches"] for row in
                       receipt["source_original_archives"].values()):
                raise ValueError("historical original source MD5 mismatch")

            receipt["last_stage"] = "original-decrypt-and-first-form-candidate"
            finished = recovery.complete_owner_private_godzilla_pipeline(
                source,
                server_output=output["server"],
                rig_output=output["rig"],
                ally_output=output["ally"],
                resource_output=output["candidate"],
                private_root=private,
            )
            for name in (
                "godzilla_original_rig",
                "godzilla_ally_preview",
                "godzilla_WImageDataServer_research_candidate",
            ):
                if (name not in finished
                    or finished[name].get("ready_to_install") is not False):
                    raise ValueError("verified source pipeline stage missing")

            candidate = finished["godzilla_WImageDataServer_research_candidate"]
            art = finished["godzilla_original_rig"]
            ally = finished["godzilla_ally_preview"]
            # Use only precomputed SHA+size evidence. It never contains the
            # original art, decrypted model lines, or full data blobs.
            receipt["original_enemy_art_550e"] = {
                name: {
                    "bytes": row["size"],
                    "sha256": row["sha256"],
                } for name, row in sorted(art["art"].items())
            }
            receipt["candidate_first_form_702f"] = {
                name: {"bytes": row["bytes"], "sha256": row["sha256"]}
                for name, row in sorted(ally["candidate_ally_art"].items())
            }
            receipt["candidate_WImageDataServer"] = {
                "original_entry_count": candidate["original_source_entry_count"],
                "candidate_entry_count": candidate["candidate_entry_count"],
                "original_second_form_bytes_changed":
                    candidate["original_second_form_bytes_changed"],
                "unrelated_original_resources_changed":
                    candidate["unrelated_original_server_resource_bytes_changed"],
                "changed_first_form_names":
                    candidate["changed_original_first_form_entries"],
                "extra_PNG_in_earlier_family":
                    candidate["candidate_extra_PNG_in_earlier_WImageDataServer"],
                "candidate_manifest_sha256":
                    candidate["candidate_manifest_sha256"],
                "candidate_pack_sha256": candidate["candidate_pack_sha256"],
                "original_702c_second_form_unchanged":
                    candidate["original_second_form_bytes_changed"] is False,
            }
            receipt["original_rig_geometry"] = ally["atlas_geometry"]
            receipt["original_imgcut_sprite_count"] = (
                ally["imgcut_conversion"]["sprite_part_count"]
            )
            receipt["original_model_node_count"] = (
                ally["mamodel_conversion"]["declared_model_nodes"]
            )
            receipt["real_model_conversion"] = {
                "atlas_550_to_702_rows":
                    ally["mamodel_conversion"]["atlas_rows_rebased"],
                "root_horizontal_orientation_changed":
                    ally["mamodel_conversion"]["root_was_reoriented"],
                "other_original_model_fields_preserved":
                    ally["mamodel_conversion"]["extra_collision_and_model_footer_bytes_preserved"],
            }
            receipt["original_animation_track_summaries"] = {
                name: {
                    "track_count": info["track_count"],
                    "keyframe_count": info["keyframe_count"],
                    "negative_frame_key_count":
                        info["negative_frame_key_count"],
                    "special_minus_two_node_track_count":
                        info["special_minus_two_node_track_count"],
                    "largest_frame_number": info["largest_frame_number"],
                    "zero_keyframe_track_count": info["zero_keyframe_track_count"],
                }
                for name, info in sorted(ally["animations_untouched"].items())
            }
            originals = receipt["original_enemy_art_550e"]
            candidates = receipt["candidate_first_form_702f"]
            for suffix in (".png", "00.maanim", "01.maanim",
                           "02.maanim", "03.maanim"):
                if (originals["550_e" + suffix]["sha256"]
                    != candidates["702_f" + suffix]["sha256"]):
                    raise ValueError("original Godzilla PNG or animation bytes changed")
            receipt["PNG_and_four_maanim_SHA256_all_unchanged"] = True
            # The historical WImage source also includes the ORIGINAL
            # allied 702_f and second-form 702_c native models. Compare
            # their actual root horizontal orientation to the newly
            # generated enemy->ally 702_f model without exposing any source
            # model bytes or assuming the renderer's facing rules.
            original_family = recovery.FILES
            if set(KNOWN_SAFE_FILES) != set(original_family):
                raise ValueError("source family definition changed")
            stream = PackReader(
                "WImageDataServer",
                (source / "WImageDataServer.list").read_bytes(),
                (source / "WImageDataServer.pack").read_bytes(),
                region="jp",
            )
            original_first = _private_original_model_root_summary(
                stream.read("702_f.mamodel")[0]
            )
            original_second = _private_original_model_root_summary(
                stream.read("702_c.mamodel")[0]
            )
            original_enemy = _private_original_model_root_summary(
                stream.read("550_e.mamodel")[0]
            )
            converted_first = _private_original_model_root_summary(
                (output["ally"] / "702_f.mamodel").read_bytes()
            )
            receipt["original_allied_model_comparison"] = {
                "original_enemy_550_e": original_enemy,
                "original_ally_702_f": original_first,
                "original_second_form_702_c": original_second,
                "candidate_ally_702_f": converted_first,
                "candidate_matches_original_friendly_root_scale_sign":
                    converted_first["horizontal_root_scale_sign"]
                    == original_first["horizontal_root_scale_sign"],
                "source_and_candidate_model_contents_preserved_except_recorded_fields":
                    ally["mamodel_conversion"]["extra_collision_and_model_footer_bytes_preserved"],
            }
            receipt["private_staging_worked_without_original_game_mutation"] = True
            receipt["status"] = "PASS_ORIGINAL_PUBLIC_ARCHIVE_MATCHED_AND_PRIVATE_PREVIEW_BUILT"
            receipt["last_stage"] = "metadata-only-receipt"
        except Exception as exc:
            # Even if a parser leaks original plaintext into its exception,
            # NEVER record that exception message or its stack trace.
            receipt["status"] = "BLOCKED_ORIGINAL_MIRROR_SOURCE_OR_FORMAT"
            receipt["failure_type"] = type(exc).__name__[:75]
            receipt["failure_code"] = _error_code(str(exc))
    # TemporaryDirectory has been removed before this receipt is returned.
    return receipt


def write_metadata_receipt(output: Path, receipt: dict[str, Any]) -> None:
    """Exclusive JSON file output: never export byte-bearing native assets."""
    target = output.resolve()
    if output.is_symlink() or target.exists() or target.suffix.lower() != ".json":
        raise ValueError("metadata receipt must be a new JSON file")
    if "source_original_archives" in receipt and len(
        receipt["source_original_archives"]
    ) != len(KNOWN_SAFE_FILES):
        raise ValueError("wrong original source metadata")
    encoded = (json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2)
               + "\n").encode("utf-8")
    if len(encoded) > RESULT_LIMIT:
        raise ValueError("unsafe oversized metadata receipt")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as stream:
        stream.write(encoded)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-historical-mirror-download",
                        action="store_true",
                        help="Explicitly permit only 4 pinned public archive downloads")
    parser.add_argument("--metadata-output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = verify_public_mirror_volatile(
        allow_mirror_download=args.allow_historical_mirror_download
    )
    try:
        write_metadata_receipt(args.metadata_output, result)
    except (OSError, ValueError) as exc:
        parser.error("metadata-only output could not be written: "
                     + type(exc).__name__)
    print("GODZILLA_HISTORICAL_MIRROR_RESULT=" + result["status"])
    print("GODZILLA_HISTORICAL_MIRROR_STAGE=" + result["last_stage"])
    return 0 if result["status"].startswith("PASS_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
