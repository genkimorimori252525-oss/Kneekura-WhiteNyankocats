#ifndef KNEEKURA_BATTLE101_H
#define KNEEKURA_BATTLE101_H

/* KNEEKURA 1.01 -- bounded battle decision logic, NO original-game hook.
 * Caller must verify the exact original-game stat and castle HP-debit seams.
 * This ABI is not installed into the original Battle Cats engine. */
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
#if defined(__GNUC__)
#define K101_EXPORT __attribute__((visibility("default")))
#else
#define K101_EXPORT
#endif

#define K101_ABI_VERSION 1u
#define K101_MAX_ACTORS 256u
#define K101_GODZILLA_ASSET_ID 702u /* public No.703, first form */
#define K101_MADOKA_ASSET_ID 288u   /* public No.289, third form */
#define K101_GODZILLA_FORM 0u
#define K101_MADOKA_FORM 2u

typedef enum K101Decision {
    K101_UNCHANGED = 0,
    K101_CHANGED = 1,
    K101_INVALID_ARGUMENT = -1,
    K101_INVALID_EVENT = -2,
    K101_CAPACITY_EXCEEDED = -3
} K101Decision;

typedef struct K101BaseHitQuery {
    uint32_t cat_asset_id;
    uint32_t cat_form_index;
    uint32_t level;
    uint32_t hit_index;
    uint32_t engine_base_damage; /* BEFORE target-specific modifiers */
} K101BaseHitQuery;

typedef struct K101CastleHitEvent {
    uint64_t battle_instance_id; /* nonzero, verified engine identity */
    uint64_t cat_instance_id;    /* nonzero, unique deployed cat identity */
    uint64_t attack_sequence_id; /* nonzero, monotonic for that cat */
    uint32_t cat_asset_id;
    uint32_t cat_form_index;
    uint32_t hit_index;          /* zero-based 0..2 */
    uint32_t engine_castle_damage; /* AFTER modifiers, BEFORE castle HP debit */
} K101CastleHitEvent;

typedef struct K101ActorTracker {
    uint64_t cat_instance_id;
    uint64_t current_sequence_id;
    uint8_t occupied;
    uint8_t credited;
    uint8_t seen_hit_mask;
    uint8_t reserved;
} K101ActorTracker;

typedef struct K101BattleState {
    uint64_t battle_instance_id;
    K101ActorTracker actors[K101_MAX_ACTORS];
} K101BattleState;

K101_EXPORT uint32_t kneekura_battle101_abi_version(void);
K101_EXPORT K101Decision kneekura_battle101_begin(
    K101BattleState *state, uint64_t battle_instance_id);
K101_EXPORT K101Decision kneekura_battle101_release_actor(
    K101BattleState *state, uint64_t battle_instance_id, uint64_t cat_instance_id);
K101_EXPORT K101Decision kneekura_battle101_base_hit(
    const K101BaseHitQuery *query, uint32_t *resolved_base_damage);
/* Negative return = unverified context; do NOT apply an HP debit. */
K101_EXPORT K101Decision kneekura_battle101_castle_hit(
    K101BattleState *state, const K101CastleHitEvent *event,
    uint32_t *resolved_castle_damage);
#ifdef __cplusplus
}
#endif
#endif