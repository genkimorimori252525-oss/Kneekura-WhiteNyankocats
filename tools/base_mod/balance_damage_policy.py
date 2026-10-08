"""Reference-only hit resolution contract, NOT wired to the Android game.

Use this small model only for tests/design validation. Integrating equivalent
logic at the original game's actual base-HP deduction site remains required.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DamageResult:
    damage_to_target: int
    remaining_castle_budget: int


def resolve_hit_damage(
    raw_damage: int,
    *,
    is_castle: bool,
    is_selected_godzilla_form: bool,
    remaining_castle_budget: int,
) -> DamageResult:
    """Model UGOD-001's per-three-hit castle policy.

    Caller creates an independent budget of 1 for each attacking cat instance
    and each new attack sequence; do not share budgets between simultaneous
    attackers. Damage to non-castle enemy units is never capped.
    """
    if raw_damage < 0 or remaining_castle_budget < 0:
        raise ValueError("damage and budget must be nonnegative")
    if not (is_castle and is_selected_godzilla_form):
        return DamageResult(raw_damage, remaining_castle_budget)
    effective = min(raw_damage, remaining_castle_budget)
    return DamageResult(effective, remaining_castle_budget - effective)