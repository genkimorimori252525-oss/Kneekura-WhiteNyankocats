import json
import unittest

from tools.base_mod.summarize_service_trace import (
    PREFIX,
    parse_trace_lines,
    summarize_events,
)


class ServiceTraceSummaryTests(unittest.TestCase):
    def _line(self, payload: dict) -> str:
        return PREFIX + json.dumps(payload)

    def test_summary_correlates_request_and_response_sequence(self) -> None:
        lines = [
            self._line({"kind": "trace_ready"}),
            self._line({
                "kind": "method_catalog",
                "method": "newHttpRequest",
                "overloads": [{"arguments": ["java.lang.String"], "returnType": "int"}],
            }),
            self._line({
                "kind": "call_enter",
                "method": "newHttpRequest",
                "overload": 0,
                "args": [],
            }),
            self._line({
                "kind": "call_return",
                "method": "newHttpRequest",
                "overload": 0,
                "result": {"type": "int", "value": 42},
            }),
            self._line({
                "kind": "call_enter",
                "method": "newResponse",
                "overload": 0,
                "args": [{"type": "int", "value": 42}],
            }),
            self._line({
                "kind": "call_enter",
                "method": "onResponseCodeHeaders",
                "overload": 0,
                "args": [{"type": "int", "value": 42}],
            }),
            self._line({
                "kind": "call_enter",
                "method": "onResponseData",
                "overload": 0,
                "args": [{"type": "int", "value": 42}],
            }),
            self._line({
                "kind": "call_enter",
                "method": "onResponseFinish",
                "overload": 0,
                "args": [{"type": "int", "value": 42}],
            }),
        ]
        result = summarize_events(parse_trace_lines(lines))
        self.assertTrue(result["trace_ready"])
        self.assertEqual(result["request_returns"][0]["request_id"], 42)
        lifecycle = result["response_lifecycles"][0]
        self.assertEqual(lifecycle["request_id"], "42")
        self.assertTrue(lifecycle["matches_simple_expected_order"])

    def test_invalid_json_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid Kneekura trace JSON"):
            parse_trace_lines([PREFIX + "{not-json}"])


if __name__ == "__main__":
    unittest.main()
