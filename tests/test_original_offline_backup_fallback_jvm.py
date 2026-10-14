"""Execute exact original-client backup failure replay on a synthetic JVM.

No real game data, SAVE, device, official server or network. The actual
rendered research MyActivity Java is compiled with minimal Android stubs.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tools.base_mod.inject_java_http_bridge import render_bridge_source

ROOT=Path(__file__).resolve().parents[1]


class OriginalLocalBackupOfflineFallbackJvmTests(unittest.TestCase):
    def test_exact_original_failure_completion_and_unknown_strict_deny(self):
        self._exercise()

    def test_pc_authority_delivers_local_origin_and_direct_body(self):
        self._exercise(authority=True)

    def _exercise(self, *, authority=False):
        javac=shutil.which("javac")
        java=shutil.which("java")
        if not javac or not java:
            self.skipTest("local JDK unavailable")
        rendered=render_bridge_source(
            (ROOT/"bridge/java/MyActivity.java.in").read_text(encoding="utf-8"),
            flavor="local-research",enabled=False,
            offline_393_import_enabled=True,
            pc_jni_scene_observer=True,
            pc_boot_authority=authority,
        )
        source={
            "android/os/Bundle.java":"package android.os; public class Bundle {}",
            "android/opengl/GLSurfaceView.java":(
                "package android.opengl;"
                "public class GLSurfaceView {"
                " public void queueEvent(Runnable run) {run.run();}"
                "}"
            ),
            "android/os/FileObserver.java":(
                "package android.os;"
                "public abstract class FileObserver {"
                " public static final int CREATE=256,CLOSE_WRITE=8,"
                "MOVED_TO=128,DELETE=512,OPEN=32,ACCESS=1;"
                " public FileObserver(String path,int flags) {}"
                " public void startWatching() {}"
                " public abstract void onEvent(int kind,String name);"
                "}"
            ),
            "android/util/Log.java":(
                "package android.util;"
                "public class Log {"
                " public static int i(String tag,String event) {"
                "  if (event.startsWith(\"original-local-\"))"
                "   System.out.println(event);"
                "  return 0;"
                " }"
                "}"
            ),
            "jp/co/ponos/battlecats/MyActivity.java":"""
                package jp.co.ponos.battlecats;
                import java.io.File;
                import java.nio.ByteBuffer;
                import java.util.HashMap;
                import java.util.Map;
                import android.opengl.GLSurfaceView;
                public class MyActivity {
                  protected void onCreate(android.os.Bundle state) {}
                  public void runOnUiThread(Runnable run) {run.run();}
                  public void setWebViewUrl(int handle,String url,String[] cookies) {}
                  private int mNextRequestHandle = 1;
                  private Map mRequestHandles = new HashMap();
                  private GLSurfaceView mGLView = new GLSurfaceView();
                  public static int superCalled;
                  public static int networkAvailableSuperCalled;
                  public boolean isNetworkAvailable(){
                    networkAvailableSuperCalled++;
                    return true;
                  }
                  public static int nativeResponseCount;
                  public static int lastNativeCode;
                  public static String lastNativeBody;
                  public static String lastNativeUrl;
                  public static boolean lastNativeDirect;
                  public static boolean lastNativeLocalBody;
                  public static boolean lastNativeFinal;
                  public static String streamOrder="";
                  public static int streamCode;
                  public static boolean streamError;
                  public static boolean streamDirect;
                  public static void onResponseCodeHeaders(int id,int code,String url,String headers) {
                    streamOrder="H"; streamCode=code; streamDirect=false;
                  }
                  public static void onResponseData(int id,ByteBuffer body) {
                    streamOrder+="D"; streamDirect=body.isDirect() && body.remaining()>0;
                  }
                  public static void onResponseFinish(int id,boolean error) {
                    streamOrder+="F"; streamError=error;
                  }
                  public int newHttpRequest(String method,String url,
                    float timeout,HashMap headers,ByteBuffer body,
                    String[] strings,boolean a,boolean b) {
                    superCalled++;
                    return -98;
                  }
                  public static void newResponse(int id,int code,String url,
                    String json,Object body,boolean end) {
                    nativeResponseCount++;
                    lastNativeUrl=url;
                    lastNativeDirect=body instanceof ByteBuffer && ((ByteBuffer)body).isDirect();
                    lastNativeLocalBody=false;
                    if (body instanceof ByteBuffer) {
                      ByteBuffer copy=((ByteBuffer)body).duplicate();
                      byte[] bytes=new byte[copy.remaining()]; copy.get(bytes);
                      String payload=new String(bytes,java.nio.charset.StandardCharsets.UTF_8);
                      lastNativeLocalBody=payload.contains("\\\"authority\\\":\\\"kneekura-local\\\"")
                        && payload.contains("\\\"success\\\":true") && payload.contains("\\\"timestamp\\\":");
                    }
                    lastNativeCode=code;
                    lastNativeBody=json;
                    lastNativeFinal=end;
                  }
                  public File getFilesDir(){ return new File(
                    System.getProperty("kn.local.dir","."));
                  }
                  public File getExternalFilesDir(String type){return null;}
                }
            """,
            "a32.java":"""
                import java.net.URL;
                import java.nio.ByteBuffer;
                import java.util.HashMap;
                public class a32 {
                  public a32(int id,String method,URL url,float timeout,
                    HashMap headers,ByteBuffer body,String[] strings){}
                }
            """,
            "jp/kn/local/battlecats/MyActivity.java":rendered,
            "jp/kn/local/battlecats/Harness.java":"""
                package jp.kn.local.battlecats;
                import java.util.HashMap;
                public class Harness {
                  public static void main(String[] args) {
                    MyActivity app=new MyActivity();
                    new java.io.File(System.getProperty("kn.local.dir")).mkdirs();
                    int request=app.newHttpRequest(
                       "GET","https://nyanko-backups.ponosgames.com/?safe-shape=1",
                       10.0f,new HashMap(),null,new String[0],false,false);
                    System.out.println("EXACT_REQUEST_ID="+request);
                    System.out.println("ORIGINAL_FALLBACK_COUNT="+
                      jp.co.ponos.battlecats.MyActivity.nativeResponseCount);
                    System.out.println("ORIGINAL_FALLBACK_CODE="+
                      jp.co.ponos.battlecats.MyActivity.lastNativeCode);
                    System.out.println("ORIGINAL_FALLBACK_BODY="+
                      jp.co.ponos.battlecats.MyActivity.lastNativeBody);
                    System.out.println("ORIGINAL_FALLBACK_FINAL="+
                      jp.co.ponos.battlecats.MyActivity.lastNativeFinal);
                    boolean unknownBlocked=false;
                    try {
                      app.newHttpRequest(
                        "GET","https://service.ponosgames.com/unknown",
                        10.0f,new HashMap(),null,new String[0],false,false);
                      unknownBlocked=jp.co.ponos.battlecats.MyActivity.lastNativeCode==503
                        && jp.co.ponos.battlecats.MyActivity.lastNativeFinal;
                    } catch(IllegalStateException expected){
                      unknownBlocked=true;
                    }
                    System.out.println("UNKNOWN_BLOCKED="+unknownBlocked);
                    int syntheticTimeoutVariant=app.newHttpRequest(
                        "GET","https://nyanko-backups.ponosgames.com/?synthetic=1",
                        11.0f,new HashMap(),null,new String[0],false,false);
                    System.out.println("SYNTHETIC_TIMEOUT_11_ID="+syntheticTimeoutVariant);
                    System.out.println("FALLBACK_COUNT_AFTER_VARIANT="+
                      jp.co.ponos.battlecats.MyActivity.nativeResponseCount);
                    boolean nonfiniteTimeoutBlocked=false;
                    try {
                      app.newHttpRequest(
                        "GET","https://nyanko-backups.ponosgames.com/?synthetic=1",
                        Float.NaN,new HashMap(),null,new String[0],false,false);
                      nonfiniteTimeoutBlocked=jp.co.ponos.battlecats.MyActivity.lastNativeCode==503
                        && jp.co.ponos.battlecats.MyActivity.lastNativeFinal;
                    } catch(IllegalStateException expected) {
                      nonfiniteTimeoutBlocked=true;
                    }
                    System.out.println("NONFINITE_TIMEOUT_BLOCKED="+nonfiniteTimeoutBlocked);
                    boolean wrongBackupPathBlocked=false;
                    try {
                      app.newHttpRequest(
                        "GET","https://nyanko-backups.ponosgames.com/unapproved?synthetic=1",
                        10.0f,new HashMap(),null,new String[0],false,false);
                      wrongBackupPathBlocked=jp.co.ponos.battlecats.MyActivity.lastNativeCode==503
                        && jp.co.ponos.battlecats.MyActivity.lastNativeFinal;
                    } catch(IllegalStateException expected) {
                      wrongBackupPathBlocked=true;
                    }
                    System.out.println("WRONG_BACKUP_PATH_BLOCKED="+wrongBackupPathBlocked);
                    boolean invalidNegativeTimeoutBlocked=false;
                    try {
                      app.newHttpRequest(
                        "GET","https://nyanko-backups.ponosgames.com/?synthetic=1",
                        -1.0f,new HashMap(),null,new String[0],false,false);
                      invalidNegativeTimeoutBlocked=jp.co.ponos.battlecats.MyActivity.lastNativeCode==503
                        && jp.co.ponos.battlecats.MyActivity.lastNativeFinal;
                    } catch(IllegalStateException expected) {
                      invalidNegativeTimeoutBlocked=true;
                    }
                    System.out.println("NEGATIVE_TIMEOUT_BLOCKED="+invalidNegativeTimeoutBlocked);
                    boolean outOfRangeTimeoutBlocked=false;
                    try {
                      app.newHttpRequest(
                        "GET","https://nyanko-backups.ponosgames.com/?synthetic=1",
                        121.0f,new HashMap(),null,new String[0],false,false);
                      outOfRangeTimeoutBlocked=jp.co.ponos.battlecats.MyActivity.lastNativeCode==503
                        && jp.co.ponos.battlecats.MyActivity.lastNativeFinal;
                    } catch(IllegalStateException expected) {
                      outOfRangeTimeoutBlocked=true;
                    }
                    System.out.println("OUT_OF_RANGE_TIMEOUT_BLOCKED="+outOfRangeTimeoutBlocked);
                    boolean uppercaseHostBlocked=false;
                    try {
                      app.newHttpRequest(
                        "GET","https://NYANKO-BACKUPS.PONOSGAMES.COM/?synthetic=1",
                        11.0f,new HashMap(),null,new String[0],false,false);
                      uppercaseHostBlocked=jp.co.ponos.battlecats.MyActivity.lastNativeCode==503
                        && jp.co.ponos.battlecats.MyActivity.lastNativeFinal;
                    } catch(IllegalStateException expected) {
                      uppercaseHostBlocked=true;
                    }
                    System.out.println("UPPERCASE_HOST_BLOCKED="+uppercaseHostBlocked);
                    __PC_AUTH_EXERCISE__
                    app.newHttpRequest("GET",
                        "https://nyanko-backups.ponosgames.com/?action=createAccount&referenceId=PRIVATE_VALUE",
                        10.0f,new HashMap(),null,new String[0],false,false);
                    app.newHttpRequest("GET",
                        "https://nyanko-backups.ponosgames.com/?action=getTime&private=PRIVATE_VALUE",
                        10.0f,new HashMap(),null,new String[0],false,false);
                    System.out.println("PC_LOCAL_CODE="+jp.co.ponos.battlecats.MyActivity.lastNativeCode);
                    System.out.println("PC_LOCAL_ERROR="+jp.co.ponos.battlecats.MyActivity.lastNativeFinal);
                    System.out.println("PC_LOCAL_ORIGIN="+jp.co.ponos.battlecats.MyActivity.lastNativeUrl.startsWith("file:///kneekura-local/boot/"));
                    System.out.println("PC_LOCAL_DIRECT="+jp.co.ponos.battlecats.MyActivity.lastNativeDirect);
                    System.out.println("PC_LOCAL_BODY="+jp.co.ponos.battlecats.MyActivity.lastNativeLocalBody);
                    if (__PC_AUTHORITY__) {
                      app.newHttpRequest("GET","https://nyanko-backups.ponosgames.com/?action=getTime",
                        10.0f,new HashMap(),null,new String[0],true,false);
                      System.out.println("CLOCK_STREAM_ORDER="+jp.co.ponos.battlecats.MyActivity.streamOrder);
                      System.out.println("CLOCK_STREAM_CODE="+jp.co.ponos.battlecats.MyActivity.streamCode);
                      System.out.println("CLOCK_STREAM_ERROR="+jp.co.ponos.battlecats.MyActivity.streamError);
                      System.out.println("CLOCK_STREAM_DIRECT="+jp.co.ponos.battlecats.MyActivity.streamDirect);
                    }
                    System.out.println("ORIGINAL_SUPER_HTTP_CALLS="+
                      jp.co.ponos.battlecats.MyActivity.superCalled);
                    System.out.println("LOCAL_ONLY_NETWORK_AVAILABLE="+
                      app.isNetworkAvailable());
                    System.out.println("ORIGINAL_SUPER_NETWORK_CHECK_CALLS="+
                      jp.co.ponos.battlecats.MyActivity.networkAvailableSuperCalled);
                  }
                }
            """,
        }
        if authority:
            source['jp/kn/local/battlecats/KneekuraPcBootAuthority.java'] = (
                ROOT/'bridge/java/KneekuraPcBootAuthority.java.in').read_text(encoding='utf-8').replace(
                    '__KNEEKURA_PACKAGE__', 'jp.kn.local.battlecats')
            auth_test = '''
                    try {
                      java.io.File files=app.getFilesDir();
                      String id=KneekuraPcBootAuthority.player(files);
                      java.nio.ByteBuffer payload=java.nio.ByteBuffer.wrap(
                        ("{\\\"accountCode\\\":\\\""+id+"\\\",\\\"nonce\\\":\\\"synthetic-nonce\\\"}").getBytes(java.nio.charset.StandardCharsets.UTF_8));
                      app.newHttpRequest("POST","https://nyanko-auth.ponosgames.com/v1/users",
                        65.0f,new HashMap(),payload,new String[0],false,false);
                      System.out.println("PC_AUTH_LOCAL="+(jp.co.ponos.battlecats.MyActivity.lastNativeCode==200
                        && !jp.co.ponos.battlecats.MyActivity.lastNativeFinal
                        && jp.co.ponos.battlecats.MyActivity.lastNativeUrl.equals("file:///kneekura-local/boot/register")));
                      String deliveredHeaders=jp.co.ponos.battlecats.MyActivity.lastNativeBody;
                      System.out.println("PC_AUTH_HEADER_STRING="+(deliveredHeaders.contains("\\\"Nyanko-Signature\\\":\\\"")
                        && !deliveredHeaders.contains("[")));
                      boolean rejected=false;
                      try {
                        app.newHttpRequest("POST","https://nyanko-auth.ponosgames.com/v1/users",
                          65.0f,new HashMap(),java.nio.ByteBuffer.wrap("{\\\"accountCode\\\":\\\"FOREIGN_ACCOUNT\\\"}".getBytes()),
                          new String[0],false,false);
                        rejected=jp.co.ponos.battlecats.MyActivity.lastNativeCode==503
                          && jp.co.ponos.battlecats.MyActivity.lastNativeFinal;
                      } catch(IllegalStateException expected) { rejected=true; }
                      System.out.println("PC_AUTH_FOREIGN_REJECTED="+rejected);
                    } catch(java.io.IOException failure) { throw new AssertionError(failure); }
            '''
        else:
            auth_test = ''
        source['jp/kn/local/battlecats/Harness.java'] = source['jp/kn/local/battlecats/Harness.java'].replace('__PC_AUTH_EXERCISE__', auth_test).replace('__PC_AUTHORITY__',str(authority).lower())
        with tempfile.TemporaryDirectory(prefix="kn-backup-fallback-synthetic-") as tmp:
            root=Path(tmp)
            if authority:
                source['jp/kn/local/battlecats/KneekuraPcAgeAssets.java'] = (ROOT/
                    'bridge/java/KneekuraPcAgeAssets.java.in').read_text(encoding='utf-8').replace(
                        '__KNEEKURA_PACKAGE__', 'jp.kn.local.battlecats')
                # This HTTP harness never creates a WebView; the actual adapter
                # is compiled against Android in the real APK build.
                source['jp/kn/local/battlecats/KneekuraPcAgeWebView.java'] = '''package jp.kn.local.battlecats;
final class KneekuraPcAgeWebView {
 static void install(jp.co.ponos.battlecats.MyActivity activity,int handle,java.io.File files)
   throws ReflectiveOperationException {throw new AssertionError("no WebView in HTTP harness");}
}'''
                try:
                    from Crypto.PublicKey import RSA
                except ImportError:
                    self.skipTest('existing RSA tooling unavailable')
                import hashlib
                key = RSA.generate(4096)
                isolated = root / 'isolated'
                isolated.mkdir()
                (isolated / 'kneekura-local-signing-v1.pk8').write_bytes(key.export_key('DER', pkcs=8))
                source['jp/kn/local/battlecats/KneekuraPcBootAuthority.java'] = source[
                    'jp/kn/local/battlecats/KneekuraPcBootAuthority.java'].replace(
                        '__KNEEKURA_PC_BOOT_PUBLIC_KEY_SHA256__', hashlib.sha256(
                            key.public_key().export_key('DER')).hexdigest())
            sources=[]
            for name,code in source.items():
                file=root/"src"/name
                file.parent.mkdir(parents=True,exist_ok=True)
                file.write_text(code,encoding="utf-8")
                sources.append(str(file))
            out=root/"classes";out.mkdir()
            compiled=subprocess.run(
                [javac,"-source","8","-target","8","-d",str(out),*sources],
                capture_output=True,text=True,errors="replace",timeout=45)
            self.assertEqual(compiled.returncode,0,compiled.stderr)
            test=subprocess.run(
                [java,"-cp",str(out),
                 "-Dkn.local.dir="+str(root/"isolated"),"jp.kn.local.battlecats.Harness"],
                capture_output=True,text=True,errors="replace",timeout=25)
            self.assertEqual(test.returncode,0,test.stderr)
            observed=set(test.stdout.splitlines())
            if authority:
                self.assertIn('PC_AUTH_LOCAL=true', observed)
                self.assertIn('PC_AUTH_HEADER_STRING=true', observed)
                self.assertIn('PC_AUTH_FOREIGN_REJECTED=true', observed)
                for value in ('CLOCK_STREAM_ORDER=HDF','CLOCK_STREAM_CODE=200',
                              'CLOCK_STREAM_ERROR=false','CLOCK_STREAM_DIRECT=true'):
                    self.assertIn(value,observed)
            for exact in ('PC_LOCAL_CODE=' + ('200' if authority else '0'),
                          'PC_LOCAL_ERROR=' + ('false' if authority else 'true'),
                          'PC_LOCAL_ORIGIN=' + str(authority).lower(),
                          'PC_LOCAL_BODY=' + str(authority).lower(),
                          'PC_LOCAL_DIRECT=' + str(authority).lower()):
                self.assertIn(exact, observed)
            for exact in (
                "EXACT_REQUEST_ID=1",
                "original-local-pc-boot-operation-v1 create-account",
                "original-local-pc-boot-operation-v1 time",
                "original-local-pc-boot-operation-v1 other",
                "ORIGINAL_FALLBACK_COUNT=1",
                "ORIGINAL_FALLBACK_CODE=0",
                "ORIGINAL_FALLBACK_BODY={}",
                "ORIGINAL_FALLBACK_FINAL=true",
                "UNKNOWN_BLOCKED=true",
                "SYNTHETIC_TIMEOUT_11_ID="+('3' if authority else '2'),
                "FALLBACK_COUNT_AFTER_VARIANT="+('3' if authority else '2'),
                "NONFINITE_TIMEOUT_BLOCKED=true",
                "WRONG_BACKUP_PATH_BLOCKED=true",
                "NEGATIVE_TIMEOUT_BLOCKED=true",
                "OUT_OF_RANGE_TIMEOUT_BLOCKED=true",
                "UPPERCASE_HOST_BLOCKED=true",
                "original-local-backup-timeout-variant-v1 enqueued",
                "original-local-backup-timeout-variant-v1 returned",
                "original-local-backup-callback-v1 returned",
                "original-local-backup-timeout-class-v1 nonfinite",
                "original-local-backup-timeout-class-v1 nonpositive",
                "original-local-backup-timeout-class-v1 gt120",
                "original-local-backup-strict-envelope-v1 match",
                "original-local-backup-strict-envelope-v1 mismatch",
                "original-local-http-kind-v1 backup",
                "original-local-backup-shape-v1 mask=7fd",
                "ORIGINAL_SUPER_HTTP_CALLS=0",
                "LOCAL_ONLY_NETWORK_AVAILABLE=" + ("true" if authority else "false"),
                "ORIGINAL_SUPER_NETWORK_CHECK_CALLS=0",
                ("original-local-pc-authority-readiness-v1 ready" if authority else
                 "original-local-network-availability-v1 offline"),
                "original-local-backup-failure-fallback-v1 enqueued",
                "original-local-denied-http-v1",
                "original-local-http-kind-v1 publisher-other",
            ):
                self.assertIn(exact,observed)
            self.assertNotIn("https://service.ponosgames.com/unknown",test.stdout)
            self.assertNotIn("PRIVATE_VALUE", test.stdout)

if __name__=="__main__":
    unittest.main()
