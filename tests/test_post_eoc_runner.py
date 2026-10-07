from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools/base_mod/run_post_eoc_bootstrap.ps1"


class PostEocRunnerContractTest(unittest.TestCase):
    def test_runner_defaults_to_static_only_and_apply_is_explicit(self):
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("[switch]$Apply", text)
        self.assertIn("if (-not $Apply)", text)
        self.assertIn("No device mutation was requested.", text)

    def test_runner_finds_and_verifies_clean_premax_source(self):
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("SAVE_DATA.kneekura-premax", text)
        self.assertIn("tools.base_mod.verify_offline_baseline", text)
        self.assertIn("source-clean-verification.json", text)

    def test_runner_statically_verifies_before_device_mutation(self):
        text = RUNNER.read_text(encoding="utf-8")
        build_pos = text.index("tools.base_mod.build_post_eoc_save")
        verify_pos = text.index("tools.base_mod.verify_post_eoc_save")
        stage_pos = text.index("[5/8] Staging rollback + Post-EoC candidate")
        self.assertLess(build_pos, stage_pos)
        self.assertLess(verify_pos, stage_pos)

    def test_runner_preserves_current_player_state_for_rollback(self):
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("current-before-post-eoc-SAVE_DATA", text)
        self.assertIn("SAVE_DATA.kneekura-before-posteoc", text)
        self.assertIn("Restore-CurrentState", text)
        self.assertIn("ExpectedSha", text)

    def test_runner_never_uninstalls_or_clears_package(self):
        text = " ".join(RUNNER.read_text(encoding="utf-8").lower().split())
        for forbidden in (" uninstall ", " pm clear ", " install-multiple ", " adb root "):
            self.assertNotIn(forbidden, f" {text} ")

    def test_liveops_sidecars_are_prepared_but_not_overclaimed(self):
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("KNEEKURA_CHANNEL.json", text)
        self.assertIn("KNEEKURA_LOGIN_POOL.json", text)
        self.assertIn("KNEEKURA_LOGIN_STATE.json", text)
        self.assertIn("login_runtime_provider_connected = $false", text)
        self.assertIn("event_runtime_schedule_provider_connected = $false", text)


if __name__ == "__main__":
    unittest.main()
