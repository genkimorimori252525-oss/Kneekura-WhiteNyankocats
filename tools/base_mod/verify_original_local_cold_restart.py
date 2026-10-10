"""Fail-closed TWO-PROCESS original JP15.7.1 SAVE readback receipt gate.

Join ONLY two metadata-only receipts from the existing read-only ADB
collector. Never read any SAVE, installed APK, account, device identifier,
publisher service, arbitrary logcat or credentials. Do not control a device.

A PASS means two independent process-log observations are CONSISTENT with
fresh isolated original-native SAVE creation and second-process readback.
It does NOT cryptographically prove the same device/session, durable fsync,
a full physical phone restart, a playable game or zero external egress.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.base_mod.collect_original_local_first_boot import (
    RESEARCH_PACKAGE, ROOT, PRIVATE_ROOT, _protected_output_destination,
    OriginalLocalBootObservationError,
)

SCHEMA = "original-native-local-first-boot-metadata-v1"
STATUS = "TWO_DISTINCT_ORIGINAL_PROCESS_SAVE_READBACK_METADATA_CONSISTENT_ONLY"
FIRST_EXPECTED_TRIAL = [
    "original-native-virgin-save-trial-v1 root-attested",
    "original-native-virgin-save-trial-v1 read-accepted",
]
SECOND_READER_EVENT = ["original-native-app-launch-save-read-v1 accepted"]


class OriginalLocalColdRestartError(ValueError):
    """Metadata cannot safely support the claimed two-process sequence."""


def _require(cond: bool, reason: str) -> None:
    if not cond:
        raise OriginalLocalColdRestartError(reason)


def _save_size(observation: dict[str, Any]) -> int:
    if type(observation) is not dict:
        raise OriginalLocalColdRestartError("SAVE snapshot missing or malformed")
    save = observation.get("last_original_SAVE_metadata")
    _require(type(save) is dict, "no original SAVE metadata snapshot")
    _require(set(save) == {"SAVE_DATA", "SAVE_DATA4", "SAVE_DATA8"},
             "original SAVE snapshot names changed")
    main = save["SAVE_DATA"]
    _require(type(main) is dict and main.get("status") == "present",
             "original SAVE_DATA not present at snapshot")
    size = main.get("size_bytes")
    _require(type(size) is int and 0 < size <= 128 * 1024 * 1024,
             "original SAVE_DATA file length invalid")
    for other in ("SAVE_DATA4", "SAVE_DATA8"):
        item = save[other]
        _require(type(item) is dict and item.get("status") in ("absent", "present"),
                 "original secondary SAVE metadata unsafe")
        length = item.get("size_bytes")
        _require((item["status"] == "absent" and length is None) or
                 (item["status"] == "present" and type(length) is int
                  and 0 < length <= 128 * 1024 * 1024),
                 "original secondary SAVE size invalid")
    return size


def evaluate_original_local_two_process_readback(
    first: dict[str, Any], second: dict[str, Any],
) -> dict[str, Any]:
    """Only supplied metadata; no arbitrary payloads or source files consumed."""
    _require(type(first) is dict and type(second) is dict,
             "both original boot receipts must be objects")
    for name, receipt in (("first", first), ("second", second)):
        _require(receipt.get("schema") == SCHEMA,
                 name + " original observer receipt schema mismatch")
        _require(receipt.get("status") ==
                 "LOCAL_ROOT_METADATA_OBSERVED_NOT_NATIVE_BOOT_PROOF",
                 name + " original research root not witnessed")
        _require(receipt.get("exact_package") == RESEARCH_PACKAGE,
                 name + " not the isolated original research app")
        _require(receipt.get("installed_original_research_apk_split_count") == 6,
                 name + " not all original 6 APK splits installed")
        _require(receipt.get("manifest_INTERNET_permission_not_declared_observed") is True,
                 name + " Android INTERNET permission gate not passed")
        _require(receipt.get("adb_commands_were_read_only") is True
                 and receipt.get("original_APK_player_SAVE_or_pack_mutated_by_collector") is False
                 and receipt.get("logcat_or_SAVE_raw_contents_persisted") is False,
                 name + " metadata collection safety unverified")
        _require(receipt.get("native_scene_ID_source_in_current_logcat") is True,
                 name + " original native hook attachment not witnessed")
        signals = receipt.get("signals")
        _require(type(signals) is dict
                 and signals.get("root_probe_witnessed") is True
                 and signals.get("optional_native_hook_installed_marker_seen") is True,
                 name + " source-pinned original process event source absent")
        pid = receipt.get("currently_running_process_pid")
        _require(type(pid) is int and 1 <= pid <= 4_194_303,
                 name + " original process PID invalid")
    pid_first = first["currently_running_process_pid"]
    pid_second = second["currently_running_process_pid"]
    _require(pid_first != pid_second,
             "two receipts refer to the same process PID")
    a, b = first["signals"], second["signals"]
    _require(first.get("observed_original_native_virgin_trial_readback_this_process_only")
             is True and a.get("SAVE_absence_then_presence_observed_in_this_PID")
             is True, "first process did not witness original virgin SAVE transition")
    _require(a.get("native_original_virgin_trial_event_order_metadata_only")
             == FIRST_EXPECTED_TRIAL,
             "original first process virgin writer/reader outcome is not exclusive")
    _require(a.get("native_virgin_trial_failed_or_conflicting") is False,
             "original first process virgin write/read conflict")
    _require(a.get("native_virgin_trial_original_read_accepted_in_this_pid_only")
             is True,
             "original first process native loader did not accept readback")
    first_size = _save_size(a)

    # Restart MUST NOT create a new virgin marker, retry writer or report a
    # synthetic new-player transaction. A preexisting original SAVE must
    # be observed and accepted by the original AppLaunchLoad reader.
    _require(second.get("observed_original_AppLaunchLoad_SAVE_read_accepted") is True,
             "second process original game SAVE reader did not report accepted")
    _require(b.get("source_pinned_app_launch_save_read_outcomes")
             == SECOND_READER_EVENT,
             "second process native original reader outcome ambiguous")
    _require(b.get("native_app_launch_save_read_conflicting") is False,
             "second process original reader returned conflicting outcomes")
    _require(b.get("native_original_virgin_trial_event_order_metadata_only") == [],
             "second process unexpectedly attempted fresh virgin SAVE creation")
    _require(b.get("SAVE_absence_then_presence_observed_in_this_PID") is False,
             "second process cannot be a fresh missing-SAVE creation event")
    _require(b.get("native_virgin_trial_failed_or_conflicting") is False,
             "second process reports virgin writer error")
    second_size = _save_size(b)

    # NO 'SAVE was durably fsynced' conclusion or claim these receipts are
    # cryptographically bound to one device, original gameplay or cold reboot.
    return {
        "schema": "kneekura-original-two-process-save-evidence-v1",
        "status": STATUS,
        "exact_package": RESEARCH_PACKAGE,
        "installed_original_apk_splits_each_capture": 6,
        "two_distinct_original_process_PIDs_observed": True,
        "first_process_original_virgin_native_readback_observed": True,
        "second_process_original_AppLaunchLoad_read_accepted_observed": True,
        "first_original_SAVE_file_size_bytes": first_size,
        "second_original_SAVE_file_size_bytes": second_size,
        "original_SAVE_size_unchanged_between_processes": first_size == second_size,
        "source_user_APK_or_original_SAVE_read_or_modified": False,
        "raw_logcat_device_ID_or_player_account_collected": False,
        "same_device_cryptographically_attested": False,
        "physical_device_reboot_verified": False,
        "original_SAVE_fsync_and_durability_proven": False,
        "original_gameplay_level60_MAX_and_Madoka_Godzilla_verified": False,
        "Jolly_original_base_i_and_liveops_verified": False,
        "all_download_TSV_and_original_615MB_assets_accepted": False,
        "SDK_IPC_external_network_egress_measured_zero": False,
        "ready_to_install_or_ship_original_game": False,
    }


def _load_protected_metadata(source: Path) -> dict[str, Any]:
    if not isinstance(source, Path) or source.is_symlink() or not source.is_file():
        raise OriginalLocalColdRestartError("metadata must be an existing regular private JSON")
    folder = PRIVATE_ROOT.resolve()
    if not source.resolve().is_relative_to(folder):
        raise OriginalLocalColdRestartError("boot metadata inputs must stay under private/")
    if source.suffix != ".json" or source.stat().st_size > 64 * 1024:
        raise OriginalLocalColdRestartError("unsafe original private JSON receipt")
    try:
        parsed = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise OriginalLocalColdRestartError("unable to parse private metadata JSON") from exc
    if type(parsed) is not dict:
        raise OriginalLocalColdRestartError("private metadata receipt not an object")
    return parsed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only two-process original JP15.7.1 SAVE receipt comparison"
    )
    parser.add_argument("--first", required=True, type=Path)
    parser.add_argument("--second", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        first = _load_protected_metadata(args.first)
        second = _load_protected_metadata(args.second)
        result = evaluate_original_local_two_process_readback(first, second)
        dest = _protected_output_destination(args.output)
        dest.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with dest.open("x", encoding="utf-8") as output:
            json.dump(result, output, ensure_ascii=False, sort_keys=True, indent=2)
            output.write("\n")
    except (OriginalLocalColdRestartError, OriginalLocalBootObservationError,
            OSError) as exc:
        parser.error(str(exc))
    print("TWO PROCESS ORIGINAL SAVE READBACK METADATA consistent, "
          "NOT actual gameplay/reboot/fsync proof")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
