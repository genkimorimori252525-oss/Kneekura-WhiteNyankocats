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
SOURCE_MSG = re.compile(r"KNEEKURA_STATIC_HTTP:\s*([^\r\n]{1,220})")
SCENE = re.compile(r"original-native-scene-v1 id=(4|97|101|102|104)\Z")
LOOSE = re.compile(
    r"original-download-tsv-loose-v1 present=(\d{1,2}) absent=(\d{1,2}) unsafe=(\d{1,2})\Z"
)

class OriginalOfflineRuntimeProofBlocked(ValueError):
    pass


def summarize_runtime_events(source: str) -> dict:
    if not isinstance(source, str) or len(source) > 16_000_000:
        raise OriginalOfflineRuntimeProofBlocked("owner-local original log unavailable or oversized")
    counts = Counter()
    scenes = []
    kinds = Counter()
    last_loose = None
    for line in source.splitlines():
        found = SOURCE_MSG.search(line)
        if not found:
            continue
        msg = found.group(1).strip()
        if msg == HOOK:
            counts["native_hook_installed"] += 1
        elif msg == "original-local-denied-http-v1":
            counts["denied_http"] += 1
        elif msg == "original-local-backup-failure-fallback-v1 completed":
            counts["backup_original_failure_response_completed"] += 1
        elif msg == "original-local-backup-failure-fallback-v1 unavailable":
            counts["backup_original_failure_response_unavailable"] += 1
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
        "last_original_loose_tsv_presence": last_loose,
        "denied_http_requests_observed": counts["denied_http"],
        "exact_backup_original_network_failure_callbacks_completed": (
            counts["backup_original_failure_response_completed"]),
        "exact_backup_original_network_failure_callbacks_unavailable": (
            counts["backup_original_failure_response_unavailable"]),
        "actual_publisher_backup_server_success_claimed": False,
        "safe_denied_http_category_counts": dict(sorted(kinds.items())),
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
    args=parser.parse_args()
    try:
        repo=args.repo.resolve(strict=True)
        parent=(repo/"private").resolve(strict=True)
        file=args.private_log
        if file.is_symlink() or not file.resolve(strict=True).is_relative_to(parent):
            raise OriginalOfflineRuntimeProofBlocked("filtered log must be in owner private root")
        if not file.is_file() or file.stat().st_size>16_000_000:
            raise OriginalOfflineRuntimeProofBlocked("owner log size/type invalid")
        report=summarize_runtime_events(file.read_text(encoding="utf-8-sig",errors="replace"))
    except (OSError, OriginalOfflineRuntimeProofBlocked) as error:
        parser.error(str(error))
    print(json.dumps(report,sort_keys=True,ensure_ascii=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
