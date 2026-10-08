package jp.kneekura.whitenyankocats;

import java.util.List;

public final class GameImportResult {
    public final List<UnitRecord> units;
    public final List<EnemyRecord> enemies;
    public final List<StageDefinition> stages;

    public GameImportResult(
            List<UnitRecord> units,
            List<EnemyRecord> enemies,
            List<StageDefinition> stages
    ) {
        this.units = units;
        this.enemies = enemies;
        this.stages = stages;
    }
}