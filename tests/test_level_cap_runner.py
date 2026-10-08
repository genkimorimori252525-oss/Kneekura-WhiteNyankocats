from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools/base_mod/run_level_cap_unlock.ps1"
MIGRATION = ROOT / "tools/base_mod/level_cap_unlock.py"


class LevelCapRunnerContractTest(unittest.TestCase):
    def test_apply_is_explicit_and_static_build_happens_first(self):
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("[switch]$Apply", text)
        self.assertIn("if (-not $Apply)", text)
        build_pos = text.index("level_cap_unlock apply")
        promote_pos = text.index("[4/6] Promoting level-cap migration")
        self.assertLess(build_pos, promote_pos)

    def test_exact_backup_is_preserved_before_promotion(self):
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("pre-level-cap-SAVE_DATA", text)
        self.assertIn("SAVE_DATA.kneekura-before-levelcap-v1", text)
        self.assertIn("Staging exact rollback copy and candidate", text)
        self.assertIn("Restore-Backup", text)
        self.assertIn("rollback SHA verification failed", text)

    def test_candidate_and_post_restart_are_semantically_verified(self):
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("level-cap-candidate-verification.json", text)
        self.assertIn("post-restart-level-cap-verification.json", text)
        self.assertGreaterEqual(text.count("level_cap_unlock verify"), 3)
        self.assertIn("force-stop", text)
        self.assertIn("pidof", text)

    def test_no_destructive_package_operation(self):
        text = " ".join(RUNNER.read_text(encoding="utf-8").lower().split())
        for forbidden in (" uninstall ", " pm clear ", " adb root "):
            self.assertNotIn(forbidden, f" {text} ")

    def test_migration_does_not_reference_story_or_event_mutators(self):
        text = MIGRATION.read_text(encoding="utf-8")
        self.assertNotIn("STORY_PROGRESS_OFFSET", text)
        self.assertNotIn("EVENT_UNLOCK_STATE_BASE", text)
        self.assertNotIn("unit_drops", text)
        self.assertIn("current_level_untouched", text)
        self.assertIn("story_event_progress_untouched", text)


if __name__ == "__main__":
    unittest.main()
