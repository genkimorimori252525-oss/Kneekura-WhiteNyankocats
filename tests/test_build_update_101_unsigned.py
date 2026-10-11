"""Security contract for an unsigned data-only 1.01 split build."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.base_mod.build_update_101_unsigned import (
    TARGET, audit_unsigned_installpack, validate_form_delta,
    validate_preview_receipt,
)


def approved_receipt():
    return {
        "source_export_sha256": "38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56",
        "status": "STATIC_CANDIDATE_NOT_INSTALLABLE_NOT_NATIVE_VALIDATED",
        "only_cat_forms": {"unit289.csv": 2, "unit703.csv": 0},
        "DataLocal_pack_mutated": False,
        "SAVE_DATA_mutated": False,
        "approved_specs": {
            "madoka": {"lv30_attack": 28000, "sensing": 750,
                       "cost_eoc2": 4550, "recharge_frames": 4650},
            "godzilla": {"lv30_sequence_attack": 150000, "lv30_hit_damage": [50000]*3,
                        "sensing": 2950, "cost_eoc2": 9800, "recharge_frames": 15000,
                        "attack_cycle_frames": 450, "castle_hp_per_sequence_max": 1},
        },
    }


class Update101UnsignedTests(unittest.TestCase):
    def test_preview_must_match_exact_approval_and_not_applied(self):
        validate_preview_receipt(approved_receipt())
        for key, changed in [
            ("status", "INSTALLED"),
            ("DataLocal_pack_mutated", True),
            ("only_cat_forms", {"unit289.csv": 1, "unit703.csv": 0}),
        ]:
            bad = copy.deepcopy(approved_receipt())
            bad[key] = changed
            with self.assertRaises(ValueError):
                validate_preview_receipt(bad)
        bad = approved_receipt()
        bad["approved_specs"]["godzilla"]["sensing"] = 3800
        with self.assertRaises(ValueError):
            validate_preview_receipt(bad)

    def test_one_form_only_and_exact_columns(self):
        original_lines = [b",".join([b"0"]*108)+b"\n" for _ in range(3)]
        for name, (form, approved) in TARGET.items():
            original = b"".join(original_lines)
            lines = list(original_lines)
            fields = lines[form].strip().split(b",")
            for index, value in approved.items():
                fields[index] = str(value).encode()
            lines[form] = b",".join(fields) + b"\n"
            candidate = b"".join(lines)
            result = validate_form_delta(original, candidate, file_name=name,
                                        original_sha=hashlib.sha256(original).hexdigest())
            self.assertEqual(result["form_index"], form)
            self.assertEqual(set(map(int, result["columns"])), set(approved))
            corrupted = bytearray(candidate)
            corrupted[-2] = ord("1")
            with self.assertRaises(ValueError):
                validate_form_delta(original, bytes(corrupted), file_name=name,
                                    original_sha=hashlib.sha256(original).hexdigest())
            with self.assertRaises(ValueError):
                validate_form_delta(original, candidate, file_name=name, original_sha="bad")

    def test_unsigned_pack_delta_gate(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original, modified = root/"before.apk", root/"after.apk"
            base = {
                "assets/DataLocal.list": b"same-list",
                "assets/DataLocal.pack": b"same-pack",
                "assets/DownloadLocal.list": b"before-list",
                "assets/DownloadLocal.pack": b"before-pack",
                "classes.dex": b"untouched",
                "META-INF/CERT.RSA": b"old-signature",
            }
            with zipfile.ZipFile(original, "w") as z:
                for name, data in base.items():
                    z.writestr(name, data)
            with zipfile.ZipFile(modified, "w") as z:
                for name, data in base.items():
                    if name.startswith("META-INF/"):
                        continue
                    if name.startswith("assets/DownloadLocal"):
                        data += b"+added"
                    z.writestr(name, data)
            report = audit_unsigned_installpack(original, modified)
            self.assertTrue(report["datalocal_byte_identical"])
            self.assertEqual(len(report["changed_apk_entries"]), 2)
            with zipfile.ZipFile(modified, "a") as z:
                z.writestr("unwanted.txt", "oops")
            with self.assertRaises(ValueError):
                audit_unsigned_installpack(original, modified)


if __name__ == "__main__":
    unittest.main()