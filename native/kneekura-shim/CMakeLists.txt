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