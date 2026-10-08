"""Offline-first five-slot Kneekura login campaign scheduler.

This module is intentionally independent from Battle Cats runtime hooks. It is
pure state-machine logic that can be tested and reused by the future original-UI
provider without tying player history to a server connection.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import json
import random
from typing import Iterable


ACTIVE_SLOT_COUNT = 5


@dataclass(frozen=True)
class Campaign:
    event_id: int
    day_count: int


@dataclass
class ActiveSlot:
    event_id: int
    day_count: int
    progress: int = 0
    not_before_day: int = 0

    @property
    def complete(self) -> bool:
        return self.progress >= self.day_count


@dataclass
class SchedulerState:
    schema_version: int
    seed: str
    cycle: int
    last_observed_day: int | None
    bag: list[int]
    active: list[ActiveSlot]
    completed_event_ids: list[int]

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "seed": self.seed,
            "cycle": self.cycle,
            "last_observed_day": self.last_observed_day,
            "bag": list(self.bag),
            "active": [asdict(slot) for slot in self.active],
            "completed_event_ids": list(self.completed_event_ids),
        }

    @staticmethod
    def from_dict(data: dict) -> "SchedulerState":
        return SchedulerState(
            schema_version=int(data.get("schema_version", 1)),
            seed=str(data["seed"]),
            cycle=int(data.get("cycle", 0)),
            last_observed_day=data.get("last_observed_day"),
            bag=[int(value) for value in data.get("bag", [])],
            active=[
                ActiveSlot(
                    event_id=int(slot["event_id"]),
                    day_count=int(slot["day_count"]),
                    progress=int(slot.get("progress", 0)),
                    not_before_day=int(slot.get("not_before_day", 0)),
                )
                for slot in data.get("active", [])
            ],
            completed_event_ids=[
                int(value) for value in data.get("completed_event_ids", [])
            ],
        )


def _rng(seed: str, cycle: int) -> random.Random:
    digest = hashlib.sha256(f"{seed}:{cycle}".encode("utf-8")).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def _campaign_map(campaigns: Iterable[Campaign]) -> dict[int, Campaign]:
    result: dict[int, Campaign] = {}
    for campaign in campaigns:
        if campaign.day_count <= 0:
            raise ValueError(f"campaign {campaign.event_id} has no claim days")
        if campaign.event_id in result:
            raise ValueError(f"duplicate campaign id {campaign.event_id}")
        result[campaign.event_id] = campaign
    if len(result) < ACTIVE_SLOT_COUNT:
        raise ValueError(
            f"need at least {ACTIVE_SLOT_COUNT} eligible campaigns, got {len(result)}"
        )
    return result


def _new_bag(
    campaign_ids: list[int],
    *,
    seed: str,
    cycle: int,
    excluded: set[int],
) -> list[int]:
    values = [event_id for event_id in campaign_ids if event_id not in excluded]
    rng = _rng(seed, cycle)
    rng.shuffle(values)
    return values


def _refill(
    state: SchedulerState,
    campaigns: dict[int, Campaign],
    *,
    local_day: int,
) -> None:
    while len(state.active) < ACTIVE_SLOT_COUNT:
        active_ids = {slot.event_id for slot in state.active}
        if not state.bag:
            state.cycle += 1
            state.bag = _new_bag(
                sorted(campaigns),
                seed=state.seed,
                cycle=state.cycle,
                excluded=active_ids,
            )
        if not state.bag:
            raise ValueError("unable to refill login campaign slots")

        event_id = state.bag.pop(0)
        if event_id in active_ids:
            continue
        campaign = campaigns[event_id]
        state.active.append(
            ActiveSlot(
                event_id=event_id,
                day_count=campaign.day_count,
                progress=0,
                not_before_day=local_day,
            )
        )


def initialize(
    campaigns: Iterable[Campaign],
    *,
    seed: str,
    local_day: int,
) -> SchedulerState:
    campaign_map = _campaign_map(campaigns)
    state = SchedulerState(
        schema_version=1,
        seed=seed,
        cycle=0,
        last_observed_day=None,
        bag=_new_bag(
            sorted(campaign_map),
            seed=seed,
            cycle=0,
            excluded=set(),
        ),
        active=[],
        completed_event_ids=[],
    )
    _refill(state, campaign_map, local_day=local_day)
    return state


def advance_local_day(
    state: SchedulerState,
    campaigns: Iterable[Campaign],
    *,
    local_day: int,
) -> dict:
    """Advance all active campaigns at most once for a newly observed day.

    - same day: no claim;
    - clock rollback: no claim;
    - large forward jump: one claim per eligible active campaign;
    - completed slots are replaced only after claims and replacements become
      claimable from the *next* local day.
    """

    campaign_map = _campaign_map(campaigns)

    if state.last_observed_day is not None:
        if local_day <= state.last_observed_day:
            return {
                "advanced": False,
                "reason": "same-day-or-clock-rollback",
                "local_day": local_day,
                "claims": [],
                "completed": [],
                "active": [asdict(slot) for slot in state.active],
            }

    claims: list[dict] = []
    completed: list[int] = []

    for slot in state.active:
        if local_day < slot.not_before_day:
            continue
        if slot.complete:
            continue
        slot.progress += 1
        claims.append(
            {
                "event_id": slot.event_id,
                "stamp": slot.progress,
                "day_count": slot.day_count,
            }
        )
        if slot.complete:
            completed.append(slot.event_id)

    if completed:
        state.completed_event_ids.extend(completed)
        state.active = [
            slot for slot in state.active if slot.event_id not in set(completed)
        ]

        # Replacements are deliberately not eligible today.
        before = len(state.active)
        _refill(state, campaign_map, local_day=local_day + 1)
        if len(state.active) != ACTIVE_SLOT_COUNT or len(state.active) < before:
            raise AssertionError("login slot refill failed")

    state.last_observed_day = local_day

    return {
        "advanced": True,
        "reason": "new-local-day",
        "local_day": local_day,
        "claims": claims,
        "completed": completed,
        "active": [asdict(slot) for slot in state.active],
    }


def dumps(state: SchedulerState) -> str:
    return json.dumps(state.to_dict(), ensure_ascii=False, indent=2) + "\n"


def loads(text: str) -> SchedulerState:
    return SchedulerState.from_dict(json.loads(text))
