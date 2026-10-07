"""Cross-platform terminal validation harness for coding agents.

The harness executes argv directly (``shell=False``), records the working
context plus stdout/stderr/exit code, and writes a JSON evidence report.  It is
intended to let an agent prove a command before handing an equivalent command
to a human.

Commands that require a physical Android device, private game export, signing
secret, or another unavailable external dependency are *user gates*: validate
all repository-local/static parts first, then make the remaining gate explicit.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = ROOT / ".agent-validation" / "reports" / "latest.json"
SCHEMA_VERSION = 1


@dataclass
class CommandResult:
    name: str
    argv: list[str]
    cwd: str
    started_at_unix: float
    duration_seconds: float
    exit_code: int | None
    timed_out: bool
    stdout: str
    stderr: str
    executable: str | None
    status: str
    platform: str
    skipped_reason: str | None = None


def _platform_tag() -> str:
    if os.name == "nt":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def _replace_secrets(text: str, secrets: Iterable[str]) -> str:
    redacted = text
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, "<redacted>")
    return redacted


def _resolve_executable(name: str, cwd: Path) -> str | None:
    candidate = Path(name)
    if candidate.is_absolute() and candidate.exists():
        return str(candidate)
    if any(sep in name for sep in ("/", "\\")):
        local = (cwd / candidate).resolve()
        return str(local) if local.exists() else None
    return shutil.which(name)


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)


def run_command(
    argv: Sequence[str],
    *,
    name: str = "command",
    cwd: Path = ROOT,
    timeout_seconds: int = 900,
    secret_env: Sequence[str] = (),
) -> CommandResult:
    if not argv:
        raise ValueError("argv must not be empty")
    cwd = cwd.resolve()
    if not cwd.is_dir():
        raise ValueError(f"working directory does not exist: {cwd}")

    secrets = [os.environ.get(key, "") for key in secret_env]
    executable = _resolve_executable(str(argv[0]), cwd)
    start = time.time()
    if executable is None:
        return CommandResult(
            name=name,
            argv=[str(x) for x in argv],
            cwd=str(cwd),
            started_at_unix=start,
            duration_seconds=0.0,
            exit_code=127,
            timed_out=False,
            stdout="",
            stderr=f"executable not found: {argv[0]}",
            executable=None,
            status="FAIL",
            platform=_platform_tag(),
        )

    try:
        completed = subprocess.run(
            [str(x) for x in argv],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            shell=False,
            check=False,
        )
        duration = time.time() - start
        stdout = _replace_secrets(completed.stdout or "", secrets)
        stderr = _replace_secrets(completed.stderr or "", secrets)
        return CommandResult(
            name=name,
            argv=[_replace_secrets(str(x), secrets) for x in argv],
            cwd=str(cwd),
            started_at_unix=start,
            duration_seconds=round(duration, 6),
            exit_code=completed.returncode,
            timed_out=False,
            stdout=stdout,
            stderr=stderr,
            executable=executable,
            status="PASS" if completed.returncode == 0 else "FAIL",
            platform=_platform_tag(),
        )
    except subprocess.TimeoutExpired as exc:
        duration = time.time() - start
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return CommandResult(
            name=name,
            argv=[_replace_secrets(str(x), secrets) for x in argv],
            cwd=str(cwd),
            started_at_unix=start,
            duration_seconds=round(duration, 6),
            exit_code=None,
            timed_out=True,
            stdout=_replace_secrets(stdout, secrets),
            stderr=_replace_secrets(stderr, secrets),
            executable=executable,
            status="TIMEOUT",
            platform=_platform_tag(),
        )


def _load_plan(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1:
        raise ValueError("validation plan version must be 1")
    steps = data.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError("validation plan must contain a non-empty steps list")
    return data


def _step_matches_platform(value: str | None) -> bool:
    if value in (None, "any"):
        return True
    return value == _platform_tag()


def run_plan(plan_path: Path, report_path: Path) -> int:
    plan_path = plan_path.resolve()
    plan = _load_plan(plan_path)
    results: list[CommandResult] = []

    for index, step in enumerate(plan["steps"], start=1):
        if not isinstance(step, dict):
            raise ValueError(f"plan step {index} must be an object")
        name = str(step.get("name") or f"step-{index}")
        platform_name = step.get("platform", "any")
        if not _step_matches_platform(platform_name):
            results.append(
                CommandResult(
                    name=name,
                    argv=[str(x) for x in step.get("argv", [])],
                    cwd=str(ROOT),
                    started_at_unix=time.time(),
                    duration_seconds=0.0,
                    exit_code=None,
                    timed_out=False,
                    stdout="",
                    stderr="",
                    executable=None,
                    status="SKIP",
                    platform=_platform_tag(),
                    skipped_reason=f"step targets {platform_name}",
                )
            )
            continue

        argv = step.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
            raise ValueError(f"plan step {name!r} must contain a non-empty string argv list")
        cwd_value = step.get("cwd", ".")
        cwd = (ROOT / str(cwd_value)).resolve()
        timeout_seconds = int(step.get("timeout_seconds", 900))
        secret_env = step.get("secret_env", [])
        if not isinstance(secret_env, list) or not all(isinstance(x, str) for x in secret_env):
            raise ValueError(f"plan step {name!r} secret_env must be a list of names")
        result = run_command(
            argv,
            name=name,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
            secret_env=secret_env,
        )
        results.append(result)
        if result.status not in {"PASS", "SKIP"} and not bool(step.get("continue_on_error", False)):
            break

    verdict = "PASS" if all(r.status in {"PASS", "SKIP"} for r in results) else "FAIL"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "kind": "agent-terminal-plan",
        "plan": str(plan_path),
        "platform": _platform_tag(),
        "python": sys.version,
        "verdict": verdict,
        "results": [asdict(result) for result in results],
    }
    _write_report(report_path, payload)
    _print_summary(payload)
    return 0 if verdict == "PASS" else 1


def _print_summary(payload: dict[str, Any]) -> None:
    print(f"AGENT_TERMINAL_VERDICT={payload['verdict']}")
    for result in payload.get("results", []):
        suffix = ""
        if result.get("exit_code") is not None:
            suffix += f" exit={result['exit_code']}"
        if result.get("timed_out"):
            suffix += " timeout=true"
        if result.get("skipped_reason"):
            suffix += f" ({result['skipped_reason']})"
        print(f"[{result['status']}] {result['name']}{suffix}")
    if payload.get("report"):
        print(f"report={payload['report']}")


def self_test(report_path: Path) -> int:
    results: list[CommandResult] = []

    ok = run_command(
        [sys.executable, "-c", "print('agent-terminal-ok')"],
        name="capture-success",
        cwd=ROOT,
        timeout_seconds=15,
    )
    results.append(ok)

    expected_failure = run_command(
        [
            sys.executable,
            "-c",
            "import sys; print('expected-stderr', file=sys.stderr); sys.exit(7)",
        ],
        name="capture-nonzero",
        cwd=ROOT,
        timeout_seconds=15,
    )
    expected_failure_ok = (
        expected_failure.exit_code == 7
        and "expected-stderr" in expected_failure.stderr
        and expected_failure.status == "FAIL"
    )
    expected_failure.status = "PASS" if expected_failure_ok else "FAIL"
    results.append(expected_failure)

    timeout = run_command(
        [sys.executable, "-c", "import time; time.sleep(2)"],
        name="capture-timeout",
        cwd=ROOT,
        timeout_seconds=1,
    )
    timeout_ok = timeout.timed_out and timeout.status == "TIMEOUT"
    timeout.status = "PASS" if timeout_ok else "FAIL"
    results.append(timeout)

    with tempfile.TemporaryDirectory() as temp_name:
        missing = run_command(
            ["definitely-not-a-real-kneekura-command"],
            name="capture-missing-executable",
            cwd=Path(temp_name),
            timeout_seconds=5,
        )
    missing_ok = missing.exit_code == 127 and missing.status == "FAIL"
    missing.status = "PASS" if missing_ok else "FAIL"
    results.append(missing)

    verdict = "PASS" if all(r.status == "PASS" for r in results) else "FAIL"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "kind": "agent-terminal-self-test",
        "platform": _platform_tag(),
        "python": sys.version,
        "verdict": verdict,
        "results": [asdict(result) for result in results],
        "report": str(report_path.resolve()),
    }
    _write_report(report_path, payload)
    _print_summary(payload)
    return 0 if verdict == "PASS" else 1


def _run_once(args: argparse.Namespace) -> int:
    argv = list(args.command)
    if argv and argv[0] == "--":
        argv = argv[1:]
    if not argv:
        raise SystemExit("run requires a command after --")
    cwd = (ROOT / args.cwd).resolve() if not Path(args.cwd).is_absolute() else Path(args.cwd).resolve()
    result = run_command(
        argv,
        name=args.name,
        cwd=cwd,
        timeout_seconds=args.timeout,
        secret_env=args.secret_env,
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "kind": "agent-terminal-command",
        "platform": _platform_tag(),
        "python": sys.version,
        "verdict": "PASS" if result.status == "PASS" else "FAIL",
        "results": [asdict(result)],
        "report": str(args.report.resolve()),
    }
    _write_report(args.report, payload)
    _print_summary(payload)
    return 0 if payload["verdict"] == "PASS" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="subcommand", required=True)

    p_self = sub.add_parser("self-test", help="prove capture/exit/timeout behavior")
    p_self.add_argument("--report", type=Path, default=DEFAULT_REPORT)

    p_plan = sub.add_parser("plan", help="run a committed JSON validation plan")
    p_plan.add_argument("plan", type=Path)
    p_plan.add_argument("--report", type=Path, default=DEFAULT_REPORT)

    p_run = sub.add_parser("run", help="run one argv command without a shell")
    p_run.add_argument("--name", default="command")
    p_run.add_argument("--cwd", default=".")
    p_run.add_argument("--timeout", type=int, default=900)
    p_run.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    p_run.add_argument(
        "--secret-env",
        action="append",
        default=[],
        help="environment variable whose value must be redacted from argv/output",
    )
    p_run.add_argument("command", nargs=argparse.REMAINDER)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.subcommand == "self-test":
        return self_test(args.report)
    if args.subcommand == "plan":
        return run_plan(args.plan, args.report)
    if args.subcommand == "run":
        return _run_once(args)
    raise AssertionError(args.subcommand)


if __name__ == "__main__":
    raise SystemExit(main())
