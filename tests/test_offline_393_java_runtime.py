"""Execute the REAL offline Java importer on a local JVM with synthetic files.

Never use the real owner's APK/P12/SAVE/Android device. This isolates the
background import algorithm, all-393-precheck, checksum correctness and
existing SAVE preservation under a normal Java 17 compiler.
"""
from __future__ import annotations
from hashlib import md5
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "bridge/java/KneekuraOfflineAssetImporter.java.in"
PKG = "jp.kn.local.battlecats"

def code_rows() -> tuple[str,dict[str,bytes]]:
    assets = {f"S{i:03d}Server.list":f"ORIGINAL_FIXTURE_{i}".encode()
              for i in range(358)}
    for i in range(35):
        assets[f"download_{i}.tsv"] = (
            f"\\t{i+1}\\t"+ "0"*32 + "\\n").encode()
    assert len(assets) == 393
    metadata = '"' + "".join(
        f"{n}\\t{len(value)}\\t{md5(value).hexdigest()}\\n"
        for n,value in sorted(assets.items())
    ) + '"'
    return metadata,assets

class OriginalOfflineImporterJvmTests(unittest.TestCase):
    def test_java_background_import_is_fail_closed_and_save_safe(self):
        javac = shutil.which("javac")
        java = shutil.which("java")
        if not javac or not java:
            self.skipTest("Java SDK unavailable (real Android compilation is separately checked)")
        with tempfile.TemporaryDirectory(prefix="kn-real-java-393-") as temp:
            base = Path(temp)
            source = base / "src"
            build = base / "out"
            stage = base / "external/kneekura-original-jp1571-stage"
            internal = base / "internal"
            stage.mkdir(parents=True)
            internal.mkdir()
            metadata, assets = code_rows()
            for name,value in assets.items():
                if name == "S000Server.list":
                    continue
                (stage/name).write_bytes(value)
            existing_save = internal/"SAVE_DATA"
            existing_save.write_bytes(b"SYNTHETIC_UNTOUCHED_SAVE")
            replacement = (TEMPLATE.read_text(encoding="utf-8")
                           .replace("__KNEEKURA_PACKAGE__",PKG)
                           .replace("__KNEEKURA_OFFLINE_IMPORT_ENABLED__","true")
                           .replace("__KNEEKURA_OFFLINE_IMPORT_INDEX__",metadata))
            stubs = {
                "android/util/Log.java":"""
                    package android.util;
                    public class Log {
                        public static int i(String tag,String event) {
                            System.out.println(event);return 0;
                        }
                    }
                """,
                "jp/kn/local/battlecats/MyActivity.java":"""
                    package jp.kn.local.battlecats;
                    import java.io.File;
                    public class MyActivity {
                        File getExternalFilesDir(String type) {
                            return new File(System.getProperty("kn.external"));
                        }
                    }
                """,
                "jp/kn/local/battlecats/KneekuraOfflineAssetImporter.java":replacement,
                "jp/kn/local/battlecats/Harness.java":"""
                    package jp.kn.local.battlecats;
                    import java.io.File;
                    public class Harness {
                        public static void main(String[] args)throws Exception {
                            File root = new File(System.getProperty("kn.internal"));
                            KneekuraOfflineAssetImporter.schedule(
                                new MyActivity(),root);
                            File mark = new File(root,
                                ".kneekura-original-jp1571-393-import-complete-v1");
                            for(int i=0;i<70 && !mark.isFile();i++){
                                Thread.sleep(100);
                            }
                            Thread.sleep(200);
                            System.out.println("MARKER="+mark.isFile());
                        }
                    }
                """,
            }
            sources=[]
            for name,body in stubs.items():
                path=source/name
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(body,encoding="utf-8")
                sources.append(str(path))
            build.mkdir()
            c=subprocess.run(
                [javac,"-source","8","-target","8","-d",str(build),*sources],
                capture_output=True,text=True,errors="replace",timeout=45)
            self.assertEqual(c.returncode,0,c.stderr)

            def run() -> str:
                env=dict(os.environ)
                r=subprocess.run(
                    [java,"-cp",str(build),"-Dkn.external="+str(stage.parent),
                     "-Dkn.internal="+str(internal),PKG+".Harness"],
                    capture_output=True,text=True,errors="replace",timeout=40,env=env)
                self.assertEqual(r.returncode,0,r.stderr)
                return r.stdout

            # Missing one of the 393 means NONE may be copied.
            blocked=run()
            self.assertIn("MARKER=false",blocked)
            self.assertFalse((internal/"S001Server.list").exists())
            self.assertEqual(existing_save.read_bytes(),b"SYNTHETIC_UNTOUCHED_SAVE")
            # Complete staged source permits all pinned assets, not SAVE.
            (stage/"S000Server.list").write_bytes(assets["S000Server.list"])
            accepted=run()
            self.assertIn("MARKER=true",accepted)
            self.assertIn("original-local-import-v1 completed-393",accepted)
            self.assertTrue(all((internal/name).read_bytes()==value
                                for name,value in assets.items()))
            self.assertEqual(existing_save.read_bytes(),b"SYNTHETIC_UNTOUCHED_SAVE")
            # A cold restart will accept marker without rewriting assets/SAVE.
            self.assertIn("original-local-import-v1 already-complete",run())

if __name__=="__main__":
    unittest.main()
