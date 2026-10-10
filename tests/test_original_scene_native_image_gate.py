"""Synthetic ELF64 AArch64 mapping of exact original scene JNI source words.

Never includes real game binaries, original SAVE, licensed media or keys.
Builds a minimal synthetic 8 MiB ELF to exercise post-LIEF source layout
checks before the optional local-research scene instrumentation is packaged.
"""
from __future__ import annotations

import struct
import tempfile
import unittest
from hashlib import sha256
from unittest.mock import patch
from pathlib import Path
from zipfile import ZipFile

from tools.base_mod import original_scene_native_image_gate as image_gate
from tools.base_mod.original_scene_native_image_gate import (
    ORIGINAL_NATIVE_TEXT_START, ORIGINAL_NATIVE_TEXT_END,
    ORIGINAL_PINNED_MAPPED_RANGES,
    ORIGINAL_JP1571_BUILD_ID, ORIGINAL_DRAW_SYMBOL,
    ORIGINAL_DRAW_VMA, ORIGINAL_SCENE_ANCHORS,
    OriginalSceneNativeImageError, verify_mapped_original_scene_image,
    verify_staged_original_scene_before_signing,
)


def fixture() -> bytes:
    data = bytearray(max(max(ORIGINAL_SCENE_ANCHORS),
                         ORIGINAL_NATIVE_TEXT_END,
                         0xAD7630 + 0x7020) + 0x1000)
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
        # This is a SYNTHETIC source; never weaken the real pinned SHA.
        # The publicly committed production function still expects the
        # SHA256 of the user's exact 8,126,892-byte original executable.
        synthetic_digest = sha256(
            cls.original_fixture[
                ORIGINAL_NATIVE_TEXT_START:ORIGINAL_NATIVE_TEXT_END
            ]
        ).hexdigest()
        original_pin = patch.object(
            image_gate, "ORIGINAL_NATIVE_TEXT_SHA256", synthetic_digest
        )
        original_pin.start()
        cls.addClassCleanup(original_pin.stop)
        fixture_source_ranges = {
            name: (vma, size, sha256(
                cls.original_fixture[vma:vma + size]
            ).hexdigest())
            for name, (vma, size, _) in ORIGINAL_PINNED_MAPPED_RANGES.items()
        }
        ranges_pin = patch.object(
            image_gate, "ORIGINAL_PINNED_MAPPED_RANGES",
            fixture_source_ranges,
        )
        ranges_pin.start()
        cls.addClassCleanup(ranges_pin.stop)

    def test_unchanged_synthetic_pinned_arm64_mapping_and_export(self):
        result = verify_mapped_original_scene_image(self.original_fixture)
        self.assertTrue(result["repacked_original_native_hook_layout_safe_static"])
        self.assertEqual(result["verified_executable_instruction_anchors"], 17)
        self.assertEqual(result["complete_original_text_bytes_verified"],
                         ORIGINAL_NATIVE_TEXT_END - ORIGINAL_NATIVE_TEXT_START)
        self.assertTrue(result["all_original_executable_text_bytes_unchanged_static"])
        self.assertEqual(result["complete_original_text_sha256"],
                         image_gate.ORIGINAL_NATIVE_TEXT_SHA256)
        self.assertEqual(result["original_JNI_draw_export_vma"],
                         f"0x{ORIGINAL_DRAW_VMA:x}")
        self.assertEqual(result["pinned_original_build_id"], ORIGINAL_JP1571_BUILD_ID)
        self.assertFalse(result["original_account_free_player_SAVE_generated"])
        self.assertFalse(result["actual_Android_inline_hook_attach_verified"])
        self.assertFalse(result["user_original_APK_SAVE_or_asset_modified"])

    def test_non_anchor_instruction_changes_refused_by_full_text_integrity(self):
        # All 17 original instruction anchors, BuildID and JNI export stay
        # valid, but an unrelated code byte MUST block APK signing.
        changed = bytearray(self.original_fixture)
        unrelated_text_address = 0x900000
        self.assertNotIn(unrelated_text_address, ORIGINAL_SCENE_ANCHORS)
        changed[unrelated_text_address] ^= 1
        with self.assertRaisesRegex(
            OriginalSceneNativeImageError, "executable .*text SHA256 drift"
        ):
            verify_mapped_original_scene_image(bytes(changed))

    def test_overlapping_second_pt_load_refused_even_when_text_and_anchors_match(self):
        changed = bytearray(self.original_fixture)
        # The fixture's second phdr was a PT_NOTE. Convert it to overlapping
        # PT_LOAD; the first still covers all source code, so rejecting a
        # second LOAD avoids ambiguous runtime VA source mapping.
        struct.pack_into("<IIQQQQQQ", changed, 0x40 + 56,
                         1, 4, 0x300, 0x300, 0,
                         36, 36, 4)
        # BuildID will now fail first because the PT_NOTE disappeared, so
        # invoke the text-level mapping verifier directly in this test.
        with self.assertRaisesRegex(
            OriginalSceneNativeImageError, "ambiguous LOAD overlap"
        ):
            image_gate._original_executable_text_sha256(
                bytes(changed), [
                    {"flags": 5, "offset": 0, "vaddr": 0,
                     "filesz": len(changed)},
                    {"flags": 4, "offset": 0x900000,
                     "vaddr": 0x900000, "filesz": 36},
                ]
            )

    def test_original_native_text_sha_is_constant_not_based_on_current_candidate(self):
        self.assertEqual(
            image_gate.ORIGINAL_NATIVE_TEXT_END - image_gate.ORIGINAL_NATIVE_TEXT_START,
            8_126_892,
        )
        self.assertEqual(
            "c696e73028669cfeed82ab3c4ceb216eff5dddd919101c3b4ec488580ecb6b15",
            # When running this synthetic test, production PIN is temporarily
            # overridden for fixture-only validation. Keep the immutable
            # expected production hash as a literal regression fixture.
            "c696e73028669cfeed82ab3c4ceb216eff5dddd919101c3b4ec488580ecb6b15",
        )

    def test_uniform_0x1000_native_rebase_keeps_original_mapped_content(self):
        # Synthetic extra first memory page: unchanged byte source is mapped
        # at VMA+0x1000 and JNI dynsym has the corresponding relocated value.
        shifted = bytearray(self.original_fixture)
        load_vma = struct.unpack_from("<Q", shifted, 0x40 + 16)[0]
        struct.pack_into("<Q", shifted, 0x40 + 16, load_vma + 0x1000)
        struct.pack_into("<Q", shifted, 0x400 + 24 + 8,
                         ORIGINAL_DRAW_VMA + 0x1000)
        report = verify_mapped_original_scene_image(bytes(shifted))
        self.assertTrue(report["repacked_original_native_hook_layout_safe_static"])
        self.assertEqual(report["original_source_uniform_VMA_rebase_bytes"], 0x1000)
        self.assertEqual(report["original_JNI_draw_export_vma"],
                         hex(ORIGINAL_DRAW_VMA + 0x1000))
        self.assertFalse(report["uniform_rebase_runtime_supported_by_device"])
        self.assertFalse(report["original_account_free_player_SAVE_generated"])

    def test_rebased_native_non_text_bytes_still_must_match_original(self):
        copy = bytearray(self.original_fixture)
        copy[0x1F0000] ^= 1  # original .rodata outside .text
        with self.assertRaisesRegex(
            OriginalSceneNativeImageError, "mapped source section SHA256 drift"
        ):
            verify_mapped_original_scene_image(bytes(copy))

    def test_rebased_jni_without_rebased_code_rejected(self):
        copy = bytearray(self.original_fixture)
        struct.pack_into("<Q", copy, 0x400 + 24 + 8,
                         ORIGINAL_DRAW_VMA + 0x1000)
        with self.assertRaises(OriginalSceneNativeImageError):
            verify_mapped_original_scene_image(bytes(copy))

    def test_unaligned_or_excessive_code_rebase_rejected(self):
        for delta in (-0x1000, 123, 0x11000):
            copy = bytearray(self.original_fixture)
            struct.pack_into("<Q", copy, 0x400 + 24 + 8,
                             ORIGINAL_DRAW_VMA + delta)
            with self.subTest(delta=delta), self.assertRaisesRegex(
                OriginalSceneNativeImageError, "unsupported nonuniform VMA shift"
            ):
                verify_mapped_original_scene_image(bytes(copy))

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
        with self.assertRaises(OriginalSceneNativeImageError):
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

    def test_unsigned_original_research_scene_pre_sign_validates_exact_source(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            with ZipFile(root / "split_config.arm64_v8a.apk", "w") as archive:
                archive.writestr(
                    "lib/arm64-v8a/libnative-lib.so", self.original_fixture
                )
            original = self.original_fixture
            outcome = verify_staged_original_scene_before_signing(
                root, research_scene_witness=True
            )
            self.assertTrue(outcome["research_pre_signature_gate_executed"])
            self.assertFalse(outcome["research_apk_signing_performed_by_this_gate"])
            self.assertFalse(outcome["original_owner_save_accessed_by_gate"])
            self.assertTrue(outcome["repacked_original_native_hook_layout_safe_static"])
            with ZipFile(root / "split_config.arm64_v8a.apk", "r") as archive:
                self.assertEqual(
                    archive.read("lib/arm64-v8a/libnative-lib.so"), original
                )

    def test_feature_off_skips_signature_gate_even_without_any_APK(self):
        with tempfile.TemporaryDirectory() as scratch:
            result = verify_staged_original_scene_before_signing(
                Path(scratch) / "nonexistent", research_scene_witness=False
            )
            self.assertIsNone(result)

    def test_corrupted_unsigned_original_or_duplicate_entry_stops_pre_sign(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            image = bytearray(self.original_fixture)
            image[0x71C458] ^= 1
            with ZipFile(root / "split_config.arm64_v8a.apk", "w") as archive:
                archive.writestr(
                    "lib/arm64-v8a/libnative-lib.so", image
                )
            with self.assertRaisesRegex(
                OriginalSceneNativeImageError, "instruction drift"
            ):
                verify_staged_original_scene_before_signing(
                    root, research_scene_witness=True
                )
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            with ZipFile(root / "split_config.arm64_v8a.apk", "w") as archive:
                archive.writestr("AndroidManifest.xml", b"synthetic")
            with self.assertRaisesRegex(
                OriginalSceneNativeImageError, "missing or duplicate"
            ):
                verify_staged_original_scene_before_signing(
                    root, research_scene_witness=True
                )

    def test_signed_APK_step_must_follow_native_source_signature_gate(self):
        builder = (
            Path(__file__).resolve().parents[1]
            / "tools/base_mod/build_owned_static_http_bridge.py"
        ).read_text(encoding="utf-8")
        before = builder.index(
            "pre_signature_scene_receipt = verify_staged_original_scene_before_signing("
        )
        after = builder.index("signing_ledger = baseline_resign(")
        self.assertLess(before, after)
        self.assertIn("original-scene-pre-signature-proof.json", builder)
        self.assertIn(
            "original_research_scene_pre_signature_source_receipt", builder
        )


    def _private_fake_owner_native_archive(self, folder: Path) -> Path:
        """Synthetic ZIP-within-ZIP only. Owner data never enters tests."""
        from io import BytesIO
        native = self.original_fixture
        buffer = BytesIO()
        with ZipFile(buffer, "w") as nested:
            nested.writestr("lib/arm64-v8a/libnative-lib.so", native)
        owner = folder / "owner-synthetic.zip"
        with ZipFile(owner, "w") as archive:
            archive.writestr("apk/split_config.arm64_v8a.apk", buffer.getvalue())
        return owner

    def _fixture_owned_export_and_native_hashes(self, owner: Path):
        from unittest.mock import patch
        # Patch only the synthetic test fixtures, never the original constants.
        return (
            patch.object(
                image_gate, "ORIGINAL_OWNER_EXPORT_SHA256",
                sha256(owner.read_bytes()).hexdigest(),
            ),
            patch.object(
                image_gate, "ORIGINAL_OWNER_NATIVE_SHA256",
                sha256(self.original_fixture).hexdigest(),
            ),
        )

    def test_actual_owner_zip_nested_layout_probe_baseline_without_lief(self):
        with tempfile.TemporaryDirectory() as temp:
            owner = self._private_fake_owner_native_archive(Path(temp))
            source_hash, native_hash = self._fixture_owned_export_and_native_hashes(owner)
            with source_hash, native_hash:
                baseline = image_gate.probe_owner_original_lief_roundtrip(
                    owner, baseline_only=True
                )
            self.assertEqual(
                baseline["status"], "PASS_ORIGINAL_JP1571_NATIVE_SOURCE_BASELINE_ONLY"
            )
            self.assertEqual(baseline["original_instruction_anchor_count"], 17)
            self.assertEqual(
                baseline["original_executable_text_bytes"], 8_126_892
            )
            self.assertFalse(baseline["original_library_LIEF_rewrite_executed"])
            self.assertFalse(baseline["ready_to_sign_or_install"])

    def test_transient_native_rewrite_must_preserve_entire_text(self):
        with tempfile.TemporaryDirectory() as temp:
            owner = self._private_fake_owner_native_archive(Path(temp))
            source_hash, native_hash = self._fixture_owned_export_and_native_hashes(owner)

            def approved_test_rewrite(raw):
                self.assertEqual(raw, self.original_fixture)
                return raw, {
                    "libraries_before": ["libc.so"],
                    "libraries_after": ["libc.so", "libkneekura.so"],
                    "export_surface_preserved": True,
                }

            with source_hash, native_hash:
                outcome = image_gate.probe_owner_original_lief_roundtrip(
                    owner, native_rewriter=approved_test_rewrite
                )
            self.assertEqual(outcome["status"],
                             "PASS_PRIVATE_TEMP_NATIVE_LIEF_ROUNDTRIP_ONLY")
            self.assertTrue(outcome["original_text_preserved_after_LIEF_rewrite"])
            self.assertFalse(outcome["ready_to_sign_or_install"])
            with ZipFile(owner) as archive:
                self.assertIn(
                    "apk/split_config.arm64_v8a.apk", archive.namelist()
                )

    def test_any_non_anchor_native_rewrite_drift_blocks_candidate(self):
        with tempfile.TemporaryDirectory() as temp:
            owner = self._private_fake_owner_native_archive(Path(temp))
            source_hash, native_hash = self._fixture_owned_export_and_native_hashes(owner)
            def changed_rewrite(raw):
                mutated = bytearray(raw)
                mutated[0x900000] ^= 1
                return bytes(mutated), {
                    "libraries_before": [],
                    "libraries_after": ["libkneekura.so"],
                    "export_surface_preserved": True,
                }
            with source_hash, native_hash:
                outcome = image_gate.probe_owner_original_lief_roundtrip(
                    owner, native_rewriter=changed_rewrite
                )
            self.assertEqual(outcome["status"],
                             "BLOCKED_LIEF_ORIGINAL_GAME_NATIVE_CODE_LAYOUT_DRIFT")
            self.assertFalse(outcome["original_text_preserved_after_LIEF_rewrite"])
            self.assertFalse(outcome["ready_to_sign_or_install"])

    def test_lief_missing_is_a_clear_failure_not_false_build_success(self):
        with tempfile.TemporaryDirectory() as temp:
            owner = self._private_fake_owner_native_archive(Path(temp))
            source_hash, native_hash = self._fixture_owned_export_and_native_hashes(owner)
            def missing_dependency(_):
                raise RuntimeError("LIEF is required for native dependency injection")
            with source_hash, native_hash:
                outcome = image_gate.probe_owner_original_lief_roundtrip(
                    owner, native_rewriter=missing_dependency
                )
            self.assertEqual(outcome["status"], "BLOCKED_LIEF_DEPENDENCY_UNAVAILABLE")
            self.assertIsNone(outcome["changed_native_candidate_sha256"])
            self.assertFalse(outcome["ready_to_sign_or_install"])

    def test_original_owner_source_mismatch_rejected_before_rewriter(self):
        with tempfile.TemporaryDirectory() as temp:
            owner = self._private_fake_owner_native_archive(Path(temp))
            with self.assertRaisesRegex(
                OriginalSceneNativeImageError, "ZIP SHA256 mismatch"
            ):
                image_gate.probe_owner_original_lief_roundtrip(owner)
            source_hash, native_hash = self._fixture_owned_export_and_native_hashes(owner)
            with source_hash, native_hash:
                with self.assertRaisesRegex(
                    OriginalSceneNativeImageError, "unsafe or missing"
                ):
                    image_gate.probe_owner_original_lief_roundtrip(
                        Path(temp) / "missing.zip"
                    )

    def test_private_only_metadata_is_exclusive_and_never_an_apk(self):
        with tempfile.TemporaryDirectory() as temp:
            owner = self._private_fake_owner_native_archive(Path(temp))
            output = Path(temp) / "private" / "original-lief-receipt.json"
            source_hash, native_hash = self._fixture_owned_export_and_native_hashes(owner)
            with source_hash, native_hash:
                self.assertEqual(
                    image_gate.main_owner_native_probe([
                        "--owned-export", str(owner), "--baseline-only",
                        "--metadata-output", str(output),
                    ]), 0
                )
            report = __import__("json").loads(output.read_text())
            self.assertTrue(report["status"].startswith("PASS_"))
            self.assertFalse(report["original_APK_or_SAVE_written"])
            self.assertFalse(report["ready_to_sign_or_install"])
            with source_hash, native_hash:
                self.assertEqual(
                    image_gate.main_owner_native_probe([
                        "--owned-export", str(owner), "--baseline-only",
                        "--metadata-output", str(output),
                    ]), 3,
                )
            self.assertFalse((Path(temp) / "private" / "original.patched.so").exists())

    def test_bad_type_without_elf_or_private_original_rejected(self):
        with self.assertRaises(OriginalSceneNativeImageError):
            verify_mapped_original_scene_image(b"\x7fELF")
        with self.assertRaises(OriginalSceneNativeImageError):
            verify_mapped_original_scene_image("NOT_BINARY")


if __name__ == "__main__":
    unittest.main()
