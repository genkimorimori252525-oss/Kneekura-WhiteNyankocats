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
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
import java.util.zip.ZipInputStream;

import javax.crypto.Cipher;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;

public final class BattleCatsImporter {
    private static final byte[] JP_KEY = hex("d754868de89d717fa9e7b06da45ae9e3");
    private static final byte[] JP_IV = hex("40b2131a9f388ad4e5002a98118f6128");

    private BattleCatsImporter() {
    }

    public static List<UnitRecord> importFromUri(Context context, Uri uri) throws Exception {
        File installApk = new File(context.getCacheDir(), "kneekura-installpack-" + System.nanoTime() + ".apk");
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
                    byte[] statsBytes = data.read(statsName);
                    byte[] explanationBytes = res.read(explanationName);
                    units.add(new UnitRecord(
                            id,
                            firstCsvField(explanationBytes),
                            firstStatRow(statsBytes)
                    ));
                }
                return units;
            }
        } finally {
            if (installApk.exists()) {
                installApk.delete();
            }
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