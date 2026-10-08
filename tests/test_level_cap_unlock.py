import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock

from tools.base_mod import level_cap_unlock as cap


class NativeLevelCapMigrationTest(unittest.TestCase):
    def synthetic_save(self) -> bytes:
        size = 496_340
        data = bytearray(size)
        struct.pack_into("<i", data, 0, cap.GAME_VERSION)
        struct.pack_into(
            "<i",
            data,
            cap.MAX_UPGRADE_COUNT_OFFSET,
            cap.EXPECTED_CAT_COUNT,
        )

        # Distinct plus/base values prove the migration preserves plus and
        # raises base monotonically rather than resetting records.
        struct.pack_into(
            "<HH",
            data,
            cap.MAX_UPGRADE_DATA_OFFSET + 10 * cap.MAX_UPGRADE_RECORD_SIZE,
            7,
            5,
        )
        struct.pack_into(
            "<HH",
            data,
            cap.MAX_UPGRADE_DATA_OFFSET + 20 * cap.MAX_UPGRADE_RECORD_SIZE,
            9,
            45,
        )

        digest = hashlib.md5(b"battlecats" + bytes(data[:-32])).hexdigest()
        data[-32:] = digest.encode("ascii")
        return bytes(data)

    def fake_targets(self):
        return (
            {
                10: {
                    "original_max": 20,
                    "native_hard_max": 60,
                    "effective_target": 60,
                    "required_increment": 40,
                },
                20: {
                    "original_max": 20,
                    "native_hard_max": 50,
                    "effective_target": 50,
                    "required_increment": 30,
                },
                30: {
                    "original_max": 20,
                    "native_hard_max": 20,
                    "effective_target": 20,
                    "required_increment": 0,
                },
            },
            {
                "eligible_count": 3,
                "requested_cap": 60,
                "effective_target_distribution": {20: 1, 50: 1, 60: 1},
                "native_hard_cap_distribution": {20: 1, 50: 1, 60: 1},
                "unitbuy_sha256": "synthetic",
                "required_level60_ids": [],
            },
        )

    def test_layout_contract_is_pinned(self):
        self.assertEqual(cap.MAX_UPGRADE_COUNT_OFFSET, 306_330)
        self.assertEqual(cap.MAX_UPGRADE_DATA_OFFSET, 306_334)
        self.assertEqual(cap.MAX_UPGRADE_RECORD_SIZE, 4)
        self.assertEqual(cap.EXPECTED_CAT_COUNT, 882)
        self.assertEqual(cap.REQUESTED_CAP, 60)

    def test_apply_changes_only_cap_records_and_hash(self):
        source = self.synthetic_save()
        with mock.patch.object(cap, "_derive_targets", return_value=self.fake_targets()):
            built, report = cap.apply_native_level_cap_unlock(
                source,
                Path("synthetic-export.zip"),
            )

        rec10 = cap.MAX_UPGRADE_DATA_OFFSET + 10 * cap.MAX_UPGRADE_RECORD_SIZE
        rec20 = cap.MAX_UPGRADE_DATA_OFFSET + 20 * cap.MAX_UPGRADE_RECORD_SIZE
        rec30 = cap.MAX_UPGRADE_DATA_OFFSET + 30 * cap.MAX_UPGRADE_RECORD_SIZE

        self.assertEqual(struct.unpack_from("<HH", built, rec10), (7, 40))
        # Existing 45 is above the official required increment of 30; never lower.
        self.assertEqual(struct.unpack_from("<HH", built, rec20), (9, 45))
        self.assertEqual(struct.unpack_from("<HH", built, rec30), (0, 0))

        changed_non_hash = [
            i
            for i, (before, after) in enumerate(zip(source[:-32], built[:-32]))
            if before != after
        ]
        self.assertTrue(changed_non_hash)
        self.assertTrue(
            all(
                cap.MAX_UPGRADE_DATA_OFFSET
                <= i
                < cap.MAX_UPGRADE_DATA_OFFSET
                + cap.EXPECTED_CAT_COUNT * cap.MAX_UPGRADE_RECORD_SIZE
                for i in changed_non_hash
            )
        )
        self.assertTrue(report["mutation"]["current_level_untouched"])
        self.assertTrue(report["mutation"]["ownership_untouched"])
        self.assertTrue(report["mutation"]["story_event_progress_untouched"])
        self.assertTrue(report["mutation"]["catseyes_used_history_untouched"])

    def test_verify_accepts_native_caps_and_preserved_higher_cap(self):
        source = self.synthetic_save()
        with mock.patch.object(cap, "_derive_targets", return_value=self.fake_targets()):
            built, _ = cap.apply_native_level_cap_unlock(
                source,
                Path("synthetic-export.zip"),
            )
            result = cap.verify_native_level_cap_unlock(
                built,
                Path("synthetic-export.zip"),
            )

        self.assertTrue(result["passed"])
        self.assertEqual(result["failures"], [])
        self.assertEqual(result["satisfied_count"], 3)


if __name__ == "__main__":
    unittest.main()
