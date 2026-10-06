from pathlib import Path
import unittest

from tools.base_mod.verify_shipping_profile import (
    FORBIDDEN_BINARY_MARKERS,
    FORBIDDEN_ENTRY_TOKENS,
)


ROOT = Path(__file__).resolve().parents[1]


class ShippingProfileParityTests(unittest.TestCase):
    def test_research_payloads_are_explicitly_forbidden(self) -> None:
        joined = " ".join(FORBIDDEN_ENTRY_TOKENS)
        self.assertIn("frida", joined)
        self.assertIn("trace_service_bridge", joined)
        self.assertIn("replay_backup_offline", joined)

        binary = b" ".join(FORBIDDEN_BINARY_MARKERS)
        self.assertIn(b"KNEEKURA_TRACE", binary)
        self.assertIn(b"KNEEKURA_REPLAY", binary)
        self.assertIn(b"KNEEKURA_STATIC_HTTP", binary)
        self.assertIn(b"libfrida-gadget", binary)

    def test_shipping_verifier_requires_original_scene_and_feature_off(self) -> None:
        source = (
            ROOT / "tools/base_mod/verify_shipping_profile.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"original_scene_host_preserved"', source)
        self.assertIn('"verification_harness_ui_absent"', source)
        self.assertIn('"installpack_game_payload_preserved"', source)
        self.assertIn('arm64.get("feature_mask_default") != 0', source)
        self.assertIn('arm64.get("extension_off_fallthrough") is not True', source)
        self.assertIn('expected=False,\n                    replacement=False', source)
        self.assertIn('"classes5.dex"', source)

    def test_final_smoke_builds_both_shipping_profiles_and_gacha_proof(self) -> None:
        source = (
            ROOT / "tools/base_mod/run_phase_c_final_smoke.ps1"
        ).read_text(encoding="utf-8")
        self.assertIn("build_owned_boot_smoke", source)
        self.assertIn('"--flavor", "personal"', source)
        self.assertIn('"--flavor", "practice"', source)
        self.assertIn("verify_shipping_profile", source)
        self.assertIn("build_owned_gacha_ui_proof", source)
        self.assertIn("gacha_proof_set_id = 1089", source)
        self.assertIn("gacha_proof_units = @(37, 30, 34)", source)
        self.assertIn("schedule_provider_required", source)
        self.assertIn("Did the normal Battle Cats Rare Gacha screen open", source)


if __name__ == "__main__":
    unittest.main()
