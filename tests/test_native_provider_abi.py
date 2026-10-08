from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class NativeProviderAbiTests(unittest.TestCase):
    def test_provider_bits_default_to_off(self) -> None:
        header = (
            ROOT / "native/kneekura-shim/include/kneekura_shim.h"
        ).read_text(encoding="utf-8")
        self.assertIn("KNEEKURA_DEFAULT_FEATURE_MASK 0ull", header)
        for token in [
            "KNEEKURA_FEATURE_LOCAL_EVENTS",
            "KNEEKURA_FEATURE_SUPER_GACHA",
            "KNEEKURA_FEATURE_LOGIN_BONUS",
            "KNEEKURA_FEATURE_STAGE_CATFOOD",
        ]:
            self.assertIn(token, header)

    def test_approved_provider_values_exist(self) -> None:
        source = (
            ROOT / "native/kneekura-shim/src/kneekura_provider.c"
        ).read_text(encoding="utf-8")
        self.assertIn("draw_count == 1u", source)
        self.assertIn("return 150;", source)
        self.assertIn("draw_count == 11u", source)
        self.assertIn("return 1500;", source)
        self.assertIn("difficulty == 11u", source)
        self.assertIn("return 8;", source)
        self.assertIn("return 10;", source)

    def test_provider_source_has_no_runtime_hook_transport(self) -> None:
        source = (
            ROOT / "native/kneekura-shim/src/kneekura_provider.c"
        ).read_text(encoding="utf-8")
        for forbidden in ["dlsym(", "dlopen(", "socket(", "connect(", "JNI_OnLoad"]:
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
