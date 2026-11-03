package jp.co.ponos.battlecats;

import android.app.Activity;

import java.nio.ByteBuffer;
import java.util.HashMap;

/**
 * Compile-only ABI stub for the exact JP 15.7.1 bridge.
 *
 * This class is never packaged. It exists only so javac can compile the
 * flavor-specific subclass that is injected as an additional DEX.
 */
public class MyActivity extends Activity {
    public void setWebViewUrl(int handle, String url, String[] cookies) {
        throw new AssertionError("compile-only stub");
    }
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

    // Exact original JP15.7.1 classes4.dex instance method.
    // Compile-only stub; never included in any signed APK.
    public boolean isNetworkAvailable() {
        throw new AssertionError("compile-only stub");
    }

    public int newAlert(String message, String[] buttons) {
        throw new AssertionError("compile-only stub");
    }

    public static native void newResponse(
            int requestId,
            int status,
            String requestUrl,
            String responseHeaders,
            ByteBuffer body,
            boolean flag);
    public static native void onResponseCodeHeaders(int requestId, int status,
            String requestUrl, String responseHeaders);
    public static native void onResponseData(int requestId, ByteBuffer body);
    public static native void onResponseFinish(int requestId, boolean error);
}
