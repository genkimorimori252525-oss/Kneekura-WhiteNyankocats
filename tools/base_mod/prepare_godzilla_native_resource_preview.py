"""Source-only research: candidate WImageDataServer first-form asset lookup.

This builds an isolated, NOT INSTALLABLE, private WImageDataServer.list/pack
candidate from the owner's *independently verified* original JP15.7.1 Server
pair and a privately staged 702_f art preview. The original pair is NEVER
modified. No APK, DataLocal, DownloadLocal, game SAVE, download table or signer
is written, and no publisher service is contacted.

Original ARM64 static registration: WImageDataServer index4, QNumberServer
index27. Its duplicate-key insertion code preserves the first successfully
registered key, so adding 702_f.png to WImageDataServer is a testable
CONDITIONAL path for an earlier PNG lookup; not live runtime acceptance.
The non-target 702_c second form must remain exactly original.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from typing import Any

from tools.battlecats_pack import PackReader
from tools.base_mod.battlecats_pack_writer import append_pack_entries, rebuild_pack
from tools.base_mod.fetch_godzilla_server_assets import (
    FILES as EXACT_FILES, verify as verify_jp_original,
)

FAMILY = "WImageDataServer"
PNG_NAME = "702_f.png"
FIRST_FORM_DATA = (
    "702_f.imgcut", "702_f.mamodel",
    "702_f00.maanim", "702_f01.maanim", "702_f02.maanim", "702_f03.maanim",
)
FIRST_FORM_NAMES = frozenset((PNG_NAME, *FIRST_FORM_DATA))
SECOND_FORM_PRESERVE = ("702_c.imgcut", "702_c.mamodel")
REGISTRATION_INDEX = {"WImageDataServer": 4, "QNumberServer": 27}
MAX_ASSET_BYTES = 64 * 1024 * 1024


class OriginalGodzillaResourcePreviewError(ValueError):
    """Source, provenance or candidate resource invariant was not established."""


def _sha(payload: bytes) -> str:
    return sha256(payload).hexdigest()


def prepare_wimage_first_form_candidate(
    original_manifest: bytes, original_pack: bytes,
    preview: dict[str, bytes],
) -> tuple[bytes, bytes, dict[str, Any]]:
    """Deterministic synthetic/owner-independent transform; no filesystem I/O.

    Requires all six original 702_f model/motion slots already exist in
    WImageDataServer, 702_f.png is ABSENT, and 702_c second form is present.
    The source pack is immutable. Rebuild only first form plus one appended
    PNG; all other encrypted original payloads remain byte-for-byte identical.
    """
    if set(preview) != FIRST_FORM_NAMES:
        raise OriginalGodzillaResourcePreviewError(
            "expected exactly seven approved 702_f first-form candidate names"
        )
    for name, blob in preview.items():
        if type(blob) is not bytes or not 0 < len(blob) <= MAX_ASSET_BYTES:
            raise OriginalGodzillaResourcePreviewError(
                "invalid first-form preview data: " + name
            )
    if not preview[PNG_NAME].startswith(b"\x89PNG\r\n\x1a\n"):
        raise OriginalGodzillaResourcePreviewError("candidate 702_f.png is not PNG")

    source = PackReader(FAMILY, original_manifest, original_pack, region="jp")
    missing_first = [name for name in FIRST_FORM_DATA if not source.has(name)]
    missing_second = [name for name in SECOND_FORM_PRESERVE if not source.has(name)]
    if missing_first or missing_second:
        raise OriginalGodzillaResourcePreviewError(
            "original WImageDataServer lacks necessary first/second form "
            f"slots: first={missing_first}, second={missing_second}"
        )
    if source.has(PNG_NAME):
        raise OriginalGodzillaResourcePreviewError(
            "original WImageDataServer already has 702_f.png: priority would be ambiguous"
        )
    original_second = {
        name: source.read(name)[0] for name in SECOND_FORM_PRESERVE
    }

    rebuilt_list, rebuilt_pack, replacement_proof = rebuild_pack(
        FAMILY, original_manifest, original_pack,
        {name: preview[name] for name in FIRST_FORM_DATA}, region="jp",
    )
    final_list, final_pack, append_proof = append_pack_entries(
        FAMILY, rebuilt_list, rebuilt_pack,
        {PNG_NAME: preview[PNG_NAME]}, region="jp",
    )
    inspected = PackReader(FAMILY, final_list, final_pack, region="jp")
    for name, payload in preview.items():
        after, _ = inspected.read(name)
        if after != payload:
            raise OriginalGodzillaResourcePreviewError(
                "source PNG/model/animation candidate altered by encryption"
            )
    for name, before in original_second.items():
        if inspected.read(name)[0] != before:
            raise OriginalGodzillaResourcePreviewError(
                "original second form 702_c was changed"
            )
    source_names = {entry.name for entry in source.entries}
    final_names = {entry.name for entry in inspected.entries}
    if final_names != (source_names | {PNG_NAME}):
        raise OriginalGodzillaResourcePreviewError(
            "unexpected non-target original resource key mutation"
        )
    if len(inspected.entries) != len(source.entries) + 1:
        raise OriginalGodzillaResourcePreviewError(
            "source file-family entry count changed unexpectedly"
        )
    receipt = {
        "schema_version": 1,
        "status": "GODZILLA_FIRST_FORM_WIMAGEDATA_LOOKUP_PREVIEW_ONLY_NOT_INSTALLABLE",
        "original_family": FAMILY,
        "original_family_index_zero_based": 4,
        "existing_QNumberServer_family_index_zero_based": 27,
        "source_first_successful_name_registration_priority_static": True,
        "actual_Android_source_winner_or_rendering_verified": False,
        "source_original_list_sha256": _sha(original_manifest),
        "source_original_pack_sha256": _sha(original_pack),
        "candidate_manifest_sha256": _sha(final_list),
        "candidate_pack_sha256": _sha(final_pack),
        "changed_original_first_form_entries": list(FIRST_FORM_DATA),
        "candidate_extra_PNG_in_earlier_WImageDataServer": PNG_NAME,
        "original_source_entry_count": len(source.entries),
        "candidate_entry_count": len(inspected.entries),
        "original_second_form_names_preserved": list(SECOND_FORM_PRESERVE),
        "original_second_form_bytes_changed": False,
        "unrelated_original_server_resource_bytes_changed": False,
        "candidate_original_download_table_MD5_still_valid": False,
        "original_35_Server_download_archives_complete": False,
        "original_DataLocal_or_DownloadLocal_or_APK_modified": False,
        "original_player_SAVE_or_Android_device_modified": False,
        "original_game_running_or_battle_verified": False,
        "candidate_payload_sha256": {name: _sha(data)
                                     for name, data in sorted(preview.items())},
        "internal_rebuilder_changed_entries":
            replacement_proof["changed_entries"],
        "internal_appender_added_entries": append_proof["added_entries"],
        "ready_to_install": False,
    }
    return final_list, final_pack, receipt


def preview_private_candidate(
    source_dir: Path, allied_preview: Path, output_dir: Path,
    *, enforce_owner_file_md5: bool = True,
) -> dict[str, Any]:
    """Source file bytes stay private; stage ONLY a new preview directory."""
    if (source_dir.is_symlink() or allied_preview.is_symlink()
        or not source_dir.is_dir() or not allied_preview.is_dir()
        or output_dir.is_symlink() or output_dir.exists()):
        raise OriginalGodzillaResourcePreviewError(
            "original WImageServer and allied preview must be safe directories; "
            "output must be new"
        )
    files = {}
    for name in ("WImageDataServer.list", "WImageDataServer.pack"):
        path = source_dir / name
        if not path.is_file() or path.is_symlink():
            raise OriginalGodzillaResourcePreviewError(
                "missing original owner WImageDataServer file " + name
            )
        if enforce_owner_file_md5:
            verify_jp_original(path, EXACT_FILES[name])
        files[name] = path.read_bytes()
    receipt_path = allied_preview / "rig-conversion-preview-receipt.json"
    if receipt_path.is_symlink() or not receipt_path.is_file():
        raise OriginalGodzillaResourcePreviewError("missing private 702_f source receipt")
    conversion = json.loads(receipt_path.read_text(encoding="utf-8"))
    if (conversion.get("status") != "GODZILLA_FIRST_FORM_RIG_PREVIEW_ONLY_NOT_INSTALLABLE"
        or conversion.get("ready_to_install") is not False
        or conversion.get("second_form_bytes_changed") is not False):
        raise OriginalGodzillaResourcePreviewError("candidate private 702_f proof invalid")
    source_hashes = conversion.get("candidate_ally_art")
    if not isinstance(source_hashes, dict) or set(source_hashes) != FIRST_FORM_NAMES:
        raise OriginalGodzillaResourcePreviewError("candidate artwork provenance drift")
    previews = {}
    for name in sorted(FIRST_FORM_NAMES):
        path = allied_preview / name
        if path.is_symlink() or not path.is_file():
            raise OriginalGodzillaResourcePreviewError(
                "missing owner-private candidate artwork " + name
            )
        body = path.read_bytes()
        expected = source_hashes[name]
        if expected.get("bytes") != len(body) or expected.get("sha256") != _sha(body):
            raise OriginalGodzillaResourcePreviewError(
                "owner candidate artwork hash changed after conversion"
            )
        previews[name] = body

    new_list, new_pack, evidence = prepare_wimage_first_form_candidate(
        files["WImageDataServer.list"], files["WImageDataServer.pack"], previews
    )
    if output_dir.parent.is_symlink():
        raise OriginalGodzillaResourcePreviewError("unsafe private research output parent")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".kneekura-WImage-702f-",dir=output_dir.parent) as tmp:
        stage = Path(tmp) / "candidate"
        stage.mkdir()
        (stage / "WImageDataServer.list").write_bytes(new_list)
        (stage / "WImageDataServer.pack").write_bytes(new_pack)
        (stage / "candidate-research-receipt.json").write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if output_dir.exists():
            raise OriginalGodzillaResourcePreviewError(
                "private WImageDataServer candidate destination appeared during staging"
            )
        stage.rename(output_dir)
    return evidence


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-server-dir", type=Path, required=True)
    p.add_argument("--ally-preview-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args(argv)
    private_root = (Path(__file__).resolve().parents[2] / "private").resolve()
    if not args.output.resolve().is_relative_to(private_root):
        p.error("candidate original Server archive must stay in Git-ignored private/")
    try:
        proof = preview_private_candidate(
            args.original_server_dir, args.ally_preview_dir, args.output
        )
    except (OSError, ValueError, KeyError, TypeError, UnicodeError) as exc:
        p.error(str(exc))
    print(proof["status"])
    print("STATIC research candidate only; original APK/download MD5/Android game unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
