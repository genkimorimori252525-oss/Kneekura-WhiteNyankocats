"""Offline deterministic five-slot login campaigns (pure, no reward writes).

Implements the older Post-EoC Kneekura spec:
- five simultaneously displayed slots if five eligible local definitions exist
- shuffle-bag local rotation, one stamp/campaign/JST day
- replacements become claimable next local day, not immediately
- no duplicate active definitions, no reward duplication on a clock rollback
- emits an idempotency intent; the host must later grant/reconcile rewards
No official account, server time, networking, original save or SDK.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, date, timedelta
import hashlib
import json
import random
from typing import Any

from tools.localcore.ops_calendar import JST, LiveOpsError, _id

ROTATION_SCHEMA = "KNEEKURA_LOGIN_ROTATION_V1"
EPOCH = date(1970, 1, 1)
SLOTS = 5


def local_day(at: datetime) -> int:
    if at.tzinfo is None:
        raise LiveOpsError("login time must include timezone")
    day = at.astimezone(JST).date()
    return (day - EPOCH).days


def _definitions(data: dict[str, int]) -> dict[str, int]:
    if not isinstance(data, dict) or len(data) > 250:
        raise LiveOpsError("invalid bounded login content pool")
    definitions = {}
    for cid, count in data.items():
        _id(cid)
        if type(count) is not int or not 1 <= count <= 365:
            raise LiveOpsError("invalid local login reward cycle length")
        definitions[cid] = count
    return definitions


def _shuffled(pool: list[str], seed: int, generation: int,
              avoid: str | None) -> list[str]:
    order = sorted(pool)
    raw = f"{seed}:{generation}".encode("ascii")
    local_seed = int(hashlib.sha256(raw).hexdigest(), 16)
    random.Random(local_seed).shuffle(order)
    if avoid and len(order) > 1 and order[0] == avoid:
        order.append(order.pop(0))
    return order


def _fill(state: dict, now_day: int, *, replacement: bool = False) -> None:
    while len(state["active"]) < min(SLOTS, len(state["definitions"])):
        used = {slot["id"] for slot in state["active"]}
        candidates = [cid for cid in state["bag"] if cid not in used]
        if not candidates:
            state["generation"] += 1
            state["bag"] = _shuffled(
                list(state["definitions"]), state["seed"],
                state["generation"], state["last_completed_id"])
            candidates = [cid for cid in state["bag"] if cid not in used]
        if not candidates:
            break
        cid = candidates[0]
        state["bag"].remove(cid)
        taken = {slot["slot"] for slot in state["active"]}
        free = next(s for s in range(1, SLOTS + 1) if s not in taken)
        state["active"].append({
            "slot": free, "id": cid, "stamps": 0,
            "max_stamps": state["definitions"][cid],
            "cycle": state["generation"],
            "last_claimed_day": None,
            "eligible_from_day": now_day + (1 if replacement else 0),
        })
    state["active"].sort(key=lambda slot: slot["slot"])


def initial_rotation(campaign_max_stamps: dict[str, int], *,
                     seed: int, today: int) -> dict:
    definitions = _definitions(campaign_max_stamps)
    if type(seed) is not int or not 0 <= seed <= 2**63 - 1:
        raise LiveOpsError("invalid local random seed")
    if type(today) is not int:
        raise LiveOpsError("invalid local day")
    state = {
        "schema": ROTATION_SCHEMA, "seed": seed,
        "definitions": definitions, "generation": 0,
        "bag": _shuffled(list(definitions), seed, 0, None),
        "active": [], "last_observed_day": today,
        "last_completed_id": None,
        "completed_count": 0,
    }
    _fill(state, today)
    return state


def claim_stamp(state: dict, cid: str, today: int) -> tuple[dict, dict]:
    """Returns updated state and grant *intent*; not a reward transfer."""
    if not isinstance(state, dict) or state.get("schema") != ROTATION_SCHEMA:
        raise LiveOpsError("incompatible independent login rotation state")
    _id(cid)
    if type(today) is not int:
        raise LiveOpsError("invalid local day")
    result = deepcopy(state)
    if today < result["last_observed_day"]:
        return result, {"status": "CLOCK_ROLLBACK_NO_CLAIM"}
    result["last_observed_day"] = today
    row = next((r for r in result["active"] if r["id"] == cid), None)
    if row is None:
        return result, {"status": "NOT_IN_ACTIVE_FIVE"}
    if today < row["eligible_from_day"]:
        return result, {"status": "REPLACEMENT_WAIT_UNTIL_NEXT_DAY"}
    if row["last_claimed_day"] == today:
        return result, {"status": "ALREADY_CLAIMED_TODAY"}
    row["last_claimed_day"] = today
    row["stamps"] += 1
    stamp_no = row["stamps"]
    claim_key = f"{cid}:{row['cycle']}:{stamp_no}"
    if stamp_no >= row["max_stamps"]:
        result["last_completed_id"] = cid
        result["completed_count"] += 1
        result["active"] = [r for r in result["active"] if r["id"] != cid]
        _fill(result, today, replacement=True)
    return result, {
        "status": "STAMP_RECORDED_NO_REWARD_GRANTED",
        "campaign_id": cid, "stamp": stamp_no,
        "claim_key": claim_key,
        "reward_pending_host_idempotency": True,
    }


def eligible_login_templates(pack: dict) -> dict[str, int]:
    """Only ready local campaigns with a verified bounded daily-reward length."""
    from tools.localcore.ops_calendar import validate_pack
    validate_pack(pack)
    definitions = {}
    for item in pack["catalog"]["login"]:
        if not item["ready"]:
            continue
        count = item.get("max_stamps")
        if type(count) is not int or not 1 <= count <= 365:
            raise LiveOpsError("ready login campaign missing local reward length")
        definitions[item["id"]] = count
    return _definitions(definitions)
