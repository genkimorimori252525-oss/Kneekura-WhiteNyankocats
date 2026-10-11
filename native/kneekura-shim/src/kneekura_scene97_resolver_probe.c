#include "kneekura_scene97_resolver_probe.h"

#include <string.h>

int kneekura_scene97_resolver_histogram(
        const uint8_t *slot_bytes, size_t byte_count,
        struct KneekuraScene97ResolverHistogram *out) {
    if (slot_bytes == NULL || out == NULL ||
        byte_count != KNEEKURA_SCENE97_RESOLVER_SLOT_COUNT * sizeof(int32_t)) {
        return 0;
    }
    struct KneekuraScene97ResolverHistogram value = {0u, 0u, 0u, 0u};
    for (size_t i = 0; i < KNEEKURA_SCENE97_RESOLVER_SLOT_COUNT; ++i) {
        int32_t original_return = 0;
        memcpy(&original_return, slot_bytes + i * sizeof(original_return),
               sizeof(original_return));
        if (original_return == -1) {
            value.missing++;
        } else if (original_return == 0) {
            value.zero++;
        } else if (original_return == 1) {
            value.one++;
        } else {
            value.other++;
        }
    }
    *out = value;
    return 1;
}

uint32_t kneekura_scene97_resolver_histogram_signature(
        const struct KneekuraScene97ResolverHistogram *value) {
    if (value == NULL || value->missing > 35u || value->zero > 35u ||
        value->one > 35u || value->other > 35u ||
        value->missing + value->zero + value->one + value->other != 35u) {
        return UINT32_MAX;
    }
    return value->missing
        | (value->zero << 6)
        | (value->one << 12)
        | (value->other << 18);
}
