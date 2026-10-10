"""Synthetic read-only ADB first-boot observations; no device or SAVE required."""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from tools.base_mod import collect_original_local_first_boot as obs

DUMPSYS = (
    "Packages:\n"
    "  Package [jp.kn.local.battlecats] (abc):\n"
    "    requested permissions:\n"
    "      android.permission.ACCESS_NETWORK_STATE\n"
)
PM_PATHS = (
    "package:/data/app/jp.kn.local.battlecats/base.apk\n"
    "package:/data/app/jp.kn.local.battlecats/split_config.arm64_v8a.apk\n"
)
PID = 2345


def safe_thread(pid: int, message: str, *, tag: str = obs.LOG_TAG) -> str:
    return f"10-10 18:40:01.012  {pid:>5}  2500 I {tag}: {message}\n"


SAMPLE = "".join([
    safe_thread(PID, "original-save-presence-v1 SAVE_DATA=absent "
                     "SAVE_DATA4=absent SAVE_DATA8=absent"),
    safe_thread(PID, "original-save-event-observer-v1 active"),
    safe_thread(PID, "original-download-tsv-loose-v1 present=0 absent=35 unsafe=0"),
    safe_thread(PID, "original-local-fresh-package-root active"),
    safe_thread(PID, "original-local-denied-http-v1"),
    safe_thread(PID, "original-save-presence-v1 SAVE_DATA=present:2048 "
                     "SAVE_DATA4=absent SAVE_DATA8=absent"),
])


class OriginalNativeLocalFirstBootMetadataTests(TestCase):
    def test_allowed_original_research_process_only_and_no_save_leak(self):
        signal = obs.sanitized_original_activity_events(SAMPLE, pid=PID)
        self.assertTrue(signal["root_probe_witnessed"])
        self.assertTrue(signal["file_observer_witnessed"])
        self.assertTrue(signal["SAVE_absence_then_presence_observed_in_this_PID"])
        self.assertEqual(
            signal["last_original_SAVE_metadata"]["SAVE_DATA"],
            {"status": "present", "size_bytes": 2048},
        )
        self.assertEqual(signal["last_loose_35_TSV_presence_metadata"],
                         {"loose_present": 0, "loose_absent": 35, "unsafe": 0})
        self.assertEqual(signal["denied_HTTP_calls_observed"], 1)
        self.assertFalse(signal["original_SAVE_content_read"])
        self.assertFalse(signal["raw_logcat_lines_retained"])

    def test_unknown_logs_foreign_pid_urls_and_account_data_are_discarded(self):
        raw = (
            SAMPLE
            + safe_thread(2346, "original-save-presence-v1 SAVE_DATA=present:999999 "
                                "SAVE_DATA4=present:123 SAVE_DATA8=present:123")
            + safe_thread(PID, "request GET https://not_logged/account?token=TOP_SECRET")
            + safe_thread(PID, "SAVE_CONTENT=VERY_PRIVATE_PLAYER_SAVE")
            + safe_thread(PID, "original-local-denied-http-v1", tag="SOME_OTHER_APP")
            + "10-10 18:40:01.013  2345  2500 E KNEEKURA_STATIC_HTTP: SECRET\n"
        )
        signal = obs.sanitized_original_activity_events(raw, pid=PID)
        self.assertEqual(signal["denied_HTTP_calls_observed"], 1)
        report = repr(signal)
        for secret in ("TOP_SECRET", "VERY_PRIVATE_PLAYER_SAVE",
                       "not_logged", "SAVE_CONTENT", "999999"):
            self.assertNotIn(secret, report)

    def test_one_research_pid_and_no_online_permission_are_strict(self):
        receipt = obs.build_original_local_boot_metadata_receipt(
            pm_paths=PM_PATHS, dumpsys_package=DUMPSYS,
            pid_output=str(PID), logcat=SAMPLE,
        )
        self.assertEqual(receipt["exact_package"], "jp.kn.local.battlecats")
        self.assertEqual(receipt["status"], "LOCAL_ROOT_METADATA_OBSERVED_NOT_NATIVE_BOOT_PROOF")
        self.assertEqual(receipt["installed_original_research_apk_split_count"], 2)
        self.assertTrue(receipt["manifest_INTERNET_permission_not_declared_observed"])
        for field in (
            "observed_original_native_scene102",
            "observed_original_native_scene101",
            "original_gameplay_SAVE_validated_or_generated",
            "original_stage_level60_xp_catseye_gameplay_verified",
            "all_35_download_tsv_contents_original_engine_accepted",
            "independent_sdk_ipc_external_network_egress_measured_zero",
            "finished_original_game_offline_product",
        ):
            self.assertFalse(receipt[field], field)
        self.assertTrue(receipt["adb_commands_were_read_only"])

    def test_no_research_root_event_is_hard_blocked_not_fake_boot(self):
        receipt = obs.build_original_local_boot_metadata_receipt(
            pm_paths=PM_PATHS, dumpsys_package=DUMPSYS,
            pid_output=str(PID), logcat=safe_thread(PID, "unrecognized-notice"),
        )
        self.assertEqual(
            receipt["status"], "BLOCKED_NO_CURRENT_PROCESS_RESEARCH_ROOT_WITNESS"
        )
        self.assertFalse(receipt["finished_original_game_offline_product"])

    def test_permission_package_and_installed_apk_fail_closed(self):
        params = {
            "pm_paths": PM_PATHS, "dumpsys_package": DUMPSYS,
            "pid_output": str(PID), "logcat": SAMPLE,
        }
        variations = [
            {"dumpsys_package": DUMPSYS + "android.permission.INTERNET\n"},
            {"dumpsys_package": "Package [jp.co.ponos.battlecats]:"},
            {"pm_paths": "package:/tmp/foreign/not_game.bin"},
            {"pm_paths": ""},
            {"pid_output": ""},
            {"pid_output": "1234 5678"},
            {"pid_output": "0"},
        ]
        for variant in variations:
            with self.subTest(variant=variant), self.assertRaises(
                obs.OriginalLocalBootObservationError
            ):
                obs.build_original_local_boot_metadata_receipt(
                    **{**params, **variant}
                )

    def test_loose_tsv_coverage_must_sum_to_exact_original_35(self):
        raw = (
            safe_thread(PID, "original-download-tsv-loose-v1 present=2 absent=33 unsafe=0")
            + safe_thread(PID, "original-download-tsv-loose-v1 present=5 absent=35 unsafe=1")
        )
        receipt = obs.sanitized_original_activity_events(raw, pid=PID)
        self.assertEqual(receipt["last_loose_35_TSV_presence_metadata"],
                         {"loose_present": 2, "loose_absent": 33, "unsafe": 0})
        self.assertNotIn("secret", repr(receipt).lower())

    def test_logcat_byte_cap_and_malformed_pid_rejected(self):
        with self.assertRaises(obs.OriginalLocalBootObservationError):
            obs.sanitized_original_activity_events("X" * (obs.MAX_LOGCAT_BYTES+1),
                                                  pid=PID)
        for invalid in (None, True, 0, -5, 5_000_000):
            with self.subTest(invalid=invalid), self.assertRaises(
                obs.OriginalLocalBootObservationError
            ):
                obs.sanitized_original_activity_events(SAMPLE, pid=invalid)

    def test_only_whitelisted_read_only_adb_commands_and_one_exact_package(self):
        calls = []
        answers = iter((PM_PATHS, DUMPSYS, str(PID), SAMPLE))
        def fake_run(exe, args, *, serial, timeout=20):
            calls.append((exe, tuple(args), serial))
            return next(answers)
        with patch.object(obs, "_adb_read", side_effect=fake_run):
            report = obs.collect_original_local_boot_adb(serial="emulator-5554")
        self.assertEqual(len(calls), 4)
        self.assertEqual(calls[0][1], (
            "shell", "pm", "path", "jp.kn.local.battlecats"
        ))
        self.assertEqual(calls[1][1], (
            "shell", "dumpsys", "package", "jp.kn.local.battlecats"
        ))
        self.assertEqual(calls[2][1], (
            "shell", "pidof", "jp.kn.local.battlecats"
        ))
        self.assertEqual(calls[3][1], (
            "logcat", "-d", "-v", "threadtime", "--pid=2345",
            "-s", "KNEEKURA_STATIC_HTTP:I", "*:S"
        ))
        self.assertTrue(all(serial == "emulator-5554"
                            for _, _, serial in calls))
        self.assertFalse(report["finished_original_game_offline_product"])

    def test_foreign_or_online_package_fails_before_pid_or_logcat(self):
        calls = []
        def fake_read(exe, args, *, serial, timeout=20):
            calls.append(tuple(args))
            if len(calls) == 1:
                return PM_PATHS
            return DUMPSYS + "  android.permission.INTERNET\n"
        with patch.object(obs, "_adb_read", side_effect=fake_read):
            with self.assertRaises(obs.OriginalLocalBootObservationError):
                obs.collect_original_local_boot_adb()
        self.assertEqual(len(calls), 2)
        self.assertNotIn(("shell","pidof","jp.kn.local.battlecats"), calls)

    def test_private_output_directory_only_no_existing_file(self):
        with tempfile.TemporaryDirectory() as scratch:
            home = Path(scratch)
            private = home / "private"
            private.mkdir()
            (home / "other").mkdir()
            with patch.object(obs, "ROOT", home), patch.object(obs, "PRIVATE_ROOT", private):
                path = obs._protected_output_destination(
                    Path("private/observations/check-01.json")
                )
                self.assertTrue(path.is_relative_to(private))
                with self.assertRaises(obs.OriginalLocalBootObservationError):
                    obs._protected_output_destination(Path("other/receipt.json"))
                with self.assertRaises(obs.OriginalLocalBootObservationError):
                    obs._protected_output_destination(Path("../escaped.json"))
                path.parent.mkdir(exist_ok=True)
                path.write_text("SENSITIVE_USER_PRIVATE_DATA")
                with self.assertRaises(obs.OriginalLocalBootObservationError):
                    obs._protected_output_destination(path)
                self.assertEqual(path.read_text(), "SENSITIVE_USER_PRIVATE_DATA")


if __name__ == "__main__":
    import unittest
    unittest.main()
