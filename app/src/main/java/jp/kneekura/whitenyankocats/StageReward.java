package jp.kneekura.whitenyankocats;

public final class StageReward {
    public final int probability;
    public final int itemId;
    public final int amount;
    public final boolean timedScore;

    public StageReward(int probability, int itemId, int amount, boolean timedScore) {
        this.probability = probability;
        this.itemId = itemId;
        this.amount = amount;
        this.timedScore = timedScore;
    }
}