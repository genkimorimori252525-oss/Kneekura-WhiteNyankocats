"""SYNTHETIC ONLY: exact package, positive approval and safe six-split update.

No owner device, APK, keystore, account, SAVE or actual ADB command is used.
The FakeRunner verifies every external process invocation and never executes it.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import unittest
from zipfile import ZipFile

from tests.test_original_device_update_preflight import (
    FakeRunner,
    OriginalResearchDeviceSignerGateTests,
)
from tools.base_mod import preflight_original_device_update as gate
from tools.base_mod import update_original_isolated_research as updater


class UpdateFakeRunner(FakeRunner):
    def __init__(self, *args, live_process=False, install_timeout=False,
                 candidate_mutation=None, install_output="Success\\n",
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.live_process = live_process
        self.install_timeout = install_timeout
        self.candidate_mutation = candidate_mutation
        self.install_output = install_output
        self.installs = []
        self.did_mutate = False

    def __call__(self, command, **kwargs):
        args = command[1:]
        if args == ["-s", "FAKE-DEVICE", "shell", "pidof", gate.PACKAGE]:
            self.calls.append(args)
            return subprocess.CompletedProcess(
                command, 0 if self.live_process else 1,
                "7654" if self.live_process else "", "",
            )
        if args[:4] == ["-s", "FAKE-DEVICE", "install-multiple", "--no-streaming"]:
            self.calls.append(args)
            self.installs.append(args)
            if (args[4] != "-r" or len(args) != 5+len(gate.SPLITS)
                or [Path(x).name for x in args[5:]] != list(gate.SPLITS)):
                raise AssertionError("Only exact six-split replace allowed")
            if self.install_timeout:
                raise subprocess.TimeoutExpired(command, 180)
            return subprocess.CompletedProcess(command, 0, self.install_output, "")
        # Try to substitute a candidate split *after* the signer preflight
        # had started. Installation must detect its SHA changed and abort.
        if (self.candidate_mutation is not None and not self.did_mutate
            and args[:2] == ["verify", "--print-certs"]
            and args[-1].endswith("split_config.ja.apk")):
            self.did_mutate = True
            Path(self.candidate_mutation).write_bytes(
                Path(self.candidate_mutation).read_bytes() + b"changed-after-check"
            )
        return super().__call__(command, **kwargs)


class ApprovedOriginalResearchUpdateTests(unittest.TestCase):
    def setUp(self):
        self.fixtures = OriginalResearchDeviceSignerGateTests("runTest")
        self.fixtures.setUp()
        self.addCleanup(self.fixtures.doCleanups)
        self.runner = UpdateFakeRunner()

    def execute(self, approval=None, runner=None):
        return updater.run_user_approved_update(
            repo=self.fixtures.repo, candidate=self.fixtures.candidate,
            adb=self.fixtures.adb, apksigner=self.fixtures.signer,
            explicit_approval=(updater._APPROVAL if approval is None else approval),
            runner=runner or self.runner,
        )

    def test_default_no_owner_approval_never_touches_adb(self):
        with self.assertRaisesRegex(updater.ResearchUpdateBlocked, "explicit"):
            self.execute(approval="")
        self.assertEqual(self.runner.calls, [])

    def test_install_only_exact_isolated_six_split_and_cert_afterwards(self):
        receipt, destination = self.execute()
        self.assertEqual(len(self.runner.installs), 1)
        self.assertEqual(receipt["package"], "jp.kn.local.battlecats")
        self.assertEqual(receipt["updated_splits"], 6)
        self.assertTrue(receipt["post_install_actual_research_signature_match"])
        self.assertTrue(receipt["original_gameplay_black_screen_fix_unverified"])
        self.assertTrue(receipt["android_data_preservation_not_dynamically_verified"])
        self.assertNotIn("FAKE-DEVICE", destination.read_text())
        self.assertNotIn("a"*64, destination.read_text())
        self.assertFalse(list((self.fixtures.repo/"private").glob(
            "approved-original-update-proofs-*")))
        for call in self.runner.calls:
            args = " ".join(call)
            self.assertNotIn("jp.co.ponos.battlecats", args)
            self.assertNotIn("uninstall", args)
            self.assertNotIn(" pm clear ", args)
            self.assertNotIn(" force-stop ", args)
            self.assertNotIn(" -d ", args)

    def test_real_adb_progress_then_final_success_is_accepted_but_not_playable(self):
        runner = UpdateFakeRunner(install_output="Performing Push Install\\nSuccess\\n")
        receipt, _ = self.execute(runner=runner)
        self.assertEqual(receipt["status"],
                         "SIX_SPLIT_UPDATE_CONFIRMED_SIGNER_ONLY_NOT_GAMEPLAY")
        self.assertEqual(len(runner.installs), 1)
        self.assertTrue(receipt["original_gameplay_black_screen_fix_unverified"])

    def test_trailing_installer_failure_is_never_treated_as_success(self):
        runner = UpdateFakeRunner(install_output="Success\\nFailure [INSTALL_FAILED]\\n")
        with self.assertRaisesRegex(updater.ResearchUpdateBlocked,
                                    "did not finish with exact Success"):
            self.execute(runner=runner)
        self.assertEqual(len(runner.installs), 1)
        self.assertFalse(list((self.fixtures.repo/"private").glob(
            "isolated-sixsplit-update-*.json")))

    def test_active_research_process_blocks_without_killing_it(self):
        runner = UpdateFakeRunner(live_process=True)
        with self.assertRaisesRegex(updater.ResearchUpdateBlocked, "currently running"):
            self.execute(runner=runner)
        self.assertEqual(runner.installs, [])

    def test_installed_signature_mismatch_blocks_without_installer(self):
        runner = UpdateFakeRunner(installed_cert=FakeRunner.OTHER)
        with self.assertRaises(gate.PreflightBlocked):
            self.execute(runner=runner)
        self.assertEqual(runner.installs, [])

    def test_changed_candidate_bytes_between_check_and_install_blocked(self):
        target = self.fixtures.candidate / "split_config.ja.apk"
        runner = UpdateFakeRunner(candidate_mutation=target)
        with self.assertRaisesRegex(updater.ResearchUpdateBlocked,
                                    "signed APK content changed"):
            self.execute(runner=runner)
        self.assertEqual(runner.installs, [])

    def test_ambiguous_install_timeout_never_retries_or_clears_data(self):
        runner = UpdateFakeRunner(install_timeout=True)
        with self.assertRaisesRegex(updater.ResearchUpdateBlocked,
                                    "outcome unknown"):
            self.execute(runner=runner)
        self.assertEqual(len(runner.installs), 1)
        self.assertFalse(list((self.fixtures.repo/"private").glob(
            "approved-original-update-proofs-*")))

    def test_postinstall_installed_certificate_mismatch_blocks_receipt(self):
        class PostInstallSignerSwitch(UpdateFakeRunner):
            def __call__(self, command, **kwargs):
                args = command[1:]
                if args[:4] == ["-s", "FAKE-DEVICE", "install-multiple", "--no-streaming"]:
                    result = super().__call__(command, **kwargs)
                    self.installed_cert = FakeRunner.OTHER
                    return result
                return super().__call__(command, **kwargs)

        runner = PostInstallSignerSwitch()
        with self.assertRaisesRegex(updater.ResearchUpdateBlocked,
                                    "post-update installed research signature mismatch"):
            self.execute(runner=runner)
        self.assertEqual(len(runner.installs), 1)
        self.assertFalse(list((self.fixtures.repo/"private").glob(
            "isolated-sixsplit-update-*.json")))


if __name__ == "__main__":
    unittest.main()
