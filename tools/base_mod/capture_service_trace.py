"""Capture sanitized Phase-C service trace lines from an installed research build.

The user performs the original Battle Cats action while this command waits.
Run it once normally and once after manually enabling airplane mode.

This tool never changes Android network settings and never captures raw packet
traffic. It only reads KNEEKURA_TRACE log lines emitted by the research script.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import time

from tools.base_mod.summarize_service_trace import (
    PREFIX,
    parse_trace_lines,
    summarize_events,
)


DEFAULT_PACKAGE = "jp.kn.trace.battlecats"
DEFAULT_ACTIVITY = "jp.co.ponos.battlecats.MyActivity"


def adb_path(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    found = shutil.which("adb")
    if not found:
        raise FileNotFoundError("adb not found in PATH")
    return found


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def filter_trace_lines(logcat_text: str) -> list[str]:
    return [
        line
        for line in logcat_text.splitlines()
        if PREFIX in line
    ]


def capture(
    *,
    adb: str,
    output_dir: Path,
    seconds: int,
    package: str = DEFAULT_PACKAGE,
    activity: str = DEFAULT_ACTIVITY,
    launch: bool = True,
    label: str = "normal",
) -> dict:
    if seconds < 1:
        raise ValueError("seconds must be >= 1")
    output_dir.mkdir(parents=True, exist_ok=True)

    state = _run([adb, "get-state"]).stdout.strip()
    if state != "device":
        raise RuntimeError(f"adb device state is {state!r}, expected 'device'")

    _run([adb, "logcat", "-c"])
    if launch:
        _run([
            adb,
            "shell",
            "am",
            "start",
            "-n",
            f"{package}/{activity}",
        ])

    print(
        f"[{label}] Navigate the ORIGINAL Battle Cats research build now. "
        f"Perform exactly one low-risk action that should cause a service request. "
        f"Capturing sanitized trace metadata for {seconds} seconds..."
    )
    time.sleep(seconds)

    logcat = _run([adb, "logcat", "-d"]).stdout
    lines = filter_trace_lines(logcat)
    raw_path = output_dir / f"kneekura-service-trace-{label}.log"
    raw_path.write_text(
        ("\n".join(lines) + ("\n" if lines else "")),
        encoding="utf-8",
    )

    events = parse_trace_lines(lines)
    summary = summarize_events(events)
    summary.update(
        {
            "capture_label": label,
            "package": package,
            "activity": activity,
            "capture_seconds": seconds,
            "trace_line_count": len(lines),
        }
    )
    summary_path = output_dir / f"kneekura-service-trace-{label}-summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return {
        "label": label,
        "trace_log": str(raw_path),
        "summary": str(summary_path),
        "trace_line_count": len(lines),
        "event_count": summary["event_count"],
        "trace_ready": summary["trace_ready"],
        "request_return_count": len(summary["request_returns"]),
        "response_lifecycle_count": len(summary["response_lifecycles"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seconds", type=int, default=30)
    parser.add_argument("--package", default=DEFAULT_PACKAGE)
    parser.add_argument("--activity", default=DEFAULT_ACTIVITY)
    parser.add_argument("--adb")
    parser.add_argument("--label", choices=["normal", "airplane"], required=True)
    parser.add_argument("--no-launch", action="store_true")
    args = parser.parse_args()

    result = capture(
        adb=adb_path(args.adb),
        output_dir=args.output.resolve(),
        seconds=args.seconds,
        package=args.package,
        activity=args.activity,
        launch=not args.no_launch,
        label=args.label,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
