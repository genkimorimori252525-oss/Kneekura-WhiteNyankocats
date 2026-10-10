"""Synthetic (not original APK or player SAVE) regressions for virgin read failure."""
import struct
import unittest

from tools.base_mod.trace_original_virgin_save_gate import (
    FIRST_BOOT_ANCHORS, DIRECT_BL, CONDITIONAL_BRANCHES,
    OriginalVirginSaveGateError, WRITER_TARGET, _bl_target, _cond_target,
    inspect_original_virgin_save_failure, trace_exact_original_virgin_save_gate,
)


def _fixture():
    image = bytearray(max(FIRST_BOOT_ANCHORS) + 4)
    for pc, opcode in FIRST_BOOT_ANCHORS.items():
        struct.pack_into("<I", image, pc, opcode)
    image[0x191955:0x19195F] = b"SAVE_DATA\x00"
    image[0x1A47F8:0x1A4805] = b"Map_Name.csv\x00"
    image[0x193AA0:0x193AAD] = b"Matatabi.tsv\x00"
    return image


class OriginalVirginSaveGateTests(unittest.TestCase):
    def test_missing_original_save_propagates_worker_failure_not_fake_profile(self):
        fixture = _fixture()
        original = bytes(fixture)
        receipt = inspect_original_virgin_save_failure(original)
        self.assertTrue(receipt["this_worker_attempting_missing_SAVE_reports_error_static_proven"])
        self.assertEqual(receipt["bounded_constructor_direct_calls_to_original_save_writer"], [])
        self.assertEqual(receipt["bounded_worker_direct_calls_to_original_save_writer"], [])
        self.assertIn("0x492bec", receipt["failure_propagates_to_worker"])
        self.assertIn("0x723448", receipt["observed_frame_failure_route"])
        self.assertFalse(receipt["all_original_virgin_initialization_paths_excluded"])
        self.assertFalse(receipt["fresh_local_original_native_profile_generator_identified"])
        self.assertFalse(receipt["any_sdk_ipc_zero_egress_hardware_run_verified"])
        self.assertEqual(bytes(fixture), original)

    def test_exact_source_original_calls_and_conditional_failure_edges(self):
        image = bytes(_fixture())
        for pc, target in DIRECT_BL.items():
            with self.subTest(pc=hex(pc)):
                self.assertEqual(_bl_target(image, pc), target)
        for pc, (kind, target) in CONDITIONAL_BRANCHES.items():
            with self.subTest(pc=hex(pc)):
                self.assertEqual(_cond_target(image, pc, kind), target)

    def test_missing_save_read_or_worker_error_branch_mutation_fails_closed(self):
        original = _fixture()
        for pc in (0x71C9C8, 0x71D30C, 0x493200, 0x492BD4, 0x492BE8,
                   0x492BEC, 0x9BB78C, 0x9BB794, 0x8B4404, 0x8B441C,
                   0x492D28, 0x492D2C, 0x723448, 0x72344C,
                   0x723458, 0x723460):
            with self.subTest(pc=hex(pc)):
                mutated = bytearray(original)
                mutated[pc] ^= 1
                with self.assertRaises(OriginalVirginSaveGateError):
                    inspect_original_virgin_save_failure(bytes(mutated))

    def test_ctor_direct_original_save_writer_would_invalidate_negative_claim(self):
        altered = _fixture()
        pc = 0x492950
        direct_delta = (WRITER_TARGET - pc) // 4
        self.assertEqual((WRITER_TARGET - pc) % 4, 0)
        struct.pack_into("<I", altered, pc, 0x94000000 | (direct_delta & 0x3FFFFFF))
        with self.assertRaisesRegex(OriginalVirginSaveGateError, "new direct SAVE writer"):
            inspect_original_virgin_save_failure(bytes(altered))

    def test_only_exact_owner_native_hash_is_authorized(self):
        with self.assertRaisesRegex(OriginalVirginSaveGateError, "exact JP15.7.1"):
            trace_exact_original_virgin_save_gate(bytes(_fixture()))
        with self.assertRaises(OriginalVirginSaveGateError):
            inspect_original_virgin_save_failure(b"\x7fELF")


if __name__ == "__main__":
    unittest.main()
