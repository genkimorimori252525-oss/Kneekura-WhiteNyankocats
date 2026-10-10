"""Synthetic ELF64 AArch64 mapping of exact original scene JNI source words.

Never includes real game binaries, original SAVE, licensed media or keys.
Builds a minimal synthetic 8 MiB ELF to exercise post-LIEF source layout
checks before the optional local-research scene instrumentation is packaged.
"""
from __future__ import annotations

import struct
import unittest

from tools.base_mod.original_scene_native_image_gate import (
    ORIGINAL_JP1571_BUILD_ID, ORIGINAL_DRAW_SYMBOL,
    ORIGINAL_DRAW_VMA, ORIGINAL_SCENE_ANCHORS,
    OriginalSceneNativeImageError, verify_mapped_original_scene_image,
)


def fixture() -> bytes:
    data = bytearray(max(ORIGINAL_SCENE_ANCHORS) + 0x1000)
    data[:4] = b"\x7fELF"
    data[4:6] = b"\x02\x01"  # ELF64 little
    struct.pack_into("<HHI", data, 16, 3, 183, 1)  # ET_DYN, AArch64
    struct.pack_into("<Q", data, 32, 0x40)  # phoff
    struct.pack_into("<Q", data, 40, 0x600) # shoff
    struct.pack_into("<HH", data, 54, 56, 2) # phentsize, phnum
    struct.pack_into("<HH", data, 58, 64, 3) # shentsize, shnum
    # PT_LOAD executable from file offset zero, exact original VMAs preserved.
    struct.pack_into("<IIQQQQQQ", data, 0x40, 1, 5, 0, 0, 0,
                     len(data), len(data), 0x1000)
    # PT_NOTE with a single correct GNU BuildID note.
    struct.pack_into("<IIQQQQQQ", data, 0x40 + 56, 4, 4,
                     0x300, 0x300, 0, 36, 36, 4)
    data[0x300:0x300+36] = (
        struct.pack("<III", 4, 20, 3)
        + b"GNU\x00" + bytes.fromhex(ORIGINAL_JP1571_BUILD_ID)
    )
    # Minimal SHT_DYNSYM with dummy + named original JNI function.
    # Section0: NULL, Section1: dynamic symbols, Section2: string table.
    struct.pack_into("<IIQQQQIIQQ", data, 0x600+64, 0, 11,
                     0, 0x400, 0x400, 48, 2, 0, 8, 24)
    name = ORIGINAL_DRAW_SYMBOL.encode("ascii")
    data[0x500:0x500+len(name)+2] = b"\x00" + name + b"\x00"
    struct.pack_into("<IIQQQQIIQQ", data, 0x600+128,
                     0, 3, 0, 0x500, 0x500, len(name)+2, 0, 0, 1, 0)
    struct.pack_into("<IBBHQQ", data, 0x400+24, 1, 0x12, 0,
                     1, ORIGINAL_DRAW_VMA, 228)
    for pc, opcode in ORIGINAL_SCENE_ANCHORS.items():
        struct.pack_into("<I", data, pc, opcode)
    return bytes(data)


class OriginalSceneSourceRepackPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_fixture = fixture()

    def test_unchanged_synthetic_pinned_arm64_mapping_and_export(self):
        result = verify_mapped_original_scene_image(self.original_fixture)
        self.assertTrue(result["repacked_original_native_hook_layout_safe_static"])
        self.assertEqual(result["verified_executable_instruction_anchors"], 6)
        self.assertEqual(result["original_JNI_draw_export_vma"],
                         f"0x{ORIGINAL_DRAW_VMA:x}")
        self.assertEqual(result["pinned_original_build_id"], ORIGINAL_JP1571_BUILD_ID)
        self.assertFalse(result["original_account_free_player_SAVE_generated"])
        self.assertFalse(result["actual_Android_inline_hook_attach_verified"])
        self.assertFalse(result["user_original_APK_SAVE_or_asset_modified"])

    def test_repacked_one_opcode_changed_is_refused(self):
        for at in ORIGINAL_SCENE_ANCHORS:
            with self.subTest(offset=hex(at)):
                bad = bytearray(self.original_fixture)
                bad[at] ^= 1
                with self.assertRaisesRegex(
                    OriginalSceneNativeImageError,
                    "instruction drift"
                ):
                    verify_mapped_original_scene_image(bytes(bad))

    def test_changed_jni_export_name_or_value_is_refused_even_when_opcodes_match(self):
        corrupt_export = bytearray(self.original_fixture)
        corrupt_export[0x400+24+8] ^= 1  # st_value low byte
        with self.assertRaisesRegex(OriginalSceneNativeImageError, "JNI draw export VMA"):
            verify_mapped_original_scene_image(bytes(corrupt_export))
        corrupt_name = bytearray(self.original_fixture)
        corrupt_name[0x501] ^= 1
        with self.assertRaisesRegex(OriginalSceneNativeImageError, "missing or duplicated"):
            verify_mapped_original_scene_image(bytes(corrupt_name))

    def test_changed_buildid_or_wrong_machine_is_refused(self):
        corrupt = bytearray(self.original_fixture)
        corrupt[0x300+16] ^= 1
        with self.assertRaisesRegex(OriginalSceneNativeImageError, "Build ID drift"):
            verify_mapped_original_scene_image(bytes(corrupt))
        corrupt = bytearray(self.original_fixture)
        struct.pack_into("<H", corrupt, 18, 62)  # x86_64
        with self.assertRaises(OriginalSceneNativeImageError):
            verify_mapped_original_scene_image(bytes(corrupt))

    def test_invalid_text_mappings_and_section_header_boundaries_fail_closed(self):
        corrupted = bytearray(self.original_fixture)
        struct.pack_into("<I", corrupted, 0x40+4, 4)  # PT_LOAD is non-exec
        with self.assertRaisesRegex(OriginalSceneNativeImageError, "not unique and mapped"):
            verify_mapped_original_scene_image(bytes(corrupted))
        corrupted = bytearray(self.original_fixture)
        struct.pack_into("<Q", corrupted, 40, len(corrupted) + 16) # shoff
        with self.assertRaisesRegex(OriginalSceneNativeImageError, "section headers unavailable"):
            verify_mapped_original_scene_image(bytes(corrupted))

    def test_bad_type_without_elf_or_private_original_rejected(self):
        with self.assertRaises(OriginalSceneNativeImageError):
            verify_mapped_original_scene_image(b"\x7fELF")
        with self.assertRaises(OriginalSceneNativeImageError):
            verify_mapped_original_scene_image("NOT_BINARY")


if __name__ == "__main__":
    unittest.main()
