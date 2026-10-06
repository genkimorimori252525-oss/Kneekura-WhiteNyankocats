from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class NativeShimSourceContractTests(unittest.TestCase):
    def test_phase_a_shim_is_inert_by_default(self) -> None:
        header = (
            ROOT / "native/kneekura-shim/include/kneekura_shim.h"
        ).read_text(encoding="utf-8")
        source = (
            ROOT / "native/kneekura-shim/src/kneekura_shim.c"
        ).read_text(encoding="utf-8")

        self.assertIn("KNEEKURA_DEFAULT_FEATURE_MASK 0ull", header)
        self.assertIn("kneekura_feature_mask", source)
        self.assertIn("kneekura_bootstrap_ctor", source)

        forbidden = [
            "dlopen(",
            "dlsym(",
            "socket(",
            "connect(",
            "fopen(",
            "open(",
            "JNI_OnLoad",
        ]
        for token in forbidden:
            self.assertNotIn(token, source)

    def test_shim_is_pinned_to_exact_native_anchor(self) -> None:
        source = (
            ROOT / "native/kneekura-shim/src/kneekura_shim.c"
        ).read_text(encoding="utf-8")
        inject = (
            ROOT / "tools/base_mod/inject_shim.py"
        ).read_text(encoding="utf-8")

        expected_sha = (
            "333d2974ab2ff881fd70087fd62dea7d12d82addbc55cab2f2a675ad67e3a7e2"
        )
        expected_build = "8cb3815648eb9642da10bfb039d71bff7a3519bd"
        self.assertIn(expected_sha, source)
        self.assertIn(expected_sha, inject)
        self.assertIn(expected_build, source)
        self.assertIn(expected_build, inject)
        self.assertIn('SHIM_SONAME = "libkneekura.so"', inject)


if __name__ == "__main__":
    unittest.main()