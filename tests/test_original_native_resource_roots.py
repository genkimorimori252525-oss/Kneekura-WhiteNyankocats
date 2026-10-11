"""Synthetic static regression for real original resource file-root fallbacks.

No copyrighted original executable, private owned pack payload or SAVE bytes.
"""
import struct
import unittest

from tools.base_mod.trace_original_native_resource_roots import (
    FILE_SOURCE_ANCHORS, DIRECT_BL, BRANCHES,
    OriginalNativeResourceSeamError, _direct_target,
    inspect_source_file_roots, trace_exact_owner_source,
)


def _synthetic_exact_file_root_fixture() -> bytearray:
    # The file is a SPARSE synthetic instruction fixture, not real executable.
    blob = bytearray(max(FILE_SOURCE_ANCHORS) + 4)
    for pc, opcode in FILE_SOURCE_ANCHORS.items():
        struct.pack_into("<I", blob, pc, opcode)
    blob[0x1905A5:0x1905B1] = b"getFilesDir\x00"
    return blob


class OriginalNativeServerAssetSourceTests(unittest.TestCase):
    def test_original_registers_list_through_app_files_root_fallback(self):
        fixture = _synthetic_exact_file_root_fixture()
        before = bytes(fixture)
        result = inspect_source_file_roots(before)
        self.assertIn("getFilesDir", result["list_filesdir_fallback"])
        self.assertIn("0x35e144", result["list_filesdir_retry"])
        self.assertTrue(result["registered_server_list_searches_application_filesdir_static_proven"])
        self.assertTrue(result["normal_and_alternative_registered_key_source_differentiated"])
        self.assertIn("0x42cdf8", result["final_unregistered_direct_name_source_attempt"])
        self.assertTrue(result["final_direct_source_attempt_without_registry_static_proven"])
        self.assertFalse(result["registered_list_and_pair_loaded_on_android"])
        self.assertFalse(result["direct_source_35_tsv_success_or_acceptance_proven"])
        self.assertFalse(result["native_first_run_save_or_lv60_verified"])
        self.assertFalse(result["original_apk_save_or_pack_modified"])
        self.assertEqual(bytes(fixture), before)

    def test_all_exact_call_and_branch_targets_from_original(self):
        fixture = bytes(_synthetic_exact_file_root_fixture())
        for pc, target in DIRECT_BL.items():
            with self.subTest(pc=hex(pc)):
                self.assertEqual(_direct_target(fixture, pc, "bl"), target)
        for pc, (kind, target) in BRANCHES.items():
            with self.subTest(pc=hex(pc)):
                self.assertEqual(_direct_target(fixture, pc, kind), target)

    def test_if_filesdir_fallback_or_end_of_chain_is_mutated_fail_closed(self):
        fixture = _synthetic_exact_file_root_fixture()
        for pc in (0x42CDE4, 0x42CDE8, 0x45A694, 0x34D178,
                   0x34D17C, 0x34D184, 0x34D1D8, 0x34D304,
                   0x34D93C, 0x34DB44, 0x34DB94,
                   0x34DBF4, 0x34DC24, 0x364BA4,
                   0x364BD0, 0x364C44, 0x364C50, 0x364CC4):
            with self.subTest(pc=hex(pc)):
                bad = bytearray(fixture)
                bad[pc] ^= 1
                with self.assertRaises(OriginalNativeResourceSeamError):
                    inspect_source_file_roots(bytes(bad))

    def test_local_source_type_and_literal_mismatch_are_refused(self):
        fixture = _synthetic_exact_file_root_fixture()
        for where in (0x1905A5, 0x1905B0):
            with self.subTest(where=hex(where)):
                bad = bytearray(fixture)
                bad[where] ^= 1
                with self.assertRaisesRegex(
                    OriginalNativeResourceSeamError, "getFilesDir"
                ):
                    inspect_source_file_roots(bytes(bad))
        for pc, kind in ((0x34D93C, "cbz"),
                         (0x34DBF4, "b"),
                         (0x34D17C, "cbnz")):
            with self.subTest(pc=hex(pc)):
                with self.assertRaises(OriginalNativeResourceSeamError):
                    _direct_target(bytes(fixture), pc, kind)

    def test_only_exact_private_original_native_hash_can_be_live_evidence(self):
        with self.assertRaisesRegex(OriginalNativeResourceSeamError, "exact original"):
            trace_exact_owner_source(bytes(_synthetic_exact_file_root_fixture()))
        with self.assertRaises(OriginalNativeResourceSeamError):
            inspect_source_file_roots(b"\x7fELF")


if __name__ == "__main__":
    unittest.main()
