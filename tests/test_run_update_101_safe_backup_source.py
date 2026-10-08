from pathlib import Path
import unittest

class Update101SafeBackupSourceTests(unittest.TestCase):
    def test_no_destructive_commands(self):
        source = (Path(__file__).resolve().parents[1] /
                  "tools/base_mod/run_update_101_safe_backup.ps1").read_text(encoding="utf-8")
        self.assertIn("verify_update_101_device", source)
        self.assertIn("--backup-dir", source)
        self.assertIn("--signed-splits", source)
        self.assertIn("NO INSTALL was attempted", source)
        for forbidden in ("install-multiple", "uninstall", "force-stop", "pm clear", "Remove-Item"):
            self.assertNotIn(forbidden, source)

if __name__ == "__main__":
    unittest.main()