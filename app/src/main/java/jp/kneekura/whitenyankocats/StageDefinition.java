package jp.kneekura.whitenyankocats;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

public final class StageDefinition {
    public final String key;
    public final String category;
    public final String sourcePrefix;
    public final int mapIndex;
    public final int stageIndex;
    public final String mapName;
    public final String stageName;
    public final String name;
    public final String sourceFile;
    public final int width;
    public final long baseHealth;
    public final int minProductionFrames;
    public final int maxProductionFrames;
    public final int backgroundId;
    public final int maxEnemyCount;
    public final int castleEnemyId;

    public final int energy;
    public final int clearXp;
    public final int mainMusicId;
    public final int bossMusicHpPercentage;
    public final int bossMusicId;
    public final int rewardType;
    public final int starCount;
    public final int[] starMultipliers;
    public final int difficultyMask;

    public final List<StageReward> rewards;
    public final List<StageRestriction> restrictions;
    public final List<EnemySpawn> spawns;

    public StageDefinition(
            String key,
            String category,
            String sourcePrefix,
            int mapIndex,
            int stageIndex,
            String mapName,
            String stageName,
            String name,
            String sourceFile,
            int width,
            long baseHealth,
            int minProductionFrames,
            int maxProductionFrames,
            int backgroundId,
            int maxEnemyCount,
            int castleEnemyId,
            int energy,
            int clearXp,
            int mainMusicId,
            int bossMusicHpPercentage,
            int bossMusicId,
            int rewardType,
            int starCount,
            int[] starMultipliers,
            int difficultyMask,
            List<StageReward> rewards,
            List<StageRestriction> restrictions,
            List<EnemySpawn> spawns
    ) {
        this.key = key;
        this.category = category;
        this.sourcePrefix = sourcePrefix;
        this.mapIndex = mapIndex;
        this.stageIndex = stageIndex;
        this.mapName = mapName == null ? "" : mapName;
        this.stageName = stageName == null ? "" : stageName;
        this.name = name == null || name.trim().isEmpty() ? sourceFile : name;
        this.sourceFile = sourceFile;
        this.width = width;
        this.baseHealth = baseHealth;
        this.minProductionFrames = minProductionFrames;
        this.maxProductionFrames = maxProductionFrames;
        this.backgroundId = backgroundId;
        this.maxEnemyCount = maxEnemyCount;
        this.castleEnemyId = castleEnemyId;
        this.energy = energy;
        this.clearXp = clearXp;
        this.mainMusicId = mainMusicId;
        this.bossMusicHpPercentage = bossMusicHpPercentage;
        this.bossMusicId = bossMusicId;
        this.rewardType = rewardType;
        this.starCount = starCount;
        this.starMultipliers = starMultipliers == null
                ? new int[]{100, 100, 100, 100}
                : Arrays.copyOf(starMultipliers, 4);
        this.difficultyMask = difficultyMask;
        this.rewards = Collections.unmodifiableList(new ArrayList<>(rewards));
        this.restrictions = Collections.unmodifiableList(new ArrayList<>(restrictions));
        this.spawns = Collections.unmodifiableList(new ArrayList<>(spawns));
    }

    public String label() {
        return category + "  " + name;
    }
}