from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PERSISTENCE = ROOT / "tools/base_mod/run_offline_max_persistence_gate.ps1"
VERIFIER = ROOT / "tools/base_mod/verify_offline_max_save.py"


class OfflineMaxPersistenceGateTest(unittest.TestCase):
    def test_runner_uses_only_install_r_and_never_uninstall(self):
        raw = PERSISTENCE.read_text(encoding="utf-8")
        text = " ".join(raw.lower().split())
        self.assertIn('"install-multiple"', raw)
        self.assertIn('"--no-streaming"', raw)
        self.assertIn('"-r"', raw)
        self.assertNotIn(" uninstall ", f" {text} ")
        self.assertNotIn(" pm clear ", f" {text} ")

    def test_runner_requires_sentinel_and_verifies_before_and_after(self):
        text = PERSISTENCE.read_text(encoding="utf-8")
        self.assertIn("KNEEKURA_OFFLINE_MAX_BOOTSTRAP.json", text)
        self.assertGreaterEqual(text.count("verify_offline_max_save"), 2)
        self.assertIn("pre-install-r-SAVE_DATA", text)
        self.assertIn("post-install-r-SAVE_DATA", text)
        self.assertIn("offline-max-persistence-gate-result.json", text)
        self.assertIn("offline-max-persistence-gate.log", text)
        self.assertIn("Restore-PreUpgradeSave", text)

    def test_persistence_gate_allows_original_game_rewrite_layout(self):
        text = PERSISTENCE.read_text(encoding="utf-8")
        self.assertGreaterEqual(text.count("--allow-runtime-rewrite"), 2)

    def test_verifier_is_read_only(self):
        text = VERIFIER.read_text(encoding="utf-8")
        self.assertIn("without modifying the file", text)
        self.assertNotIn("write_bytes(", text)
        self.assertIn('"passed": not failures', text)


if __name__ == "__main__":
    unittest.main()
