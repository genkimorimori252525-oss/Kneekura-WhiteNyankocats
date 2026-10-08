from pathlib import Path
import hashlib
import tempfile
import unittest

from tools.base_mod.cache_server_assets import (
    file_matches,
    latest_file_map,
)


class ServerAssetCacheTests(unittest.TestCase):
    def test_latest_lane_wins_duplicate_file(self) -> None:
        lanes = [
            {
                "lane": 1,
                "entries": [
                    {"name": "same.pack", "size": 10, "md5": "a" * 32},
                    {"name": "old.list", "size": 2, "md5": "b" * 32},
                ],
            },
            {
                "lane": 2,
                "entries": [
                    {"name": "same.pack", "size": 20, "md5": "c" * 32},
                ],
            },
        ]
        latest = latest_file_map(lanes)
        self.assertEqual(latest["same.pack"]["lane"], 2)
        self.assertEqual(latest["same.pack"]["size"], 20)
        self.assertEqual(latest["old.list"]["lane"], 1)

    def test_file_matches_checks_size_and_original_md5(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            path = Path(temp_name) / "file.bin"
            payload = b"battlecats-cache"
            path.write_bytes(payload)
            md5 = hashlib.md5(payload).hexdigest()
            self.assertTrue(file_matches(path, size=len(payload), md5=md5))
            self.assertFalse(file_matches(path, size=len(payload) + 1, md5=md5))
            self.assertFalse(file_matches(path, size=len(payload), md5="0" * 32))


if __name__ == "__main__":
    unittest.main()
