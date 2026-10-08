package jp.kneekura.whitenyankocats;

public final class EnemyRecord {
    public final int enemyId;
    public final String name;
    public final long hp;
    public final int kbs;
    public final int speed;
    public final long attackDamage;
    public final int attackInterval;
    public final int range;
    public final int moneyDrop;
    public final int collisionStart;
    public final int collisionWidth;
    public final boolean areaAttack;
    public final int foreswing;

    public EnemyRecord(
            int enemyId,
            String name,
            long hp,
            int kbs,
            int speed,
            long attackDamage,
            int attackInterval,
            int range,
            int moneyDrop,
            int collisionStart,
            int collisionWidth,
            boolean areaAttack,
            int foreswing
    ) {
        this.enemyId = enemyId;
        this.name = name == null || name.trim().isEmpty() ? ("Enemy " + enemyId) : name;
        this.hp = hp;
        this.kbs = kbs;
        this.speed = speed;
        this.attackDamage = attackDamage;
        this.attackInterval = attackInterval;
        this.range = range;
        this.moneyDrop = moneyDrop;
        this.collisionStart = collisionStart;
        this.collisionWidth = collisionWidth;
        this.areaAttack = areaAttack;
        this.foreswing = foreswing;
    }
}