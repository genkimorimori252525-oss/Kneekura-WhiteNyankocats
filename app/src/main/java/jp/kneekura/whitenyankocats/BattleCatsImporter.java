package jp.kneekura.whitenyankocats;

import android.content.Context;
import android.net.Uri;

import java.io.BufferedInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
import java.util.zip.ZipInputStream;

import javax.crypto.Cipher;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;

public final class BattleCatsImporter {
    private static final byte[] JP_KEY = hex("d754868de89d717fa9e7b06da45ae9e3");
    private static final byte[] JP_IV = hex("40b2131a9f388ad4e5002a98118f6128");

    private static final Pattern EOC_STAGE = Pattern.compile("^stage(\\d{2})\\.csv$", Pattern.CASE_INSENSITIVE);
    private static final Pattern ITF_STAGE = Pattern.compile("^stageW(\\d{2})_(\\d{2})\\.csv$", Pattern.CASE_INSENSITIVE);
    private static final Pattern COTC_STAGE = Pattern.compile("^stageSpace(\\d{2})_(\\d{2})\\.csv$", Pattern.CASE_INSENSITIVE);
    private static final Pattern GENERIC_STAGE = Pattern.compile("^stage([A-Za-z]+)(\\d{3})_(\\d{2})\\.csv$", Pattern.CASE_INSENSITIVE);

    private BattleCatsImporter() {
    }

    public static List<UnitRecord> importFromUri(Context context, Uri uri) throws Exception {
        return importGameFromUri(context, uri).units;
    }

    public static GameImportResult importGameFromUri(Context context, Uri uri) throws Exception {
        File installApk = new File(
                context.getCacheDir(),
                "kneekura-installpack-" + System.nanoTime() + ".apk"
        );
        try {
            extractInstallPack(context, uri, installApk);
            try (ZipFile install = new ZipFile(installApk)) {
                Pack data = new Pack(
                        readZipEntry(install, "assets/DataLocal.list"),
                        readZipEntry(install, "assets/DataLocal.pack")
                );
                Pack res = new Pack(
                        readZipEntry(install, "assets/resLocal.list"),
                        readZipEntry(install, "assets/resLocal.pack")
                );
                Pack map = new Pack(
                        readZipEntry(install, "assets/MapLocal.list"),
                        readZipEntry(install, "assets/MapLocal.pack")
                );

                return new GameImportResult(
                        importUnits(data, res),
                        importEnemies(data, res, map),
                        importStages(data, res, map)
                );
            }
        } finally {
            if (installApk.exists()) {
                installApk.delete();
            }
        }
    }

    private static List<UnitRecord> importUnits(Pack data, Pack res) throws Exception {
        TreeSet<Integer> ids = new TreeSet<>();
        for (String name : data.names()) {
            String lower = name.toLowerCase(Locale.ROOT);
            if (lower.startsWith("unit") && lower.endsWith(".csv")) {
                String number = lower.substring(4, lower.length() - 4);
                try {
                    ids.add(Integer.parseInt(number));
                } catch (NumberFormatException ignored) {
                }
            }
        }
        if (ids.isEmpty()) {
            throw new IllegalArgumentException("DataLocal に unitNNN.csv が見つかりません");
        }

        List<UnitRecord> units = new ArrayList<>();
        for (int id : ids) {
            String statsName = String.format(Locale.ROOT, "unit%03d.csv", id);
            String explanationName = "Unit_Explanation" + id + "_ja.csv";
            units.add(new UnitRecord(
                    id,
                    firstCsvField(res.read(explanationName)),
                    firstStatRow(data.read(statsName))
            ));
        }
        return units;
    }

    private static List<EnemyRecord> importEnemies(Pack data, Pack res, Pack map) throws Exception {
        Pack owner = findOwner("t_unit.csv", data, res, map);
        if (owner == null) {
            return Collections.emptyList();
        }
        List<List<String>> statRows = csvRows(owner.read("t_unit.csv"), ",", true);

        List<List<String>> nameRows = Collections.emptyList();
        Pack nameOwner = findOwner("Enemyname.tsv", data, res, map);
        if (nameOwner != null) {
            nameRows = csvRows(nameOwner.read("Enemyname.tsv"), "\t", false);
        }

        List<EnemyRecord> enemies = new ArrayList<>();
        for (int rowIndex = 2; rowIndex < statRows.size(); rowIndex++) {
            List<String> row = statRows.get(rowIndex);
            if (row.isEmpty()) {
                continue;
            }
            int enemyId = rowIndex - 2;
            String name = enemyId < nameRows.size() && !nameRows.get(enemyId).isEmpty()
                    ? nameRows.get(enemyId).get(0)
                    : "Enemy " + enemyId;
            enemies.add(new EnemyRecord(
                    enemyId,
                    name,
                    longAt(row, 0, 1),
                    intAt(row, 1, 1),
                    intAt(row, 2, 1),
                    longAt(row, 3, 1),
                    intAt(row, 4, 30),
                    intAt(row, 5, 100),
                    intAt(row, 6, 0),
                    intAt(row, 7, 0),
                    intAt(row, 8, 0),
                    intAt(row, 11, 0) != 0,
                    intAt(row, 12, 1)
            ));
        }
        return enemies;
    }

    private static List<StageDefinition> importStages(Pack data, Pack res, Pack map) throws Exception {
        List<StageDefinition> stages = new ArrayList<>();

        for (String fileName : map.names()) {
            StageAddress address = parseStageAddress(fileName);
            if (address == null) {
                continue;
            }

            List<List<String>> rows = csvRows(map.read(fileName), ",", true);
            if (rows.isEmpty()) {
                continue;
            }

            int infoRow = rows.get(0).size() < 7 ? 1 : 0;
            if (infoRow >= rows.size()) {
                continue;
            }
            List<String> info = rows.get(infoRow);
            if (info.size() < 6) {
                continue;
            }

            List<EnemySpawn> spawns = new ArrayList<>();
            for (int i = infoRow + 1; i < rows.size(); i++) {
                List<String> row = rows.get(i);
                int enemyReleaseId = intAt(row, 0, -1);
                if (enemyReleaseId < 0) {
                    continue;
                }
                spawns.add(new EnemySpawn(
                        enemyReleaseId,
                        intAt(row, 1, 1),
                        intAt(row, 2, 0),
                        intAt(row, 3, 0),
                        intAt(row, 4, 0),
                        intAt(row, 5, 100),
                        intAt(row, 6, 0),
                        intAt(row, 7, 0),
                        intAt(row, 8, 0) != 0,
                        intAt(row, 9, 100)
                ));
            }

            String stageName = resolveStageName(address, data, res, map);
            String key = address.kindKey + ":" + address.mapIndex + ":" + address.stageIndex;
            stages.add(new StageDefinition(
                    key,
                    address.category,
                    address.sourcePrefix,
                    address.mapIndex,
                    address.stageIndex,
                    stageName,
                    fileName,
                    intAt(info, 0, 6000),
                    longAt(info, 1, 100000),
                    intAt(info, 2, 0),
                    intAt(info, 3, 0),
                    intAt(info, 4, 0),
                    intAt(info, 5, 50),
                    intAt(info, 6, 0),
                    spawns
            ));
        }

        stages.sort(Comparator
                .comparing((StageDefinition stage) -> stage.category)
                .thenComparingInt(stage -> stage.mapIndex)
                .thenComparingInt(stage -> stage.stageIndex)
                .thenComparing(stage -> stage.sourceFile));
        return stages;
    }

    private static StageAddress parseStageAddress(String fileName) {
        Matcher eoc = EOC_STAGE.matcher(fileName);
        if (eoc.matches()) {
            return new StageAddress("eoc", "日本編", "", 0,
                    Integer.parseInt(eoc.group(1)), "StageName0_ja.csv");
        }

        Matcher itf = ITF_STAGE.matcher(fileName);
        if (itf.matches()) {
            return new StageAddress("itf", "未来編", "W",
                    Math.max(0, Integer.parseInt(itf.group(1)) - 4),
                    Integer.parseInt(itf.group(2)), "StageName1_ja.csv");
        }

        Matcher cotc = COTC_STAGE.matcher(fileName);
        if (cotc.matches()) {
            return new StageAddress("cotc", "宇宙編", "Space",
                    Math.max(0, Integer.parseInt(cotc.group(1)) - 7),
                    Integer.parseInt(cotc.group(2)), "StageName2_ja.csv");
        }

        Matcher generic = GENERIC_STAGE.matcher(fileName);
        if (!generic.matches()) {
            return null;
        }

        String prefix = generic.group(1).toUpperCase(Locale.ROOT);
        int mapIndex = Integer.parseInt(generic.group(2));
        int stageIndex = Integer.parseInt(generic.group(3));
        String stageNameCode = prefix.equals("EX") ? "RE" : prefix;
        String stageNameFile = stageNameCode.equals("Z")
                ? null
                : "StageName_" + stageNameCode + "_ja.csv";

        return new StageAddress(
                "prefix_" + prefix.toLowerCase(Locale.ROOT),
                categoryForPrefix(prefix),
                prefix,
                mapIndex,
                stageIndex,
                stageNameFile
        );
    }

    private static String categoryForPrefix(String prefix) {
        switch (prefix) {
            case "RN":
                return "レジェンドストーリー";
            case "RNA":
                return "真レジェンドステージ";
            case "RND":
                return "レジェンドストーリー0";
            case "RS":
                return "イベントステージ";
            case "RC":
                return "コラボステージ";
            case "RCA":
                return "コラボ強襲";
            case "EX":
                return "EXステージ";
            case "RA":
                return "強襲ステージ";
            case "RB":
                return "ネコビタンステージ";
            case "RH":
                return "発掘ステージ";
            case "RM":
                return "チャレンジバトル";
            case "RQ":
                return "超獣研究ステージ";
            case "RR":
                return "ネコ道場ランキング";
            case "RT":
                return "にゃんこ道場";
            case "RV":
                return "にゃんこ塔";
            case "DM":
                return "魔界編";
            case "L":
                return "地底迷宮";
            case "Z":
                return "ゾンビ襲来";
            default:
                return "その他(" + prefix + ")";
        }
    }

    private static String resolveStageName(
            StageAddress address,
            Pack data,
            Pack res,
            Pack map
    ) throws Exception {
        if (address.stageNameFile == null) {
            return address.fallbackName();
        }
        Pack owner = findOwner(address.stageNameFile, res, data, map);
        if (owner == null) {
            return address.fallbackName();
        }

        List<List<String>> rows = csvRows(owner.read(address.stageNameFile), ",", false);
        if (address.kindKey.equals("eoc")
                || address.kindKey.equals("itf")
                || address.kindKey.equals("cotc")) {
            int rowIndex = convertMainStoryStageId(address.stageIndex);
            if (rowIndex >= 0 && rowIndex < rows.size() && !rows.get(rowIndex).isEmpty()) {
                String value = cleanName(rows.get(rowIndex).get(0));
                if (!value.isEmpty()) {
                    return value;
                }
            }
            return address.fallbackName();
        }

        if (address.mapIndex < rows.size()) {
            List<String> row = rows.get(address.mapIndex);
            if (address.stageIndex < row.size()) {
                String value = cleanName(row.get(address.stageIndex));
                if (!value.isEmpty() && !value.equals("＠")) {
                    return value;
                }
            }
        }
        return address.fallbackName();
    }

    private static int convertMainStoryStageId(int id) {
        if (id == 46 || id == 47) {
            return id;
        }
        return 45 - id;
    }

    private static String cleanName(String value) {
        return value == null ? "" : value.replace("\uFEFF", "").trim();
    }

    private static Pack findOwner(String name, Pack... packs) {
        for (Pack pack : packs) {
            if (pack != null && pack.has(name)) {
                return pack;
            }
        }
        return null;
    }

    private static List<List<String>> csvRows(
            byte[] payload,
            String delimiter,
            boolean stripComments
    ) {
        String text = new String(payload, StandardCharsets.UTF_8).replace("\uFEFF", "");
        List<List<String>> result = new ArrayList<>();
        for (String rawLine : text.split("\\R", -1)) {
            String line = rawLine;
            if (stripComments) {
                int comment = line.indexOf("//");
                if (comment >= 0) {
                    line = line.substring(0, comment);
                }
            }
            if (line.trim().isEmpty()) {
                continue;
            }
            String[] columns = line.split(delimiter, -1);
            List<String> row = new ArrayList<>(columns.length);
            for (String column : columns) {
                row.add(column.trim());
            }
            while (!row.isEmpty() && row.get(row.size() - 1).isEmpty()) {
                row.remove(row.size() - 1);
            }
            result.add(row);
        }
        return result;
    }

    private static int intAt(List<String> row, int index, int fallback) {
        if (index < 0 || index >= row.size()) {
            return fallback;
        }
        try {
            return Integer.parseInt(row.get(index).trim());
        } catch (NumberFormatException ignored) {
            return fallback;
        }
    }

    private static long longAt(List<String> row, int index, long fallback) {
        if (index < 0 || index >= row.size()) {
            return fallback;
        }
        try {
            return Long.parseLong(row.get(index).trim());
        } catch (NumberFormatException ignored) {
            return fallback;
        }
    }

    private static void extractInstallPack(Context context, Uri uri, File target) throws Exception {
        InputStream raw = context.getContentResolver().openInputStream(uri);
        if (raw == null) {
            throw new IllegalArgumentException("選択したファイルを開けません");
        }

        boolean found = false;
        try (ZipInputStream zip = new ZipInputStream(new BufferedInputStream(raw));
             FileOutputStream out = new FileOutputStream(target)) {
            ZipEntry entry;
            byte[] buffer = new byte[1024 * 1024];
            while ((entry = zip.getNextEntry()) != null) {
                String lower = entry.getName().toLowerCase(Locale.ROOT);
                if (!entry.isDirectory() && (lower.endsWith("/split_installpack.apk")
                        || lower.equals("split_installpack.apk"))) {
                    int read;
                    while ((read = zip.read(buffer)) >= 0) {
                        if (read > 0) {
                            out.write(buffer, 0, read);
                        }
                    }
                    found = true;
                    break;
                }
                zip.closeEntry();
            }
        }

        if (!found) {
            target.delete();
            throw new IllegalArgumentException("export ZIP 内に split_InstallPack.apk がありません");
        }
    }

    private static String firstCsvField(byte[] payload) {
        String text = new String(payload, StandardCharsets.UTF_8).replace("\uFEFF", "");
        for (String rawLine : text.split("\\R")) {
            String line = rawLine.trim();
            if (line.isEmpty()) {
                continue;
            }
            int comma = line.indexOf(',');
            return (comma >= 0 ? line.substring(0, comma) : line).trim();
        }
        return "";
    }

    private static List<String> firstStatRow(byte[] payload) {
        String text = new String(payload, StandardCharsets.UTF_8).replace("\uFEFF", "");
        for (String rawLine : text.split("\\R")) {
            String line = rawLine;
            int comment = line.indexOf("//");
            if (comment >= 0) {
                line = line.substring(0, comment);
            }
            line = line.trim();
            if (line.isEmpty()) {
                continue;
            }
            String[] columns = line.split(",", -1);
            int end = columns.length;
            while (end > 0 && columns[end - 1].trim().isEmpty()) {
                end--;
            }
            List<String> values = new ArrayList<>(end);
            for (int i = 0; i < end; i++) {
                values.add(columns[i].trim());
            }
            return values;
        }
        return Collections.emptyList();
    }

    private static byte[] readZipEntry(ZipFile zip, String name) throws Exception {
        ZipEntry entry = zip.getEntry(name);
        if (entry == null) {
            throw new IllegalArgumentException("InstallPack に " + name + " がありません");
        }
        try (InputStream in = zip.getInputStream(entry)) {
            return readAll(in);
        }
    }

    private static byte[] readAll(InputStream in) throws Exception {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] buffer = new byte[256 * 1024];
        int read;
        while ((read = in.read(buffer)) >= 0) {
            if (read > 0) {
                out.write(buffer, 0, read);
            }
        }
        return out.toByteArray();
    }

    private static byte[] decryptManifest(byte[] raw) throws Exception {
        byte[] digest = MessageDigest.getInstance("MD5")
                .digest("pack".getBytes(StandardCharsets.UTF_8));
        byte[] key = hexAscii(Arrays.copyOf(digest, 8));
        Cipher cipher = Cipher.getInstance("AES/ECB/PKCS5Padding");
        cipher.init(Cipher.DECRYPT_MODE, new SecretKeySpec(key, "AES"));
        return cipher.doFinal(raw);
    }

    private static byte[] decryptLocal(byte[] raw) throws Exception {
        Cipher cipher = Cipher.getInstance("AES/CBC/PKCS5Padding");
        cipher.init(
                Cipher.DECRYPT_MODE,
                new SecretKeySpec(JP_KEY, "AES"),
                new IvParameterSpec(JP_IV)
        );
        return cipher.doFinal(raw);
    }

    private static byte[] hexAscii(byte[] bytes) {
        final char[] alphabet = "0123456789abcdef".toCharArray();
        byte[] result = new byte[bytes.length * 2];
        for (int i = 0; i < bytes.length; i++) {
            int value = bytes[i] & 0xff;
            result[i * 2] = (byte) alphabet[value >>> 4];
            result[i * 2 + 1] = (byte) alphabet[value & 0x0f];
        }
        return result;
    }

    private static byte[] hex(String value) {
        byte[] out = new byte[value.length() / 2];
        for (int i = 0; i < out.length; i++) {
            out[i] = (byte) Integer.parseInt(value.substring(i * 2, i * 2 + 2), 16);
        }
        return out;
    }

    private static final class StageAddress {
        final String kindKey;
        final String category;
        final String sourcePrefix;
        final int mapIndex;
        final int stageIndex;
        final String stageNameFile;

        StageAddress(
                String kindKey,
                String category,
                String sourcePrefix,
                int mapIndex,
                int stageIndex,
                String stageNameFile
        ) {
            this.kindKey = kindKey;
            this.category = category;
            this.sourcePrefix = sourcePrefix;
            this.mapIndex = mapIndex;
            this.stageIndex = stageIndex;
            this.stageNameFile = stageNameFile;
        }

        String fallbackName() {
            return String.format(
                    Locale.ROOT,
                    "%s %03d-%02d",
                    category,
                    mapIndex,
                    stageIndex
            );
        }
    }

    private static final class Pack {
        private final Map<String, Entry> entries = new TreeMap<>();
        private final byte[] pack;

        Pack(byte[] manifestBytes, byte[] packBytes) throws Exception {
            this.pack = packBytes;
            String manifest = new String(decryptManifest(manifestBytes), StandardCharsets.UTF_8)
                    .replace("\uFEFF", "");
            String[] lines = manifest.split("\\R");
            int declared = Integer.parseInt(lines[0].trim());
            int parsed = 0;
            for (int i = 1; i < lines.length; i++) {
                String line = lines[i].trim();
                if (line.isEmpty()) {
                    continue;
                }
                String[] columns = line.split(",", 4);
                if (columns.length < 3) {
                    throw new IllegalArgumentException("壊れた pack manifest row: " + line);
                }
                String name = columns[0].trim();
                int offset = Integer.parseInt(columns[1].trim());
                int size = Integer.parseInt(columns[2].trim());
                if (offset < 0 || size < 0 || (long) offset + size > packBytes.length) {
                    throw new IllegalArgumentException("pack 範囲外: " + name);
                }
                entries.put(name, new Entry(offset, size));
                parsed++;
            }
            if (declared != parsed) {
                throw new IllegalArgumentException("pack manifest count mismatch");
            }
        }

        Iterable<String> names() {
            return entries.keySet();
        }

        boolean has(String name) {
            return entries.containsKey(name);
        }

        byte[] read(String name) throws Exception {
            Entry entry = entries.get(name);
            if (entry == null) {
                throw new IllegalArgumentException("pack entry missing: " + name);
            }
            byte[] encrypted = Arrays.copyOfRange(pack, entry.offset, entry.offset + entry.size);
            return decryptLocal(encrypted);
        }
    }

    private static final class Entry {
        final int offset;
        final int size;

        Entry(int offset, int size) {
            this.offset = offset;
            this.size = size;
        }
    }
}