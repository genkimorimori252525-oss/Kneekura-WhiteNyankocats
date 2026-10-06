#ifndef KNEEKURA_SHIM_H
#define KNEEKURA_SHIM_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define KNEEKURA_SHIM_ABI_VERSION 2u
#define KNEEKURA_TARGET_VERSION_CODE 1507010u

#define KNEEKURA_FEATURE_LOCAL_STATE (1ull << 0)
#define KNEEKURA_FEATURE_LOCAL_CLOCK (1ull << 1)
#define KNEEKURA_FEATURE_PROVIDER_API (1ull << 2)
#define KNEEKURA_FEATURE_LOCAL_EVENTS (1ull << 3)
#define KNEEKURA_FEATURE_SUPER_GACHA (1ull << 4)
#define KNEEKURA_FEATURE_LOGIN_BONUS (1ull << 5)
#define KNEEKURA_FEATURE_STAGE_CATFOOD (1ull << 6)

#define KNEEKURA_PROVIDER_ABI_VERSION 1u
#define KNEEKURA_GACHA_KIND_SUPER 1u

#ifndef KNEEKURA_DEFAULT_FEATURE_MASK
#define KNEEKURA_DEFAULT_FEATURE_MASK 0ull
#endif

#define KNEEKURA_SIDECAR_SCHEMA_VERSION 1u
#define KNEEKURA_LOGIN_DAY_UNSET INT64_MIN

typedef enum KneekuraProfileMode {
    KNEEKURA_PROFILE_UNSET = 0,
    KNEEKURA_PROFILE_PERSONAL_MAX = 1,
    KNEEKURA_PROFILE_PRACTICE_CLEAN = 2
} KneekuraProfileMode;

typedef enum KneekuraStatus {
    KNEEKURA_STATUS_OK = 0,
    KNEEKURA_STATUS_DISABLED = 1,
    KNEEKURA_STATUS_NOT_FOUND = 2,
    KNEEKURA_STATUS_INVALID_ARGUMENT = 3,
    KNEEKURA_STATUS_IO_ERROR = 4,
    KNEEKURA_STATUS_BAD_MAGIC = 5,
    KNEEKURA_STATUS_UNSUPPORTED_SCHEMA = 6,
    KNEEKURA_STATUS_CHECKSUM_MISMATCH = 7
} KneekuraStatus;

typedef struct KneekuraSidecarState {
    uint32_t schema_version;
    uint32_t profile_mode;
    int64_t last_seen_epoch_day;
    int64_t last_claim_epoch_day;
    uint32_t login_cycle_index;
    uint32_t event_snapshot_version;
    uint32_t gacha_config_version;
    uint64_t extension_flags;
} KneekuraSidecarState;

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

KNEEKURA_EXPORT uint32_t kneekura_profile_mode_valid(uint32_t profile_mode);
KNEEKURA_EXPORT int32_t kneekura_sidecar_state_init(
        uint32_t profile_mode,
        KneekuraSidecarState *state);
KNEEKURA_EXPORT int32_t kneekura_clock_observe_epoch_day(
        KneekuraSidecarState *state,
        int64_t observed_epoch_day);
KNEEKURA_EXPORT int32_t kneekura_login_claim_available(
        const KneekuraSidecarState *state);
KNEEKURA_EXPORT int32_t kneekura_login_claim(
        KneekuraSidecarState *state,
        uint32_t cycle_length,
        uint32_t *claimed_index);

KNEEKURA_EXPORT size_t kneekura_sidecar_encoded_size(void);
KNEEKURA_EXPORT int32_t kneekura_sidecar_encode(
        const KneekuraSidecarState *state,
        uint8_t *output,
        size_t output_size);
KNEEKURA_EXPORT int32_t kneekura_sidecar_decode(
        const uint8_t *input,
        size_t input_size,
        KneekuraSidecarState *state);
KNEEKURA_EXPORT int32_t kneekura_sidecar_save_atomic(
        const char *path,
        const KneekuraSidecarState *state);
KNEEKURA_EXPORT int32_t kneekura_sidecar_load(
        const char *path,
        KneekuraSidecarState *state);

KNEEKURA_EXPORT uint32_t kneekura_provider_abi_version(void);
KNEEKURA_EXPORT uint32_t kneekura_provider_event_visible(
        uint32_t original_visible,
        uint32_t local_available);
KNEEKURA_EXPORT int32_t kneekura_provider_gacha_cost(
        uint32_t gacha_kind,
        uint32_t draw_count,
        int32_t original_cost);
KNEEKURA_EXPORT int32_t kneekura_provider_login_claim(
        KneekuraSidecarState *state,
        int64_t observed_epoch_day,
        uint32_t cycle_length,
        uint32_t *claimed_index);
KNEEKURA_EXPORT int32_t kneekura_provider_stage_cat_food(
        uint32_t difficulty,
        uint32_t already_claimed);

#ifdef __cplusplus
}
#endif

#endif