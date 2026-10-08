"""Contract regression tests for approved Kneekura balance targets.

No owned APK, decrypted CSV or SAVE_DATA is needed for these checks.
"""
import json
from pathlib import Path
import unittest

MANIFEST_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "updates"
    / "2026-10-09-umdkgodz-targets.json"
)


class KneekuraBalanceSpecContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        cls.m = cls.data["updates"]["UMDK-001"]
        cls.g = cls.data["updates"]["GODZ-001"]

    def test_release_must_not_claim_an_applied_update(self):
        self.assertEqual(self.data["game_anchor"], "JP 15.7.1")
        self.assertEqual(self.data["status"], "DESIGN_ONLY_NOT_APPLIED")
        self.assertIn("NOT_IMPLEMENTED", self.m["status"])
        self.assertIn("NOT_IMPLEMENTED", self.g["status"])

    def test_identities_and_form_isolation(self):
        self.assertEqual((self.m["unit"]["catalog_no"], self.m["unit"]["asset_id"], self.m["unit"]["form_index"]), (289, 288, 2))
        self.assertEqual((self.g["unit"]["catalog_no"], self.g["unit"]["asset_id"], self.g["unit"]["form_index"]), (703, 702, 0))
        self.assertEqual(self.g["reference_enemy"]["t_unit_row_index"], 552)
        self.assertTrue(self.m["unchanged"]["other_forms"])
        self.assertTrue(self.m["unchanged"]["unique_death_animation"])
        self.assertTrue(self.g["protected"]["other_forms"])
        self.assertTrue(self.g["protected"]["enemy_definition"])

    def test_exact_approved_madoka_targets(self):
        expected = {
            "base_hp": 55250, "attack": 28000, "standing_range": 750,
            "ld_min_range": 450, "ld_max_range": 800,
            "deploy_cost_eoc_ch2": 4550, "recharge_seconds": 155,
        }
        self.assertEqual(self.m["approved_at_level30"], expected)
        self.assertEqual(self.m["unchanged"]["attack_cycle_frames"], 271)
        self.assertEqual(self.m["unchanged"]["foreswing_frames"], 72)

    def test_madoka_native_representability_is_not_falsified(self):
        raw = self.m["pinned_original_raw"]
        self.assertEqual(raw["lv1_attack"] * 17, 31450)
        self.assertEqual(raw["base_cost"] * 3 // 2, 4350)
        self.assertEqual(2 * raw["recharge_field"] - 254, 4146)
        candidate = self.m["simple_csv_mapping"]
        self.assertEqual(candidate["standing_range_column"], 5)
        self.assertEqual(candidate["new_value"], 750)
        self.assertEqual(2 * candidate["candidate_raw"] - 254, 155 * 30)
        self.assertEqual(self.m["native_precision_gate"]["native_attack_below"]["lv30"], 1647 * 17)
        self.assertEqual(self.m["native_precision_gate"]["native_attack_above"]["lv30"], 1648 * 17)
        self.assertNotEqual(28000 % 17, 0)
        self.assertNotEqual(4550 * 2 % 3, 0)
        self.assertFalse(self.m["native_precision_gate"]["exact_28000_from_integer_raw_under_pinned_growth"])

    def test_godzilla_base_and_stage_multiplier_are_separate(self):
        e = self.g["reference_enemy"]
        self.assertEqual(e["base_attack_total"], sum(e["three_hit_damage"]))
        self.assertEqual(e["hit_frames"], [130, 170, 210])
        self.assertEqual((e["standing_range"], e["ld_min_range"], e["ld_max_range"]), (3800, 2300, 3800))
        self.assertEqual(self.g["approved"], {"deploy_cost_eoc_ch2": 9800, "recharge_seconds": 500})
        self.assertEqual(2 * self.g["candidate_recharge_raw_for_reference_tech"] - 254, 15000)
        self.assertNotEqual(9800 * 2 % 3, 0)
        for stage in self.g["stage_examples"]:
            self.assertEqual(stage["hp"], e["base_hp"] * stage["hp_pct"] // 100)
            self.assertEqual(stage["attack_total"], e["base_attack_total"] * stage["attack_pct"] // 100)
        self.assertIn("which_enemy_stage_hp_attack_magnification_to_use", self.g["undecided"])

    def test_public_repository_must_not_contain_owned_payloads(self):
        for filename, digest in self.data["source_sha256"].items():
            self.assertTrue(filename.startswith("DataLocal/"))
            self.assertEqual(len(digest), 64)
            self.assertTrue(all(c in "0123456789abcdef" for c in digest))
        self.assertTrue(self.m["unchanged"]["save_data"])
        self.assertTrue(self.g["protected"]["save_data"])
        self.assertTrue(any("No user APK" in gate for gate in self.data["validation_gates"]))


if __name__ == "__main__":
    unittest.main()