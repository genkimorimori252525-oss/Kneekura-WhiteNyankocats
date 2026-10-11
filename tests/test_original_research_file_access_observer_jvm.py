"""Run the actual original research Java file-access watcher on a fake JVM.

It only receives synthetic Android file events and never reads any real
Battle Cats asset, player SAVE, account or Android process.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tools.base_mod.inject_java_http_bridge import render_bridge_source

ROOT = Path(__file__).resolve().parents[1]

class OriginalResearchFileAccessObserverTests(unittest.TestCase):
    def test_owned_resource_access_events_emit_only_fixed_kinds_once(self):
        javac, java = shutil.which("javac"), shutil.which("java")
        if not javac or not java:
            self.skipTest("Java SDK unavailable")
        rendered = render_bridge_source(
            (ROOT / "bridge/java/MyActivity.java.in").read_text(encoding="utf-8"),
            flavor="local-research", enabled=False,
            offline_393_import_enabled=True,
        )
        stubs = {
            "android/opengl/GLSurfaceView.java": """
                package android.opengl;
                public class GLSurfaceView {
                    public void queueEvent(Runnable runnable){runnable.run();}
                }
            """,
            "android/os/FileObserver.java": """
                package android.os;
                public abstract class FileObserver {
                    public static final int CREATE=256, CLOSE_WRITE=8,
                        MOVED_TO=128, DELETE=512, OPEN=32, ACCESS=1;
                    public static FileObserver latest;
                    public FileObserver(String path,int flags){latest=this;}
                    public void startWatching(){}
                    public abstract void onEvent(int event,String filename);
                    public static void emit(int event,String filename){
                        if(latest!=null)latest.onEvent(event,filename);
                    }
                }
            """,
            "android/util/Log.java": """
                package android.util;
                public class Log {
                    public static int i(String tag,String message){
                        if(message.startsWith("original-local-file-access-v1 ")){
                            System.out.println(message);
                        }
                        return 0;
                    }
                }
            """,
            "jp/co/ponos/battlecats/MyActivity.java": """
                package jp.co.ponos.battlecats;
                import java.io.File;
                import java.nio.ByteBuffer;
                import java.util.HashMap;
                public class MyActivity {
                    public File getFilesDir(){
                        return new File(System.getProperty("kn.originalRoot"));
                    }
                    public File getExternalFilesDir(String type){return null;}
                    public int newHttpRequest(String m,String url,float t,
                      HashMap h,ByteBuffer b,String[] x,boolean a,boolean c){return -1;}
                    public boolean isNetworkAvailable(){return true;}
                    public static void newResponse(int id,int status,String url,
                      String headers,Object body,boolean end){}
                }
            """,
            "jp/kn/local/battlecats/MyActivity.java": rendered,
            "jp/kn/local/battlecats/Harness.java": """
                package jp.kn.local.battlecats;
                import android.os.FileObserver;
                import java.io.File;
                public class Harness {
                    public static void main(String[] args)throws Exception{
                        new MyActivity().getFilesDir();
                        FileObserver.emit(FileObserver.OPEN,"download_0.tsv");
                        FileObserver.emit(FileObserver.ACCESS,"download_34.tsv");
                        FileObserver.emit(FileObserver.OPEN,"AServer.list");
                        FileObserver.emit(FileObserver.ACCESS,"BServer.pack");
                        FileObserver.emit(FileObserver.OPEN,"BGM_1.ogg");
                        FileObserver.emit(FileObserver.OPEN,"SAVE_DATA");
                        FileObserver.emit(FileObserver.ACCESS,"SAVE_DATA8");
                        FileObserver.emit(FileObserver.OPEN,"../SAVE_DATA");
                        FileObserver.emit(FileObserver.OPEN,"unknown-account.dat");
                        FileObserver.emit(FileObserver.OPEN,"AServer.list");
                        System.out.println("WITNESS_DONE");
                    }
                }
            """,
        }
        with tempfile.TemporaryDirectory(prefix="kn-original-resource-events-") as tmp:
            root=Path(tmp)
            src=root/"src"
            classes=root/"classes"
            classes.mkdir()
            paths=[]
            for name,body in stubs.items():
                f=src/name
                f.parent.mkdir(parents=True,exist_ok=True)
                f.write_text(body,encoding="utf-8")
                paths.append(str(f))
            comp=subprocess.run(
                [javac,"-source","8","-target","8","-d",str(classes),*paths],
                capture_output=True,text=True,errors="replace",timeout=45)
            self.assertEqual(comp.returncode,0,comp.stderr)
            isolated=root/"isolated"
            isolated.mkdir()
            ran=subprocess.run(
                [java,"-cp",str(classes),"-Dkn.originalRoot="+str(isolated),
                 "jp.kn.local.battlecats.Harness"],
                capture_output=True,text=True,errors="replace",timeout=30)
            self.assertEqual(ran.returncode,0,ran.stderr)
            lines=ran.stdout.splitlines()
            for kind in ("watching","download-tsv","server-list","server-pack","media"):
                self.assertEqual(
                    lines.count("original-local-file-access-v1 "+kind),1)
            self.assertIn("WITNESS_DONE",lines)
            for private in ("SAVE_DATA", "BGM_1.ogg", "../", "unknown-account"):
                self.assertNotIn(private,ran.stdout)
            self.assertEqual(sorted(x for x in lines
                                    if x.startswith("original-local-file-access-v1 ")),
                             sorted({"original-local-file-access-v1 "+x for x in
                                     ("watching","download-tsv","server-list",
                                      "server-pack","media")}))
            self.assertFalse((isolated/"SAVE_DATA").exists())


if __name__ == "__main__":
    unittest.main()
