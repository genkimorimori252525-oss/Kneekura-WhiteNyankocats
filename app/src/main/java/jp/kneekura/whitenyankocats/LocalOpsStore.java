package jp.kneekura.whitenyankocats;

import android.content.Context;
import android.util.AtomicFile;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

/**
 * Independent Kneekura operations-content store. Never modifies the actual
 * player profile, original Battle Cats SAVE_DATA, original APK, or network.
 *
 * SHA content addresses plus AtomicFile current/previous pointers make
 * update interruption non-destructive; rollback selects last-known-good
 * content and does not reset player achievements or inventory.
 *
 * The calling Activity MUST verify the ECDSA signature against the separately
 * pinned public key, then display the signed revision for confirmation.
 */
final class LocalOpsStore {
    private static final String CURRENT = "current.json";
    private static final String PREVIOUS = "previous.json";
    private static final int MAX_CONTENT = 1024 * 1024;
    private static final String CHANNEL = "kneekura-main-offline";

    private LocalOpsStore() {}

    static final class Status {
        final int revision;
        final String digest;
        Status(int revision, String digest) {
            this.revision = revision;
            this.digest = digest;
        }
    }

    private static File contentDir(Context context) {
        return new File(LocalOpsTrust.root(context), "revisions");
    }

    private static byte[] readBounded(File path) throws IOException {
        if (!path.isFile() || path.length() < 1 || path.length() > MAX_CONTENT) {
            throw new IOException("Invalid independent content file");
        }
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        try (FileInputStream input = new FileInputStream(path)) {
            byte[] buffer = new byte[8192];
            int n;
            while ((n = input.read(buffer)) != -1) {
                if (out.size() + n > MAX_CONTENT) {
                    throw new IOException("Content store exceeds allowed size");
                }
                out.write(buffer, 0, n);
            }
        }
        return out.toByteArray();
    }

    private static String sha(byte[] data) throws IOException {
        try {
            byte[] raw = MessageDigest.getInstance("SHA-256").digest(data);
            char[] symbols = "0123456789abcdef".toCharArray();
            char[] out = new char[raw.length * 2];
            for (int i = 0; i < raw.length; i++) {
                out[2 * i] = symbols[(raw[i] >>> 4) & 15];
                out[2 * i + 1] = symbols[raw[i] & 15];
            }
            return new String(out);
        } catch (Exception error) {
            throw new IOException("Cannot compute content fingerprint", error);
        }
    }

    private static JSONObject readPointer(Context context, String name) throws Exception {
        File file = new File(LocalOpsTrust.root(context), name);
        if (!file.exists()) return null;
        byte[] raw = new AtomicFile(file).readFully();
        JSONObject pointer = new JSONObject(new String(raw, StandardCharsets.UTF_8));
        String digest = pointer.getString("content_sha256");
        String filename = pointer.getString("file");
        if (!digest.matches("[0-9a-f]{64}") ||
                !filename.matches("rev-[0-9]+-[0-9a-f]{64}\\.json") ||
                !filename.equals("rev-" + pointer.getInt("revision") + "-" + digest + ".json")) {
            throw new IOException("Unexpected local content pointer");
        }
        String pinned = LocalOpsTrust.fingerprint(LocalOpsTrust.trustedKey(context));
        if (!pinned.equals(pointer.getString("operator_key_sha256"))) {
            throw new IOException("Pinned operator identity changed");
        }
        byte[] stored = readBounded(new File(contentDir(context), filename));
        if (!sha(stored).equals(digest)) {
            throw new IOException("Installed content hash mismatch");
        }
        JSONObject content = new JSONObject(new String(stored, StandardCharsets.UTF_8));
        if (!CHANNEL.equals(content.getString("channel")) ||
                !"published".equals(content.getString("status")) ||
                content.getInt("revision") != pointer.getInt("revision")) {
            throw new IOException("Unrecognized installed content schema");
        }
        return pointer;
    }

    private static void writeAtomic(File file, byte[] content) throws IOException {
        File parent = file.getParentFile();
        if (parent == null || (!parent.isDirectory() && !parent.mkdirs())) {
            throw new IOException("Could not create private content directory");
        }
        AtomicFile atomic = new AtomicFile(file);
        FileOutputStream output = null;
        try {
            output = atomic.startWrite();
            output.write(content);
            atomic.finishWrite(output);
        } catch (IOException ex) {
            if (output != null) atomic.failWrite(output);
            throw ex;
        }
    }

    static synchronized String importVerified(
            Context context, LocalOpsBundleVerifier.Verified received
    ) throws Exception {
        if (received == null || received.revision < 1 ||
                received.contentBytes == null || received.contentBytes.length > MAX_CONTENT ||
                !sha(received.contentBytes).equals(received.sha256)) {
            throw new IOException("Unverified or invalid content passed to store");
        }
        JSONObject now = readPointer(context, CURRENT);
        String keyDigest = LocalOpsTrust.fingerprint(LocalOpsTrust.trustedKey(context));
        if (now != null) {
            int currentRevision = now.getInt("revision");
            String currentHash = now.getString("content_sha256");
            if (received.revision == currentRevision &&
                    currentHash.equals(received.sha256)) {
                return "同じ運営データがすでに適用されています（変更なし）";
            }
            if (received.revision <= currentRevision ||
                    received.predecessor == null ||
                    received.predecessor.getInt("revision") != currentRevision ||
                    !received.predecessor.getString("content_sha256").equals(currentHash)) {
                throw new IOException("更新順序が違います。前のバージョンから適用してください");
            }
        } else if (received.predecessor != null) {
            throw new IOException("初回更新ではありません。前の運営パックが必要です");
        }
        String filename = "rev-" + received.revision + "-" + received.sha256 + ".json";
        File revision = new File(contentDir(context), filename);
        if (revision.exists()) {
            if (!sha(readBounded(revision)).equals(received.sha256)) {
                throw new IOException("既存のローカル更新ファイルが壊れています");
            }
        } else {
            writeAtomic(revision, received.contentBytes);
        }
        JSONObject pointer = new JSONObject();
        pointer.put("revision", received.revision);
        pointer.put("content_sha256", received.sha256);
        pointer.put("file", filename);
        pointer.put("operator_key_sha256", keyDigest);

        if (now != null) {
            writeAtomic(
                new File(LocalOpsTrust.root(context), PREVIOUS),
                now.toString().getBytes(StandardCharsets.UTF_8)
            );
        }
        writeAtomic(new File(LocalOpsTrust.root(context), CURRENT),
                    pointer.toString().getBytes(StandardCharsets.UTF_8));
        return "にーくら運営データ v" + received.revision + " を適用しました";
    }

    static Status current(Context context) throws Exception {
        JSONObject pointer = readPointer(context, CURRENT);
        return pointer == null ? null : new Status(
            pointer.getInt("revision"), pointer.getString("content_sha256")
        );
    }

    static synchronized String rollback(Context context) throws Exception {
        JSONObject current = readPointer(context, CURRENT);
        JSONObject previous = readPointer(context, PREVIOUS);
        if (current == null || previous == null) {
            throw new IOException("復元できる一つ前の運営データがありません");
        }
        writeAtomic(
            new File(LocalOpsTrust.root(context), CURRENT),
            previous.toString().getBytes(StandardCharsets.UTF_8)
        );
        new AtomicFile(new File(LocalOpsTrust.root(context), PREVIOUS)).delete();
        return "運営データを v" + previous.getInt("revision") + " に戻しました";
    }
}
