from pathlib import Path
import unittest

from tools.base_mod.audit_shim_imports import (
    FORBIDDEN_EXACT_EXPORTS,
    FORBIDDEN_IMPORT_PREFIXES,
    FORBIDDEN_NEEDED_SUBSTRINGS,
)


ROOT = Path(__file__).resolve().parents[1]


class ShimImportAuditPolicyTests(unittest.TestCase):
    def test_policy_covers_network_and_dynamic_hook_seams(self) -> None:
        prefixes = set(FORBIDDEN_IMPORT_PREFIXES)
        for expected in [
            "socket",
            "connect",
            "getaddrinfo",
            "send",
            "recv",
            "SSL_",
            "curl_",
            "dlopen",
            "dlsym",
        ]:
            self.assertIn(expected, prefixes)
        self.assertIn("JNI_OnLoad", FORBIDDEN_EXACT_EXPORTS)

    def test_shipping_source_does_not_embed_hook_transport(self) -> None:
        for path in [
            ROOT / "native/kneekura-shim/src/kneekura_shim.c",
            ROOT / "native/kneekura-shim/src/kneekura_state.c",
            ROOT / "native/kneekura-shim/src/kneekura_provider.c",
        ]:
            source = path.read_text(encoding="utf-8")
            for token in [
                "socket(",
                "connect(",
                "dlopen(",
                "dlsym(",
                "JNI_OnLoad",
            ]:
                self.assertNotIn(token, source)

    def test_policy_rejects_common_network_libraries(self) -> None:
        tokens = set(FORBIDDEN_NEEDED_SUBSTRINGS)
        self.assertIn("ssl", tokens)
        self.assertIn("curl", tokens)
        self.assertIn("cronet", tokens)


if __name__ == "__main__":
    unittest.main()
