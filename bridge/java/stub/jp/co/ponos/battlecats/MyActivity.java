package jp.co.ponos.battlecats;

import androidx.appcompat.app.AppCompatActivity;

import java.nio.ByteBuffer;
import java.util.HashMap;

/**
 * Compile-only ABI stub for the exact JP 15.7.1 bridge.
 *
 * This class is never packaged. It exists only so javac can compile the
 * flavor-specific subclass that is injected as an additional DEX.
 */
public class MyActivity extends AppCompatActivity {
    public int newHttpRequest(
            String method,
            String requestUrl,
            float timeout,
            HashMap headers,
            ByteBuffer body,
            String[] strings,
            boolean flag1,
            boolean flag2) {
        throw new AssertionError("compile-only stub");
    }

    public static native void newResponse(
            int requestId,
            int status,
            String requestUrl,
            String responseHeaders,
            ByteBuffer body,
            boolean flag);
}
