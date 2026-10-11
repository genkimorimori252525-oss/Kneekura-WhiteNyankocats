package jp.kneekura.whitenyankocats;

import android.app.Activity;
import android.content.ContentResolver;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;

/**
 * Android bridge *sample* for a future INDEPENDENT Kneekura game host.
 *
 * This is deliberately NOT patched into PONOS MyActivity. It does NOT verify
 * ECDSA signatures, activate a pack, or hook Battle Cats. After staging, hand
 * the private file to the future trusted LocalOpsBundleVerifier for complete
 * P-256 signature, allowed-entry, schema and revision checks BEFORE install.
 *
 * The picker needs neither INTERNET nor broad storage permissions. This API
 * never performs network I/O or writes to the original Battle Cats SAVE_DATA.
 */
public final class OfflineUpdatePicker {
    public static final int REQUEST_CONTENT_UPDATE = 1042;
    private static final long MAX_BYTES = 2L * 1024 * 1024;

    private OfflineUpdatePicker() {}

    /** Call from an actual in-app "更新を取り込む" user action. */
    public static void open(Activity activity) {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("application/zip");
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        activity.startActivityForResult(intent, REQUEST_CONTENT_UPDATE);
    }

    /**
     * Stages the user-selected LOCAL document in app-private cache only.
     * Invoke from the host Activity result handler, not from a background
     * service or original game network hook. Caller must verify signature
     * via a pinned public key before touching live operation content.
     */
    public static File stageFromResult(
            Context context, int requestCode, int resultCode, Intent data
    ) throws IOException {
        if (requestCode != REQUEST_CONTENT_UPDATE
                || resultCode != Activity.RESULT_OK
                || data == null || data.getData() == null) {
            throw new IOException("No user-selected local update document");
        }
        Uri uri = data.getData();
        if (!"content".equals(uri.getScheme())) {
            throw new IOException("Only user-granted content URI is accepted");
        }
        ContentResolver resolver = context.getContentResolver();
        File directory = new File(context.getCacheDir(), "kneekura-update-staging");
        if (!directory.isDirectory() && !directory.mkdirs()) {
            throw new IOException("Cannot open private update staging directory");
        }
        File temp = File.createTempFile("pending-", ".kneekura.zip", directory);
        boolean accepted = false;
        try {
            try (InputStream input = resolver.openInputStream(uri);
                 FileOutputStream output = new FileOutputStream(temp)) {
                if (input == null) {
                    throw new IOException("Selected document cannot be read");
                }
                byte[] buffer = new byte[64 * 1024];
                long total = 0L;
                int n;
                while ((n = input.read(buffer)) != -1) {
                    total += n;
                    if (total > MAX_BYTES) {
                        throw new IOException("The update file is too large");
                    }
                    output.write(buffer, 0, n);
                }
                if (total == 0L) {
                    throw new IOException("Empty update file");
                }
                output.flush();
                output.getFD().sync();
            }
            accepted = true;
            return temp;
        } finally {
            if (!accepted && temp.exists()) {
                temp.delete();
            }
        }
    }
}
