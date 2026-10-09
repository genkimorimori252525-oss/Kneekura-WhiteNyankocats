from pathlib import Path
import unittest

from tools.base_mod.inject_java_http_bridge import (
    BRIDGE_DEX_ENTRY,
    render_bridge_source,
    ORIGINAL_LAUNCHER,
)
from tools.base_mod.package_flavor import FLAVOR_PACKAGES


ROOT = Path(__file__).resolve().parents[1]


class StaticHttpBridgeTests(unittest.TestCase):
    def test_bridge_launchers_preserve_original_length(self) -> None:
        for package in FLAVOR_PACKAGES.values():
            launcher = package + ".MyActivity"
            self.assertEqual(
                len(launcher.encode("utf-8")),
                len(ORIGINAL_LAUNCHER.encode("utf-8")),
            )

    def test_bridge_template_is_exact_and_fail_closed(self) -> None:
        source = (ROOT / "bridge/java/MyActivity.java.in").read_text(
            encoding="utf-8"
        )
        self.assertIn("extends jp.co.ponos.battlecats.MyActivity", source)
        self.assertIn("ENABLE_BACKUP_OFFLINE_REPLAY", source)
        self.assertIn("DEBUG_RESEARCH_LOG", source)
        self.assertIn("USE_EXTERNAL_FILES_DIR", source)
        self.assertIn("super.getExternalFilesDir(null)", source)
        self.assertIn("return super.getFilesDir()", source)
        self.assertIn("KNEEKURA_STATIC_HTTP", source)
        self.assertIn('"GET".equals(method)', source)
        self.assertIn('BACKUP_HOST = "nyanko-backups.ponosgames.com"', source)
        self.assertIn('BACKUP_PATH = "/"', source)
        self.assertIn("parsed.getQuery() != null", source)
        self.assertIn("Float.compare(timeout, 10.0f)", source)
        self.assertIn("headers == null || !headers.isEmpty()", source)
        self.assertIn("body != null", source)
        self.assertIn("strings == null || strings.length != 0", source)
        self.assertIn("flag1 || flag2", source)
        self.assertGreaterEqual(source.count("super.newHttpRequest("), 2)

    def test_bridge_replays_only_observed_offline_shape(self) -> None:
        source = (ROOT / "bridge/java/MyActivity.java.in").read_text(
            encoding="utf-8"
        )
        self.assertIn('getDeclaredField("mNextRequestHandle")', source)
        self.assertIn('getDeclaredField("mRequestHandles")', source)
        self.assertIn('getDeclaredField("mGLView")', source)
        self.assertIn('Class.forName("a32")', source)
        self.assertIn("requestMap.put(Integer.valueOf(requestId), request)", source)
        self.assertIn("view.queueEvent(new Runnable()", source)
        self.assertIn("MyActivity.newResponse(", source)
        self.assertIn('requestUrl,\n                            "{}",\n                            null,\n                            true', source)

    def test_original_game_private_root_flag_defaults_off_in_all_flavors(self) -> None:
        original = (ROOT / "bridge/java/MyActivity.java.in").read_text(encoding="utf-8")
        for flavor in ("research", "personal", "practice"):
            with self.subTest(flavor=flavor):
                rendered = render_bridge_source(
                    original, flavor=flavor, enabled=False
                )
                self.assertIn(
                    "private static final boolean ISOLATE_ORIGINAL_NATIVE_FILES_DIR =\n"
                    "            false;", rendered
                )
                self.assertIn("return super.getFilesDir()", rendered)
                self.assertNotIn("__KNEEKURA_", rendered)
                self.assertIn("kneekura-native-jp15-7-1", rendered)

    def test_private_native_original_game_root_requires_explicit_research(self) -> None:
        original = (ROOT / "bridge/java/MyActivity.java.in").read_text(encoding="utf-8")
        research = render_bridge_source(
            original, flavor="research", enabled=False,
            isolate_original_native_files_dir=True,
        )
        self.assertIn(
            "private static final boolean ISOLATE_ORIGINAL_NATIVE_FILES_DIR =\n"
            "            true;", research
        )
        self.assertIn("new File(base, ORIGINAL_NATIVE_FILES_LEAF)", research)
        self.assertIn("base.getCanonicalPath() + File.separator", research)
        self.assertIn("directory.getCanonicalPath().startsWith(trusted)", research)
        self.assertIn("return directory;", research)
        self.assertNotIn("originalNativeFilesDirectory", research)
        self.assertIn("original native private save root changed during creation", research)
        self.assertIn("throw new IllegalStateException", research)
        self.assertIn("getCanonicalPath()", research)
        self.assertNotIn("mkdirs() || !directory.isDirectory()", original.split(
            "if (!USE_EXTERNAL_FILES_DIR)", 1)[-1])
        for invalid_flavor in ("personal", "practice"):
            with self.assertRaisesRegex(
                    ValueError, "requires research flavor"):
                render_bridge_source(
                    original, flavor=invalid_flavor, enabled=False,
                    isolate_original_native_files_dir=True,
                )
        with self.assertRaisesRegex(ValueError, "conflicts with external files"):
            render_bridge_source(
                original, flavor="research", enabled=False,
                use_external_files_dir=True,
                isolate_original_native_files_dir=True,
            )
        with self.assertRaisesRegex(ValueError, "unknown flavor"):
            render_bridge_source(original, flavor="unknown", enabled=False)
        with self.assertRaisesRegex(ValueError, "unresolved placeholders"):
            render_bridge_source(
                original + "__KNEEKURA_UNRECOGNIZED__", flavor="research", enabled=False,
            )

    def test_native_getfilesdir_is_not_full_offline_or_authoritative_save(self) -> None:
        original = (ROOT / "bridge/java/MyActivity.java.in").read_text(encoding="utf-8")
        injector = (ROOT / "tools/base_mod/inject_java_http_bridge.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("the original native app may expect additional local assets", original)
        self.assertIn("nor implements a network-free game", original)
        self.assertIn("original native private save root unavailable", original)
        self.assertIn('isolate_original_native_files_dir: bool = False', injector)
        self.assertIn('"original_native_gameplay_persistence_verified": False', injector)
        self.assertIn('"network_egress_guarantee": "NOT_VERIFIED"', injector)
        self.assertIn("--research-isolate-original-native-files-dir", injector)


    def test_original_activity_java_compiles_and_native_root_is_isolated(self) -> None:
        """Exercise the actual rendered original-game Activity override on a JVM.

        Only Android API compile stubs are faked; actual Java getFilesDir
        implementation, directory creation and save separation are executed.
        This is NOT the original Android runtime / native game persistence.
        """
        import shutil
        import subprocess
        import tempfile

        javac, java = shutil.which("javac"), shutil.which("java")
        if not (javac and java):
            self.skipTest("Java compiler/runtime unavailable")
        original = (ROOT / "bridge/java/MyActivity.java.in").read_text(encoding="utf-8")
        stubs = {
            "android/opengl/GLSurfaceView.java": (
                "package android.opengl; public class GLSurfaceView {"
                "public void queueEvent(Runnable task) {task.run();}}"
            ),
            "android/util/Log.java": (
                "package android.util; public class Log {"
                "public static int i(String tag,String value) {return 0;}}"
            ),
            "jp/co/ponos/battlecats/MyActivity.java": """
                package jp.co.ponos.battlecats;
                import java.io.File;
                import java.net.URL;
                import java.nio.ByteBuffer;
                import java.util.HashMap;
                public class MyActivity {
                    public File getFilesDir() {return new File(System.getProperty("bc.baseDir"));}
                    public File getExternalFilesDir(String type) {
                        return new File(System.getProperty("bc.externalDir", "no-external-folder"));
                    }
                    public int newHttpRequest(
                        String method, String url, float timeout, HashMap headers,
                        ByteBuffer body, String[] values, boolean b1, boolean b2
                    ) {return 0;}
                    public static void newResponse(
                        int id, int code, String url, String body,
                        Object bytes, boolean finalResponse
                    ) {}
                }
            """,
            "Harness.java": """
                import jp.kn.trace.battlecats.MyActivity;
                public class Harness {
                    public static void main(String[] args) throws Exception {
                        try {
                            System.out.println(new MyActivity().getFilesDir().getCanonicalPath());
                        } catch (IllegalStateException error) {
                            System.out.println("BLOCKED");
                        }
                    }
                }
            """,
        }
        with tempfile.TemporaryDirectory(prefix="kneekura-native-io-test-") as temp:
            temp_path = Path(temp)
            files_root = temp_path / "original-root"
            files_root.mkdir()
            original_save = files_root / "SAVE_DATA"
            original_save.write_bytes(b"UNTOUCHED_OWNER_ORIGINAL_SAVE_FIXTURE")
            external = temp_path / "external"
            external.mkdir()
            for isolated in (False, True):
                with self.subTest(isolated=isolated):
                    name = "isolated" if isolated else "default"
                    root = temp_path / name
                    src = root / "src"
                    out = root / "out"
                    out.mkdir(parents=True)
                    material = dict(stubs)
                    material["jp/kn/trace/battlecats/MyActivity.java"] = (
                        render_bridge_source(
                            original, flavor="research", enabled=False,
                            isolate_original_native_files_dir=isolated,
                        )
                    )
                    java_sources = []
                    for filename, code in material.items():
                        source_file = src / filename
                        source_file.parent.mkdir(parents=True, exist_ok=True)
                        source_file.write_text(code, encoding="utf-8")
                        java_sources.append(str(source_file))
                    compiled = subprocess.run(
                        [javac, "-source", "8", "-target", "8", "-d", str(out),
                         *java_sources],
                        capture_output=True, text=True, check=False,
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    command = [
                        java, "-cp", str(out), "-Dbc.baseDir=" + str(files_root),
                        "-Dbc.externalDir=" + str(external), "Harness"
                    ]
                    one = subprocess.run(command, capture_output=True, text=True)
                    two = subprocess.run(command, capture_output=True, text=True)
                    self.assertEqual(one.returncode, 0, one.stderr)
                    self.assertEqual(one.stdout, two.stdout)
                    expected = (files_root / "kneekura-native-jp15-7-1"
                                if isolated else files_root)
                    self.assertEqual(one.stdout.strip(), str(expected.resolve()))
                    self.assertTrue(expected.is_dir())
                    if isolated:
                        self.assertFalse((expected / "SAVE_DATA").exists())
                    self.assertEqual(
                        original_save.read_bytes(),
                        b"UNTOUCHED_OWNER_ORIGINAL_SAVE_FIXTURE"
                    )
                    if isolated and hasattr(__import__("os"), "symlink"):
                        # Symlink change must not redirect the native root out
                        # of its app-private parent on the next call.
                        import os
                        isolated_root = files_root / "kneekura-native-jp15-7-1"
                        import shutil as _shutil
                        _shutil.rmtree(isolated_root)
                        outside = temp_path / "outside"
                        outside.mkdir(exist_ok=True)
                        try:
                            os.symlink(outside, isolated_root)
                        except OSError:
                            pass  # symlink privileges may be absent on Windows
                        else:
                            blocked = subprocess.run(
                                command, capture_output=True, text=True
                            )
                            self.assertEqual(blocked.returncode, 0, blocked.stderr)
                            self.assertEqual(blocked.stdout.strip(), "BLOCKED")
                            isolated_root.unlink()

    def test_bridge_is_additional_dex_not_original_method_rewrite(self) -> None:
        injector = (
            ROOT / "tools/base_mod/inject_java_http_bridge.py"
        ).read_text(encoding="utf-8")
        self.assertEqual(BRIDGE_DEX_ENTRY, "classes5.dex")
        self.assertIn("patch_equal_length_strings", injector)
        self.assertIn('"true" if flavor in ("research", "local-research") else "false"', injector)
        self.assertIn("{ORIGINAL_LAUNCHER: launcher}", injector)
        self.assertIn("use_external_files_dir: bool = False", injector)
        self.assertIn("__KNEEKURA_USE_EXTERNAL_FILES_DIR__", injector)
        self.assertNotIn("patch_exact_dex_string(", injector)

    def test_local_research_flavor_preserves_original_native_file_root(self) -> None:
        template = (ROOT / "bridge/java/MyActivity.java.in").read_text(encoding="utf-8")
        self.assertEqual(FLAVOR_PACKAGES["local-research"], "jp.kn.local.battlecats")
        rendered = render_bridge_source(
            template, flavor="local-research", enabled=False
        )
        self.assertIn(
            "private static final boolean LOCAL_RESEARCH_FRESH_ROOT =\n            true;",
            rendered,
        )
        self.assertIn(
            "private static final boolean LOCAL_RESEARCH_DENY_HTTP =\n            true;",
            rendered,
        )
        self.assertIn(
            "private static final boolean ISOLATE_ORIGINAL_NATIVE_FILES_DIR =\n            false;",
            rendered,
        )
        self.assertIn("return root;", rendered)
        self.assertIn("unowned prior SAVE_DATA in local research package", rendered)
        self.assertIn("original local research HTTP disabled", rendered)
        self.assertNotIn("__KNEEKURA_", rendered)
        for invalid in (
            {"enabled": True},
            {"use_external_files_dir": True},
            {"isolate_original_native_files_dir": True},
        ):
            with self.subTest(kwargs=invalid):
                with self.assertRaisesRegex(ValueError, "must keep original files root"):
                    render_bridge_source(
                        template, flavor="local-research", enabled=False, **invalid
                    ) if "enabled" not in invalid else render_bridge_source(
                        template, flavor="local-research", **invalid
                    )

    def test_local_research_java_executes_virgin_and_rejects_saved_data_and_http(self) -> None:
        """Java executes actual ORIGINAL MyActivity subclass, not a fake cat UI."""
        import shutil
        import subprocess
        import tempfile
        import os

        javac, java = shutil.which("javac"), shutil.which("java")
        if not (javac and java):
            self.skipTest("Java compiler/runtime unavailable")
        original = (ROOT / "bridge/java/MyActivity.java.in").read_text(encoding="utf-8")
        source = render_bridge_source(
            original, flavor="local-research", enabled=False
        )
        stubs = {
            "android/opengl/GLSurfaceView.java": (
                "package android.opengl; public class GLSurfaceView {"
                "public void queueEvent(Runnable task) {task.run();}}"
            ),
            "android/util/Log.java": (
                "package android.util; public class Log {"
                "public static int i(String tag,String message) {"
                "System.out.println(\"TRACE=\"+message); return 0;}}"
            ),
            "jp/co/ponos/battlecats/MyActivity.java": """
                package jp.co.ponos.battlecats;
                import java.io.File;
                import java.nio.ByteBuffer;
                import java.util.HashMap;
                public class MyActivity {
                    public File getFilesDir() {
                        return new File(System.getProperty("bc.localDir"));
                    }
                    public File getExternalFilesDir(String type) {
                        throw new AssertionError("external files root must never run");
                    }
                    public int newHttpRequest(
                        String method, String url, float timeout,
                        HashMap headers, ByteBuffer body, String[] values,
                        boolean first, boolean second) {
                        throw new AssertionError("online super HTTP must never run");
                    }
                    public static void newResponse(
                        int id, int code, String url, String body,
                        Object data, boolean done) {}
                }
            """,
            "jp/kn/local/battlecats/MyActivity.java": source,
            "Harness.java": """
                import jp.kn.local.battlecats.MyActivity;
                import java.util.HashMap;
                public class Harness {
                    public static void main(String[] args) throws Exception {
                        MyActivity activity = new MyActivity();
                        try {
                            System.out.println("ROOT=" + activity.getFilesDir().getCanonicalPath());
                        } catch (IllegalStateException rejected) {
                            System.out.println("ROOT=BLOCKED");
                        }
                        try {
                            activity.newHttpRequest(
                                "GET", "https://example.invalid", 10.0f,
                                new HashMap(), null, new String[0], false, false
                            );
                            System.out.println("HTTP=LEAK");
                        } catch (IllegalStateException blocked) {
                            System.out.println("HTTP=BLOCKED");
                        }
                    }
                }
            """,
        }
        with tempfile.TemporaryDirectory(prefix="kneekura-virgin-original-") as tmp:
            base = Path(tmp)
            compile_root = base / "src"
            class_dir = base / "classes"
            class_dir.mkdir()
            sources = []
            for filename, body in stubs.items():
                path = compile_root / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(body, encoding="utf-8")
                sources.append(str(path))
            result = subprocess.run(
                [javac, "-source", "8", "-target", "8", "-d", str(class_dir),
                 *sources], text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            official_root = base / "ponos-app-data"
            official_root.mkdir()
            (official_root / "SAVE_DATA").write_bytes(b"PROTECTED_ORIGINAL")
            local_root = base / "new-local-original-app"
            local_root.mkdir()

            def run_host():
                return subprocess.run(
                    [java, "-cp", str(class_dir),
                     "-Dbc.localDir=" + str(local_root), "Harness"],
                    text=True, capture_output=True,
                )

            first = run_host()
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertIn("ROOT=" + str(local_root.resolve()), first.stdout)
            self.assertIn("HTTP=BLOCKED", first.stdout)
            self.assertIn(
                "TRACE=original-save-presence-v1 SAVE_DATA=absent"
                " SAVE_DATA4=absent SAVE_DATA8=absent", first.stdout
            )
            self.assertNotIn("PROTECTED_ORIGINAL", first.stdout)
            self.assertIn(
                "TRACE=original-download-tsv-loose-v1"
                " present=0 absent=35 unsafe=0", first.stdout
            )
            marker = local_root / ".kneekura-virgin-local-jp15-7-1"
            self.assertTrue(marker.is_file())
            self.assertEqual(marker.stat().st_size, 0)
            self.assertFalse((local_root / "SAVE_DATA").exists())
            self.assertEqual((official_root / "SAVE_DATA").read_bytes(),
                             b"PROTECTED_ORIGINAL")

            (local_root / "SAVE_DATA").write_bytes(b"NEW_LOCAL_GAME_SAVE_FIXTURE")
            (local_root / "download_0.tsv").write_bytes(b"OWNED_LOCAL_TEST_TSV")
            resumed = run_host()
            self.assertIn("ROOT=" + str(local_root.resolve()), resumed.stdout)
            self.assertIn(
                "TRACE=original-save-presence-v1 SAVE_DATA=present:"
                + str(len(b"NEW_LOCAL_GAME_SAVE_FIXTURE")), resumed.stdout
            )
            self.assertNotIn("NEW_LOCAL_GAME_SAVE_FIXTURE", resumed.stdout)
            self.assertIn(
                "TRACE=original-download-tsv-loose-v1"
                " present=1 absent=34 unsafe=0", resumed.stdout
            )
            self.assertNotIn("OWNED_LOCAL_TEST_TSV", resumed.stdout)
            self.assertEqual((local_root / "SAVE_DATA").read_bytes(),
                             b"NEW_LOCAL_GAME_SAVE_FIXTURE")
            if hasattr(os, "symlink"):
                external_tsv = base / "not-app-private-download-tsv"
                external_tsv.write_bytes(b"PRIVATE_EXTERNAL_TSV_CONTENT")
                try:
                    os.symlink(external_tsv, local_root / "download_1.tsv")
                except OSError:
                    pass
                else:
                    tsv_scan = run_host()
                    self.assertIn(
                        "TRACE=original-download-tsv-loose-v1"
                        " present=1 absent=33 unsafe=1", tsv_scan.stdout
                    )
                    self.assertNotIn("PRIVATE_EXTERNAL_TSV_CONTENT", tsv_scan.stdout)
                    (local_root / "download_1.tsv").unlink()
                (local_root / "SAVE_DATA").unlink()
                outside_file = base / "out-of-app-data"
                outside_file.write_bytes(b"PRIVATE_EXTERNAL_FILE")
                try:
                    os.symlink(outside_file, local_root / "SAVE_DATA")
                except OSError:
                    pass
                else:
                    escaped = run_host()
                    self.assertIn("SAVE_DATA=unsafe", escaped.stdout)
                    self.assertNotIn("PRIVATE_EXTERNAL_FILE", escaped.stdout)
                    (local_root / "SAVE_DATA").unlink()
            else:
                (local_root / "SAVE_DATA").unlink()
            # The provenance guard must refuse a pre-existing local SAVE
            # when its origin marker is missing. Restore a LOCAL fixture
            # after the symlink-escape test before removing that marker.
            local_save = local_root / "SAVE_DATA"
            if local_save.is_symlink():
                local_save.unlink()
            local_save.write_bytes(b"NEW_LOCAL_GAME_SAVE_FIXTURE")
            marker.unlink()
            refused = run_host()
            self.assertIn("ROOT=BLOCKED", refused.stdout)
            self.assertFalse(marker.exists())
            if (local_root / "SAVE_DATA").exists():
                (local_root / "SAVE_DATA").unlink()
            for name in ("SAVE_DATA4", "SAVE_DATA8"):
                with self.subTest(name=name):
                    (local_root / name).write_bytes(b"UNOWNED")
                    refused = run_host()
                    self.assertIn("ROOT=BLOCKED", refused.stdout)
                    (local_root / name).unlink()
            marker.write_bytes(b"CORRUPTED")
            corrupted = run_host()
            self.assertIn("ROOT=BLOCKED", corrupted.stdout)
            marker.unlink()
            if hasattr(os, "symlink"):
                outside = base / "outside"
                outside.write_bytes(b"SYMLINK_MARKER")
                try:
                    os.symlink(outside, marker)
                except OSError:
                    pass
                else:
                    refused = run_host()
                    self.assertIn("ROOT=BLOCKED", refused.stdout)
                    marker.unlink()

    def test_local_research_original_tsv_observer_is_single_pass_and_read_only(self):
        original = (ROOT / "bridge/java/MyActivity.java.in").read_text(
            encoding="utf-8"
        )
        self.assertIn("private static boolean localDownloadTsvProbeCompleted", original)
        self.assertIn("if (localDownloadTsvProbeCompleted)", original)
        self.assertIn('new File(root, "download_" + index + ".tsv")', original)
        self.assertIn("for (int index = 0; index < 35; index++)", original)
        self.assertIn("candidate.getCanonicalPath().startsWith(trusted)", original)
        self.assertIn("original-download-tsv-loose-v1", original)
        self.assertIn("localDownloadTsvProbeCompleted = true", original)
        self.assertIn("probeLocalDownloadBatchTsvFiles(root);", original)
        self.assertNotIn("FileInputStream", original)
        self.assertNotIn("FileOutputStream", original)

    def test_local_research_builder_rejects_networked_or_legacy_save_modes_before_io(self):
        from tools.base_mod.build_owned_static_http_bridge import (
            build_owned_static_http_bridge,
        )
        from tools.base_mod.inject_java_http_bridge import inject_bridge_split_set
        from tools.base_mod.verify_static_http_bridge import verify_static_http_bridge

        for no_internet, subdir, backup in (
            (False, False, False),
            (True, True, False),
            (True, False, True),
        ):
            with self.subTest(no_internet=no_internet, subdir=subdir, backup=backup):
                with self.assertRaisesRegex(
                        ValueError, "local research requires no-INTERNET"):
                    build_owned_static_http_bridge(
                        Path("missing-original-source.zip"),
                        flavor="local-research",
                        shim=Path("missing-shim"),
                        keystore=Path("missing-signing-key"),
                        alias="not-used", storepass="not-used",
                        output_dir=Path("must-not-create"),
                        research_isolate_original_native_files_dir=subdir,
                        research_deny_internet=no_internet,
                        enable_backup_offline_replay=backup,
                    )
        with self.assertRaisesRegex(ValueError, "must remove Android INTERNET"):
            inject_bridge_split_set(
                Path("must-not-read"), Path("must-not-write"),
                flavor="local-research",
                bridge_dex_path=Path("missing.dex"),
            )
        with self.assertRaisesRegex(ValueError, "must omit INTERNET"):
            verify_static_http_bridge(
                Path("must-not-read"), Path("must-not-write"),
                flavor="local-research", replay_enabled=False,
            )

    def test_original_owner_builder_rejects_nonresearch_private_save_mode(self) -> None:
        from tools.base_mod.build_owned_static_http_bridge import (
            build_owned_static_http_bridge,
        )
        for flavor in ("personal", "practice"):
            with self.subTest(flavor=flavor):
                with self.assertRaisesRegex(ValueError, "requires research flavor"):
                    build_owned_static_http_bridge(
                        Path("not-read-export.zip"),
                        flavor=flavor,
                        shim=Path("not-read-shim.so"),
                        keystore=Path("not-read-keystore"),
                        alias="never-used",
                        storepass="unused",
                        output_dir=Path("not-created"),
                        research_isolate_original_native_files_dir=True,
                    )

    def test_research_no_internet_original_host_requires_private_root(self) -> None:
        from tools.base_mod.build_owned_static_http_bridge import (
            build_owned_static_http_bridge,
        )
        from tools.base_mod.inject_java_http_bridge import inject_bridge_split_set
        from tools.base_mod.verify_static_http_bridge import verify_static_http_bridge

        for flavor, isolated in (
            ("personal", True), ("practice", True), ("research", False)
        ):
            with self.subTest(flavor=flavor, isolated=isolated):
                with self.assertRaisesRegex(
                        ValueError,
                        "requires research flavor AND private file root"):
                    build_owned_static_http_bridge(
                        Path("must-not-read-user-source.zip"),
                        flavor=flavor,
                        shim=Path("must-not-read-shim.so"),
                        keystore=Path("must-not-read-signing-key"),
                        alias="not-used",
                        storepass="not-used",
                        output_dir=Path("must-not-create"),
                        research_isolate_original_native_files_dir=isolated,
                        research_deny_internet=True,
                    )
        with self.assertRaisesRegex(ValueError, "research flavor only"):
            inject_bridge_split_set(
                Path("must-not-read"), Path("must-not-write"),
                flavor="personal", bridge_dex_path=Path("must-not-read.dex"),
                research_deny_internet=True,
            )
        with self.assertRaisesRegex(ValueError, "requires research flavor"):
            verify_static_http_bridge(
                Path("must-not-read"), Path("must-not-write"),
                flavor="personal", replay_enabled=False,
                research_deny_internet=True,
            )

    def test_original_host_network_permission_gate_is_not_release_claim(self) -> None:
        injector = (
            ROOT / "tools/base_mod/inject_java_http_bridge.py"
        ).read_text(encoding="utf-8")
        builder = (
            ROOT / "tools/base_mod/build_owned_static_http_bridge.py"
        ).read_text(encoding="utf-8")
        verifier = (
            ROOT / "tools/base_mod/verify_static_http_bridge.py"
        ).read_text(encoding="utf-8")
        self.assertIn("--research-no-internet-permission", injector)
        self.assertIn("remove_exact_uses_permission(", injector)
        self.assertIn("manifest_components(patched_manifest)", injector)
        self.assertIn("research_deny_internet: bool = False", builder)
        self.assertIn("research_deny_internet=research_deny_internet", builder)
        self.assertIn("research_deny_internet: bool = False", verifier)
        self.assertIn('"original_game_zero_egress_proven": False', verifier)
        self.assertIn('"original_independent_local_save_verified": False', builder)
        self.assertIn('"original_zero_network_verified": False', builder)

    def test_static_builder_preserves_original_native_extraction(self) -> None:
        source = (
            ROOT / "tools/base_mod/build_owned_static_http_bridge.py"
        ).read_text(encoding="utf-8")
        self.assertIn("research_native_extraction=False", source)
        self.assertIn("research_isolate_original_native_files_dir: bool = False", source)
        self.assertIn(
            "isolate_original_native_files_dir=research_isolate_original_native_files_dir",
            source,
        )
        self.assertIn('"original_independent_local_save_verified": False', source)
        self.assertIn('"original_zero_network_verified": False', source)
        self.assertIn("--research-isolate-original-native-files-dir", source)

    def test_compile_stub_is_never_product_logic(self) -> None:
        stub = (
            ROOT / "bridge/java/stub/jp/co/ponos/battlecats/MyActivity.java"
        ).read_text(encoding="utf-8")
        self.assertIn("Compile-only ABI stub", stub)
        self.assertIn("throw new AssertionError", stub)
        self.assertIn("static native void newResponse", stub)


if __name__ == "__main__":
    unittest.main()
