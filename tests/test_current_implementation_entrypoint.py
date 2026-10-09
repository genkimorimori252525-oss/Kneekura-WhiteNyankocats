"""Prevent future agent sessions from rebuilding Level-0 plans or shipping a cat-game clone.

This is a source-of-truth document regression, NOT a gameplay completion test.
"""
from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / "CURRENT.md"
IDENTITY = ROOT / "PRODUCT_IDENTITY.md"
ROADMAP = ROOT / "docs/roadmap/2026-10-09-original-battle-cats-delivery.md"
AGENTS = ROOT / "AGENTS.md"
README = ROOT / "README.md"
RELEASE_GATES = ROOT / "docs/architecture/product-identity-gates.json"
STATS = ROOT / "docs/updates/manifests/update-1.01.json"


class OneDoorFourImplementationsTests(unittest.TestCase):
    def test_one_current_entrypoint_for_every_new_agent(self):
        for f in (CURRENT, IDENTITY, ROADMAP, AGENTS, README, RELEASE_GATES):
            self.assertTrue(f.is_file(), str(f))
        current = CURRENT.read_text(encoding="utf-8")
        agents = AGENTS.read_text(encoding="utf-8")
        readme = README.read_text(encoding="utf-8")
        self.assertIn("[PRODUCT_IDENTITY.md]", current)
        self.assertIn("docs/roadmap/2026-10-09-original-battle-cats-delivery.md", current)
        self.assertIn("FIRST: READ [CURRENT.md]", agents[:1300])
        self.assertIn("START HERE — CURRENT.md", readme[:600])
        self.assertIn("レベル0", ROADMAP.read_text(encoding="utf-8"))

    def test_four_only_current_workstreams_with_one_live_issue_each(self):
        doc = CURRENT.read_text(encoding="utf-8")
        plan = ROADMAP.read_text(encoding="utf-8")
        for number, name in ((12, "LEVEL"), (13, "MADOKA"),
                             (14, "GODZILLA"), (15, "OFFLINE")):
            self.assertIn(f"/issues/{number}", doc)
            self.assertIn(f"/issues/{number}", plan)
            self.assertIn(name, doc)
        self.assertIn("/issues/11", doc)
        self.assertIn("レベル上限", plan)
        self.assertIn("本家", plan)
        self.assertIn("完全オフライン化", plan)

    def test_pins_user_approved_forms_and_real_game_not_harness(self):
        plan = ROADMAP.read_text(encoding="utf-8")
        for content in ("No.289", "asset288", "form2", "28,000", "750",
                        "4,550", "155", "No.703", "asset702", "form0",
                        "50,000", "150,000", "2,950", "9,800", "500",
                        "550_e", "702_f", "城", "60", "50", "20"):
            self.assertIn(content, plan, content)
        self.assertIn("app/", plan)
        self.assertIn("研究ハーネス", plan)
        self.assertIn("実装", plan)
        self.assertIn("JP15.7.1", plan)

    def test_no_ci_pass_can_claim_finished_without_original_and_offline(self):
        gate = json.loads(RELEASE_GATES.read_text(encoding="utf-8"))
        self.assertFalse(gate["release_ready"])
        self.assertFalse(gate["release_claim_allowed"])
        self.assertEqual(set(gate["axes"]),
                         {"BATTLE_CATS_FIDELITY", "ZERO_EGRESS_AND_LOCAL_AUTHORITY"})
        self.assertFalse(any(check["verified"]
                         for section in gate["axes"].values()
                         for check in section["checks"].values()))
        self.assertIn("検証ハーネス", IDENTITY.read_text(encoding="utf-8"))

    def test_original_manifest_remains_unshipped_with_exact_spec(self):
        data = json.loads(STATS.read_text(encoding="utf-8"))
        self.assertEqual(data["status"], "PREVIEW_ONLY_NOT_INSTALLABLE")
        self.assertEqual(data["approved_specs"]["madoka"]["lv30_attack"], 28000)
        self.assertEqual(data["approved_specs"]["godzilla"]["lv30_sequence_attack"], 150000)
        self.assertEqual(data["approved_specs"]["godzilla"]["castle_hp_per_sequence_max"], 1)
        self.assertFalse(data["release_gates"]["native_exact_stat_hook_attached"])


if __name__ == "__main__":
    unittest.main()
