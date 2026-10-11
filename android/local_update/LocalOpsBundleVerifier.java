package jp.kn.localops;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.KeyFactory;
import java.security.MessageDigest;
import java.security.PublicKey;
import java.security.Signature;
import java.security.spec.X509EncodedKeySpec;
import java.util.Enumeration;
import java.util.HashSet;
import java.util.Set;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

/**
 * Offline Android P-256 content authenticity verifier for a future independent
 * Kneekura host. NOT WIRED to Android builds or an update UI yet.
 *
 * The public key passed by the HOST must be pinned into the Android app
 * installation, NOT loaded from the untrusted incoming ZIP. It must be
 * X.509 SubjectPublicKeyInfo DER of the trusted local operator public key.
 *
 * This reads only the app-private TEMP file staged by OfflineUpdatePicker.
 * It NEVER contacts the Internet, imports a PONOS SAVE_DATA, writes game
 * progress, or installs an APK. Only a separate reviewed host adapter may
 * commit validated content with rollback.
 */
public final class LocalOpsBundleVerifier {
    private static final int MAX_ARCHIVE = 2 * 1024 * 1024;
    private static final int MAX_MANIFEST = 8192;
    private static final int MAX_CONTENT = 1024 * 1024;
    private static final int MAX_SIGNATURE = 256;
    private static final String BUNDLE_KIND = "kneekura.localops.bundle.v1";
    private static final String ALGORITHM = "ECDSA-P256-SHA256-DER";
    private static final String CHANNEL = "kneekura-main-offline";

    private LocalOpsBundleVerifier() {}

    public static final class Verified {
        public final int revision;
        public final String sha256;
        public final JSONObject predecessor;
        public final byte[] contentBytes;

        private Verified(int revision, String sha256, JSONObject predecessor, byte[] bytes) {
            this.revision = revision;
            this.sha256 = sha256;
            this.predecessor = predecessor;
            this.contentBytes = bytes;
        }
    }

    private static byte[] boundedRead(ZipFile zip, ZipEntry entry, int max) throws IOException {
        if (entry == null || entry.isDirectory() || entry.getSize() > max || entry.getSize() == 0L) {
            throw new IOException("Missing, empty, or oversized update entry");
        }
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        byte[] buffer = new byte[8192];
        int count;
        try (InputStream input = zip.getInputStream(entry)) {
            while ((count = input.read(buffer)) != -1) {
                if (output.size() + count > max) {
                    throw new IOException("Uncompressed update entry exceeded limit");
                }
                output.write(buffer, 0, count);
            }
        }
        if (output.size() == 0 || (entry.getSize() >= 0 && entry.getSize() != output.size())) {
            throw new IOException("Update entry is empty or truncated");
        }
        return output.toByteArray();
    }

    private static String sha256(byte[] bytes) throws Exception {
        byte[] digest = MessageDigest.getInstance("SHA-256").digest(bytes);
        final char[] digits = "0123456789abcdef".toCharArray();
        char[] out = new char[digest.length * 2];
        for (int i = 0; i < digest.length; i++) {
            out[i * 2] = digits[(digest[i] >>> 4) & 15];
            out[i * 2 + 1] = digits[digest[i] & 15];
        }
        return new String(out);
    }

    private static void checkNoNetworkFields(Object item, int depth) throws JSONException, IOException {
        if (depth > 32) throw new IOException("Excessively nested pack");
        if (item instanceof JSONObject) {
            JSONObject map = (JSONObject) item;
            JSONArray names = map.names();
            if (names == null) return;
            if (names.length() > 2000) throw new IOException("Oversized pack object");
            for (int i = 0; i < names.length(); i++) {
                String key = names.getString(i);
                String lower = key.toLowerCase(java.util.Locale.ROOT);
                if ("endpoint".equals(lower) || "account_token".equals(lower) ||
                        "server_url".equals(lower) || "inquiry_code".equals(lower) ||
                        "official_save_data".equals(lower)) {
                    throw new IOException("External account or service field not accepted");
                }
                checkNoNetworkFields(map.get(key), depth + 1);
            }
        } else if (item instanceof JSONArray) {
            JSONArray array = (JSONArray) item;
            if (array.length() > 5000) throw new IOException("Oversized pack array");
            for (int i = 0; i < array.length(); i++) {
                checkNoNetworkFields(array.get(i), depth + 1);
            }
        } else if (item instanceof String) {
            String text = ((String) item).toLowerCase(java.util.Locale.ROOT);
            if (text.contains("http://") || text.contains("https://") ||
                    text.contains("wss://") || text.contains("ws://") ||
                    text.contains("file://")) {
                throw new IOException("External URL is not valid offline content");
            }
        }
    }

    /**
     * Exact ZIP format emitted by tools/localcore/offline_update_bundle.py.
     * Android supports SHA256withECDSA (P-256) without Ed25519 API-33 limit.
     */
    public static Verified verify(File archive, byte[] pinnedOperatorSpkiDer)
            throws Exception {
        if (!archive.isFile() || archive.length() < 1 || archive.length() > MAX_ARCHIVE) {
            throw new IOException("Not a bounded local update file");
        }
        if (pinnedOperatorSpkiDer == null || pinnedOperatorSpkiDer.length < 40) {
            throw new IOException("No trusted built-in operator public key");
        }
        byte[] manifestBytes;
        byte[] packBytes;
        byte[] signatureBytes;
        try (ZipFile zip = new ZipFile(archive)) {
            Enumeration<? extends ZipEntry> entries = zip.entries();
            Set<String> names = new HashSet<>();
            int count = 0;
            while (entries.hasMoreElements()) {
                ZipEntry entry = entries.nextElement();
                String name = entry.getName();
                if (entry.isDirectory() ||
                        !("manifest.json".equals(name) || "ops.json".equals(name) ||
                          "signature.der".equals(name)) || !names.add(name)) {
                    throw new IOException("Unknown, repeated, or unsafe update ZIP entry");
                }
                count++;
            }
            if (count != 3) throw new IOException("Incomplete signed update ZIP");
            manifestBytes = boundedRead(zip, zip.getEntry("manifest.json"), MAX_MANIFEST);
            packBytes = boundedRead(zip, zip.getEntry("ops.json"), MAX_CONTENT);
            signatureBytes = boundedRead(zip, zip.getEntry("signature.der"), MAX_SIGNATURE);
        }
        JSONObject manifest = new JSONObject(new String(manifestBytes, StandardCharsets.UTF_8));
        if (!BUNDLE_KIND.equals(manifest.getString("bundle_kind")) ||
                !CHANNEL.equals(manifest.getString("channel")) ||
                !ALGORITHM.equals(manifest.getString("algorithm")) ||
                manifest.getInt("schema_version") != 1 ||
                manifest.getInt("revision") < 1 ||
                manifest.getBoolean("requires_network") ||
                manifest.getBoolean("contains_player_state") ||
                manifest.getInt("content_bytes") != packBytes.length ||
                !sha256(packBytes).equals(manifest.getString("content_sha256")) ||
                !sha256(pinnedOperatorSpkiDer).equals(manifest.getString("operator_key_sha256"))) {
            throw new IOException("Update identity, key fingerprint, or contents mismatch");
        }

        KeyFactory keyFactory = KeyFactory.getInstance("EC");
        PublicKey pinned = keyFactory.generatePublic(new X509EncodedKeySpec(pinnedOperatorSpkiDer));
        Signature checker = Signature.getInstance("SHA256withECDSA");
        checker.initVerify(pinned);
        checker.update(manifestBytes);
        if (!checker.verify(signatureBytes)) {
            throw new IOException("Update signature invalid for installed operator key");
        }

        JSONObject ops = new JSONObject(new String(packBytes, StandardCharsets.UTF_8));
        JSONObject policy = ops.getJSONObject("policy");
        if (!CHANNEL.equals(ops.getString("channel")) ||
                !"published".equals(ops.getString("status")) ||
                ops.getInt("revision") != manifest.getInt("revision") ||
                !"Asia/Tokyo".equals(ops.getString("timezone")) ||
                !"forbidden".equals(policy.getString("network")) ||
                !"KNEEKURA_SAVE_V1".equals(policy.getString("owner_save")) ||
                policy.getInt("login_active_slots") != 5 ||
                policy.getBoolean("real_money") ||
                policy.getBoolean("stage_availability_is_clear")) {
            throw new IOException("Operator pack violates local game safety policy");
        }
        checkNoNetworkFields(ops, 0);
        Object predecessor = manifest.get("previous");
        JSONObject previous = predecessor == JSONObject.NULL ? null : manifest.getJSONObject("previous");
        // The Android host still MUST check the revision/predecessor chain,
        // local asset readiness and its own last-known-good state atomically.
        return new Verified(
            manifest.getInt("revision"), manifest.getString("content_sha256"),
            previous, packBytes
        );
    }
}
