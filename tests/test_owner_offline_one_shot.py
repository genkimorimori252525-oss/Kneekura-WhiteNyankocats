"""Static fail-closed owner research one-shot contract, without real secrets/ADB.

The separate OWNER-READY-TO-SIGN wrapper owns the user's on-device prompt.
This test must never execute the live update or read any real APK/SAVE.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/base_mod/OWNER-OFFLINE-615-ONE-SHOT.ps1"


class OwnerLocalOfflineOneShotGuardTests(unittest.TestCase):
    def test_staged_import_same_signer_and_boot_are_separately_checked(self):
        text = SCRIPT.read_text(encoding="utf-8-sig")
        self.assertIn("ONE_AUTHORIZED_RESEARCH_DEVICE_REQUIRED_NO_ACTION", text)
        self.assertIn("EXISTING_ISOLATED_ORIGINAL_SIX_SPLITS_REQUIRED", text)
        self.assertIn("ORIGINAL_393_EXTERNAL_STAGE_BLOCKED_NO_INSTALL", text)
        self.assertIn("--stage --repair-incomplete", text)
        self.assertIn("OWNER_PRIVATE_SIGNING_FAILED_NO_INSTALL", text)
        self.assertIn("-EnableOfflineServerImport", text)
        self.assertIn("-DoBuild -SigningAlias $SigningAlias", text)
        self.assertIn("EXACTLY_ONE_NEW_OWNER_SIGNED_APK_FOLDER", text)
        self.assertIn("REAL_INSTALLED_RESEARCH_SIGNER_MISMATCH_NO_INSTALL", text)
        self.assertIn("ANDROID_DEVICE_CHANGED_AFTER_SIGNING_ABORT", text)
        self.assertIn("SIX_SPLIT_COUNT", text.upper())
        self.assertIn("-ApproveUpdateOfIsolatedResearchApp", text)
        self.assertIn("-ObserveSeconds 30", text)
        self.assertIn("audit_original_offline_boot_events", text)
        self.assertLess(
            text.index("--stage --repair-incomplete"),
            text.index("-DoBuild -SigningAlias $SigningAlias"),
        )
        self.assertLess(
            text.index("-CandidateSignedSplitDirectory $signed"),
            text.index("shell am force-stop jp.kn.local.battlecats"),
        )
        self.assertLess(
            text.index("-ApproveUpdateOfIsolatedResearchApp"),
            text.index("-ObserveSeconds 30"),
        )

    def test_no_publisher_save_mutation_or_unsafe_signing(self):
        text = SCRIPT.read_text(encoding="utf-8-sig")
        for forbidden in (
            "shell pm clear", "adb uninstall", " adb uninstall ",
            "install-multiple", "Clear-Item", "Remove-Item",
            "New-Item -ItemType", "--storepass",
            "--keypass", "-Password", "newkey",
            "jp.co.ponos.battlecats", "Disable-NetAdapter",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, text)
        self.assertNotIn("SECRET_", text)
        self.assertNotIn("Get-Credential", text)
        self.assertIn("OWNER-READY-TO-SIGN.ps1", text)
        self.assertIn("ONE_RESEARCH_UPDATE_FAILED_DO_NOT_RETRY", text)

    def test_preflight_does_not_require_secret_or_install(self):
        text = SCRIPT.read_text(encoding="utf-8-sig")
        preflight = text[text.index("    if ($OnlyPreflight) {"):
                         text.index("    # The 393 exact original assets")]
        self.assertIn("& py @prepareArgs", preflight)
        self.assertIn("OWNER_OFFLINE_ONE_SHOT_READONLY_PREFLIGHT_PASS", preflight)
        self.assertNotIn("-DoBuild", preflight)
        self.assertNotIn("-ApproveUpdateOfIsolatedResearchApp", preflight)
        self.assertNotIn("shell am force-stop", preflight)


if __name__ == "__main__":
    unittest.main()
