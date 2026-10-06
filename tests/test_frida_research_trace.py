from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class FridaResearchTraceTests(unittest.TestCase):
    def test_trace_redacts_response_header_values(self) -> None:
        source = (
            Path(__file__).resolve().parents[1]
            / "research/frida/trace_service_bridge.js"
        ).read_text(encoding="utf-8")
        self.assertIn("summarizeHeaderBlock", source)
        self.assertIn("redacted: true", source)
        self.assertIn("headerArg: 3", source)

    def test_trace_emits_to_android_logcat(self) -> None:
        source = (
            Path(__file__).resolve().parents[1]
            / "research/frida/trace_service_bridge.js"
        ).read_text(encoding="utf-8")
        self.assertIn("android.util.Log", source)
        self.assertIn("AndroidLog.i('KNEEKURA_TRACE'", source)
        self.assertIn("AndroidLog.e('KNEEKURA_TRACE'", source)

    def test_service_trace_is_call_through_only(self) -> None:
        source = (
            ROOT / "research/frida/trace_service_bridge.js"
        ).read_text(encoding="utf-8")
        self.assertIn("import Java from 'frida-java-bridge';", source)
        self.assertIn("overload.call(receiver, ...originalArgs)", source)
        self.assertIn("newHttpRequest", source)
        self.assertIn("isNetworkAvailable", source)
        self.assertIn("onResponseData", source)
        self.assertNotIn("Interceptor.replace", source)
        self.assertNotIn("return true; //", source)

    def test_trace_does_not_log_payload_bytes_or_header_values(self) -> None:
        source = (
            ROOT / "research/frida/trace_service_bridge.js"
        ).read_text(encoding="utf-8")
        self.assertIn("remaining: value.remaining()", source)
        self.assertIn("keys: keys", source)
        self.assertNotIn("value.array()", source)
        self.assertNotIn("entrySet()", source)
        self.assertNotIn("send(payload)", source)
        self.assertIn("script_loaded", source)
        self.assertIn("trace_setup_error", source)
        self.assertIn("?<redacted>", source)
        self.assertIn("staticMethod: true", source)

    def test_research_readme_forbids_shipping_frida(self) -> None:
        readme = (ROOT / "research/frida/README.md").read_text(encoding="utf-8")
        self.assertIn("must not remain in the final APK", readme)


if __name__ == "__main__":
    unittest.main()
