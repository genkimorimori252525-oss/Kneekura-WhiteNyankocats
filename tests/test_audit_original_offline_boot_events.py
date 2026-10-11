"""Synthetic privacy/safety tests for original offline scene97 fixed event audit."""
import unittest
from tools.base_mod.audit_original_offline_boot_events import (
    summarize_runtime_events, OriginalOfflineRuntimeProofBlocked,
)


class OriginalOfflineNativeBootMarkerTests(unittest.TestCase):
    def test_realistic_import_first_boot_never_proves_base(self):
        raw = "\n".join([
            "10-11 15:01:00.012 1234 5678 I KNEEKURA_STATIC_HTTP: original-native-scene-hook-v1 installed",
            "10-11 15:01:00.013 1234 5678 I KNEEKURA_STATIC_HTTP: original-native-scene-v1 id=102",
            "10-11 15:01:00.014 1234 5678 I KNEEKURA_STATIC_HTTP: original-native-scene-v1 id=101",
            "10-11 15:01:00.015 1234 5678 I KNEEKURA_STATIC_HTTP: original-native-scene-v1 id=97",
            "10-11 15:01:00.016 1234 5678 I KNEEKURA_STATIC_HTTP: original-local-import-v1 393-source-md5-pass",
            "10-11 15:01:00.017 1234 5678 I KNEEKURA_STATIC_HTTP: original-local-import-v1 completed-393",
            "10-11 15:01:00.018 1234 5678 I KNEEKURA_STATIC_HTTP: original-download-tsv-loose-v1 present=35 absent=0 unsafe=0",
            "10-11 15:01:00.019 1234 5678 I KNEEKURA_STATIC_HTTP: original-local-denied-http-v1",
            "10-11 15:01:00.020 1234 5678 I KNEEKURA_STATIC_HTTP: original-local-http-kind-v1 publisher-other",
        ])
        report=summarize_runtime_events(raw)
        self.assertEqual(report["status"], "ORIGINAL_393_IMPORTED_SCENE97_STILL_LAST_OBSERVED")
        self.assertEqual(report["native_hook_installed_events"],1)
        self.assertEqual(report["import_completed_393_events"],1)
        self.assertEqual(report["original_native_scene_ids_observed"],[102,101,97])
        self.assertEqual(report["last_original_loose_tsv_presence"]["present"],35)
        self.assertEqual(report["safe_denied_http_category_counts"],{"publisher-other":1})
        self.assertFalse(report["original_cat_base_visible_proven"])
        self.assertFalse(report["original_615mb_gate_bypassed_proven"])

    def test_exact_backup_failure_callback_is_not_publisher_success(self):
        report=summarize_runtime_events(
            "KNEEKURA_STATIC_HTTP: original-local-backup-failure-fallback-v1 completed\n"
            "KNEEKURA_STATIC_HTTP: original-local-backup-failure-fallback-v1 unavailable\n"
            "KNEEKURA_STATIC_HTTP: original-local-denied-http-v1\n"
            "KNEEKURA_STATIC_HTTP: original-local-http-kind-v1 publisher-other\n"
        )
        self.assertEqual(
            report["exact_backup_original_network_failure_callbacks_completed"],1)
        self.assertEqual(
            report["exact_backup_original_network_failure_callbacks_unavailable"],1)
        self.assertEqual(report["denied_http_requests_observed"],1)
        self.assertFalse(report["actual_publisher_backup_server_success_claimed"])
        self.assertFalse(report["original_cat_base_visible_proven"])

    def test_isolated_game_offline_network_gate_is_not_device_airplane_mode(self):
        report=summarize_runtime_events(
            "KNEEKURA_STATIC_HTTP: original-local-network-availability-v1 offline\n"
            "KNEEKURA_STATIC_HTTP: original-local-backup-failure-fallback-v1 completed\n"
            "KNEEKURA_STATIC_HTTP: original-native-scene-v1 id=97\n"
        )
        self.assertTrue(report["original_local_network_availability_false_observed"])
        self.assertEqual(report["original_local_network_unavailable_event_count"],1)
        self.assertEqual(report["exact_backup_original_network_failure_callbacks_completed"],1)
        self.assertFalse(report["original_cat_base_visible_proven"])
        self.assertFalse(report["original_615mb_gate_bypassed_proven"])

    def test_backup_request_shape_mask_is_bounded_and_has_no_request_data(self):
        source=chr(10).join([
            "KNEEKURA_STATIC_HTTP: original-local-backup-shape-v1 mask=7fd",
            "KNEEKURA_STATIC_HTTP: original-local-backup-shape-v1 mask=000",
            "KNEEKURA_STATIC_HTTP: original-local-backup-shape-v1 mask=800",
            "KNEEKURA_STATIC_HTTP: original-local-backup-shape-v1 mask=123456",
            "KNEEKURA_STATIC_HTTP: original-local-backup-shape-v1 mask=https://PRIVATE",
        ])
        report=summarize_runtime_events(source)
        self.assertEqual(report["blocked_backup_source_contract_bitmasks"],
                         {"000":1,"7fd":1})
        self.assertEqual(report["source_contract_mask_flags"]["timeout_10"],2)
        self.assertFalse(report["raw_request_URL_or_account_logged"])
        self.assertNotIn("PRIVATE",repr(report))
        self.assertFalse(report["original_cat_base_visible_proven"])

    def test_file_access_witness_is_bounded_and_does_not_name_files(self):
        report=summarize_runtime_events(chr(10).join([
            "KNEEKURA_STATIC_HTTP: original-local-file-access-v1 watching",
            "KNEEKURA_STATIC_HTTP: original-local-file-access-v1 download-tsv",
            "KNEEKURA_STATIC_HTTP: original-local-file-access-v1 server-list",
            "KNEEKURA_STATIC_HTTP: original-local-file-access-v1 server-pack",
            "KNEEKURA_STATIC_HTTP: original-local-file-access-v1 media",
            "KNEEKURA_STATIC_HTTP: original-local-file-access-v1 SAVE_DATA",
            "KNEEKURA_STATIC_HTTP: original-local-file-access-v1 /private/account",
        ]))
        self.assertEqual(
            report["original_file_source_access_kind_counts"],
            {"download-tsv":1, "media":1, "server-list":1,
             "server-pack":1, "watching":1},
        )
        self.assertFalse(report["real_native_source_consumed_original_TSV_proven"])
        self.assertFalse(report["original_game_cat_base_visible_proven"])
        self.assertNotIn("SAVE_DATA",repr(report))
        self.assertNotIn("/private/account",repr(report))

    def test_cold_restart_marker_and_no_source_md5_repetition(self):
        text=("KNEEKURA_STATIC_HTTP: original-local-import-v1 already-complete\n"
              "KNEEKURA_STATIC_HTTP: original-native-scene-v1 id=97\n")
        result=summarize_runtime_events(text)
        self.assertEqual(result["status"],"ORIGINAL_393_IMPORTED_SCENE97_STILL_LAST_OBSERVED")
        self.assertEqual(result["import_already_complete_events"],1)
        self.assertEqual(result["import_all_393_source_md5_verified_events"],0)

    def test_unknown_or_tainted_values_never_leak(self):
        raw="\n".join([
            "KNEEKURA_STATIC_HTTP: original-local-http-kind-v1 https://secret.invalid/TOKEN",
            "KNEEKURA_STATIC_HTTP: original-local-import-v1 /data/user/0/SAVE_DATA",
            "KNEEKURA_STATIC_HTTP: original-native-scene-v1 id=123456789",
            "AndroidRuntime: account user-PRIVATE@example.com URL https://bad.invalid",
            "KNEEKURA_STATIC_HTTP: original-local-http-kind-v1 asset-cdn",
            "KNEEKURA_STATIC_HTTP: original-local-http-kind-v1 malformed",
        ])
        result=summarize_runtime_events(raw)
        serialized=repr(result)
        for secret in ("https://", "user-PRIVATE", "SAVE_DATA", "123456789", "/data/user"):
            self.assertNotIn(secret,serialized)
        self.assertEqual(result["safe_denied_http_category_counts"],
                         {"asset-cdn":1,"malformed":1})
        self.assertFalse(result["device_or_game_data_modified"])

    def test_no_import_marker_and_bad_loose_count_fail(self):
        text=("KNEEKURA_STATIC_HTTP: original-download-tsv-loose-v1 present=35 absent=35 unsafe=0\n"
              "KNEEKURA_STATIC_HTTP: original-native-scene-v1 id=4\n")
        result=summarize_runtime_events(text)
        self.assertEqual(result["status"],"ORIGINAL_393_IMPORT_NOT_YET_ACCEPTED")
        self.assertIsNone(result["last_original_loose_tsv_presence"])
        self.assertFalse(result["original_scene97_completed_successfully_proven"])

    def test_oversized_research_log_refused(self):
        with self.assertRaisesRegex(OriginalOfflineRuntimeProofBlocked,"oversized"):
            summarize_runtime_events("X"*16_000_001)


if __name__=="__main__":
    unittest.main()
