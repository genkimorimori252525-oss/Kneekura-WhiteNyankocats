from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.base_mod.build_owned_research_trace import RESEARCH_FLAVOR
from tools.base_mod.inject_research_gadget import (
    GADGET_CONFIG,
    GADGET_CONFIG_ENTRY,
    GADGET_ENTRY,
    GADGET_SONAME,
    TRACE_SCRIPT_ENTRY,
)
from tools.base_mod.package_flavor import FLAVOR_PACKAGES
from tools.base_mod.verify_parity import _split_diff


ROOT = Path(__file__).resolve().parents[1]


class ResearchTraceBuilderContractTests(unittest.TestCase):
    def test_research_package_isolated_from_product_profiles(self) -> None:
        self.assertEqual(RESEARCH_FLAVOR, "research")
        self.assertEqual(
            FLAVOR_PACKAGES["research"],
            "jp.kn.trace.battlecats",
        )
        self.assertNotEqual(
            FLAVOR_PACKAGES["research"],
            FLAVOR_PACKAGES["personal"],
        )
        self.assertNotEqual(
            FLAVOR_PACKAGES["research"],
            FLAVOR_PACKAGES["practice"],
        )

    def test_gadget_layout_matches_tbcml_style_names(self) -> None:
        self.assertEqual(GADGET_SONAME, "libfrida-gadget.so")
        self.assertEqual(
            GADGET_ENTRY,
            "lib/arm64-v8a/libfrida-gadget.so",
        )
        self.assertEqual(
            GADGET_CONFIG_ENTRY,
            "lib/arm64-v8a/libfrida-gadget.config.so",
        )
        self.assertEqual(
            TRACE_SCRIPT_ENTRY,
            "lib/arm64-v8a/libbc_script.js.so",
        )
        self.assertIn(b'"type":"script"', GADGET_CONFIG)
        self.assertIn(b"libbc_script.js.so", GADGET_CONFIG)

    def test_research_builder_never_downloads_frida(self) -> None:
        source = (
            ROOT / "tools/base_mod/build_owned_research_trace.py"
        ).read_text(encoding="utf-8")
        injector = (
            ROOT / "tools/base_mod/inject_research_gadget.py"
        ).read_text(encoding="utf-8")
        joined = source + "\n" + injector
        for token in [
            "requests.get(",
            "urllib.request",
            "curl ",
            "wget ",
            "download_gadgets",
        ]:
            self.assertNotIn(token, joined)
        self.assertIn("--frida-gadget", source)

    def test_split_diff_ignores_android_signing_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            original = root / "original.apk"
            modified = root / "modified.apk"
            with zipfile.ZipFile(original, "w") as archive:
                archive.writestr("AndroidManifest.xml", b"same")
                archive.writestr("assets/data.bin", b"payload")
                archive.writestr("stamp-cert-sha256", b"old-source-stamp")
                archive.writestr("pinlist.meta", b"old-pin-layout")
            with zipfile.ZipFile(modified, "w") as archive:
                archive.writestr("AndroidManifest.xml", b"same")
                archive.writestr("assets/data.bin", b"payload")
            self.assertEqual(
                _split_diff(original, modified),
                {"added": [], "removed": [], "changed": []},
            )

    def test_research_builder_uses_exact_owner_export_and_static_audit(self) -> None:
        source = (
            ROOT / "tools/base_mod/build_owned_research_trace.py"
        ).read_text(encoding="utf-8")
        self.assertIn("EXPECTED_EXPORT_SHA256", source)
        self.assertIn("verify_research_trace_set", source)
        self.assertIn("TRACE-INSTRUCTIONS.txt", source)
        self.assertIn("summarize_service_trace", source)


if __name__ == "__main__":
    unittest.main()
