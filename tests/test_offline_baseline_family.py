import hashlib
import struct
import unittest

from tools.base_mod import build_offline_max_save as maxsave


class SemanticBaselineFamilyTest(unittest.TestCase):
    def _build_clean_baseline(self) -> bytes:
        data = bytearray(maxsave.BASELINE_SIZE)
        struct.pack_into("<i", data, 0, 150700)

        for name, expected in (
            ("cat_unlocked", 882),
            ("cat_current_form", 882),
            ("cat_gatya_seen", 882),
            ("unit_drops", 400),
            ("cat_unlocked_forms", 882),
            ("catfruit", 29),
            ("cat_fourth_form", 882),
            ("catseyes", 6),
            ("catamins", 3),
            ("base_materials", 16),
            ("lucky_tickets", 55),
        ):
            count_offset = maxsave.ARRAYS_I32[name][2]
            self.assertIsNotNone(count_offset)
            struct.pack_into("<i", data, count_offset, expected)

        data[484927] = 4
        data[495796] = 42
        struct.pack_into("<h", data, maxsave.TALENT_ORB_COUNT_OFFSET, 0)

        digest = hashlib.md5(
            maxsave.JP_SALT + bytes(data[:-maxsave.HASH_LEN])
        ).hexdigest().encode("ascii")
        data[-maxsave.HASH_LEN:] = digest
        return bytes(data)

    def test_clean_baseline_family_does_not_require_historical_sha(self):
        original = self._build_clean_baseline()
        result = maxsave.validate_baseline_family(original)
        self.assertTrue(result["jp_hash_valid"])
        self.assertEqual(result["game_version"], 150700)

        changed = bytearray(original)
        struct.pack_into("<d", changed, 35, 1234567890.0)
        digest = hashlib.md5(
            maxsave.JP_SALT + bytes(changed[:-maxsave.HASH_LEN])
        ).hexdigest().encode("ascii")
        changed[-maxsave.HASH_LEN:] = digest

        changed_result = maxsave.validate_baseline_family(bytes(changed))
        self.assertTrue(changed_result["jp_hash_valid"])
        self.assertNotEqual(result["sha256"], changed_result["sha256"])

    def test_corrupt_hash_is_rejected(self):
        data = bytearray(self._build_clean_baseline())
        data[100] ^= 1
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            maxsave.validate_baseline_family(bytes(data))

    def test_wrong_version_is_rejected(self):
        data = bytearray(self._build_clean_baseline())
        struct.pack_into("<i", data, 0, 150600)
        digest = hashlib.md5(
            maxsave.JP_SALT + bytes(data[:-maxsave.HASH_LEN])
        ).hexdigest().encode("ascii")
        data[-maxsave.HASH_LEN:] = digest
        with self.assertRaisesRegex(ValueError, "game version"):
            maxsave.validate_baseline_family(bytes(data))

    def test_builder_uses_semantic_baseline_gate(self):
        source = (
            __import__("pathlib").Path(__file__).resolve().parents[1]
            / "tools/base_mod/build_offline_max_save.py"
        ).read_text(encoding="utf-8")
        self.assertIn("baseline_validation = validate_baseline_family(source)", source)
        self.assertNotIn("input SAVE_DATA is not the exact captured bootstrap baseline", source)
        self.assertIn(
            'max(_read_i32(out, I32["tutorial_state"]), 1)',
            source,
        )
        self.assertIn(
            'max(_read_i32(out, I32["story_chapter0_progress"]), 1)',
            source,
        )

    def test_evolved_baseline_is_rejected(self):
        data = bytearray(self._build_clean_baseline())
        start = maxsave.ARRAYS_I32["cat_current_form"][0]
        struct.pack_into("<i", data, start, 1)
        digest = hashlib.md5(
            maxsave.JP_SALT + bytes(data[:-maxsave.HASH_LEN])
        ).hexdigest().encode("ascii")
        data[-maxsave.HASH_LEN:] = digest
        with self.assertRaisesRegex(ValueError, "not a clean first-form baseline"):
            maxsave.validate_baseline_family(bytes(data))


if __name__ == "__main__":
    unittest.main()
