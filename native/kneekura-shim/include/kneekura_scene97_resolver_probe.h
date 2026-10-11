#ifndef KNEEKURA_SCENE97_RESOLVER_PROBE_H
#define KNEEKURA_SCENE97_RESOLVER_PROBE_H

/*
 * Privacy-bounded, PURE read-only histogram of the original JP15.7.1
 * DownloadBatchTask's 35 int32_t resolver return slots.
 *
 * These are constructor/source-lookup return values, NOT a proven
 * downloader completion state or proof that a game data file was consumed.
 * Caller must establish the exact original game context lifetime/scene.
 * There is deliberately no game symbol, SAVE access, network or JNI here.
 */
#include <stddef.h>
#include <stdint.h>

enum { KNEEKURA_SCENE97_RESOLVER_SLOT_COUNT = 35 };

struct KneekuraScene97ResolverHistogram {
    uint32_t missing; /* exact -1 only */
    uint32_t zero;    /* exact 0 only */
    uint32_t one;     /* exact 1 only */
    uint32_t other;   /* every remaining signed int32 */
};

/* A zero return means invalid input; out is never partially written. */
int kneekura_scene97_resolver_histogram(
        const uint8_t *slot_bytes, size_t byte_count,
        struct KneekuraScene97ResolverHistogram *out);

/* Six bits per bounded count (0..35); UINT32_MAX means invalid. */
uint32_t kneekura_scene97_resolver_histogram_signature(
        const struct KneekuraScene97ResolverHistogram *value);

#endif
