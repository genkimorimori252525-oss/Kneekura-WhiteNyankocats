package jp.kneekura.whitenyankocats;

import android.content.Context;
import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.LocalTime;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * Read-only local notice feed from the independently imported, signed
 * Kneekura operator content. Never accesses the original Battle Cats save,
 * opens URLs, polls a server, claims rewards or changes game progress.
 *
 * The saved operator revision is already verified by LocalOpsStore. Notices
 * with missing assets, missing schedule, invalid timestamps or future
 * publication dates are not published into the displayed feed.
 */
final class LocalNoticeRepository {
    private static final ZoneId JST = ZoneId.of("Asia/Tokyo");
    private static final DateTimeFormatter DISPLAY_DAY =
            DateTimeFormatter.ofPattern("yyyy/MM/dd", Locale.JAPAN);
    private static final int MAX_NOTICES = 80;
    private static final int MAX_BODY_CHARS = 12000;

    static final class Notice {
        final String id;
        final String category;
        final String title;
        final String date;
        final String body;
        final boolean pinned;
        final ZonedDateTime publishedAt;
        final int priority;

        Notice(String id, String category, String title, String date,
               String body, boolean pinned, ZonedDateTime publishedAt, int priority) {
            this.id = id;
            this.category = category;
            this.title = title;
            this.date = date;
            this.body = body;
            this.pinned = pinned;
            this.publishedAt = publishedAt;
            this.priority = priority;
        }
    }

    private LocalNoticeRepository() {}

    static List<Notice> current(Context context) throws Exception {
        JSONObject pack = LocalOpsStore.loadCurrentPack(context);
        if (pack == null) return bundled(context, ZonedDateTime.now(JST));
        return fromPack(pack, ZonedDateTime.now(JST));
    }

    /** APK-bundled welcome news is available even before any external pack. */
    static List<Notice> bundled(Context context, ZonedDateTime now) throws Exception {
        ByteArrayOutputStream sink = new ByteArrayOutputStream();
        try (InputStream input = context.getAssets().open("kneekura-notices-bootstrap.json")) {
            byte[] buffer = new byte[8192];
            int n;
            while ((n = input.read(buffer)) != -1) {
                if (sink.size() + n > 64 * 1024) {
                    throw new IllegalArgumentException("Bundled notice feed is too large");
                }
                sink.write(buffer, 0, n);
            }
        }
        JSONObject document = new JSONObject(
                new String(sink.toByteArray(), StandardCharsets.UTF_8));
        if (document.getInt("schema_version") != 1 ||
                !"kneekura-bundled-local".equals(document.getString("source"))) {
            throw new IllegalArgumentException("Not a Kneekura bundled notice file");
        }
        JSONArray items = document.getJSONArray("notices");
        if (items.length() > MAX_NOTICES) {
            throw new IllegalArgumentException("Too many bundled notices");
        }
        ZonedDateTime jstNow = now.withZoneSameInstant(JST);
        List<Notice> list = new ArrayList<>();
        for (int i = 0; i < items.length(); i++) {
            JSONObject item = items.getJSONObject(i);
            String id = item.getString("id");
            String category = item.getString("category");
            String title = item.getString("title");
            String body = item.getString("body");
            ZonedDateTime publication = parseDate(item.getString("published_at"));
            ZonedDateTime expiry = parseDate(item.getString("expires_at"));
            if (!id.startsWith("kneekura:notice:") || !validCategory(category) ||
                    title.isEmpty() || title.length() > 140 ||
                    body.isEmpty() || body.length() > MAX_BODY_CHARS ||
                    containsRemoteMarkup(body) || containsRemoteMarkup(title) ||
                    jstNow.isBefore(publication) || !jstNow.isBefore(expiry)) {
                continue;
            }
            list.add(new Notice(id, category, title,
                    publication.format(DISPLAY_DAY), body,
                    item.optBoolean("pinned", false), publication, 0));
        }
        list.sort(Comparator.comparing((Notice n) -> !n.pinned)
                .thenComparing((Notice n) -> n.publishedAt, Comparator.reverseOrder())
                .thenComparing(n -> n.id));
        return list;
    }

    /** Pure evaluator; now can be supplied by future unit/device tests. */
    static List<Notice> fromPack(JSONObject pack, ZonedDateTime now) throws Exception {
        List<Notice> result = new ArrayList<>();
        if (!"published".equals(pack.optString("status", "")) ||
                !"kneekura-main-offline".equals(pack.optString("channel", ""))) {
            return result;
        }
        JSONObject catalog = pack.optJSONObject("catalog");
        JSONArray schedule = pack.optJSONArray("schedule");
        if (catalog == null || schedule == null || schedule.length() > 2000) {
            return result;
        }
        JSONArray notices = catalog.optJSONArray("notice");
        if (notices == null || notices.length() > 400) return result;

        Map<String, JSONObject> byId = new HashMap<>();
        for (int i = 0; i < notices.length(); i++) {
            JSONObject notice = notices.optJSONObject(i);
            if (notice == null || !notice.optBoolean("ready", false)) continue;
            String id = notice.optString("id", "");
            if (id.startsWith("kneekura:notice:") && !byId.containsKey(id)) {
                byId.put(id, notice);
            }
        }

        ZonedDateTime localNow = now.withZoneSameInstant(JST);
        // Duplicate notices on multiple valid schedule slots are collapsed.
        Map<String, Notice> visibleById = new HashMap<>();
        for (int i = 0; i < schedule.length(); i++) {
            JSONObject entry = schedule.optJSONObject(i);
            if (entry == null || !"notice".equals(entry.optString("kind"))) continue;
            String contentId = entry.optString("content_id", "");
            JSONObject content = byId.get(contentId);
            if (content == null || entry.optJSONObject("rule") == null) continue;
            if (entry.has("requires") && entry.optJSONObject("requires") != null &&
                    entry.optJSONObject("requires").length() != 0) continue;
            try {
                if (!isActive(entry.getJSONObject("rule"), localNow)) continue;
                String title = content.getString("title").trim();
                String body = content.optString("body",
                        content.optString("message", "")).trim();
                if (title.isEmpty() || title.length() > 140 ||
                        body.isEmpty() || body.length() > MAX_BODY_CHARS) continue;
                // Never render remote HTML/images/links. Illustrations may be
                // added later from whitelisted local drawable resources only.
                if (containsRemoteMarkup(title) || containsRemoteMarkup(body)) continue;
                String category = content.optString("category", "お知らせ").trim();
                if (!validCategory(category)) category = "お知らせ";
                ZonedDateTime published = parseDate(content.optString(
                        "published_at", pack.getJSONObject("season").getString("start")));
                if (published.isAfter(localNow)) continue;
                Notice value = new Notice(contentId, category, title,
                        published.format(DISPLAY_DAY), body,
                        content.optBoolean("pinned", false), published,
                        entry.optInt("priority", 0));
                Notice existing = visibleById.get(contentId);
                if (existing == null || existing.priority < value.priority) {
                    visibleById.put(contentId, value);
                }
            } catch (Exception ignored) {
                // Malformed, unrecognized or incompatible notice data never
                // triggers an Internet lookup or crashes the entire UI.
            }
        }
        result.addAll(visibleById.values());
        result.sort(Comparator.comparing((Notice n) -> !n.pinned)
                .thenComparing((Notice n) -> n.publishedAt, Comparator.reverseOrder())
                .thenComparing((Notice n) -> n.priority, Comparator.reverseOrder())
                .thenComparing(n -> n.id));
        if (result.size() > MAX_NOTICES) {
            return new ArrayList<>(result.subList(0, MAX_NOTICES));
        }
        return result;
    }

    private static boolean validCategory(String value) {
        return "更新情報".equals(value) || "イベント".equals(value) ||
                "ガチャ".equals(value) || "重要".equals(value) ||
                "運営情報".equals(value) || "お知らせ".equals(value) ||
                "不具合".equals(value);
    }

    private static boolean containsRemoteMarkup(String value) {
        String check = value.toLowerCase(Locale.ROOT);
        return check.contains("https://") || check.contains("http://") ||
                check.contains("javascript:") || check.contains("<script") ||
                check.contains("file://") || check.contains("content://");
    }

    private static ZonedDateTime parseDate(String raw) {
        return OffsetDateTime.parse(raw).atZoneSameInstant(JST);
    }

    private static boolean isActive(JSONObject rule, ZonedDateTime now) throws Exception {
        String mode = rule.getString("mode");
        if ("once".equals(mode)) {
            ZonedDateTime begin = parseDate(rule.getString("start"));
            ZonedDateTime end = parseDate(rule.getString("end"));
            return !now.isBefore(begin) && now.isBefore(end);
        }
        if (!("daily".equals(mode) || "weekly".equals(mode) ||
                "monthly".equals(mode))) return false;

        LocalDate first = LocalDate.parse(rule.getString("valid_from"));
        LocalDate until = LocalDate.parse(rule.getString("valid_until"));
        LocalTime open = LocalTime.parse(rule.getString("from_time"));
        LocalTime close = LocalTime.parse(rule.getString("to_time"));

        // Include yesterday for overnight windows (22:00–02:00).
        for (int offset = 0; offset <= 1; offset++) {
            LocalDate day = now.toLocalDate().minusDays(offset);
            if (day.isBefore(first) || !day.isBefore(until)) continue;
            if ("weekly".equals(mode) &&
                    !includes(rule.getJSONArray("weekdays"), day.getDayOfWeek().getValue() - 1)) {
                continue;
            }
            if ("monthly".equals(mode) &&
                    !includes(rule.getJSONArray("monthdays"), day.getDayOfMonth())) {
                continue;
            }
            ZonedDateTime begin = day.atTime(open).atZone(JST);
            ZonedDateTime end = day.atTime(close).atZone(JST);
            if (!end.isAfter(begin)) end = end.plusDays(1);
            if (!now.isBefore(begin) && now.isBefore(end)) return true;
        }
        return false;
    }

    private static boolean includes(JSONArray array, int expected) {
        for (int i = 0; i < array.length(); i++) {
            if (array.optInt(i, -1) == expected) return true;
        }
        return false;
    }
}
