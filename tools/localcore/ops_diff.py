"""Pure offline LiveOps pack review: revision, added/changed/retired IDs.

Never rewrites previous seasons or player progression, and never updates
the game. This is an operator review receipt, NOT an approval signature.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.localcore.ops_calendar import (
    KINDS, LiveOpsError, canonical_hash, validate_pack,
)


def review_update(before: dict, after: dict) -> dict:
    validate_pack(before)
    validate_pack(after)
    if after["revision"] <= before["revision"]:
        raise LiveOpsError("content revision must increase monotonically")
    if before["channel"] != after["channel"]:
        raise LiveOpsError("cannot change the offline content channel")
    old_content = {
        record["id"]: (kind, record)
        for kind in KINDS for record in before["catalog"][kind]
    }
    new_content = {
        record["id"]: (kind, record)
        for kind in KINDS for record in after["catalog"][kind]
    }
    for key in old_content.keys() & new_content.keys():
        if old_content[key][0] != new_content[key][0]:
            raise LiveOpsError("stable content ID reused for a different kind")
    old_schedule = {item["id"]: item for item in before["schedule"]}
    new_schedule = {item["id"]: item for item in after["schedule"]}
    for key in old_schedule.keys() & new_schedule.keys():
        previous, newer = old_schedule[key], new_schedule[key]
        if (previous["kind"], previous["content_id"]) != (
            newer["kind"], newer["content_id"]
        ):
            raise LiveOpsError("existing schedule ID may not be repointed to unrelated content")

    def delta(old: dict, new: dict) -> dict:
        a, b = set(old), set(new)
        return {
            "created": sorted(b - a),
            "updated": sorted(x for x in a & b if old[x] != new[x]),
            "retired": sorted(a - b),
        }

    content = delta(old_content, new_content)
    schedule = delta(old_schedule, new_schedule)
    declined = [
        key for key in old_content.keys() & new_content.keys()
        if old_content[key][1]["ready"] and not new_content[key][1]["ready"]
    ]
    changed = any(
        group[key] for group in (content, schedule)
        for key in ("created", "updated", "retired")
    )
    report = {
        "schema_version": 1,
        "mode": "kneekura-operator-review-only",
        "from_revision": before["revision"],
        "to_revision": after["revision"],
        "from_season": before["season"]["id"],
        "to_season": after["season"]["id"],
        "from_sha256": canonical_hash(before),
        "to_sha256": canonical_hash(after),
        "content_changes": content,
        "schedule_changes": schedule,
        "content_ready_true_to_false": sorted(declined),
        "requires_operator_review": changed or before["season"] != after["season"],
        "requires_player_save_migration": False,
        "player_progress_modified": False,
        "network_requests": 0,
        "android_content_imported": False,
        "released": False,
    }
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        before = json.loads(args.before.read_text(encoding="utf-8"))
        after = json.loads(args.after.read_text(encoding="utf-8"))
        report = review_update(before, after)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
