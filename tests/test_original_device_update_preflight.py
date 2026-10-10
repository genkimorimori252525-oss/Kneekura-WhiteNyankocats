"""Synthetic read-only original-game research signer gate, no real APK/ADB/SAVE."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from tools.base_mod import preflight_original_device_update as gate


class FakeRunner:
    CERT = "a" * 64
    OTHER = "b" * 64

    def __init__(self, *, device_state="device", installed_cert=None,
                 candidate_certs=None, no_pull=False):
        self.device_state = device_state
        self.installed_cert = installed_cert or self.CERT
        self.candidate_certs = candidate_certs or {s:self.CERT for s in gate.SPLITS}
        self.no_pull = no_pull
        self.calls = []

    def __call__(self, command, **kwargs):
        args = command[1:]
        self.calls.append(args)
        if args == ["devices"]:
            lines = "List of devices attached\n"
            if self.device_state == "two":
                lines += "FAKE-DEVICE\tdevice\nOTHER-FAKE\tdevice\n"
            elif self.device_state != "none":
                lines += "FAKE-DEVICE\t" + self.device_state + "\n"
            return subprocess.CompletedProcess(command, 0, lines, "")
        if args == ["-s", "FAKE-DEVICE", "shell", "pm", "path", gate.PACKAGE]:
            base = "/data/app/~~TEST+/jp.kn.local.battlecats-fixture==/"
            text = "\n".join("package:" + base + name for name in gate.SPLITS)
            return subprocess.CompletedProcess(command, 0, text, "")
        if len(args) == 5 and args[:3] == ["-s", "FAKE-DEVICE", "pull"]:
            assert args[3].endswith("/base.apk")
            if not self.no_pull:
                Path(args[4]).write_bytes(b"FAKE_INSTALLED_APK_NEVER_SHARED"*60)
            return subprocess.CompletedProcess(command, 0, "1 file pulled", "")
        if args[:2] == ["verify", "--print-certs"] and len(args) == 3:
            file = Path(args[2])
            digest = (self.installed_cert if file.name == "installed-base.apk"
                      else self.candidate_certs[file.name])
            return subprocess.CompletedProcess(command, 0,
                "Signer #1 certificate SHA-256 digest: " + digest + "\n", "")
        raise AssertionError("Unexpected ADB or signer action; install/clear prohibited")


class OriginalResearchDeviceSignerGateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        (self.repo / "private").mkdir()
        self.candidate = (self.repo / "private" / "trial" /
                          "local-research-static-http-signed-splits")
        self.candidate.mkdir(parents=True)
        self.adb = self.repo / "fake-adb"
        self.signer = self.repo / "fake-signer"
        self.adb.write_text("FAKE")
        self.signer.write_text("FAKE")
        self.main = b"FAKE_REVIEWED_MAIN"
        self.companion = b"FAKE_REVIEWED_NOTHING"
        for name, value in (
            ("MAIN_SHA", hashlib.sha256(self.main).hexdigest()),
            ("COMPANION_SHA", hashlib.sha256(self.companion).hexdigest()),
        ):
            p = patch.object(gate, name, value)
            p.start()
            self.addCleanup(p.stop)
        self.make_signed_synthetic_six()

    def make_signed_synthetic_six(self, *, no_helper=False,
                                   writer=False, internet=False, bad_hash=False):
        parity = {
            "mode": "static-java-http-bridge",
            "package": gate.PACKAGE,
            "flavor": "local-research",
            "native_scene_hook_research_only": True,
            "research_no_internet_manifest": True,
            "final_INTERNET_permission": internet,
            "reviewed_external_hook_binary_hash_pinned": gate.MAIN_SHA,
            "reviewed_official_shadowhook_companion_hash_pinned": gate.COMPANION_SHA,
            "repackaged_original_native_scene_layout": {
                "all_original_executable_text_bytes_unchanged_static": True,
            },
        }
        (self.candidate / "parity-report.json").write_text(json.dumps(parity))
        for name in gate.SPLITS:
            with ZipFile(self.candidate / name, "w") as z:
                z.writestr("AndroidManifest.xml", b"SYNTHETIC_ONLY"*80)
                z.writestr("assets/fixture.bin", b"NO_GAME_ASSETS"*60)
                if name == "split_config.arm64_v8a.apk":
                    z.writestr(gate.MAIN, self.main)
                    if not no_helper:
                        z.writestr(gate.COMPANION, (
                            self.companion if not bad_hash else b"BAD_AUX"))
                    z.writestr(gate.SHIM, b"PASSIVE" + b"\n".join(gate.MARKERS)
                               + (b"kneekura-original-virgin-save-trial-v1"
                                  if writer else b""))

    def invoke(self, runner=None, **kwargs):
        return gate.preflight(
            repo=self.repo, candidate=self.candidate, adb=self.adb,
            apksigner=self.signer, runner=runner or FakeRunner(), **kwargs,
        )

    def test_actual_installed_signer_checked_against_all_six_and_raw_apk_erased(self):
        runner = FakeRunner()
        receipt, destination = self.invoke(runner)
        self.assertTrue(receipt["candidate_signer_matches_installed_research_base"])
        self.assertEqual(receipt["installed_research_splits"], 6)
        self.assertFalse(receipt["device_install_launch_stop_or_clear_executed"])
        self.assertFalse(receipt["actual_game_boot_or_Level60_passed"])
        self.assertEqual(sum(x[:1] == ["verify"] for x in runner.calls), 7)
        self.assertEqual(sum("pull" in x for x in runner.calls), 1)
        self.assertNotIn("FAKE-DEVICE", destination.read_text())
        self.assertNotIn(runner.CERT, destination.read_text())
        self.assertNotIn("/data/app", destination.read_text())
        self.assertFalse(list((self.repo / "private").glob("read-only-installed-research-*")))
        for args in runner.calls:
            self.assertNotIn("install", args)
            self.assertNotIn("clear", args)
            self.assertNotIn("uninstall", args)
            self.assertNotIn("jp.co.ponos.battlecats", args)

    def test_installed_research_cert_mismatch_blocks_and_cleans_copy(self):
        with self.assertRaisesRegex(gate.PreflightBlocked, "DOES NOT match"):
            self.invoke(FakeRunner(installed_cert=FakeRunner.OTHER))
        self.assertFalse(list((self.repo / "private").glob("read-only-installed-research-*")))
        self.assertFalse(list((self.repo / "private").glob("device-research-signer-*.json")))

    def test_six_candidate_signers_must_all_be_identical(self):
        certs = {x:FakeRunner.CERT for x in gate.SPLITS}
        certs["split_config.ja.apk"] = FakeRunner.OTHER
        runner = FakeRunner(candidate_certs=certs)
        with self.assertRaisesRegex(gate.PreflightBlocked, "candidate split signer mismatch"):
            self.invoke(runner)
        self.assertFalse(any("pull" in args for args in runner.calls))

    def test_unsafe_native_and_bad_offline_parity_refuse_before_adb(self):
        for variant in (
            {"no_helper":True}, {"bad_hash":True},
            {"writer":True}, {"internet":True},
        ):
            with self.subTest(variant=variant):
                self.make_signed_synthetic_six(**variant)
                runner = FakeRunner()
                with self.assertRaises(gate.PreflightBlocked):
                    self.invoke(runner)
                self.assertEqual(runner.calls, [])
        self.make_signed_synthetic_six()

    def test_offline_unauthorized_two_and_missing_pull_fail_closed(self):
        for state in ("offline", "unauthorized", "two", "none"):
            with self.subTest(state=state), self.assertRaises(gate.PreflightBlocked):
                self.invoke(FakeRunner(device_state=state))
        with self.assertRaises(gate.PreflightBlocked):
            self.invoke(FakeRunner(no_pull=True))
        self.assertFalse(list((self.repo / "private").glob("read-only-installed-research-*")))

    def test_pm_path_rejects_vendor_app_duplicate_and_path_escape(self):
        path = "/data/app/~~TEST+/jp.kn.local.battlecats-test==/"
        valid = "\n".join("package:" + path + name for name in gate.SPLITS)
        self.assertEqual(set(gate._paths(valid)), set(gate.SPLITS))
        for unsafe in (
            valid.replace("jp.kn.local.battlecats", "jp.co.ponos.battlecats"),
            valid.replace("base.apk", "../base.apk"),
            valid.replace("split_InstallPack.apk", "base.apk"),
            valid + "\npackage:/data/app/extra.apk",
            valid.replace("/base.apk", ";echo/../../base.apk"),
        ):
            with self.subTest(unsafe=unsafe[:70]), self.assertRaises(gate.PreflightBlocked):
                gate._paths(unsafe)

    def test_ambiguous_signer_and_foreign_device_are_refused(self):
        with self.assertRaises(gate.PreflightBlocked):
            gate._cert("Signer #1 certificate SHA-256 digest: " + "a"*64
                       + "\nSigner #2 certificate SHA-256 digest: " + "b"*64)
        for value in ("List of devices attached\nFAKE-DEV\toffline\n",
                      "List of devices attached\n"):
            with self.assertRaises(gate.PreflightBlocked):
                gate._device(value)

    def test_private_only_receipt_never_overwrites(self):
        with self.assertRaises(gate.PreflightBlocked):
            self.invoke(output=self.repo / "not-private.json")
        receipt = self.repo / "private" / "existing.json"
        receipt.write_text("OWNER_EXISTING_DATA")
        with self.assertRaises(gate.PreflightBlocked):
            self.invoke(output=receipt)
        self.assertEqual(receipt.read_text(), "OWNER_EXISTING_DATA")


if __name__ == "__main__":
    unittest.main()
