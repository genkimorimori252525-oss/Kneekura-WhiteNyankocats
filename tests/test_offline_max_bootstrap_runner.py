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

    def test_bootstrap_uses_semantic_baseline_and_dynamic_candidate_hash(self):
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("tools.base_mod.verify_offline_baseline", text)
        self.assertIn("pre-apply-baseline-verification.json", text)
        self.assertIn("candidateSha = Get-Sha256", text)
        self.assertIn("offline-max-candidate-verification.json", text)
        self.assertNotIn("ExpectedBaselineSha256", text)
        self.assertNotIn("ExpectedCandidateSha256", text)

    def test_rollback_requires_semantic_clean_baseline(self):
        text = ROLLBACK.read_text(encoding="utf-8")
        self.assertIn("tools.base_mod.verify_offline_baseline", text)
        self.assertIn("rollback-baseline-verification.json", text)
        self.assertIn("manual-rollback-verify-SAVE_DATA", text)
        self.assertIn("rollback_verified = $true", text)
        self.assertNotIn("ExpectedBaselineSha256", text)


    def test_bootstrap_semantically_verifies_post_restart_save(self):
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("post-restart-max-verification.json", text)
        self.assertIn("tools.base_mod.verify_offline_max_save", text)
        self.assertIn("--allow-runtime-rewrite", text)
        self.assertIn("failed even the stable-prefix runtime verification", text)


if __name__ == "__main__":
    unittest.main()
