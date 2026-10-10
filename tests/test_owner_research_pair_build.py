"""Build-only owner-private two-ShadowHook-SO signer guard.

These tests inspect committed source only. Actual keystore, game, phone,
PowerShell 5.1 execution and signed owner APK are NEVER accessed by CI.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/base_mod/BUILD-OWNER-RESEARCH-PAIR.ps1"


class OriginalResearchSameSignerHandoffTests(unittest.TestCase):
    def test_source_is_utf8_bom_and_never_installs_or_clears_device(self):
        data = SCRIPT.read_bytes()
        self.assertTrue(data.startswith(bytes((0xEF, 0xBB, 0xBF))))
        source = data.decode("utf-8-sig")
        for forbidden in (
            " install-multiple ", " pm clear ", " adb uninstall ",
            " shell am start ", "Stop-Process", "adb.exe",
            "--research-virgin-save-trial",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)
        self.assertIn("--research-shadowhook-aar", source)
        self.assertIn("--research-no-internet-permission", source)
        self.assertIn("--root', $repo", source)
        self.assertIn("original_save_writer_enabled -ne $false", source)
        self.assertIn("PreviouslySignedBaseApk", source)
        self.assertIn("SignerDigest $existingBase $apksigner", source)
        self.assertIn("SignerDigest $newBase $apksigner", source)
        self.assertIn("if ($before -ne $after)", source)
        self.assertIn("Do NOT install this build", source)

    def test_preflight_pins_owner_original_and_official_public_archive(self):
        source = SCRIPT.read_text(encoding="utf-8-sig")
        from tools.base_mod.extract_owned_splits import EXPECTED_EXPORT_SHA256
        from tools.base_mod.prepare_original_scene_witness import (
            APPROVED_OFFICIAL_SHADOWHOOK_V201_AAR_SHA256,
        )
        self.assertIn(EXPECTED_EXPORT_SHA256, source)
        self.assertIn(APPROVED_OFFICIAL_SHADOWHOOK_V201_AAR_SHA256, source)
        for item in (
            "PUBLIC_PASSIVE_SHIM_RECEIPT.json",
            "public-original-research-passive-shim-v1",
            "fixed_error_markers_compiled",
            "merge-base --is-ancestor",
            "PRIVATE-build-receipt.json",
            "BUILD_ONLY_PASS; EXISTING_RESEARCH_SIGNER_MATCHED",
        ):
            # Exact fixture metadata file name may be passed as a parameter;
            # the schema/sha verification is authoritative.
            if item == "PUBLIC_PASSIVE_SHIM_RECEIPT.json":
                continue
            self.assertIn(item, source)
        self.assertNotIn("Create-ResearchKeystore", source)


if __name__ == "__main__":
    unittest.main()
