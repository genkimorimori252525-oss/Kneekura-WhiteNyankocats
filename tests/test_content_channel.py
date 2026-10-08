from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CHANNEL = ROOT / "tools/liveops/build_default_channel.py"


class ContentChannelContractTest(unittest.TestCase):
    def test_revision_one_is_offline_first_and_fail_safe(self):
        text = CHANNEL.read_text(encoding="utf-8")
        self.assertIn('"channel": "kneekura-main"', text)
        self.assertIn('"revision": 1', text)
        self.assertIn('"game_anchor": "jp-15.7.1"', text)
        self.assertIn('"active_slots": 5', text)
        self.assertIn('"offline_cache_required": True', text)
        self.assertIn('"last_known_good_required": True', text)

    def test_unfinished_runtime_providers_are_explicit(self):
        text = CHANNEL.read_text(encoding="utf-8")
        self.assertIn('"status": "pending-original-ui-integration"', text)
        self.assertIn('"provider": "deferred"', text)
        self.assertIn('"signature_status": "not-yet-enabled"', text)

    def test_channel_does_not_embed_player_progress(self):
        text = CHANNEL.read_text(encoding="utf-8")
        self.assertNotIn("SAVE_DATA", text)
        self.assertIn('"custom_stages"', text)
        self.assertIn('"provider": "data-pack"', text)


if __name__ == "__main__":
    unittest.main()
