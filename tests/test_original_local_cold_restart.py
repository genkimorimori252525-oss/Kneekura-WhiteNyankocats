"""Synthetic original two-PID readback receipts, not user game SAVE/ADB."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.base_mod import collect_original_local_first_boot as boot
from tools.base_mod import verify_original_local_cold_restart as proof


PACKAGE_PATHS = "".join(
    "package:/data/app/jp.kn.local.battlecats/" + p + "\n"
    for p in boot.JP_15_7_1_SPLITS
)
PACKAGE_PERMISSIONS = ("Packages:\n"
   "  Package [jp.kn.local.battlecats] (abcdef):\n"
   "    requested permissions:\n"
   "      android.permission.ACCESS_NETWORK_STATE\n")


def event(pid: int, msg: str) -> str:
    return f"10-11 01:20:09.010 {pid:5d} 2500 I {boot.LOG_TAG}: {msg}\n"


def receipt(which: str, *, pid: int = 1337) -> dict:
    logs = [
        "original-save-event-observer-v1 active",
        "original-local-fresh-package-root active",
    ]
    if which == "first":
        logs.extend([
            "original-save-presence-v1 SAVE_DATA=absent "
                "SAVE_DATA4=absent SAVE_DATA8=absent",
            "original-native-scene-hook-v1 installed",
            "original-native-virgin-save-trial-v1 root-attested",
            "original-native-virgin-save-trial-v1 read-accepted",
            "original-save-presence-v1 SAVE_DATA=present:2048 "
                "SAVE_DATA4=absent SAVE_DATA8=absent",
        ])
    elif which == "second":
        logs.extend([
            "original-save-presence-v1 SAVE_DATA=present:2048 "
                "SAVE_DATA4=absent SAVE_DATA8=absent",
            "original-native-scene-hook-v1 installed",
            "original-native-app-launch-save-read-v1 accepted",
        ])
    else:
        raise ValueError(which)
    return boot.build_original_local_boot_metadata_receipt(
        pm_paths=PACKAGE_PATHS, dumpsys_package=PACKAGE_PERMISSIONS,
        pid_output=str(pid),
        logcat="".join(event(pid, msg) for msg in logs),
    )


class OriginalSourceTwoProcessReadbackTests(unittest.TestCase):
    def setUp(self):
        self.first = receipt("first", pid=2010)
        self.second = receipt("second", pid=2111)

    def test_two_process_source_narrow_pass_does_not_promote_gameplay(self):
        result = proof.evaluate_original_local_two_process_readback(
            self.first, self.second
        )
        self.assertEqual(result["status"], proof.STATUS)
        self.assertTrue(result["first_process_original_virgin_native_readback_observed"])
        self.assertTrue(result["second_process_original_AppLaunchLoad_read_accepted_observed"])
        self.assertTrue(result["two_distinct_original_process_PIDs_observed"])
        self.assertEqual(result["first_original_SAVE_file_size_bytes"], 2048)
        self.assertEqual(result["second_original_SAVE_file_size_bytes"], 2048)
        for forbidden in (
            "same_device_cryptographically_attested", "physical_device_reboot_verified",
            "original_SAVE_fsync_and_durability_proven",
            "original_gameplay_level60_MAX_and_Madoka_Godzilla_verified",
            "SDK_IPC_external_network_egress_measured_zero",
            "ready_to_install_or_ship_original_game",
        ):
            self.assertFalse(result[forbidden], forbidden)
        self.assertNotIn("currently_running_process_pid", result)

    def test_reject_same_PID_different_packages_or_missing_splits(self):
        for field, bad in (
            ("currently_running_process_pid", 2010),
            ("exact_package", "jp.co.ponos.battlecats"),
            ("installed_original_research_apk_split_count", 5),
            ("manifest_INTERNET_permission_not_declared_observed", False),
            ("status", "BLOCKED_NO_CURRENT_PROCESS_RESEARCH_ROOT_WITNESS"),
            ("adb_commands_were_read_only", False),
            ("native_scene_ID_source_in_current_logcat", False),
        ):
            candidate = copy.deepcopy(self.second)
            candidate[field] = bad
            with self.subTest(field=field), self.assertRaises(
                proof.OriginalLocalColdRestartError
            ):
                proof.evaluate_original_local_two_process_readback(
                    self.first, candidate
                )

    def test_reject_first_missing_save_transition_or_native_failure(self):
        for path,bad in (
            (("observed_original_native_virgin_trial_readback_this_process_only",),
             False),
            (("signals", "SAVE_absence_then_presence_observed_in_this_PID"),False),
            (("signals", "native_virgin_trial_failed_or_conflicting"),True),
            (("signals", "native_original_virgin_trial_event_order_metadata_only"),
             ["original-native-virgin-save-trial-v1 writer-rejected"]),
        ):
            modified = copy.deepcopy(self.first)
            current = modified
            for field in path[:-1]:
                current = current[field]
            current[path[-1]]=bad
            with self.subTest(path=path), self.assertRaises(
                proof.OriginalLocalColdRestartError
            ):
                proof.evaluate_original_local_two_process_readback(
                    modified, self.second
                )

    def test_reject_second_new_virgin_write_or_original_read_failed(self):
        for path,bad in (
            (("observed_original_AppLaunchLoad_SAVE_read_accepted",),False),
            (("signals","source_pinned_app_launch_save_read_outcomes"),
             ["original-native-app-launch-save-read-v1 failed"]),
            (("signals","native_original_virgin_trial_event_order_metadata_only"),
             ["original-native-virgin-save-trial-v1 root-attested"]),
            (("signals","native_app_launch_save_read_conflicting"),True),
            (("signals","SAVE_absence_then_presence_observed_in_this_PID"),True),
        ):
            modified=copy.deepcopy(self.second)
            node=modified
            for field in path[:-1]:
                node=node[field]
            node[path[-1]]=bad
            with self.subTest(path=path),self.assertRaises(
                proof.OriginalLocalColdRestartError
            ):
                proof.evaluate_original_local_two_process_readback(
                    self.first,modified
                )

    def test_reject_missing_zero_or_unsafe_save_snapshots(self):
        for state,size in (("absent",None),("unsafe",None),("present",0),
                           ("present",-1),("present",2**29)):
            second=copy.deepcopy(self.second)
            second["signals"]["last_original_SAVE_metadata"]["SAVE_DATA"]={
                "status":state,"size_bytes":size
            }
            with self.subTest(state=state,size=size),self.assertRaises(
                proof.OriginalLocalColdRestartError
            ):
                proof.evaluate_original_local_two_process_readback(
                    self.first,second
                )

    def test_private_inputs_only_and_exclusive_json_output(self):
        with tempfile.TemporaryDirectory(prefix="knee-two-process-") as d:
            directory=Path(d)
            a=directory/"first.json"; b=directory/"second.json"
            out=directory/"verified.json"
            a.write_text(json.dumps(self.first),encoding="utf-8")
            b.write_text(json.dumps(self.second),encoding="utf-8")
            with patch.object(proof,"PRIVATE_ROOT",directory),\
                 patch.object(boot,"PRIVATE_ROOT",directory):
                self.assertEqual(proof.main([
                    "--first",str(a),"--second",str(b),"--output",str(out)
                ]),0)
                result=json.loads(out.read_text(encoding="utf-8"))
                self.assertEqual(result["status"],proof.STATUS)
                with self.assertRaises(SystemExit):
                    proof.main([
                        "--first",str(a),"--second",str(b),"--output",str(out)
                    ])
                with self.assertRaises(proof.OriginalLocalColdRestartError):
                    proof._load_protected_metadata(Path("/tmp/foreign.json"))

    def test_source_code_has_no_android_mutation_operations(self):
        source=Path(proof.__file__).read_text(encoding="utf-8")
        for banned in ("adb install", "pm clear", "adb uninstall",
                       "am force-stop", "shell rm -rf", "getFilesDir",
                       "SAVE_DATA=open(", "newHttpRequest"):
            self.assertNotIn(banned,source)
        self.assertIn("same_device_cryptographically_attested",source)
        self.assertIn("original_SAVE_fsync_and_durability_proven",source)


if __name__=="__main__":
    unittest.main()
