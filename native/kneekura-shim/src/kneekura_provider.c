#include "kneekura_shim.h"

uint32_t kneekura_provider_abi_version(void) {
    return KNEEKURA_PROVIDER_ABI_VERSION;
}

uint32_t kneekura_provider_event_visible(
        uint32_t original_visible,
        uint32_t local_available) {
    if (kneekura_feature_enabled(KNEEKURA_FEATURE_PROVIDER_API) == 0u
            || kneekura_feature_enabled(KNEEKURA_FEATURE_LOCAL_EVENTS) == 0u) {
        return original_visible != 0u ? 1u : 0u;
    }
    return original_visible != 0u || local_available != 0u ? 1u : 0u;
}

int32_t kneekura_provider_gacha_cost(
        uint32_t gacha_kind,
        uint32_t draw_count,
        int32_t original_cost) {
    if (kneekura_feature_enabled(KNEEKURA_FEATURE_PROVIDER_API) == 0u
            || kneekura_feature_enabled(KNEEKURA_FEATURE_SUPER_GACHA) == 0u
            || gacha_kind != KNEEKURA_GACHA_KIND_SUPER) {
        return original_cost;
    }

    if (draw_count == 1u) {
        return 150;
    }
    if (draw_count == 11u) {
        return 1500;
    }
    return original_cost;
}

int32_t kneekura_provider_login_claim(
        KneekuraSidecarState *state,
        int64_t observed_epoch_day,
        uint32_t cycle_length,
        uint32_t *claimed_index) {
    if (kneekura_feature_enabled(KNEEKURA_FEATURE_PROVIDER_API) == 0u
            || kneekura_feature_enabled(KNEEKURA_FEATURE_LOGIN_BONUS) == 0u
            || kneekura_feature_enabled(KNEEKURA_FEATURE_LOCAL_CLOCK) == 0u) {
        return KNEEKURA_STATUS_DISABLED;
    }

    int32_t available = kneekura_clock_observe_epoch_day(
            state, observed_epoch_day);
    if (available <= 0) {
        return available;
    }
    return kneekura_login_claim(state, cycle_length, claimed_index);
}

int32_t kneekura_provider_stage_cat_food(
        uint32_t difficulty,
        uint32_t already_claimed) {
    if (kneekura_feature_enabled(KNEEKURA_FEATURE_PROVIDER_API) == 0u
            || kneekura_feature_enabled(KNEEKURA_FEATURE_STAGE_CATFOOD) == 0u
            || already_claimed != 0u) {
        return 0;
    }

    if (difficulty <= 3u) return 1;
    if (difficulty <= 6u) return 2;
    if (difficulty <= 8u) return 3;
    if (difficulty <= 10u) return 5;
    if (difficulty == 11u) return 8;
    return 10;
}
