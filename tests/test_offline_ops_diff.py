from copy import deepcopy
import json
from pathlib import Path
import unittest

from tools.localcore.ops_calendar import LiveOpsError
from tools.localcore.ops_diff import review_update


PACK = (Path(__file__).resolve().parents[1] /
        "ops/seasons/2026-autumn-prototype.json")


def original():
    return json.loads(PACK.read_text(encoding="utf-8"))


class OperatorRevisionDiffTests(unittest.TestCase):
    def test_one_new_revision_generates_review_receipt_without_write(self):
        before, after = original(), original()
        after["revision"] = 2
        after["catalog"]["notice"][0]["title"] = "試作のお知らせ（更新）"
        stage = deepcopy(after["schedule"][2])
        stage["id"] = "kneekura:schedule:stage-sunday"
        stage["slot"] = "event-map-2"
        stage["rule"]["weekdays"] = [6]
        after["schedule"].append(stage)
        report = review_update(before, after)
        self.assertEqual(report["content_changes"]["updated"],
                         ["kneekura:notice:prototype"])
        self.assertEqual(report["schedule_changes"]["created"],
                         ["kneekura:schedule:stage-sunday"])
        self.assertTrue(report["requires_operator_review"])
        self.assertFalse(report["requires_player_save_migration"])
        self.assertFalse(report["released"])
        self.assertFalse(report["android_content_imported"])
        self.assertEqual(report["network_requests"], 0)

    def test_reject_revision_rollback_or_id_retargeting(self):
        before, after = original(), original()
        with self.assertRaises(LiveOpsError):
            review_update(before, after)
        after["revision"] = 2
        after["schedule"][0]["content_id"] = "kneekura:gacha:local-rotation-b"
        with self.assertRaisesRegex(LiveOpsError, "repointed"):
            review_update(before, after)

    def test_ready_to_unready_is_a_visible_operator_change(self):
        before, after = original(), original()
        after["revision"] = 2
        after["catalog"]["notice"][0]["ready"] = False
        report = review_update(before, after)
        self.assertEqual(report["content_ready_true_to_false"],
                         ["kneekura:notice:prototype"])
        self.assertTrue(report["requires_operator_review"])

    def test_revision_only_or_publication_flag_still_needs_review(self):
        before, after = original(), original()
        after["revision"] = 2
        report = review_update(before, after)
        self.assertTrue(report["requires_operator_review"])
        self.assertFalse(report["publication_status_changed"])
        after["status"] = "published"
        report = review_update(before, after)
        self.assertTrue(report["requires_operator_review"])
        self.assertTrue(report["publication_status_changed"])
        self.assertFalse(report["released"])  # Android release remains a separate gate

    def test_retirement_requires_removing_dependent_schedule(self):
        before, after = original(), original()
        after["revision"] = 2
        after["catalog"]["notice"] = []
        with self.assertRaisesRegex(LiveOpsError, "reference"):
            review_update(before, after)
        after["schedule"] = [
            item for item in after["schedule"]
            if item["kind"] != "notice"
        ]
        report = review_update(before, after)
        self.assertEqual(report["content_changes"]["retired"],
                         ["kneekura:notice:prototype"])
        self.assertEqual(report["schedule_changes"]["retired"],
                         ["kneekura:schedule:notice"])


if __name__ == "__main__":
    unittest.main()
