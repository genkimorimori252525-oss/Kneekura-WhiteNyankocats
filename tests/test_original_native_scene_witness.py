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
        for exact_address in ("0x53B2BC", "0x53BE0C", "0x8B9FC8"):
            self.assertIn(exact_address, code)
        for proxy in ("research_original_cap_getter_proxy",
                      "research_original_upgrade_gate_proxy",
                      "research_original_save_wrapper_proxy"):
            self.assertIn(proxy, code)
        self.assertIn("gOriginalCapGetter", code)
        self.assertIn("gOriginalUpgradeGate", code)
        self.assertIn("gOriginalSaveWrapper", code)
        self.assertIn("gSaveHookStub", code)
        self.assertIn("gUpgradeHookStub", code)
        self.assertIn("gCapHookStub", code)
        self.assertIn("original-native-save-wrapper-v1 original-returned", code)
        self.assertIn("int rollback_failed = 0;", code)
        self.assertIn("shadowhook_hook_sym_addr", code)
        self.assertNotIn('"shadowhook_hook_sym_name"', code)
        self.assertIn("witness.base + ORIGINAL_JNI_DRAW", code)
        self.assertIn("research_draw_proxy", code)
        self.assertIn("shadowhook_unhook", code)
        self.assertIn("original-native-scene-hook-v1 partial-unhook-failed", code)
        self.assertIn("original_draw(jni_env, jni_class);", code)
        self.assertIn("result = original(asset_index);", code)
        self.assertIn("result = original(context);", code)
        self.assertIn("return result;", code)
        self.assertIn("get_game_context()", code)
        self.assertIn("original-native-scene-v1 id=%u", code)
        # These are not APIs for any original game SAVE mutation, online login
        # or original anti-BAN workarounds.
        self.assertNotIn("fwrite(", code)
        self.assertNotIn("remove(", code)
        self.assertNotIn("unlink(", code)
        self.assertNotIn("newHttpRequest(", code)

    def test_native_loader_walks_all_elf_modules_before_uniqueness_decision(self):
        """Do not stop at first basename match and miss a duplicate ELF.

        dl_iterate_phdr expects a ZERO callback result to continue walking.
        This regression caught an earlier first-match early return of 1.
        """
        code = WITNESS.read_text(encoding="utf-8")
        callback = code.split(
            "static int inspect_original_library(", 1
        )[1].split("static int source_words_match_exact_original(", 1)[0]
        self.assertIn("witness->original_library_count++", callback)
        self.assertIn("witness->exact_build_id_count++", callback)
        self.assertNotIn("return 1;", callback)
        self.assertGreaterEqual(callback.count("return 0;"), 3)
        self.assertIn("witness.original_library_count != 1u", code)
        self.assertIn("witness.exact_build_id_count != 1u", code)

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

    def test_optimized_research_elf_keeps_public_identity_and_scene_markers(self):
        """Build an optimized host-only mock ELF; marker must survive -O2/GC.

        This doesn't constitute a genuine Android ABI or JNI runtime test.
        """
        compiler = shutil.which("gcc") or shutil.which("clang")
        if not compiler:
            self.skipTest("host C compiler unavailable")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            android_dir = root / "android"
            android_dir.mkdir()
            (android_dir / "log.h").write_text(
                "#define ANDROID_LOG_INFO 4\n"
                "int __android_log_write(int, const char*, const char*);\n",
                encoding="utf-8",
            )
            (root / "logger.c").write_text(
                "int __android_log_write(int level, const char *tag, "
                "const char *message) {"
                "(void)level;(void)tag;(void)message;return 0;}",
                encoding="utf-8",
            )
            so = root / "libscene-witness-optimized-mock.so"
            build = subprocess.run(
                [compiler, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                 "-fvisibility=hidden", "-ffunction-sections", "-fdata-sections",
                 "-fPIC", "-shared", "-Wl,--gc-sections",
                 "-D__ANDROID__", "-D__aarch64__",
                 "-DKNEEKURA_RESEARCH_SCENE_WITNESS=1",
                 "-I", str(root), "-I", str(NATIVE / "include"),
                 str(WITNESS), str(POLICY), str(root / "logger.c"), "-ldl",
                 "-o", str(so)],
                capture_output=True, text=True, timeout=50,
            )
            self.assertEqual(build.returncode, 0, build.stderr)
            # No 'nm' or 'strings' subprocesses: these may be delayed by
            # slow shared runners, while exact ARM64 symbol visibility is
            # independently checked via readelf in build-kneekura-shim.yml.
            optimized_binary = so.read_bytes()
            self.assertIn(
                b"kneekura_scene_research_package_identity", optimized_binary
            )
            self.assertIn(
                b"kneekura_scene_research_event_format", optimized_binary
            )
            self.assertIn(b"jp.kn.local.battlecats", optimized_binary)
            self.assertIn(b"original-native-scene-v1 id=%u", optimized_binary)

    def test_research_level_proxies_forward_original_inputs_returns_and_log_once(self):
        """Executable HOST-C ABI regression, not original-device gameplay.

        Include the existing native witness C in a local temporary program.
        Stub ONLY the Android log API and original functions; never load
        copyrighted game code, a third-party hook, APK or user SAVE.
        """
        compiler = shutil.which("gcc") or shutil.which("clang")
        if not compiler:
            self.skipTest("host C compiler unavailable")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "android").mkdir()
            (root / "android" / "log.h").write_text(
                "#ifndef KNEEKURA_TEST_ANDROID_LOG_H\n"
                "#define KNEEKURA_TEST_ANDROID_LOG_H\n"
                "#define ANDROID_LOG_INFO 4\n"
                "int __android_log_write(int, const char *, const char *);\n"
                "#endif\n",
                encoding="utf-8",
            )
            witness_path = str(WITNESS).replace("\\\\", "/")
            harness = r'''
#define _GNU_SOURCE
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "'''+witness_path+r'''"
static int cap_arg = -1, gate_arg = -1;
static void *save_arg = NULL;
static int cap_count = 0, gate_count = 0, save_count = 0;
static int32_t original_cap(int32_t idx) {
    cap_arg = idx;
    return idx + 170;
}
static int32_t original_gate(int32_t idx) {
    gate_arg = idx;
    return (idx == 101) ? 1 : 0;
}
static int32_t original_save(void *ctx) {
    save_arg = ctx;
    return 1;
}
int __android_log_write(int priority, const char *tag, const char *msg) {
    if (priority != ANDROID_LOG_INFO ||
        strcmp(tag, "KNEEKURA_STATIC_HTTP") != 0) return -1;
    if (strcmp(msg, "original-native-level-cap-getter-v1 original-returned") == 0) {
        cap_count++;
    } else if (strcmp(msg,
              "original-native-upgrade-gate-v1 original-returned") == 0) {
        gate_count++;
    } else if (strcmp(msg,
              "original-native-save-wrapper-v1 original-returned") == 0) {
        save_count++;
    }
    return 0;
}
int main(void) {
    int sentinel = 42;
    gOriginalCapGetter = (void *)&original_cap;
    gOriginalUpgradeGate = (void *)&original_gate;
    gOriginalSaveWrapper = (void *)&original_save;
    if (research_original_cap_getter_proxy(5) != 175 || cap_arg != 5) return 1;
    if (research_original_cap_getter_proxy(6) != 176 || cap_arg != 6) return 2;
    if (research_original_upgrade_gate_proxy(101) != 1 || gate_arg != 101) return 3;
    if (research_original_upgrade_gate_proxy(22) != 0 || gate_arg != 22) return 4;
    if (research_original_save_wrapper_proxy(&sentinel) != 1 ||
        save_arg != &sentinel) return 5;
    if (research_original_save_wrapper_proxy(&sentinel) != 1) return 6;
    if (cap_count != 1 || gate_count != 1 || save_count != 1) return 7;
    return 0;
}
'''
            source = root / "check_original_proxies.c"
            executable = root / "check_original_proxies"
            source.write_text(harness, encoding="utf-8")
            built = subprocess.run(
                [compiler, "-std=c11", "-Wall", "-Wextra", "-Werror",
                 "-D__ANDROID__", "-D__aarch64__",
                 "-DKNEEKURA_RESEARCH_SCENE_WITNESS=1",
                 "-I", str(root), "-I", str(NATIVE / "include"),
                 str(source), str(POLICY), "-ldl",
                 "-o", str(executable)],
                capture_output=True, text=True, timeout=45,
            )
            self.assertEqual(built.returncode, 0, built.stderr)
            run = subprocess.run(
                [str(executable)], capture_output=True, text=True, timeout=15
            )
            self.assertEqual(run.returncode, 0, run.stderr)

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
