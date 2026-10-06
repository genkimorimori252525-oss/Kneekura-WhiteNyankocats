"""Summarize research/frida service-bridge trace output.

The Frida script emits sanitized lines prefixed with KNEEKURA_TRACE.
This parser never needs raw HTTP bodies or header values.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Iterable


PREFIX = "KNEEKURA_TRACE "


def parse_trace_lines(lines: Iterable[str]) -> list[dict]:
    events: list[dict] = []
    for line_number, raw in enumerate(lines, start=1):
        marker = raw.find(PREFIX)
        if marker < 0:
            continue
        payload_text = raw[marker + len(PREFIX):].strip()
        if not payload_text:
            continue
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"invalid Kneekura trace JSON on line {line_number}: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise ValueError(
                f"trace payload on line {line_number} is not an object"
            )
        payload["_line"] = line_number
        events.append(payload)
    return events


def _primitive_result(event: dict):
    result = event.get("result")
    if not isinstance(result, dict):
        return None
    return result.get("value")


def summarize_events(events: list[dict]) -> dict:
    kind_counts = Counter(str(event.get("kind")) for event in events)
    method_counts = Counter(
        str(event.get("method"))
        for event in events
        if event.get("kind") == "call_enter"
    )

    catalogs: dict[str, list] = {}
    request_returns: list[dict] = []
    response_sequence: list[dict] = []
    throws: list[dict] = []

    for event in events:
        kind = event.get("kind")
        method = event.get("method")
        if kind == "method_catalog" and isinstance(method, str):
            catalogs[method] = event.get("overloads", [])
        elif kind == "call_return" and method == "newHttpRequest":
            request_returns.append(
                {
                    "line": event.get("_line"),
                    "request_id": _primitive_result(event),
                    "overload": event.get("overload"),
                }
            )
        elif kind == "call_enter" and method in {
            "newResponse",
            "onResponseCodeHeaders",
            "onResponseData",
            "onResponseFinish",
        }:
            args = event.get("args", [])
            first_value = None
            if isinstance(args, list) and args:
                first = args[0]
                if isinstance(first, dict):
                    first_value = first.get("value")
            response_sequence.append(
                {
                    "line": event.get("_line"),
                    "method": method,
                    "request_id_candidate": first_value,
                    "overload": event.get("overload"),
                }
            )
        elif kind == "call_throw":
            throws.append(
                {
                    "line": event.get("_line"),
                    "method": method,
                    "error": event.get("error"),
                }
            )

    by_request: dict[str, list[str]] = defaultdict(list)
    for row in response_sequence:
        request_id = row["request_id_candidate"]
        if request_id is not None:
            by_request[str(request_id)].append(row["method"])

    expected_response_order = [
        "newResponse",
        "onResponseCodeHeaders",
        "onResponseData",
        "onResponseFinish",
    ]
    lifecycle_checks = []
    for request_id, methods in sorted(by_request.items()):
        compressed: list[str] = []
        for method in methods:
            if not compressed or compressed[-1] != method:
                compressed.append(method)
        lifecycle_checks.append(
            {
                "request_id": request_id,
                "observed_methods": methods,
                "compressed_methods": compressed,
                "contains_finish": "onResponseFinish" in methods,
                "starts_with_new_response": bool(methods)
                and methods[0] == "newResponse",
                "matches_simple_expected_order": compressed
                == expected_response_order,
            }
        )

    return {
        "schema_version": 1,
        "event_count": len(events),
        "trace_ready": any(event.get("kind") == "trace_ready" for event in events),
        "kind_counts": dict(sorted(kind_counts.items())),
        "method_call_counts": dict(sorted(method_counts.items())),
        "method_catalog": catalogs,
        "request_returns": request_returns,
        "response_sequence": response_sequence,
        "response_lifecycles": lifecycle_checks,
        "throws": throws,
        "privacy_note": (
            "Input is expected to contain only the sanitized metadata emitted "
            "by trace_service_bridge.js; raw body/header values are not required."
        ),
    }


def summarize_file(path: Path) -> dict:
    return summarize_events(
        parse_trace_lines(path.read_text(encoding="utf-8", errors="replace").splitlines())
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace_log", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = summarize_file(args.trace_log.resolve())
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
