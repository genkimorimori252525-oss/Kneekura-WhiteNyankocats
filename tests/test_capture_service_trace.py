from pathlib import Path
import unittest

from tools.base_mod.capture_service_trace import (
    DEFAULT_ACTIVITY,
    DEFAULT_PACKAGE,
    filter_trace_lines,
)


ROOT = Path(__file__).resolve().parents[1]


class CaptureServiceTraceTests(unittest.TestCase):
    def test_filter_keeps_only_sanitized_trace_marker_lines(self) -> None:
        logcat = (
            "10-06 I/Other: hello\n"
            '10-06 I/frida: KNEEKURA_TRACE {"kind":"trace_ready"}\n'
            '10-06 I/frida: KNEEKURA_TRACE {"kind":"call_enter"}\n'
            "10-06 E/Other: nope\n"
        )
        lines = filter_trace_lines(logcat)
        self.assertEqual(len(lines), 2)
        self.assertTrue(all("KNEEKURA_TRACE " in line for line in lines))

    def test_subprocess_decode_is_utf8_and_replacement_tolerant(self) -> None:
        source = (ROOT / "tools/base_mod/capture_service_trace.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('encoding="utf-8"', source)
        self.assertIn('errors="replace"', source)

    def test_defaults_target_isolated_original_activity(self) -> None:
        self.assertEqual(DEFAULT_PACKAGE, "jp.kn.trace.battlecats")
        self.assertEqual(
            DEFAULT_ACTIVITY,
            "jp.co.ponos.battlecats.MyActivity",
        )


if __name__ == "__main__":
    unittest.main()
