#include "kneekura_battle101.h"
#include "kneekura_shim.h"
#include <assert.h>
#include <stdio.h>

static K101CastleHitEvent mk(uint64_t battle, uint64_t actor, uint64_t seq,
                              uint32_t hit, uint32_t damage) {
    K101CastleHitEvent e = {0};
    e.battle_instance_id = battle;
    e.cat_instance_id = actor;
    e.attack_sequence_id = seq;
    e.cat_asset_id = K101_GODZILLA_ASSET_ID;
    e.cat_form_index = K101_GODZILLA_FORM;
    e.hit_index = hit;
    e.engine_castle_damage = damage;
    return e;
}
static void test_base_damage(void) {
    uint32_t out = 0u;
    const int enabled = kneekura_feature_enabled(KNEEKURA_FEATURE_BATTLE101);
    K101BaseHitQuery madoka = {288u, 2u, 30u, 0u, 27999u};
    assert(kneekura_battle101_abi_version() == 1u);
    assert(kneekura_battle101_base_hit(&madoka, &out) ==
           (enabled ? K101_CHANGED : K101_UNCHANGED));
    assert(out == (enabled ? 28000u : 27999u));
    madoka.cat_form_index = 1u;
    assert(kneekura_battle101_base_hit(&madoka, &out) == K101_UNCHANGED);
    assert(out == 27999u);
    madoka.level = 60u; madoka.cat_form_index = 2u;
    assert(kneekura_battle101_base_hit(&madoka, &out) == K101_UNCHANGED);

    K101BaseHitQuery god = {702u, 0u, 30u, 0u, 49997u};
    for (uint32_t i = 0u; i < 3u; i++) {
        god.hit_index = i;
        assert(kneekura_battle101_base_hit(&god, &out) ==
               (enabled ? K101_CHANGED : K101_UNCHANGED));
        assert(out == (enabled ? 50000u : 49997u));
    }
    god.cat_form_index = 1u;
    assert(kneekura_battle101_base_hit(&god, &out) == K101_UNCHANGED);
    assert(out == 49997u);
    assert(kneekura_battle101_base_hit(NULL, &out) == K101_INVALID_ARGUMENT);
}
static void test_castle_damage(void) {
    K101BattleState st;
    const int enabled = kneekura_feature_enabled(KNEEKURA_FEATURE_BATTLE101);
    uint32_t out = 0u;
    assert(kneekura_battle101_begin(&st, 7u) == K101_CHANGED);
    for (uint32_t hit = 0u; hit < 3u; hit++) {
        K101CastleHitEvent e = mk(7, 10, 1, hit, 50000);
        assert(kneekura_battle101_castle_hit(&st, &e, &out) ==
               (enabled ? K101_CHANGED : K101_UNCHANGED));
        assert(out == (enabled ? (hit == 0u ? 1u : 0u) : 50000u));
    }
    K101CastleHitEvent repeated = mk(7, 10, 1, 0, 50000);
    kneekura_battle101_castle_hit(&st, &repeated, &out);
    assert(out == (enabled ? 0u : 50000u));
    K101CastleHitEvent other = mk(7, 11, 1, 0, 50000);
    kneekura_battle101_castle_hit(&st, &other, &out);
    assert(out == (enabled ? 1u : 50000u)); /* separate actor */
    K101CastleHitEvent second = mk(7, 10, 2, 2, 50000);
    kneekura_battle101_castle_hit(&st, &second, &out);
    assert(out == (enabled ? 1u : 50000u)); /* next sequence */
    K101CastleHitEvent stale = mk(7, 10, 1, 1, 50000);
    assert(kneekura_battle101_castle_hit(&st, &stale, &out) ==
           (enabled ? K101_INVALID_EVENT : K101_UNCHANGED));
    assert(out == (enabled ? 0u : 50000u));
    stale.cat_asset_id = 1u; /* ordinary cat always bypassed */
    assert(kneekura_battle101_castle_hit(&st, &stale, &out) == K101_UNCHANGED);
    assert(out == 50000u);
    assert(kneekura_battle101_release_actor(&st, 7, 10) ==
           (enabled ? K101_CHANGED : K101_UNCHANGED));
}
static void test_capacity_and_zero_hit(void) {
    K101BattleState st;
    uint32_t out = 0u;
    assert(kneekura_battle101_begin(&st, 99u) == K101_CHANGED);
    if (!kneekura_feature_enabled(KNEEKURA_FEATURE_BATTLE101)) return;
    K101CastleHitEvent zero = mk(99, 13, 1, 0, 0);
    assert(kneekura_battle101_castle_hit(&st, &zero, &out) == K101_CHANGED);
    assert(out == 0u);
    K101CastleHitEvent later = mk(99, 13, 1, 1, 50000);
    assert(kneekura_battle101_castle_hit(&st, &later, &out) == K101_CHANGED);
    assert(out == 1u); /* first actual landed strike */
    kneekura_battle101_castle_hit(&st, &later, &out);
    assert(out == 0u); /* cannot credit same strike twice */
    K101CastleHitEvent wrong_battle = mk(100, 14, 1, 0, 50000);
    assert(kneekura_battle101_castle_hit(&st, &wrong_battle, &out) == K101_INVALID_EVENT);
    assert(out == 0u); /* invalid context fail closed */
    for (uint64_t i = 0u; i < K101_MAX_ACTORS - 1u; i++) {
        K101CastleHitEvent e = mk(99, i + 20u, 1, 0, 50000);
        assert(kneekura_battle101_castle_hit(&st, &e, &out) == K101_CHANGED);
    }
    K101CastleHitEvent full = mk(99, 9999, 1, 0, 50000);
    assert(kneekura_battle101_castle_hit(&st, &full, &out) == K101_CAPACITY_EXCEEDED);
    assert(out == 0u);
    assert(kneekura_battle101_release_actor(&st, 99, 13) == K101_CHANGED);
    assert(kneekura_battle101_castle_hit(&st, &full, &out) == K101_CHANGED);
    assert(out == 1u);
    assert(kneekura_battle101_begin(&st, 101u) == K101_CHANGED);
    assert(kneekura_battle101_castle_hit(&st, &full, &out) == K101_INVALID_EVENT);
}
int main(void) {
    test_base_damage();
    test_castle_damage();
    test_capacity_and_zero_hit();
    puts("PASS battle101 native policy");
    return 0;
}