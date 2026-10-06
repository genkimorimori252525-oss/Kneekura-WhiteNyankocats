package jp.kneekura.whitenyankocats;

import android.content.Context;
import android.content.SharedPreferences;

import java.util.LinkedHashMap;
import java.util.Map;

public final class ProfileStore {
    public static final long MAX_VALUE = 999_999_999L;
    private static final String PREFS = "kneekura_profile";
    private static final String INITIALIZED = "initialized_v1";

    private static final String[] MAXED_RESOURCE_KEYS = {
            "cat_food",
            "xp",
            "np",
            "rare_ticket",
            "platinum_ticket",
            "legend_ticket",
            "leadership",
            "speed_up",
            "treasure_radar",
            "rich_cat",
            "sniper_cat",
            "cat_cpu",
            "cat_jobs",
            "catfruit_red",
            "catfruit_purple",
            "catfruit_blue",
            "catfruit_green",
            "catfruit_yellow",
            "catfruit_seed_red",
            "catfruit_seed_purple",
            "catfruit_seed_blue",
            "catfruit_seed_green",
            "catfruit_seed_yellow",
            "epic_catfruit",
            "elder_catfruit",
            "gold_catfruit",
            "catseye_normal",
            "catseye_special",
            "catseye_rare",
            "catseye_super_rare",
            "catseye_uber",
            "catseye_legend",
            "behemoth_stone_red",
            "behemoth_stone_purple",
            "behemoth_stone_blue",
            "behemoth_stone_green",
            "behemoth_stone_yellow",
            "epic_behemoth_stone",
            "talent_orb",
            "evolution_material",
            "battle_item",
            "local_event_currency"
    };

    private ProfileStore() {
    }

    public static void ensureMaxed(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        if (prefs.getBoolean(INITIALIZED, false)) {
            return;
        }

        SharedPreferences.Editor edit = prefs.edit();
        edit.putBoolean(INITIALIZED, true);
        edit.putBoolean("all_units_unlocked", true);\n        edit.putBoolean("all_stages_unlocked", true);
        edit.putInt("default_form", 0);
        edit.putBoolean("offline_only", true);
        edit.putBoolean("resource_mode_max", true);
        for (String key : MAXED_RESOURCE_KEYS) {
            edit.putLong(key, MAX_VALUE);
        }
        edit.apply();
    }

    public static Map<String, Long> headlineResources(Context context) {
        ensureMaxed(context);
        SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        Map<String, Long> values = new LinkedHashMap<>();
        values.put("ネコカン", prefs.getLong("cat_food", MAX_VALUE));
        values.put("XP", prefs.getLong("xp", MAX_VALUE));
        values.put("NP", prefs.getLong("np", MAX_VALUE));
        values.put("進化素材", prefs.getLong("evolution_material", MAX_VALUE));
        values.put("チケット", prefs.getLong("rare_ticket", MAX_VALUE));
        return values;
    }
}