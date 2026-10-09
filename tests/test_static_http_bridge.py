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
        self.assertIn("originalNativeFilesDirectory = directory", research)
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
        self.assertIn("does not implement a network-free game", original)
        self.assertIn("original native private save root unavailable", original)
        self.assertIn('isolate_original_native_files_dir: bool = False', injector)
        self.assertIn('"original_native_gameplay_persistence_verified": False', injector)
        self.assertIn('"network_egress_guarantee": "NOT_VERIFIED"', injector)
        self.assertIn("--research-isolate-original-native-files-dir", injector)

    def test_bridge_is_additional_dex_not_original_method_rewrite(self) -> None:
        injector = (
            ROOT / "tools/base_mod/inject_java_http_bridge.py"
        ).read_text(encoding="utf-8")
        self.assertEqual(BRIDGE_DEX_ENTRY, "classes5.dex")
        self.assertIn("patch_equal_length_strings", injector)
        self.assertIn('"true" if flavor == "research" else "false"', injector)
        self.assertIn("{ORIGINAL_LAUNCHER: launcher}", injector)
        self.assertIn("use_external_files_dir: bool = False", injector)
        self.assertIn("__KNEEKURA_USE_EXTERNAL_FILES_DIR__", injector)
        self.assertNotIn("patch_exact_dex_string(", injector)

    def test_static_builder_preserves_original_native_extraction(self) -> None:
        source = (
            ROOT / "tools/base_mod/build_owned_static_http_bridge.py"
        ).read_text(encoding="utf-8")
        self.assertIn("research_native_extraction=False", source)

    def test_compile_stub_is_never_product_logic(self) -> None:
        stub = (
            ROOT / "bridge/java/stub/jp/co/ponos/battlecats/MyActivity.java"
        ).read_text(encoding="utf-8")
        self.assertIn("Compile-only ABI stub", stub)
        self.assertIn("throw new AssertionError", stub)
        self.assertIn("static native void newResponse", stub)


if __name__ == "__main__":
    unittest.main()
