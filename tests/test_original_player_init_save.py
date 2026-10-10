"""Synthetic only: no original binary, private SAVE, or owner pack is committed."""
import struct
import unittest

from tools.base_mod.trace_original_player_init_save import (
    ORIGINAL_ANCHORS, ORIGINAL_LABELS, RELOCATIONS, RELA_START, RELA_SIZE,
    BL_TARGETS, BRANCHES, ACCOUNT_DELETE_RESET_ANCHORS,
    ACCOUNT_DELETE_RESET_CALLS, ACCOUNT_DELETE_RESET_BRANCHES,
    OriginalPlayerInitSaveTraceError,
    _target, inspect_original_player_init_save,
    trace_exact_original_player_init_save,
)


def _fixture() -> bytearray:
    # Exact *selected instruction words*, with every unrelated byte synthetic 0.
    blob = bytearray(max(ORIGINAL_ANCHORS) + 4)
    for pc, op in {**ORIGINAL_ANCHORS, **ACCOUNT_DELETE_RESET_ANCHORS}.items():
        struct.pack_into("<I", blob, pc, op)
    for at, literal in ORIGINAL_LABELS.items():
        blob[at:at + len(literal)] = literal
    for index, (slot, dest) in enumerate(RELOCATIONS.items()):
        struct.pack_into(
            "<QQq", blob, RELA_START + index * RELA_SIZE, slot, 0x403, dest
        )
    return blob


class OriginalPlayerStateInitToNativeSaveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = bytes(_fixture())

    def test_real_baseline_initializes_exact_original_game_upgrade_records(self):
        result = inspect_original_player_init_save(self.source)
        self.assertEqual(result["status"],
                         "ORIGINAL_NATIVE_PLAYER_INITIALIZER_AND_TITLE_RESET_SAVER_STATIC")
        self.assertIn("0xc3b8", result["xp_zero_writer"])
        self.assertIn("882 records", result["current_level_initialization"])
        self.assertIn("0x47ba4", result["current_level_initialization"])
        self.assertIn("882 records", result["cap_increment_initialization"])
        self.assertIn("0x3ad80c", result["cap_increment_initialization"])
        self.assertFalse(result["original_android_fresh_local_SAVE_written"])
        self.assertFalse(result["original_lv60_xp_catseye_reboot_passed"])

    def test_original_title_rtti_source_and_save_are_not_fresh_start_evidence(self):
        result = inspect_original_player_init_save(self.source)
        self.assertIn("TitleUpdate", result["title_rtti"])
        self.assertIn("restart_reflect", result["title_dialog_name"])
        self.assertIn("0x9345a4 -> 0x8b9fc8", result["title_reset_writes_original_SAVE"])
        self.assertTrue(result["original_title_reset_and_native_writer_connected"])
        self.assertFalse(result["title_or_service_reset_accepted_for_legitimate_virgin_game"])
        self.assertFalse(result["normal_new_player_entry_identified"])
        self.assertFalse(result["original_sdk_ipc_zero_egress_verified"])
        self.assertFalse(result["original_apk_SAVE_pack_modified"])

    def test_my_game_services_reset_save_not_mislabeled_as_virgin(self):
        result = inspect_original_player_init_save(self.source)
        self.assertEqual(result["game_services_rtti"], "22MyGameServicesDelegate")
        self.assertIn("0x749e80 -> 0x89385c", result["service_state9_reset_and_save"])
        self.assertIn("0x749eb0 -> 0x8b9fc8", result["service_state9_reset_and_save"])
        self.assertFalse(result["normal_new_player_entry_identified"])

    def test_account_delete_browser_reset_save_cannot_be_claimed_virgin(self):
        receipt = inspect_original_player_init_save(self.source)
        self.assertIn("miniBrowserLinkClicked", receipt["account_deletion_callback_rtti"])
        self.assertIn("AccountDelete_error02",
                      receipt["account_deletion_error_literals"])
        self.assertIn("0x776584 -> 0x89385c",
                      receipt["account_deletion_success_reset"])
        self.assertIn("0x7765a4 -> 0x8b9fc8",
                      receipt["account_deletion_success_original_SAVE"])
        self.assertIn("scene104", receipt["account_deletion_success_scene"])
        self.assertTrue(receipt["account_deletion_not_safe_to_repurpose_as_offline_virgin"])
        self.assertFalse(receipt["normal_new_player_entry_identified"])

    def test_account_delete_callback_branch_and_actual_writer_drift_fails(self):
        for pc, op in ACCOUNT_DELETE_RESET_CALLS.items():
            with self.subTest(call=hex(pc)):
                self.assertEqual(_target(self.source, pc, "bl"), op)
        for pc, (kind, target) in ACCOUNT_DELETE_RESET_BRANCHES.items():
            with self.subTest(branch=hex(pc)):
                self.assertEqual(_target(self.source, pc, kind), target)
        for pc in ACCOUNT_DELETE_RESET_ANCHORS:
            with self.subTest(pinned_instruction=hex(pc)):
                changed = bytearray(self.source)
                changed[pc] ^= 1
                with self.assertRaises(OriginalPlayerInitSaveTraceError):
                    inspect_original_player_init_save(bytes(changed))

    def test_selected_real_arm64_direct_calls_and_branches(self):
        for at, dest in BL_TARGETS.items():
            with self.subTest(site=hex(at)):
                self.assertEqual(_target(self.source, at, "bl"), dest)
        for at, (kind, dest) in BRANCHES.items():
            with self.subTest(site=hex(at)):
                self.assertEqual(_target(self.source, at, kind), dest)

    def test_mutated_init_level_cap_title_and_save_instructions_fail_closed(self):
        for at in (
            0x719434, 0x719444, 0x71A1E0, 0x71A214, 0x71A224, 0x71A228,
            0x71A4FC, 0x71A504, 0x71A510, 0x71A51C, 0x71F338,
            0x89386C, 0x938CC4, 0x938D28, 0x938D30, 0x938DE0,
            0x934028, 0x9345A4, 0x749E78, 0x749E80, 0x749EB0,
        ):
            with self.subTest(site=hex(at)):
                bad = bytearray(self.source)
                bad[at] ^= 1
                with self.assertRaises(OriginalPlayerInitSaveTraceError):
                    inspect_original_player_init_save(bytes(bad))

    def test_type_identification_and_relocation_drift_fail_closed(self):
        for at in ORIGINAL_LABELS:
            with self.subTest(label=hex(at)):
                bad = bytearray(self.source)
                bad[at] ^= 1
                with self.assertRaises(OriginalPlayerInitSaveTraceError):
                    inspect_original_player_init_save(bytes(bad))
        for offset, replacement in ((8, 0), (16, 0x11111)):
            with self.subTest(reloffset=offset):
                bad = bytearray(self.source)
                struct.pack_into("<Q", bad, RELA_START + offset, replacement)
                with self.assertRaises(OriginalPlayerInitSaveTraceError):
                    inspect_original_player_init_save(bytes(bad))
        bad = bytearray(self.source)
        slot = next(iter(RELOCATIONS))
        struct.pack_into("<QQq", bad,
                         RELA_START + len(RELOCATIONS) * RELA_SIZE,
                         slot, 0x403, RELOCATIONS[slot])
        with self.assertRaises(OriginalPlayerInitSaveTraceError):
            inspect_original_player_init_save(bytes(bad))

    def test_strict_owner_hash_and_truncated_source_guard(self):
        with self.assertRaisesRegex(OriginalPlayerInitSaveTraceError, "exact original"):
            trace_exact_original_player_init_save(self.source)
        with self.assertRaises(OriginalPlayerInitSaveTraceError):
            inspect_original_player_init_save(b"\x7fELF")


if __name__ == "__main__":
    unittest.main()
