package jp.kneekura.whitenyankocats;

public final class EnemySpawn {
    public final int enemyReleaseId;
    public final int maxEnemyCount;
    public final int startFrame;
    public final int minSpawnInterval;
    public final int maxSpawnInterval;
    public final int spawnBasePercent;
    public final int minZ;
    public final int maxZ;
    public final boolean boss;
    public final int magnification;

    public EnemySpawn(
            int enemyReleaseId,
            int maxEnemyCount,
            int startFrame,
            int minSpawnInterval,
            int maxSpawnInterval,
            int spawnBasePercent,
            int minZ,
            int maxZ,
            boolean boss,
            int magnification
    ) {
        this.enemyReleaseId = enemyReleaseId;
        this.maxEnemyCount = maxEnemyCount;
        this.startFrame = startFrame;
        this.minSpawnInterval = minSpawnInterval;
        this.maxSpawnInterval = maxSpawnInterval;
        this.spawnBasePercent = spawnBasePercent;
        this.minZ = minZ;
        this.maxZ = maxZ;
        this.boss = boss;
        this.magnification = magnification;
    }
}