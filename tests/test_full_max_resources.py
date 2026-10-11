"""MAX economy numbers reused from the user's established JP15.7.1 research.

Testable independent-save contract. A passing test is NOT proof that the real
Battle Cats inventory/upgrade screens consume these amounts yet.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from tools.base_mod.build_offline_max_save import (
    ARRAYS_I16, ARRAYS_I32, MAX_VALUES, TALENT_ORB_COUNT,
)
from tools.localcore.full_max_resources import (
    POLICY_PATH, POLICY_ID, LocalEconomyError,
    apply_first_max_resources, load_full_max_policy,
)
from tools.localcore.kneekura_save_v1 import fresh_profile, validate

CURRENCY = {"xp", "catfood", "np"}


class OwnerFullMaxResourcesTests(unittest.TestCase):
    def test_all_20_previous_research_categories_are_kept_exact(self):
        policy = load_full_max_policy()
        self.assertEqual(policy["policy_id"], POLICY_ID)
        self.assertEqual(policy["max_values"], MAX_VALUES)
        self.assertEqual(len(policy["max_values"]), 20)
        self.assertEqual(set(policy["currency_fields"]), CURRENCY)
        self.assertEqual(policy["max_values"]["xp"], 99_999_999)
        self.assertEqual(policy["max_values"]["catfood"], 45_000)
        self.assertEqual(policy["max_values"]["np"], 9_999)
        self.assertEqual(policy["max_values"]["rare_tickets"], 299)
        self.assertEqual(policy["max_values"]["talent_orbs"], 998)
        self.assertEqual(policy["max_values"]["engineers"], 5)
        self.assertEqual(policy["caps_confidence"]["xp"], "exact_native_confirmed")
        self.assertEqual(policy["caps_confidence"]["others"],
                         "prior_editor_research_policy_pending_native_verify")

    def test_all_previous_original_slot_counts_are_exact(self):
        data = load_full_max_policy()
        expected = {key: value[1] for key, value in ARRAYS_I32.items()
                    if key in data["slot_counts"]}
        expected.update({key: value[1] for key, value in ARRAYS_I16.items()
                         if key in data["slot_counts"]})
        expected["talent_orbs"] = TALENT_ORB_COUNT
        self.assertEqual(data["slot_counts"], expected)
        self.assertEqual(len(data["slot_counts"]), 9)

    def test_new_player_starts_with_approved_wallet_and_all_items_max(self):
        save = fresh_profile(10000)
        validate(save)
        policy = load_full_max_policy()
        self.assertEqual(save["resource_policy_revision"], 1)
        for name, cap in policy["max_values"].items():
            if name in CURRENCY:
                self.assertEqual(save["currency"][name], cap)
            elif name in policy["slot_counts"]:
                self.assertEqual(
                    save["inventory"][name],
                    [cap] * policy["slot_counts"][name],
                    name,
                )
            else:
                self.assertEqual(save["inventory"][name], cap)
        self.assertEqual(save["story_chapters"]["itf1"]["progress"], 48)
        self.assertEqual(save["unlocked_units"], [])
        self.assertEqual(save["cleared_stages"], [])
        self.assertEqual(save["local_gacha"], {})

    def test_exactly_once_while_player_can_spend_resources(self):
        start = fresh_profile(0)
        spent = deepcopy(start)
        spent["currency"]["xp"] -= 3500
        spent["currency"]["catfood"] -= 100
        spent["inventory"]["rare_tickets"] -= 1
        self.assertEqual(apply_first_max_resources(spent), spent)
        self.assertLess(spent["currency"]["xp"], MAX_VALUES["xp"])
        self.assertLess(spent["inventory"]["rare_tickets"],
                        MAX_VALUES["rare_tickets"])

    def test_upgrading_preexisting_save_preserves_progress_and_unknown_fields(self):
        old = {
            "schema": "KNEEKURA_SAVE_V1",
            "revision": 17,
            "resource_policy_revision": 0,
            "currency": {"xp": 150, "catfood": 170, "custom_currency": 4},
            "inventory": {"rare_tickets": 27, "catfruit": [998, 12],
                          "custom_owned_item": 5},
            "unlocked_units": [288, 702],
            "cleared_stages": ["kneekura:stage:my-clear"],
            "story_chapters": {"itf2": {"progress": 4}},
            "local_gacha": {"draws": 3},
            "local_events": {"campaign": "player"},
        }
        before = deepcopy(old)
        after = apply_first_max_resources(old)
        self.assertEqual(old, before)
        self.assertEqual(after["revision"], 17)
        self.assertEqual(after["unlocked_units"], old["unlocked_units"])
        self.assertEqual(after["cleared_stages"], old["cleared_stages"])
        self.assertEqual(after["story_chapters"], old["story_chapters"])
        self.assertEqual(after["local_gacha"], old["local_gacha"])
        self.assertEqual(after["local_events"], old["local_events"])
        self.assertEqual(after["currency"]["custom_currency"], 4)
        self.assertEqual(after["inventory"]["custom_owned_item"], 5)
        self.assertEqual(after["inventory"]["catfruit"][:2], [998, 998])
        self.assertEqual(after["inventory"]["rare_tickets"], 299)
        self.assertEqual(after["currency"]["xp"], MAX_VALUES["xp"])
        self.assertEqual(apply_first_max_resources(after), after)

    def test_malformed_existing_values_fail_without_mutating_original(self):
        initial = {"schema": "KNEEKURA_SAVE_V1",
                   "currency": {"catfood": -1}, "unlocked_units": []}
        before = deepcopy(initial)
        with self.assertRaises(LocalEconomyError):
            apply_first_max_resources(initial)
        self.assertEqual(initial, before)
        for bad_inventory in (
            {"catfruit": [1] * 30},
            {"catfruit": [1, "invalid"]},
            {"battle_items": "not an array"},
        ):
            broken = {"schema": "KNEEKURA_SAVE_V1",
                      "currency": {}, "inventory": bad_inventory}
            with self.assertRaises(LocalEconomyError):
                apply_first_max_resources(broken)

    def test_never_mutate_ponos_save_or_accept_unapproved_resource_amounts(self):
        with self.assertRaises(LocalEconomyError):
            apply_first_max_resources({"schema": "PONOS_SAVE_DATA"})
        with self.assertRaises(LocalEconomyError):
            apply_first_max_resources(
                {"schema": "KNEEKURA_SAVE_V1", "inquiry_code": "official"}
            )
        with self.assertRaises(LocalEconomyError):
            apply_first_max_resources(
                {"schema": "KNEEKURA_SAVE_V1", "currency": {}},
                policy={"max_values": {"xp": 999_999_999}},
            )
        with tempfile.TemporaryDirectory() as temp:
            altered = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
            altered["complete_game_integration"] = "CLAIMED_RELEASE"
            target = Path(temp) / "unauthorized-max.json"
            target.write_text(json.dumps(altered), encoding="utf-8")
            with self.assertRaises(LocalEconomyError):
                load_full_max_policy(target)


if __name__ == "__main__":
    unittest.main()
