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
# original ELF GNU BuildID and pinned ARM64 instructions. libshadowhook.so
# must be reviewed and bundled separately, from its official distribution;
# it is NOT fetched/vendored by CMake or by this project.
option(KNEEKURA_RESEARCH_SCENE_WITNESS
       "Isolated research-only original scene numbers (never shipping)" OFF)
if(KNEEKURA_RESEARCH_SCENE_WITNESS)
    if(NOT ANDROID OR NOT ANDROID_ABI STREQUAL "arm64-v8a")
        message(FATAL_ERROR
            "Original JP15.7.1 scene witness is only for Android arm64-v8a research")
    endif()
    target_sources(kneekura PRIVATE
        src/kneekura_original_scene_witness.c
        src/kneekura_scene_witness_policy.c)
    target_compile_definitions(kneekura PRIVATE
        KNEEKURA_RESEARCH_SCENE_WITNESS=1)
    target_link_libraries(kneekura PRIVATE log dl)
endif()
