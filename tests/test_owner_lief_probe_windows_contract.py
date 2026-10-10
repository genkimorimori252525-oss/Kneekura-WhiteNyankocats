"""Offline owner wheel contract checks; no source ZIP or player SAVE."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "base_mod" / "run_owner_lief_probe.ps1"
WORKFLOW = ROOT / ".github" / "workflows" / "build-kneekura-shim.yml"

class WindowsPrivateLiefKitContractTests(unittest.TestCase):
    def test_script_never_installs_game_or_contacts_network(self):
        code = SCRIPT.read_text(encoding="utf-8")
        for required in (
            "[Parameter(Mandatory = $true)][string]$OwnerExport",
            "[Parameter(Mandatory = $true)][string]$WheelDirectory",
            "lief-0.17.6-cp312-cp312-win_amd64.whl",
            "wheel-receipt.json",
            "Get-FileHash -LiteralPath $wheel -Algorithm SHA256",
            "-3.12 -m venv",
            "--no-index --no-deps --no-cache-dir",
            "tools.base_mod.original_scene_native_image_gate",
            "PASS_PRIVATE_TEMP_NATIVE_LIEF_ROUNDTRIP_ONLY",
            "original_text_preserved_after_LIEF_rewrite",
            "Refusing to overwrite",
        ):
            self.assertIn(required, code)
        for forbidden in ("adb install", "adb uninstall", "Remove-Item",
                          "Invoke-WebRequest", "curl.exe", "am start",
                          "apksigner sign"):
            self.assertNotIn(forbidden, code)
        self.assertIn('Join-Path $repo "private"', code)
        self.assertIn("$result.ready_to_sign_or_install -ne $false", code)

    def test_windows_ci_wheel_is_public_and_verified_offline(self):
        code = WORKFLOW.read_text(encoding="utf-8")
        for required in (
            "owner-lief-probe-wheel-windows:",
            "runs-on: windows-latest",
            "lief==0.17.6",
            "lief-0.17.6-cp312-cp312-win_amd64.whl",
            "pip download --only-binary=:all: --no-deps",
            "--no-index --no-deps --no-cache-dir",
            "original_game_apk_or_save_downloaded = $false",
            "ready_to_install_game = $false",
            "tests.test_owner_lief_probe_windows_contract",
            "kneekura-owner-LIEF-0.17.6-win312-OFFLINE-WHEEL-ONLY",
        ):
            self.assertIn(required, code)

if __name__ == "__main__":
    unittest.main()
