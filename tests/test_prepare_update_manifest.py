"""Future version updates must only change the manifest, never originals."""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from tools.base_mod.prepare_update_manifest import (
    UnsafeUpdate, validate_manifest, edit_unit_bytes, preview_receipt,
)
from tools.base_mod.build_update_101_unsigned import (
    TARGET, SOURCE_UNIT_SHA, validate_preview_receipt,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "docs/updates/manifests/update-1.01.json"


class ManifestDrivenUpdateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(DEFAULT_MANIFEST.read_text(encoding="utf-8"))

    def test_approved_101_fields_and_legacy_builder_match_exactly(self):
        ordered = validate_manifest(self.manifest)
        self.assertEqual(set(row["unit_file"] for row in ordered), set(TARGET))
        for entry in ordered:
            name = entry["unit_file"]
            self.assertEqual(entry["original_sha256"], SOURCE_UNIT_SHA[name])
            self.assertEqual(entry["form_index"], TARGET[name][0])
            self.assertEqual(entry["raw_columns"],
                             {str(k): v for k, v in TARGET[name][1].items()})
        rec = preview_receipt(self.manifest, {})
        validate_preview_receipt(rec)  # legacy 1.01 unsigned builder can consume it
        self.assertFalse(rec["DataLocal_pack_mutated"])
        self.assertFalse(rec["SAVE_DATA_mutated"])
        self.assertFalse(rec["gameplay_release_ready"])

    def test_edits_only_selected_form_columns_preserves_crlf(self):
        rows = [b",".join([b"0"]*75) + b"\r\n" for _ in range(3)]
        original = b"".join(rows)
        entry = dict(self.manifest["units"][0])
        entry["original_sha256"] = hashlib.sha256(original).hexdigest()
        candidate, diff = edit_unit_bytes(original, entry)
        self.assertEqual(diff["form_index"], 2)
        self.assertEqual(diff["source_sha256"], hashlib.sha256(original).hexdigest())
        self.assertEqual(candidate.splitlines(keepends=True)[0], rows[0])
        self.assertEqual(candidate.splitlines(keepends=True)[1], rows[1])
        self.assertTrue(candidate.splitlines(keepends=True)[2].endswith(b"\r\n"))
        self.assertEqual(set(diff["changes"]), set(entry["raw_columns"]))

    def test_wrong_source_or_missing_form_rejected(self):
        original = b"0,0,0,0\n"
        entry = deepcopy(self.manifest["units"][0])
        with self.assertRaises(UnsafeUpdate):
            edit_unit_bytes(original, entry)
        entry["original_sha256"] = hashlib.sha256(original).hexdigest()
        with self.assertRaises(UnsafeUpdate):
            edit_unit_bytes(original, entry)

    def test_release_or_unsafe_changes_rejected(self):
        for field, value in (
            ("status", "RELEASED"), ("schema_version", 2),
        ):
            invalid = deepcopy(self.manifest)
            invalid[field] = value
            with self.assertRaises(UnsafeUpdate):
                validate_manifest(invalid)
        for field in (
            "install_apk", "modify_save_data", "alter_original_datalocal",
            "redistribute_owner_assets",
        ):
            invalid = deepcopy(self.manifest)
            invalid["safety"][field] = True
            with self.assertRaises(UnsafeUpdate):
                validate_manifest(invalid)
        invalid = deepcopy(self.manifest)
        invalid["release_gates"]["castle_hp_debit_hook_attached"] = True
        with self.assertRaises(UnsafeUpdate):
            validate_manifest(invalid)

    def test_unknown_unit_and_namespace_protected(self):
        invalid = deepcopy(self.manifest)
        invalid["units"].append(deepcopy(invalid["units"][0]))
        with self.assertRaises(UnsafeUpdate):
            validate_manifest(invalid)
        invalid = deepcopy(self.manifest)
        invalid["units"][0]["unit_file"] = "../enemy552.csv"
        with self.assertRaises(UnsafeUpdate):
            validate_manifest(invalid)
        invalid = deepcopy(self.manifest)
        invalid["units"][0]["asset_id"] = 289
        with self.assertRaises(UnsafeUpdate):
            validate_manifest(invalid)
        invalid = deepcopy(self.manifest)
        invalid["units"][0]["raw_columns"]["5"] = -1
        with self.assertRaises(UnsafeUpdate):
            validate_manifest(invalid)

    def test_original_server_packs_immutable(self):
        invalid = deepcopy(self.manifest)
        invalid["source_assets"]["immutable_owner_packs"] = []
        with self.assertRaises(UnsafeUpdate):
            validate_manifest(invalid)
        invalid = deepcopy(self.manifest)
        invalid["source_assets"]["second_form_untouched"] = False
        with self.assertRaises(UnsafeUpdate):
            validate_manifest(invalid)


if __name__ == "__main__":
    unittest.main()