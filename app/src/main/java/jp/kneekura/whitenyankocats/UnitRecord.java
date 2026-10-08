package jp.kneekura.whitenyankocats;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public final class UnitRecord {
    public final int unitNo;
    public final String name;
    public final List<String> firstFormStats;

    public UnitRecord(int unitNo, String name, List<String> firstFormStats) {
        this.unitNo = unitNo;
        this.name = name == null || name.trim().isEmpty() ? ("Unit " + unitNo) : name;
        this.firstFormStats = Collections.unmodifiableList(new ArrayList<>(firstFormStats));
    }

    public String stat(int index) {
        if (index < 0 || index >= firstFormStats.size()) {
            return "?";
        }
        String value = firstFormStats.get(index);
        return value == null || value.trim().isEmpty() ? "?" : value;
    }
}