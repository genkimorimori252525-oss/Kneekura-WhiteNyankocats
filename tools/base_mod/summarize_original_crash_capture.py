"""Sanitize the owner's one-shot ORIGINAL research crash log into counts only.

Input must be the exact gitignored private/ original capture log. Never emit
raw PID, Android serial, crash address, account, SAVE, URL or unrelated app
lines to GitHub or chat. Native hook init failure != proven SIGSEGV root cause.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
from uuid import uuid4

LOG_LINE = re.compile(
    r"^\d\d-\d\d\s+\d\d:\d\d:\d\d\.\d{3,6}\s+"
    r"(?P<pid>\d{1,7})\s+\d{1,7}\s+[IWEF]\s+"
    r"(?P<tag>[A-Za-z0-9_]+):\s*(?P<message>.*)$"
)
START = re.compile(r"^Start proc (\d{1,7}):jp\.kn\.local\.battlecats/\S+")
DIED = re.compile(r"^Process jp\.kn\.local\.battlecats \(pid (\d{1,7})\) has died:")
INIT_STATUS = re.compile(r"^original-native-scene-hook-v1 hook-init-status=(-?[0-9]{1,5})$")
EVENTS = frozenset({
    "original-native-scene-hook-v1 hook-initialization-failed",
    "original-native-scene-hook-v1 hook-api-missing",
    "original-native-scene-hook-v1 hook-runtime-init-failed",
    "original-native-scene-hook-v1 hook-unavailable",
    "original-native-scene-hook-v1 partial-unhook-failed",
    "original-native-scene-hook-v1 library-unavailable",
    "original-native-scene-hook-v1 original-source-unavailable",
    "original-native-scene-hook-v1 installed",
})
KNOWN_LIBS = ("libkneekura.so", "libshadowhook.so",
              "libshadowhook_nothing.so", "libnative-lib.so")


class OriginalCrashLogBlocked(ValueError):
    pass


def summarize(log: str) -> dict:
    if len(log.encode("utf-8")) > 10_000_000:
        raise OriginalCrashLogBlocked("research filtered log too large")
    starts, deaths = set(), set()
    errors_by_process: dict[int, Counter] = {}
    init_codes_by_process: dict[int, Counter] = {}
    research_signals: list[tuple[int, str]] = []
    backtrace_known_libs = set()
    backtrace_known_frames = 0
    for line in log.splitlines():
        found = LOG_LINE.fullmatch(line)
        if not found:
            continue
        pid = int(found.group("pid"))
        tag, msg = found.group("tag"), found.group("message")
        if tag == "ActivityManager":
            start, death = START.match(msg), DIED.match(msg)
            if start:
                starts.add(int(start.group(1)))
            if death:
                deaths.add(int(death.group(1)))
        elif tag == "KNEEKURA_STATIC_HTTP":
            if msg in EVENTS:
                errors_by_process.setdefault(pid, Counter())[msg.split(" ")[-1]] += 1
            else:
                status = INIT_STATUS.fullmatch(msg)
                if status and -9999 <= int(status.group(1)) <= 9999:
                    errors_by_process.setdefault(pid, Counter())["hook-init-status"] += 1
                    init_codes_by_process.setdefault(pid, Counter())[int(status.group(1))] += 1
        elif tag in ("libc", "DEBUG", "AndroidRuntime"):
            if "Fatal signal 11" in msg or "SIGSEGV" in msg:
                research_signals.append((pid, msg))
            if re.search(r"#\d{2}\s+pc\s+[0-9a-fA-F]+", msg):
                hit = [name for name in KNOWN_LIBS if name in msg]
                if hit:
                    backtrace_known_frames += 1
                    backtrace_known_libs.update(hit)
    # A generic AndroidRuntime or libc log can belong to ANY other app.
    # Only count signals whose message identifies a research PID/namespace.
    signal_count = 0
    for pid, msg in research_signals:
        inner = re.search(r"\bpid (\d{1,7})\b", msg)
        if (inner and int(inner.group(1)) in starts
            or pid in starts and "jp.kn.local.battlecats" in msg):
            signal_count += 1
    # A public log tag is not proof of research process identity. Discard
    # all fixed research-looking lines without corroborating start/death PID
    # from the separately generated Android ActivityManager trace.
    verified = starts | deaths
    errors_by_process = {
        pid: counts for pid, counts in errors_by_process.items()
        if pid in verified
    }
    init_codes = Counter()
    for pid, codes in init_codes_by_process.items():
        if pid in verified:
            init_codes.update(codes)
    events = Counter()
    for counts in errors_by_process.values():
        events.update(counts)
    loop = len(starts) >= 3 and len(deaths) >= 2 and any(
        events[key] for key in ("hook-initialization-failed",
                               "hook-runtime-init-failed",
                               "hook-api-missing")
    )
    return {
        "schema": "original-isolated-crash-aggregate-v1",
        "status": "OBSERVED_RESTART_LOOP_WITH_HOOK_INITIALIZATION_FAILURE"
                  if loop else "INSUFFICIENT_FOR_ROOT_CAUSE",
        "isolated_original_research_process_starts_unique": len(starts),
        "isolated_original_research_process_deaths_unique": len(deaths),
        "isolated_research_hook_event_processes_unique": len(errors_by_process),
        "native_hook_event_counts": dict(sorted(events.items())),
        "reported_shadowhook_init_status_codes": {
            str(k): v for k, v in sorted(init_codes.items())},
        "research_SIGSEGV_signal_lines_in_filtered_log": signal_count,
        "known_native_libraries_in_backtrace_only": sorted(backtrace_known_libs),
        "known_native_backtrace_frames_in_filtered_log": backtrace_known_frames,
        "every_start_matched_to_a_death_in_log": starts.issubset(deaths),
        "observed_native_fault_PC_verified": False,
        "hook_error_caused_crash_proven": False,
        "original_gameplay_SAVE_level60_passed": False,
        "sdk_ipc_zero_egress_proven": False,
        "raw_log_pid_serial_account_URL_path_or_SAVE_retained": False,
    }


def from_private_capture(*, repo: Path, raw: Path) -> tuple[dict, Path]:
    repo = repo.resolve(strict=True)
    private = repo / "private"
    if not private.is_dir() or private.is_symlink():
        raise OriginalCrashLogBlocked("research private directory missing")
    capture_dir = private / "original-crash-captures"
    if capture_dir.is_symlink() or not capture_dir.is_dir() or raw.is_symlink():
        raise OriginalCrashLogBlocked("original private capture folder unsafe")
    try:
        input_file = raw.resolve(strict=True)
    except OSError as exc:
        raise OriginalCrashLogBlocked("original private capture file unavailable") from exc
    if (not input_file.is_file()
        or input_file.parent != capture_dir.resolve(strict=True)
        or not input_file.name.endswith("-filtered-logcat-PRIVATE.txt")
        or input_file.stat().st_size > 10_000_000):
        raise OriginalCrashLogBlocked("only the gitignored bounded research capture is allowed")
    report = summarize(input_file.read_text(encoding="utf-8-sig", errors="replace"))
    destination = private / ("original-crash-aggregate-" + uuid4().hex[:12] + ".json")
    if destination.exists() or destination.is_symlink():
        raise OriginalCrashLogBlocked("will not overwrite an existing owner capture")
    destination.write_text(json.dumps(report, ensure_ascii=False,
                                      indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    return report, destination


def main() -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--repo", type=Path, required=True)
    cli.add_argument("--raw", type=Path, required=True)
    args = cli.parse_args()
    try:
        report, _ = from_private_capture(repo=args.repo, raw=args.raw)
    except (OriginalCrashLogBlocked, OSError) as exc:
        cli.error(str(exc))
    print(json.dumps(report, sort_keys=True, ensure_ascii=False, indent=2))
    print("PRIVATE metadata-only receipt produced; raw Android log remains LOCAL.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
