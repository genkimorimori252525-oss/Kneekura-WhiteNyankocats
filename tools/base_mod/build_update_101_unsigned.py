"""Build strictly UNSIGNED and NOT INSTALLABLE 1.01 original-APK data candidate.

Inputs are owner-only: exact JP15.7.1 owned export and two CSV files from the
existing 1.01 preflight receipt. No player save, key, device or network I/O.
The output is a local research/diff candidate, NOT a product patch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

from tools.battlecats_source import BattleCatsExport
from tools.base_mod.extract_owned_splits import (
    EXPECTED_EXPORT_SHA256, extract_owned_splits,
)
from tools.base_mod.patch_installpack_downloadlocal import patch_split_set
from tools.base_mod.repack import JP_15_7_1_SPLITS

SOURCE_UNIT_SHA = {
    "unit289.csv": "e48bc212537fe7949c74527f0a8212874e8595fd9414f6d9bc2b7a1e3aee1a82",
    "unit703.csv": "8caeff21c1c02918da708d06095def423d05f9df14da63b741ac78994b57dbad",
}
TARGET = {
    "unit289.csv": (2, {3: 1647, 5: 750, 6: 3033, 7: 2452}),
    "unit703.csv": (0, {3: 2941, 4: 180, 5: 2950, 6: 6533, 7: 7627, 59: 2941, 60: 2941}),
}
PAIR = {"assets/DownloadLocal.list", "assets/DownloadLocal.pack"}
DATALOCAL = {"assets/DataLocal.list", "assets/DataLocal.pack"}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_form_delta(
    original: bytes, candidate: bytes, *, file_name: str, original_sha: str
) -> dict:
    if file_name not in TARGET or _sha(original) != original_sha:
        raise ValueError("unrecognized source unit or SHA")
    form_index, approved_fields = TARGET[file_name]
    before = original.splitlines(keepends=True)
    after = candidate.splitlines(keepends=True)
    if len(before) != len(after) or form_index >= len(before):
        raise ValueError("unexpected unit CSV form count")
    if [i for i, (a, b) in enumerate(zip(before, after)) if a != b] != [form_index]:
        raise ValueError("only the approved unit form may change")
    left, right = before[form_index], after[form_index]
    if left[len(left.rstrip(b"\r\n")):] != right[len(right.rstrip(b"\r\n")):]:
        raise ValueError("original line ending changed")
    original_fields = left.rstrip(b"\r\n").split(b",")
    modified_fields = right.rstrip(b"\r\n").split(b",")
    if len(original_fields) != len(modified_fields):
        raise ValueError("unit CSV column count changed")
    changes = {}
    for i, (old, new) in enumerate(zip(original_fields, modified_fields)):
        if old == new:
            continue
        if i not in approved_fields or new != str(approved_fields[i]).encode():
            raise ValueError("unapproved column changed: " + file_name + ":" + str(i))
        changes[str(i)] = {"before": old.decode(), "after": new.decode()}
    if set(map(int, changes)) != set(approved_fields):
        raise ValueError("required approved columns were not changed")
    return {"form_index": form_index, "columns": changes, "candidate_sha256": _sha(candidate)}


def validate_preview_receipt(receipt: dict) -> None:
    if receipt.get("source_export_sha256") != EXPECTED_EXPORT_SHA256 or (
        receipt.get("status") != "STATIC_CANDIDATE_NOT_INSTALLABLE_NOT_NATIVE_VALIDATED"
    ):
        raise ValueError("preflight provenance or status changed")
    if receipt.get("only_cat_forms") != {"unit289.csv": 2, "unit703.csv": 0}:
        raise ValueError("preflight may touch unapproved forms")
    if receipt.get("DataLocal_pack_mutated") is not False or receipt.get("SAVE_DATA_mutated") is not False:
        raise ValueError("preflight does not preserve original data")
    approved = receipt.get("approved_specs", {})
    if approved.get("madoka") != {
        "lv30_attack": 28000, "sensing": 750, "cost_eoc2": 4550, "recharge_frames": 4650
    }:
        raise ValueError("Madoka design unexpectedly changed")
    god = approved.get("godzilla", {})
    expected = {
        "lv30_sequence_attack": 150000, "lv30_hit_damage": [50000, 50000, 50000],
        "sensing": 2950, "cost_eoc2": 9800, "recharge_frames": 15000,
        "attack_cycle_frames": 450, "castle_hp_per_sequence_max": 1,
    }
    if any(god.get(k) != v for k, v in expected.items()):
        raise ValueError("Godzilla design unexpectedly changed")


def _is_legacy_signature(name: str) -> bool:
    upper = name.upper()
    if not upper.startswith("META-INF/"):
        return False
    leaf = upper.rsplit("/", 1)[-1]
    return leaf == "MANIFEST.MF" or leaf.endswith((".SF", ".RSA", ".DSA", ".EC"))


def audit_unsigned_installpack(original_apk: Path, output_apk: Path) -> dict:
    with zipfile.ZipFile(original_apk) as original, zipfile.ZipFile(output_apk) as output:
        if original.testzip() is not None or output.testzip() is not None:
            raise ValueError("source or output InstallPack CRC invalid")
        original_names = {i.filename for i in original.infolist() if not i.is_dir()}
        output_names = {i.filename for i in output.infolist() if not i.is_dir()}
        expected = {name for name in original_names if not _is_legacy_signature(name)}
        if output_names != expected:
            raise ValueError("unapproved InstallPack member added or deleted")
        for name in sorted(output_names - PAIR):
            if original.read(name) != output.read(name):
                raise ValueError("unapproved InstallPack entry changed: " + name)
        if any(original.read(name) == output.read(name) for name in PAIR):
            raise ValueError("expected DownloadLocal overlay is missing")
        return {
            "changed_apk_entries": sorted(PAIR),
            "unchanged_other_member_count": len(output_names - PAIR),
            "datalocal_byte_identical": all(original.read(name) == output.read(name) for name in DATALOCAL),
        }


def build_unsigned_candidate(owner_export: Path, preview: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError("output directory already exists; do not overwrite")
    owner_export = owner_export.resolve()
    preview = preview.resolve()
    receipt = json.loads((preview / "receipt.json").read_text(encoding="utf-8"))
    validate_preview_receipt(receipt)
    additions = {name: (preview / name).read_bytes() for name in sorted(TARGET)}
    with BattleCatsExport(
        owner_export, region="jp", expected_sha256=EXPECTED_EXPORT_SHA256
    ) as export:
        reader = export.pack("DataLocal")
        diff = {}
        for name in TARGET:
            original, _ = reader.read(name)
            diff[name] = validate_form_delta(
                original, additions[name], file_name=name, original_sha=SOURCE_UNIT_SHA[name]
            )
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".kneekura-101-", dir=output.parent) as tmp:
        root = Path(tmp)
        original_splits = root / "owned-original"
        candidate = root / "candidate-splits"
        extract_owned_splits(owner_export, original_splits)
        ledger = patch_split_set(original_splits, candidate, additions)
        audit = audit_unsigned_installpack(
            original_splits / "split_InstallPack.apk", candidate / "split_InstallPack.apk"
        )
        for name in JP_15_7_1_SPLITS:
            if name != "split_InstallPack.apk" and (
                (original_splits / name).read_bytes() != (candidate / name).read_bytes()
            ):
                raise ValueError("original non-InstallPack APK changed: " + name)
        if ledger.get("datalocal_preserved_byte_identical") is not True or (
            audit.get("datalocal_byte_identical") is not True
        ):
            raise ValueError("DataLocal integrity gate failed")
        report = {
            "schema_version": 1,
            "version_intent": "KNEEKURA UPDATE 1.01",
            "status": "UNSIGNED_DATA_CANDIDATE_NOT_INSTALLABLE_NO_NATIVE_GAME_HOOK",
            "source_export_sha256": EXPECTED_EXPORT_SHA256,
            "changed_unit_csv_forms": diff,
            "installpack_audit": audit,
            "device_installed": False,
            "existing_save_modified": False,
            "original_game_hit_hook_proven": False,
            "castle_hp_hook_proven": False,
            "unit_animation_transplanted": False,
            "signed": False,
        }
        (candidate / "UNSIGNED-DO-NOT-INSTALL.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        candidate.rename(output)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owned-export", type=Path, required=True)
    parser.add_argument("--preview", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = build_unsigned_candidate(args.owned_export, args.preview, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())