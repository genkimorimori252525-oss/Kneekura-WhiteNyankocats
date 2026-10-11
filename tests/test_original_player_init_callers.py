"""Synthetic exact-site regression; never commit original JP ELF or SAVE bytes."""
from __future__ import annotations

import struct
import unittest

from tools.base_mod.trace_original_player_init_callers import (
    TEXT_START, TEXT_END, EXPECTED_DIRECT_INIT_CALLERS,
    EXPECTED_DIRECT_RESET_CALLERS, EXPECTED_DIRECT_SAVE_READER_CALLERS,
    EXPECTED_NATIVE_SAVE_WRITER_DIRECT_SITE_COUNT,
    ORIGINAL_CALLER_CONTEXT_LABELS, STATE_DEFAULT_INITIALIZER,
    SUBSYSTEM_RESET, ORIGINAL_SAVE_READER_WORKER, ORIGINAL_SAVE_WRITER,
    OriginalInitCensusError, direct_call_census,
    inspect_direct_original_player_init_callers,
    inspect_exact_owner_original_init_callers,
)


def _put_bl(blob: bytearray, pc: int, target: int) -> None:
    distance = target - pc
    assert distance % 4 == 0 and -(1 << 27) <= distance < (1 << 27)
    struct.pack_into("<I", blob, pc, 0x94000000 | ((distance // 4) & 0x03FFFFFF))


def _put_original_adrp_add(blob: bytearray, pc: int, target: int, rd: int) -> None:
    diff_pages = ((target & ~0xFFF) - (pc & ~0xFFF)) // 4096
    imm = diff_pages & 0x1FFFFF
    adrp = 0x90000000 | ((imm & 3) << 29) | (((imm >> 2) & 0x7FFFF) << 5) | rd
    add = 0x91000000 | ((target & 0xFFF) << 10) | (rd << 5) | rd
    struct.pack_into("<II", blob, pc, adrp, add)


def _synthetic_full_text_fixture() -> bytes:
    # These zeros are NOT native game executable. Only relevant synthetic
    # ARM64 direct BL, ADRP, ADD, and NUL-terminated fixture labels exist.
    blob = bytearray(TEXT_END)
    for pc in EXPECTED_DIRECT_INIT_CALLERS:
        _put_bl(blob, pc, STATE_DEFAULT_INITIALIZER)
    for pc in EXPECTED_DIRECT_RESET_CALLERS:
        _put_bl(blob, pc, SUBSYSTEM_RESET)
    for pc in EXPECTED_DIRECT_SAVE_READER_CALLERS:
        _put_bl(blob, pc, ORIGINAL_SAVE_READER_WORKER)
    for i in range(EXPECTED_NATIVE_SAVE_WRITER_DIRECT_SITE_COUNT):
        _put_bl(blob, 0x400000 + i * 4, ORIGINAL_SAVE_WRITER)
    for pc, rodata, name in ORIGINAL_CALLER_CONTEXT_LABELS:
        blob[rodata:rodata + len(name) + 1] = name.encode("ascii") + b"\x00"
        _put_original_adrp_add(blob, pc, rodata, 8 if pc == 0x7765D4 else 9)
    return bytes(blob)


class NativeFirstPlayerInitializerCallerCensusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.native = _synthetic_full_text_fixture()

    def test_exhaustive_exact_synthetic_ram_initializer_and_reset_xrefs(self):
        receipt = inspect_direct_original_player_init_callers(self.native)
        self.assertEqual(receipt["state_initializer_direct_site_count"], 4)
        self.assertEqual(receipt["common_reset_direct_site_count"], 6)
        self.assertEqual(receipt["original_SAVE_writer_direct_bl_site_count"], 158)
        self.assertEqual(receipt["original_SAVE_reader_worker_direct_bl_sites"],
                         ["0x492be8"])
        self.assertEqual(len(receipt["transfer_and_account_context_source_labels"]), 5)
        self.assertTrue(receipt["direct_caller_survey_complete_for_exact_original_text"])
        self.assertFalse(receipt["indirect_BLR_or_virtual_reset_callers_excluded"])
        self.assertFalse(receipt["other_player_state_initializers_excluded"])
        self.assertFalse(receipt["legitimate_original_new_player_SAVE_constructor_identified"])
        self.assertFalse(receipt["user_private_original_APK_SAVE_or_assets_modified"])

    def test_transfer_source_and_account_delete_are_not_new_player_evidence(self):
        receipt = inspect_direct_original_player_init_callers(self.native)
        all_labels = {x["source_label"]
                      for x in receipt["transfer_and_account_context_source_labels"]}
        self.assertEqual(all_labels, {
            "kisyuhen_02_kisyuhen02", "transfer_backup",
            "data_download_error_could_not_load", "kisyuhen_03_hikitugi02",
            "AccountDelete_error02",
        })
        self.assertIn("restore/deserializer",
                      receipt["reset_caller_context"]["0x74906c"])
        self.assertIn("AccountDelete",
                      receipt["reset_caller_context"]["0x776584"])
        self.assertFalse(receipt["transfer_restore_delete_flow_is_verified_virgin_profile"])

    def test_unknown_new_initializer_direct_caller_must_not_silently_pass(self):
        broken = bytearray(self.native)
        _put_bl(broken, 0x410000, STATE_DEFAULT_INITIALIZER)
        with self.assertRaisesRegex(OriginalInitCensusError, "initializer direct caller drift"):
            inspect_direct_original_player_init_callers(bytes(broken))

    def test_unknown_new_subsystem_reset_caller_must_not_silently_pass(self):
        broken = bytearray(self.native)
        _put_bl(broken, 0x420000, SUBSYSTEM_RESET)
        with self.assertRaisesRegex(OriginalInitCensusError, "reset direct caller drift"):
            inspect_direct_original_player_init_callers(bytes(broken))

    def test_missing_read_caller_or_changed_native_save_writer_count_rejected(self):
        for pc in (0x492BE8, 0x400000):
            with self.subTest(call=hex(pc)):
                broken = bytearray(self.native)
                struct.pack_into("<I", broken, pc, 0xD503201F)
                with self.assertRaises(OriginalInitCensusError):
                    inspect_direct_original_player_init_callers(bytes(broken))

    def test_private_original_context_string_xref_or_opcode_drift_rejected(self):
        for pc, rodata, name in ORIGINAL_CALLER_CONTEXT_LABELS:
            with self.subTest(source_label=name):
                bad_str = bytearray(self.native)
                bad_str[rodata] ^= 1
                with self.assertRaises(OriginalInitCensusError):
                    inspect_direct_original_player_init_callers(bytes(bad_str))
                bad_adrp = bytearray(self.native)
                bad_adrp[pc] ^= 1
                with self.assertRaises(OriginalInitCensusError):
                    inspect_direct_original_player_init_callers(bytes(bad_adrp))

    def test_invalid_bounds_wrong_type_and_privacy_hash_fail_closed(self):
        with self.assertRaises(OriginalInitCensusError):
            direct_call_census(b"not-ELF", text_start=0, text_end=TEXT_END)
        with self.assertRaises(OriginalInitCensusError):
            direct_call_census(self.native, (STATE_DEFAULT_INITIALIZER,
                                             STATE_DEFAULT_INITIALIZER))
        with self.assertRaises(OriginalInitCensusError):
            direct_call_census(self.native, text_start=1, text_end=8)
        with self.assertRaises(OriginalInitCensusError):
            inspect_exact_owner_original_init_callers(self.native)

    def test_small_synthetic_bl_scan_is_not_executed_or_mislabeled_gameplay(self):
        blob = bytearray(64)
        _put_bl(blob, 0, 32)
        result = direct_call_census(bytes(blob), (32,), text_start=0, text_end=64)
        self.assertEqual(result, {32: [0]})


if __name__ == "__main__":
    unittest.main()
