from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Update101OwnerGateSourceTests(unittest.TestCase):
    def test_no_destructive_device_commands_or_silent_install(self):
        src = (ROOT / "tools/base_mod/run_update_101_owner_gates.ps1").read_text(encoding="utf-8")
        self.assertIn("build_update_101_unsigned", src)
        self.assertIn("CollectPrivateServerPacks", src)
        self.assertIn("collect_update_101_server_assets", src)
        self.assertIn("extract_godzilla_owner_rig", src)
        self.assertIn("NOT INSTALLABLE", src)
        for forbidden in ("install-multiple", "uninstall", "pm clear", "rm -rf", "Remove-Item"):
            self.assertNotIn(forbidden, src)
        self.assertIn("existing run_update_101_preflight.ps1", src)

if __name__ == "__main__":
    unittest.main()