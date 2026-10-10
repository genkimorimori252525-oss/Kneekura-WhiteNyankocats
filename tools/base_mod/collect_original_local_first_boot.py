"""Read-only Android *original-host* local research first-boot metadata collector.

This does NOT install, launch, stop, reboot, root, modify, clear logs, or
read SAVE_DATA/APK bytes. The ONLY supported package is the separate original
native JP15.7.1 research host `jp.kn.local.battlecats`.
The app must already be running. Capture is restricted to the ORIGINAL
MyActivity subclass's allowlisted metadata debug tag and its current PID.

By default there are no native scene observations. When the optional
research-only, exact-original-BuildID scene hook actually emits allowlisted
scene IDs from the same isolated PID, record that narrow runtime witness.
This is still NOT proof of game-save correctness, user-visible gameplay or
independent zero SDK/IPC network egress.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
from typing import Any

RESEARCH_PACKAGE = "jp.kn.local.battlecats"
LOG_TAG = "KNEEKURA_STATIC_HTTP"
MAX_LOGCAT_BYTES = 1_048_576
ROOT = Path(__file__).resolve().parents[2]
PRIVATE_ROOT = ROOT / "private"
REQUIRED_SAVE_NAMES = ("SAVE_DATA", "SAVE_DATA4", "SAVE_DATA8")
LOG_LINE = re.compile(
    r"^\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3,6}\s+"
    r"(?P<pid>\d+)\s+\d+\s+I\s+" + LOG_TAG +
    r"\s*:\s*(?P<message>[^\r\n]*)$"
)
SAVE_FIELD = r"(?:absent|unsafe|present:[0-9]+)"
SAVE_MESSAGE = re.compile(
    r"^original-save-presence-v1 "
    + r" ".join(rf"{name}=(?P<{name}>{SAVE_FIELD})" for name in REQUIRED_SAVE_NAMES)
    + r"$"
)
DOWNLOAD_MESSAGE = re.compile(
    r"^original-download-tsv-loose-v1 present=(\d+) absent=(\d+) unsafe=(\d+)$"
)
# Only integer original scene IDs already source-pinned in exact JP15.7.1.
# A native-hook 'installed' marker must precede them in SAME process logs.
NATIVE_SCENE_MESSAGE = re.compile(
    r"^original-native-scene-v1 id=(4|97|101|102|104)$"
)
ALLOWED_STANDALONE_EVENTS = {
    "original-local-fresh-package-root active",
    "original-save-event-observer-v1 active",
    "original-save-event-observer-v1 unavailable",
    "original-save-presence-v1 unavailable",
    "original-download-tsv-loose-v1 unavailable",
    "original-local-denied-http-v1",
    "original-native-scene-hook-v1 installed",
    "original-native-scene-hook-v1 original-source-unavailable",
    "original-native-scene-hook-v1 library-unavailable",
    "original-native-scene-hook-v1 hook-initialization-failed",
    "original-native-scene-hook-v1 hook-unavailable",
    "original-native-scene-hook-v1 partial-unhook-failed",
}


class OriginalLocalBootObservationError(ValueError):
    """Untrusted package/device/source observation must not be accepted."""


def _parse_pid(stdout: str) -> int:
    pid_list = stdout.strip().split()
    if len(pid_list) != 1 or not pid_list[0].isascii() or not pid_list[0].isdigit():
        raise OriginalLocalBootObservationError(
            "original local-research package must already have one running PID"
        )
    pid = int(pid_list[0])
    if not 1 <= pid <= 4_194_303:
        raise OriginalLocalBootObservationError("invalid original research process PID")
    return pid


def sanitized_original_activity_events(logcat: str, *, pid: int) -> dict[str, Any]:
    """Count only explicitly allowed research messages for ONE current PID.

    Unknown lines, account data, URLs, strings, stack traces, and raw SAVE
    content are NEVER returned. A logcat observation isn't native execution
    proof unless separate, independently scoped instrumentation confirms it.
    """
    if type(pid) is not int or not 1 <= pid <= 4_194_303:
        raise OriginalLocalBootObservationError("invalid tracked PID")
    if len(logcat.encode("utf-8")) > MAX_LOGCAT_BYTES:
        raise OriginalLocalBootObservationError("filtered logcat output exceeds safety cap")
    counts: Counter[str] = Counter()
    last_save_state: dict[str, dict[str, Any]] | None = None
    first_save_seen_absent = False
    later_save_seen_present = False
    last_download_coverage: dict[str, int] | None = None
    scene_events: list[int] = []
    hook_install_marker_seen = False
    for line in logcat.splitlines():
        match = LOG_LINE.fullmatch(line)
        if not match or int(match.group("pid")) != pid:
            continue
        msg = match.group("message").strip()
        if msg in ALLOWED_STANDALONE_EVENTS:
            counts[msg] += 1
            if msg == "original-native-scene-hook-v1 installed":
                hook_install_marker_seen = True
            continue
        scene_match = NATIVE_SCENE_MESSAGE.fullmatch(msg)
        if scene_match:
            # Discard untrusted scene-looking logs before a native-hook
            # success marker, and cap report size even after long sessions.
            if hook_install_marker_seen:
                scene = int(scene_match.group(1))
                if not scene_events or scene_events[-1] != scene:
                    if len(scene_events) < 64:
                        scene_events.append(scene)
                counts["original-native-scene-v1 valid-transition"] += 1
            continue
        save = SAVE_MESSAGE.fullmatch(msg)
        if save:
            counts["original-save-presence-v1 valid-snapshot"] += 1
            parsed: dict[str, dict[str, Any]] = {}
            for name in REQUIRED_SAVE_NAMES:
                token = save.group(name)
                if token.startswith("present:"):
                    parsed[name] = {"status": "present", "size_bytes": int(token[8:])}
                else:
                    parsed[name] = {"status": token, "size_bytes": None}
            if parsed["SAVE_DATA"]["status"] == "absent":
                first_save_seen_absent = True
            elif parsed["SAVE_DATA"]["status"] == "present" and first_save_seen_absent:
                later_save_seen_present = True
            last_save_state = parsed
            continue
        download = DOWNLOAD_MESSAGE.fullmatch(msg)
        if download:
            present, absent, unsafe = (int(x) for x in download.groups())
            if present + absent + unsafe != 35:
                continue
            last_download_coverage = {
                "loose_present": present, "loose_absent": absent, "unsafe": unsafe,
            }
            counts["original-download-tsv-loose-v1 valid-snapshot"] += 1
    return {
        "allowlisted_event_counts": dict(sorted(counts.items())),
        "last_original_SAVE_metadata": last_save_state,
        "SAVE_absence_then_presence_observed_in_this_PID": later_save_seen_present,
        "last_loose_35_TSV_presence_metadata": last_download_coverage,
        "root_probe_witnessed": (
            counts["original-local-fresh-package-root active"] > 0
        ),
        "file_observer_witnessed": (
            counts["original-save-event-observer-v1 active"] > 0
        ),
        "denied_HTTP_calls_observed": counts["original-local-denied-http-v1"],
        "optional_native_hook_installed_marker_seen": hook_install_marker_seen,
        "optional_native_scene_ID_sequence": scene_events,
        "optional_native_scene102_then101_reported": (
            102 in scene_events
            and 101 in scene_events[scene_events.index(102) + 1:]
        ),
        "raw_logcat_lines_retained": False,
        "original_SAVE_content_read": False,
    }


def build_original_local_boot_metadata_receipt(
    *, pm_paths: str, dumpsys_package: str, pid_output: str, logcat: str,
) -> dict[str, Any]:
    """Strict Android package identity/permission + metadata-only observation.

    All values must come from the bounded read-only adb calls below. Tests
    provide purely synthetic strings; fixture PASS is not Android validation.
    """
    paths = [line for line in pm_paths.splitlines() if line.strip()]
    if (not paths or len(paths) > 16
        or any(not line.startswith("package:") or not line.endswith(".apk")
               for line in paths)
        or "base.apk" not in "\n".join(paths)):
        raise OriginalLocalBootObservationError(
            "the exact original-engine local research APK is not installed"
        )
    if (f"Package [{RESEARCH_PACKAGE}]" not in dumpsys_package
        or "requested permissions:" not in dumpsys_package.lower()):
        raise OriginalLocalBootObservationError(
            "cannot validate isolated original-research package identity/permissions"
        )
    if "android.permission.INTERNET" in dumpsys_package:
        raise OriginalLocalBootObservationError(
            "research package still reports INTERNET permission; stop"
        )
    pid = _parse_pid(pid_output)
    observation = sanitized_original_activity_events(logcat, pid=pid)
    root_seen = observation["root_probe_witnessed"]
    return {
        "schema": "original-native-local-first-boot-metadata-v1",
        "status": (
            "LOCAL_ROOT_METADATA_OBSERVED_NOT_NATIVE_BOOT_PROOF"
            if root_seen else "BLOCKED_NO_CURRENT_PROCESS_RESEARCH_ROOT_WITNESS"
        ),
        "exact_package": RESEARCH_PACKAGE,
        "currently_running_process_pid": pid,
        "installed_original_research_apk_split_count": len(paths),
        "manifest_INTERNET_permission_not_declared_observed": True,
        "signals": observation,
        # Hook events come from this exact isolated PID and only after the
        # native-hook marker. These are narrow process-log witnesses, NOT
        # trusted screenshots, native scene acceptance or full product PASS.
        "observed_original_native_scene102": (
            root_seen and 102 in observation["optional_native_scene_ID_sequence"]
        ),
        "observed_original_native_scene101": (
            root_seen and 101 in observation["optional_native_scene_ID_sequence"]
        ),
        "native_scene_ID_source_in_current_logcat": (
            root_seen and observation["optional_native_hook_installed_marker_seen"]
        ),
        "native_scene_witness_is_current_process_log_only": True,
        "original_gameplay_SAVE_validated_or_generated": False,
        "original_stage_level60_xp_catseye_gameplay_verified": False,
        "original_Jolly_i_gacha_events_stage_liveops_verified": False,
        "original_owner_Madoka_Godzilla_runtime_verified": False,
        "all_35_download_tsv_contents_original_engine_accepted": False,
        "independent_sdk_ipc_external_network_egress_measured_zero": False,
        "finished_original_game_offline_product": False,
        "original_APK_player_SAVE_or_pack_mutated_by_collector": False,
        "adb_commands_were_read_only": True,
        "logcat_or_SAVE_raw_contents_persisted": False,
    }


def _adb_read(
    adb: str, args: list[str], *, serial: str | None,
    timeout: int = 20,
) -> str:
    argv = [adb]
    if serial:
        if not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", serial):
            raise OriginalLocalBootObservationError("unsafe Android device serial")
        argv += ["-s", serial]
    argv += args
    try:
        result = subprocess.run(
            argv, capture_output=True, check=False, text=True,
            errors="replace", timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise OriginalLocalBootObservationError(
            "read-only adb command could not finish"
        ) from exc
    if result.returncode != 0:
        raise OriginalLocalBootObservationError(
            "read-only adb command failed (raw stderr intentionally suppressed)"
        )
    if len(result.stdout) > 2_000_000:
        raise OriginalLocalBootObservationError("adb metadata output too large")
    return result.stdout


def collect_original_local_boot_adb(
    *, adb: str = "adb", serial: str | None = None,
) -> dict[str, Any]:
    """Observe existing original-game research process, without launching it."""
    if not isinstance(adb, str) or not adb.strip() or "\x00" in adb:
        raise OriginalLocalBootObservationError("invalid adb executable")
    package = RESEARCH_PACKAGE  # fixed: NEVER operate on the official package
    pm_paths = _adb_read(adb, ["shell", "pm", "path", package], serial=serial)
    dump = _adb_read(adb, ["shell", "dumpsys", "package", package], serial=serial)
    if f"Package [{package}]" not in dump or "android.permission.INTERNET" in dump:
        raise OriginalLocalBootObservationError(
            "original local-research package does not meet fail-closed permissions gate"
        )
    pid_output = _adb_read(adb, ["shell", "pidof", package], serial=serial)
    pid = _parse_pid(pid_output)
    # -d dumps without clearing, --pid filters the ONE current app process.
    # -s restricts other package logcat entirely to this diagnostic tag.
    logcat = _adb_read(
        adb,
        ["logcat", "-d", "-v", "threadtime", f"--pid={pid}",
         "-s", f"{LOG_TAG}:I", "*:S"],
        serial=serial,
        timeout=25,
    )
    return build_original_local_boot_metadata_receipt(
        pm_paths=pm_paths, dumpsys_package=dump,
        pid_output=pid_output, logcat=logcat,
    )


def _protected_output_destination(dest: Path) -> Path:
    """One private JSON receipt, never a public Git or owner SAVE directory."""
    if PRIVATE_ROOT.is_symlink():
        raise OriginalLocalBootObservationError(
            "research private directory cannot be a symlink"
        )
    private = PRIVATE_ROOT.resolve()
    candidate = dest if dest.is_absolute() else ROOT / dest
    target = candidate.resolve()
    if not target.is_relative_to(private) or target == private:
        raise OriginalLocalBootObservationError(
            "observation output must stay inside repository private/"
        )
    if target.suffix.lower() != ".json" or target.exists():
        raise OriginalLocalBootObservationError(
            "private JSON output must be a NEW file (no overwrites)"
        )
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", default="adb", help="ADB executable (no shell)")
    parser.add_argument("--serial", help="Optional exact ADB serial")
    parser.add_argument("--output", required=True, type=Path,
                        help="New private/ output JSON; never an APK or SAVE")
    args = parser.parse_args(argv)
    try:
        destination = _protected_output_destination(args.output)
        receipt = collect_original_local_boot_adb(
            adb=args.adb, serial=args.serial
        )
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        # Exclusive create: no existing private observation or owner data
        # can be overwritten even if the output appeared since validation.
        with destination.open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, ensure_ascii=False, indent=2,
                      sort_keys=True)
            stream.write("\n")
    except (OriginalLocalBootObservationError, OSError) as error:
        parser.error(str(error))
    print(
        "original local-research passive metadata receipt: "
        f"{destination} (NOT native-game gameplay acceptance)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
