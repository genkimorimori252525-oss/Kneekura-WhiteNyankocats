package jp.kneekura.whitenyankocats;

import android.content.Context;
import android.net.Uri;
import android.util.AtomicFile;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.KeyFactory;
import java.security.MessageDigest;
import java.security.PublicKey;
import java.security.interfaces.ECPublicKey;
import java.security.spec.X509EncodedKeySpec;
import java.util.Base64;
import java.util.Locale;

/**
 * Explicit one-time pairing of the owner's public P-256 LiveOps signing key.
 *
 * Android app NEVER downloads a key and NEVER trusts a public key bundled with
 * an incoming update. The user imports the pubkey once from a local file
 * supplied separately by their trusted computer and confirms its fingerprint.
 * The private signing key stays ONLY on that computer.
 */
final class LocalOpsTrust {
    private static final int KEY_FILE_MAX = 8192;
    private static final String PINNED_NAME = "operator-public.der";

    private LocalOpsTrust() {}

    static File root(Context context) {
        return new File(context.getFilesDir(), "kneekura-liveops");
    }

    static File keyFile(Context context) {
        return new File(root(context), PINNED_NAME);
    }

    static boolean paired(Context context) {
        return keyFile(context).isFile();
    }

    static byte[] trustedKey(Context context) throws IOException {
        File file = keyFile(context);
        if (!file.isFile() || file.length() < 40L || file.length() > KEY_FILE_MAX) {
            throw new IOException("No valid local operator key paired");
        }
        try (InputStream stream = new java.io.FileInputStream(file)) {
            byte[] bytes = bounded(stream);
            verifyPublicKey(bytes);
            return bytes;
        }
    }

    static byte[] candidateFromUri(Context context, Uri uri) throws IOException {
        if (uri == null || !"content".equals(uri.getScheme())) {
            throw new IOException("Select a local operator public key file");
        }
        try (InputStream stream = context.getContentResolver().openInputStream(uri)) {
            if (stream == null) throw new IOException("Could not read public key");
            byte[] input = bounded(stream);
            String text = new String(input, StandardCharsets.US_ASCII);
            byte[] bytes;
            if (text.contains("-----BEGIN PUBLIC KEY-----")) {
                String base64 = text.replace("-----BEGIN PUBLIC KEY-----", "")
                        .replace("-----END PUBLIC KEY-----", "")
                        .replaceAll("\\s+", "");
                try {
                    bytes = Base64.getDecoder().decode(base64);
                } catch (IllegalArgumentException exception) {
                    throw new IOException("Invalid public key PEM", exception);
                }
            } else {
                bytes = input; // DER/SubjectPublicKeyInfo input
            }
            verifyPublicKey(bytes);
            return bytes;
        }
    }

    private static byte[] bounded(InputStream input) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] buffer = new byte[1024];
        int n;
        while ((n = input.read(buffer)) >= 0) {
            if (n == 0) continue;
            if (out.size() + n > KEY_FILE_MAX) {
                throw new IOException("Public key file is unexpectedly large");
            }
            out.write(buffer, 0, n);
        }
        return out.toByteArray();
    }

    private static void verifyPublicKey(byte[] der) throws IOException {
        try {
            PublicKey key = KeyFactory.getInstance("EC")
                    .generatePublic(new X509EncodedKeySpec(der));
            if (!(key instanceof ECPublicKey) ||
                    ((ECPublicKey) key).getParams().getCurve().getField().getFieldSize() != 256) {
                throw new IOException("Only the P-256 operator public key is allowed");
            }
        } catch (IOException ex) {
            throw ex;
        } catch (Exception ex) {
            throw new IOException("Not a valid P-256 X.509 public key", ex);
        }
    }

    static String fingerprint(byte[] bytes) throws IOException {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(bytes);
            StringBuilder output = new StringBuilder();
            for (byte b : digest) {
                output.append(String.format(Locale.ROOT, "%02x", b & 255));
            }
            return output.toString();
        } catch (Exception ex) {
            throw new IOException("Could not hash the operator key", ex);
        }
    }

    static void pinOnce(Context context, byte[] bytes) throws IOException {
        verifyPublicKey(bytes);
        File output = keyFile(context);
        if (output.exists()) {
            throw new IOException("Operator key already paired; no silent replacement");
        }
        if (!root(context).isDirectory() && !root(context).mkdirs()) {
            throw new IOException("Cannot create local operator storage");
        }
        AtomicFile target = new AtomicFile(output);
        FileOutputStream stream = null;
        try {
            stream = target.startWrite();
            stream.write(bytes);
            target.finishWrite(stream);
        } catch (IOException exception) {
            if (stream != null) target.failWrite(stream);
            throw exception;
        }
    }
}
