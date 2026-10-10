"""Synthetic six-APK native observer opt-in packaging; no original user assets."""
from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import patch as mock_patch
import struct
import tempfile
import unittest
from zipfile import ZipFile, ZIP_STORED

from tools.base_mod import prepare_original_scene_witness as official_checker
from tools.base_mod.prepare_original_scene_witness import (
    APPROVED_FLAVOR, EXTRA_NATIVE_ENTRY, OriginalSceneWitnessPackageError,
    check_original_scene_witness_build_contract,
    include_reviewed_shadowhook_in_private_split_set,
)
from tools.base_mod.repack import JP_15_7_1_SPLITS


def synthetic_reviewed_arm64_so() -> bytes:
    """Pure SYNTHETIC ELF64 with six correctly defined FUNC dynsyms.

    Unlike arbitrary name strings in a fake ELF, the actual reviewed
    library must export these functions from .dynsym so dlsym() can find
    them. No owner's APK, SAVE, assets or a real third-party library used.
    """
    data = bytearray(4096)
    data[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<HHI", data, 16, 3, 183, 1)  # ET_DYN / AARCH64
    struct.pack_into("<Q", data, 40, 0x800)
    struct.pack_into("<HH", data, 58, 64, 3)
    names = (
        "shadowhook_init", "shadowhook_hook_sym_addr",
        "shadowhook_hook_func_addr", "shadowhook_hook_sym_addr_2",
        "shadowhook_hook_func_addr_2", "shadowhook_unhook",
    )
    names_blob = bytearray(b"\x00")
    for idx, name in enumerate(names, start=1):
        name_offset = len(names_blob)
        names_blob.extend(name.encode("ascii") + b"\x00")
        struct.pack_into(
            "<IBBHQQ", data, 0x200 + idx * 24,
            name_offset, 0x12, 0, 1, 0x1000 + idx * 16, 24
        )
    data[0x400:0x400 + len(names_blob)] = names_blob
    # Section 1 .dynsym (null + six GLOBAL/FUNC entries), section 2 dynstr.
    struct.pack_into(
        "<IIQQQQIIQQ", data, 0x800 + 64,
        0, 11, 0, 0, 0x200, (1+len(names))*24, 2, 0, 8, 24,
    )
    struct.pack_into(
        "<IIQQQQIIQQ", data, 0x800 + 128,
        0, 3, 0, 0, 0x400, len(names_blob), 0, 0, 1, 0,
    )
    return bytes(data)

def mock_shim(*, observer: bool, virgin_trial: bool = False) -> bytes:
    blob = bytearray(2048)
    blob[:4] = b"\x7fELF"
    blob[4:6] = b"\x02\x01"
    struct.pack_into("<H", blob, 18, 183)
    if virgin_trial:
        word = b"kneekura-original-virgin-save-trial-v1"
        blob[700:700+len(word)] = word
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
        # A synthetic test fixture cannot match a REAL official Maven
        # binary SHA. Override only during these explicit fixture tests.
        pinned = mock_patch.object(
            official_checker,
            "APPROVED_OFFICIAL_SHADOWHOOK_V201_ARM64_SHA256", self.sha,
        )
        pinned.start()
        self.addCleanup(pinned.stop)

    def contract(self, **changes):
        kwargs = dict(
            flavor=APPROVED_FLAVOR, no_internet=True,
            shim=self.shim, shadowhook=self.reviewed,
            shadowhook_sha256=self.sha,
        )
        kwargs.update(changes)
        return check_original_scene_witness_build_contract(**kwargs)

    def test_virgin_trial_shim_requires_explicit_matching_local_research_build(self):
        self.shim.write_bytes(mock_shim(observer=True, virgin_trial=True))
        valid = self.contract(virgin_save_trial=True)
        self.assertTrue(valid["research_virgin_SAVE_trial_compiled_and_explicit"])
        self.assertFalse(valid["original_virgin_first_SAVE_device_reloaded_verified"])
        with self.assertRaisesRegex(
            OriginalSceneWitnessPackageError, "matching explicit Java opt-in"
        ):
            self.contract()
        self.shim.write_bytes(mock_shim(observer=True, virgin_trial=False))
        with self.assertRaisesRegex(
            OriginalSceneWitnessPackageError, "matching explicit Java opt-in"
        ):
            self.contract(virgin_save_trial=True)
        self.shim.write_bytes(mock_shim(observer=True, virgin_trial=True))
        for changes in (
            {"no_internet": False},
            {"flavor": "personal"},
            {"shadowhook": None, "shadowhook_sha256": None},
        ):
            with self.subTest(changes=changes), self.assertRaises(
                OriginalSceneWitnessPackageError
            ):
                self.contract(virgin_save_trial=True, **changes)

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

    def test_unsymbolized_native_hook_needs_reviewed_func_addr_API(self):
        # Older ShadowHook libraries could expose sym_addr but not the
        # func_addr entrypoint. The four original stripped functions must
        # never attempt the sym_addr fallback.
        good = synthetic_reviewed_arm64_so()
        needle = b"shadowhook_hook_func_addr_2" + bytes((0,))
        self.assertEqual(good.count(needle), 1)
        self.reviewed.write_bytes(good.replace(needle, bytes(len(needle))))
        broken_digest = hashlib.sha256(self.reviewed.read_bytes()).hexdigest()
        with self.assertRaisesRegex(
            OriginalSceneWitnessPackageError, "hook ABI FUNC exports absent"
        ):
            self.contract(shadowhook_sha256=broken_digest)
        self.reviewed.write_bytes(good)
        self.assertTrue(self.contract()["research_scene_witness_build_enabled"])

    def test_fake_ELF_with_embedded_API_strings_but_no_dynsym_is_rejected(self):
        from tools.base_mod.prepare_original_scene_witness import _safe_native_so
        corrupted = bytearray(synthetic_reviewed_arm64_so())
        # Names still literally exist in the ELF, but the dynamic symbol
        # section is removed. Binary substring matching alone would PASS.
        struct.pack_into("<I", corrupted, 0x800 + 64 + 4, 0)
        self.reviewed.write_bytes(corrupted)
        digest = hashlib.sha256(corrupted).hexdigest()
        with self.assertRaisesRegex(
            OriginalSceneWitnessPackageError, "dynsym missing"
        ):
            _safe_native_so(self.reviewed, digest)

    def test_virgin_save_trial_requires_actual_audited_official_SHA(self):
        from tools.base_mod.prepare_original_scene_witness import (
            _safe_native_so,
        )
        # Artificial fixture digest accepted ONLY while test monkeypatch
        # replaces the production pin. Here explicitly restore true pin,
        # to guarantee no arbitrary signed-but-unreviewed library can write.
        with mock_patch.object(
            official_checker, "APPROVED_OFFICIAL_SHADOWHOOK_V201_ARM64_SHA256",
            "fc84287eac46e3bade2f7e07e3c9efdca005822e21191d6db5b8cb222d53e8a0",
        ):
            with self.assertRaisesRegex(
                OriginalSceneWitnessPackageError,
                "SHA-pinned official ShadowHook 2.0.1",
            ):
                _safe_native_so(
                    self.reviewed, self.sha, require_official_v201=True
                )

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
                needle = b"shadowhook_hook_sym_addr_2\x00"
                at = bad.find(needle)
                self.assertGreater(at, 0)
                bad[at] ^= 1
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
            "reviewed exact-address scene hook ABI changed",
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, verifier)


if __name__ == "__main__":
    unittest.main()
