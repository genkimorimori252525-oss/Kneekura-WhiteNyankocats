from pathlib import Path
import unittest

from tools.base_mod.phase_c_preflight import (
    EXPECTED_BASE_APK_SHA256,
    EXPECTED_COMEBACK_CYCLE,
    EXPECTED_COMEBACK_TEMPLATE,
    EXPECTED_HTTP_METHOD_HASH,
    EXPECTED_LA32_RUN_HASH,
    EXPECTED_LZ22_RUN_HASH,
    EXPECTED_LZ22_FALLBACK_HASH,
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
        self.assertEqual(report["status"], "ready_for_original_ui_data_proof")
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
        self.assertEqual(
            report["anchor"]["la32_run_insns_sha256"],
            EXPECTED_LA32_RUN_HASH,
        )
        self.assertEqual(
            report["anchor"]["lz22_run_insns_sha256"],
            EXPECTED_LZ22_RUN_HASH,
        )
        self.assertEqual(
            report["anchor"]["lz22_fallback_insns_sha256"],
            EXPECTED_LZ22_FALLBACK_HASH,
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
        self.assertTrue(report["static_http_bridge"]["implemented"])
        self.assertTrue(report["static_http_bridge"]["frida_free"])
        self.assertTrue(report["runtime_anchor_sets"]["login"])
        self.assertEqual(
            report["runtime_anchor_sets"]["gacha_dataset_loader"],
            "0x5ed65c",
        )
        self.assertTrue(report["tiny_gacha_prototype"]["append_only"])
        self.assertFalse(
            report["tiny_gacha_prototype"]["rarity_probability_vector_defined"]
        )


if __name__ == "__main__":
    unittest.main()
