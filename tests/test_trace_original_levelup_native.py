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
    LevelUpNativeTraceError,
    _original_unit_data_loader, _levelmax_popup_branch,
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
        with self.assertRaisesRegex(
            LevelUpNativeTraceError, "exact JP15.7.1 native hash"
        ):
            trace_exact_native(b"not an original game library")

if __name__ == "__main__":
    unittest.main()
