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
    ORIGINAL_WORKER_STATUS_VTABLE, ORIGINAL_WORKER_STATUS_ANCHORS,
    ORIGINAL_APP_LAUNCH_SCENE_ANCHORS,
    ORIGINAL_APP_LAUNCH_RESULT_ANCHORS,
    ORIGINAL_APP_LAUNCH_TARGET_SCENE_ENTRY_ANCHORS,
    ORIGINAL_SCENE97_DOWNLOAD_BATCH_ANCHORS,
    ORIGINAL_DOWNLOAD_TSV_FILE_RESOLVER_ANCHORS,
    ORIGINAL_RESOURCE_REGISTRY_NATIVE_ANCHORS,
    ORIGINAL_SERVER_FAMILY_CATALOG_ANCHORS,
    ORIGINAL_RESOURCE_TABLE_LOAD_INIT_ARRAY_ANCHORS,
    ORIGINAL_INIT_ARRAY_RELOCATION_SLOT,
    ORIGINAL_INIT_ARRAY_SOURCE_START,
    ORIGINAL_INIT_ARRAY_FILE_OFFSET,
    JP15_7_1_ORIGINAL_LOCAL_LIST_COUNTS,
    ORIGINAL_SCENE97_DOWNLOAD_BATCH_RELOCS, ORIGINAL_DOWNLOAD_BATCH_RTTI,
    ORIGINAL_RELA_DYN_OFFSET, ORIGINAL_RELA_DYN_COUNT,
    ORIGINAL_RELA_DYN_ENTRY_SIZE,
    LevelUpNativeTraceError,
    _original_unit_data_loader, _original_effective_level_cap_getter,
    _original_upgrade_purchase_flow, _original_save_data_serialization,
    _original_save_restore_flow, _original_cap_increment_item_transaction,
    _original_normal_xp_purchase_save_routes,
    _original_save_jni_files_root, _original_missing_save_read_path,
    _original_save_read_worker, _original_save_worker_virtual_status,
    _original_app_launch_scene_from_save_presence,
    _original_app_launch_result_scene_dispatch,
    _original_app_launch_target_scene_entries,
    _original_scene97_download_batch_task,
    _original_download_tsv_file_source_resolver,
    _original_download_tsv_resource_registration_chain,
    _original_registered_server_family_catalog,
    _original_server_registry_constructor_initialized_on_load,
    _original_download_batch_tsv_installed_local_coverage,
    _additional_owner_list_coverage,
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



def _synthetic_worker_status_fixture() -> bytearray:
    # Exposes no original native executable or owner player SAVE: a handful of
    # exact opcodes, plus three synthetic ELF RELATIVE relocation entries only.
    file_length = max(0x49312C, ORIGINAL_RELA_DYN_OFFSET +
                      ORIGINAL_RELA_DYN_COUNT * ORIGINAL_RELA_DYN_ENTRY_SIZE)
    data = bytearray(file_length)
    for at, opcode in ORIGINAL_WORKER_STATUS_ANCHORS.items():
        struct.pack_into("<I", data, at, opcode)
    for idx, (slot, target) in enumerate(ORIGINAL_WORKER_STATUS_VTABLE.items()):
        struct.pack_into("<QQq", data, ORIGINAL_RELA_DYN_OFFSET + idx * 24,
                         slot, 0x403, target)
    return data



def _synthetic_original_app_launch_scene_fixture() -> bytearray:
    """Synthetic ARM64 scene branch canvas with exact JP opcode anchors ONLY.

    Do not store original proprietary game function bodies or SAVE_DATA.
    """
    payload = bytearray(0x8B4530)
    payload[0x191955:0x19195F] = b"SAVE_DATA\x00"
    payload[0x1C507D:0x1C508D] = b"13AppLaunchLoad\x00"
    # The source's actual conditional absent-file witness travels 0x71c9c8
    # -> 0x71d208 -> 0x71d2e8 -> constructor at 0x71d30c. NOPs model only
    # otherwise irrelevant local cleanup. Distinct ERROR scene 4 remains UDF.
    for pc in range(0x71D208, 0x71D320, 4):
        struct.pack_into("<I", payload, pc, 0xD503201F)
    for pc, opcode in ORIGINAL_APP_LAUNCH_SCENE_ANCHORS.items():
        struct.pack_into("<I", payload, pc, opcode)
    return payload



def _synthetic_app_launch_result_fixture() -> bytearray:
    """Exact AArch64 opcodes from owner source; no proprietary native or SAVE."""
    blob = bytearray(0x723490)
    for address, opcode in ORIGINAL_APP_LAUNCH_RESULT_ANCHORS.items():
        struct.pack_into("<I", blob, address, opcode)
    return blob



def _synthetic_scene97_download_task_fixture() -> bytearray:
    """Tiny pinned opcode/RTTI+RELATIVE relocation fixture, not owner ELF."""
    size = max(
        0x73CAB4, 0x1DB616 + len(ORIGINAL_DOWNLOAD_BATCH_RTTI),
        ORIGINAL_RELA_DYN_OFFSET
        + ORIGINAL_RELA_DYN_COUNT * ORIGINAL_RELA_DYN_ENTRY_SIZE,
    )
    blob = bytearray(size)
    blob[0x1DB616:0x1DB616 + len(ORIGINAL_DOWNLOAD_BATCH_RTTI)] = (
        ORIGINAL_DOWNLOAD_BATCH_RTTI
    )
    blob[0x197B44:0x197B54] = b"download_%d.tsv\x00"
    for pc, opcode in ORIGINAL_SCENE97_DOWNLOAD_BATCH_ANCHORS.items():
        struct.pack_into("<I", blob, pc, opcode)
    for idx, (slot, dest) in enumerate(
            ORIGINAL_SCENE97_DOWNLOAD_BATCH_RELOCS.items()):
        struct.pack_into("<QQq", blob, ORIGINAL_RELA_DYN_OFFSET + idx*24,
                         slot, 0x403, dest)
    return blob



def _synthetic_tsv_source_resolver_fixture() -> bytearray:
    """Exact minimal native site opcodes, not the private owned ELF bytes."""
    payload = bytearray(0x73CAB4)
    payload[0x1A8C27:0x1A8C2B] = b"snd\x00"
    for address, opcode in ORIGINAL_DOWNLOAD_TSV_FILE_RESOLVER_ANCHORS.items():
        struct.pack_into("<I", payload, address, opcode)
    return payload



def _synthetic_original_resource_registry_fixture() -> bytearray:
    """Pinned opcodes + one synthetic relocation, NEVER original ELF assets."""
    blob = bytearray(0x741B94)
    for pc, opcode in ORIGINAL_RESOURCE_REGISTRY_NATIVE_ANCHORS.items():
        struct.pack_into("<I", blob, pc, opcode)
    struct.pack_into(
        "<QQq", blob, ORIGINAL_RELA_DYN_OFFSET,
        0xB17D78, 0x403, 0xF98D38
    )
    return blob



def _synthetic_original_server_family_catalog_fixture() -> bytearray:
    """Original opcode/string addresses, synthetic family names only."""
    blob = bytearray(0x7159C4)
    for pc, opcode in ORIGINAL_SERVER_FAMILY_CATALOG_ANCHORS.items():
        struct.pack_into("<I", blob, pc, opcode)
    blob[0x1918D1:0x1918E3] = b"XImageServer.list\x00"
    synthetic = (
        b"XImageServer.pack\x00"
        b"MNumberServer.list\x00MNumberServer.pack\x00"
        b"WImageDataServer.list\x00WImageDataServer.pack\x00"
    )
    for i in range(1, 90):
        synthetic += f"Test{i:03d}Server.list\x00".encode()
        synthetic += f"Test{i:03d}Server.pack\x00".encode()
    blob[0x1A0000:0x1A0000 + len(synthetic)] = synthetic
    return blob



def _synthetic_native_resource_ctor_init_array() -> bytearray:
    """One synthetic ELF .init_array R_RELATIVE and seven exact opcodes."""
    blob = bytearray(0xB12CC0)
    for pc, opcode in ORIGINAL_RESOURCE_TABLE_LOAD_INIT_ARRAY_ANCHORS.items():
        struct.pack_into("<I", blob, pc, opcode)
    blob[0x1918D1:0x1918E3] = b"XImageServer.list\x00"
    struct.pack_into(
        "<QQq", blob, ORIGINAL_RELA_DYN_OFFSET,
        ORIGINAL_INIT_ARRAY_RELOCATION_SLOT, 0x403, 0x714AE8,
    )
    return blob


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

    def test_original_save_worker_virtual_status_consumes_distinct_state_flags(self):
        result = _original_save_worker_virtual_status(
            bytes(_synthetic_worker_status_fixture())
        )
        self.assertEqual(
            result["vtable_entries"],
            {"0xaefb48": "0x492d40",
             "0xaefb50": "0x4930a4",
             "0xaefb58": "0x4930b8"},
        )
        self.assertIn("worker_state+8", result["status_checks_success_byte"])
        self.assertIn("worker_state+9", result["status_checks_failure_byte"])
        self.assertFalse(result["first_run_game_creation_proven"])
        self.assertFalse(result["first_launch_dispatch_reachable_proven"])

    def test_original_save_worker_virtual_status_rejects_wrong_relocations(self):
        baseline = _synthetic_worker_status_fixture()
        for opcode_pc in (0x4930D8, 0x4930FC, 0x493128):
            broken = bytearray(baseline)
            broken[opcode_pc] ^= 1
            with self.subTest(opcode=hex(opcode_pc)):
                with self.assertRaisesRegex(LevelUpNativeTraceError, "opcode drifted"):
                    _original_save_worker_virtual_status(bytes(broken))
        for index, fault in (
            (0, "wrong destination"),
            (1, "wrong relocation type"),
            (2, "duplicate slot"),
        ):
            broken = bytearray(baseline)
            at = ORIGINAL_RELA_DYN_OFFSET + index * 24
            if index == 0:
                struct.pack_into("<Q", broken, at + 16, 0x4930A4)
            elif index == 1:
                struct.pack_into("<Q", broken, at + 8, 0x402)
            else:
                struct.pack_into("<Q", broken, at, 0xAEFB50)
            with self.subTest(fault=fault):
                with self.assertRaises(LevelUpNativeTraceError):
                    _original_save_worker_virtual_status(bytes(broken))

    def test_original_scene_101_has_SAVE_DATA_probe_and_AppLaunchLoad_conditional_path(self):
        result = _original_app_launch_scene_from_save_presence(
            bytes(_synthetic_original_app_launch_scene_fixture())
        )
        self.assertEqual(result["status"],
                         "PINNED_ORIGINAL_SCENE_101_SAVE_PROBE_AND_APP_LAUNCH_LOAD")
        self.assertEqual(result["explicit_scene_101_caller"],
                         "0x7231c8 MOV w1=101; 0x7231cc BL 0x71c408")
        self.assertEqual(result["original_source_file_literal"], "SAVE_DATA (0x191955)")
        self.assertEqual(result["absent_file_branch"], "0x71c9c8 TBZ -> 0x71d208")
        self.assertEqual(result["native_AppLaunchLoad_constructor"],
                         "0x71d30c -> 0x4926f8")
        self.assertEqual(result["native_scene_ptr_record"],
                         "game_context+0x3c40b0")
        self.assertEqual(result["SAVE_read_failure_different_scene"],
                         "0x8b4528 w1=4; 0x8b452c -> 0x71c408")
        self.assertGreater(result["conditional_absent_file_witness_length"], 8)
        self.assertFalse(result["scene_101_is_obligatory_first_launch_proven"])
        self.assertFalse(result["first_run_native_player_save_initializer_found"])
        self.assertFalse(result["original_offline_first_boot_and_level60_proven"])

    def test_original_AppLaunchLoad_scene_rejects_branch_constructor_and_RTTI_drift(self):
        source = _synthetic_original_app_launch_scene_fixture()
        for pc in (0x71C5B4, 0x71C6E4, 0x71C6E8, 0x71C9A8,
                   0x71C9B0, 0x71C9C8, 0x71D264, 0x71D2DC,
                   0x71D30C, 0x71D31C, 0x492730, 0x492738,
                   0x7231C8, 0x7231CC, 0x8B4528, 0x8B452C):
            broken = bytearray(source)
            broken[pc] ^= 1
            with self.subTest(pc=hex(pc)):
                with self.assertRaises(LevelUpNativeTraceError):
                    _original_app_launch_scene_from_save_presence(bytes(broken))
        for literal in (0x191955, 0x1C507D):
            broken = bytearray(source)
            broken[literal] ^= 1
            with self.subTest(literal=hex(literal)):
                with self.assertRaises(LevelUpNativeTraceError):
                    _original_app_launch_scene_from_save_presence(bytes(broken))
        # Fail closed if expected first-hop branch target no longer exists.
        wrong_branch = bytearray(source)
        struct.pack_into("<I", wrong_branch, 0x71D220, 0xD503201F)
        with self.assertRaisesRegex(LevelUpNativeTraceError, "opcode drifted"):
            _original_app_launch_scene_from_save_presence(bytes(wrong_branch))


    def test_original_app_launch_status_selects_wait_scene4_or_success_scenes(self):
        original = bytes(_synthetic_app_launch_result_fixture())
        evidence = _original_app_launch_result_scene_dispatch(original)
        self.assertEqual(
            evidence["status"],
            "EXACT_ORIGINAL_APP_LAUNCH_LOAD_RESULT_SCENE_DISPATCH",
        )
        self.assertEqual(evidence["frame_update_entry"], "0x721854")
        self.assertIn("context+0x3c40b0", evidence["producer_scene_ptr"])
        self.assertIn("context+0x3c40b0", evidence["consumer_scene_ptr"])
        self.assertIn("0x4930b8", evidence["virtual_status_pinned_target"])
        self.assertEqual(
            evidence["status_false_branch"], "0x722b30 TBZ -> 0x723440"
        )
        self.assertEqual(
            evidence["wait_without_failure"],
            "0x723448 LDRB worker+9; 0x72344c CBZ -> 0x72299c",
        )
        self.assertIn("w1=4", evidence["error_scene"])
        self.assertIn("scene97", evidence["success_side_scene_choice"])
        self.assertIn("scene104", evidence["success_side_scene_choice"])
        self.assertEqual(
            _original_arm64_cfg_successors(original, 0x722B30),
            (0x723440, 0x722B34),
        )
        self.assertEqual(
            _original_arm64_cfg_successors(original, 0x72344C),
            (0x72299C, 0x723450),
        )
        self.assertFalse(evidence["original_first_launch_without_SAVE_verified"])
        self.assertFalse(evidence["native_first_game_account_free_initializer_found"])
        self.assertFalse(evidence["original_android_device_scene_transition_observed"])
        self.assertFalse(evidence["original_lv60_and_local_save_reboot_verified"])
        self.assertFalse(evidence["all_sdk_network_egress_zero_proven"])

    def test_original_app_launch_result_rejects_mutated_object_status_or_scene(self):
        source = _synthetic_app_launch_result_fixture()
        for address in (
            0x721878, 0x721884, 0x722B10, 0x722B14, 0x722B18,
            0x722B1C, 0x722B20, 0x722B24, 0x722B28, 0x722B2C,
            0x722B30, 0x722B6C, 0x723440, 0x723444, 0x723448,
            0x72344C, 0x723450, 0x723458, 0x72345C, 0x723460,
            0x723474, 0x723484, 0x723488, 0x72348C,
            0x71D310, 0x71D314, 0x71D31C,
        ):
            with self.subTest(address=hex(address)):
                corrupted = bytearray(source)
                corrupted[address] ^= 1
                with self.assertRaises(LevelUpNativeTraceError):
                    _original_app_launch_result_scene_dispatch(bytes(corrupted))

    def test_original_success_scene97_and_104_have_distinct_real_handlers(self):
        blob = bytearray(0x71CE84)
        for pc, opcode in ORIGINAL_APP_LAUNCH_TARGET_SCENE_ENTRY_ANCHORS.items():
            struct.pack_into("<I", blob, pc, opcode)
        report = _original_app_launch_target_scene_entries(bytes(blob))
        self.assertEqual(report["scene97_handler_calls"],
                         ["0x71ce78 -> 0x781170", "0x71ce80 -> 0x725e1c"])
        self.assertEqual(report["scene104_handler_call"], "0x71c518 -> 0x368eb8")
        self.assertFalse(report["account_free_virgin_player_creation_in_scene97_proven"])
        self.assertFalse(report["account_free_virgin_player_creation_in_scene104_proven"])
        self.assertFalse(report["original_game_player_save_created_or_reloaded"])

    def test_original_scene97_104_handler_drift_fails_closed(self):
        source = bytearray(0x71CE84)
        for pc, opcode in ORIGINAL_APP_LAUNCH_TARGET_SCENE_ENTRY_ANCHORS.items():
            struct.pack_into("<I", source, pc, opcode)
        for pc in (0x71C9EC, 0x71C9F0, 0x71CE78, 0x71CE80,
                   0x71C504, 0x71C508, 0x71C518):
            broken = bytearray(source)
            broken[pc] ^= 1
            with self.subTest(where=hex(pc)):
                with self.assertRaises(LevelUpNativeTraceError):
                    _original_app_launch_target_scene_entries(bytes(broken))

    def test_original_scene97_allocates_download_batch_task_not_fresh_profile(self):
        result = _original_scene97_download_batch_task(
            bytes(_synthetic_scene97_download_task_fixture())
        )
        self.assertEqual(result["task_constructor"], "0x725ee8 -> 0x73c9b8")
        self.assertIn("DownloadBatchTask", result["rtti"])
        self.assertEqual(result["rtti_relocation"], "0xafe0e0 -> 0x1db616")
        self.assertEqual(result["typeinfo_relocation"], "0xafe0a8 -> 0xafe0d8")
        self.assertFalse(result["network_transport_call_proven"])
        self.assertFalse(result["remote_data_required_proven"])
        self.assertFalse(result["615mb_additional_assets_locally_available_proven"])
        self.assertFalse(result["task_is_new_game_save_generator_proven"])
        self.assertEqual(result["tsv_template"], "download_%d.tsv (native 0x197b44)")
        self.assertEqual(result["indexed_manifest_entries"], 35)
        self.assertIn("0x73ca68 BEQ -> 0x73cb40", result["native_index_loop"])
        self.assertIn("0x320be0", result["per_index_source_lookup"])
        self.assertIn("context+0x2fb8+idx*4", result["per_index_native_storage"])

    def test_original_download_batch_task_drift_fails_closed(self):
        intact = _synthetic_scene97_download_task_fixture()
        for pc in (0x71CE80, 0x725EC4, 0x725ECC, 0x725EE8,
                   0x73C9F0, 0x73C9F8):
            other = bytearray(intact)
            other[pc] ^= 1
            with self.subTest(opcode=hex(pc)):
                with self.assertRaises(LevelUpNativeTraceError):
                    _original_scene97_download_batch_task(bytes(other))
        for where in (0x1DB616, 0x197B44,
                      ORIGINAL_RELA_DYN_OFFSET,
                      ORIGINAL_RELA_DYN_OFFSET+8):
            other = bytearray(intact)
            other[where] ^= 1
            with self.subTest(where=hex(where)):
                with self.assertRaises(LevelUpNativeTraceError):
                    _original_scene97_download_batch_task(bytes(other))

    def test_original_installpack_35_tsv_coverage_is_exact_manifest_not_guess(self):
        # Synthetic AES manifests, no original local .list/.pack bytes.
        from tools.base_mod.battlecats_pack_writer import encrypt_manifest_bytes

        def sealed_list(names):
            text = str(len(names)) + "\n"
            text += "".join(f"{name},{index*16},16\n"
                            for index, name in enumerate(names))
            return encrypt_manifest_bytes(text.encode("utf-8"))

        source = {
            family: sealed_list(
                ["download_5.tsv", "not-a-download.tsv"] if family == "DataLocal"
                else ["download_12.tsv"] if family == "DownloadLocal"
                else []
            )
            for family in JP15_7_1_ORIGINAL_LOCAL_LIST_COUNTS
        }
        report = _original_download_batch_tsv_installed_local_coverage(
            source, require_exact_owner_counts=False
        )
        self.assertEqual(report["checked_bundled_local_family_count"], 9)
        self.assertEqual(report["checked_bundled_local_entry_count"], 3)
        self.assertEqual(report["present_bundled_local_tsv"],
                         ["download_12.tsv", "download_5.tsv"])
        self.assertEqual(len(report["missing_bundled_local_tsv"]), 33)
        self.assertFalse(report["all_35_download_tsv_bundled_locally"])
        self.assertFalse(report["actual_remote_server_packs_examined"])
        self.assertFalse(report["actual_615mb_download_completed"])
        self.assertFalse(report["local_engine_boot_and_download_fallback_verified"])

        with self.assertRaisesRegex(LevelUpNativeTraceError, "count drifted"):
            _original_download_batch_tsv_installed_local_coverage(source)
        with self.assertRaisesRegex(LevelUpNativeTraceError, "family set changed"):
            _original_download_batch_tsv_installed_local_coverage(
                {"DataLocal": source["DataLocal"]},
                require_exact_owner_counts=False,
            )


    def test_native_original_tsv_resolver_indexes_source_before_getfilesdir(self):
        result = _original_download_tsv_file_source_resolver(
            bytes(_synthetic_tsv_source_resolver_fixture())
        )
        self.assertEqual(
            result["status"],
            "ORIGINAL_DOWNLOAD_BATCH_TSV_SOURCE_INDEX_AND_JNI_FILES_ROOT_VERIFIED",
        )
        self.assertEqual(result["original_lookup"], "0x73caa8 -> 0x320be0")
        self.assertEqual(result["source_index_query"], "0x320c34 -> 0x321138")
        self.assertEqual(
            result["missing_source_index_branch"],
            "0x320c38 TBZ -> 0x320f30",
        )
        self.assertEqual(
            result["shared_android_files_dir"],
            "0x320c40 -> 0x42cde8 (getFilesDir JNI thunk)",
        )
        self.assertEqual(result["observed_return_value_constants"], [-1, 0, 1])
        self.assertEqual(result["audio_only_suffixes"], [".caf", ".ogg"])
        self.assertFalse(result["download_tsv_audio_extension"])
        self.assertFalse(result["loose_tsv_in_files_dir_satisfies_source_index_proven"])
        self.assertFalse(result["actual_original_35_asset_files_resolved_successfully"])
        self.assertFalse(result["direct_real_network_request_from_resolver_proven"])
        self.assertFalse(result["original_offline_gameplay_Lv60_verified"])

    def test_original_native_tsv_source_resolver_opcode_or_root_drift_fails(self):
        exact = _synthetic_tsv_source_resolver_fixture()
        for pc in (
            0x73CA9C, 0x73CAA8, 0x73CAB0,
            0x320C34, 0x320C38, 0x320C40, 0x320C48,
            0x320C98, 0x320CA8, 0x320E24, 0x320E28,
            0x320E68, 0x320E6C, 0x320E88, 0x320F34, 0x320F48,
        ):
            changed = bytearray(exact)
            changed[pc] ^= 1
            with self.subTest(address=hex(pc)):
                with self.assertRaises(LevelUpNativeTraceError):
                    _original_download_tsv_file_source_resolver(bytes(changed))
        bad_audio_string = bytearray(exact)
        bad_audio_string[0x1A8C27] = ord("x")
        with self.assertRaisesRegex(LevelUpNativeTraceError, "prefix literal drifted"):
            _original_download_tsv_file_source_resolver(bytes(bad_audio_string))



    def test_original_tsv_name_resolves_through_registered_resource_map(self):
        # Only 29 original opcode words are used, no original executable or
        # game assets. This verifies a different, original registry-backed
        # path from a guessed loose-file/provider-only shortcut.
        blob = _synthetic_original_resource_registry_fixture()
        result = _original_download_tsv_resource_registration_chain(bytes(blob))
        self.assertEqual(
            result["status"],
            "ORIGINAL_NATIVE_NAMED_RESOURCE_REGISTRY_CONSUMER_AND_92_ROW_PRODUCER",
        )
        self.assertIn("0x321138 -> 0x364950", result["download_tsv_call_chain"])
        self.assertEqual(
            result["registered_resource_lookup"],
            "0x364980 -> 0x34d014; 0x364990 -> 0x34d8e4",
        )
        self.assertEqual(
            result["reader_no_registered_resource"],
            "0x321190 TBZ -> 0x321278",
        )
        self.assertIn("count92", result["registry_registration_loop"])
        self.assertIn("stride48", result["registry_registration_loop"])
        self.assertEqual(
            _original_arm64_cfg_successors(bytes(blob), 0x741B90),
            (0x741B74, 0x741B94),
        )
        self.assertFalse(result["all_35_download_tsv_registered_proven"])
        self.assertFalse(result["92_registry_names_enumerated_proven"])
        self.assertEqual(
            result["registry_source_pointer_relocation"],
            "0xb17d78 R_AARCH64_RELATIVE -> 0xf98d38",
        )
        self.assertIn("inside .bss", result["registry_runtime_source_memory"])
        self.assertFalse(result["registration_names_static_elf_available"])
        self.assertFalse(result["registry_initialized_before_offline_scene97_proven"])
        self.assertFalse(result["loose_original_app_files_dir_tsv_accepted_proven"])
        self.assertFalse(result["independent_fresh_local_profile_attached"])
        self.assertFalse(result["original_device_offline_gameplay_Lv60_verified"])

    def test_original_tsv_resource_registry_registration_and_parser_drift_fails(self):
        fixture = _synthetic_original_resource_registry_fixture()
        for pc in (0x321138, 0x321188, 0x321190, 0x3211A4,
                   0x3211E8, 0x364980, 0x364990, 0x3649F8,
                   0x34D014, 0x34D0F4, 0x741B6C, 0x741B70,
                   0x741B74, 0x741B84, 0x741B88, 0x741B8C,
                   0x741B90, 0x71C6F4, 0x71C748):
            corrupted = bytearray(fixture)
            corrupted[pc] ^= 1
            with self.subTest(site=hex(pc)):
                with self.assertRaises(LevelUpNativeTraceError):
                    _original_download_tsv_resource_registration_chain(bytes(corrupted))
        for field_offset in (0, 8, 16):
            corrupted = bytearray(fixture)
            corrupted[ORIGINAL_RELA_DYN_OFFSET + field_offset] ^= 1
            with self.subTest(relocation_field=field_offset):
                with self.assertRaises(LevelUpNativeTraceError):
                    _original_download_tsv_resource_registration_chain(bytes(corrupted))


    def test_extra_owned_list_scan_identifies_names_without_private_pack_bytes(self):
        from pathlib import Path
        import tempfile
        from tools.base_mod.battlecats_pack_writer import encrypt_manifest_bytes

        def encrypt_names(names):
            raw = str(len(names)) + "\n"
            raw += "".join(
                f"{name},{index*16},16\n" for index, name in enumerate(names)
            )
            return encrypt_manifest_bytes(raw.encode("utf-8"))

        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / "MNumberServer.list").write_bytes(
                encrypt_names(["download_0.tsv", "download_34.tsv", "PRIVATE_ACCOUNT_NOT_LOGGED"])
            )
            (root / "WImageDataServer.list").write_bytes(
                encrypt_names(["download_12.tsv"])
            )
            (root / "DO_NOT_READ.pack").write_bytes(b"PRIVATE_PACK_NEVER_READ")
            report = _additional_owner_list_coverage(root)
            self.assertEqual(report["family_count"], 2)
            self.assertEqual(report["total_declared_entries"], 4)
            self.assertEqual(
                report["matched_download_batch_tsv_names"],
                ["download_0.tsv", "download_12.tsv", "download_34.tsv"],
            )
            self.assertEqual(len(report["missing_download_batch_tsv_names"]), 32)
            self.assertFalse(report["all_35_tsv_names_listed"])
            self.assertFalse(report["all_35_tsv_content_bytes_present_and_valid"])
            self.assertFalse(report["native_registry_92_entries_cover_names"])
            self.assertFalse(report["original_game_offline_first_boot_and_Lv60_verified"])
            self.assertNotIn("PRIVATE_ACCOUNT_NOT_LOGGED", repr(report))
            self.assertNotIn("PRIVATE_PACK_NEVER_READ", repr(report))
            self.assertEqual(report["families"]["MNumberServer"]["declared_entries"], 3)
            pinned_families = {"MNumberServer", "WImageDataServer"}
            original_only = _additional_owner_list_coverage(
                root, known_original_families=pinned_families
            )
            self.assertEqual(original_only["family_count"], 2)
            (root / "WrongServer.list").write_bytes(
                encrypt_names(["download_2.tsv"])
            )
            with self.assertRaisesRegex(
                LevelUpNativeTraceError, "not declared in pinned"
            ):
                _additional_owner_list_coverage(
                    root, known_original_families=pinned_families
                )


    def test_private_tsv_candidate_sources_join_original_static_row_index(self):
        from pathlib import Path
        import tempfile
        from tools.base_mod.battlecats_pack_writer import encrypt_manifest_bytes

        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            common = encrypt_manifest_bytes(b"1\ndownload_9.tsv,0,16\n")
            (root / "MNumberServer.list").write_bytes(common)
            (root / "WImageDataServer.list").write_bytes(common)
            registry = {"MNumberServer": 43, "WImageDataServer": 4}
            report = _additional_owner_list_coverage(
                root, known_original_families=set(registry),
                registered_family_indices=registry,
            )
            candidates = report["download_tsv_candidate_registered_families"][
                "download_9.tsv"
            ]
            self.assertEqual(
                candidates,
                [
                    {"family": "WImageDataServer", "original_registration_index": 4},
                    {"family": "MNumberServer", "original_registration_index": 43},
                ],
            )
            self.assertEqual(
                report["ambiguous_target_filenames_across_families"],
                ["download_9.tsv"],
            )
            self.assertTrue(report["native_static_registration_indices_joined"])
            self.assertTrue(
                report["original_native_same_key_first_successful_registration_rule_static_proven"]
            )
            self.assertEqual(
                report["conditional_first_source_for_duplicate_names_if_all_register"],
                {"download_9.tsv": {
                    "family": "WImageDataServer",
                    "original_registration_index": 4,
                }},
            )
            self.assertFalse(report["original_native_actual_duplicate_tsv_source_winner_proven"])
            self.assertFalse(
                report["original_native_source_priority_or_duplicate_precedence_proven"]
            )
            self.assertFalse(report["native_registry_92_entries_cover_names"])
            with self.assertRaisesRegex(LevelUpNativeTraceError, "map invalid"):
                _additional_owner_list_coverage(
                    root, known_original_families=set(registry),
                    registered_family_indices={
                        "MNumberServer": 4, "WImageDataServer": 4,
                    },
                )
            with self.assertRaisesRegex(LevelUpNativeTraceError, "map invalid"):
                _additional_owner_list_coverage(
                    root, known_original_families=set(registry),
                    registered_family_indices={"MNumberServer": 43},
                )


    def test_two_verified_owner_tsv_candidates_remain_conditional_not_live_winner(self):
        """Each encrypted synthetic pack is inspected, not guessed or selected."""
        from pathlib import Path
        from hashlib import sha256
        import tempfile
        from tools.base_mod.battlecats_pack_writer import (
            encrypt_manifest_bytes, _encrypt_entry,
        )

        names = {"MNumberServer": b"synthetic-M-source\n",
                 "WImageDataServer": b"synthetic-W-source\n"}
        original_order = {"MNumberServer": 43, "WImageDataServer": 4}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source_digest = {}
            for family, payload in names.items():
                ciphertext, mode = _encrypt_entry(family, payload, region="jp")
                self.assertEqual(mode, "aes-128-ecb-server")
                manifest = encrypt_manifest_bytes(
                    f"1\ndownload_9.tsv,0,{len(ciphertext)}\n".encode()
                )
                (root / (family + ".list")).write_bytes(manifest)
                (root / (family + ".pack")).write_bytes(ciphertext)
                source_digest[family] = (
                    sha256(manifest).hexdigest(),
                    sha256(ciphertext).hexdigest(),
                )

            with self.assertRaisesRegex(
                LevelUpNativeTraceError, "ambiguous original TSV"
            ):
                _additional_owner_list_coverage(
                    root, known_original_families=set(original_order),
                    verify_paired_pack_tsv_payloads=True,
                )
            receipt = _additional_owner_list_coverage(
                root, known_original_families=set(original_order),
                registered_family_indices=original_order,
                verify_paired_pack_tsv_payloads=True,
            )
            self.assertTrue(receipt["all_duplicate_candidate_payloads_decrypted"])
            self.assertEqual(receipt["download_tsv_payloads_decrypted"],
                             ["download_9.tsv"])
            self.assertEqual(receipt["ambiguous_target_filenames_across_families"],
                             ["download_9.tsv"])
            self.assertEqual(
                receipt["conditional_first_source_for_duplicate_names_if_all_register"],
                {"download_9.tsv": {
                    "family": "WImageDataServer", "original_registration_index": 4
                }},
            )
            self.assertFalse(receipt["original_native_actual_duplicate_tsv_source_winner_proven"])
            self.assertFalse(receipt["original_native_tsv_semantics_accepted"])
            for family, payload in names.items():
                metadata = receipt["families"][family]["targeted_decrypted_tsv_payloads"]
                self.assertEqual(
                    metadata["download_9.tsv"]["decrypted_payload_sha256"],
                    sha256(payload).hexdigest(),
                )
                self.assertNotIn(payload.decode().strip(), repr(receipt))
                self.assertEqual(
                    sha256((root / (family + ".list")).read_bytes()).hexdigest(),
                    source_digest[family][0],
                )
                self.assertEqual(
                    sha256((root / (family + ".pack")).read_bytes()).hexdigest(),
                    source_digest[family][1],
                )


    def test_owned_additional_list_scan_rejects_missing_duplicate_or_symlink(self):
        from pathlib import Path
        import tempfile
        from tools.base_mod.battlecats_pack_writer import encrypt_manifest_bytes

        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            with self.assertRaisesRegex(
                LevelUpNativeTraceError, "1..64 encrypted manifests"
            ):
                _additional_owner_list_coverage(root)
            one = encrypt_manifest_bytes(b"1\ndownload_1.tsv,0,16\n")
            (root / "OwnedServer.list").write_bytes(one)
            self.assertEqual(
                _additional_owner_list_coverage(root)["matched_download_batch_tsv_names"],
                ["download_1.tsv"],
            )
            (root / "ownedserver.list").write_bytes(one)
            with self.assertRaisesRegex(LevelUpNativeTraceError, "duplicate"):
                _additional_owner_list_coverage(root)
            (root / "ownedserver.list").unlink()
            (root / "Unsafe-Path.list").write_bytes(one)
            with self.assertRaisesRegex(LevelUpNativeTraceError, "safe family name"):
                _additional_owner_list_coverage(root)
            (root / "Unsafe-Path.list").unlink()
            (root / "BrokenServer.list").write_bytes(b"not encrypted")
            with self.assertRaises(ValueError):
                _additional_owner_list_coverage(root)
            (root / "BrokenServer.list").unlink()
            symlink = root / "LinkServer.list"
            if hasattr(symlink, "symlink_to"):
                try:
                    symlink.symlink_to(root / "OwnedServer.list")
                except (OSError, NotImplementedError):
                    pass
                else:
                    with self.assertRaisesRegex(
                        LevelUpNativeTraceError, "not a regular safe"
                    ):
                        _additional_owner_list_coverage(root)



    def test_owner_server_pack_selected_tsv_optin_decrypts_only_approved_spans(self):
        """No original asset is in this test; encrypted ECB+manifest fixture."""
        import tempfile
        from pathlib import Path
        from hashlib import sha256
        from tools.base_mod.battlecats_pack_writer import (
            encrypt_manifest_bytes, _encrypt_entry,
        )

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            family = "MNumberServer"
            payload = b"0\t1\t2\nOwned local-only TSV fixture\n"
            secret_decoy = b"PRIVATE_PLAYER_ACCOUNT_DO_NOT_DECRYPT_OR_LOG"
            selected_ct, selected_mode = _encrypt_entry(family, payload, region="jp")
            secret_ct, _ = _encrypt_entry(family, secret_decoy, region="jp")
            self.assertEqual(selected_mode, "aes-128-ecb-server")
            plain_manifest = (
                "2\n"
                f"download_0.tsv,0,{len(selected_ct)}\n"
                f"private_account.csv,{len(selected_ct)},{len(secret_ct)}\n"
            ).encode()
            list_content = encrypt_manifest_bytes(plain_manifest)
            pack_content = selected_ct + secret_ct
            (root / (family + ".list")).write_bytes(list_content)
            (root / (family + ".pack")).write_bytes(pack_content)
            before_list, before_pack = sha256(list_content).hexdigest(), sha256(pack_content).hexdigest()

            names_only = _additional_owner_list_coverage(
                root, known_original_families={family},
            )
            self.assertEqual(names_only["status"],
                             "OWNER_ADDITIONAL_ENCRYPTED_LIST_NAMES_ONLY")
            self.assertFalse(names_only["paired_pack_payload_check_explicitly_requested"])
            self.assertEqual(names_only["download_tsv_payloads_decrypted"], [])
            self.assertEqual(
                names_only["families"][family]["targeted_decrypted_tsv_payloads"], {}
            )

            verified = _additional_owner_list_coverage(
                root, known_original_families={family},
                verify_paired_pack_tsv_payloads=True,
            )
            self.assertEqual(verified["status"],
                             "OWNER_ADDITIONAL_SELECTED_TSV_PAYLOAD_SHA256_ONLY")
            self.assertEqual(verified["download_tsv_payloads_decrypted"],
                             ["download_0.tsv"])
            self.assertTrue(verified["each_download_tsv_has_unique_listed_family"])
            entry = verified["families"][family]["targeted_decrypted_tsv_payloads"]["download_0.tsv"]
            self.assertEqual(entry["decrypted_payload_sha256"],
                             sha256(payload).hexdigest())
            self.assertEqual(entry["decrypted_payload_bytes"], len(payload))
            self.assertEqual(entry["source_ciphertext_bytes"], len(selected_ct))
            self.assertFalse(verified["all_35_payloads_decrypted_from_owner_paired_packs"])
            self.assertFalse(verified["all_35_tsv_content_bytes_present_and_valid"])
            self.assertFalse(verified["original_native_tsv_semantics_accepted"])
            self.assertFalse(verified["original_game_offline_first_boot_and_Lv60_verified"])
            self.assertNotIn("private_account.csv", repr(verified))
            self.assertNotIn(secret_decoy.decode(), repr(verified))
            self.assertNotIn(payload.decode(), repr(verified))
            self.assertEqual(
                sha256((root / (family + ".list")).read_bytes()).hexdigest(),
                before_list,
            )
            self.assertEqual(
                sha256((root / (family + ".pack")).read_bytes()).hexdigest(),
                before_pack,
            )

    def test_owner_extra_pack_tsv_optin_rejects_missing_bad_and_ambiguous_ciphertext(self):
        import tempfile
        from pathlib import Path
        from tools.base_mod.battlecats_pack_writer import (
            encrypt_manifest_bytes, _encrypt_entry,
        )

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            family = "MNumberServer"
            source_ct, _ = _encrypt_entry(family, b"new-local-fixture\n", region="jp")
            good_list = encrypt_manifest_bytes(
                f"1\ndownload_8.tsv,0,{len(source_ct)}\n".encode()
            )
            manifest = root / (family + ".list")
            pack = root / (family + ".pack")
            manifest.write_bytes(good_list)
            with self.assertRaisesRegex(
                LevelUpNativeTraceError, ".pack pair missing or unsafe"
            ):
                _additional_owner_list_coverage(
                    root, known_original_families={family},
                    verify_paired_pack_tsv_payloads=True,
                )
            pack.write_bytes(source_ct[:8])
            with self.assertRaisesRegex(LevelUpNativeTraceError, "span invalid"):
                _additional_owner_list_coverage(
                    root, known_original_families={family},
                    verify_paired_pack_tsv_payloads=True,
                )
            pack.write_bytes(b"\x00" * len(source_ct))
            with self.assertRaisesRegex(ValueError, "padding"):
                _additional_owner_list_coverage(
                    root, known_original_families={family},
                    verify_paired_pack_tsv_payloads=True,
                )
            pack.write_bytes(source_ct)
            duplicated = encrypt_manifest_bytes(
                f"2\ndownload_8.tsv,0,{len(source_ct)}\n"
                f"download_8.tsv,0,{len(source_ct)}\n".encode()
            )
            manifest.write_bytes(duplicated)
            with self.assertRaisesRegex(
                LevelUpNativeTraceError, "repeats target TSV"
            ):
                _additional_owner_list_coverage(
                    root, known_original_families={family},
                    verify_paired_pack_tsv_payloads=True,
                )
            manifest.write_bytes(good_list)
            other = "WImageDataServer"
            (root / (other + ".list")).write_bytes(good_list)
            (root / (other + ".pack")).write_bytes(source_ct)
            name_receipt = _additional_owner_list_coverage(
                root, known_original_families={family,other},
            )
            self.assertEqual(
                name_receipt["ambiguous_target_filenames_across_families"],
                ["download_8.tsv"],
            )
            self.assertFalse(name_receipt["each_download_tsv_has_unique_listed_family"])
            with self.assertRaisesRegex(
                LevelUpNativeTraceError, "ambiguous original TSV ciphertext"
            ):
                _additional_owner_list_coverage(
                    root, known_original_families={family, other},
                    verify_paired_pack_tsv_payloads=True,
                )

    def test_exact_original_server_families_have_92_list_pack_pairs(self):
        data = bytes(_synthetic_original_server_family_catalog_fixture())
        receipt = _original_registered_server_family_catalog(data)
        self.assertEqual(receipt["count_list_literals"], 92)
        self.assertEqual(receipt["count_pack_literals"], 92)
        self.assertEqual(receipt["count_paired_original_server_families"], 92)
        self.assertIn("XImageServer", receipt["original_server_family_stems"])
        self.assertIn("Test089Server", receipt["original_server_family_stems"])
        self.assertIn("XImageServer.list", receipt["one_original_runtime_initializer"])
        self.assertTrue(receipt["matches_92_registration_loop_row_count"])
        self.assertFalse(receipt["all_runtime_registered_names_proven"])
        self.assertFalse(receipt["all_owner_pack_payloads_possessed"])
        self.assertFalse(receipt["real_original_game_first_boot_local_success"])

    def test_original_server_family_catalog_rejects_opcode_literalmismatch_and_missing_pack(self):
        source = _synthetic_original_server_family_catalog_fixture()
        for pc in (0x71599C, 0x7159A0, 0x7159A4, 0x7159A8, 0x7159C0):
            corrupted = bytearray(source)
            corrupted[pc] ^= 1
            with self.subTest(pc=hex(pc)):
                with self.assertRaises(LevelUpNativeTraceError):
                    _original_registered_server_family_catalog(bytes(corrupted))
        corrupted = bytearray(source)
        corrupted[0x1918D1] = ord("Q")
        with self.assertRaisesRegex(LevelUpNativeTraceError, "literal drifted"):
            _original_registered_server_family_catalog(bytes(corrupted))
        corrupted = bytearray(source)
        cursor = corrupted.find(b"Test089Server.pack\x00")
        self.assertGreater(cursor, 0)
        corrupted[cursor + len(b"Test089Server.pac")] = ord("x")
        with self.assertRaisesRegex(LevelUpNativeTraceError, "92 paired"):
            _original_registered_server_family_catalog(bytes(corrupted))


    def test_original_server_table_ctor_runs_from_ELF_init_array(self):
        owner_like = bytes(_synthetic_native_resource_ctor_init_array())
        result = _original_server_registry_constructor_initialized_on_load(
            owner_like
        )
        self.assertEqual(result["ELF_init_array_slot"], "0xb16cb8")
        self.assertEqual(result["ELF_relative_ctor"], "0x714ae8")
        self.assertEqual(result["original_first_literal_loaded"],
                         "XImageServer.list")
        self.assertEqual(result["BSS_store_site"], "0x7159c0")
        self.assertEqual(result["runtime_BSS_table_source"], "0xf98d38")
        self.assertEqual(result["subsequent_92_row_registration"],
                         "0x741b68..0x741b90")
        self.assertFalse(result["all_92_registered_native_rows_resolved"])
        self.assertFalse(result["owned_additional_Server_pack_available"])
        self.assertFalse(result["native_first_game_initializer_or_save_attached"])
        self.assertFalse(result["original_offline_Lv60_UI_and_reboot_tested"])

    def test_original_native_resource_ctor_fail_closed_on_relocation_or_literal_drift(self):
        pristine = _synthetic_native_resource_ctor_init_array()
        for at in (0x714AE8, 0x71599C, 0x7159A0,
                   0x7159A4, 0x7159AC, 0x7159C0):
            corrupted = bytearray(pristine)
            corrupted[at] ^= 1
            with self.subTest(opcode=hex(at)):
                with self.assertRaises(LevelUpNativeTraceError):
                    _original_server_registry_constructor_initialized_on_load(
                        bytes(corrupted)
                    )
        for off in (0x1918D1,
                    ORIGINAL_RELA_DYN_OFFSET,
                    ORIGINAL_RELA_DYN_OFFSET + 8,
                    ORIGINAL_RELA_DYN_OFFSET + 16,
                    ORIGINAL_INIT_ARRAY_FILE_OFFSET
                    + ORIGINAL_INIT_ARRAY_RELOCATION_SLOT
                    - ORIGINAL_INIT_ARRAY_SOURCE_START):
            corrupted = bytearray(pristine)
            corrupted[off] ^= 1
            with self.subTest(offset=hex(off)):
                with self.assertRaises(LevelUpNativeTraceError):
                    _original_server_registry_constructor_initialized_on_load(
                        bytes(corrupted)
                    )

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
