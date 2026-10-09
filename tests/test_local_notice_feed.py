"""Operator-authored i-button news never depends on online PONOS notices."""
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import unittest

from tools.localcore.notice_feed import notice_feed
from tools.localcore.ops_calendar import JST, LiveOpsError

PACK = (Path(__file__).resolve().parents[1] /
        "ops/seasons/2026-autumn-prototype.json")


def draft():
    return json.loads(PACK.read_text(encoding="utf-8"))


def at(day, hour=12, minute=0):
    return datetime(2026, 10, day, hour, minute, tzinfo=JST)


class OfflineJollyNoticesTests(unittest.TestCase):
    def test_authored_news_is_not_falsely_published_in_draft(self):
        pack = draft()
        self.assertEqual(pack["status"], "draft")
        self.assertEqual(notice_feed(pack, at(9, 11))["news"], [])
        preview = notice_feed(pack, at(9, 11), allow_draft_preview=True)
        self.assertEqual(preview["status"], "DRAFT_PREVIEW_ONLY")
        self.assertEqual(len(preview["news"]), 3)
        self.assertFalse(preview["player_save_changed"])
        self.assertEqual(preview["network_requests"], 0)
        self.assertTrue(preview["no_external_assets"])

    def test_news_are_locally_scheduled_and_display_in_order(self):
        pack = draft()
        pack["status"] = "published"
        before = notice_feed(pack, at(9, 9, 30))["news"]
        self.assertEqual(len(before), 1)
        current = notice_feed(pack, at(9, 10, 30))
        self.assertEqual(len(current["news"]), 3)
        self.assertEqual(current["news"][0]["category"], "重要")
        self.assertTrue(current["news"][0]["pinned"])
        self.assertTrue(all(entry["body"] for entry in current["news"]))
        self.assertTrue(all(entry["source"] == "kneekura-local"
                            for entry in current["news"]))
        self.assertEqual(notice_feed(pack, datetime(
            2026, 12, 1, tzinfo=JST))["news"], [])

    def test_notice_not_ready_never_shown_even_if_scheduled(self):
        pack = draft()
        pack["status"] = "published"
        pack["catalog"]["notice"][0]["ready"] = False
        contents = notice_feed(pack, at(9, 11))["news"]
        self.assertEqual(len(contents), 2)
        self.assertNotIn("kneekura:notice:prototype",
                         [record["id"] for record in contents])

    def test_remote_url_or_bad_category_rejected(self):
        pack = draft()
        pack["catalog"]["notice"][0]["body"] = "https://external.example/test"
        with self.assertRaises(LiveOpsError):
            notice_feed(pack, at(9, 12), allow_draft_preview=True)
        pack = draft()
        pack["catalog"]["notice"][0]["category"] = "公式PONOSリリース"
        with self.assertRaises(LiveOpsError):
            notice_feed(pack, at(9, 12), allow_draft_preview=True)

    def test_calendar_and_news_share_same_notice_slot_ids(self):
        from tools.localcore.ops_calendar import active_at
        pack = draft()
        pack["status"] = "published"
        moment = at(9, 12)
        snapshot = active_at(pack, moment)
        feed = notice_feed(pack, moment)
        self.assertEqual({n["schedule_id"] for n in feed["news"]},
                         {n["schedule_id"] for n in snapshot["active"]["notice"]})
        self.assertEqual(pack["catalog"]["gacha"][0]["ready"], False)
        self.assertEqual(pack["catalog"]["stage"][0]["ready"], False)

    def test_news_notices_do_not_grant_rewards_or_mutate_pack(self):
        pack = draft()
        original = deepcopy(pack)
        report = notice_feed(pack, at(9, 12), allow_draft_preview=True)
        self.assertEqual(pack, original)
        self.assertNotIn("reward_granted", report)
        self.assertNotIn("stage_cleared", report)
        self.assertEqual(report["network_requests"], 0)


if __name__ == "__main__":
    unittest.main()
