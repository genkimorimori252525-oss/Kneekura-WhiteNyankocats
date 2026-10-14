cmake_minimum_required(VERSION 3.22)
project(kneekura_shim C)

add_library(kneekura SHARED
    src/kneekura_shim.c
    src/kneekura_state.c
    src/kneekura_provider.c
    src/kneekura_battle101.c
)

target_include_directories(kneekura
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_compile_features(kneekura PRIVATE c_std_11)
target_compile_options(kneekura PRIVATE
    -Wall
    -Wextra
    -Werror
    -fvisibility=hidden
    -ffunction-sections
    -fdata-sections
)

target_link_options(kneekura PRIVATE
    -Wl,--gc-sections
    -Wl,--no-undefined
    -Wl,-z,relro
    -Wl,-z,now
    -Wl,--build-id=sha1
)

set_target_properties(kneekura PROPERTIES
    OUTPUT_NAME "kneekura"
)

# Isolated original JP15.7.1 native scene observer.
# OFF by default, NEVER silently enabled for a Personal/Practice build.
# The opt-in runtime checks /proc/self/cmdline == jp.kn.local.battlecats,
# original ELF GNU BuildID and pinned ARM64 instructions. OFFICIAL
# libshadowhook.so AND libshadowhook_nothing.so MUST both be staged from the
# SHA-pinned 2.0.1 Maven AAR in the PRIVATE owner research split. Omitting the
# companion can cause ShadowHook linker init failures (upstream Issue #113).
# CMake never fetches/vendors this archive or touches the owner game/SAVE.
option(KNEEKURA_RESEARCH_SCENE_WITNESS
       "Isolated research-only original scene numbers (never shipping)" OFF)
if(KNEEKURA_RESEARCH_SCENE_WITNESS)
    if(NOT ANDROID OR NOT ANDROID_ABI STREQUAL "arm64-v8a")
        message(FATAL_ERROR
            "Original JP15.7.1 scene witness is only for Android arm64-v8a research")
    endif()
    target_sources(kneekura PRIVATE
        src/kneekura_original_scene_witness.c
        src/kneekura_scene_witness_policy.c
        src/kneekura_scene97_resolver_probe.c)
    target_compile_definitions(kneekura PRIVATE
        KNEEKURA_RESEARCH_SCENE_WITNESS=1)
    target_link_libraries(kneekura PRIVATE log dl)
endif()

# PC NativeBridge cannot initialize the full inline-hook backend. A separate
# JNI binding observes only draw-return/scene on the ORIGINAL GL thread.
# Never enable for phone CI, default shipping builds, or the SAVE experiment.
option(KNEEKURA_RESEARCH_PC_JNI_SCENE_OBSERVER
       "PC-only original GL-thread scene observer (never shipping)" OFF)
if(KNEEKURA_RESEARCH_PC_JNI_SCENE_OBSERVER)
    if(NOT KNEEKURA_RESEARCH_SCENE_WITNESS OR KNEEKURA_RESEARCH_VIRGIN_SAVE_TRIAL)
        message(FATAL_ERROR "PC scene observer requires passive original research")
    endif()
    target_compile_definitions(kneekura PRIVATE KNEEKURA_RESEARCH_PC_JNI_SCENE_OBSERVER=1)
endif()

option(KNEEKURA_RESEARCH_PC_BALANCE
       "Exact PC-only approved forms and native castle limit (never phone shipping)" OFF)
if(KNEEKURA_RESEARCH_PC_BALANCE)
    if(NOT KNEEKURA_RESEARCH_PC_JNI_SCENE_OBSERVER)
        message(FATAL_ERROR "PC balance requires the isolated PC JNI research build")
    endif()
    target_sources(kneekura PRIVATE src/kneekura_pc_balance.c)
    set_source_files_properties(src/kneekura_pc_balance.c PROPERTIES
        COMPILE_OPTIONS "-mno-outline-atomics")
    target_compile_definitions(kneekura PRIVATE KNEEKURA_RESEARCH_PC_BALANCE=1)
endif()

# Deliberately separate from the passive scene/LEVEL/SAVE observer.
# ONLY an independently signed original-game local-research package may
# enable this experiment; never a default release or an account-restoration
# product. Research trial calls the original native writer/reader ONCE only.
option(KNEEKURA_RESEARCH_VIRGIN_SAVE_TRIAL
       "DANGEROUS explicit isolated first-run original SAVE experiment (never shipping)" OFF)
if(KNEEKURA_RESEARCH_VIRGIN_SAVE_TRIAL)
    if(KNEEKURA_RESEARCH_PC_JNI_SCENE_OBSERVER)
        message(FATAL_ERROR "PC scene observer cannot enable the original SAVE trial")
    endif()
    if(NOT KNEEKURA_RESEARCH_SCENE_WITNESS)
        message(FATAL_ERROR
            "Original first-SAVE research trial requires the exact original scene witness")
    endif()
    target_compile_definitions(kneekura PRIVATE
        KNEEKURA_RESEARCH_VIRGIN_SAVE_TRIAL=1)
endif()
