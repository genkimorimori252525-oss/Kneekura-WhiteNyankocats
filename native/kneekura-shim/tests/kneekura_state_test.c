#include "kneekura_shim.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static void require(int condition, const char *message) {
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        exit(1);
    }
}

int main(void) {
    KneekuraSidecarState state;
    require(
            kneekura_sidecar_state_init(
                    KNEEKURA_PROFILE_PRACTICE_CLEAN, &state)
                    == KNEEKURA_STATUS_OK,
            "state init");
    require(state.last_seen_epoch_day == KNEEKURA_LOGIN_DAY_UNSET, "unset seen day");

    require(kneekura_clock_observe_epoch_day(&state, 100) == 1, "first day available");
    uint32_t claimed = UINT32_MAX;
    require(kneekura_login_claim(&state, 3, &claimed) == 1, "claim day 100");
    require(claimed == 0u, "first stamp");
    require(kneekura_clock_observe_epoch_day(&state, 100) == 0, "same day denied");
    require(kneekura_clock_observe_epoch_day(&state, 99) == 0, "rollback denied");

    require(kneekura_clock_observe_epoch_day(&state, 500) == 1, "forward jump gives one");
    require(kneekura_login_claim(&state, 3, &claimed) == 1, "claim forward day");
    require(claimed == 1u, "second stamp");
    require(kneekura_login_claim(&state, 3, &claimed) == 0, "cannot claim twice");
    require(kneekura_clock_observe_epoch_day(&state, 501) == 1, "next day available");
    require(kneekura_login_claim(&state, 3, &claimed) == 1, "third claim");
    require(claimed == 2u, "third stamp");
    require(state.login_cycle_index == 0u, "cycle wraps");

    uint8_t encoded[128];
    memset(encoded, 0, sizeof(encoded));
    require(
            kneekura_sidecar_encode(&state, encoded, sizeof(encoded))
                    == KNEEKURA_STATUS_OK,
            "encode");
    KneekuraSidecarState decoded;
    require(
            kneekura_sidecar_decode(
                    encoded, kneekura_sidecar_encoded_size(), &decoded)
                    == KNEEKURA_STATUS_OK,
            "decode");
    require(decoded.last_claim_epoch_day == 501, "decode day");
    require(decoded.profile_mode == KNEEKURA_PROFILE_PRACTICE_CLEAN, "decode profile");

    encoded[63] ^= 0x1u;
    require(
            kneekura_sidecar_decode(
                    encoded, kneekura_sidecar_encoded_size(), &decoded)
                    == KNEEKURA_STATUS_CHECKSUM_MISMATCH,
            "checksum catches mutation");

    const char *path = "/tmp/kneekura-sidecar-test.bin";
    (void) unlink(path);
    (void) unlink("/tmp/kneekura-sidecar-test.bin.tmp");
    (void) unlink("/tmp/kneekura-sidecar-test.bin.bak");

#if (KNEEKURA_DEFAULT_FEATURE_MASK & KNEEKURA_FEATURE_LOCAL_STATE)
    require(
            kneekura_sidecar_save_atomic(path, &state) == KNEEKURA_STATUS_OK,
            "enabled atomic save");
    memset(&decoded, 0, sizeof(decoded));
    require(
            kneekura_sidecar_load(path, &decoded) == KNEEKURA_STATUS_OK,
            "enabled load");
    require(decoded.last_claim_epoch_day == 501, "loaded state");
#else
    require(
            kneekura_sidecar_save_atomic(path, &state) == KNEEKURA_STATUS_DISABLED,
            "disabled save");
    struct stat info;
    require(stat(path, &info) != 0, "feature-off must not create file");
    require(
            kneekura_sidecar_load(path, &decoded) == KNEEKURA_STATUS_DISABLED,
            "disabled load");
#endif

    (void) unlink(path);
    (void) unlink("/tmp/kneekura-sidecar-test.bin.tmp");
    (void) unlink("/tmp/kneekura-sidecar-test.bin.bak");
    return 0;
}