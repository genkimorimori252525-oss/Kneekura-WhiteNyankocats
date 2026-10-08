"""Design-contract assertions only; these do not prove Android integration."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from tools.base_mod.balance_damage_policy import resolve_hit_damage


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "updates" / "kneekura-balance-2026-10-09.json"


class KneekuraBalanceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_status_is_not_claimed_implemented_or_released(self) -> None:
        self.assertEqual(self.manifest["status"], "APPROVED_DESIGN_ONLY_NOT_APPLIED")
        self.assertFalse(self.manifest["safety"]["may_mark_released"])
        for spec in self.manifest["updates"].values():
            self.assertEqual(spec["implementation_status"], "NOT_IMPLEMENTED")

    def test_madoka_form_and_exact_user_approved_values(self) -> None:
        spec = self.manifest["updates"]["UMDK-001"]
        self.assertEqual((spec["catalog_no"], spec["asset_id"], spec["form_index"]), (289, 288, 2))
        approved = spec["approved"]
        self.assertEqual((approved["level_reference"], approved["attack_damage"], approved["standing_range"]), (30, 28000, 750))
        self.assertEqual(approved["production_cost_eoc2"], 4550)
        self.assertEqual(approved["recharge_frames"], 155 * 30)
        self.assertEqual((spec["preserve"]["ld_minimum"], spec["preserve"]["ld_maximum"]), (450, 800))
        self.assertEqual(spec["preserve"]["attack_cycle_frames"], 271)

    def test_godzilla_form_mapping_three_hit_damage_period_and_castle_cap(self) -> None:
        spec = self.manifest["updates"]["UGOD-001"]
        self.assertEqual((spec["catalog_no"], spec["asset_id"], spec["form_index"]), (703, 702, 0))
        self.assertEqual((spec["original_form_name"], spec["next_form_name"]), ("ゴジラにゃんこ", "シン・ゴジラにゃんこ"))
        self.assertEqual(spec["form_target_confirmation"], "USER_CONFIRMED_FIRST_FORM_2026-10-09")
        approved = spec["approved"]
        self.assertEqual(approved["attack_cycle_frames"], 15 * 30)
        self.assertEqual(approved["recharge_frames"], 500 * 30)
        self.assertEqual(approved["level_reference"], 30)
        self.assertEqual(approved["production_cost_eoc2"], 9800)
        self.assertEqual(approved["hit_attack_damage"], [50000] * 3)
        self.assertEqual(sum(approved["hit_attack_damage"]), approved["sequence_attack_damage"])
        self.assertEqual(approved["sequence_attack_damage"], 150000)
        self.assertEqual(approved["attack_hit_frames"], [130, 170, 210])
        self.assertLess(max(approved["attack_hit_frames"]), approved["attack_cycle_frames"])
        self.assertEqual(approved["enemy_castle_damage_cap_per_sequence"], 1)

    def test_castle_three_hits_deal_one_not_three(self) -> None:
        budget = self.manifest["updates"]["UGOD-001"]["approved"]["enemy_castle_damage_cap_per_sequence"]
        outcomes = []
        for hit in [50000,50000,50000]:
            result = resolve_hit_damage(hit,is_castle=True,is_selected_godzilla_form=True,remaining_castle_budget=budget)
            outcomes.append(result.damage_to_target)
            budget = result.remaining_castle_budget
        self.assertEqual(outcomes, [1,0,0])

    def test_enemy_damage_unaffected_and_late_castle_hit_is_one(self) -> None:
        budget = 1
        outcomes = []
        for is_castle in [False,True,True]:
            result = resolve_hit_damage(50000,is_castle=is_castle,is_selected_godzilla_form=True,remaining_castle_budget=budget)
            outcomes.append(result.damage_to_target)
            budget = result.remaining_castle_budget
        self.assertEqual(outcomes, [50000,1,0])
        self.assertEqual(resolve_hit_damage(50000,is_castle=True,is_selected_godzilla_form=False,remaining_castle_budget=1).damage_to_target,50000)

    def test_sequence_reset_and_invalid_budget(self) -> None:
        first = resolve_hit_damage(50000,is_castle=True,is_selected_godzilla_form=True,remaining_castle_budget=1)
        self.assertEqual(first.damage_to_target, 1)
        next_attack = resolve_hit_damage(50000,is_castle=True,is_selected_godzilla_form=True,remaining_castle_budget=1)
        self.assertEqual(next_attack.damage_to_target, 1)
        with self.assertRaises(ValueError):
            resolve_hit_damage(-1,is_castle=True,is_selected_godzilla_form=True,remaining_castle_budget=1)

    def test_no_private_material_and_source_receipts_present(self) -> None:
        self.assertFalse(self.manifest["safety"]["modify_save_data"])
        self.assertFalse(self.manifest["safety"]["write_to_original_apk_in_git"])
        for source in ("DataLocal/unit289.csv","DataLocal/unit703.csv","DataLocal/t_unit.csv"):
            self.assertEqual(len(self.manifest["sources"][source]["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()