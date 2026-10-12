/* PC-only, JP15.7.1 source-pinned adapters. Called on the original GL thread.
 * No SAVE access, allocation, I/O, network, or ShadowHook dependency.
 * The static linker adapters preserve all integer/vector registers and NZCV.
 */
#include <stdint.h>
#include <stdatomic.h>
#include "kneekura_pc_balance.h"

typedef struct PcActor {
    int32_t unit;
    int32_t form;
    uint32_t initialized;
    uint32_t credited;
} PcActor;

static PcActor actors[51];
static atomic_uint_fast64_t counters[KNEEKURA_PC_BALANCE_COUNTERS];
static atomic_uintptr_t level_context;
static atomic_uint_fast64_t level_counters[3];

void kneekura_pc_xp_level_counters(uint64_t *output) {
    if (!output) return;
    for (unsigned i = 0; i < 3u; ++i)
        output[i] = atomic_load_explicit(&level_counters[i], memory_order_relaxed);
}

static uint32_t supported_level_cap(uint32_t hard) {
    /* Fixed original JP15.7.1 hard maxima, including Legend Rare 50. */
    return hard == 1u || hard == 20u || hard == 50u || hard == 60u ? hard : 0u;
}

static void xp_level_dispatch(uint64_t *r, uint32_t operation) {
    if (operation == 11u) {
        /* Only the attested original draw observer supplies this singleton. */
        if (r[0] && !(r[0] & 7u)) {
            atomic_store_explicit(&level_context, (uintptr_t)r[0], memory_order_release);
            atomic_fetch_add_explicit(&level_counters[2], 1u, memory_order_relaxed);
        }
        return;
    }
    uintptr_t context = atomic_load_explicit(&level_context, memory_order_acquire);
    if (!context) return;
    if (operation == 9u) {
        uint32_t cap = supported_level_cap((uint32_t)r[1]);
        if (cap) r[0] = cap;
        atomic_fetch_add_explicit(&level_counters[0], 1u, memory_order_relaxed);
    } else if (operation == 10u) {
        uint32_t unit = (uint32_t)r[20], level = (uint32_t)r[21];
        if (unit >= 882u || !level || level > 100u) return;
        const uint8_t *row = (const uint8_t *)(context + 0x4b060u + unit * 0x100u);
        uint32_t hard = 0u;
        for (unsigned i = 0; i < 4u; ++i)
            hard |= (uint32_t)(row[0xc8u + i] ^ row[0xfcu + i]) << (i * 8u);
        uint32_t cap = supported_level_cap(hard);
        if (cap) r[0] = level < cap;
        atomic_fetch_add_explicit(&level_counters[1], 1u, memory_order_relaxed);
    }
}

void kneekura_pc_balance_counters(uint64_t *output, uint32_t capacity) {
    if (!output || capacity < KNEEKURA_PC_BALANCE_COUNTERS) return;
    for (unsigned i = 0; i < KNEEKURA_PC_BALANCE_COUNTERS; ++i)
        output[i] = atomic_load_explicit(&counters[i], memory_order_relaxed);
}
typedef struct PcRechargeQuery {
    uint64_t frame;
    uint32_t unit;
    uint32_t form;
} PcRechargeQuery;
static PcRechargeQuery recharge_queries[32];
static atomic_flag recharge_lock = ATOMIC_FLAG_INIT;

static void recharge_dispatch(uint64_t *r, uint32_t operation) {
    /* Match the original caller frame, so concurrent/nested UI stat queries
     * cannot use another form's metadata. Lock only our short metadata update. */
    uint64_t frame = r[29];
    if (!frame) return;
    while (atomic_flag_test_and_set_explicit(&recharge_lock, memory_order_acquire)) {}
    PcRechargeQuery *match = 0;
    PcRechargeQuery *vacant = 0;
    for (unsigned i = 0; i < 32u; ++i) {
        if (recharge_queries[i].frame == frame) match = &recharge_queries[i];
        if (!recharge_queries[i].frame && !vacant) vacant = &recharge_queries[i];
    }
    if (operation == 8u) {
        if (!match) match = vacant;
        if (match) {
            match->frame = frame;
            match->unit = (uint32_t)r[1];
            match->form = (uint32_t)r[2];
        } else atomic_fetch_add_explicit(&counters[11], 1u, memory_order_relaxed);
    } else if (match) {
        if (r[19] == match->unit) {
            if (match->unit == 288u && match->form == 2u)
                r[20] = (uint32_t)((int32_t)r[20] + 4650 - 4904 + (int32_t)r[8]);
            else if (match->unit == 702u && match->form == 0u)
                r[20] = (uint32_t)((int32_t)r[20] + 15000 - 15254 + (int32_t)r[8]);
        }
        match->frame = 0u;
    }
    atomic_flag_clear_explicit(&recharge_lock, memory_order_release);
}

__attribute__((visibility("default")))
void kneekura_pc_balance_dispatch(uint64_t *r, uint32_t operation) {
    if (!r || operation < 1u || operation > 11u) return;
    if (operation >= 9u) { xp_level_dispatch(r, operation); return; }
    atomic_fetch_add_explicit(&counters[operation - 1u], 1u, memory_order_relaxed);
    if (operation == 1u) {
        /* Original growth result BEFORE treasure/orbs/talents, never 50000 here. */
        if (r[24] == 30u && r[21] == 702u && r[20] == 0u) r[19] = 20000u;
    } else if (operation == 4u) {
        /* Capture the actual constructor arguments, including the original form. */
        uint32_t slot = (uint32_t)r[19];
        if (r[20] != 1u || slot == 0u || slot > 50u) return;
        actors[slot].unit = (int32_t)r[22];
        actors[slot].form = (int32_t)r[25];
        actors[slot].initialized = 1u;
        actors[slot].credited = 0u;
    } else if (operation == 3u) {
        uint32_t slot = (uint32_t)r[20];
        /* Original frame reset covers cycle start, interruption, and slot reuse.
         * Global tick arithmetic incorrectly splits a paused attack sequence. */
        if (r[21] == 1u && slot > 0u && slot <= 50u && (uint32_t)r[19] == 0u)
            actors[slot].credited = 0u;
    } else if (operation == 2u) {
        uint32_t slot = (uint32_t)r[22];
        if (r[19] != 0u || slot == 0u || slot > 50u) return;
        PcActor *a = &actors[slot];
        if (!a->initialized || a->unit != 702 || a->form != 0) return;
        uintptr_t actor = (uintptr_t)r[20] + 0x84080u + 0xc804u + slot * 0x3ecu;
        if (*(const int32_t *)(actor + 4u) != 702) return;
        /* Original final damage is w23, destination w2. Credit only positive
         * hits; a first miss leaves the one-point budget for a later hit.
         * Godzilla form0 has no wave/surge/delayed attack generators. */
        uint32_t damage = (uint32_t)r[23];
        r[2] = 0u;
        atomic_fetch_add_explicit(&counters[9], 1u, memory_order_relaxed);
        if (*(const int32_t *)(actor + 0x9cu) != 0 ||
            *(const int32_t *)(actor + 0x2b8u) != 0 ||
            *(const int32_t *)(actor + 0x380u) != 0) {
            atomic_fetch_add_explicit(&counters[10], 1u, memory_order_relaxed);
            return;
        }
        if (!a->credited && damage > 0u && (int32_t)damage > 0) {
            a->credited = 1u;
            r[2] = 1u;
            atomic_fetch_add_explicit(&counters[8], 1u, memory_order_relaxed);
            atomic_fetch_sub_explicit(&counters[9], 1u, memory_order_relaxed);
        }
    } else if (operation == 5u) {
        /* Loaded frequency before the original talent percentage reduction. */
        if (r[20] == 702u && r[19] == 0u) r[22] += 1u;
    } else if (operation == 6u) {
        /* EoC2 chapter factor truncates CSV integer cost by one yen.
         * Add that yen before original stage/combo adjustments; keep talents. */
        if ((r[19] == 288u && r[22] == 2u) || (r[19] == 702u && r[22] == 0u)) {
            const int32_t chapter = *(const int32_t *)((uintptr_t)r[0] + 0x38fad8u);
            if (chapter == 1) r[25] += 100u;
        }
    } else if (operation == 7u || operation == 8u) {
        /* Fixed approved base cooldown. Keep original talent subtraction,
         * combo calculation, minimum clamp and later stage overrides. */
        recharge_dispatch(r, operation);
    }
}
