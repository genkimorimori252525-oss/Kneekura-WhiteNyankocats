from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.base_mod.verify_shipping_boundary import (
    PRODUCT_FLAVORS,
    RESEARCH_PACKAGE,
    _scan_apk_forbidden_markers,
    audit_repository,
)


ROOT = Path(__file__).resolve().parents[1]


class ShippingBoundaryTests(unittest.TestCase):
    def test_repository_shipping_boundary_passes(self) -> None:
        report = audit_repository(ROOT)
        self.assertEqual(tuple(report["product_flavors"]), PRODUCT_FLAVORS)
        self.assertEqual(report["research_package"], RESEARCH_PACKAGE)
        self.assertFalse(report["shipping_builders_reference_frida"])
        self.assertTrue(report["research_gadget_path_isolated"])
        self.assertTrue(report["research_log_compiled_only_for_research"])
        self.assertTrue(report["original_http_fallthrough_required"])
        self.assertTrue(report["external_files_dir_default_off"])
        self.assertTrue(report["external_files_dir_research_only"])

    def test_scanner_rejects_frida_entry_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            apk = Path(temp_name) / "bad.apk"
            with zipfile.ZipFile(apk, "w") as archive:
                archive.writestr(
                    "lib/arm64-v8a/libfrida-gadget.so",
                    b"placeholder",
                )
            findings = _scan_apk_forbidden_markers(apk)
            self.assertTrue(findings)
            self.assertTrue(
                any("research payload entry" in row["reason"] for row in findings)
            )

    def test_scanner_rejects_research_package_in_dex_surface(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            apk = Path(temp_name) / "bad.apk"
            with zipfile.ZipFile(apk, "w") as archive:
                archive.writestr(
                    "classes5.dex",
                    b"dex\n035\x00...jp.kn.trace.battlecats...",
                )
            findings = _scan_apk_forbidden_markers(apk)
            self.assertTrue(
                any("jp.kn.trace.battlecats" in row["reason"] for row in findings)
            )

    def test_shipping_builder_sources_do_not_import_research_gadget(self) -> None:
        for relative in (
            "tools/base_mod/build_owned_boot_smoke.py",
            "tools/base_mod/build_owned_static_http_bridge.py",
            "tools/base_mod/build_owned_gacha_ui_proof.py",
        ):
            source = (ROOT / relative).read_text(encoding="utf-8")
            self.assertNotIn("inject_research_gadget", source)
            self.assertNotIn("libfrida-gadget", source)
            self.assertNotIn("TRACE_SCRIPT_ENTRY", source)


if __name__ == "__main__":
    unittest.main()
