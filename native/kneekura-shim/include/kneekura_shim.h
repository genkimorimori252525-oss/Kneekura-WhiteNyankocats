#ifndef KNEEKURA_SHIM_H
#define KNEEKURA_SHIM_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define KNEEKURA_SHIM_ABI_VERSION 1u
#define KNEEKURA_TARGET_VERSION_CODE 1507010u
#define KNEEKURA_DEFAULT_FEATURE_MASK 0ull

#if defined(__GNUC__)
#define KNEEKURA_EXPORT __attribute__((visibility("default")))
#else
#define KNEEKURA_EXPORT
#endif

KNEEKURA_EXPORT uint32_t kneekura_shim_abi_version(void);
KNEEKURA_EXPORT uint32_t kneekura_target_version_code(void);
KNEEKURA_EXPORT const char *kneekura_target_native_sha256(void);
KNEEKURA_EXPORT const char *kneekura_target_native_build_id(void);
KNEEKURA_EXPORT uint32_t kneekura_bootstrap_initialized(void);
KNEEKURA_EXPORT uint64_t kneekura_feature_mask(void);
KNEEKURA_EXPORT uint32_t kneekura_feature_enabled(uint64_t bit);

#ifdef __cplusplus
}
#endif

#endif