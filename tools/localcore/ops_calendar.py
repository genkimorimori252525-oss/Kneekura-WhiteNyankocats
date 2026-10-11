"""Independent, deterministic, *offline* KNEEKURA LiveOps calendar.

This is a pure Python authoring/evaluation engine. It does not call a server,
read the original Battle Cats SAVE_DATA, install an APK, draw gacha, grant
rewards, or unlock stages. It ONLY describes potential availability.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
import re
from typing import Any

JST = timezone(timedelta(hours=9))
KINDS = ("gacha", "stage", "event", "login", "mission", "notice", "modifier")
CHANNEL = "kneekura-main-offline"
ID = re.compile(r"^kneekura:[a-z0-9][a-z0-9_.:-]{0,95}$")
HHMM = re.compile(r"^([01][0-9]|2[0-3]):([0-5][0-9])$")


class LiveOpsError(ValueError):
    pass


def _id(value: Any) -> str:
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise LiveOpsError("invalid locally namespaced content ID")
    return value


def _local_timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise LiveOpsError("timestamp must be an ISO8601 string with a timezone")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LiveOpsError("invalid ISO8601 timestamp") from exc
    if stamp.tzinfo is None:
        raise LiveOpsError("timestamps must include their timezone")
    return stamp.astimezone(JST)


def _date(value: Any) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise LiveOpsError("invalid YYYY-MM-DD date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise LiveOpsError("invalid calendar day") from exc


def _time(value: Any) -> time:
    if not isinstance(value, str) or not HHMM.fullmatch(value):
        raise LiveOpsError("invalid 24-hour HH:MM")
    hour, minute = map(int, value.split(":"))
    return time(hour, minute, tzinfo=JST)


def _is_int(x: Any, lo: int, hi: int) -> bool:
    return type(x) is int and lo <= x <= hi


def _deny_external_strings(obj: Any) -> None:
    """Content never contains a transport destination, remote code or user ID."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if not isinstance(key, str):
                raise LiveOpsError("JSON keys must be strings")
            if key.casefold() in {"endpoint", "account_token", "server_url",
                                  "inquiry_code", "official_save_data"}:
                raise LiveOpsError("external account/service fields are forbidden")
            _deny_external_strings(value)
    elif isinstance(obj, list):
        for value in obj:
            _deny_external_strings(value)
    elif isinstance(obj, str) and re.search(r"(https?://|wss?://|file://)", obj, re.I):
        raise LiveOpsError("content pack must not contain external URLs")


def _span(rule: dict, anchor: date) -> tuple[datetime, datetime]:
    begin = datetime.combine(anchor, _time(rule["from_time"]))
    finish = datetime.combine(anchor, _time(rule["to_time"]))
    if finish <= begin:
        finish += timedelta(days=1)  # overnight window
    return begin, finish


def _rule_intervals(rule: dict, start: datetime, end: datetime):
    """Return bounded half-open [start,end) windows overlapping a requested range."""
    mode = rule["mode"]
    if mode == "once":
        a = _local_timestamp(rule["start"])
        b = _local_timestamp(rule["end"])
        if a < end and start < b:
            yield a, b
        return
    cursor = (start - timedelta(days=1)).date()
    stop = end.date()
    first = _date(rule["valid_from"])
    last_exclusive = _date(rule["valid_until"])
    while cursor <= stop:
        if first <= cursor < last_exclusive:
            day_allowed = (
                mode == "daily"
                or (mode == "weekly" and cursor.weekday() in rule["weekdays"])
                or (mode == "monthly" and cursor.day in rule["monthdays"])
            )
            if day_allowed:
                a, b = _span(rule, cursor)
                if a < end and start < b:
                    yield a, b
        cursor += timedelta(days=1)


def _validate_rule(rule: Any, season_start: datetime, season_end: datetime) -> None:
    if not isinstance(rule, dict):
        raise LiveOpsError("schedule rule must be object")
    mode = rule.get("mode")
    if mode == "once":
        start, end = _local_timestamp(rule.get("start")), _local_timestamp(rule.get("end"))
        if not season_start <= start < end <= season_end:
            raise LiveOpsError("one-time window outside season or reversed")
    elif mode in ("daily", "weekly", "monthly"):
        first = _date(rule.get("valid_from"))
        last = _date(rule.get("valid_until"))
        if not (season_start.date() <= first < last <= season_end.date()):
            raise LiveOpsError("recurrence outside declared season")
        _time(rule.get("from_time"))
        _time(rule.get("to_time"))
        if mode == "weekly":
            days = rule.get("weekdays")
            if not isinstance(days, list) or not days or len(set(map(str, days))) != len(days):
                raise LiveOpsError("missing or duplicate weekly days")
            if not all(_is_int(x, 0, 6) for x in days):
                raise LiveOpsError("weekly days must be 0..6")
        if mode == "monthly":
            days = rule.get("monthdays")
            if not isinstance(days, list) or not days or len(set(map(str, days))) != len(days):
                raise LiveOpsError("missing or duplicate monthly days")
            if not all(_is_int(x, 1, 31) for x in days):
                raise LiveOpsError("monthdays must be 1..31")
    else:
        raise LiveOpsError("unsupported scheduling mode")


def validate_pack(pack: Any) -> dict:
    """Strictly validate one locally managed operator pack, no network/file IO."""
    if not isinstance(pack, dict) or pack.get("schema_version") != 1:
        raise LiveOpsError("unsupported offline content pack schema")
    if pack.get("channel") != CHANNEL or pack.get("timezone") != "Asia/Tokyo":
        raise LiveOpsError("unsupported offline channel/timezone")
    if pack.get("status") not in ("draft", "published"):
        raise LiveOpsError("invalid authoring state")
    if not _is_int(pack.get("revision"), 1, 2**31 - 1):
        raise LiveOpsError("invalid revision")
    policy = pack.get("policy")
    if not isinstance(policy, dict) or (
        policy.get("network") != "forbidden"
        or policy.get("owner_save") != "KNEEKURA_SAVE_V1"
        or policy.get("stage_availability_is_clear") is not False
        or policy.get("login_active_slots") != 5
        or policy.get("real_money") is not False
    ):
        raise LiveOpsError("offline/ownership/content policies changed")
    _deny_external_strings(pack)
    season = pack.get("season")
    if not isinstance(season, dict):
        raise LiveOpsError("missing season")
    _id(season.get("id"))
    if not isinstance(season.get("title"), str) or not season["title"]:
        raise LiveOpsError("missing season title")
    season_start = _local_timestamp(season.get("start"))
    season_end = _local_timestamp(season.get("end"))
    if season_end <= season_start or (season_end - season_start).days > 366:
        raise LiveOpsError("season must be bounded to at most one year")
    if season_start.hour != 0 or season_start.minute != 0 or (
        season_end.hour != 0 or season_end.minute != 0
    ):
        raise LiveOpsError("season boundaries must align to local midnight")

    catalog = pack.get("catalog")
    if not isinstance(catalog, dict) or set(catalog) != set(KINDS):
        raise LiveOpsError("catalog must define every supported operational category")
    by_id: dict[str, tuple[str, dict]] = {}
    for kind in KINDS:
        records = catalog[kind]
        if not isinstance(records, list) or len(records) > 400:
            raise LiveOpsError("invalid bounded catalog category")
        for record in records:
            if not isinstance(record, dict):
                raise LiveOpsError("catalog record must be an object")
            cid = _id(record.get("id"))
            if cid in by_id:
                raise LiveOpsError("duplicate global content ID")
            if not isinstance(record.get("title"), str) or not record["title"]:
                raise LiveOpsError("catalog item must have a title")
            if type(record.get("ready")) is not bool:
                raise LiveOpsError("content must explicitly indicate asset/game readiness")
            if record.get("source") != "kneekura-local":
                raise LiveOpsError("content may only reference owned local definitions")
            by_id[cid] = (kind, record)
    schedule = pack.get("schedule")
    if not isinstance(schedule, list) or len(schedule) > 1000:
        raise LiveOpsError("invalid bounded schedule entries")
    used: set[str] = set()
    for entry in schedule:
        if not isinstance(entry, dict):
            raise LiveOpsError("schedule entry must be object")
        eid = _id(entry.get("id"))
        if eid in used:
            raise LiveOpsError("duplicate schedule entry ID")
        used.add(eid)
        kind = entry.get("kind")
        cid = entry.get("content_id")
        if kind not in KINDS or cid not in by_id or by_id[cid][0] != kind:
            raise LiveOpsError("unknown or incorrectly typed content reference")
        slot = entry.get("slot")
        if not isinstance(slot, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,31}", slot):
            raise LiveOpsError("invalid display slot")
        if not _is_int(entry.get("priority"), 0, 1000):
            raise LiveOpsError("priority must be a small nonnegative integer")
        req = entry.get("requires", {})
        if not isinstance(req, dict) or set(req) - {"cleared_stages", "owned_units"}:
            raise LiveOpsError("unsupported availability requirement")
        for key in ("cleared_stages", "owned_units"):
            values = req.get(key, [])
            if not isinstance(values, list) or not all(
                isinstance(v, (int, str)) and type(v) is not bool for v in values
            ):
                raise LiveOpsError("malformed local requirement")
        _validate_rule(entry.get("rule"), season_start, season_end)

    # Sweep sorted intervals per (kind,slot,priority) in O(n log n).
    # Two distinct authors must never claim the same display slot with an
    # equal-priority overlapping window; larger priorities explicitly win.
    in_slot: dict[tuple[str, str, int], list[tuple[datetime, datetime, str]]] = {}
    for entry in schedule:
        key = (entry["kind"], entry["slot"], entry["priority"])
        rows = in_slot.setdefault(key, [])
        for begin, end in _rule_intervals(entry["rule"], season_start, season_end):
            rows.append((begin, end, entry["id"]))
    for entries in in_slot.values():
        latest_end = None
        latest_id = None
        for begin, end, eid in sorted(entries, key=lambda x: (x[0], x[1], x[2])):
            if latest_end is not None and begin < latest_end and eid != latest_id:
                raise LiveOpsError("ambiguous same-priority overlapping display slot")
            if latest_end is None or end > latest_end:
                latest_end, latest_id = end, eid
    return pack


def active_at(pack: dict, at: datetime, *, player: dict | None = None) -> dict:
    """Compute snapshot from *in-memory local definitions only*; no state writes."""
    validate_pack(pack)
    if at.tzinfo is None:
        raise LiveOpsError("snapshot time must carry timezone")
    now = at.astimezone(JST)
    season_start = _local_timestamp(pack["season"]["start"])
    season_end = _local_timestamp(pack["season"]["end"])
    result: dict[str, Any] = {
        "channel": CHANNEL, "revision": pack["revision"],
        "pack_status": pack["status"], "local_time": now.isoformat(),
        "active": {kind: [] for kind in KINDS},
        "preview": {kind: [] for kind in KINDS},
        "blocked": [], "season_active": season_start <= now < season_end,
        "actual_stage_clear_modified": False,
        "gacha_draw_performed": False,
        "login_reward_granted": False,
        "network_required": False,
    }
    if not result["season_active"]:
        return result
    by_kind = {kind: {r["id"]: r for r in pack["catalog"][kind]}
               for kind in KINDS}
    player = player or {}
    cleared = set(player.get("cleared_stages", []))
    owned = set(player.get("unlocked_units", []))
    candidates = {}
    for entry in pack["schedule"]:
        if not any(a <= now < b for a, b in _rule_intervals(
            entry["rule"], now - timedelta(days=1), now + timedelta(days=1)
        )):
            continue
        key = (entry["kind"], entry["slot"])
        prev = candidates.get(key)
        if prev is None or (entry["priority"], entry["id"]) > (prev["priority"], prev["id"]):
            candidates[key] = entry
    for entry in sorted(candidates.values(), key=lambda x: (
        KINDS.index(x["kind"]), x["slot"], -x["priority"], x["id"]
    )):
        content = by_kind[entry["kind"]][entry["content_id"]]
        req = entry.get("requires", {})
        reasons = []
        if not content["ready"]:
            reasons.append("ASSETS_OR_GAME_CONTENT_NOT_READY")
        if not set(req.get("cleared_stages", [])).issubset(cleared):
            reasons.append("PLAYER_STAGE_PREREQUISITE")
        if not set(req.get("owned_units", [])).issubset(owned):
            reasons.append("PLAYER_UNIT_PREREQUISITE")
        row = {
            "schedule_id": entry["id"], "kind": entry["kind"],
            "slot": entry["slot"], "content_id": content["id"],
            "title": content["title"], "priority": entry["priority"],
        }
        if reasons:
            result["blocked"].append({**row, "reasons": reasons})
        elif pack["status"] == "draft":
            result["preview"][entry["kind"]].append(row)
        else:
            result["active"][entry["kind"]].append(row)
    return result


def canonical_hash(pack: dict) -> str:
    """Digest for versioned local content bundles, not a publisher signature."""
    validate_pack(pack)
    payload = json.dumps(pack, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
