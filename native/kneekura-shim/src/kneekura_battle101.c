#include "kneekura_battle101.h"
#include "kneekura_shim.h"
#include <stddef.h>
#include <string.h>

/* Deliberately NOT a hook. No native addresses, Java or private game state. */
static uint32_t battle101_enabled(void) {
    return kneekura_feature_enabled(KNEEKURA_FEATURE_BATTLE101);
}
uint32_t kneekura_battle101_abi_version(void) {
    return K101_ABI_VERSION;
}
K101Decision kneekura_battle101_begin(K101BattleState *state,
                                        uint64_t battle_instance_id) {
    if (state == NULL || battle_instance_id == 0u) {
        return K101_INVALID_ARGUMENT;
    }
    memset(state, 0, sizeof(*state));
    state->battle_instance_id = battle_instance_id;
    return K101_CHANGED;
}
K101Decision kneekura_battle101_release_actor(K101BattleState *state,
                                                 uint64_t battle_instance_id,
                                                 uint64_t cat_instance_id) {
    if (state == NULL || battle_instance_id == 0u || cat_instance_id == 0u ||
            state->battle_instance_id != battle_instance_id) {
        return K101_INVALID_ARGUMENT;
    }
    for (size_t i = 0; i < K101_MAX_ACTORS; i++) {
        K101ActorTracker *actor = &state->actors[i];
        if (actor->occupied && actor->cat_instance_id == cat_instance_id) {
            memset(actor, 0, sizeof(*actor));
            return K101_CHANGED;
        }
    }
    return K101_UNCHANGED;
}
K101Decision kneekura_battle101_base_hit(const K101BaseHitQuery *query,
                                           uint32_t *resolved_base_damage) {
    if (query == NULL || resolved_base_damage == NULL) {
        return K101_INVALID_ARGUMENT;
    }
    *resolved_base_damage = query->engine_base_damage;
    if (!battle101_enabled()) return K101_UNCHANGED;
    if (query->level == 30u &&
            query->cat_asset_id == K101_MADOKA_ASSET_ID &&
            query->cat_form_index == K101_MADOKA_FORM &&
            query->hit_index == 0u) {
        *resolved_base_damage = 28000u;
        return K101_CHANGED;
    }
    if (query->level == 30u &&
            query->cat_asset_id == K101_GODZILLA_ASSET_ID &&
            query->cat_form_index == K101_GODZILLA_FORM &&
            query->hit_index < 3u) {
        *resolved_base_damage = 50000u;
        return K101_CHANGED;
    }
    return K101_UNCHANGED;
}
K101Decision kneekura_battle101_castle_hit(K101BattleState *state,
                                            const K101CastleHitEvent *event,
                                            uint32_t *resolved_castle_damage) {
    if (state == NULL || event == NULL || resolved_castle_damage == NULL) {
        return K101_INVALID_ARGUMENT;
    }
    *resolved_castle_damage = event->engine_castle_damage;
    if (!battle101_enabled()) return K101_UNCHANGED;
    if (event->cat_asset_id != K101_GODZILLA_ASSET_ID ||
            event->cat_form_index != K101_GODZILLA_FORM) {
        return K101_UNCHANGED;
    }
    /* When enabled for Godzilla, unexpected state never leaks large damage. */
    *resolved_castle_damage = 0u;
    if (state->battle_instance_id == 0u ||
            event->battle_instance_id != state->battle_instance_id ||
            event->cat_instance_id == 0u || event->attack_sequence_id == 0u ||
            event->hit_index >= 3u) {
        return K101_INVALID_EVENT;
    }
    K101ActorTracker *slot = NULL;
    K101ActorTracker *vacant = NULL;
    for (size_t i = 0; i < K101_MAX_ACTORS; i++) {
        K101ActorTracker *candidate = &state->actors[i];
        if (candidate->occupied &&
                candidate->cat_instance_id == event->cat_instance_id) {
            slot = candidate;
            break;
        }
        if (!candidate->occupied && vacant == NULL) vacant = candidate;
    }
    if (slot == NULL) {
        if (vacant == NULL) return K101_CAPACITY_EXCEEDED;
        slot = vacant;
        memset(slot, 0, sizeof(*slot));
        slot->occupied = 1u;
        slot->cat_instance_id = event->cat_instance_id;
        slot->current_sequence_id = event->attack_sequence_id;
    } else {
        if (event->attack_sequence_id < slot->current_sequence_id) {
            return K101_INVALID_EVENT;
        }
        if (event->attack_sequence_id > slot->current_sequence_id) {
            slot->current_sequence_id = event->attack_sequence_id;
            slot->credited = 0u;
            slot->seen_hit_mask = 0u;
        }
    }
    const uint8_t hit_mask = (uint8_t)(1u << event->hit_index);
    if ((slot->seen_hit_mask & hit_mask) != 0u) {
        return K101_CHANGED; /* repeated strike: stays zero damage */
    }
    slot->seen_hit_mask = (uint8_t)(slot->seen_hit_mask | hit_mask);
    if (!slot->credited && event->engine_castle_damage > 0u) {
        *resolved_castle_damage = 1u;
        slot->credited = 1u;
    }
    return K101_CHANGED;
}