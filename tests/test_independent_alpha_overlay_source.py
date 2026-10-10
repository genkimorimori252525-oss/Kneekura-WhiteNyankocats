"""Ensure the familiar folder-overwrite installer remains fail-closed."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "tools/base_mod/run_independent_alpha_update.ps1"

class FamiliarOverlayUpdateTests(unittest.TestCase):
    def test_named_apply_gate_and_pinned_artifact_hashes(self):
        source = WRAPPER.read_text(encoding="utf-8")
        self.assertIn("[switch]$Apply", source)
        self.assertIn("if (-not $Apply)", source)
        self.assertIn("Get-FileHash", source)
        self.assertIn("491bf95fe1f494460c280ef1c253ccd25a303bfc31b5dd916f23564d4e30c3c1", source)
        self.assertIn("jp.kneekura.whitenyankocats", source)
        self.assertIn("independent_alpha_20261009", source)
        self.assertIn("433e7d684b27f2d27e3b2250103521f996a4f5b9", source)
        self.assertIn("& $installer @installerArgs", source)
        self.assertIn("[switch]$TransferOwnedExport", source)
        self.assertIn("nyanko_battlecats_2026-10-06.zip", source)
    def test_windows_powershell51_utf8_bom_and_installer_hash(self):
        # Windows powershell.exe 5.1 reads non-BOM scripts in the local
        # ANSI encoding. Japanese text can break parsing before any command.
        raw = WRAPPER.read_bytes()
        self.assertTrue(
            raw.startswith(bytes((0xEF, 0xBB, 0xBF))),
            "Windows PowerShell 5.1 requires UTF-8 BOM for this Japanese script",
        )
        parsed = raw.decode("utf-8-sig")
        self.assertTrue(parsed.startswith("param("))
        self.assertIn(
            "b7302c34b18f705bab5c374935572f250ce9e221ba400dfcc522ba7fa76186ec",
            parsed,
        )
        self.assertNotIn("5f2b19732ee61913863b3bf8147137706f284b85d837e0e9886e68e0965b0b25", parsed)

    def test_null_java_home_regression_and_distribution_digests(self):
        helper = ROOT / "tools/base_mod/resolve_java_keytool.ps1"
        self.assertTrue(helper.exists())
        self.assertTrue(helper.read_bytes().startswith(bytes((0xEF, 0xBB, 0xBF))))
        source = helper.read_text(encoding="utf-8-sig")
        self.assertIn("function Resolve-JavaKeytool", source)
        self.assertIn("Get-Command -Name $name -CommandType Application", source)
        self.assertIn("[string]::IsNullOrWhiteSpace($root)", source)
        self.assertNotIn("Join-Path $env:JAVA_HOME", source)
        self.assertIsNone(re.search(r"(?i)\$home\b", source), "Do not assign/read PowerShell read-only $HOME via $home")
        self.assertIn("$jdkInstallDirectory", source)
        self.assertIn("throw 'Java JDK keytool.exe not found", source)
        wrapper = WRAPPER.read_text(encoding="utf-8-sig")
        self.assertIn("b7302c34b18f705bab5c374935572f250ce9e221ba400dfcc522ba7fa76186ec", wrapper)
        self.assertIn("d3f7f6c1af84690a444887d0b5dbeb85e3b4b4679cb31abcb7a47ae431472ac7", wrapper)
        self.assertNotIn("fe32e0b9010449fd8ea747521d215ff052b59a3f4dae8cdd263698ba755250f6", wrapper)

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
