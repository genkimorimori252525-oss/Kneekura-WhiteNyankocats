"""Strict privacy-safe offline original JP15.7.1 scene97 boot event gate.

Read an owner-only filtered logcat transcript, keep ONLY exact fixed research
markers and bounded native scene IDs, never include personal/URL/path/SAVE
text in output. Do not contact Android, write app files, or claim Cat Base
based on an importer-completion marker.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re

HOOK = "original-native-scene-hook-v1 installed"
IMPORT_ALLOWED = frozenset({
    "393-source-md5-pass", "completed-393", "already-complete",
    "stage-not-ready", "invalid-stage", "conflicting-private-file",
    "blocked", "unavailable",
})
HTTP_KINDS = frozenset({
    "asset-cdn", "backup", "publisher-other", "external-other", "malformed",
})
BACKUP_TIMEOUT_CLASSES = frozenset({
    "nonfinite", "nonpositive", "lt10", "eq10",
    "gt10-le30", "gt30-le120", "gt120",
})
BACKUP_ENVELOPE_CLASSES = frozenset({"match", "mismatch"})
FILE_ACCESS_KINDS = frozenset({
    "watching", "unavailable", "download-tsv",
    "server-list", "server-pack", "media",
})
SOURCE_MSG = re.compile(r"KNEEKURA_STATIC_HTTP:\s*([^\r\n]{1,220})")
SCENE = re.compile(r"original-native-scene-v1 id=(4|97|101|102|104)\Z")
BACKUP_SHAPE = re.compile(r"original-local-backup-shape-v1 mask=([0-7a-f]{1,3})\Z")

LOOSE = re.compile(
    r"original-download-tsv-loose-v1 present=(\d{1,2}) absent=(\d{1,2}) unsafe=(\d{1,2})\Z"
)

SCENE97_RESOLVER = re.compile(
    r"original-native-scene97-resolver-v1 "
    r"missing=(\d{1,2}) zero=(\d{1,2}) "
    r"one=(\d{1,2}) other=(\d{1,2})\Z"
)
OWNER_FINAL_SCREEN_KINDS = frozenset({"internet-unavailable"})

class OriginalOfflineRuntimeProofBlocked(ValueError):
    pass


def summarize_runtime_events(
    source: str, *, owner_final_screen: str | None = None,
    owner_reported_615mb_request_passed: bool = False,
) -> dict:
    if not isinstance(source, str) or len(source) > 16_000_000:
        raise OriginalOfflineRuntimeProofBlocked("owner-local original log unavailable or oversized")
    if owner_final_screen is not None and owner_final_screen not in OWNER_FINAL_SCREEN_KINDS:
        raise OriginalOfflineRuntimeProofBlocked("unknown owner final screen category")
    if not isinstance(owner_reported_615mb_request_passed, bool):
        raise OriginalOfflineRuntimeProofBlocked("invalid owner 615MB observation")
    counts = Counter()
    scenes = []
    kinds = Counter()
    backup_shapes = Counter()
    backup_timeout_classes = Counter()
    backup_envelope_classes = Counter()
    file_events = Counter()
    last_loose = None
    scene97_slot_snapshots = []
    last_scene97_slot_summary = None
    for line in source.splitlines():
        found = SOURCE_MSG.search(line)
        if not found:
            continue
        msg = found.group(1).strip()
        if msg == HOOK:
            counts["native_hook_installed"] += 1
        elif msg == "original-local-network-availability-v1 offline":
            counts["original_local_network_unavailable"] += 1
        elif msg == "original-local-denied-http-v1":
            counts["denied_http"] += 1
        elif msg == "original-local-backup-failure-fallback-v1 completed":
            # Historical legacy marker fires AFTER queueEvent() scheduling,
            # NOT after GL-thread callback execution. Do not infer completion.
            counts["backup_original_queued_legacy"] += 1
        elif msg == "original-local-backup-failure-fallback-v1 enqueued":
            counts["backup_original_enqueued"] += 1
        elif msg == "original-local-backup-callback-v1 returned":
            counts["backup_original_callback_returned"] += 1
        elif msg == "original-local-backup-timeout-variant-v1 completed":
            counts["backup_timeout_variant_queued_legacy"] += 1
        elif msg == "original-local-backup-timeout-variant-v1 enqueued":
            counts["backup_timeout_variant_enqueued"] += 1
        elif msg == "original-local-backup-timeout-variant-v1 returned":
            counts["backup_timeout_variant_callback_returned"] += 1
        elif msg == "original-local-backup-failure-fallback-v1 unavailable":
            counts["backup_original_failure_response_unavailable"] += 1
        elif BACKUP_SHAPE.fullmatch(msg):
            # Exactly 11 bounded boolean contract bits, no URL or query.
            match = BACKUP_SHAPE.fullmatch(msg)
            bits = int(match.group(1), 16)
            if 0 <= bits <= 0x7ff:
                backup_shapes[format(bits, "03x")] += 1
        elif msg.startswith("original-local-backup-timeout-class-v1 "):
            kind=msg[len("original-local-backup-timeout-class-v1 "):]
            if kind in BACKUP_TIMEOUT_CLASSES:
                backup_timeout_classes[kind] += 1
        elif msg.startswith("original-local-backup-strict-envelope-v1 "):
            kind=msg[len("original-local-backup-strict-envelope-v1 "):]
            if kind in BACKUP_ENVELOPE_CLASSES:
                backup_envelope_classes[kind] += 1
        elif SCENE97_RESOLVER.fullmatch(msg):
            # Four whole counts, no IDs, filenames, paths, or source bytes.
            # Signed native resolver statuses are NOT download progress.
            groups = tuple(map(int, SCENE97_RESOLVER.fullmatch(msg).groups()))
            if all(x <= 35 for x in groups) and sum(groups) == 35:
                last_scene97_slot_summary = dict(zip(
                    ("missing", "zero", "one", "other"), groups))
                if len(scene97_slot_snapshots) < 4:
                    scene97_slot_snapshots.append(last_scene97_slot_summary)
        elif msg.startswith("original-local-file-access-v1 "):
            # Only bounded file TYPE names from this app's own read-only
            # FileObserver. Never emit raw Android names, paths or SAVE.
            kind = msg[len("original-local-file-access-v1 "):]
            if kind in FILE_ACCESS_KINDS:
                file_events[kind] += 1
        elif msg.startswith("original-local-import-v1 "):
            status = msg[len("original-local-import-v1 "):]
            if status in IMPORT_ALLOWED:
                counts["import_"+status] += 1
        elif msg.startswith("original-local-http-kind-v1 "):
            kind = msg[len("original-local-http-kind-v1 "):]
            if kind in HTTP_KINDS:
                kinds[kind] += 1
        else:
            scene = SCENE.fullmatch(msg)
            if scene:
                scenes.append(int(scene.group(1)))
            else:
                match = LOOSE.fullmatch(msg)
                if match:
                    p, a, u = map(int, match.groups())
                    if p + a + u == 35:
                        last_loose = {
                            "present": p, "absent": a, "unsafe": u,
                        }
    import_complete = (
        counts["import_completed-393"] > 0
        or counts["import_already-complete"] > 0
    )
    scene97 = 97 in scenes
    other_after_97 = (
        any(scene != 97 for scene in scenes[scenes.index(97)+1:])
        if scene97 else False
    )
    if not import_complete:
        status = "ORIGINAL_393_IMPORT_NOT_YET_ACCEPTED"
    elif scene97 and not other_after_97:
        status = "ORIGINAL_393_IMPORTED_SCENE97_STILL_LAST_OBSERVED"
    elif scene97:
        status = "ORIGINAL_393_IMPORTED_SCENE_TRANSITION_OBSERVED_NOT_GAMEPLAY"
    else:
        status = "ORIGINAL_393_IMPORTED_NO_SCENE97_OBSERVED"
    return {
        "schema": "kneekura-jp1571-native-offline-bootstrap-fixed-events-v1",
        "status": status,
        "native_hook_installed_events": counts["native_hook_installed"],
        "import_all_393_source_md5_verified_events": counts["import_393-source-md5-pass"],
        "import_completed_393_events": counts["import_completed-393"],
        "import_already_complete_events": counts["import_already-complete"],
        "import_blocked_events": sum(
            counts["import_"+x] for x in (
                "blocked", "stage-not-ready", "invalid-stage",
                "conflicting-private-file", "unavailable")),
        "import_completed_or_persisted_marker_observed": import_complete,
        "original_native_scene_ids_observed": scenes[:20],
        "scene97_native_resolver_status_histograms": scene97_slot_snapshots,
        "scene97_native_resolver_last_histogram": last_scene97_slot_summary,
        "scene97_resolver_return_values_are_not_download_completion": True,
        "owner_observed_final_screen": owner_final_screen,
        "owner_reported_615mb_request_dialog_passed": owner_reported_615mb_request_passed,
        "owner_observed_offline_error_during_scene97": (
            owner_final_screen == "internet-unavailable"
            and bool(scenes) and scenes[-1] == 97),
        "screen_message_source_or_native_version_check_proven": False,
        "last_original_loose_tsv_presence": last_loose,
        "denied_http_requests_observed": counts["denied_http"],
        "original_local_network_availability_false_observed": (
            counts["original_local_network_unavailable"] > 0),
        "original_local_network_unavailable_event_count": (
            counts["original_local_network_unavailable"]),
        "exact_backup_original_network_failure_callbacks_completed": (
            counts["backup_original_callback_returned"]),
        "exact_backup_original_network_failure_callbacks_enqueued": (
            counts["backup_original_enqueued"]
            + counts["backup_original_queued_legacy"]),
        "backup_timeout_variant_original_failure_callbacks_completed": (
            counts["backup_timeout_variant_callback_returned"]),
        "backup_timeout_variant_original_failure_callbacks_enqueued": (
            counts["backup_timeout_variant_enqueued"]
            + counts["backup_timeout_variant_queued_legacy"]),
        "legacy_misnamed_callback_completed_tags_observed": (
            counts["backup_original_queued_legacy"]
            + counts["backup_timeout_variant_queued_legacy"]),
        "callback_enqueued_is_not_native_task_or_scene_acceptance": True,
        "exact_backup_original_network_failure_callbacks_unavailable": (
            counts["backup_original_failure_response_unavailable"]),
        "actual_publisher_backup_server_success_claimed": False,
        "safe_denied_http_category_counts": dict(sorted(kinds.items())),
        "blocked_backup_source_contract_bitmasks": dict(sorted(
            backup_shapes.items())),
        "blocked_backup_timeout_class_counts": dict(sorted(
            backup_timeout_classes.items())),
        "blocked_backup_strict_url_envelope_counts": dict(sorted(
            backup_envelope_classes.items())),
        "original_file_source_access_kind_counts": dict(sorted(
            file_events.items())),
        "real_native_source_consumed_original_TSV_proven": False,
        "source_contract_mask_flags": {
            "method_GET": 0x001,
            "timeout_10": 0x002,
            "empty_headers": 0x004,
            "body_null": 0x008,
            "string_array_empty": 0x010,
            "first_flag_false": 0x020,
            "second_flag_false": 0x040,
            "https": 0x080,
            "root_path": 0x100,
            "query_present": 0x200,
            "default_port_no_userinfo_fragment": 0x400,
        },
        "original_scene97_completed_successfully_proven": False,
        "original_615mb_gate_bypassed_proven": False,
        "original_cat_base_visible_proven": False,
        "original_SAVE_contents_read_or_logged": False,
        "raw_request_URL_or_account_logged": False,
        "device_or_game_data_modified": False,
    }


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--private-log", type=Path, required=True)
    parser.add_argument(
        "--owner-observed-final-screen", choices=sorted(OWNER_FINAL_SCREEN_KINDS),
        default=None, help="Only the owner's final-screen category; no screenshot uploaded")
    parser.add_argument("--owner-reported-615mb-request-passed",
                        action="store_true", default=False)
    args=parser.parse_args()
    try:
        repo=args.repo.resolve(strict=True)
        parent=(repo/"private").resolve(strict=True)
        file=args.private_log
        if file.is_symlink() or not file.resolve(strict=True).is_relative_to(parent):
            raise OriginalOfflineRuntimeProofBlocked("filtered log must be in owner private root")
        if not file.is_file() or file.stat().st_size>16_000_000:
            raise OriginalOfflineRuntimeProofBlocked("owner log size/type invalid")
        report=summarize_runtime_events(
            file.read_text(encoding="utf-8-sig", errors="replace"),
            owner_final_screen=args.owner_observed_final_screen,
            owner_reported_615mb_request_passed=args.owner_reported_615mb_request_passed)
    except (OSError, OriginalOfflineRuntimeProofBlocked) as error:
        parser.error(str(error))
    print(json.dumps(report,sort_keys=True,ensure_ascii=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
