package jp.kneekura.whitenyankocats;

import android.content.Context;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

public final class GameContentStore {
    private static final String FILE_NAME = "game-content.json";

    private GameContentStore() {
    }

    public static void save(
            Context context,
            List<EnemyRecord> enemies,
            List<StageDefinition> stages
    ) throws Exception {
        JSONObject root = new JSONObject();
        root.put("schema_version", 2);

        JSONArray enemyRows = new JSONArray();
        for (EnemyRecord enemy : enemies) {
            JSONObject row = new JSONObject();
            row.put("enemy_id", enemy.enemyId);
            row.put("name", enemy.name);
            row.put("hp", enemy.hp);
            row.put("kbs", enemy.kbs);
            row.put("speed", enemy.speed);
            row.put("attack_damage", enemy.attackDamage);
            row.put("attack_interval", enemy.attackInterval);
            row.put("range", enemy.range);
            row.put("money_drop", enemy.moneyDrop);
            row.put("collision_start", enemy.collisionStart);
            row.put("collision_width", enemy.collisionWidth);
            row.put("area_attack", enemy.areaAttack);
            row.put("foreswing", enemy.foreswing);
            enemyRows.put(row);
        }
        root.put("enemies", enemyRows);

        JSONArray stageRows = new JSONArray();
        for (StageDefinition stage : stages) {
            JSONObject row = new JSONObject();
            row.put("key", stage.key);
            row.put("category", stage.category);
            row.put("source_prefix", stage.sourcePrefix);
            row.put("map_index", stage.mapIndex);
            row.put("stage_index", stage.stageIndex);
            row.put("map_name", stage.mapName);
            row.put("stage_name", stage.stageName);
            row.put("name", stage.name);
            row.put("source_file", stage.sourceFile);
            row.put("width", stage.width);
            row.put("base_health", stage.baseHealth);
            row.put("min_production_frames", stage.minProductionFrames);
            row.put("max_production_frames", stage.maxProductionFrames);
            row.put("background_id", stage.backgroundId);
            row.put("max_enemy_count", stage.maxEnemyCount);
            row.put("castle_enemy_id", stage.castleEnemyId);
            row.put("energy", stage.energy);
            row.put("clear_xp", stage.clearXp);
            row.put("main_music_id", stage.mainMusicId);
            row.put("boss_music_hp_percentage", stage.bossMusicHpPercentage);
            row.put("boss_music_id", stage.bossMusicId);
            row.put("reward_type", stage.rewardType);
            row.put("star_count", stage.starCount);
            row.put("difficulty_mask", stage.difficultyMask);

            JSONArray multipliers = new JSONArray();
            for (int multiplier : stage.starMultipliers) {
                multipliers.put(multiplier);
            }
            row.put("star_multipliers", multipliers);

            JSONArray rewardRows = new JSONArray();
            for (StageReward reward : stage.rewards) {
                JSONObject rewardRow = new JSONObject();
                rewardRow.put("probability", reward.probability);
                rewardRow.put("item_id", reward.itemId);
                rewardRow.put("amount", reward.amount);
                rewardRow.put("timed_score", reward.timedScore);
                rewardRows.put(rewardRow);
            }
            row.put("rewards", rewardRows);

            JSONArray restrictionRows = new JSONArray();
            for (StageRestriction restriction : stage.restrictions) {
                JSONObject restrictionRow = new JSONObject();
                restrictionRow.put("star_id", restriction.starId);
                restrictionRow.put("rarity_mask", restriction.rarityMask);
                restrictionRow.put("deploy_limit", restriction.deployLimit);
                restrictionRow.put("slot_limit", restriction.slotLimit);
                restrictionRow.put("min_deploy_cost", restriction.minDeployCost);
                restrictionRow.put("max_deploy_cost", restriction.maxDeployCost);
                restrictionRow.put("group_id", restriction.groupId);
                restrictionRows.put(restrictionRow);
            }
            row.put("restrictions", restrictionRows);

            JSONArray spawnRows = new JSONArray();
            for (EnemySpawn spawn : stage.spawns) {
                JSONObject spawnRow = new JSONObject();
                spawnRow.put("enemy_release_id", spawn.enemyReleaseId);
                spawnRow.put("max_enemy_count", spawn.maxEnemyCount);
                spawnRow.put("start_frame", spawn.startFrame);
                spawnRow.put("min_spawn_interval", spawn.minSpawnInterval);
                spawnRow.put("max_spawn_interval", spawn.maxSpawnInterval);
                spawnRow.put("spawn_base_percent", spawn.spawnBasePercent);
                spawnRow.put("min_z", spawn.minZ);
                spawnRow.put("max_z", spawn.maxZ);
                spawnRow.put("boss", spawn.boss);
                spawnRow.put("magnification", spawn.magnification);
                spawnRows.put(spawnRow);
            }
            row.put("spawns", spawnRows);
            stageRows.put(row);
        }
        root.put("stages", stageRows);

        File target = new File(context.getFilesDir(), FILE_NAME);
        try (FileOutputStream out = new FileOutputStream(target)) {
            out.write(root.toString().getBytes(StandardCharsets.UTF_8));
        }
    }

    public static List<EnemyRecord> loadEnemies(Context context) {
        List<EnemyRecord> result = new ArrayList<>();
        try {
            JSONArray rows = readRoot(context).getJSONArray("enemies");
            for (int i = 0; i < rows.length(); i++) {
                JSONObject row = rows.getJSONObject(i);
                result.add(new EnemyRecord(
                        row.getInt("enemy_id"),
                        row.optString("name", ""),
                        row.optLong("hp", 1),
                        row.optInt("kbs", 1),
                        row.optInt("speed", 1),
                        row.optLong("attack_damage", 1),
                        row.optInt("attack_interval", 30),
                        row.optInt("range", 100),
                        row.optInt("money_drop", 0),
                        row.optInt("collision_start", 0),
                        row.optInt("collision_width", 0),
                        row.optBoolean("area_attack", false),
                        row.optInt("foreswing", 1)
                ));
            }
        } catch (Exception ignored) {
            result.clear();
        }
        return result;
    }

    public static List<StageDefinition> loadStages(Context context) {
        List<StageDefinition> result = new ArrayList<>();
        try {
            JSONArray rows = readRoot(context).getJSONArray("stages");
            for (int i = 0; i < rows.length(); i++) {
                JSONObject row = rows.getJSONObject(i);

                List<EnemySpawn> spawns = new ArrayList<>();
                JSONArray spawnRows = row.optJSONArray("spawns");
                if (spawnRows != null) {
                    for (int j = 0; j < spawnRows.length(); j++) {
                        JSONObject spawn = spawnRows.getJSONObject(j);
                        spawns.add(new EnemySpawn(
                                spawn.getInt("enemy_release_id"),
                                spawn.optInt("max_enemy_count", 1),
                                spawn.optInt("start_frame", 0),
                                spawn.optInt("min_spawn_interval", 0),
                                spawn.optInt("max_spawn_interval", 0),
                                spawn.optInt("spawn_base_percent", 100),
                                spawn.optInt("min_z", 0),
                                spawn.optInt("max_z", 0),
                                spawn.optBoolean("boss", false),
                                spawn.optInt("magnification", 100)
                        ));
                    }
                }

                List<StageReward> rewards = new ArrayList<>();
                JSONArray rewardRows = row.optJSONArray("rewards");
                if (rewardRows != null) {
                    for (int j = 0; j < rewardRows.length(); j++) {
                        JSONObject reward = rewardRows.getJSONObject(j);
                        rewards.add(new StageReward(
                                reward.optInt("probability", -1),
                                reward.optInt("item_id", -1),
                                reward.optInt("amount", 0),
                                reward.optBoolean("timed_score", false)
                        ));
                    }
                }

                List<StageRestriction> restrictions = new ArrayList<>();
                JSONArray restrictionRows = row.optJSONArray("restrictions");
                if (restrictionRows != null) {
                    for (int j = 0; j < restrictionRows.length(); j++) {
                        JSONObject restriction = restrictionRows.getJSONObject(j);
                        restrictions.add(new StageRestriction(
                                restriction.optInt("star_id", 0),
                                restriction.optInt("rarity_mask", 0),
                                restriction.optInt("deploy_limit", 0),
                                restriction.optInt("slot_limit", 0),
                                restriction.optInt("min_deploy_cost", 0),
                                restriction.optInt("max_deploy_cost", 0),
                                restriction.optInt("group_id", 0)
                        ));
                    }
                }

                int[] starMultipliers = new int[]{100, 100, 100, 100};
                JSONArray multiplierRows = row.optJSONArray("star_multipliers");
                if (multiplierRows != null) {
                    for (int j = 0; j < Math.min(4, multiplierRows.length()); j++) {
                        starMultipliers[j] = multiplierRows.optInt(j, 100);
                    }
                }

                String sourceFile = row.optString("source_file", "");
                String displayName = row.optString("name", sourceFile);
                String mapName = row.optString("map_name", "");
                String stageName = row.optString("stage_name", displayName);

                result.add(new StageDefinition(
                        row.getString("key"),
                        row.optString("category", "不明"),
                        row.optString("source_prefix", ""),
                        row.optInt("map_index", 0),
                        row.optInt("stage_index", 0),
                        mapName,
                        stageName,
                        displayName,
                        sourceFile,
                        row.optInt("width", 6000),
                        row.optLong("base_health", 100000),
                        row.optInt("min_production_frames", 0),
                        row.optInt("max_production_frames", 0),
                        row.optInt("background_id", 0),
                        row.optInt("max_enemy_count", 50),
                        row.optInt("castle_enemy_id", 0),
                        row.optInt("energy", -1),
                        row.optInt("clear_xp", -1),
                        row.optInt("main_music_id", -1),
                        row.optInt("boss_music_hp_percentage", -1),
                        row.optInt("boss_music_id", -1),
                        row.optInt("reward_type", -1),
                        row.optInt("star_count", 1),
                        starMultipliers,
                        row.optInt("difficulty_mask", 0),
                        rewards,
                        restrictions,
                        spawns
                ));
            }
        } catch (Exception ignored) {
            result.clear();
        }
        return result;
    }

    public static StageDefinition findStage(Context context, String key) {
        if (key == null) {
            return null;
        }
        for (StageDefinition stage : loadStages(context)) {
            if (key.equals(stage.key)) {
                return stage;
            }
        }
        return null;
    }

    private static JSONObject readRoot(Context context) throws Exception {
        File target = new File(context.getFilesDir(), FILE_NAME);
        if (!target.isFile()) {
            return new JSONObject().put("enemies", new JSONArray()).put("stages", new JSONArray());
        }
        byte[] bytes;
        try (FileInputStream in = new FileInputStream(target);
             ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[128 * 1024];
            int read;
            while ((read = in.read(buffer)) >= 0) {
                if (read > 0) {
                    out.write(buffer, 0, read);
                }
            }
            bytes = out.toByteArray();
        }
        return new JSONObject(new String(bytes, StandardCharsets.UTF_8));
    }
}