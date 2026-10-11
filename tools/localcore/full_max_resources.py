"""Owner-approved MAX initial economy for the future *real Battle Cats* offline host.

Uses the previous pinned JP15.7.1 research amounts without ever editing JP
SAVE_DATA, creating an account, or manipulating the unfinished Android
Stage Fidelity Alpha. This is a reusable local-save economic *data contract*,
NOT an original Battle Cats UI integration or evidence of native legal caps.

Initial creation / one-time migration raises the relevant local balances and
items to the owner-approved research maxima, once only. It deliberately does
NOT auto-refill after a legitimate purchase, grant unearned cat ownership,
clear stages, alter levels, or reset gacha or mission history.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

POLICY_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs/updates/manifests/full-max-start-jp15.7.1.json"
)
POLICY_ID = "kneekura:profile:full-max-jp1571"
POLICY_REVISION = 1
ORIGINAL_EXPORT_SHA = (
    "38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56"
)


class LocalEconomyError(ValueError):
    pass


def load_full_max_policy(path: Path = POLICY_PATH) -> dict:
    """Validate the content record, not an official PONOS save or account."""
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise LocalEconomyError("unreadable local MAX policy") from exc
    if not isinstance(policy, dict) or (
        policy.get("schema_version") != 1
        or policy.get("policy_id") != POLICY_ID
        or policy.get("revision") != POLICY_REVISION
        or policy.get("mode") != "OWNER_APPROVED_INITIAL_FULL_MAX"
        or policy.get("game_anchor") != "JP15.7.1"
        or policy.get("owner_export_sha256") != ORIGINAL_EXPORT_SHA
        or policy.get("source_reference")
        != "tools/base_mod/build_offline_max_save.py::MAX_VALUES"
        or policy.get("one_time_initialization") is not True
        or policy.get("reapply_after_spending") is not False
        or policy.get("complete_game_integration") != "NOT_YET_CONNECTED"
    ):
        raise LocalEconomyError("MAX policy origin/semantics changed unexpectedly")
    caps = policy.get("max_values")
    counts = policy.get("slot_counts")
    currencies = policy.get("currency_fields")
    if (not isinstance(caps, dict) or not isinstance(counts, dict)
        or not isinstance(currencies, list) or
        set(currencies) != {"xp", "catfood", "np"} or
        len(currencies) != 3):
        raise LocalEconomyError("invalid local balance categories")
    if (len(caps) != 20 or len(counts) != 9 or
        set(currencies) - set(caps) or set(counts) - set(caps)):
        raise LocalEconomyError("incomplete MAX policy categories")
    if any(type(amount) is not int or not 0 <= amount <= 99_999_999
           for amount in caps.values()):
        raise LocalEconomyError("invalid maximum amounts")
    if any(type(slots) is not int or not 1 <= slots <= 310
           for slots in counts.values()):
        raise LocalEconomyError("invalid item slot counts")
    if caps.get("xp") != 99_999_999 or caps.get("catfood") != 45_000 or (
        caps.get("np") != 9_999 or caps.get("engineers") != 5
        or caps.get("talent_orbs") != 998
    ):
        raise LocalEconomyError("frozen prior JP research maxima changed")
    if policy.get("caps_confidence", {}).get("xp") != "exact_native_confirmed":
        raise LocalEconomyError("native-vs-research confidence lost")
    safety = policy.get("safety")
    if not isinstance(safety, dict) or not safety or any(
        value is not False for value in safety.values()
    ):
        raise LocalEconomyError("MAX profile cannot affect original accounts or play")
    return policy


def _take_local_max(value: Any, minimum: int, *, category: str) -> int:
    if type(value) is not int or value < 0:
        raise LocalEconomyError("invalid existing local amount for " + category)
    # If an older independent save contains more than an unverified editor cap,
    # never reduce/erase the user's earned balance.
    return max(value, minimum)


def apply_first_max_resources(profile: dict, *,
                              policy: dict | None = None) -> dict:
    """Idempotently populate local economy only on an eligible first migration.

    Existing unrelated player-state fields, including ownership and chapters,
    are deep-copied unchanged; a damaged profile fails closed.
    """
    if not isinstance(profile, dict) or profile.get("schema") != "KNEEKURA_SAVE_V1":
        raise LocalEconomyError("only independent Kneekura player profiles supported")
    if any(key in profile for key in (
        "original_SAVE_DATA", "account_token", "inquiry_code", "ponos_account",
    )):
        raise LocalEconomyError("official account/save cannot enter local economy")
    approved = load_full_max_policy()
    if policy is not None and policy != approved:
        raise LocalEconomyError("unapproved MAX amount manifest")
    revision = profile.get("resource_policy_revision", 0)
    if type(revision) is not int or revision < 0:
        raise LocalEconomyError("invalid local resource migration marker")
    result = deepcopy(profile)
    if revision >= POLICY_REVISION:
        return result  # No infinite item refill after spending.
    wallet = result.setdefault("currency", {})
    inventory = result.setdefault("inventory", {})
    if not isinstance(wallet, dict) or not isinstance(inventory, dict):
        raise LocalEconomyError("malformed previous local economy")
    currency_names = set(approved["currency_fields"])
    for key, cap in approved["max_values"].items():
        if key in currency_names:
            wallet[key] = _take_local_max(wallet.get(key, 0), cap, category=key)
        elif key in approved["slot_counts"]:
            count = approved["slot_counts"][key]
            previous = inventory.get(key, [])
            if not isinstance(previous, list) or len(previous) > count:
                raise LocalEconomyError("invalid previous local inventory slots: " + key)
            inventory[key] = [
                _take_local_max(previous[i] if i < len(previous) else 0,
                                cap, category=f"{key}[{i}]")
                for i in range(count)
            ]
        else:
            inventory[key] = _take_local_max(
                inventory.get(key, 0), cap, category=key
            )
    result["resource_policy_revision"] = POLICY_REVISION
    return result
