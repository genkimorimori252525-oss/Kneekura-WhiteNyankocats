import struct
import unittest

from tools.base_mod.analyze_server_download_gate import (
    EXPECTED_LANE_COUNT,
    EXPECTED_NATIVE_VERSIONS,
    EXPECTED_TOTAL_ARCHIVE_BYTES,
    build_lane_url,
    derive_native_download_versions,
    parse_download_tsv,
)


class ServerDownloadGateTests(unittest.TestCase):
    def test_parse_download_tsv(self) -> None:
        payload = (
            b"\t123\t0123456789abcdef0123456789abcdef\n"
            b"AUnitServer.list\t16\t11111111111111111111111111111111\n"
            b"AUnitServer.pack\t32\t22222222222222222222222222222222\n"
        )
        report = parse_download_tsv(payload, 4)
        self.assertEqual(report["lane"], 4)
        self.assertEqual(report["archive_size"], 123)
        self.assertEqual(report["entry_count"], 2)
        self.assertEqual(report["extracted_bytes"], 48)

    def test_native_version_anchor_derivation(self) -> None:
        vector = EXPECTED_NATIVE_VERSIONS
        native = (
            b"prefix"
            + struct.pack("<" + "I" * len(vector), *vector)
            + b"suffix"
        )
        self.assertEqual(
            derive_native_download_versions(native, EXPECTED_LANE_COUNT),
            vector,
        )

    def test_lane_url_old_and_modern_shapes(self) -> None:
        self.assertEqual(
            build_lane_url(0, 5),
            (
                "https://nyanko-assets.ponosgames.com/iphone/battlecats/"
                "download/battlecats_5_0.zip"
            ),
        )
        self.assertEqual(
            build_lane_url(34, 15_040_000),
            (
                "https://nyanko-assets.ponosgames.com/iphone/battlecats/"
                "download/battlecats_150400_34_00.zip"
            ),
        )

    def test_exact_total_matches_observed_615_mib_family(self) -> None:
        mib = EXPECTED_TOTAL_ARCHIVE_BYTES / (1024 * 1024)
        self.assertGreaterEqual(mib, 615.0)
        self.assertLess(mib, 617.0)


if __name__ == "__main__":
    unittest.main()
