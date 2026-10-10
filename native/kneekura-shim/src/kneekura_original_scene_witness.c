/*
 * Original-JP15.7.1-only local research scene witness.
 *
 * Explicit opt-in, OFF in every default CMake build. NEVER for the publisher
 * package, any Personal/Practice flavour or an INTERNET-enabled product.
 *
 * At runtime, ShadowHook (if separately bundled in the isolated APK) makes
 * an IN-MEMORY inline hook of original appUpdateDraw. This necessarily
 * changes process code pages temporarily and is NOT an unmodified gameplay
 * execution. It never writes an APK, SAVE, user credentials or player state.
 *
 * The installed user-owned original ELF build ID AND critical AArch64 words
 * must match EXACTLY. Mismatch, unsupported ABI, missing ShadowHook or wrong
 * process name => no hook, no fallthrough to publisher network/account logic.
 *
 * Dependencies: Android NDK arm64, libdl, liblog. ShadowHook is NOT bundled
 * or fetched here; use only the independently reviewed official distribution.
 * The original native JNI method has DEX proto static ()V in JP15.7.1.
 */
#ifndef KNEEKURA_RESEARCH_SCENE_WITNESS
#error "Never compile the original scene witness without explicit research opt-in"
#endif
#ifndef __ANDROID__
#error "Original native research witness may only be compiled for Android"
#endif
#ifndef __aarch64__
#error "Pinned JP15.7.1 scene witness supports only ARM64"
#endif
#define _GNU_SOURCE
#include <android/log.h>
#include <dlfcn.h>
#include <elf.h>
#include <fcntl.h>
#include <link.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
/* These extra APIs are compiled ONLY for an explicitly enabled, research-only
 * new-player transaction experiment, never in the default/passive observer. */
#ifdef KNEEKURA_RESEARCH_VIRGIN_SAVE_TRIAL
#include <errno.h>
#include <dirent.h>
#include <jni.h>
#include <stdlib.h>
#include <sys/stat.h>
#endif

#include "kneekura_scene_witness_policy.h"

#define WITNESS_TAG "KNEEKURA_STATIC_HTTP"
#define ORIGINAL_LIB "libnative-lib.so"
#define ORIGINAL_DRAW_SYM \
    "Java_jp_co_ponos_battlecats_MyActivity_appUpdateDraw"
#define EXACT_LOCAL_PROCESS "jp.kn.local.battlecats"

/*
 * An opt-in original-scene research shim MUST be identifiable from its
 * compiled ELF even with Clang LTO, string merging and -O2. These
 * exported, used constants let the local build gate distinguish an
 * instrumented research library from the default feature-OFF shim.
 * Neither value contains game/save/account information.
 */
__attribute__((used, visibility("default")))
const char kneekura_scene_research_package_identity[] = EXACT_LOCAL_PROCESS;
__attribute__((used, visibility("default")))
const char kneekura_scene_research_event_format[] =
    "original-native-scene-v1 id=%u";

/* original installed-owner ELF 8cb3815648eb9642da10bfb039d71bff7a3519bd */
static const uint8_t kPinnedNativeBuildId[20] = {
    0x8c, 0xb3, 0x81, 0x56, 0x48, 0xeb, 0x96, 0x42, 0xda, 0x10,
    0xbf, 0xb0, 0x39, 0xd7, 0x1b, 0xff, 0x7a, 0x35, 0x19, 0xbd,
};

/* VMAs from exact original JP15.7.1 ELF, before any repackaging. */
enum {
    ORIGINAL_JNI_DRAW = 0x31755C,
    ORIGINAL_APP_CONTEXT_GETTER = 0x71BF24,
    ORIGINAL_SCENE_DISPATCH = 0x71C408,
    ORIGINAL_SCENE_STORE = 0x71C458,
    ORIGINAL_SCENE_RECORD_OFFSET = 0x3480,
    /* Exact JP15.7.1 original-game functions, NOT local save implementations. */
    ORIGINAL_UNIT_CAP_GETTER = 0x53B2BC,
    ORIGINAL_UPGRADE_GATE = 0x53BE0C,
    ORIGINAL_SAVE_WRAPPER = 0x8B9FC8,
    /* AppLaunchLoad's one source-proven direct SAVE reader site. */
    ORIGINAL_APP_LAUNCH_LOADER = 0x9BB764,
    ORIGINAL_APP_LAUNCH_READ_CALL = 0x492BE8,
    ORIGINAL_NATIVE_TEXT_BEGIN = 0x317370,
    ORIGINAL_NATIVE_TEXT_END_EXCLUSIVE = 0xAD751C,
    MAX_SOURCE_VMA_REBASE = 0x10000,
};
typedef void (*OriginalDrawFn)(void *, void *);
typedef int32_t (*OriginalIndexResultFn)(int32_t);
typedef int32_t (*OriginalSaveWrapperFn)(void *);
typedef int32_t (*OriginalAppLaunchLoaderFn)(void *);
/* Hook the exact already-mapped ELF address, never a basename-driven
 * future/pending symbol match that could attach to another library. */
typedef void *(*ShadowHookSymAddrFn)(void *, void *, void **);
typedef int (*ShadowHookInitFn)(int, _Bool);
typedef int (*ShadowHookUnhookFn)(void *);

static void *gOriginalDraw = NULL;
static void *gOriginalCapGetter = NULL;
static void *gOriginalUpgradeGate = NULL;
static void *gOriginalSaveWrapper = NULL;
static void *gOriginalAppLaunchLoader = NULL;
static uintptr_t gOriginalLoadBias = 0u;
static uintptr_t gOriginalVmaShift = 0u;
static _Atomic uint32_t gLastScene = UINT32_MAX;
static _Atomic uint32_t gSawCapGetter = 0u;
static _Atomic uint32_t gSawUpgradeGate = 0u;
static _Atomic uint32_t gSawSaveReturned = 0u;
static _Atomic uint32_t gSawAppLaunchReadAccepted = 0u;
static _Atomic uint32_t gSawAppLaunchReadFailed = 0u;
static void *gHookStub = NULL;
static void *gCapHookStub = NULL;
static void *gUpgradeHookStub = NULL;
static void *gSaveHookStub = NULL;
static void *gAppLaunchReadHookStub = NULL;
static void *gShadowHookLibrary = NULL;
/* A partially installed/reverted hook chain MUST NEVER activate the writer. */
static _Atomic uint32_t gAllOriginalHooksInstalled = 0u;

/*
 * NEVER a default behavior. The whole experiment requires a special native
 * build, matching Java build flag, owner-private isolated first-run app root,
 * independently reviewed hook dependency and all exact original opcodes.
 */
static int current_process_is_isolated_original_research(void);
#ifdef KNEEKURA_RESEARCH_VIRGIN_SAVE_TRIAL
__attribute__((used, visibility("default")))
const char kneekura_virgin_trial_build_identity[] =
    "kneekura-original-virgin-save-trial-v1";
enum {
    VIRGIN_TRIAL_NOT_ATTESTED = 0,
    VIRGIN_TRIAL_ATTESTED = 1,
    VIRGIN_TRIAL_ATTEMPTED = 2,
    VIRGIN_TRIAL_COMPLETED = 3,
    VIRGIN_TRIAL_BLOCKED = 4,
};
static _Atomic uint32_t gVirginTrialState = VIRGIN_TRIAL_NOT_ATTESTED;
static int gVirginRootFd = -1;

/* Do not build absolute app-private paths from tainted logcat/native input. */
static int exact_private_original_root_path(const char *path) {
    if (path == NULL) return 0;
    size_t len = strlen(path);
    const char suffix[] = "/jp.kn.local.battlecats/files";
    const size_t suffix_len = sizeof(suffix) - 1u;
    if (len < suffix_len + 1u || len > 512u
        || strcmp(path + len - suffix_len, suffix) != 0) return 0;
    const size_t prefix_len = len - suffix_len;
    if (prefix_len == strlen("/data/data")
        && memcmp(path, "/data/data", prefix_len) == 0) return 1;
    const char prefix[] = "/data/user/";
    if (prefix_len <= sizeof(prefix) - 1u
        || memcmp(path, prefix, sizeof(prefix) - 1u) != 0) return 0;
    for (size_t i = sizeof(prefix) - 1u; i < prefix_len; ++i) {
        if (path[i] < '0' || path[i] > '9') return 0;
    }
    return 1;
}

static int virgin_save_files_all_absent(int root_fd) {
    if (root_fd < 0) return 0;
    const char *const names[] = {
        "SAVE_DATA", "SAVE_DATA4", "SAVE_DATA8"
    };
    for (size_t i = 0; i < sizeof(names)/sizeof(names[0]); ++i) {
        struct stat item = {0};
        errno = 0;
        if (fstatat(root_fd, names[i], &item, AT_SYMLINK_NOFOLLOW) == 0
            || errno != ENOENT) return 0;
    }
    /* Also refuse file variants such as SAVE_DATA.tmp or .bak, to avoid
     * overwriting any pre-existing state in a previous research experiment. */
    /* dup() shares the ORIGINAL directory stream offset. A second safety
     * check after a new SAVE_DATA.* file appears could silently see EOF!
     * Re-open "." relative to the verified root FD for a fresh offset. */
    int cloned = openat(root_fd, ".", O_RDONLY | O_DIRECTORY |
                                      O_CLOEXEC | O_NOFOLLOW);
    if (cloned < 0) return 0;
    DIR *directory = fdopendir(cloned);
    if (directory == NULL) {
        close(cloned);
        return 0;
    }
    int safe = 1;
    struct dirent *member;
    errno = 0;
    while ((member = readdir(directory)) != NULL) {
        if (strncmp(member->d_name, "SAVE_DATA", 9u) == 0) {
            safe = 0;
            break;
        }
        errno = 0;
    }
    if (errno != 0) safe = 0;
    closedir(directory);
    return safe;
}

static int virgin_source_root_remains_trusted(void) {
    if (gVirginRootFd < 0) return 0;
    struct stat root = {0}, marker = {0};
    if (fstat(gVirginRootFd, &root) != 0
        || !S_ISDIR(root.st_mode) || root.st_uid != geteuid()
        || fstatat(gVirginRootFd, ".kneekura-virgin-local-jp15-7-1",
                   &marker, AT_SYMLINK_NOFOLLOW) != 0
        || !S_ISREG(marker.st_mode) || marker.st_size != 0
        || marker.st_uid != geteuid()) return 0;
    return virgin_save_files_all_absent(gVirginRootFd);
}

/* JNI handshake MUST originate from MyActivity immediately after a NEW
 * marker was created and exactly three source SAVE filenames were absent.
 * A pre-existing marker on a later boot MUST NEVER call this handshake. */
__attribute__((visibility("default")))
JNIEXPORT jboolean JNICALL
Java_jp_kn_local_battlecats_MyActivity_kneekuraAttestVirginRoot(
        JNIEnv *env, jclass owner_class, jstring java_canonical_root) {
    (void)owner_class;
    if (env == NULL || java_canonical_root == NULL
        || !current_process_is_isolated_original_research()
        || atomic_load_explicit(
               &gAllOriginalHooksInstalled, memory_order_acquire) != 1u
        || gShadowHookLibrary == NULL || gAppLaunchReadHookStub == NULL
        || gOriginalAppLaunchLoader == NULL || gOriginalSaveWrapper == NULL
        || atomic_load_explicit(&gVirginTrialState, memory_order_acquire)
            != VIRGIN_TRIAL_NOT_ATTESTED) return JNI_FALSE;
    const char *root_path = (*env)->GetStringUTFChars(
        env, java_canonical_root, NULL);
    if (root_path == NULL) return JNI_FALSE;
    int fd = -1;
    if (exact_private_original_root_path(root_path)) {
        fd = open(root_path, O_RDONLY | O_CLOEXEC | O_DIRECTORY | O_NOFOLLOW);
    }
    (*env)->ReleaseStringUTFChars(env, java_canonical_root, root_path);
    if (fd < 0) return JNI_FALSE;
    gVirginRootFd = fd;
    if (!virgin_source_root_remains_trusted()) {
        gVirginRootFd = -1;
        close(fd);
        return JNI_FALSE;
    }
    atomic_store_explicit(
        &gVirginTrialState, VIRGIN_TRIAL_ATTESTED, memory_order_release);
    __android_log_write(
        ANDROID_LOG_INFO, WITNESS_TAG,
        "original-native-virgin-save-trial-v1 root-attested");
    return JNI_TRUE;
}
#endif

/* Forward reference for optional JNI root attestation. */
static int current_process_is_isolated_original_research(void) {
    char process_name[96] = {0};
    int fd = open("/proc/self/cmdline", O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        return 0;
    }
    ssize_t count = read(fd, process_name, sizeof(process_name) - 1u);
    close(fd);
    if (count <= 0 || (size_t)count >= sizeof(process_name)) {
        return 0;
    }
    /* The first NUL-terminated argv[0] MUST be the exact dedicated package.
       This also prevents accidentally activating in the actual PONOS app. */
    return strcmp(process_name, kneekura_scene_research_package_identity) == 0;
}

static size_t align_note_size(size_t size) {
    return (size + 3u) & ~(size_t)3u;
}

static int note_has_exact_build_id(const uint8_t *data, size_t len) {
    size_t offset = 0u;
    while (offset + sizeof(Elf64_Nhdr) <= len) {
        Elf64_Nhdr note;
        memcpy(&note, data + offset, sizeof(note));
        offset += sizeof(note);
        if (note.n_namesz > len || note.n_descsz > len) {
            return 0;
        }
        size_t name_size = align_note_size(note.n_namesz);
        size_t description_size = align_note_size(note.n_descsz);
        if (name_size > len - offset || description_size > len - offset - name_size) {
            return 0;
        }
        const uint8_t *name = data + offset;
        const uint8_t *description = name + name_size;
        if (note.n_type == NT_GNU_BUILD_ID
            && note.n_namesz == 4u && note.n_descsz == sizeof(kPinnedNativeBuildId)
            && memcmp(name, "GNU", 4u) == 0
            && memcmp(description, kPinnedNativeBuildId,
                      sizeof(kPinnedNativeBuildId)) == 0) {
            return 1;
        }
        offset += name_size + description_size;
    }
    return 0;
}

struct NativeElfWitness {
    uintptr_t base;
    uintptr_t executable_begin;
    uintptr_t executable_end;
    unsigned exact_build_id_count;
    unsigned original_library_count;
    unsigned executable_load_count;
};

static int inspect_original_library(struct dl_phdr_info *info,
                                    size_t size, void *private_value) {
    (void)size;
    struct NativeElfWitness *witness = (struct NativeElfWitness *)private_value;
    const char *name = info->dlpi_name;
    if (name == NULL) {
        return 0;
    }
    const char *basename = strrchr(name, '/');
    basename = basename == NULL ? name : basename + 1;
    if (strcmp(basename, ORIGINAL_LIB) != 0) {
        return 0;
    }
    witness->original_library_count++;
    if (witness->original_library_count != 1u || info->dlpi_addr == 0u) {
        // Keep enumerating: returning nonzero from dl_iterate_phdr STOPs
        // its scan and would silently miss a duplicate libnative-lib.so.
        // The caller must require EXACTLY one matching library and Build ID.
        return 0;
    }
    for (ElfW(Half) index = 0; index < info->dlpi_phnum; ++index) {
        const ElfW(Phdr) *phdr = &info->dlpi_phdr[index];
        if (phdr->p_type == PT_LOAD && (phdr->p_flags & PF_X)) {
            witness->executable_load_count++;
            if (witness->executable_load_count == 1u
                && phdr->p_memsz >= 4u
                && phdr->p_vaddr <= UINTPTR_MAX - (uintptr_t)info->dlpi_addr
                && phdr->p_memsz <= UINTPTR_MAX -
                    ((uintptr_t)info->dlpi_addr + (uintptr_t)phdr->p_vaddr)) {
                witness->executable_begin =
                    (uintptr_t)info->dlpi_addr + (uintptr_t)phdr->p_vaddr;
                witness->executable_end =
                    witness->executable_begin + (uintptr_t)phdr->p_memsz;
            }
        }
        if (phdr->p_type == PT_NOTE && phdr->p_memsz > 0u
            && phdr->p_memsz <= 65536u) {
            const uint8_t *notes =
                (const uint8_t *)(uintptr_t)(info->dlpi_addr + phdr->p_vaddr);
            if (note_has_exact_build_id(notes, (size_t)phdr->p_memsz)) {
                witness->exact_build_id_count++;
            }
        }
    }
    witness->base = (uintptr_t)info->dlpi_addr;
    // 0 = continue enumeration; source uniqueness is checked afterwards.
    return 0;
}

struct OriginalCodeWordAnchor {
    uintptr_t vma;
    uint32_t instruction;
};

static const struct OriginalCodeWordAnchor kSourceWordAnchors[] = {
    {ORIGINAL_JNI_DRAW, 0xD10143FFu},
    {ORIGINAL_APP_CONTEXT_GETTER, 0xB0002040u},
    {ORIGINAL_APP_CONTEXT_GETTER + 4u, 0x911CC000u},
    {ORIGINAL_APP_CONTEXT_GETTER + 8u, 0xD65F03C0u},
    {ORIGINAL_SCENE_DISPATCH, 0xA9BB7BFDu},
    {ORIGINAL_SCENE_STORE, 0xB9348001u},
    {ORIGINAL_UNIT_CAP_GETTER, 0xA9BB7BFDu},
    {ORIGINAL_UPGRADE_GATE, 0xA9BA7BFDu},
    {ORIGINAL_SAVE_WRAPPER, 0xD10103FFu},
    {ORIGINAL_APP_LAUNCH_LOADER, 0xD102C3FFu},
    {ORIGINAL_APP_LAUNCH_READ_CALL, 0x9414A2DFu},
    /* Original direct-call graph; cap getter is NOT a proven purchase
     * call. 0x8581fc is the original actual upgrade predicate call. */
    {0x821904u, 0x97F4666Eu},
    {0x8581FCu, 0x97F38F04u},
    {0x85C734u, 0x97F37DB6u},
    {0x860224u, 0x97F36EFAu},
    {0x88CB00u, 0x97F2BCC3u},
    {0x88E884u, 0x97F2B562u},
    /* Main purchase path: native XP debit and CURRENT base level +1. */
    {0x858390u, 0x940600D5u},
    {0x8583B8u, 0x9405CF25u},
};

static int source_words_match_exact_original(
    uintptr_t base, uintptr_t shift,
    uintptr_t executable_begin, uintptr_t executable_end
) {
    if (executable_end <= executable_begin
        || base > UINTPTR_MAX - ORIGINAL_NATIVE_TEXT_END_EXCLUSIVE - shift
        || base + ORIGINAL_NATIVE_TEXT_BEGIN + shift < executable_begin
        || base + ORIGINAL_NATIVE_TEXT_END_EXCLUSIVE + shift > executable_end) {
        return 0;
    }
    for (size_t i = 0;
         i < sizeof(kSourceWordAnchors) / sizeof(kSourceWordAnchors[0]);
         ++i) {
        const uintptr_t at = base + kSourceWordAnchors[i].vma + shift;
        if (at < executable_begin || at > executable_end - 4u) {
            return 0;
        }
        uint32_t actual = 0u;
        memcpy(&actual, (const void *)at, sizeof(actual));
        if (actual != kSourceWordAnchors[i].instruction) {
            return 0;
        }
    }
    return 1;
}

/*
 * A normal LIEF DT_NEEDED rebuild can rebase ALL original program sections
 * by one aligned page while leaving original instructions intact. We allow
 * only 0..64KiB page-aligned offsets and require ALL 17 original words,
 * the exact BuildID, one executable LOAD, and one UNIQUE matching rebase.
 * Exact original mapped .text/rodata/eh hashes must also pass pre-sign gate.
 * No hook is installed if any part of this runtime proof is uncertain.
 */
static int select_unique_original_source_vma_shift(
    const struct NativeElfWitness *native, uintptr_t *out_shift
) {
    if (native == NULL || out_shift == NULL
        || native->base == 0u || native->executable_load_count != 1u
        || native->executable_end <= native->executable_begin) {
        return 0;
    }
    unsigned matches = 0u;
    uintptr_t selected = 0u;
    for (uintptr_t delta = 0u; delta <= MAX_SOURCE_VMA_REBASE;
         delta += 0x1000u) {
        if (source_words_match_exact_original(
                native->base, delta,
                native->executable_begin, native->executable_end)) {
            selected = delta;
            matches++;
        }
    }
    if (matches != 1u) {
        return 0;
    }
    *out_shift = selected;
    return 1;
}

static void research_draw_proxy(void *jni_env, void *jni_class) {
    /* ALWAYS forward the exact original JNI invocation before observing.
       The function has original DEX prototype static ()V (two JNI args).
       The hook may be called on the original GL render/update thread. */
    OriginalDrawFn original_draw = NULL;
    memcpy(&original_draw, &gOriginalDraw, sizeof(original_draw));
    if (original_draw == NULL) {
        return;
    }
    original_draw(jni_env, jni_class);

    uintptr_t base = gOriginalLoadBias;
    if (base == 0u) {
        return;
    }
    typedef void *(*OriginalContextFn)(void);
    OriginalContextFn get_game_context = NULL;
    uintptr_t context_getter = base + ORIGINAL_APP_CONTEXT_GETTER
                               + gOriginalVmaShift;
    memcpy(&get_game_context, &context_getter, sizeof(get_game_context));
    if (get_game_context == NULL) {
        return;
    }
    const uint8_t *context = (const uint8_t *)get_game_context();
    if (context == NULL) {
        return;
    }
    uint32_t scene = 0u;
    memcpy(&scene, context + ORIGINAL_SCENE_RECORD_OFFSET, sizeof(scene));

    uint32_t previous = atomic_exchange_explicit(
        &gLastScene, scene, memory_order_relaxed);
    if (!kneekura_scene_witness_should_emit(previous, scene)) {
        return;
    }
    /* Only five numeric original scene IDs. No scene title, text, save,
       account, URL, player identifier, gameplay values or stack traces. */
    char message[64];
    int size = snprintf(message, sizeof(message),
                        kneekura_scene_research_event_format, (unsigned)scene);
    if (size > 0 && (size_t)size < sizeof(message)) {
        __android_log_write(ANDROID_LOG_INFO, WITNESS_TAG, message);
    }
}

/*
 * Four extra EXACT-VMA research witnesses for original LEVEL #12.
 * Do not log unit IDs, levels, cap numbers, XP, SAVE names, or paths.
 * Calls always forward FIRST and preserve the original return register.
 * This is neither a purchase implementation nor a first-SAVE generator.
 */
static void record_native_event_once(_Atomic uint32_t *seen, const char *tag) {
    if (atomic_exchange_explicit(seen, 1u, memory_order_relaxed) == 0u) {
        __android_log_write(ANDROID_LOG_INFO, WITNESS_TAG, tag);
    }
}

static int32_t research_original_cap_getter_proxy(int32_t asset_index) {
    OriginalIndexResultFn original = NULL;
    memcpy(&original, &gOriginalCapGetter, sizeof(original));
    if (original == NULL) {
        return 0; /* Cannot act as an implementation without the trampoline. */
    }
    int32_t result = original(asset_index);
    record_native_event_once(&gSawCapGetter,
                             "original-native-level-cap-getter-v1 original-returned");
    return result;
}

static int32_t research_original_upgrade_gate_proxy(int32_t asset_index) {
    OriginalIndexResultFn original = NULL;
    memcpy(&original, &gOriginalUpgradeGate, sizeof(original));
    if (original == NULL) {
        return 0;
    }
    int32_t result = original(asset_index);
    record_native_event_once(&gSawUpgradeGate,
                             "original-native-upgrade-gate-v1 original-returned");
    return result;
}

static int32_t research_original_save_wrapper_proxy(void *context) {
    OriginalSaveWrapperFn original = NULL;
    memcpy(&original, &gOriginalSaveWrapper, sizeof(original));
    if (original == NULL) {
        return 0;
    }
    int32_t result = original(context);
    /* Source wrapper 0x8ba030 returns bit0 of internal serializer result.
     * This indicates only that the wrapper returned; no fsync, file
     * persistence, fresh player or restart acceptance is thereby proven. */
    record_native_event_once(&gSawSaveReturned,
                             "original-native-save-wrapper-v1 original-returned");
    return result;
}

/*
 * Source exact call: AppLaunchLoad 0x492be8 BL -> 0x9bb764.
 * The caller checks bit0 of W0 at 0x492bec. A returned bit0 is NOT
 * proof of a new account-free SAVE, disk persistence, or a successful reboot.
 * Default research build is an OBSERVER ONLY and never touches a SAVE.
 * Separate KNEEKURA_RESEARCH_VIRGIN_SAVE_TRIAL build can issue a one-time
 * original-native write in its newly attested isolated package root only.
 */
static int32_t research_original_app_launch_read_proxy(void *game_context) {
    OriginalAppLaunchLoaderFn original = NULL;
    memcpy(&original, &gOriginalAppLaunchLoader, sizeof(original));
    if (original == NULL) {
        return 0;
    }
    int32_t result = original(game_context);
#ifdef KNEEKURA_RESEARCH_VIRGIN_SAVE_TRIAL
    /*
     * User explicitly selected virgin-save trial AND Java attested a newly
     * created private root. Only original AppLaunchLoad callsite may try it:
     * source 0x492be8 BL -> reader; LR is 0x492bec, before worker TBZ W0,#0.
     * On ANY failure preserve the original reader failure (never forge W0).
     */
    const uintptr_t caller = (uintptr_t)__builtin_return_address(0);
    const uintptr_t expected_caller = (
        gOriginalLoadBias + ORIGINAL_APP_LAUNCH_READ_CALL + 4u
        + gOriginalVmaShift
    );
    if ((result & 1) == 0
        && game_context != NULL
        && caller == expected_caller
        && gShadowHookLibrary != NULL
        && atomic_load_explicit(
               &gAllOriginalHooksInstalled, memory_order_acquire) == 1u
        && virgin_source_root_remains_trusted()) {
        uint32_t expected = VIRGIN_TRIAL_ATTESTED;
        if (atomic_compare_exchange_strong_explicit(
                &gVirginTrialState, &expected, VIRGIN_TRIAL_ATTEMPTED,
                memory_order_acq_rel, memory_order_acquire)) {
            /* The native original wrapper is the owner of the actual SAVE
             * format. One original write, at most one original read retry.
             * No account ID or pseudo save container is synthesized here. */
            OriginalSaveWrapperFn native_writer = NULL;
            memcpy(&native_writer, &gOriginalSaveWrapper, sizeof(native_writer));
            int32_t wrote = native_writer == NULL ? 0 : native_writer(game_context);
            struct stat saved = {0};
            if ((wrote & 1) != 0 && gVirginRootFd >= 0
                && fstatat(gVirginRootFd, "SAVE_DATA", &saved,
                           AT_SYMLINK_NOFOLLOW) == 0
                && S_ISREG(saved.st_mode) && saved.st_uid == geteuid()
                && saved.st_size > 0) {
                int32_t retried = original(game_context);
                if ((retried & 1) != 0) {
                    result = retried;
                    atomic_store_explicit(
                        &gVirginTrialState, VIRGIN_TRIAL_COMPLETED,
                        memory_order_release);
                    __android_log_write(
                        ANDROID_LOG_INFO, WITNESS_TAG,
                        "original-native-virgin-save-trial-v1 read-accepted");
                } else {
                    atomic_store_explicit(
                        &gVirginTrialState, VIRGIN_TRIAL_BLOCKED,
                        memory_order_release);
                    __android_log_write(
                        ANDROID_LOG_INFO, WITNESS_TAG,
                        "original-native-virgin-save-trial-v1 read-rejected");
                }
            } else {
                atomic_store_explicit(
                    &gVirginTrialState, VIRGIN_TRIAL_BLOCKED,
                    memory_order_release);
                __android_log_write(
                    ANDROID_LOG_INFO, WITNESS_TAG,
                    "original-native-virgin-save-trial-v1 writer-rejected");
            }
        }
    }
#endif
    if ((result & 1) != 0) {
        record_native_event_once(
            &gSawAppLaunchReadAccepted,
            "original-native-app-launch-save-read-v1 accepted");
    } else {
        record_native_event_once(
            &gSawAppLaunchReadFailed,
            "original-native-app-launch-save-read-v1 failed");
    }
    return result;
}

__attribute__((constructor))
static void kneekura_init_scene_witness_research_only(void) {
    if (!current_process_is_isolated_original_research()) {
        return;
    }
    /* libnative-lib.so is the owner of this DT_NEEDED research dependency.
       LIEF may uniformly rebase its source VMAs. Never assume raw hardcoded
       absolute addresses, even when original instruction bytes match. */
    struct NativeElfWitness witness = {0};
    dl_iterate_phdr(inspect_original_library, &witness);
    uintptr_t validated_shift = 0u;
    if (witness.original_library_count != 1u
        || witness.exact_build_id_count != 1u
        || !select_unique_original_source_vma_shift(
            &witness, &validated_shift)) {
        __android_log_write(
            ANDROID_LOG_INFO, WITNESS_TAG,
            "original-native-scene-hook-v1 original-source-unavailable");
        return;
    }
    /* Optional, independent third-party hooking dependency. We do NOT
       fetch, vendor, or silently load arbitrary files outside our APK. */
    void *library = dlopen("libshadowhook.so", RTLD_NOW | RTLD_LOCAL);
    if (library == NULL) {
        __android_log_write(
            ANDROID_LOG_INFO, WITNESS_TAG,
            "original-native-scene-hook-v1 library-unavailable");
        return;
    }
    ShadowHookInitFn init_fn =
        (ShadowHookInitFn)dlsym(library, "shadowhook_init");
    ShadowHookSymAddrFn hook_fn =
        (ShadowHookSymAddrFn)dlsym(library, "shadowhook_hook_sym_addr");
    ShadowHookUnhookFn unhook_fn =
        (ShadowHookUnhookFn)dlsym(library, "shadowhook_unhook");
    if (init_fn == NULL || hook_fn == NULL || unhook_fn == NULL
        || init_fn(1, 0) != 0) {
        __android_log_write(
            ANDROID_LOG_INFO, WITNESS_TAG,
            "original-native-scene-hook-v1 hook-initialization-failed");
        dlclose(library);
        return;
    }
    gOriginalLoadBias = witness.base;
    gOriginalVmaShift = validated_shift;
    /* Hook only the loaded library with verified BuildID/opcodes. All
     * observers are REQUIRED together so a partial research report is
     * never misread as one coherent upgrade/save lifecycle. */
    gHookStub = hook_fn(
        (void *)(witness.base + ORIGINAL_JNI_DRAW + validated_shift),
        (void *)&research_draw_proxy, &gOriginalDraw
    );
    if (gHookStub != NULL && gOriginalDraw != NULL) {
        gCapHookStub = hook_fn(
            (void *)(witness.base + ORIGINAL_UNIT_CAP_GETTER + validated_shift),
            (void *)&research_original_cap_getter_proxy, &gOriginalCapGetter
        );
    }
    if (gCapHookStub != NULL && gOriginalCapGetter != NULL) {
        gUpgradeHookStub = hook_fn(
            (void *)(witness.base + ORIGINAL_UPGRADE_GATE + validated_shift),
            (void *)&research_original_upgrade_gate_proxy, &gOriginalUpgradeGate
        );
    }
    if (gUpgradeHookStub != NULL && gOriginalUpgradeGate != NULL) {
        gSaveHookStub = hook_fn(
            (void *)(witness.base + ORIGINAL_SAVE_WRAPPER + validated_shift),
            (void *)&research_original_save_wrapper_proxy, &gOriginalSaveWrapper
        );
    }
    if (gSaveHookStub != NULL && gOriginalSaveWrapper != NULL) {
        gAppLaunchReadHookStub = hook_fn(
            (void *)(witness.base + ORIGINAL_APP_LAUNCH_LOADER + validated_shift),
            (void *)&research_original_app_launch_read_proxy,
            &gOriginalAppLaunchLoader
        );
    }
    if (gHookStub == NULL || gOriginalDraw == NULL
        || gCapHookStub == NULL || gOriginalCapGetter == NULL
        || gUpgradeHookStub == NULL || gOriginalUpgradeGate == NULL
        || gSaveHookStub == NULL || gOriginalSaveWrapper == NULL
        || gAppLaunchReadHookStub == NULL || gOriginalAppLaunchLoader == NULL) {
        atomic_store_explicit(
            &gAllOriginalHooksInstalled, 0u, memory_order_release);
        /* A partially patched JNI/level/save path can corrupt execution
         * if left behind. Undo in reverse order. Any failed unhook keeps
         * ShadowHook mapped; logging must not claim coherent attachment. */
        void *installed[] = {
            gAppLaunchReadHookStub, gSaveHookStub, gUpgradeHookStub,
            gCapHookStub, gHookStub
        };
        int rollback_failed = 0;
        for (size_t i = 0; i < sizeof(installed) / sizeof(installed[0]); ++i) {
            if (installed[i] != NULL && unhook_fn(installed[i]) != 0) {
                rollback_failed = 1;
            }
        }
        gOriginalLoadBias = 0u;
        if (rollback_failed) {
            gShadowHookLibrary = library;
            __android_log_write(
                ANDROID_LOG_INFO, WITNESS_TAG,
                "original-native-scene-hook-v1 partial-unhook-failed");
            return;
        }
        gHookStub = NULL;
        gCapHookStub = NULL;
        gUpgradeHookStub = NULL;
        gSaveHookStub = NULL;
        gAppLaunchReadHookStub = NULL;
        __android_log_write(
            ANDROID_LOG_INFO, WITNESS_TAG,
            "original-native-scene-hook-v1 hook-unavailable");
        dlclose(library);
        return;
    }
    /* Keep the trampoline library alive. Never log 'installed' until
     * ALL source-exact scene, LEVEL, SAVE-WRITER and app-launch READ
     * observers are usable. The read hook never writes player state. */
    gShadowHookLibrary = library;
    atomic_store_explicit(
        &gAllOriginalHooksInstalled, 1u, memory_order_release);
    __android_log_write(
        ANDROID_LOG_INFO, WITNESS_TAG,
        "original-native-scene-hook-v1 installed");
}
