"""Pure-source and host C tests of research-only original scene97 resolver observer.

These tests never read the owner APK, Android, SAVE, or a network endpoint.
The four whole numbers summarize 35 source-resolver returns (-1, 0, 1, other),
NOT real game download task completion.
"""
from __future__ import annotations

import ctypes
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tools.base_mod.audit_original_offline_boot_events import (
    OriginalOfflineRuntimeProofBlocked,
    summarize_runtime_events,
)

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "native/kneekura-shim"
CONTRACT = NATIVE / "src/kneekura_scene97_resolver_probe.c"
WITNESS = NATIVE / "src/kneekura_original_scene_witness.c"


class Histogram(ctypes.Structure):
    _fields_ = [
        ("missing", ctypes.c_uint32), ("zero", ctypes.c_uint32),
        ("one", ctypes.c_uint32), ("other", ctypes.c_uint32),
    ]


class OriginalScene97ResolverResearchTests(unittest.TestCase):
    def test_host_c_histogram_is_bounded_and_does_not_read_other_memory(self):
        compiler = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
        if not compiler:
            self.skipTest("host C compiler unavailable")
        with tempfile.TemporaryDirectory(prefix="kn-original-resolver-pure-") as folder:
            library = Path(folder) / ("histogram.dll" if __import__("os").name == "nt" else "histogram.so")
            args = [
                compiler, "-std=c11", "-Wall", "-Wextra", "-Werror",
                "-shared", "-fPIC", "-I", str(NATIVE / "include"),
                str(CONTRACT), "-o", str(library),
            ]
            result = subprocess.run(
                args, capture_output=True, text=True,
                errors="replace", timeout=40)
            self.assertEqual(result.returncode, 0, result.stderr)
            dll = ctypes.CDLL(str(library))
            histogram = dll.kneekura_scene97_resolver_histogram
            histogram.argtypes = [
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t,
                ctypes.POINTER(Histogram),
            ]
            histogram.restype = ctypes.c_int
            signature = dll.kneekura_scene97_resolver_histogram_signature
            signature.argtypes = [ctypes.POINTER(Histogram)]
            signature.restype = ctypes.c_uint32

            examples = [-1] * 11 + [0] * 20 + [1] * 3 + [71]
            self.assertEqual(len(examples), 35)
            data = (ctypes.c_int32 * 35)(*examples)
            source = ctypes.cast(data, ctypes.POINTER(ctypes.c_uint8))
            summary = Histogram()
            self.assertEqual(histogram(source, ctypes.sizeof(data),
                                       ctypes.byref(summary)), 1)
            self.assertEqual(tuple(getattr(summary, name) for name, _ in Histogram._fields_),
                             (11, 20, 3, 1))
            self.assertEqual(
                signature(ctypes.byref(summary)),
                11 | (20 << 6) | (3 << 12) | (1 << 18),
            )
            untouched = Histogram(99, 99, 99, 99)
            self.assertEqual(histogram(source, ctypes.sizeof(data) - 1,
                                       ctypes.byref(untouched)), 0)
            self.assertEqual(tuple(getattr(untouched, name) for name, _ in Histogram._fields_),
                             (99, 99, 99, 99))
            self.assertEqual(histogram(None, ctypes.sizeof(data),
                                       ctypes.byref(untouched)), 0)
            invalid = Histogram(36, 0, 0, 0)
            self.assertEqual(signature(ctypes.byref(invalid)), 0xFFFFFFFF)

    def test_same_original_research_draw_hook_and_explicit_source_sites(self):
        code = WITNESS.read_text(encoding="utf-8")
        cmake = (NATIVE / "CMakeLists.txt").read_text(encoding="utf-8")
        self.assertIn("KNEEKURA_RESEARCH_SCENE_WITNESS", cmake)
        self.assertIn("OFF)", cmake)
        self.assertIn("src/kneekura_scene97_resolver_probe.c", cmake)
        self.assertIn("ORIGINAL_SCENE97_RESOLVER_SLOT_OFFSET = 0x2FB8", code)
        self.assertIn("{0x73CA20u, 0x5285F70Au}", code)
        self.assertIn("{0x73CAB0u, 0xB8357B40u}", code)
        self.assertIn("original_draw(jni_env, jni_class);", code)
        self.assertIn("observe_original_scene97_resolver_histogram(context, scene);", code)
        self.assertIn("scene != 97u", code)
        self.assertIn("gAllOriginalHooksInstalled", code)
        self.assertIn("nth >= 4u", code)
        self.assertIn("original-native-scene97-resolver-v1 missing=%u zero=%u one=%u other=%u", code)
        # This is NOT an extra hook or an original first-run SAVE transaction.
        self.assertEqual(code.count("= hook_func_fn("), 4)
        self.assertNotIn("original-native-scene97-resolver-v1", 
                         (NATIVE / "src/kneekura_shim.c").read_text(encoding="utf-8"))

    def test_owner_observed_internet_error_is_not_fake_native_gate_proof(self):
        raw = "\n".join([
            "I KNEEKURA_STATIC_HTTP: original-native-scene-v1 id=102",
            "I KNEEKURA_STATIC_HTTP: original-native-scene-v1 id=101",
            "I KNEEKURA_STATIC_HTTP: original-native-scene-v1 id=97",
            "I KNEEKURA_STATIC_HTTP: original-local-network-availability-v1 offline",
            "I KNEEKURA_STATIC_HTTP: original-local-backup-callback-v1 returned",
            "I KNEEKURA_STATIC_HTTP: original-local-backup-callback-v1 returned",
            "I KNEEKURA_STATIC_HTTP: original-local-import-v1 already-complete",
            "I KNEEKURA_STATIC_HTTP: original-native-scene97-resolver-v1 missing=11 zero=20 one=3 other=1",
            "I KNEEKURA_STATIC_HTTP: original-native-scene97-resolver-v1 missing=0 zero=0 one=35 other=0",
            "I KNEEKURA_STATIC_HTTP: original-native-scene97-resolver-v1 missing=36 zero=0 one=0 other=0",
            "I KNEEKURA_STATIC_HTTP: original-native-scene97-resolver-v1 missing=1 zero=0 one=33 other=TOKEN",
            "I KNEEKURA_STATIC_HTTP: original-native-scene97-resolver-v1 missing=4 zero=4 one=4 other=4",
        ])
        report = summarize_runtime_events(
            raw, owner_final_screen="internet-unavailable",
            owner_reported_615mb_request_passed=True,
        )
        self.assertEqual(report["status"], "ORIGINAL_393_IMPORTED_SCENE97_STILL_LAST_OBSERVED")
        self.assertTrue(report["owner_observed_offline_error_during_scene97"])
        self.assertEqual(report["owner_observed_final_screen"], "internet-unavailable")
        self.assertTrue(report["owner_reported_615mb_request_dialog_passed"])
        self.assertEqual(report["exact_backup_original_network_failure_callbacks_completed"], 2)
        self.assertEqual(report["scene97_native_resolver_last_histogram"],
                         {"missing": 0, "zero": 0, "one": 35, "other": 0})
        self.assertEqual(len(report["scene97_native_resolver_status_histograms"]), 2)
        self.assertTrue(report["scene97_resolver_return_values_are_not_download_completion"])
        self.assertFalse(report["screen_message_source_or_native_version_check_proven"])
        self.assertFalse(report["original_scene97_completed_successfully_proven"])
        self.assertFalse(report["original_cat_base_visible_proven"])
        self.assertNotIn("TOKEN",repr(report))

    def test_invalid_ui_observation_rejected_without_leaking_arbitrary_text(self):
        with self.assertRaises(OriginalOfflineRuntimeProofBlocked):
            summarize_runtime_events(
                "KNEEKURA_STATIC_HTTP: original-native-scene-v1 id=97",
                owner_final_screen="http://example.invalid/private")
        with self.assertRaises(OriginalOfflineRuntimeProofBlocked):
            summarize_runtime_events("", owner_reported_615mb_request_passed="yes")


if __name__ == "__main__":
    unittest.main()
