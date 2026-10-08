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

    def test_summary_extracts_sanitized_request_and_response_fields(self) -> None:
        lines = [
            self._line({"kind": "trace_ready"}),
            self._line({
                "kind": "call_enter",
                "method": "newHttpRequest",
                "overload": 0,
                "args": [
                    {"type": "java.lang.String", "value": "GET"},
                    {"type": "java.lang.String", "value": "https://example.test/?<redacted>"},
                    {"type": "float", "value": 10},
                    {"type": "java.util.HashMap", "size": 0, "keys": []},
                    None,
                    {"type": "[Ljava.lang.String;", "length": 0},
                    {"type": "boolean", "value": False},
                    {"type": "boolean", "value": False},
                ],
                "thread": {"name": "GLThread"},
                "request_state": {"next_request_handle": 0, "request_map_size": 0},
            }),
            self._line({
                "kind": "call_return",
                "method": "newHttpRequest",
                "overload": 0,
                "result": {"type": "int", "value": 1},
                "thread": {"name": "GLThread"},
                "request_state": {"next_request_handle": 1, "request_map_size": 1},
            }),
            self._line({
                "kind": "call_return",
                "method": "isNetworkAvailable",
                "result": {"type": "boolean", "value": True},
                "thread": {"name": "GLThread"},
                "request_state": {"next_request_handle": 1, "request_map_size": 1},
            }),
            self._line({
                "kind": "call_enter",
                "method": "newResponse",
                "overload": 0,
                "args": [
                    {"type": "int", "value": 1},
                    {"type": "int", "value": 200},
                    {"type": "java.lang.String", "value": "https://example.test/?<redacted>"},
                    {"type": "java.lang.String", "redacted": True, "length": 2, "empty_object": True},
                    None,
                    {"type": "boolean", "value": False},
                ],
                "thread": {"name": "GLThread"},
                "request_state": {"next_request_handle": 1, "request_map_size": 0},
            }),
        ]
        result = summarize_events(parse_trace_lines(lines))
        req = result["request_observations"][0]
        self.assertEqual(req["request_id"], 1)
        self.assertEqual(req["http_method"], "GET")
        self.assertEqual(req["flags"], [False, False])
        self.assertEqual(req["request_state_after"]["request_map_size"], 1)
        self.assertTrue(result["network_results"][0]["value"])
        response = result["response_details"][0]
        self.assertEqual(response["status"], 200)
        self.assertTrue(response["header"]["empty_object"])

    def test_invalid_json_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid Kneekura trace JSON"):
            parse_trace_lines([PREFIX + "{not-json}"])


if __name__ == "__main__":
    unittest.main()
