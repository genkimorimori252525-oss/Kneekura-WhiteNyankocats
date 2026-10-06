package jp.kneekura.whitenyankocats;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public final class StageDefinition {
    public final String key;
    public final String category;
    public final String sourcePrefix;
    public final int mapIndex;
    public final int stageIndex;
    public final String name;
    public final String sourceFile;
    public final int width;
    public final long baseHealth;
    public final int minProductionFrames;
    public final int maxProductionFrames;
    public final int backgroundId;
    public final int maxEnemyCount;
    public final int castleEnemyId;
    public final List<EnemySpawn> spawns;

    public StageDefinition(
            String key,
            String category,
            String sourcePrefix,
            int mapIndex,
            int stageIndex,
            String name,
            String sourceFile,
            int width,
            long baseHealth,
            int minProductionFrames,
            int maxProductionFrames,
            int backgroundId,
            int maxEnemyCount,
            int castleEnemyId,
            List<EnemySpawn> spawns
    ) {
        this.key = key;
        this.category = category;
        this.sourcePrefix = sourcePrefix;
        this.mapIndex = mapIndex;
        this.stageIndex = stageIndex;
        this.name = name == null || name.trim().isEmpty() ? sourceFile : name;
        this.sourceFile = sourceFile;
        this.width = width;
        this.baseHealth = baseHealth;
        this.minProductionFrames = minProductionFrames;
        this.maxProductionFrames = maxProductionFrames;
        this.backgroundId = backgroundId;
        this.maxEnemyCount = maxEnemyCount;
        this.castleEnemyId = castleEnemyId;
        this.spawns = Collections.unmodifiableList(new ArrayList<>(spawns));
    }

    public String label() {
        return category + "  " + name;
    }
}