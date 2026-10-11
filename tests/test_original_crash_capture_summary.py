"""Synthetic rapid-restart research logs only, no owner device identifiers."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from tools.base_mod.summarize_original_crash_capture import (
    summarize, from_private_capture, OriginalCrashLogBlocked,
)


def row(pid: int, tag: str, message: str) -> str:
    return f"10-11 04:04:25.123 {pid:>5} {pid:>5} I {tag}: {message}\n"


class OriginalPrivateCrashMetadataTests(unittest.TestCase):
    def test_only_isolated_original_research_pid_events_counted(self):
        log = ""
        for pid in (101, 102, 103):
            log += row(1465, "ActivityManager", f"Start proc {pid}:jp.kn.local.battlecats/u0a999 for top")
            log += row(pid, "KNEEKURA_STATIC_HTTP",
                       "original-native-scene-hook-v1 hook-initialization-failed")
            if pid != 103:
                log += row(1465, "ActivityManager",
                           f"Process jp.kn.local.battlecats (pid {pid}) has died: fg TOP")
        # A separate banking application once polluted a naive "Start proc" substring count.
        log += row(1465, "ActivityManager",
                   "Start proc 8877:jp.example.some_bank/u0a999 for broadcast")
        log += row(8877, "libc", "Fatal signal 11 (SIGSEGV), code 1 (SEGV_MAPERR), pid 8877")
        log += row(101, "KNEEKURA_STATIC_HTTP", "SAVE or URL PRIVATE_TOKEN")
        result = summarize(log)
        self.assertEqual(result["isolated_original_research_process_starts_unique"], 3)
        self.assertEqual(result["isolated_original_research_process_deaths_unique"], 2)
        self.assertEqual(result["isolated_research_hook_event_processes_unique"], 3)
        self.assertEqual(result["native_hook_event_counts"]["hook-initialization-failed"], 3)
        self.assertEqual(result["research_SIGSEGV_signal_lines_in_filtered_log"], 0)
        self.assertFalse(result["every_start_matched_to_a_death_in_log"])
        self.assertNotIn("PRIVATE_TOKEN", str(result))
        self.assertEqual(result["status"],
                         "OBSERVED_RESTART_LOOP_WITH_HOOK_INITIALIZATION_FAILURE")
        self.assertFalse(result["hook_error_caused_crash_proven"])

    def test_new_init_code_distinguishes_api_vs_runtime_status(self):
        log = (row(1465, "ActivityManager",
                   "Start proc 101:jp.kn.local.battlecats/u0a999 for top")
               + row(101, "KNEEKURA_STATIC_HTTP",
                     "original-native-scene-hook-v1 hook-runtime-init-failed")
               + row(101, "KNEEKURA_STATIC_HTTP",
                     "original-native-scene-hook-v1 hook-init-status=12")
               + row(101, "KNEEKURA_STATIC_HTTP",
                     "original-native-scene-hook-v1 hook-init-status=999999")
               + row(999, "KNEEKURA_STATIC_HTTP",
                     "original-native-scene-hook-v1 hook-api-missing"))
        result = summarize(log)
        self.assertEqual(result["reported_shadowhook_init_status_codes"], {"12":1})
        self.assertEqual(result["native_hook_event_counts"]["hook-runtime-init-failed"], 1)
        # PID 999 has no matching ActivityManager research process witness.
        self.assertNotIn("hook-api-missing", result["native_hook_event_counts"])
        self.assertEqual(result["status"], "INSUFFICIENT_FOR_ROOT_CAUSE")
        self.assertNotIn("999999", str(result))

    def test_only_private_research_log_with_no_overwrite_or_public_leak(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/"private/original-crash-captures").mkdir(parents=True)
            file = root/"private/original-crash-captures"/"20261011-040424-filtered-logcat-PRIVATE.txt"
            file.write_text(row(1465, "ActivityManager",
                                "Start proc 101:jp.kn.local.battlecats/u0a999"))
            result, path = from_private_capture(repo=root, raw=file)
            self.assertTrue(path.is_relative_to(root/"private"))
            self.assertNotIn("101", path.read_text())
            with self.assertRaises(OriginalCrashLogBlocked):
                from_private_capture(repo=root, raw=root/"outside-raw.txt")
            (root/"outside-raw.txt").write_text("MY PRIVATE SAVE")
            with self.assertRaises(OriginalCrashLogBlocked):
                from_private_capture(repo=root, raw=root/"outside-raw.txt")
            self.assertFalse(result["original_gameplay_SAVE_level60_passed"])

    def test_one_shot_owner_ps_script_sanitizes_before_sharing(self):
        source_file = (Path(__file__).resolve().parents[1] /
                       "tools/base_mod/CAPTURE-OWNER-ORIGINAL-CRASH.ps1")
        data = source_file.read_bytes()
        self.assertTrue(data.startswith(bytes((239, 187, 191))))
        source = data.decode("utf-8-sig")
        self.assertIn("tools.base_mod.summarize_original_crash_capture", source)
        self.assertIn("'jp.kn.local.battlecats'", source)
        self.assertIn("Start-Process @startOptions", source)
        self.assertIn("Stop-Process -Id $proc.Id", source)
        self.assertIn("PRIVATE-RESEARCH-AGGREGATE-PASS", source)
        for forbidden in ("install-multiple", " pm clear ", "adb uninstall",
                          "shell am force-stop", "logcat -c"):
            self.assertNotIn(forbidden, source)

    def test_malformed_log_and_unknown_tags_not_gameplay_proof(self):
        result = summarize(
            row(777, "KNEEKURA_STATIC_HTTP", "original-native-scene-v1 id=101")
            + row(777, "ActivityManager", "Start proc 777:unrelated.foreign.app/other")
            + row(777, "AndroidRuntime", "PRIVATE_MESSAGE about some other app")
        )
        self.assertEqual(result["isolated_original_research_process_starts_unique"], 0)
        self.assertEqual(result["isolated_original_research_process_deaths_unique"], 0)
        self.assertFalse(result["original_gameplay_SAVE_level60_passed"])
        self.assertFalse(result["sdk_ipc_zero_egress_proven"])
        with self.assertRaises(OriginalCrashLogBlocked):
            summarize("X"*10_000_001)


if __name__ == "__main__":
    unittest.main()
