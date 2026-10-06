from pathlib import Path
import unittest

from tools.base_mod.phase_c_preflight import (
    EXPECTED_BASE_APK_SHA256,
    EXPECTED_COMEBACK_CYCLE,
    EXPECTED_COMEBACK_TEMPLATE,
    EXPECTED_HTTP_METHOD_HASH,
    EXPECTED_NATIVE_BUILD_ID,
    EXPECTED_NATIVE_SHA256,
    EXPECTED_R1_SEED_COUNT,
    EXPECTED_RESEARCH_PACKAGE,
    audit,
)


ROOT = Path(__file__).resolve().parents[1]


class PhaseCPreflightTests(unittest.TestCase):
    def test_repository_preflight_passes(self) -> None:
        report = audit(ROOT)
        self.assertEqual(report["status"], "ready_for_owner_device_observation")
        self.assertEqual(
            report["anchor"]["native_sha256"],
            EXPECTED_NATIVE_SHA256,
        )
        self.assertEqual(
            report["anchor"]["native_build_id"],
            EXPECTED_NATIVE_BUILD_ID,
        )
        self.assertEqual(
            report["anchor"]["base_apk_sha256"],
            EXPECTED_BASE_APK_SHA256,
        )
        self.assertEqual(
            report["anchor"]["new_http_request_insns_sha256"],
            EXPECTED_HTTP_METHOD_HASH,
        )
        self.assertEqual(report["research_package"], EXPECTED_RESEARCH_PACKAGE)
        self.assertEqual(
            report["comeback_template_id"],
            EXPECTED_COMEBACK_TEMPLATE,
        )
        self.assertEqual(
            report["comeback_cycle_length"],
            EXPECTED_COMEBACK_CYCLE,
        )
        self.assertEqual(
            report["local_r1_seed_count"],
            EXPECTED_R1_SEED_COUNT,
        )
        self.assertEqual(report["rarity_rate_vector"], "unresolved-by-design")
        self.assertFalse(report["shipping_frida_allowed"])


if __name__ == "__main__":
    unittest.main()
