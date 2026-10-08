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

public final class CatalogStore {
    private static final String FILE_NAME = "unit-catalog.json";

    private CatalogStore() {
    }

    public static void save(Context context, List<UnitRecord> units) throws Exception {
        JSONArray rows = new JSONArray();
        for (UnitRecord unit : units) {
            JSONObject item = new JSONObject();
            item.put("unit_no", unit.unitNo);
            item.put("name", unit.name);
            JSONArray stats = new JSONArray();
            for (String value : unit.firstFormStats) {
                stats.put(value);
            }
            item.put("first_form_stats", stats);
            rows.put(item);
        }

        JSONObject root = new JSONObject();
        root.put("schema_version", 1);
        root.put("source", "user-selected-battle-cats-export");
        root.put("default_form", 0);
        root.put("all_units_unlocked", true);
        root.put("units", rows);

        File target = new File(context.getFilesDir(), FILE_NAME);
        try (FileOutputStream out = new FileOutputStream(target)) {
            out.write(root.toString(2).getBytes(StandardCharsets.UTF_8));
        }
    }

    public static List<UnitRecord> load(Context context) {
        List<UnitRecord> units = new ArrayList<>();
        try {
            File target = new File(context.getFilesDir(), FILE_NAME);
            if (!target.isFile()) {
                return units;
            }
            String text;
            try (FileInputStream in = new FileInputStream(target);
                 ByteArrayOutputStream out = new ByteArrayOutputStream()) {
                byte[] buffer = new byte[64 * 1024];
                int read;
                while ((read = in.read(buffer)) >= 0) {
                    if (read > 0) {
                        out.write(buffer, 0, read);
                    }
                }
                text = new String(out.toByteArray(), StandardCharsets.UTF_8);
            }

            JSONObject root = new JSONObject(text);
            JSONArray rows = root.getJSONArray("units");
            for (int i = 0; i < rows.length(); i++) {
                JSONObject item = rows.getJSONObject(i);
                JSONArray statsJson = item.getJSONArray("first_form_stats");
                List<String> stats = new ArrayList<>();
                for (int j = 0; j < statsJson.length(); j++) {
                    stats.add(statsJson.optString(j, ""));
                }
                int unitNo = item.getInt("unit_no");
                units.add(new UnitRecord(
                        unitNo,
                        item.optString("name", "Unit " + unitNo),
                        stats
                ));
            }
        } catch (Exception ignored) {
            units.clear();
        }
        return units;
    }
}