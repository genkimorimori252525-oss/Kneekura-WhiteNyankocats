"""Owner-private scene97 observer handoff safety checks (source only).

Never uses a private signing keystore, Android ADB, apk installation, SAVE,
publisher game, network credentials or original proprietary source bytes.
PowerShell 5.1 is parsed when available, but no .ps1 is executed here.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
OWNER_READY = ROOT / "tools/base_mod/OWNER-READY-TO-SIGN.ps1"
ONE_SHOT = ROOT / "tools/base_mod/OWNER-OFFLINE-615-ONE-SHOT.ps1"
NATIVE_CI = ROOT / ".github/workflows/build-kneekura-shim.yml"


class Scene97ResearchOnlyOwnerSigningGateTests(unittest.TestCase):
    def test_source_flags_do_not_allow_implicit_new_shim_or_two_signers(self):
        ready = OWNER_READY.read_text(encoding="utf-8-sig")
        one = ONE_SHOT.read_text(encoding="utf-8-sig")
        self.assertEqual(ready.count("param("), 1)
        self.assertEqual(one.count("param("), 1)
        self.assertEqual(one.count("Push-Location -LiteralPath $repo"), 1)
        self.assertEqual(one.count("} finally {"), 1)
        self.assertEqual(one.count("OWNER_OFFLINE_ONE_SHOT_READONLY_PREFLIGHT_PASS"), 1)
        self.assertEqual(one.count("RESEARCH_ONLY_SIGNED_UPDATED_AND_SINGLE_BOOT_OBSERVED_CHECK_BASE_SEPARATELY"), 1)
        self.assertEqual(one.count(" -EnableOfflineServerImport @signerResearchArgs"), 2)
        self.assertEqual(one.count("$signerResearchArgs = @()"), 1)
        self.assertIn("[switch]$RequireScene97ResolverWitness", one)
        self.assertIn("[switch]$RequireScene97ResolverWitness", ready)
        self.assertIn("[string]$ResearchShimFolder", one)
        self.assertIn("[string]$ResearchShimFolder", ready)
        self.assertIn("SCENE97_NEW_NATIVE_ARTIFACT_FOLDER_REQUIRED_NO_DEVICE_OR_KEY_ACTION", one)
        self.assertIn("EXPLICIT_SCENE97_NATIVE_FOLDER_WITHOUT_MODE_NO_DEVICE_OR_KEY_ACTION", one)
        self.assertLess(
            one.index("SCENE97_NEW_NATIVE_ARTIFACT_FOLDER_REQUIRED_NO_DEVICE_OR_KEY_ACTION"),
            one.index("$devices = @(")
        )
        self.assertIn("SCENE97_OBSERVER_RECEIPT_NOT_ATTESTED_NO_BUILD_OR_INSTALL", ready)
        self.assertIn("scene97_resolver_histogram_compiled -ne $true", ready)
        self.assertIn("$nativeProof.original_save_writer_enabled -ne $false", ready)
        self.assertIn("EXPLICIT_SCENE97_SHIM_MUST_BE_INSIDE_PRIVATE_NO_ACTION", ready)
        self.assertIn("EXPLICIT_SCENE97_SHIM_SYMLINK_NO_ACTION", ready)
        self.assertIn("merge-base --is-ancestor", ready)
        self.assertLess(ready.index("SCENE97_OBSERVER_RECEIPT_NOT_ATTESTED_NO_BUILD_OR_INSTALL"),
                        ready.index("$keystore = Require-One"))
        self.assertIn("-PassiveShimSo $native", ready)
        self.assertIn("-PassiveShimReceipt $passiveShimReceipt", ready)
        self.assertEqual(one.count(" -ApproveUpdateOfIsolatedResearchApp"), 1)
        executable_lines = "\n".join(
            line for line in one.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        self.assertNotIn("pm clear", executable_lines)
        self.assertNotIn("uninstall", executable_lines)
        self.assertNotIn("setAirplaneMode", executable_lines)

    def test_manual_owner_screen_category_is_only_in_local_metadata_audit(self):
        one = ONE_SHOT.read_text(encoding="utf-8-sig")
        self.assertIn("[switch]$OwnerObservedInternetUnavailable", one)
        self.assertIn("[switch]$OwnerReported615MBRequestPassed", one)
        self.assertIn("--owner-observed-final-screen", one)
        self.assertIn("'internet-unavailable'", one)
        self.assertIn("--owner-reported-615mb-request-passed", one)
        self.assertLess(
            one.index("RESEARCH_ONLY_SIGNED_UPDATED_AND_SINGLE_BOOT_OBSERVED_CHECK_BASE_SEPARATELY"),
            len(one),
        )
        self.assertLess(
            one.index("ONE_RESEARCH_UPDATE_FAILED_DO_NOT_RETRY"),
            one.index("$auditArgs = @("),
        )
        self.assertNotIn("SAVE_DATA", one)
        self.assertNotIn("SECRET", one)
        self.assertEqual(one.count("& py @auditArgs"), 1)

    def test_public_arm64_receipt_pins_new_observer_to_exact_opt_in(self):
        workflow = NATIVE_CI.read_text(encoding="utf-8")
        self.assertIn('"scene97_resolver_histogram_compiled": True', workflow)
        self.assertIn("original-native-scene97-resolver-v1 missing=%u zero=%u one=%u other=%u", workflow)
        self.assertIn("original_save_writer_enabled", workflow)
        self.assertIn("KNEEKURA_RESEARCH_SCENE_WITNESS=ON", workflow)
        self.assertIn("KNEEKURA_RESEARCH_SCENE_WITNESS", workflow)
        source = (ROOT / "native/kneekura-shim/src/kneekura_original_scene_witness.c").read_text()
        self.assertIn("observe_original_scene97_resolver_histogram(context, scene);", source)
        self.assertIn("scene != 97u", source)

    def test_owner_powershell_51_parses_only_without_execution(self):
        executable = shutil.which("powershell.exe") or shutil.which("powershell")
        if not executable:
            self.skipTest("Windows PowerShell 5.1 not present on this CI OS")
        selected = [OWNER_READY, ONE_SHOT]
        quoted = ",".join("'" + str(p).replace("'", "''") + "'" for p in selected)
        command = (
            "$ErrorActionPreference='Stop';"
            "$filePaths=@(" + quoted + ");"
            "foreach($filePath in $filePaths){"
            "$tokens=$null;$parseErrors=$null;"
            "[void][System.Management.Automation.Language.Parser]::ParseFile("
            "$filePath,[ref]$tokens,[ref]$parseErrors);"
            "if(@($parseErrors).Count -ne 0){"
            "Write-Output ('PS51_PARSE_FAIL '+[IO.Path]::GetFileName($filePath));"
            "exit 3"
            "}"
            "};"
            "Write-Output 'SCENE97_OWNER_PS51_PARSE_PASS'"
        )
        run = subprocess.run(
            [executable, "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True, text=True, errors="replace", timeout=30
        )
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("SCENE97_OWNER_PS51_PARSE_PASS", run.stdout)


if __name__ == "__main__":
    unittest.main()
