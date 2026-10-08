package jp.kneekura.whitenyankocats;

public final class StageRestriction {
    public final int starId;
    public final int rarityMask;
    public final int deployLimit;
    public final int slotLimit;
    public final int minDeployCost;
    public final int maxDeployCost;
    public final int groupId;

    public StageRestriction(
            int starId,
            int rarityMask,
            int deployLimit,
            int slotLimit,
            int minDeployCost,
            int maxDeployCost,
            int groupId
    ) {
        this.starId = starId;
        this.rarityMask = rarityMask;
        this.deployLimit = deployLimit;
        this.slotLimit = slotLimit;
        this.minDeployCost = minDeployCost;
        this.maxDeployCost = maxDeployCost;
        this.groupId = groupId;
    }
}