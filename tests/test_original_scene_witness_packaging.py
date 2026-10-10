"""Synthetic six-APK native observer opt-in packaging; no original user assets."""
from __future__ import annotations

import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
from zipfile import ZipFile, ZIP_STORED

from tools.base_mod.prepare_original_scene_witness import (
    APPROVED_FLAVOR, EXTRA_NATIVE_ENTRY, OriginalSceneWitnessPackageError,
    check_original_scene_witness_build_contract,
    include_reviewed_shadowhook_in_private_split_set,
)
from tools.base_mod.repack import JP_15_7_1_SPLITS


def synthetic_reviewed_arm64_so() -> bytes:
    """One synthetic *non-executable* ELF stub with only the guard identifiers."""
    data = bytearray(4096)
    data[:4] = b"\x7fELF"
    data[4] = 2
    data[5] = 1
    struct.pack_into("<H", data, 16, 3)       # ET_DYN
    struct.pack_into("<H", data, 18, 183)     # AArch64
    data[100:116] = b"shadowhook_init\x00"
    data[180:205] = b"shadowhook_hook_sym_name\x00"
    return bytes(data)


def mock_shim(*, observer: bool) -> bytes:
    blob = bytearray(2048)
    blob[:4] = b"\x7fELF"
    blob[4:6] = b"\x02\x01"
    struct.pack_into("<H", blob, 18, 183)
    if observer:
        blob[256:256+len(b"original-native-scene-v1 id=%u")] = (
            b"original-native-scene-v1 id=%u"
        )
        blob[400:400+len(b"jp.kn.local.battlecats")] = (
            b"jp.kn.local.battlecats"
        )
    return bytes(blob)


class OriginalNativeSceneWitnessPackagingTests(unittest.TestCase):
    def setUp(self):
        self.private = tempfile.TemporaryDirectory()
        self.addCleanup(self.private.cleanup)
        self.root = Path(self.private.name)
        self.shim = self.root / "research-kneekura.so"
        self.shim.write_bytes(mock_shim(observer=True))
        self.reviewed = self.root / "libshadowhook.so"
        self.reviewed.write_bytes(synthetic_reviewed_arm64_so())
        self.sha = hashlib.sha256(self.reviewed.read_bytes()).hexdigest()

    def contract(self, **changes):
        kwargs = dict(
            flavor=APPROVED_FLAVOR, no_internet=True,
            shim=self.shim, shadowhook=self.reviewed,
            shadowhook_sha256=self.sha,
        )
        kwargs.update(changes)
        return check_original_scene_witness_build_contract(**kwargs)

    def test_explicit_opt_in_requires_exact_local_research_no_internet(self):
        valid = self.contract()
        self.assertTrue(valid["research_scene_witness_build_enabled"])
        self.assertTrue(valid["research_original_native_scene_hook_runtime_supplied"])
        self.assertFalse(valid["native_scene101_102_runtime_observed"])
        for mode in (
            {"flavor": "personal"},
            {"flavor": "practice"},
            {"flavor": "research"},
            {"no_internet": False},
            {"shadowhook": None},
            {"shadowhook_sha256": None},
        ):
            with self.subTest(mode=mode), self.assertRaises(
                OriginalSceneWitnessPackageError
            ):
                self.contract(**mode)

    def test_compiled_observer_without_explicit_reviewed_library_fails(self):
        with self.assertRaises(OriginalSceneWitnessPackageError):
            self.contract(shadowhook=None, shadowhook_sha256=None)
        self.shim.write_bytes(mock_shim(observer=False))
        with self.assertRaises(OriginalSceneWitnessPackageError):
            self.contract()
        normal = self.contract(shadowhook=None, shadowhook_sha256=None)
        self.assertFalse(normal["research_scene_witness_build_enabled"])
        self.assertFalse(normal["research_original_native_scene_hook_runtime_supplied"])

    def test_bad_hash_elf_arch_and_exports_fail_before_staging(self):
        with self.assertRaisesRegex(OriginalSceneWitnessPackageError, "hash mismatched"):
            self.contract(shadowhook_sha256="0"*64)
        for mutate in ("elf_magic", "elf_32bit", "elf_x86", "not_dso", "missing_export"):
            self.reviewed.write_bytes(synthetic_reviewed_arm64_so())
            bad = bytearray(self.reviewed.read_bytes())
            if mutate == "elf_magic":
                bad[0] = 0
            if mutate == "elf_32bit":
                bad[4] = 1
            if mutate == "elf_x86":
                struct.pack_into("<H", bad, 18, 62)
            if mutate == "not_dso":
                struct.pack_into("<H", bad, 16, 2)
            if mutate == "missing_export":
                bad[180] ^= 1
            self.reviewed.write_bytes(bad)
            with self.subTest(mutation=mutate), self.assertRaises(
                OriginalSceneWitnessPackageError
            ):
                self.contract(
                    shadowhook_sha256=hashlib.sha256(bad).hexdigest()
                )

    def test_packaging_adds_only_one_library_in_arm64_of_all_six_splits(self):
        source = self.root / "original-fixture"
        output = self.root / "private-research-only"
        source.mkdir()
        for filename in JP_15_7_1_SPLITS:
            with ZipFile(source / filename, "w") as z:
                z.writestr("AndroidManifest.xml", b"PRIVATE_SYNTHETIC_MANIFEST")
                z.writestr("assets/fixture.txt", b"UNMODIFIED_FIXTURE")
        receipts = include_reviewed_shadowhook_in_private_split_set(
            source, output, shadowhook=self.reviewed, expected_sha256=self.sha
        )
        self.assertEqual(receipts["original_split_count"], 6)
        self.assertEqual(receipts["only_extra_entry"], EXTRA_NATIVE_ENTRY)
        self.assertFalse(receipts["scene_observer_runtime_or_original_gameplay_verified"])
        for filename in JP_15_7_1_SPLITS:
            with ZipFile(source/filename, "r") as original, ZipFile(output/filename, "r") as private:
                self.assertEqual(private.read("AndroidManifest.xml"),
                                 original.read("AndroidManifest.xml"))
                self.assertEqual(private.read("assets/fixture.txt"),
                                 original.read("assets/fixture.txt"))
                self.assertNotIn(EXTRA_NATIVE_ENTRY, original.namelist())
                if filename == "split_config.arm64_v8a.apk":
                    self.assertEqual(private.read(EXTRA_NATIVE_ENTRY),
                                     self.reviewed.read_bytes())
                    self.assertEqual(private.getinfo(EXTRA_NATIVE_ENTRY).compress_type,
                                     ZIP_STORED)
                else:
                    self.assertNotIn(EXTRA_NATIVE_ENTRY, private.namelist())

    def test_reject_occupied_destination_missing_owner_split_or_double_library(self):
        source = self.root / "original-fixture"
        source.mkdir()
        for filename in JP_15_7_1_SPLITS:
            with ZipFile(source/filename, "w") as z:
                z.writestr("AndroidManifest.xml", b"SYNTHETIC")
        occupied = self.root / "occupied"
        occupied.mkdir()
        with self.assertRaises(OriginalSceneWitnessPackageError):
            include_reviewed_shadowhook_in_private_split_set(
                source, occupied, shadowhook=self.reviewed, expected_sha256=self.sha
            )
        missing = self.root / "missing"
        (source / "split_InstallPack.apk").unlink()
        with self.assertRaises(OriginalSceneWitnessPackageError):
            include_reviewed_shadowhook_in_private_split_set(
                source, missing, shadowhook=self.reviewed, expected_sha256=self.sha
            )
        self.assertFalse(missing.exists())

    def test_build_pipeline_and_parity_fail_closed_source_contract(self):
        root = Path(__file__).resolve().parents[1]
        builder = (root/"tools/base_mod/build_owned_static_http_bridge.py").read_text(
            encoding="utf-8"
        )
        verifier = (root/"tools/base_mod/verify_static_http_bridge.py").read_text(
            encoding="utf-8"
        )
        for needle in (
            "check_original_scene_witness_build_contract",
            "include_reviewed_shadowhook_in_private_split_set",
            "research_shadowhook_sha256",
            "--research-shadowhook-so",
            "research_scene_witness=",
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, builder)
        for needle in (
            "research_scene_witness",
            "EXTRA_NATIVE_ENTRY",
            "SCENE_WITNESS_COMPILED_MARKER",
            "research_shadowhook_sha256",
            "verify_mapped_original_scene_image",
            "repackaged_original_native_scene_layout",
            "unexpectedly changed",
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, verifier)


if __name__ == "__main__":
    unittest.main()
