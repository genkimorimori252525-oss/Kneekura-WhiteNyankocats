from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]


class NativeServiceMapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = json.loads(
            (ROOT / "docs/references/native-service-map-jp15.7.1.json")
            .read_text(encoding="utf-8")
        )

    def test_map_is_version_pinned(self) -> None:
        anchor = self.data["anchor"]
        self.assertEqual(anchor["version_code"], 1507010)
        self.assertEqual(
            anchor["native_sha256"],
            "333d2974ab2ff881fd70087fd62dea7d12d82addbc55cab2f2a675ad67e3a7e2",
        )
        self.assertEqual(
            anchor["native_build_id"],
            "8cb3815648eb9642da10bfb039d71bff7a3519bd",
        )

    def test_original_request_response_bridge_is_recorded(self) -> None:
        exports = {row["name"]: row for row in self.data["jni_exports"]}
        self.assertEqual(
            exports["Java_jp_co_ponos_battlecats_MyActivity_request"]["address"],
            "0x317b1c",
        )
        self.assertIn(
            "Java_jp_co_ponos_battlecats_MyActivity_newResponse",
            exports,
        )

    def test_service_design_prefers_java_http_bridge(self) -> None:
        methods = {row["method"] for row in self.data["java_bridges"]}
        self.assertIn("newHttpRequest", methods)
        self.assertIn("isNetworkAvailable", methods)
        self.assertIn(
            "Java newHttpRequest/isNetworkAvailable",
            self.data["recommendations"]["network_hook_seam"],
        )

    def test_login_clock_does_not_reuse_render_clock(self) -> None:
        self.assertIn(
            "Do not hook appUpdateDraw/steady_clock",
            self.data["recommendations"]["login_clock_seam"],
        )


if __name__ == "__main__":
    unittest.main()