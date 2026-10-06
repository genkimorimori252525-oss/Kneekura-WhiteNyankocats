#include "kneekura_shim.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

static void require(int condition, const char *message) {
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        exit(1);
    }
}

int main(void) {
    require(
            kneekura_provider_abi_version() == KNEEKURA_PROVIDER_ABI_VERSION,
            "provider ABI");

#if KNEEKURA_DEFAULT_FEATURE_MASK == 0
    require(kneekura_provider_event_visible(0, 1) == 0u, "event pass-through off");
    require(
            kneekura_provider_gacha_cost(KNEEKURA_GACHA_KIND_SUPER, 1, 777)
                    == 777,
            "gacha pass-through off");
    require(kneekura_provider_stage_cat_food(12, 0) == 0, "reward disabled");

    KneekuraSidecarState state;
    require(
            kneekura_sidecar_state_init(
                    KNEEKURA_PROFILE_PRACTICE_CLEAN, &state)
                    == KNEEKURA_STATUS_OK,
            "state init");
    require(
            kneekura_provider_login_claim(&state, 100, 5, NULL)
                    == KNEEKURA_STATUS_DISABLED,
            "login provider disabled");
#else
    require(kneekura_provider_event_visible(0, 1) == 1u, "local event visible");
    require(kneekura_provider_event_visible(1, 0) == 1u, "original event visible");
    require(
            kneekura_provider_gacha_cost(KNEEKURA_GACHA_KIND_SUPER, 1, 777)
                    == 150,
            "single gacha cost");
    require(
            kneekura_provider_gacha_cost(KNEEKURA_GACHA_KIND_SUPER, 11, 777)
                    == 1500,
            "eleven gacha cost");
    require(
            kneekura_provider_gacha_cost(999, 1, 777) == 777,
            "unknown gacha pass-through");

    const int expected[] = {1, 1, 1, 2, 2, 2, 3, 3, 5, 5, 8, 10, 10};
    for (uint32_t difficulty = 1; difficulty <= 13; ++difficulty) {
        require(
                kneekura_provider_stage_cat_food(difficulty, 0)
                        == expected[difficulty - 1],
                "difficulty reward table");
    }
    require(kneekura_provider_stage_cat_food(12, 1) == 0, "claimed reward zero");

    KneekuraSidecarState state;
    require(
            kneekura_sidecar_state_init(
                    KNEEKURA_PROFILE_PRACTICE_CLEAN, &state)
                    == KNEEKURA_STATUS_OK,
            "state init");
    uint32_t claimed = UINT32_MAX;
    require(
            kneekura_provider_login_claim(&state, 100, 2, &claimed) == 1,
            "first login claim");
    require(claimed == 0u, "first stamp");
    require(
            kneekura_provider_login_claim(&state, 100, 2, &claimed) == 0,
            "same day no second claim");
    require(
            kneekura_provider_login_claim(&state, 101, 2, &claimed) == 1,
            "next day claim");
    require(claimed == 1u, "second stamp");
#endif

    return 0;
}
