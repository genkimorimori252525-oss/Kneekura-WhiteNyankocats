"""Read-only Jolly announcements from a locally signed LiveOps pack.

This mirrors the independent Android NoticeActivity rendering policy for
operator-side previews. Notices are authored in catalog.notice and scheduled
using the same JST schedule engine as events, missions, stages and gacha.

Never reads the original game's account, SAVE_DATA, downloads, sends network
requests, grants rewards, or changes any player's progression.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from tools.localcore.ops_calendar import (
    JST, LiveOpsError, _local_timestamp, active_at, validate_pack,
)

CATEGORIES = frozenset({
    "重要", "運営情報", "更新情報", "イベント", "ガチャ", "お知らせ", "不具合",
})
MAX_BODY_CHARS = 12_000


def notice_feed(pack: dict, at: datetime, *, allow_draft_preview: bool = False) -> dict:
    validate_pack(pack)
    if not isinstance(at, datetime) or at.tzinfo is None:
        raise LiveOpsError("announcement evaluation requires timezone-aware timestamp")

    snapshot = active_at(pack, at)
    source = (
        snapshot["preview"]["notice"]
        if pack["status"] == "draft" and allow_draft_preview
        else snapshot["active"]["notice"]
    )
    definitions = {n["id"]: n for n in pack["catalog"]["notice"]}
    now = at.astimezone(JST)

    notices: list[dict[str, Any]] = []
    for scheduled in source:
        original = definitions[scheduled["content_id"]]
        publication = _local_timestamp(
            original.get("published_at", pack["season"]["start"])
        )
        if publication > now:
            continue
        title = original.get("title")
        category = original.get("category", "お知らせ")
        body = original.get("body", original.get("message", ""))
        if (not isinstance(title, str) or not title.strip()
            or not isinstance(body, str) or not 0 < len(body) <= MAX_BODY_CHARS
            or not isinstance(category, str) or category not in CATEGORIES):
            raise LiveOpsError("malformed local operator announcement")
        notices.append({
            "id": original["id"],
            "title": title.strip(),
            "category": category,
            "published_at": publication.isoformat(),
            "body": body.strip(),
            "pinned": original.get("pinned", False) is True,
            "source": "kneekura-local",
            "ready": True,
            "schedule_id": scheduled["schedule_id"],
            "priority": scheduled["priority"],
        })
    # Multiple eligible schedule slots for the same article must not duplicate
    # the article. Prefer highest-priority slot when the article appears twice.
    best: dict[str, dict] = {}
    for item in notices:
        if item["id"] not in best or item["priority"] > best[item["id"]]["priority"]:
            best[item["id"]] = item
    sorted_news = sorted(
        best.values(),
        key=lambda n: (
            not n["pinned"],
            -_local_timestamp(n["published_at"]).timestamp(),
            -n["priority"],
            n["id"],
        ),
    )
    return {
        "schema_version": 1,
        "status": "DRAFT_PREVIEW_ONLY" if pack["status"] == "draft" else "LOCAL_PUBLISHED",
        "snapshot_at": now.isoformat(),
        "revision": pack["revision"],
        "news": sorted_news[:80],
        "network_requests": 0,
        "player_save_changed": False,
        "no_external_assets": True,
    }
