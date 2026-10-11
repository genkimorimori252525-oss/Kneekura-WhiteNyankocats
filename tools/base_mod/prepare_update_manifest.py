"""Generate private, form-scoped JP15.7.1 data previews from ONE update JSON.

This is a source-only candidate generator, not an APK signer, installer,
native battle hook, asset downloader, or gameplay release.
Original DataLocal, downloaded Server source packs and SAVE_DATA are untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import tempfile

from tools.battlecats_source import BattleCatsExport
from tools.base_mod.extract_owned_splits import EXPECTED_EXPORT_SHA256

UNIT_NAME = re.compile(r"^unit([0-9]{3})\.csv$")
HEX_SHA = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_ASSET_INPUTS = (
    "MNumberServer.list", "MNumberServer.pack",
    "WImageDataServer.list", "WImageDataServer.pack",
)
REPO_ROOT = Path(__file__).resolve().parents[2]


class UnsafeUpdate(ValueError):
    """The update request cannot be proven to preserve the original game."""


def _sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def validate_manifest(payload: dict) -> list[dict]:
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise UnsafeUpdate("unsupported update manifest schema")
    if not isinstance(payload.get("release"), str) or not re.fullmatch(
        r"[0-9]+\.[0-9]+", payload["release"]
    ):
        raise UnsafeUpdate("invalid update version")
    if payload.get("status") != "PREVIEW_ONLY_NOT_INSTALLABLE":
        raise UnsafeUpdate("manifest must remain PREVIEW_ONLY_NOT_INSTALLABLE")

    base = payload.get("base")
    if not isinstance(base, dict) or (
        base.get("region"), base.get("game_version"), base.get("owner_export_sha256")
    ) != ("jp", "15.7.1", EXPECTED_EXPORT_SHA256):
        raise UnsafeUpdate("unrecognized source game or owner export fingerprint")

    safety = payload.get("safety")
    if not isinstance(safety, dict) or any(
        safety.get(key) is not False for key in
        ("modify_save_data", "alter_original_datalocal",
         "install_apk", "redistribute_owner_assets")
    ):
        raise UnsafeUpdate("manifest violates original data/save safety")

    gates = payload.get("release_gates")
    if not isinstance(gates, dict) or not gates or any(
        type(value) is not bool or value for value in gates.values()
    ):
        raise UnsafeUpdate("source-preview cannot assert game/Android release gates")

    assets = payload.get("source_assets")
    if not isinstance(assets, dict) or (
        tuple(assets.get("immutable_owner_packs", [])) != EXPECTED_ASSET_INPUTS or
        assets.get("second_form_untouched") is not True
    ):
        raise UnsafeUpdate("owner source pack immutability contract changed")

    approved = payload.get("approved_specs")
    if not isinstance(approved, dict) or not approved:
        raise UnsafeUpdate("missing human-approved unit design metadata")

    entries = payload.get("units")
    if not isinstance(entries, list) or not 1 <= len(entries) <= 100:
        raise UnsafeUpdate("manifest requires bounded unit entries")

    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise UnsafeUpdate("invalid unit entry")
        file_name = entry.get("unit_file")
        match = UNIT_NAME.fullmatch(file_name) if isinstance(file_name, str) else None
        if not match or file_name in seen:
            raise UnsafeUpdate("invalid or duplicate unit CSV entry")
        seen.add(file_name)
        number = int(match.group(1))
        if (type(entry.get("catalog_no")) is not int or
            type(entry.get("asset_id")) is not int or
            entry["catalog_no"] != number or entry["asset_id"] != number - 1):
            raise UnsafeUpdate("unit No. to asset ID namespace mismatch")
        if type(entry.get("form_index")) is not int or not (
            0 <= entry["form_index"] <= 3
        ):
            raise UnsafeUpdate("invalid original cat form index")
        digest = entry.get("original_sha256")
        if not isinstance(digest, str) or not HEX_SHA.fullmatch(digest):
            raise UnsafeUpdate("missing exact original unit SHA256")
        columns = entry.get("raw_columns")
        if not isinstance(columns, dict) or not columns:
            raise UnsafeUpdate("unit entry needs actual changed raw columns")
        for column, value in columns.items():
            if (not isinstance(column, str) or not column.isascii() or
                not column.isdecimal() or int(column) >= 2048 or
                type(value) is not int or not 0 <= value < 2**31):
                raise UnsafeUpdate("unsafe raw CSV column/value in manifest")

    return sorted(entries, key=lambda row: row["unit_file"])


def edit_unit_bytes(original: bytes, entry: dict) -> tuple[bytes, dict]:
    digest = _sha(original)
    if digest != entry["original_sha256"]:
        raise UnsafeUpdate("original unit source SHA256 mismatch: " + entry["unit_file"])
    rows = original.splitlines(keepends=True)
    row_no = entry["form_index"]
    if not rows or row_no >= len(rows):
        raise UnsafeUpdate("declared original form does not exist")
    row = rows[row_no]
    newline = b"\r\n" if row.endswith(b"\r\n") else b"\n" if row.endswith(b"\n") else b""
    original_columns = row[:-len(newline)].split(b",") if newline else row.split(b",")
    columns = list(original_columns)
    changes: dict[str, dict[str, str]] = {}
    for index_str, number in entry["raw_columns"].items():
        index = int(index_str)
        if index >= len(columns):
            raise UnsafeUpdate("raw column not present in original unit CSV")
        if not re.fullmatch(rb"-?[0-9]+", columns[index]):
            raise UnsafeUpdate("original raw CSV field was not an integer")
        replacement = str(number).encode("ascii")
        if columns[index] == replacement:
            raise UnsafeUpdate("specified raw field was already unchanged")
        changes[index_str] = {
            "before": columns[index].decode("ascii"),
            "after": str(number),
        }
        columns[index] = replacement
    rows[row_no] = b",".join(columns) + newline
    candidate = b"".join(rows)
    for index, (a, b) in enumerate(zip(original.splitlines(keepends=True),
                                       candidate.splitlines(keepends=True))):
        if (a != b) != (index == row_no):
            raise UnsafeUpdate("a non-target form was changed")
    return candidate, {
        "form_index": row_no, "changes": changes,
        "source_sha256": digest, "candidate_sha256": _sha(candidate),
    }


def preview_receipt(manifest: dict, diffs: dict[str, dict]) -> dict:
    return {
        "schema_version": 1,
        "mode": "manifest-scoped-owner-local-update-preview-v1",
        "update_version": manifest["release"],
        "status": "STATIC_CANDIDATE_NOT_INSTALLABLE_NOT_NATIVE_VALIDATED",
        "source_export_sha256": EXPECTED_EXPORT_SHA256,
        "only_cat_forms": {
            entry["unit_file"]: entry["form_index"]
            for entry in manifest["units"]
        },
        "approved_specs": manifest["approved_specs"],
        "units": diffs,
        "DataLocal_pack_mutated": False,
        "SAVE_DATA_mutated": False,
        "original_apk_installed": False,
        "same_signer_device_verified": False,
        "gameplay_release_ready": False,
        "release_gates": manifest["release_gates"],
        "immutable_original_server_packs_reused": True,
    }


def build_preview(manifest_path: Path, owned_export: Path, output: Path) -> dict:
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    ordered = validate_manifest(manifest)
    dest = output.expanduser().resolve()
    private_root = (REPO_ROOT / "private").resolve()
    if not dest.is_relative_to(private_root) or dest == private_root:
        raise UnsafeUpdate("original-game CSV previews must stay below repo/private")
    if dest.exists():
        raise UnsafeUpdate("preview directory already exists; no overwrite")

    additions: dict[str, bytes] = {}
    diffs: dict[str, dict] = {}
    with BattleCatsExport(
        owned_export, region="jp", expected_sha256=EXPECTED_EXPORT_SHA256
    ) as source:
        reader = source.pack("DataLocal")
        for entry in ordered:
            original, _ = reader.read(entry["unit_file"])
            candidate, details = edit_unit_bytes(original, entry)
            additions[entry["unit_file"]] = candidate
            diffs[entry["unit_file"]] = details

    receipt = preview_receipt(manifest, diffs)
    receipt["manifest_sha256"] = _sha(manifest_bytes)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".kneekura-update-preview-", dir=dest.parent) as name:
        staging = Path(name) / "generated"
        staging.mkdir()
        for unit_name, content in additions.items():
            (staging / unit_name).write_bytes(content)
        (staging / "receipt.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        staging.rename(dest)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--owned-export", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = build_preview(args.manifest, args.owned_export, args.output)
    except (OSError, ValueError, KeyError, UnicodeError) as exc:
        parser.error(str(exc))
    print(json.dumps({
        "status": result["status"],
        "version": result["update_version"],
        "forms": result["only_cat_forms"],
        "preview_directory": str(args.output),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())