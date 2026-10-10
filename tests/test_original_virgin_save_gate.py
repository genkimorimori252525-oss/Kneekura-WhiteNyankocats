"""Synthetic (not original APK or player SAVE) regressions for virgin read failure."""
import struct
import unittest

from tools.base_mod.trace_original_virgin_save_gate import (
    FIRST_BOOT_ANCHORS, DIRECT_BL, CONDITIONAL_BRANCHES,
    OriginalVirginSaveGateError, WRITER_TARGET, _bl_target, _cond_target,
    inspect_original_virgin_save_failure, trace_exact_original_virgin_save_gate,
    ONCREATE_STATUS_ANCHORS, ONCREATE_RELOCATIONS, ONCREATE_RTTI,
    ONCREATE_RELA_START, ONCREATE_RELA_STEP,
    inspect_original_oncreate_save_status_callback,
)


def _fixture():
    image = bytearray(max(FIRST_BOOT_ANCHORS) + 4)
    for pc, opcode in FIRST_BOOT_ANCHORS.items():
        struct.pack_into("<I", image, pc, opcode)
    image[0x191955:0x19195F] = b"SAVE_DATA\x00"
    image[0x1A47F8:0x1A4805] = b"Map_Name.csv\x00"
    image[0x193AA0:0x193AAD] = b"Matatabi.tsv\x00"
    return image


def _oncreate_status_fixture():
    image = _fixture()
    # The typed lambda is later in .text than the legacy worker-fixture end.
    target_size = max(ONCREATE_STATUS_ANCHORS) + 4
    if len(image) < target_size:
        image.extend(bytes(target_size - len(image)))
    for pc, opcode in ONCREATE_STATUS_ANCHORS.items():
        struct.pack_into("<I", image, pc, opcode)
    for pc, literal in ONCREATE_RTTI.items():
        image[pc:pc + len(literal)] = literal
    for i, (slot, value) in enumerate(ONCREATE_RELOCATIONS.items()):
        struct.pack_into(
            "<QQq", image, ONCREATE_RELA_START + i * ONCREATE_RELA_STEP,
            slot, 0x403, value,
        )
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

    def test_oncreate_savedata_status_callback_routes_to_original_application(self):
        image = _oncreate_status_fixture()
        unchanged = bytes(image)
        report = inspect_original_oncreate_save_status_callback(unchanged)
        self.assertEqual(
            report["status"],
            "ORIGINAL_ONCREATE_SAVEDATA_STATUS_LAMBDA_AND_PRELOAD_RAM_RESET_STATIC",
        )
        self.assertIn("onCreate_loadSaveData", report["status_callback_name"])
        self.assertIn("aGameServices::Status", report["status_callback_type"])
        self.assertIn("0xb0bca8", report["lambda_original_registration"])
        self.assertIn("0x724544", report["app_virtual_method_target"])
        self.assertEqual(report["bounded_lambda_direct_SAVE_writer_calls"], [])
        self.assertTrue(report["oncreate_status_callback_is_not_proven_native_new_player_writer"])
        self.assertFalse(report["actual_game_services_status_or_network_requirement_verified"])
        self.assertFalse(report["original_native_game_local_first_boot_reboot_or_Lv60_passed"])
        self.assertEqual(bytes(image), unchanged)

    def test_worker_seeds_ram_BEFORE_missing_original_SAVE_failure(self):
        receipt = inspect_original_oncreate_save_status_callback(
            bytes(_oncreate_status_fixture())
        )
        self.assertIn("0x492b98 -> 0x719044", receipt["native_worker_initializes_RAM_first"])
        self.assertIn("0x492be8 -> 0x9bb764", receipt["native_worker_loads_existing_SAVE_second"])
        self.assertIn("0x492bec TBZ", receipt["native_worker_missing_save_still_fails"])
        self.assertTrue(receipt["state_zero_defaults_are_not_durable_new_profile"])
        self.assertFalse(receipt["other_valid_original_virgin_creation_path_excluded"])

    def test_oncreate_callback_vtable_lambda_and_ram_reset_instruction_drift(self):
        origin = _oncreate_status_fixture()
        for pc in (
            0x3175EC, 0x9C80E4, 0x9C8120, 0x9C8168,
            0x9C82A0, 0x9C82A4, 0x9C82B4, 0x9C82C4,
            0x9C82D0, 0x9C9BC0, 0x9C9BC8, 0x9C9BD0,
            0x492B98, 0x492BE8, 0x492BEC, 0x492D2C,
        ):
            with self.subTest(pc=hex(pc)):
                damaged = bytearray(origin)
                damaged[pc] ^= 1
                with self.assertRaises(OriginalVirginSaveGateError):
                    inspect_original_oncreate_save_status_callback(bytes(damaged))

    def test_oncreate_callback_type_and_vtable_relocation_drift_refused(self):
        origin = _oncreate_status_fixture()
        for pc in ONCREATE_RTTI:
            with self.subTest(rtti=hex(pc)):
                damaged = bytearray(origin)
                damaged[pc] ^= 1
                with self.assertRaises(OriginalVirginSaveGateError):
                    inspect_original_oncreate_save_status_callback(bytes(damaged))
        for i in range(len(ONCREATE_RELOCATIONS)):
            with self.subTest(relocation=i):
                damaged = bytearray(origin)
                damaged[ONCREATE_RELA_START + i * ONCREATE_RELA_STEP + 16] ^= 1
                with self.assertRaises(OriginalVirginSaveGateError):
                    inspect_original_oncreate_save_status_callback(bytes(damaged))
        # A second relocation to the same slot MUST NOT silently win.
        changed = bytearray(origin)
        first, target = next(iter(ONCREATE_RELOCATIONS.items()))
        struct.pack_into("<QQq", changed,
                         ONCREATE_RELA_START +
                         len(ONCREATE_RELOCATIONS) * ONCREATE_RELA_STEP,
                         first, 0x403, target)
        with self.assertRaises(OriginalVirginSaveGateError):
            inspect_original_oncreate_save_status_callback(bytes(changed))

    def test_only_exact_owner_native_hash_is_authorized(self):
        with self.assertRaisesRegex(OriginalVirginSaveGateError, "exact JP15.7.1"):
            trace_exact_original_virgin_save_gate(bytes(_fixture()))
        with self.assertRaises(OriginalVirginSaveGateError):
            inspect_original_virgin_save_failure(b"\x7fELF")


if __name__ == "__main__":
    unittest.main()
