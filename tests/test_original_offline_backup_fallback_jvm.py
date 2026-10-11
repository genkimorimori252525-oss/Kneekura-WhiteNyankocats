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
        javac=shutil.which("javac")
        java=shutil.which("java")
        if not javac or not java:
            self.skipTest("local JDK unavailable")
        rendered=render_bridge_source(
            (ROOT/"bridge/java/MyActivity.java.in").read_text(encoding="utf-8"),
            flavor="local-research",enabled=False,
            offline_393_import_enabled=True,
        )
        source={
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
                  public static boolean lastNativeFinal;
                  public int newHttpRequest(String method,String url,
                    float timeout,HashMap headers,ByteBuffer body,
                    String[] strings,boolean a,boolean b) {
                    superCalled++;
                    return -98;
                  }
                  public static void newResponse(int id,int code,String url,
                    String json,Object body,boolean end) {
                    nativeResponseCount++;
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
                    } catch(IllegalStateException expected){
                      unknownBlocked=true;
                    }
                    System.out.println("UNKNOWN_BLOCKED="+unknownBlocked);
                    boolean nonmatchingBackupBlocked=false;
                    try {
                      app.newHttpRequest(
                        "GET","https://nyanko-backups.ponosgames.com/?synthetic=1",
                        11.0f,new HashMap(),null,new String[0],false,false);
                    } catch(IllegalStateException expected) {
                      nonmatchingBackupBlocked=true;
                    }
                    System.out.println("NONMATCH_BACKUP_BLOCKED="+nonmatchingBackupBlocked);
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
        with tempfile.TemporaryDirectory(prefix="kn-backup-fallback-synthetic-") as tmp:
            root=Path(tmp)
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
            for exact in (
                "EXACT_REQUEST_ID=1",
                "ORIGINAL_FALLBACK_COUNT=1",
                "ORIGINAL_FALLBACK_CODE=0",
                "ORIGINAL_FALLBACK_BODY={}",
                "ORIGINAL_FALLBACK_FINAL=true",
                "UNKNOWN_BLOCKED=true",
                "NONMATCH_BACKUP_BLOCKED=true",
                "original-local-http-kind-v1 backup",
                "original-local-backup-shape-v1 mask=7fd",
                "ORIGINAL_SUPER_HTTP_CALLS=0",
                "LOCAL_ONLY_NETWORK_AVAILABLE=false",
                "ORIGINAL_SUPER_NETWORK_CHECK_CALLS=0",
                "original-local-network-availability-v1 offline",
                "original-local-backup-failure-fallback-v1 completed",
                "original-local-denied-http-v1",
                "original-local-http-kind-v1 publisher-other",
            ):
                self.assertIn(exact,observed)
            self.assertNotIn("https://service.ponosgames.com/unknown",test.stdout)

if __name__=="__main__":
    unittest.main()
