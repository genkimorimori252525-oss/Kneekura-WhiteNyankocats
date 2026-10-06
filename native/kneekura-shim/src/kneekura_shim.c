#include "kneekura_shim.h"

#include <stdatomic.h>

static const char kTargetNativeSha256[] =
        "333d2974ab2ff881fd70087fd62dea7d12d82addbc55cab2f2a675ad67e3a7e2";
static const char kTargetNativeBuildId[] =
        "8cb3815648eb9642da10bfb039d71bff7a3519bd";

static _Atomic uint32_t gBootstrapInitialized = 0u;

/*
 * Phase-A preservation rule:
 * loading the shim is allowed; altering Battle Cats behavior is not.
 *
 * The constructor intentionally does not install hooks, replace functions,
 * touch files, access the network, or mutate original game state.
 */
__attribute__((constructor))
static void kneekura_bootstrap_ctor(void) {
    atomic_store_explicit(&gBootstrapInitialized, 1u, memory_order_release);
}

uint32_t kneekura_shim_abi_version(void) {
    return KNEEKURA_SHIM_ABI_VERSION;
}

uint32_t kneekura_target_version_code(void) {
    return KNEEKURA_TARGET_VERSION_CODE;
}

const char *kneekura_target_native_sha256(void) {
    return kTargetNativeSha256;
}

const char *kneekura_target_native_build_id(void) {
    return kTargetNativeBuildId;
}

uint32_t kneekura_bootstrap_initialized(void) {
    return atomic_load_explicit(&gBootstrapInitialized, memory_order_acquire);
}

uint64_t kneekura_feature_mask(void) {
    return KNEEKURA_DEFAULT_FEATURE_MASK;
}

uint32_t kneekura_feature_enabled(uint64_t bit) {
    return (KNEEKURA_DEFAULT_FEATURE_MASK & bit) != 0ull ? 1u : 0u;
}