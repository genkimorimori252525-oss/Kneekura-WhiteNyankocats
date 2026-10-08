from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]


class HookCandidateMatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = json.loads(
            (ROOT / "docs/references/hook-candidate-matrix-jp15.7.1.json")
            .read_text(encoding="utf-8")
        )
        self.by_id = {row["id"]: row for row in self.data["candidates"]}

    def test_network_bridge_is_preferred_and_high_confidence(self) -> None:
        row = self.by_id["network-java-http-bridge"]
        self.assertEqual(row["confidence"], "high")
        joined = " ".join(row["exact_evidence"])
        self.assertIn("newHttpRequest", joined)
        self.assertIn("isNetworkAvailable", joined)

    def test_clock_candidate_forbids_render_clock(self) -> None:
        row = self.by_id["clock-local-day-utility"]
        self.assertEqual(row["confidence"], "medium")
        self.assertIn("Never hook steady_clock/appUpdateDraw", row["product_rule"])

    def test_gacha_is_data_first(self) -> None:
        row = self.by_id["gacha-setting-data"]
        self.assertEqual(row["confidence"], "high-data")
        self.assertIn("data tables", row["phase_c_action"])

    def test_frida_is_not_shipping_dependency(self) -> None:
        row = self.by_id["native-injection-transport"]
        self.assertEqual(row["confidence"], "confirmed")
        self.assertIn("never a final runtime dependency", row["product_rule"])


if __name__ == "__main__":
    unittest.main()