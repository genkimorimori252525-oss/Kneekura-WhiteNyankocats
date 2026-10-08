"""Build the revision-1 Kneekura offline-first content channel manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from tools.liveops.build_login_pool import build_pool


def _canonical_payload(document: dict) -> bytes:
    return json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def build_channel(export_zip: Path) -> dict:
    login_pool = build_pool(export_zip)

    document = {
        "schema_version": 1,
        "channel": "kneekura-main",
        "revision": 1,
        "game_anchor": "jp-15.7.1",
        "profile": {
            "id": "post-eoc-v1",
            "story_checkpoint": "empire-of-cats-3-complete",
            "eoc_treasures": "all-superior",
            "future_cotc": "uncompleted",
            "sol": "normal-progression",
            "economy": "low-friction-max",
        },
        "events": {
            "save_unlock_policy": {
                "stories_of_legend": "first-map-only",
                "normal_event": "all-exact-jp1571-maps-unlock-only",
                "collaboration": "all-exact-jp1571-maps-unlock-only",
            },
            "runtime_schedule_provider": {
                "status": "pending-original-ui-integration",
                "offline_cache_required": True,
            },
        },
        "login": {
            "provider": "kneekura-five-slot-v1",
            "active_slots": 5,
            "pool_count": login_pool["eligible_count"],
            "pool_ids_sha256": login_pool["eligible_ids_sha256"],
            "same_day": "no-second-claim",
            "clock_rollback": "no-claim",
            "forward_jump": "one-next-stamp-only",
            "replacement": "one-completed-slot -> one-new-slot-next-local-day",
        },
        "gacha": {
            "provider": "deferred",
            "original_ui_preferred": True,
            "history_must_survive_content_updates": True,
        },
        "custom_stages": {
            "provider": "data-pack",
            "entries": [],
        },
        "upstream": {
            "policy": "explicit-version-migration",
            "current_owned_export": (
                "38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56"
            ),
        },
        "integrity": {
            "signature_status": "not-yet-enabled",
            "last_known_good_required": True,
        },
    }

    digest_document = dict(document)
    digest_document["integrity"] = dict(document["integrity"])
    digest_document["integrity"].pop("content_sha256", None)
    document["integrity"]["content_sha256"] = hashlib.sha256(
        _canonical_payload(digest_document)
    ).hexdigest()
    return document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("owned_export", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        result = build_channel(args.owned_export)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"content-channel build failed: {exc}", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"built {result['channel']} revision {result['revision']} "
        f"-> {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
