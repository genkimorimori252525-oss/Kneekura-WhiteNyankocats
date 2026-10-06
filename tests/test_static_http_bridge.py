from pathlib import Path
import unittest

from tools.base_mod.inject_java_http_bridge import (
    BRIDGE_DEX_ENTRY,
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

    def test_bridge_is_additional_dex_not_original_method_rewrite(self) -> None:
        injector = (
            ROOT / "tools/base_mod/inject_java_http_bridge.py"
        ).read_text(encoding="utf-8")
        self.assertEqual(BRIDGE_DEX_ENTRY, "classes5.dex")
        self.assertIn("patch_equal_length_strings", injector)
        self.assertIn('"true" if flavor == "research" else "false"', injector)
        self.assertIn("{ORIGINAL_LAUNCHER: launcher}", injector)
        self.assertNotIn("patch_exact_dex_string(", injector)

    def test_compile_stub_is_never_product_logic(self) -> None:
        stub = (
            ROOT / "bridge/java/stub/jp/co/ponos/battlecats/MyActivity.java"
        ).read_text(encoding="utf-8")
        self.assertIn("Compile-only ABI stub", stub)
        self.assertIn("throw new AssertionError", stub)
        self.assertIn("static native void newResponse", stub)


if __name__ == "__main__":
    unittest.main()
