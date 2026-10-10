"""Executable HOST C test of opt-in native virgin transaction; synthetic SAVE only.

Never loads real Battle Cats assets, private original SAVE, APK or publisher account.
The host harness substitutes the ARM64 native source *caller's return address*
with its pinned synthetic address. Actual ARM64 caller verification stays intact
in the production source and must still be proven on the owner's device.
"""
from __future__ import annotations
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "native" / "kneekura-shim"
WITNESS = NATIVE / "src" / "kneekura_original_scene_witness.c"
POLICY = NATIVE / "src" / "kneekura_scene_witness_policy.c"

FAKE_JNI = r"""
#ifndef KNEEKURA_SYNTH_JNI_H
#define KNEEKURA_SYNTH_JNI_H
#define JNI_FALSE 0
#define JNI_TRUE 1
#define JNIEXPORT __attribute__((visibility("default")))
#define JNICALL
typedef void *jclass;
typedef void *jstring;
typedef unsigned char jboolean;
typedef struct JNINativeInterface_ *JNIEnv;
struct JNINativeInterface_ {
 const char *(*GetStringUTFChars)(JNIEnv *, jstring, jboolean *);
 void (*ReleaseStringUTFChars)(JNIEnv *, jstring, const char *);
};
#endif
"""

FAKE_LOG = r"""
#ifndef KNEEKURA_SYNTH_ANDROID_LOG_H
#define KNEEKURA_SYNTH_ANDROID_LOG_H
#define ANDROID_LOG_INFO 4
int __android_log_write(int, const char *, const char *);
#endif
"""

HARNESS = r"""
static int native_read_calls, native_write_calls, native_events;
static int force_writer_error;
static int32_t fake_original_loader(void *ctx) {
    if (ctx == NULL) return 0;
    native_read_calls++;
    struct stat item = {0};
    return (fstatat(gVirginRootFd, "SAVE_DATA", &item, AT_SYMLINK_NOFOLLOW) == 0
            && S_ISREG(item.st_mode) && item.st_size == 4) ? 1 : 0;
}
static int32_t fake_original_writer(void *ctx) {
    if (ctx == NULL) return 0;
    native_write_calls++;
    if (force_writer_error) return 0;
    const int f = openat(gVirginRootFd, "SAVE_DATA",
                         O_CREAT | O_EXCL | O_WRONLY | O_CLOEXEC, 0600);
    if (f < 0) return 0;
    int ok = write(f, "TEST", 4) == 4;
    if (close(f) != 0) ok = 0;
    return ok;
}
int __android_log_write(int prio, const char *tag, const char *msg) {
    if (prio == ANDROID_LOG_INFO
        && strcmp(tag, "KNEEKURA_STATIC_HTTP") == 0
        && strcmp(msg, "original-native-virgin-save-trial-v1 read-accepted") == 0)
        native_events++;
    return 0;
}
int main(void) {
    if (!exact_private_original_root_path("/data/user/0/jp.kn.local.battlecats/files")
        || !exact_private_original_root_path("/data/data/jp.kn.local.battlecats/files")
        || exact_private_original_root_path("/data/user/x/jp.kn.local.battlecats/files")
        || exact_private_original_root_path("/data/user/0/jp.co.ponos.battlecats/files")
        || exact_private_original_root_path("/tmp/fake/jp.kn.local.battlecats/files"))
        return 1;

    char template[] = "/tmp/kn-synth-original-XXXXXX";
    char *dir = mkdtemp(template);
    if (dir == NULL) return 2;
    int fd = open(dir, O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) return 3;
    const int marker = openat(fd, ".kneekura-virgin-local-jp15-7-1",
                              O_CREAT | O_EXCL | O_WRONLY | O_CLOEXEC, 0600);
    if (marker < 0) return 4;
    close(marker);
    gVirginRootFd = fd;
    gVirginTrialState = VIRGIN_TRIAL_ATTESTED;
    gOriginalLoadBias = 1;
    gOriginalVmaShift = 0;
    gShadowHookLibrary = (void *)1;
    gOriginalAppLaunchLoader = (void *)&fake_original_loader;
    gOriginalSaveWrapper = (void *)&fake_original_writer;
    if (!virgin_source_root_remains_trusted()) return 5;

    int sentinel = 1001;
    if (research_original_app_launch_read_proxy(&sentinel) != 1) return 6;
    if (native_read_calls != 2 || native_write_calls != 1
        || native_events != 1 || gVirginTrialState != VIRGIN_TRIAL_COMPLETED)
        return 7;
    if (research_original_app_launch_read_proxy(&sentinel) != 1) return 8;
    if (native_write_calls != 1) return 9; /* no duplicate SAVE */
    if (virgin_save_files_all_absent(fd)) return 10;
    if (unlinkat(fd, "SAVE_DATA", 0) != 0) return 11;

    /* Writer failure must NEVER be forged into a successful game read. */
    gVirginTrialState = VIRGIN_TRIAL_ATTESTED;
    force_writer_error = 1;
    int prev_writes = native_write_calls;
    if (research_original_app_launch_read_proxy(&sentinel) != 0) return 12;
    if (gVirginTrialState != VIRGIN_TRIAL_BLOCKED) return 13;
    if (native_write_calls != prev_writes + 1) return 14;
    if (research_original_app_launch_read_proxy(&sentinel) != 0
        || native_write_calls != prev_writes + 1) return 15;

    /* Existing variant files block a supposedly 'virgin' root. */
    const int stale = openat(fd, "SAVE_DATA.bak",
                             O_CREAT | O_EXCL | O_WRONLY, 0600);
    if (stale < 0) return 16;
    close(stale);
    if (virgin_source_root_remains_trusted()) return 17;
    if (unlinkat(fd, "SAVE_DATA.bak", 0) != 0) return 18;

    if (unlinkat(fd, ".kneekura-virgin-local-jp15-7-1", 0) != 0) return 19;
    close(fd);
    if (rmdir(dir) != 0) return 20;
    return 0;
}
"""

class SyntheticNativeOriginalVirginSaveTrialTests(unittest.TestCase):
    def test_real_native_trial_compiles_and_calls_fake_original_writer_exactly_once(self):
        compiler = shutil.which("gcc") or shutil.which("clang")
        if compiler is None:
            self.skipTest("host C compiler absent")
        source = WITNESS.read_text(encoding="utf-8")
        actual_caller = "const uintptr_t caller = (uintptr_t)__builtin_return_address(0);"
        self.assertEqual(source.count(actual_caller), 1)
        source = source.replace(
            actual_caller,
            "const uintptr_t caller = gOriginalLoadBias "
            "+ ORIGINAL_APP_LAUNCH_READ_CALL + 4u + gOriginalVmaShift;",
        )
        with tempfile.TemporaryDirectory(prefix="kn-original-trial-test-") as name:
            tmp = Path(name)
            (tmp / "android").mkdir()
            (tmp / "jni.h").write_text(FAKE_JNI, encoding="utf-8")
            (tmp / "android" / "log.h").write_text(FAKE_LOG, encoding="utf-8")
            c = tmp / "synthetic_native_trial.c"
            c.write_text(source + "\n" + HARNESS, encoding="utf-8")
            exe = tmp / "synthetic_original_native_trial"
            built = subprocess.run(
                [compiler, "-std=c11", "-Wall", "-Wextra", "-Werror",
                 "-D__ANDROID__", "-D__aarch64__",
                 "-DKNEEKURA_RESEARCH_SCENE_WITNESS=1",
                 "-DKNEEKURA_RESEARCH_VIRGIN_SAVE_TRIAL=1",
                 "-I", str(tmp), "-I", str(NATIVE / "include"),
                 str(c), str(POLICY), "-ldl", "-o", str(exe)],
                capture_output=True, text=True, timeout=45,
            )
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            run = subprocess.run(
                [str(exe)], capture_output=True, text=True, timeout=25
            )
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_default_compilation_hides_writer_experiment(self):
        src = WITNESS.read_text(encoding="utf-8")
        cmake = (NATIVE / "CMakeLists.txt").read_text(encoding="utf-8")
        self.assertIn("#ifdef KNEEKURA_RESEARCH_VIRGIN_SAVE_TRIAL", src)
        self.assertIn("VIRGIN_TRIAL_ATTESTED", src)
        self.assertIn("AT_SYMLINK_NOFOLLOW", src)
        self.assertIn("O_NOFOLLOW", src)
        self.assertIn("original-native-virgin-save-trial-v1 read-accepted", src)
        self.assertIn("KNEEKURA_RESEARCH_VIRGIN_SAVE_TRIAL", cmake)
        self.assertIn('OFF)', cmake)
        self.assertIn("NOT KNEEKURA_RESEARCH_SCENE_WITNESS", cmake)

if __name__ == "__main__":
    unittest.main()
