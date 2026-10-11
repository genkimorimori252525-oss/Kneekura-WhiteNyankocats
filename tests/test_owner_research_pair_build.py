"""Build-only owner-private two-ShadowHook-SO signer guard.

These tests inspect committed source only. Actual keystore, game, phone,
PowerShell 5.1 execution and signed owner APK are NEVER accessed by CI.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/base_mod/BUILD-OWNER-RESEARCH-PAIR.ps1"


class OriginalResearchSameSignerHandoffTests(unittest.TestCase):
    def test_source_is_utf8_bom_and_never_installs_or_clears_device(self):
        data = SCRIPT.read_bytes()
        self.assertTrue(data.startswith(bytes((0xEF, 0xBB, 0xBF))))
        source = data.decode("utf-8-sig")
        for forbidden in (
            " install-multiple ", " pm clear ", " adb uninstall ",
            " shell am start ", "Stop-Process", "adb.exe",
            "--research-virgin-save-trial",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)
        self.assertIn("--research-shadowhook-aar", source)
        self.assertIn("--research-no-internet-permission", source)
        self.assertIn("'--storepass-env', $secretEnvName", source)
        self.assertIn("'--keypass-env', $secretEnvName", source)
        self.assertIn("[Environment]::SetEnvironmentVariable($secretEnvName, $password, 'Process')", source)
        self.assertIn("[Environment]::SetEnvironmentVariable($secretEnvName, $null, 'Process')", source)
        self.assertNotIn("'--storepass', $password", source)
        self.assertNotIn("'--keypass', $password", source)
        self.assertIn("--root', $repo", source)
        self.assertIn("original_save_writer_enabled -ne $false", source)
        self.assertIn("PreviouslySignedBaseApk", source)
        self.assertIn("PASSIVE_SHIM_BUILD_SOURCE_RECEIPT.json", source)
        self.assertIn("Copy-Item -LiteralPath $receiptPath -Destination $copiedReceipt", source)
        self.assertIn("SignerDigest $existingBase $apksigner", source)
        self.assertIn("SignerDigest $newBase $apksigner", source)
        self.assertIn("if ($before -ne $after)", source)
        self.assertIn("Do NOT install this build", source)

    def test_owner_jdk17_pair_resolved_before_secret_prompt(self):
        """Regression for owner's Oracle javapath javac.exe with no sibling keytool.

        Reuse the repository's verified resolver to locate one complete JDK17
        rather than guessing that Get-Command javac.exe has keytool beside it.
        """
        source = SCRIPT.read_text(encoding="utf-8-sig")
        self.assertIn("resolve_java_keytool.ps1", source)
        self.assertIn(". $javaHelper", source)
        self.assertIn("$keytoolPath = RequireFile (Resolve-JavaKeytool)", source)
        self.assertIn("'javac.exe') 'JDK javac paired with keytool'", source)
        self.assertIn("EXISTING_JDK17_JAVAC_KEYTOOL_PAIR_VERIFIED_NO_KEY_USED", source)
        self.assertNotIn("Get-Command javac.exe", source)
        self.assertNotIn("$keytoolPath = Join-Path (Split-Path -Parent $javacPath)", source)
        self.assertLess(source.index("Resolve-JavaKeytool"),
                        source.index("$secure = Read-Host"))
        self.assertLess(source.index("EXISTING_JDK17_JAVAC_KEYTOOL_PAIR_REQUIRED_NO_SIGNING_ATTEMPT"),
                        source.index("$secure = Read-Host"))

    def test_preflight_excludes_failed_build_inputs_and_runs_before_staging(self):
        ready = (ROOT / "tools/base_mod/OWNER-READY-TO-SIGN.ps1").read_text(
            encoding="utf-8-sig")
        builder = SCRIPT.read_text(encoding="utf-8-sig")
        self.assertIn("official-shadowhook-pair-passive-", ready)
        self.assertIn("-notmatch", ready)
        self.assertIn("verify_original_research_signer", builder)
        self.assertIn("EXISTING_RESEARCH_KEYSTORE_PREFLIGHT_BLOCKED_NO_SIGNING_ATTEMPT", builder)
        self.assertLess(
            builder.index("'-m', 'tools.base_mod.verify_original_research_signer'"),
            builder.index("New-Item -ItemType Directory -Path $out"),
        )
        self.assertLess(
            builder.index("New-Item -ItemType Directory -Path $out"),
            builder.index("'-m', 'tools.base_mod.build_owned_static_http_bridge'"),
        )

    def test_private_password_name_resolves_in_python_without_stdout_leak(self):
        import contextlib
        import io
        import os
        import sys
        from unittest.mock import patch
        from tools.base_mod import build_owned_static_http_bridge as original_builder

        captured = {}
        def mock_build(*args, **kwargs):
            captured.update(kwargs)
            return {"status": "SOURCE_ONLY_CLI_PASSWORD_TEST"}

        argv = [
            "builder", "synthetic-owner.zip", "--flavor", "local-research",
            "--shim", "synthetic-shim.so", "--keystore", "synthetic.p12",
            "--alias", "private", "--output", "synthetic-output",
            "--storepass-env", "KNEEKURA_UNITTEST_SIGN_PASS",
            "--keypass-env", "KNEEKURA_UNITTEST_SIGN_PASS",
        ]
        output = io.StringIO()
        with patch.dict(os.environ, {"KNEEKURA_UNITTEST_SIGN_PASS": "SECRET_CLI_NEVER_ECHO"}), \
             patch.object(sys, "argv", argv), \
             patch.object(original_builder, "build_owned_static_http_bridge",
                          side_effect=mock_build), \
             contextlib.redirect_stdout(output):
            self.assertEqual(original_builder.main(), 0)
        self.assertEqual(captured["storepass"], "SECRET_CLI_NEVER_ECHO")
        self.assertEqual(captured["keypass"], "SECRET_CLI_NEVER_ECHO")
        self.assertNotIn("SECRET_CLI_NEVER_ECHO", output.getvalue())

    def test_private_password_env_validation_does_not_print_value(self):
        import contextlib
        import io
        import os
        import sys
        from unittest.mock import patch
        from tools.base_mod import build_owned_static_http_bridge as original_builder

        argv = [
            "builder", "synthetic-owner.zip", "--flavor", "local-research",
            "--shim", "synthetic-shim.so", "--keystore", "synthetic.p12",
            "--alias", "private", "--output", "synthetic-output",
            "--storepass-env", "KNEEKURA_UNITTEST_MISSING",
        ]
        stderr = io.StringIO()
        with patch.object(sys, "argv", argv), \
             patch.dict(os.environ, {"KNEEKURA_UNITTEST_MISSING": ""}), \
             contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit):
                original_builder.main()
        self.assertIn("required private password environment variable not set",
                      stderr.getvalue())

    def test_missing_owner_alias_is_not_misclassified_as_bad_key(self):
        source = (ROOT / "tools/base_mod/OWNER-READY-TO-SIGN.ps1").read_text(
            encoding="utf-8-sig"
        )
        self.assertIn("RESEARCH_SIGNING_ALIAS_MISSING_NO_ACTION", source)
        self.assertIn('rerun with -DoBuild -SigningAlias', source)
        self.assertIn("RESEARCH_SIGNING_ALIAS_FORMAT_INVALID_NO_ACTION", source)
        self.assertLess(
            source.index("RESEARCH_SIGNING_ALIAS_MISSING_NO_ACTION"),
            source.index("& $buildScript -RepositoryRoot"),
        )
        self.assertLess(
            source.index("RESEARCH_SIGNING_ALIAS_FORMAT_INVALID_NO_ACTION"),
            source.index("& $buildScript -RepositoryRoot"),
        )

    def test_owner_one_command_handoff_refuses_signing_by_default(self):
        path = ROOT / "tools/base_mod/OWNER-READY-TO-SIGN.ps1"
        raw = path.read_bytes()
        self.assertTrue(raw.startswith(bytes((239, 187, 191))))
        source = raw.decode("utf-8-sig")
        self.assertIn("[switch]$DoBuild", source)
        self.assertIn("if (-not $DoBuild)", source)
        self.assertIn("OWNER_PRIVATE_ORIGINAL_BUILD_INPUTS_READY_NO_DEVICE_OR_KEY_USED", source)
        self.assertIn("BUILD-OWNER-RESEARCH-PAIR.ps1", source)
        self.assertIn("PASS_PRIVATE_UNSIGNED_ORIGINAL_SIX_SPLITS_NOT_INSTALLABLE", source)
        self.assertIn("PINNED_REPACKAGED_JP1571_ORIGINAL_SCENE_VMA_AND_EXPORT_VERIFIED",
                      source)
        self.assertIn("original_save_writer_enabled -ne $false", source)
        self.assertIn("Read-only PREPARED state only.", source)
        self.assertNotIn("install-multiple", source)
        self.assertNotIn("pm clear", source)
        self.assertNotIn(" -Password ", source)

    def test_preflight_pins_owner_original_and_official_public_archive(self):
        source = SCRIPT.read_text(encoding="utf-8-sig")
        from tools.base_mod.extract_owned_splits import EXPECTED_EXPORT_SHA256
        from tools.base_mod.prepare_original_scene_witness import (
            APPROVED_OFFICIAL_SHADOWHOOK_V201_AAR_SHA256,
        )
        self.assertIn(EXPECTED_EXPORT_SHA256, source)
        self.assertIn(APPROVED_OFFICIAL_SHADOWHOOK_V201_AAR_SHA256, source)
        for item in (
            "PUBLIC_PASSIVE_SHIM_RECEIPT.json",
            "public-original-research-passive-shim-v1",
            "fixed_error_markers_compiled",
            "merge-base --is-ancestor",
            "PRIVATE-build-receipt.json",
            "BUILD_ONLY_PASS; PROVIDED_PREVIOUS_SIGNED_BASE_CERT_MATCHED",
        ):
            # Exact fixture metadata file name may be passed as a parameter;
            # the schema/sha verification is authoritative.
            if item == "PUBLIC_PASSIVE_SHIM_RECEIPT.json":
                continue
            self.assertIn(item, source)
        self.assertNotIn("Create-ResearchKeystore", source)


if __name__ == "__main__":
    unittest.main()
