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
};
typedef void (*OriginalDrawFn)(void *, void *);
typedef int32_t (*OriginalIndexResultFn)(int32_t);
typedef int32_t (*OriginalSaveWrapperFn)(void *);
/* Hook the exact already-mapped ELF address, never a basename-driven
 * future/pending symbol match that could attach to another library. */
typedef void *(*ShadowHookSymAddrFn)(void *, void *, void **);
typedef int (*ShadowHookInitFn)(int, _Bool);
typedef int (*ShadowHookUnhookFn)(void *);

static void *gOriginalDraw = NULL;
static void *gOriginalCapGetter = NULL;
static void *gOriginalUpgradeGate = NULL;
static void *gOriginalSaveWrapper = NULL;
static uintptr_t gOriginalLoadBias = 0u;
static _Atomic uint32_t gLastScene = UINT32_MAX;
static _Atomic uint32_t gSawCapGetter = 0u;
static _Atomic uint32_t gSawUpgradeGate = 0u;
static _Atomic uint32_t gSawSaveReturned = 0u;
static void *gHookStub = NULL;
static void *gCapHookStub = NULL;
static void *gUpgradeHookStub = NULL;
static void *gSaveHookStub = NULL;
static void *gShadowHookLibrary = NULL;

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
    unsigned exact_build_id_count;
    unsigned original_library_count;
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
        if (phdr->p_type != PT_NOTE || phdr->p_memsz == 0u
            || phdr->p_memsz > 65536u) {
            continue;
        }
        const uint8_t *notes =
            (const uint8_t *)(uintptr_t)(info->dlpi_addr + phdr->p_vaddr);
        if (note_has_exact_build_id(notes, (size_t)phdr->p_memsz)) {
            witness->exact_build_id_count++;
        }
    }
    witness->base = (uintptr_t)info->dlpi_addr;
    // 0 = continue enumeration; source uniqueness is checked afterwards.
    return 0;
}

static int source_words_match_exact_original(uintptr_t base) {
    struct Anchor {uintptr_t vma; uint32_t instruction;};
    static const struct Anchor anchors[] = {
        {ORIGINAL_JNI_DRAW, 0xD10143FFu},
        {ORIGINAL_APP_CONTEXT_GETTER, 0xB0002040u},
        {ORIGINAL_APP_CONTEXT_GETTER + 4u, 0x911CC000u},
        {ORIGINAL_APP_CONTEXT_GETTER + 8u, 0xD65F03C0u},
        {ORIGINAL_SCENE_DISPATCH, 0xA9BB7BFDu},
        {ORIGINAL_SCENE_STORE, 0xB9348001u},
        {ORIGINAL_UNIT_CAP_GETTER, 0xA9BB7BFDu},
        {ORIGINAL_UPGRADE_GATE, 0xA9BA7BFDu},
        {ORIGINAL_SAVE_WRAPPER, 0xD10103FFu},
    };
    for (size_t i = 0; i < sizeof(anchors) / sizeof(anchors[0]); ++i) {
        uint32_t actual = 0u;
        memcpy(&actual, (const void *)(base + anchors[i].vma), sizeof(actual));
        if (actual != anchors[i].instruction) {
            return 0;
        }
    }
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
    uintptr_t context_getter = base + ORIGINAL_APP_CONTEXT_GETTER;
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
 * Three extra EXACT-VMA research witnesses for original LEVEL #12.
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

__attribute__((constructor))
static void kneekura_init_scene_witness_research_only(void) {
    if (!current_process_is_isolated_original_research()) {
        return;
    }
    /* libnative-lib.so is the parent DT_NEEDED dependency owner. The
       mapped original's function offsets and build ID must remain exact
       after owner-private LIEF DT_NEEDED packaging. Otherwise bail out. */
    struct NativeElfWitness witness = {0u, 0u, 0u};
    dl_iterate_phdr(inspect_original_library, &witness);
    if (witness.original_library_count != 1u
        || witness.exact_build_id_count != 1u
        || !source_words_match_exact_original(witness.base)) {
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
    /* Hook only the loaded library with verified BuildID/opcodes. All
     * observers are REQUIRED together so a partial research report is
     * never misread as one coherent upgrade/save lifecycle. */
    gHookStub = hook_fn(
        (void *)(witness.base + ORIGINAL_JNI_DRAW),
        (void *)&research_draw_proxy, &gOriginalDraw
    );
    if (gHookStub != NULL && gOriginalDraw != NULL) {
        gCapHookStub = hook_fn(
            (void *)(witness.base + ORIGINAL_UNIT_CAP_GETTER),
            (void *)&research_original_cap_getter_proxy, &gOriginalCapGetter
        );
    }
    if (gCapHookStub != NULL && gOriginalCapGetter != NULL) {
        gUpgradeHookStub = hook_fn(
            (void *)(witness.base + ORIGINAL_UPGRADE_GATE),
            (void *)&research_original_upgrade_gate_proxy, &gOriginalUpgradeGate
        );
    }
    if (gUpgradeHookStub != NULL && gOriginalUpgradeGate != NULL) {
        gSaveHookStub = hook_fn(
            (void *)(witness.base + ORIGINAL_SAVE_WRAPPER),
            (void *)&research_original_save_wrapper_proxy, &gOriginalSaveWrapper
        );
    }
    if (gHookStub == NULL || gOriginalDraw == NULL
        || gCapHookStub == NULL || gOriginalCapGetter == NULL
        || gUpgradeHookStub == NULL || gOriginalUpgradeGate == NULL
        || gSaveHookStub == NULL || gOriginalSaveWrapper == NULL) {
        /* A partially patched JNI/level/save path can corrupt execution
         * if left behind. Undo in reverse order. Any failed unhook keeps
         * ShadowHook mapped; logging must not claim coherent attachment. */
        void *installed[] = {
            gSaveHookStub, gUpgradeHookStub, gCapHookStub, gHookStub
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
        __android_log_write(
            ANDROID_LOG_INFO, WITNESS_TAG,
            "original-native-scene-hook-v1 hook-unavailable");
        dlclose(library);
        return;
    }
    /* Keep the trampoline library alive. Never log 'installed' until
     * ALL exact original-level and original-SAVE observers are usable. */
    gShadowHookLibrary = library;
    __android_log_write(
        ANDROID_LOG_INFO, WITNESS_TAG,
        "original-native-scene-hook-v1 installed");
}
