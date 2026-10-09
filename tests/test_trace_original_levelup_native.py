"""The original-game upgrade entry-point survey must be exact-binary/read-only.

Tiny hand-built AArch64 instructions test the ADRP/ADD analyzer without
committing the owner's private 11 MiB original JP libnative-lib.so.
"""
from __future__ import annotations

import struct
import unittest

from tools.base_mod.trace_original_levelup_native import (
    CUES, EXPECTED_ANCHORS, NATIVE_SHA256, ORIGINAL_UNIT_DATA_ANCHORS,
    ORIGINAL_UNIT_DATA_BOOT_ANCHORS, ORIGINAL_UNIT_SOURCE_STRINGS,
    ORIGINAL_EFFECTIVE_CAP_GETTER_ANCHORS, ORIGINAL_CAP_GETTER_LEVEL_LABEL,
    ORIGINAL_UPGRADE_PURCHASE_ANCHORS,
    ORIGINAL_NATIVE_SAVE_SERIALIZATION_ANCHORS,
    ORIGINAL_NATIVE_SAVE_RESTORE_ANCHORS,
    ORIGINAL_CAP_INCREMENT_ITEM_TRANSACTION_ANCHORS,
    ORIGINAL_XP_TO_SAVE_DISPATCH_ANCHORS,
    ORIGINAL_SAVE_JNI_FILE_ROOT_ANCHORS,
    ORIGINAL_MISSING_SAVE_ANCHORS,
    ORIGINAL_SAVE_READ_WORKER_ANCHORS,
    LevelUpNativeTraceError,
    _original_unit_data_loader, _original_effective_level_cap_getter,
    _original_upgrade_purchase_flow, _original_save_data_serialization,
    _original_save_restore_flow, _original_cap_increment_item_transaction,
    _original_normal_xp_purchase_save_routes,
    _original_save_jni_files_root, _original_missing_save_read_path,
    _original_save_read_worker,
    _original_arm64_cfg_successors, _original_arm64_cfg_witness,
    _original_arm64_cfg_all_direct_paths_hit_save,
    _levelmax_popup_branch,
    _popup_value_call_chain,
    direct_adrp_add_refs, trace_exact_native,
)


def put_direct_ref(blob: bytearray, *, pc: int, target: int, reg: int = 8):
    diff = (target & ~0xFFF) - (pc & ~0xFFF)
    assert diff % 4096 == 0
    imm = (diff // 4096) & 0x1FFFFF
    adrp = 0x90000000 | ((imm & 3) << 29) | (((imm >> 2) & 0x7FFFF) << 5) | reg
    add = 0x91000000 | ((target & 0xFFF) << 10) | (reg << 5) | reg
    struct.pack_into("<II", blob, pc, adrp, add)


def _synthetic_loader_fixture() -> bytearray:
    # Source-only tiny AArch64 instructions + three filenames, no original assets.
    payload = bytearray(0x9C59AC)
    for source, address in ORIGINAL_UNIT_SOURCE_STRINGS.items():
        encoded = source.encode("ascii") + b"\x00"
        payload[address:address + len(encoded)] = encoded
    for address, opcode in {
        **ORIGINAL_UNIT_DATA_ANCHORS,
        **ORIGINAL_UNIT_DATA_BOOT_ANCHORS,
    }.items():
        struct.pack_into("<I", payload, address, opcode)
    return payload



def _synthetic_save_restore_fixture() -> bytearray:
    # Proprietary original native binary is never copied into tests or GitHub.
    blob = bytearray(0x8BA010)
    blob[0x191955:0x19195F] = b"SAVE_DATA\x00"
    for at, opcode in ORIGINAL_NATIVE_SAVE_RESTORE_ANCHORS.items():
        struct.pack_into("<I", blob, at, opcode)
    return blob



def _synthetic_normal_xp_save_dispatch_fixture() -> bytearray:
    """Small instruction-selection fixture; NEVER copied proprietary ELF."""
    blob = bytearray(0x8B9FCC)
    # A no-op-only synthetic control-flow canvas; pinned branch words below
    # are the only real original instruction words retained as test anchors.
    for at in range(0x850000, 0x85B000, 4):
        struct.pack_into("<I", blob, at, 0xD503201F)  # ARM64 nop
    for at, opcode in ORIGINAL_XP_TO_SAVE_DISPATCH_ANCHORS.items():
        struct.pack_into("<I", blob, at, opcode)
    # The real original region between 0x8597fc and 0x859850 has game UI
    # operations; synthetic fixture uses a single B to exercise route A.
    pc, target = 0x8597FC, 0x859850
    direct_b = 0x14000000 | (((target - pc) // 4) & 0x03FFFFFF)
    struct.pack_into("<I", blob, pc, direct_b)
    return blob



def _synthetic_original_jni_file_root_fixture() -> bytearray:
    """Exact instruction words, but NEVER a redistributed original ELF."""
    payload = bytearray(0x8B4700)
    payload[0x1905A5:0x1905B1] = b"getFilesDir\x00"
    payload[0x191955:0x19195F] = b"SAVE_DATA\x00"
    for pc, opcode in ORIGINAL_SAVE_JNI_FILE_ROOT_ANCHORS.items():
        struct.pack_into("<I", payload, pc, opcode)
    return payload


class ExactOriginalNativeLevelUpTraceTests(unittest.TestCase):
    def test_decodes_real_arm64_adrp_add_page_and_register(self):
        code = bytearray(0x4000)
        put_direct_ref(code, pc=0x1000, target=0x2A55, reg=8)
        found = direct_adrp_add_refs(
            bytes(code), 0x2A55, text_start=0x1000, text_end=0x1100
        )
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["adrp_address"], "0x1000")
        self.assertEqual(found[0]["add_address"], "0x1004")
        self.assertEqual(found[0]["register"], "x8")
        self.assertEqual(
            direct_adrp_add_refs(
                bytes(code), 0x2A54, text_start=0x1000, text_end=0x1100
            ), []
        )

    def test_negative_page_offset_adrp_sign_extension(self):
        code = bytearray(0x4000)
        put_direct_ref(code, pc=0x3000, target=0x12F0, reg=1)
        self.assertEqual(
            direct_adrp_add_refs(
                bytes(code), 0x12F0, text_start=0x3000, text_end=0x3100
            )[0]["register"], "x1"
        )

    def test_adrp_add_mismatch_or_outside_text_rejected(self):
        code = bytearray(0x5000)
        put_direct_ref(code, pc=0x1000, target=0x2900, reg=3)
        self.assertEqual(
            direct_adrp_add_refs(
                bytes(code), 0x2900, text_start=0x2000, text_end=0x2100
            ), []
        )
        with self.assertRaises(LevelUpNativeTraceError):
            direct_adrp_add_refs(
                bytes(code), 0x2900, text_start=0x1001, text_end=0x1100
            )
        with self.assertRaises(LevelUpNativeTraceError):
            direct_adrp_add_refs(
                bytes(code), 0x2900, text_start=0x1000, text_end=0x5100
            )

    def test_exact_original_levelmax_popup_compare_selects_two_variants(self):
        # Requires the pinned original branch opcodes to prove only the
        # 0x4e3068 cmp w0,#1 and 0x4e306c b.ne->0x4e3238 structure.
        blob = bytearray(0x4E3240)
        struct.pack_into("<II", blob, 0x4E3068, 0x7100041F, 0x54000E61)
        branch = _levelmax_popup_branch(bytes(blob))
        self.assertEqual(branch["branch_target"], "0x4e3238")
        self.assertEqual(branch["fallthrough_label"], "drop_popup_chara_levelmax1")
        self.assertEqual(branch["branch_label"], "drop_popup_chara_levelmax2")
        self.assertFalse(branch["underlying_upgrade_limit_getter_identified"])
        blob[0x4E3068] ^= 1
        with self.assertRaises(LevelUpNativeTraceError):
            _levelmax_popup_branch(bytes(blob))

    def test_actual_popup_value_call_chain_is_not_a_sixty_level_getter(self):
        blob = bytearray(0x9CBFB0)
        struct.pack_into("<I", blob, 0x4E3060, 0x9413A3CD)
        struct.pack_into("<I", blob, 0x9CBF9C, 0x940031DF)
        for where, opcode in (
            (0x9CBFA0, 0x52986A08),
            (0x9CBFA4, 0x12003C09),
            (0x9CBFA8, 0x6B08013F),
            (0x9CBFAC, 0x1A883120),
        ):
            struct.pack_into("<I", blob, where, opcode)
        details = _popup_value_call_chain(bytes(blob))
        self.assertEqual(details["value_reader"], "0x9cbf94")
        self.assertEqual(details["decoder"], "0x9d8718")
        self.assertEqual(
            details["return_expression"],
            "min((decoded_32bit & 0xffff), 50000)",
        )
        self.assertFalse(details["original_level_cap_getter_proven"])
        struct.pack_into("<I", blob, 0x9CBFA0, 0x52986A09)
        with self.assertRaises(LevelUpNativeTraceError):
            _popup_value_call_chain(bytes(blob))


    def test_exact_unit_data_sources_are_not_mislabeled(self):
        original = _synthetic_loader_fixture()
        details = _original_unit_data_loader(bytes(original))
        self.assertEqual(
            details["source_file_order"],
            ["unitbuy.csv", "unitlevel.csv", "unitexp.csv"]
        )
        self.assertEqual(
            details["unitbuy"]["decoded_column18_ram_offset"],
            "context+0x4b0a8+asset_index*0x100"
        )
        self.assertEqual(details["unitbuy"]["source_field_count_per_cat"], 63)
        self.assertEqual(details["unitbuy"]["row_stride_bytes"], 256)
        self.assertEqual(details["unitlevel"]["column18_parser_call"], "0x8a2eb4")
        self.assertEqual(details["unitlevel"]["column18_ram_offset"],
                         "context+0x44fd0c+asset_index*0x50")
        self.assertEqual(details["unitexp"]["column18_parser_call"], "0x8a3060")
        self.assertEqual(details["unitexp"]["column18_ram_offset"],
                         "context+0x4610ac+asset_index*0x50")
        self.assertEqual(details["unitbuy"]["row_count"], 882)
        self.assertEqual(details["unitlevel"]["row_count"], 882)
        self.assertFalse(details["levelup_ui_getter_identified"])
        self.assertFalse(details["upgrade_purchase_or_xp_debit_identified"])
        self.assertFalse(details["safe_original_game_patch_attached"])

    def test_original_data_loader_rejects_wrong_field_store(self):
        blob = _synthetic_loader_fixture()
        blob[0x8A2EB8] ^= 1
        with self.assertRaisesRegex(LevelUpNativeTraceError, "opcode drifted"):
            _original_unit_data_loader(bytes(blob))
        blob = _synthetic_loader_fixture()
        blob[0x8A2CF0] ^= 1
        with self.assertRaisesRegex(LevelUpNativeTraceError, "opcode drifted"):
            _original_unit_data_loader(bytes(blob))

    def test_original_loader_rejects_mismatched_filenames_and_boot_entry(self):
        blob = _synthetic_loader_fixture()
        blob[0x19294E] = ord("x")
        with self.assertRaisesRegex(LevelUpNativeTraceError, "unitlevel.csv.*drifted"):
            _original_unit_data_loader(bytes(blob))
        blob = _synthetic_loader_fixture()
        blob[0x1AB9A3] = ord("x")
        with self.assertRaisesRegex(LevelUpNativeTraceError, "unitbuy.csv.*drifted"):
            _original_unit_data_loader(bytes(blob))
        blob = _synthetic_loader_fixture()
        blob[0x9C598C] ^= 1
        with self.assertRaisesRegex(LevelUpNativeTraceError, "startup callsite drifted"):
            _original_unit_data_loader(bytes(blob))

    def test_original_native_cap_getter_is_real_col18_plus_save_min_col50(self):
        # Keep owner original source private. Synthetic pinned native instruction
        # fixture proves the exact getter, saved high16, hard cap and UI caller.
        blob = bytearray(0x821918)
        where, level = ORIGINAL_CAP_GETTER_LEVEL_LABEL
        blob[where:where + len(level)] = level
        for address, opcode in ORIGINAL_EFFECTIVE_CAP_GETTER_ANCHORS.items():
            struct.pack_into("<I", blob, address, opcode)
        actual = _original_effective_level_cap_getter(bytes(blob))
        self.assertEqual(actual["getter_entry"], "0x53b2bc")
        self.assertEqual(
            actual["formula"],
            "min(unitbuy_col18 + decoded_saved_base_increment, unitbuy_col50)"
        )
        self.assertEqual(actual["saved_increment_read"],
                         "0x53b330 -> 0x9cc024 (decoded upper 16 bits)")
        self.assertEqual(actual["min_function"], "0x53b3ac -> 0x349c94")
        self.assertEqual(actual["verified_original_caller"],
                         "0x821904 -> 0x53b2bc")
        self.assertFalse(actual["upgrade_button_purchase_caller_identified"])
        self.assertFalse(actual["xp_or_catseye_debit_identified"])
        self.assertFalse(actual["original_game_zero_egress_local_save_attached"])

    def test_native_cap_getter_rejects_wrong_min_and_csv_offset(self):
        original = bytearray(0x821918)
        where, level = ORIGINAL_CAP_GETTER_LEVEL_LABEL
        original[where:where + len(level)] = level
        for pc, opcode in ORIGINAL_EFFECTIVE_CAP_GETTER_ANCHORS.items():
            struct.pack_into("<I", original, pc, opcode)
        for drift in (0x53B2F0, 0x53B328, 0x53B3AC, 0x349C98, 0x821904):
            blob = bytearray(original)
            blob[drift] ^= 1
            with self.assertRaisesRegex(LevelUpNativeTraceError,
                                         "getter opcode drifted"):
                _original_effective_level_cap_getter(bytes(blob))
        original[where] = ord("x")
        with self.assertRaisesRegex(LevelUpNativeTraceError,
                                     "level UI label string drifted"):
            _original_effective_level_cap_getter(bytes(original))

    def test_original_purchase_checks_cap_then_debits_xp_and_adds_current_level(self):
        # Real addresses and instruction words only; original proprietary
        # libnative-lib.so, SAVE_DATA and assets stay outside GitHub.
        blob = bytearray(0x85DB84)
        for at, opcode in ORIGINAL_UPGRADE_PURCHASE_ANCHORS.items():
            struct.pack_into("<I", blob, at, opcode)
        flow = _original_upgrade_purchase_flow(bytes(blob))
        self.assertEqual(flow["cap_eligibility_predicate"],
                         "0x8581fc -> 0x53be0c")
        self.assertEqual(flow["cannot_upgrade_branch"],
                         "0x858200 TBZ -> 0x85904c")
        self.assertEqual(flow["max_cap_increment_record"],
                         "context+0x3ad80c+asset_index*8")
        self.assertEqual(flow["current_level_record"],
                         "context+0x47ba4+asset_index*8")
        self.assertEqual(flow["xp_wallet_record"], "context+0xc3b8")
        self.assertEqual(flow["xp_debit"],
                         "0x858390 -> 0x9d86e4; new_xp=old_xp-cost")
        self.assertEqual(flow["xp_affordability_branch"],
                         "0x85837c B.LT -> 0x8594c0")
        self.assertEqual(flow["current_level_increment"],
                         "0x8583b8 -> 0x9cc04c; upper16 current base+1")
        self.assertFalse(flow["save_writer_proven"])
        self.assertFalse(flow["cats_eye_consume_proven"])
        self.assertFalse(flow["native_purchase_patch_attached"])
        self.assertFalse(flow["original_device_upgrade_passed"])

    def test_original_purchase_rejects_wrong_cap_xp_or_current_level_store(self):
        clean = bytearray(0x85DB84)
        for at, opcode in ORIGINAL_UPGRADE_PURCHASE_ANCHORS.items():
            struct.pack_into("<I", clean, at, opcode)
        for address in (0x53BE44, 0x53BEA4, 0x53BF08,
                        0x8581FC, 0x858200, 0x85837C,
                        0x858390, 0x8583B8, 0x85DB80):
            broken = bytearray(clean)
            broken[address] ^= 1
            with self.subTest(address=hex(address)):
                with self.assertRaisesRegex(
                    LevelUpNativeTraceError, "purchase opcode drifted"
                ):
                    _original_upgrade_purchase_flow(bytes(broken))

    def test_original_save_data_serializer_includes_xp_current_levels_and_cap_increments(self):
        # Original runtime field sources pinned from the same owner native ELF;
        # owner SAVE_DATA and binary remain private.
        blob = bytearray(0x8BA044)
        blob[0x191955:0x19195F] = b"SAVE_DATA\x00"
        for pc, opcode in ORIGINAL_NATIVE_SAVE_SERIALIZATION_ANCHORS.items():
            struct.pack_into("<I", blob, pc, opcode)
        result = _original_save_data_serialization(bytes(blob))
        self.assertEqual(result["native_save_wrapper"], "0x8b9fc8 -> 0x8b46b0")
        self.assertEqual(result["xp_wallet_decoded"],
                         "0x8b48c8: context+0xc3b8")
        self.assertIn("882 records", result["current_level_table"])
        self.assertIn("882 records", result["max_upgrade_table"])
        self.assertEqual(result["ui_side_save_wrapper_caller"],
                         "0x8593e0 -> 0x8b9fc8")
        self.assertFalse(result["ui_side_caller_directly_post_purchase_verified"])
        self.assertFalse(result["disk_save_flush_completed_verified"])
        self.assertFalse(result["save_reboot_reload_verified"])
        self.assertFalse(result["independent_offline_local_authority_integrated"])

    def test_original_serializer_rejects_wrong_xp_level_cap_or_save_name(self):
        valid = bytearray(0x8BA044)
        valid[0x191955:0x19195F] = b"SAVE_DATA\x00"
        for pc, opcode in ORIGINAL_NATIVE_SAVE_SERIALIZATION_ANCHORS.items():
            struct.pack_into("<I", valid, pc, opcode)
        for pc in (0x8BA008, 0x8B48C0, 0x8B48D4,
                   0x8B4E30, 0x8B4E44, 0x8B4E50,
                   0x8B6304, 0x8B6318, 0x8B6324):
            with self.subTest(address=hex(pc)):
                broken = bytearray(valid)
                broken[pc] ^= 1
                with self.assertRaisesRegex(LevelUpNativeTraceError,
                                             "serializer opcode drifted"):
                    _original_save_data_serialization(bytes(broken))
        valid[0x191955] = ord("x")
        with self.assertRaisesRegex(LevelUpNativeTraceError,
                                     "bounds/name drifted"):
            _original_save_data_serialization(bytes(valid))

    def test_native_original_save_restore_xp_current_and_cap_rows(self):
        evidence = _original_save_restore_flow(
            bytes(_synthetic_save_restore_fixture())
        )
        self.assertEqual(evidence["read_entry"], "0x8b43a4")
        self.assertEqual(evidence["deserialize_game_context"],
                         "0x8b44ac -> 0x8a669c")
        self.assertEqual(evidence["writer_open"],
                         "0x8b46fc -> 0x35e410")
        self.assertIn("0x8a69f8", evidence["restore_xp"])
        self.assertIn("context+0x47ba4+cat*8",
                      evidence["restore_current_levels"])
        self.assertIn("context+0x3ad80c+cat*8",
                      evidence["restore_max_cap_increments"])
        self.assertFalse(evidence["durable_fsync_or_atomic_commit_proven"])
        self.assertFalse(evidence["successful_purchase_triggers_save_proven"])
        self.assertFalse(evidence["network_independent_fresh_game_profile_proven"])
        self.assertFalse(evidence["safe_original_native_game_patch_attached"])

    def test_native_restore_distinguishes_read_and_write_failures(self):
        clean = _synthetic_save_restore_fixture()
        for pc in (0x8B4404, 0x8B441C, 0x8B4444, 0x8B4448,
                   0x8B44AC, 0x8A69EC, 0x8A69F8,
                   0x8A91E4, 0x8A920C, 0x8A921C, 0x8A9230,
                   0x8AD14C, 0x8AD174, 0x8AD180, 0x8AD194,
                   0x8B46FC, 0x8B4700, 0x8B97E8):
            with self.subTest(site=hex(pc)):
                broken = bytearray(clean)
                broken[pc] ^= 1
                with self.assertRaisesRegex(
                        LevelUpNativeTraceError,
                        "original save restore native opcode drifted"):
                    _original_save_restore_flow(bytes(broken))
        wrong_name = bytearray(clean)
        wrong_name[0x191955] = ord("x")
        with self.assertRaisesRegex(LevelUpNativeTraceError, "bounds/name"):
            _original_save_restore_flow(bytes(wrong_name))

    def test_original_cap_increment_debits_material_before_saving(self):
        blob = bytearray(0x85DC2C)
        for at, word in ORIGINAL_CAP_INCREMENT_ITEM_TRANSACTION_ANCHORS.items():
            struct.pack_into("<I", blob, at, word)
        data = _original_cap_increment_item_transaction(bytes(blob))
        self.assertEqual(
            data["max_upgrade_increment"],
            "0x85db78 +1; 0x85db80 -> 0x9cc04c, per cat context+0x3ad80c+cat*8"
        )
        self.assertIn("neg required", data["negative_material_delta"])
        self.assertIn("0x85dc28 -> 0x5eed58", data["debit_loop"])
        self.assertEqual(data["save_called_after_increment"], "0x85db88 -> 0x8b9fc8")
        self.assertFalse(data["original_catseye_material_subtypes_verified"])
        self.assertFalse(data["original_save_file_fsync_and_restart_proven"])
        self.assertFalse(data["offline_independent_game_integrated"])

    def test_cap_increment_save_and_resource_drift_is_rejected(self):
        source = bytearray(0x85DC2C)
        for at, opcode in ORIGINAL_CAP_INCREMENT_ITEM_TRANSACTION_ANCHORS.items():
            struct.pack_into("<I", source, at, opcode)
        for at in (0x85DA04, 0x85DA14, 0x85DA1C, 0x85DABC,
                   0x85DAC4, 0x85DB50, 0x85DB78, 0x85DB80,
                   0x85DB88, 0x85DC1C, 0x85DC28):
            trial = bytearray(source)
            trial[at] ^= 1
            with self.subTest(address=hex(at)):
                with self.assertRaisesRegex(
                    LevelUpNativeTraceError, "transaction opcode drifted"
                ):
                    _original_cap_increment_item_transaction(bytes(trial))

    def test_original_normal_xp_purchase_conditional_routes_reach_real_saver(self):
        fixture = _synthetic_normal_xp_save_dispatch_fixture()
        flow = _original_normal_xp_purchase_save_routes(bytes(fixture))
        self.assertEqual(flow["source_xp_debit"], "0x858390 -> 0x9d86e4")
        self.assertEqual(flow["native_current_level_increment"],
                         "0x8583b8 -> 0x9cc04c")
        self.assertTrue(flow["xp_debit_reaches_level_increment"])
        self.assertEqual(set(flow["conditional_save_routes"]),
                         {"0x859a40", "0x85a748"})
        for site in ("0x859a40", "0x85a748"):
            self.assertEqual(
                flow["conditional_save_routes"][site]["original_save_target"],
                "0x8b9fc8"
            )
        self.assertFalse(flow["all_successful_upgrade_paths_save_proven"])
        self.assertFalse(flow["runtime_branch_values_or_reachability_proven"])
        self.assertFalse(flow["original_disk_durable_flush_proven"])
        self.assertFalse(flow["fresh_independent_zero_network_save_connected"])
        self.assertFalse(flow["original_game_lv60_screen_and_reboot_verified"])

    def test_original_normal_xp_save_route_opcode_or_path_drift_fails_closed(self):
        baseline = _synthetic_normal_xp_save_dispatch_fixture()
        for at in (0x858390, 0x8583B8, 0x858450,
                   0x858534, 0x859994, 0x859A40, 0x85A748):
            trial = bytearray(baseline)
            trial[at] ^= 1
            with self.subTest(opcode=hex(at)):
                with self.assertRaisesRegex(
                    LevelUpNativeTraceError, "branch opcode drifted"
                ):
                    _original_normal_xp_purchase_save_routes(bytes(trial))
        path_corrupted = bytearray(baseline)
        struct.pack_into("<I", path_corrupted, 0x8597FC, 0xD65F03C0)  # ret
        with self.assertRaisesRegex(LevelUpNativeTraceError,
                                     "conditional route drifted"):
            _original_normal_xp_purchase_save_routes(bytes(path_corrupted))

    def test_original_bounded_cfg_has_no_fabricated_edges(self):
        fixture = bytes(_synthetic_normal_xp_save_dispatch_fixture())
        self.assertEqual(_original_arm64_cfg_successors(fixture, 0x858450),
                         (0x8584E0, 0x858454))
        self.assertEqual(_original_arm64_cfg_successors(fixture, 0x859994),
                         (0x85A730, 0x859998))
        self.assertEqual(_original_arm64_cfg_successors(fixture, 0x859A40),
                         (0x859A44,))
        self.assertEqual(
            _original_arm64_cfg_witness(
                fixture, 0x850000, 0x85B000, 0x8583B8, 0x859A40
            )[-1], 0x859A40
        )
        with self.assertRaises(LevelUpNativeTraceError):
            _original_arm64_cfg_witness(
                fixture, 0x850001, 0x85B000, 0x8583B8, 0x859A40
            )
        # UDF/RET cannot be invented as branches.
        blank = bytearray(0x100)
        struct.pack_into("<I", blank, 0x40, 0xD65F03C0)
        self.assertEqual(
            _original_arm64_cfg_witness(bytes(blank), 0, 0x100,
                                        0x40, 0x80), []
        )

    def test_original_direct_cfg_checks_all_paths_through_saver(self):
        # Tiny synthetic AArch64 program with two conditional exits and
        # two explicit save callsite gates; no proprietary code included.
        blob = bytearray(0x200)
        struct.pack_into("<I", blob, 0x100, 0x54000100)  # b.eq +0x20
        struct.pack_into("<I", blob, 0x104, 0x1400000B)  # b -> 0x130
        struct.pack_into("<I", blob, 0x120, 0x14000005)  # b -> 0x134
        struct.pack_into("<I", blob, 0x130, 0x94000000)  # modeled save BL
        struct.pack_into("<I", blob, 0x134, 0x94000000)  # alternate save BL
        actual = _original_arm64_cfg_all_direct_paths_hit_save(
            bytes(blob), 0x100, 0x180, 0x100, frozenset({0x130, 0x134})
        )
        self.assertEqual(actual["save_calls"], ["0x130", "0x134"])
        self.assertEqual(actual["reachable_nodes"], 5)
        self.assertEqual(actual["non_save_nodes"], 3)
        self.assertTrue(actual["conditional_static_direct_paths_hit_a_saver"])
        self.assertFalse(actual["real_runtime_guaranteed_save"])
        self.assertFalse(actual["durable_disk_fsync_verified"])

    def test_original_save_gate_fails_on_unsaved_exit_cycle_or_out_of_range(self):
        source = bytearray(0x200)
        struct.pack_into("<I", source, 0x100, 0x54000100)
        struct.pack_into("<I", source, 0x104, 0x1400000B)
        struct.pack_into("<I", source, 0x120, 0x14000005)
        struct.pack_into("<I", source, 0x130, 0x94000000)
        struct.pack_into("<I", source, 0x134, 0x94000000)
        for opcode, expected in (
            (0xD65F03C0, "terminates before SAVE_DATA"),
            (0x14000000, "reachable cycle before SAVE_DATA"),
            (0x1400007F, "escapes save-gate range"),
        ):
            broken = bytearray(source)
            struct.pack_into("<I", broken, 0x104, opcode)
            with self.subTest(opcode=hex(opcode)):
                with self.assertRaisesRegex(LevelUpNativeTraceError, expected):
                    _original_arm64_cfg_all_direct_paths_hit_save(
                        bytes(broken), 0x100, 0x180, 0x100,
                        frozenset({0x130, 0x134})
                    )


    def test_original_save_reader_and_writer_use_same_android_jni_files_root(self):
        result = _original_save_jni_files_root(
            bytes(_synthetic_original_jni_file_root_fixture())
        )
        self.assertEqual(
            result["status"],
            "ORIGINAL_SAVE_DATA_READ_AND_WRITE_SHARE_ANDROID_FILES_DIR_JNI",
        )
        self.assertEqual(result["same_file_root_thunk"], "0x42cde8")
        self.assertIn("0x35d6b0 -> 0x42cde8", result["save_reader_path"])
        self.assertIn("0x35e510 -> 0x42cde8", result["save_writer_path"])
        self.assertEqual(result["jni_method_name"], "getFilesDir")
        self.assertEqual(result["filename_combiner_read"],
                         "0x35d6c0 -> 0x31a104")
        self.assertEqual(result["filename_combiner_write"],
                         "0x35e520 -> 0x31a104")
        self.assertFalse(result["actual_original_host_java_subclass_invocation_proven"])
        self.assertFalse(result["original_native_save_under_isolated_root_device_tested"])
        self.assertFalse(result["fresh_independent_player_authority_integrated"])
        self.assertFalse(result["full_zero_network_first_boot_proven"])
        self.assertFalse(result["original_lv60_purchase_reboot_proven"])

    def test_original_save_jni_chain_rejects_drift_or_incorrect_root(self):
        original = _synthetic_original_jni_file_root_fixture()
        for pc in (0x8B4404, 0x8B46FC, 0x35D6B0,
                   0x35E510, 0x35D6C0, 0x35E520,
                   0x42CDE8, 0x45AA3C, 0x45AA40):
            broken = bytearray(original)
            broken[pc] ^= 1
            with self.subTest(pc=hex(pc)):
                with self.assertRaises(LevelUpNativeTraceError):
                    _original_save_jni_files_root(bytes(broken))
        for literal in (0x1905A5, 0x191955):
            broken = bytearray(original)
            broken[literal] ^= 1
            with self.subTest(literal=hex(literal)):
                with self.assertRaises(LevelUpNativeTraceError):
                    _original_save_jni_files_root(bytes(broken))

    def test_original_no_SAVE_DATA_load_fails_and_does_not_fake_new_game(self):
        fake = bytearray(0x9BBA70)
        for at, opcode in ORIGINAL_MISSING_SAVE_ANCHORS.items():
            struct.pack_into("<I", fake, at, opcode)
        result = _original_missing_save_read_path(bytes(fake))
        self.assertEqual(result["startup_read"], "0x9bb78c -> 0x8b43a4")
        self.assertEqual(result["reader_returns_zero"], "0x8b453c w20=0")
        self.assertFalse(result["fresh_profile_native_save_initialized"])
        self.assertFalse(result["original_offline_first_boot_tested"])
        self.assertFalse(result["new_game_creation_in_other_function_excluded"])

    def test_original_empty_save_loader_rejects_branch_and_return_drift(self):
        fake = bytearray(0x9BBA70)
        for at, opcode in ORIGINAL_MISSING_SAVE_ANCHORS.items():
            struct.pack_into("<I", fake, at, opcode)
        for address in (0x8B441C, 0x8B4528, 0x8B452C,
                        0x8B453C, 0x9BB78C, 0x9BB794, 0x9BBA54):
            with self.subTest(at=hex(address)):
                edited = bytearray(fake)
                edited[address] ^= 1
                with self.assertRaises(LevelUpNativeTraceError):
                    _original_missing_save_read_path(bytes(edited))

    def test_original_save_read_is_in_async_worker_not_proven_first_boot(self):
        # Stub contains only exact instruction words, no private native bytes.
        stub = bytearray(0x49320C)
        for pc, opcode in ORIGINAL_SAVE_READ_WORKER_ANCHORS.items():
            struct.pack_into("<I", stub, pc, opcode)
        result = _original_save_read_worker(bytes(stub))
        self.assertEqual(result["worker_thread_entry"], "0x493200 -> 0x492b80")
        self.assertEqual(result["native_loader"], "0x492be8 -> 0x9bb764 -> 0x8b43a4")
        self.assertEqual(result["missing_save_status_branch"],
                         "0x492bec TBZ -> 0x492d28")
        self.assertEqual(result["success_flag"],
                         "0x492d20 STRB [worker_state+8]")
        self.assertEqual(result["failure_flag"],
                         "0x492d28 sets 1; 0x492d2c STRB [worker_state+9]")
        self.assertFalse(result["actual_app_first_launch_calls_this_worker_proven"])
        self.assertFalse(result["missing_SAVE_is_absence_of_new_game_generator_proven"])
        self.assertFalse(result["original_native_new_player_initializer_found"])

    def test_original_save_worker_error_branches_and_flags_reject_drift(self):
        template = bytearray(0x49320C)
        for pc, opcode in ORIGINAL_SAVE_READ_WORKER_ANCHORS.items():
            struct.pack_into("<I", template, pc, opcode)
        for pc in (0x492BE8, 0x492BEC, 0x492C6C, 0x492C70,
                   0x492D20, 0x492D28, 0x492D2C,
                   0x492DF0, 0x493200, 0x493208):
            broken = bytearray(template)
            broken[pc] ^= 1
            with self.subTest(where=hex(pc)):
                with self.assertRaises(LevelUpNativeTraceError):
                    _original_save_read_worker(bytes(broken))

    def test_real_game_original_upgrader_cues_are_not_fabricated_hooks(self):
        self.assertEqual(len(NATIVE_SHA256), 64)
        self.assertEqual(
            EXPECTED_ANCHORS["unit_data_file"], {0x8A2C60}
        )
        self.assertEqual(
            EXPECTED_ANCHORS["max_level_popup_first"], {0x4E3070}
        )
        self.assertEqual(
            EXPECTED_ANCHORS["max_level_popup_second"], {0x4E3238}
        )
        self.assertEqual(
            EXPECTED_ANCHORS["catseye_screen_resource"], {0x942B64}
        )
        self.assertEqual(CUES["unit_data_file"], "unitbuy.csv")
        self.assertEqual(CUES["native_activity_files_dir"], "getFilesDir")
        self.assertEqual(EXPECTED_ANCHORS["native_activity_files_dir"], {0x45AA3C})
        self.assertEqual(CUES["original_save_file"], "SAVE_DATA")
        self.assertEqual(
            EXPECTED_ANCHORS["original_save_file"],
            {0x71C984, 0x74B13C, 0x8B43D0, 0x8B9FDC, 0x8C5334},
        )
        self.assertEqual(
            EXPECTED_ANCHORS["original_save4_file"],
            {0x7EDD54, 0x8BA0B0, 0x8C1D30},
        )
        self.assertEqual(
            EXPECTED_ANCHORS["original_save8_file"],
            {0x748E00, 0x74AD74, 0x74AF48},
        )
        with self.assertRaisesRegex(
            LevelUpNativeTraceError, "exact JP15.7.1 native hash"
        ):
            trace_exact_native(b"not an original game library")

if __name__ == "__main__":
    unittest.main()
