"""Independent local Kneekura mission epochs and idempotent claim intents.

Mission availability is owned by ops_calendar; this module only calculates
stable JST mission identities and records a player-confirmed completion.
It does NOT determine battle achievements or transfer rewards.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta

from tools.localcore.ops_calendar import JST, LiveOpsError, _id

MISSION_STATE_SCHEMA = "KNEEKURA_MISSION_LEDGER_V1"
MISSION_CADENCES = frozenset({"main", "weekly", "monthly", "special"})


def mission_cycle(at: datetime, cadence: str, *, campaign_id: str | None = None) -> str:
    if not isinstance(at, datetime) or at.tzinfo is None:
        raise LiveOpsError("mission time must have timezone")
    now = at.astimezone(JST)
    if cadence not in MISSION_CADENCES:
        raise LiveOpsError("unknown mission type")
    if cadence == "main":
        return "forever"
    if cadence == "weekly":
        # ISO year+week; week begins Monday at 00:00 JST.
        iso = now.isocalendar()
        return f"weekly:{iso.year:04d}-W{iso.week:02d}"
    if cadence == "monthly":
        return f"monthly:{now.year:04d}-{now.month:02d}"
    if campaign_id is None:
        raise LiveOpsError("special mission must be tied to a local event instance")
    return "special:" + _id(campaign_id)


def initial_mission_ledger() -> dict:
    return {"schema": MISSION_STATE_SCHEMA, "claim_keys": []}


def register_mission_claim(
    ledger: dict,
    *, mission_id: str,
    cadence: str,
    at: datetime,
    completion_evidenced: bool,
    available: bool,
    campaign_id: str | None = None,
) -> tuple[dict, dict]:
    """Record a local claim reservation; actual item grant belongs to host ledger.

    The host must transactionally combine the eventual reward grant with
    claim_keys. A claimed key is not itself evidence of a delivered item.
    """
    _id(mission_id)
    if not isinstance(ledger, dict) or ledger.get("schema") != MISSION_STATE_SCHEMA:
        raise LiveOpsError("unrecognized local mission ledger")
    keys = ledger.get("claim_keys")
    if (not isinstance(keys, list) or len(keys) > 50000 or
        not all(isinstance(k, str) for k in keys) or len(keys) != len(set(keys))):
        raise LiveOpsError("corrupted mission claim ledger")
    if type(available) is not bool or type(completion_evidenced) is not bool:
        raise LiveOpsError("mission requires explicit local eligibility flags")
    if not available:
        return deepcopy(ledger), {"status": "NOT_CURRENTLY_AVAILABLE"}
    if not completion_evidenced:
        return deepcopy(ledger), {"status": "BATTLE_CONDITION_UNVERIFIED"}
    cycle = mission_cycle(at, cadence, campaign_id=campaign_id)
    claim_key = f"{mission_id}|{cycle}"
    if claim_key in keys:
        return deepcopy(ledger), {"status": "ALREADY_RESERVED_NO_DUPLICATE"}
    updated = deepcopy(ledger)
    updated["claim_keys"].append(claim_key)
    return updated, {
        "status": "CLAIM_INTENT_RESERVED_NOT_GRANTED",
        "claim_key": claim_key,
        "actual_item_granted": False,
        "must_commit_atomically_with_reward_in_local_save": True,
    }
