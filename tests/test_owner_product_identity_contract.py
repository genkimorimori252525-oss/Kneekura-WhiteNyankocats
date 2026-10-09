"""Guard the owner's product identity across session handoffs.

This is an architectural contract test, NOT a fidelity verification test.
Static documentation checks cannot establish that Battle Cats is playable.
"""
from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
IDENTITY = ROOT / "PRODUCT_IDENTITY.md"
GATES = ROOT / "docs/architecture/product-identity-gates.json"
AGENTS = ROOT / "AGENTS.md"
README = ROOT / "README.md"
PHILOSOPHY = ROOT / "docs/architecture/design-philosophy.md"
OFFLINE_AUDIT = ROOT / "docs/architecture/2026-10-09-complete-local-offline-audit.md"

FIDLITY_CHECKS = {
    "original_base_and_ui",
    "original_battle_rules_and_timings",
    "original_characters_enemies_and_assets",
    "original_animation_sound_and_transitions",
    "original_stages_rewards_gacha_and_progression",
    "owner_madoka_godzilla_levelcaps_future1_in_same_game",
}
OFFLINE_CHECKS = {
    "cold_start_no_network_egress",
    "no_original_account_or_rejected_save",
    "local_play_gacha_events_and_save_reboot",
    "safe_local_updates_backup_rollback",
}


class OwnerProductIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = IDENTITY.read_text(encoding="utf-8")
        cls.gate = json.loads(GATES.read_text(encoding="utf-8"))

    def test_real_battle_cats_not_lookalike_is_authoritative(self):
        for important in (
            "にゃんこ大戦争", "別ゲーム", "最上位", "完全オフライン",
            "本家", "戦闘", "アニメーション", "ガチャ",
            "独立Android", "検証ハーネス", "オーナー",
        ):
            self.assertIn(important, self.doc, important)
        self.assertIn("PRODUCT_IDENTITY.md", AGENTS.read_text(encoding="utf-8"))
        self.assertIn("PRODUCT_IDENTITY.md", README.read_text(encoding="utf-8"))
        self.assertIn("PRODUCT_IDENTITY.md", PHILOSOPHY.read_text(encoding="utf-8"))
        self.assertIn("PRODUCT_IDENTITY.md", OFFLINE_AUDIT.read_text(encoding="utf-8"))

    def test_both_game_fidelity_and_zero_egress_are_hard_requirements(self):
        gate = self.gate
        self.assertEqual(gate["identity"], "KNEEKURA_REAL_BATTLE_CATS_EXPERIENCE")
        self.assertEqual(gate["source"], "owner-confirmed-2026-10-09")
        self.assertEqual(set(gate["axes"]), {
            "BATTLE_CATS_FIDELITY", "ZERO_EGRESS_AND_LOCAL_AUTHORITY"
        })
        self.assertTrue(all(axis["required"] for axis in gate["axes"].values()))
        self.assertEqual(
            set(gate["axes"]["BATTLE_CATS_FIDELITY"]["checks"]), FIDLITY_CHECKS
        )
        self.assertEqual(
            set(gate["axes"]["ZERO_EGRESS_AND_LOCAL_AUTHORITY"]["checks"]),
            OFFLINE_CHECKS
        )
        for axis in gate["axes"].values():
            for name, item in axis["checks"].items():
                self.assertIs(type(item["verified"]), bool, name)
                self.assertIsInstance(item["evidence"], list, name)
                if item["verified"]:
                    self.assertTrue(
                        item["evidence"],
                        f"{name} cannot be called verified with no evidence",
                    )
        self.assertIs(type(gate["release_ready"]), bool)
        self.assertIs(type(gate["release_claim_allowed"]), bool)
        self.assertEqual(gate["release_ready"], gate["release_claim_allowed"])
        if gate["release_ready"]:
            self.assertEqual(gate["owner_acceptance"], "ACCEPTED")
            self.assertTrue(all(
                state["verified"]
                for axis in gate["axes"].values()
                for state in axis["checks"].values()
            ))

    def test_current_alpha_cannot_be_mislabeled_product(self):
        gate = self.gate
        self.assertEqual(
            gate["standalone_alpha_role"], "RESEARCH_HARNESS_NOT_PLAYABLE_PRODUCT"
        )
        self.assertFalse(gate["policy"]["harness_can_be_described_as_game_finished"])
        self.assertFalse(
            gate["policy"]["allow_substitute_clone_without_original_parity"]
        )
        self.assertTrue(gate["policy"]["requires_owner_explicit_acceptance_for_product"])
        self.assertTrue(gate["policy"]["requires_comparative_jp_game_evidence"])
        self.assertTrue(gate["policy"]["original_assets_stay_private"])
        self.assertFalse(gate["release_ready"])
        self.assertEqual(gate["owner_acceptance"], "NOT_GIVEN")

    def test_no_old_offline_independent_host_waiver_remains_unqualified(self):
        philosophy = PHILOSOPHY.read_text(encoding="utf-8")
        audit = OFFLINE_AUDIT.read_text(encoding="utf-8")
        self.assertIn("supersedes prior override", philosophy)
        self.assertIn("experimental compatibility technique only", philosophy)
        self.assertIn("PRODUCT-IDENTITY CORRECTION", audit)
        self.assertIn("original Battle Cats gameplay fidelity", audit)
        self.assertIn("research", audit.lower())

    def test_owner_approved_customization_and_release_truth(self):
        for essential in (
            "Lv60", "Lv30", "28,000", "150,000", "2,950",
            "未来編1章", "最高のお宝", "完成済み", "JP15.7.1",
        ):
            self.assertIn(essential, self.doc, essential)
        self.assertIn(
            "research harness",
            README.read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
