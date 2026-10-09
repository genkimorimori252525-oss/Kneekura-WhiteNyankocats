package jp.kneekura.whitenyankocats;

import android.content.Context;
import android.util.AtomicFile;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.HashSet;
import java.util.Set;

/**
 * Independent story checkpoint storage, not the PONOS JP SAVE_DATA format.
 *
 * A new independent player starts after EoC Chapters 1–3 and ItF Chapter 1:
 * each has 48 cleared stages and all 48 Superior treasures (rank 3).
 *
 * For already-installed independent Alphas this is a one-time, ADDITIVE
 * migration. It never deletes current units/resources, stage clears,
 * unearned reward ledgers, or progress for future chapters, Cosmos or SoL.
 * An invalid preexisting local story file is NOT silently overwritten.
 *
 * This is a checkpoint sidecar. The alpha's battle/stage UI must be explicitly
 * linked to the story ledger later; writing an independent checkpoint alone
 * does not prove the final original-style story selection UI is functional.
 */
public final class StoryProgressStore {
    private static final String FILE = "kneekura-story-progress-v1.json";
    private static final String POLICY_ASSET = "kneekura-story-bootstrap-v2.json";
    private static final String SCHEMA = "KNEEKURA_STORY_LOCAL_V1";
    private static final int POLICY_VERSION = 2;
    private static final int COMPLETE_STAGES = 48;
    private static final int SUPERIOR = 3;
    private static final String[] CHAPTERS = {"eoc1", "eoc2", "eoc3", "itf1"};
    private static final int[] JP_INDICES = {0, 1, 2, 4};

    public static final class Summary {
        public final int completeChapters;
        public final int superiorTreasures;
        public final int version;
        Summary(int chapters, int treasure, int version) {
            this.completeChapters = chapters;
            this.superiorTreasures = treasure;
            this.version = version;
        }
    }

    private StoryProgressStore() {}

    private static JSONObject loadApprovedPolicy(Context context) throws Exception {
        ByteArrayOutputStream data = new ByteArrayOutputStream();
        try (InputStream input = context.getAssets().open(POLICY_ASSET)) {
            byte[] buffer = new byte[4096];
            int read;
            while ((read = input.read(buffer)) != -1) {
                if (data.size() + read > 32 * 1024) {
                    throw new IllegalStateException("Story bootstrap policy exceeded 32KB");
                }
                data.write(buffer, 0, read);
            }
        }
        JSONObject spec = new JSONObject(
                new String(data.toByteArray(), StandardCharsets.UTF_8));
        if (spec.getInt("schema_version") != 2 ||
                !"kneekura:story:post-itf1-superior".equals(spec.getString("bootstrap_id")) ||
                !"kneekura-independent-local-only".equals(spec.getString("authority")) ||
                spec.getInt("stage_count_per_complete_chapter") != COMPLETE_STAGES ||
                spec.getInt("superior_treasure_rank") != SUPERIOR) {
            throw new IllegalStateException("Unknown local story bootstrap specification");
        }
        JSONObject safety = spec.getJSONObject("safety");
        for (String name : new String[] {
                "modifies_original_ponos_save", "affects_stage_rewards",
                "affects_gacha_ownership", "erases_existing_progress",
                "changes_treasure_on_other_chapters", "affects_stage_availability"
        }) {
            if (safety.getBoolean(name)) {
                throw new IllegalStateException("Unsafe story policy: " + name);
            }
        }
        JSONArray rows = spec.getJSONArray("chapters");
        if (rows.length() != CHAPTERS.length) {
            throw new IllegalStateException("Unexpected number of completed chapters");
        }
        for (int i = 0; i < rows.length(); i++) {
            JSONObject chapter = rows.getJSONObject(i);
            if (!CHAPTERS[i].equals(chapter.getString("id")) ||
                    chapter.getInt("original_jp_chapter_index") != JP_INDICES[i] ||
                    chapter.getInt("progress") != COMPLETE_STAGES ||
                    chapter.getInt("stage_clear_count_min") != 1 ||
                    chapter.getInt("treasure_rank_min") != SUPERIOR) {
                throw new IllegalStateException("Unapproved chapter bootstrap field");
            }
        }
        return spec;
    }

    private static int checkedCount(JSONArray values, int index, int max) throws Exception {
        if (index >= values.length()) return 0;
        Object value = values.get(index);
        if (!(value instanceof Integer || value instanceof Long) ||
                ((Number) value).longValue() < 0 ||
                ((Number) value).longValue() > max) {
            throw new IllegalStateException("Invalid existing story counter or treasure rank");
        }
        return ((Number) value).intValue();
    }

    private static boolean mergeChapter(JSONObject chapters, String name) throws Exception {
        if (chapters.has(name) && !(chapters.get(name) instanceof JSONObject)) {
            throw new IllegalStateException("Corrupt local story chapter: " + name);
        }
        JSONObject record = chapters.optJSONObject(name);
        boolean changed = record == null;
        if (record == null) record = new JSONObject();

        int progress = record.optInt("progress", 0);
        if (progress < 0 || progress > COMPLETE_STAGES) {
            throw new IllegalStateException("Invalid preexisting chapter progress: " + name);
        }
        if (progress < COMPLETE_STAGES) {
            record.put("progress", COMPLETE_STAGES);
            changed = true;
        }
        JSONArray clears = record.optJSONArray("clear_counts");
        JSONArray treasures = record.optJSONArray("treasure_ranks");
        if (record.has("clear_counts") && clears == null ||
                record.has("treasure_ranks") && treasures == null ||
                clears != null && clears.length() > COMPLETE_STAGES ||
                treasures != null && treasures.length() > COMPLETE_STAGES) {
            throw new IllegalStateException("Invalid original independent chapter array: " + name);
        }
        if (clears == null) clears = new JSONArray();
        if (treasures == null) treasures = new JSONArray();
        for (int i = 0; i < COMPLETE_STAGES; i++) {
            int priorClears = checkedCount(clears, i, Integer.MAX_VALUE);
            int priorRank = checkedCount(treasures, i, SUPERIOR);
            if (priorClears < 1) {
                clears.put(i, 1);
                changed = true;
            }
            if (priorRank < SUPERIOR) {
                treasures.put(i, SUPERIOR);
                changed = true;
            }
        }
        record.put("clear_counts", clears);
        record.put("treasure_ranks", treasures);
        chapters.put(name, record);
        return changed;
    }

    private static JSONObject readOrCreate(AtomicFile store) throws Exception {
        File target = store.getBaseFile();
        File prior = new File(target.getAbsolutePath() + ".bak");
        if (!target.exists() && !prior.exists()) {
            JSONObject initial = new JSONObject();
            initial.put("schema", SCHEMA);
            initial.put("policy_revision", 0);
            initial.put("chapters", new JSONObject());
            return initial;
        }
        byte[] raw = store.readFully();
        if (raw.length == 0 || raw.length > 512 * 1024) {
            throw new IllegalStateException("Local story sidecar is empty or oversized");
        }
        JSONObject existing = new JSONObject(new String(raw, StandardCharsets.UTF_8));
        if (!SCHEMA.equals(existing.getString("schema")) ||
                existing.optJSONObject("chapters") == null ||
                existing.getInt("policy_revision") < 0) {
            throw new IllegalStateException("Unknown or damaged local story state");
        }
        return existing;
    }

    private static Summary summary(JSONObject root) throws Exception {
        JSONObject chapters = root.getJSONObject("chapters");
        int completed = 0;
        int best = 0;
        for (String id : CHAPTERS) {
            JSONObject chapter = chapters.optJSONObject(id);
            if (chapter == null) continue;
            JSONArray clears = chapter.getJSONArray("clear_counts");
            JSONArray treasures = chapter.getJSONArray("treasure_ranks");
            boolean allCleared = chapter.getInt("progress") == COMPLETE_STAGES;
            for (int i = 0; i < COMPLETE_STAGES; i++) {
                allCleared &= checkedCount(clears, i, Integer.MAX_VALUE) >= 1;
                if (checkedCount(treasures, i, SUPERIOR) == SUPERIOR) best++;
            }
            if (allCleared) completed++;
        }
        return new Summary(completed, best, root.getInt("policy_revision"));
    }

    /**
     * New install: create local independent checkpoint.
     * Older install: one-time minimum-only merge into EoC1-3 + ItF1.
     * Second or later launch: no write, no forced reset of earned progress.
     */
    public static synchronized Summary ensureInitialCheckpoint(Context context) throws Exception {
        loadApprovedPolicy(context); // validates APK content *before* any local write
        AtomicFile store = new AtomicFile(new File(context.getFilesDir(), FILE));
        JSONObject root = readOrCreate(store);
        int revision = root.getInt("policy_revision");
        if (revision >= POLICY_VERSION) return summary(root);
        JSONObject chapters = root.getJSONObject("chapters");
        for (String id : CHAPTERS) mergeChapter(chapters, id);
        root.put("policy_revision", POLICY_VERSION);
        byte[] serialized = root.toString().getBytes(StandardCharsets.UTF_8);
        FileOutputStream output = null;
        try {
            output = store.startWrite();
            output.write(serialized);
            store.finishWrite(output);
        } catch (Exception error) {
            if (output != null) store.failWrite(output);
            throw error;
        }
        return summary(root);
    }
}
