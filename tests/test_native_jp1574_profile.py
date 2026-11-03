"""Synthetic version-selection and fail-closed source-gate regression tests."""
import struct
import unittest
from contextlib import ExitStack
from hashlib import sha256
from unittest.mock import patch

from tests.test_original_scene_native_image_gate import fixture
from tools.base_mod import source_native_jp1574 as source
from tools.base_mod import original_scene_native_image_gate as gate
from tools.base_mod.inject_shim import _source_anchor, verify_anchor_native
from tools.base_mod.pc_native_balance import SITES, make_stub, _source_profile


class NativeJP1574ProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = bytearray(fixture())
        extent = max(vma + size for vma, size, _ in source.PINNED_MAPPED_RANGES.values()) + 4096
        data.extend(bytes(max(0, extent - len(data))))
        struct.pack_into("<QQ", data, 0x40 + 32, len(data), len(data))
        data[0x310:0x324] = bytes.fromhex(source.BUILD_ID)
        struct.pack_into("<Q", data, 0x400 + 24 + 8, source.DRAW_VMA)
        for vma, word in source.SCENE_ANCHORS.items():
            struct.pack_into("<I", data, vma, word)
        cls.native = bytes(data)
        cls.stack = ExitStack()
        cls.addClassCleanup(cls.stack.close)
        cls.stack.enter_context(patch.object(source, "TEXT_SHA256", sha256(
            cls.native[source.TEXT_START:source.TEXT_END]).hexdigest()))
        cls.stack.enter_context(patch.object(source, "PINNED_MAPPED_RANGES", {
            label: (vma, size, sha256(cls.native[vma:vma+size]).hexdigest())
            for label, (vma, size, _) in source.PINNED_MAPPED_RANGES.items()
        }))

    def test_raw_injection_remains_legacy_by_default(self):
        self.assertEqual(_source_anchor("jp1571")[2], "jp-15.7.1-arm64")
        self.assertEqual(_source_anchor("jp1574")[:2], (source.NATIVE_SHA256, source.BUILD_ID))
        for profile in ("jp1571", "jp1574"):
            with self.subTest(profile=profile), self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                verify_anchor_native(self.native, source_profile=profile)
        with self.assertRaisesRegex(ValueError, "unsupported native source profile"):
            verify_anchor_native(self.native, source_profile="latest")

    def test_new_build_selects_full_new_source_profile(self):
        result = gate.verify_mapped_original_scene_image(self.native)
        self.assertIn("JP1574", result["status"])
        self.assertEqual(result["complete_original_text_bytes_verified"], 8137684)
        self.assertEqual(result["original_JNI_draw_export_vma"], "0x3184bc")
        self.assertEqual(result["verified_executable_instruction_anchors"], 19)
        self.assertEqual(len(result["verified_nontext_mapped_source_sections"]), 5)

    def test_non_anchor_text_change_is_rejected(self):
        data = bytearray(self.native)
        data[source.TEXT_START + 4] ^= 1
        with self.assertRaisesRegex(gate.OriginalSceneNativeImageError, "complete original JP executable"):
            gate.verify_mapped_original_scene_image(bytes(data))

    def test_every_nontext_range_remains_pinned(self):
        for label, (vma, size, _) in source.PINNED_MAPPED_RANGES.items():
            data = bytearray(self.native)
            data[vma + size - 1] ^= 1
            with self.subTest(label=label), self.assertRaises(gate.OriginalSceneNativeImageError):
                gate.verify_mapped_original_scene_image(bytes(data))

    def test_build_id_does_not_authorize_legacy_anchors_or_draw(self):
        data = bytearray(self.native)
        struct.pack_into("<Q", data, 0x400 + 24 + 8, gate.ORIGINAL_DRAW_VMA)
        with self.assertRaisesRegex(gate.OriginalSceneNativeImageError, "VMA shift"):
            gate.verify_mapped_original_scene_image(bytes(data))
        data = bytearray(self.native)
        struct.pack_into("<I", data, 0x71F584, gate.ORIGINAL_SCENE_ANCHORS[0x71BF28])
        with self.assertRaisesRegex(gate.OriginalSceneNativeImageError, "instruction drift"):
            gate.verify_mapped_original_scene_image(bytes(data))

    def test_unknown_build_id_fails_closed(self):
        data = bytearray(self.native)
        data[0x310] ^= 1
        with self.assertRaisesRegex(gate.OriginalSceneNativeImageError, "Build ID drift"):
            gate.verify_mapped_original_scene_image(bytes(data))
        with self.assertRaisesRegex(ValueError, "BUILD_ID_CHANGED"):
            _source_profile(bytes(data))

    def test_balance_profile_and_both_tbz_edges_use_selected_version(self):
        self.assertEqual(_source_profile(self.native), (source.BALANCE_SITES, source.DRAW_VMA, source.BUILD_ID))
        for sites in (SITES, source.BALANCE_SITES):
            code = make_stub(0x1000000, 0x1002000, 0x1000, sites[0])
            words = struct.unpack("<" + "I" * (len(code)//4), code)
            self.assertEqual(words[-3], 0x37000057)
            targets = []
            for i in (-2, -1):
                immediate = words[i] & 0x3ffffff
                if immediate & 0x2000000:
                    immediate -= 0x4000000
                targets.append(0x1000000 + len(code) + i*4 + immediate*4)
            self.assertEqual(targets, [sites[0][1] + 16 + 0x1000, sites[0][1] + 4 + 0x1000])

    def test_balance_call_words_decode_to_pinned_targets(self):
        for op, pc, word, target in source.BALANCE_SITES:
            if op in (2, 4, 8):
                self.assertEqual(word & 0xfc000000, 0x94000000)
                immediate = word & 0x3ffffff
                if immediate & 0x2000000:
                    immediate -= 0x4000000
                self.assertEqual(pc + 4*immediate, target)
            elif op != 1:
                self.assertEqual(target, pc + 4)


if __name__ == "__main__":
    unittest.main()
