from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "tools/base_mod/run_offline_max_bootstrap.ps1"
ROLLBACK = ROOT / "tools/base_mod/run_offline_max_rollback.ps1"


class OfflineMaxBootstrapRunnerTest(unittest.TestCase):
    def test_bootstrap_is_research_package_and_preservation_first(self):
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn('[string]$Package = "jp.kn.trace.battlecats"', text)
        self.assertIn("pre-apply-device-SAVE_DATA.rollback", text)
        self.assertIn("KNEEKURA_OFFLINE_MAX_BOOTSTRAP.json", text)
        self.assertIn("Type APPLY", text)
        self.assertIn("disable Wi-Fi and mobile data", text)
        self.assertIn("Restore-Baseline", text)
        self.assertIn("post-restart-SAVE_DATA", text)

    def test_bootstrap_never_uninstalls_or_clears_package(self):
        text = " ".join(BOOTSTRAP.read_text(encoding="utf-8").lower().split())
        for forbidden in (" uninstall ", " pm clear ", " install-multiple ", " adb root "):
            self.assertNotIn(forbidden, f" {text} ")

    def test_bootstrap_pins_exact_baseline_and_candidate(self):
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn(
            "cad00e84f3d64910b623b8a89b57ae1a37e8947554f4b418f50efa1c6bdc1d3c",
            text,
        )
        self.assertIn(
            "afa5ee976a85d0640244393ba8326c21a5ef5b4378228fbf85e172e28c7beb18",
            text,
        )

    def test_rollback_requires_exact_premax_baseline(self):
        text = ROLLBACK.read_text(encoding="utf-8")
        self.assertIn(
            "cad00e84f3d64910b623b8a89b57ae1a37e8947554f4b418f50efa1c6bdc1d3c",
            text,
        )
        self.assertIn("manual-rollback-verify-SAVE_DATA", text)
        self.assertIn("rollback_verified = $true", text)


if __name__ == "__main__":
    unittest.main()
