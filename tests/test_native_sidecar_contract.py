from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class NativeSidecarContractTests(unittest.TestCase):
    def test_shipping_default_keeps_io_feature_off(self) -> None:
        header = (
            ROOT / "native/kneekura-shim/include/kneekura_shim.h"
        ).read_text(encoding="utf-8")
        state = (
            ROOT / "native/kneekura-shim/src/kneekura_state.c"
        ).read_text(encoding="utf-8")

        self.assertIn("KNEEKURA_DEFAULT_FEATURE_MASK 0ull", header)
        self.assertIn("KNEEKURA_FEATURE_LOCAL_STATE", header)
        self.assertIn(
            "kneekura_feature_enabled(KNEEKURA_FEATURE_LOCAL_STATE) == 0u",
            state,
        )
        self.assertIn("return KNEEKURA_STATUS_DISABLED;", state)

    def test_sidecar_is_versioned_checked_and_atomic(self) -> None:
        header = (
            ROOT / "native/kneekura-shim/include/kneekura_shim.h"
        ).read_text(encoding="utf-8")
        state = (
            ROOT / "native/kneekura-shim/src/kneekura_state.c"
        ).read_text(encoding="utf-8")

        self.assertIn("KNEEKURA_SIDECAR_SCHEMA_VERSION 1u", header)
        self.assertIn("crc32_bytes", state)
        self.assertIn('".tmp"', state)
        self.assertIn('".bak"', state)
        self.assertIn("rename(temp_path, path)", state)
        self.assertIn("fsync(fd)", state)

    def test_approved_login_clock_rules_exist(self) -> None:
        state = (
            ROOT / "native/kneekura-shim/src/kneekura_state.c"
        ).read_text(encoding="utf-8")
        self.assertIn("observed_epoch_day > state->last_seen_epoch_day", state)
        self.assertIn(
            "state->last_seen_epoch_day > state->last_claim_epoch_day",
            state,
        )
        self.assertIn("(current + 1u) % cycle_length", state)

    def test_two_profile_modes_are_explicit(self) -> None:
        header = (
            ROOT / "native/kneekura-shim/include/kneekura_shim.h"
        ).read_text(encoding="utf-8")
        self.assertIn("KNEEKURA_PROFILE_PERSONAL_MAX = 1", header)
        self.assertIn("KNEEKURA_PROFILE_PRACTICE_CLEAN = 2", header)


if __name__ == "__main__":
    unittest.main()