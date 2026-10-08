from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
POOL = ROOT / "tools/liveops/build_login_pool.py"


class LoginPoolContractTest(unittest.TestCase):
    def test_jp1571_pool_is_version_pinned_and_fail_closed(self):
        text = POOL.read_text(encoding="utf-8")
        self.assertIn("MIN_CAMPAIGN_DAYS = 6", text)
        self.assertIn("len(eligible) != 106", text)
        self.assertIn("contains-system-negative-reward-kind", text)
        self.assertIn("require_nonempty_reward_each_day", text)
        self.assertIn("DailyLoginEventData.csv", text)


if __name__ == "__main__":
    unittest.main()
