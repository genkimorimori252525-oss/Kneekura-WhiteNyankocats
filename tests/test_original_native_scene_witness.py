"""Native-only JP15.7.1 scene ID recorder safety/ABI regressions.

Default runtime never builds or enables the optional observer. Host gcc tests
compile only synthetic opt-in source with an Android-log header stub; they do
NOT install ShadowHook, run a Battle Cats binary or access a device/SAVE.
"""
from __future__ import annotations

import ctypes
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "native" / "kneekura-shim"
POLICY = NATIVE / "src" / "kneekura_scene_witness_policy.c"
WITNESS = NATIVE / "src" / "kneekura_original_scene_witness.c"
CMAKE = NATIVE / "CMakeLists.txt"


class OriginalNativeSceneResearchObserverTests(unittest.TestCase):
    def test_default_native_shim_build_does_not_include_instrumentation(self):
        cmake = CMAKE.read_text(encoding="utf-8")
        self.assertIn("option(KNEEKURA_RESEARCH_SCENE_WITNESS", cmake)
        self.assertIn("research-only", cmake.lower())
        self.assertIn("OFF)", cmake)
        self.assertIn("if(KNEEKURA_RESEARCH_SCENE_WITNESS)", cmake)
        self.assertIn('NOT ANDROID OR NOT ANDROID_ABI STREQUAL "arm64-v8a"', cmake)
        self.assertIn("KNEEKURA_RESEARCH_SCENE_WITNESS=1", cmake)
        # No baseline mutation of the production native shim feature mask.
        default_shim = (NATIVE / "src" / "kneekura_shim.c").read_text(encoding="utf-8")
        self.assertIn("KNEEKURA_DEFAULT_FEATURE_MASK", default_shim)
        self.assertNotIn("kneekura_original_scene_witness", default_shim)
        self.assertNotIn("shadowhook_hook", default_shim)

    def test_opt_in_native_scene_observer_requires_original_id_and_package(self):
        code = WITNESS.read_text(encoding="utf-8")
        self.assertIn('#define EXACT_LOCAL_PROCESS "jp.kn.local.battlecats"', code)
        self.assertIn("current_process_is_isolated_original_research()", code)
        self.assertIn("kPinnedNativeBuildId", code)
        self.assertIn("note_has_exact_build_id", code)
        for offset in ("0x31755C", "0x71BF24", "0x71C408", "0x71C458", "0x3480"):
            self.assertIn(offset, code)
        self.assertIn("source_words_match_exact_original", code)
        self.assertIn("hook_sym_name", code)
        self.assertIn("research_draw_proxy", code)
        self.assertIn("original_draw(jni_env, jni_class);", code)
        self.assertIn("get_game_context()", code)
        self.assertIn("original-native-scene-v1 id=%u", code)
        # These are not APIs for any original game SAVE mutation, online login
        # or original anti-BAN workarounds.
        self.assertNotIn("fwrite(", code)
        self.assertNotIn("remove(", code)
        self.assertNotIn("unlink(", code)
        self.assertNotIn("newHttpRequest(", code)

    def test_native_scene_policy_only_allows_five_source_pinned_scene_ids(self):
        compiler = shutil.which("gcc") or shutil.which("clang")
        if not compiler:
            self.skipTest("C compiler unavailable")
        with tempfile.TemporaryDirectory() as folder:
            lib = Path(folder) / "libpolicy.so"
            result = subprocess.run(
                [compiler, "-std=c11", "-Wall", "-Wextra", "-Werror",
                 "-shared", "-fPIC", "-I", str(NATIVE / "include"),
                 str(POLICY), "-o", str(lib)],
                capture_output=True, text=True, timeout=40,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            dll = ctypes.CDLL(str(lib))
            predicate = dll.kneekura_scene_witness_should_emit
            predicate.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
            predicate.restype = ctypes.c_int
            for scene in (4, 97, 101, 102, 104):
                self.assertEqual(predicate(0xFFFFFFFF, scene), 1)
                self.assertEqual(predicate(scene, scene), 0)
            for scene in (0, 1, 2, 3, 5, 96, 98, 100, 103, 105, 200, 65535):
                self.assertEqual(predicate(0xFFFFFFFF, scene), 0)
            self.assertEqual(predicate(102, 101), 1)
            self.assertEqual(predicate(101, 102), 1)
            self.assertEqual(predicate(104, 97), 1)

    def test_research_native_hook_compiles_in_mocked_android_headers_no_ndk_or_source_asset(self):
        compiler = shutil.which("gcc") or shutil.which("clang")
        if not compiler:
            self.skipTest("C compiler unavailable")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            headers = root / "android"
            headers.mkdir(parents=True)
            (headers / "log.h").write_text(
                "#ifndef MOCK_ANDROID_LOG_H\n#define MOCK_ANDROID_LOG_H\n"
                "#define ANDROID_LOG_INFO 4\n"
                "int __android_log_write(int priority, const char* tag, "
                "const char* message);\n"
                "#endif\n",
                encoding="utf-8",
            )
            compile_step = subprocess.run(
                [compiler, "-std=c11", "-Wall", "-Wextra", "-Werror",
                 "-fsyntax-only", "-D__ANDROID__", "-D__aarch64__",
                 "-DKNEEKURA_RESEARCH_SCENE_WITNESS=1",
                 "-I", str(root), "-I", str(NATIVE / "include"),
                 str(WITNESS)],
                capture_output=True, text=True, timeout=40,
            )
            self.assertEqual(compile_step.returncode, 0, compile_step.stderr)

    def test_without_research_flag_compile_is_rejected_before_any_hook(self):
        compiler = shutil.which("gcc") or shutil.which("clang")
        if not compiler:
            self.skipTest("C compiler unavailable")
        result = subprocess.run(
            [compiler, "-std=c11", "-fsyntax-only", str(WITNESS)],
            capture_output=True, text=True, timeout=40,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Never compile the original scene witness", result.stderr)


if __name__ == "__main__":
    unittest.main()
