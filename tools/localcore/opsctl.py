"""Static, local-only operator CLI for draft gacha/stage/event calendars.

No network, official Battle Cats SAVE_DATA, APK signing/install, purchases or
automatic reward grants. Prints a validated schedule snapshot to stdout.
"""
from __future__ import annotations

import argparse
from datetime import datetime, time, timedelta
import json
from pathlib import Path

from tools.localcore.ops_calendar import (
    JST, KINDS, LiveOpsError, _date, _local_timestamp, _rule_intervals,
    active_at, canonical_hash, validate_pack,
)


def windows_in_range(pack: dict, start_date: str, days: int) -> list[dict]:
    validate_pack(pack)
    if type(days) is not int or not 1 <= days <= 90:
        raise LiveOpsError("calendar preview is limited to 1–90 days")
    first = datetime.combine(_date(start_date), time(0, 0), tzinfo=JST)
    stop = first + timedelta(days=days)
    # A recurring window can cross season boundaries; never project a
    # published/live appearance outside the season's approved date range.
    first = max(first, _local_timestamp(pack["season"]["start"]))
    stop = min(stop, _local_timestamp(pack["season"]["end"]))
    if first >= stop:
        return []
    content = {
        kind: {item["id"]: item for item in pack["catalog"][kind]}
        for kind in KINDS
    }
    windows = []
    for event in pack["schedule"]:
        entry = content[event["kind"]][event["content_id"]]
        for begin, end in _rule_intervals(event["rule"], first, stop):
            windows.append({
                "schedule_id": event["id"], "kind": event["kind"],
                "slot": event["slot"], "priority": event["priority"],
                "content_id": event["content_id"], "title": entry["title"],
                "start": max(first, begin).isoformat(),
                "end": min(stop, end).isoformat(),
                "content_ready": entry["ready"],
                "pack_status": pack["status"],
                "requires": event.get("requires", {}),
                "not_original_ponos_schedule": True,
            })
    return sorted(windows, key=lambda w: (
        w["start"], KINDS.index(w["kind"]), w["slot"], -w["priority"], w["schedule_id"]
    ))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "preview", "calendar", "notices"))
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--at", help="ISO timestamp with timezone for preview")
    parser.add_argument("--from-date", help="JST YYYY-MM-DD for calendar")
    parser.add_argument("--days", type=int, default=14)
    args = parser.parse_args(argv)
    try:
        pack = validate_pack(json.loads(args.pack.read_text(encoding="utf-8")))
        report = {
            "mode": args.command, "channel": pack["channel"],
            "revision": pack["revision"], "pack_status": pack["status"],
            "content_sha256": canonical_hash(pack),
            "network_requests": 0, "save_mutations": 0,
            "not_an_android_game_update": True,
        }
        if args.command == "preview":
            if not args.at:
                raise LiveOpsError("--at is required for preview")
            report["snapshot"] = active_at(pack, _local_timestamp(args.at))
        elif args.command == "notices":
            if not args.at:
                raise LiveOpsError("--at is required for notices")
            # Author can preview draft articles, but that does not publish them.
            from tools.localcore.notice_feed import notice_feed
            report["notices"] = notice_feed(
                pack, _local_timestamp(args.at), allow_draft_preview=True
            )
        elif args.command == "calendar":
            if not args.from_date:
                raise LiveOpsError("--from-date is required for calendar")
            report["windows"] = windows_in_range(pack, args.from_date, args.days)
        else:
            report["catalog_entries"] = {kind: len(pack["catalog"][kind]) for kind in KINDS}
            report["schedule_entries"] = len(pack["schedule"])
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
