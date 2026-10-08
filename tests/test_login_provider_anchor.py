from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LoginProviderAnchorTests(unittest.TestCase):
    def test_exact_comeback_template_constants_are_pinned(self) -> None:
        header = (
            ROOT / "native/kneekura-shim/include/kneekura_shim.h"
        ).read_text(encoding="utf-8")
        self.assertIn("KNEEKURA_COMEBACK_TEMPLATE_ID 949u", header)
        self.assertIn("KNEEKURA_COMEBACK_CYCLE_LENGTH 7u", header)

    def test_selector_is_default_off_and_passes_original_id(self) -> None:
        source = (
            ROOT / "native/kneekura-shim/src/kneekura_provider.c"
        ).read_text(encoding="utf-8")
        self.assertIn("kneekura_provider_login_template_id", source)
        self.assertIn("return original_template_id;", source)
        self.assertIn("return KNEEKURA_COMEBACK_TEMPLATE_ID;", source)

    def test_reward_values_are_not_duplicated_in_native_provider(self) -> None:
        source = (
            ROOT / "native/kneekura-shim/src/kneekura_provider.c"
        ).read_text(encoding="utf-8")
        for forbidden in [
            "1000000",
            "2000000",
            "レアチケット",
            "にゃんこチケット",
        ]:
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
