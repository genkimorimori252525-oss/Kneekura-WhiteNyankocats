"""Ensure the familiar folder-overwrite installer remains fail-closed."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "tools/base_mod/run_independent_alpha_update.ps1"

class FamiliarOverlayUpdateTests(unittest.TestCase):
    def test_named_apply_gate_and_pinned_artifact_hashes(self):
        source = WRAPPER.read_text(encoding="utf-8")
        self.assertIn("[switch]$Apply", source)
        self.assertIn("if (-not $Apply)", source)
        self.assertIn("Get-FileHash", source)
        self.assertIn("9fc91ad09da1f242669404b86abbb53030aca133206f27c2cfb501a443a9ec3b", source)
        self.assertIn("jp.kneekura.whitenyankocats", source)
        self.assertIn("independent_alpha_20261009", source)
        self.assertIn("& $installer @installerArgs", source)
        self.assertIn("[switch]$TransferOwnedExport", source)
        self.assertIn("nyanko_battlecats_2026-10-06.zip", source)
    def test_refuses_destructive_or_original_save_operations(self):
        source = WRAPPER.read_text(encoding="utf-8")
        for forbidden in ("adb uninstall", "pm clear", "install -d", "SAVE_DATA", "Remove-Item -Recurse"):
            if forbidden == "SAVE_DATA":
                # may appear in explanatory output; commands must not touch it
                self.assertNotIn("SAVE_DATA -Destination", source)
                continue
            self.assertNotIn(forbidden, source)

if __name__ == "__main__":
    unittest.main()
