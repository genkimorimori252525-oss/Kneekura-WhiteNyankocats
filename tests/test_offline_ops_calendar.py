"""Operator schedule CI: exact JST boundary, no false reward/stage/asset claims."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import unittest

from tools.localcore.ops_calendar import (
    CHANNEL, JST, LiveOpsError, active_at, canonical_hash, validate_pack,
)
from tools.localcore.opsctl import windows_in_range


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "ops/seasons/2026-autumn-prototype.json"


def sample_pack() -> dict:
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


def jst(year, month, day, hour=0, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=JST)


class OfflineOperationsCalendarTests(unittest.TestCase):
    def test_season_schema_and_unpublished_assets(self):
        pack = validate_pack(sample_pack())
        self.assertEqual(pack["channel"], CHANNEL)
        self.assertEqual(pack["status"], "draft")
        self.assertEqual(pack["policy"]["login_active_slots"], 5)
        self.assertFalse(pack["policy"]["real_money"])
        self.assertEqual(len(pack["schedule"]), 14)
        self.assertEqual(len(pack["catalog"]["notice"]), 3)
        self.assertEqual(canonical_hash(pack), canonical_hash(deepcopy(pack)))

    def test_jst_weekday_and_preview_never_enters_game(self):
        report = active_at(sample_pack(), jst(2026, 10, 9, 19))
        self.assertTrue(report["season_active"])
        self.assertTrue(any(item["kind"] == "stage" for item in report["blocked"]))
        self.assertEqual({x["content_id"] for x in report["preview"]["notice"]},
                         {item["id"] for item in sample_pack()["catalog"]["notice"]})
        self.assertEqual(report["active"]["stage"], [])
        self.assertEqual(report["active"]["gacha"], [])
        self.assertFalse(report["actual_stage_clear_modified"])
        self.assertFalse(report["gacha_draw_performed"])
        self.assertFalse(report["login_reward_granted"])
        self.assertFalse(report["network_required"])

    def test_ready_content_only_visible_as_preview_until_published(self):
        pack = sample_pack()
        pack["catalog"]["stage"][0]["ready"] = True
        at = jst(2026, 10, 9, 19, 0)
        self.assertEqual(len(active_at(pack, at)["preview"]["stage"]), 1)
        self.assertEqual(active_at(pack, at)["active"]["stage"], [])
        pack["status"] = "published"
        self.assertEqual(len(active_at(pack, at)["active"]["stage"]), 1)
        self.assertEqual(active_at(pack, at)["preview"]["stage"], [])

    def test_prerequisite_blocks_visibility_not_progress(self):
        pack = sample_pack()
        pack["status"] = "published"
        pack["catalog"]["stage"][0]["ready"] = True
        row = next(x for x in pack["schedule"] if x["kind"] == "stage")
        row["requires"] = {"cleared_stages": ["kneekura:stage:intro"]}
        start = jst(2026, 10, 9, 18)
        first = active_at(pack, start)
        self.assertEqual(first["active"]["stage"], [])
        self.assertIn("PLAYER_STAGE_PREREQUISITE", first["blocked"][0]["reasons"] if
                      first["blocked"][0]["kind"] == "stage" else
                      next(x for x in first["blocked"] if x["kind"] == "stage")["reasons"])
        player = {"cleared_stages": ["kneekura:stage:intro"], "unlocked_units": []}
        after = active_at(pack, start, player=player)
        self.assertEqual(len(after["active"]["stage"]), 1)
        self.assertEqual(player["cleared_stages"], ["kneekura:stage:intro"])

    def test_schedule_time_edges_are_half_open(self):
        pack = sample_pack()
        before = active_at(pack, jst(2026, 10, 9, 17, 59))
        at = active_at(pack, jst(2026, 10, 9, 18, 0))
        end = active_at(pack, jst(2026, 10, 9, 23, 0))
        self.assertFalse(any(x["kind"] == "stage" for x in before["blocked"]))
        self.assertTrue(any(x["kind"] == "stage" for x in at["blocked"]))
        self.assertFalse(any(x["kind"] == "stage" for x in end["blocked"]))
        self.assertFalse(active_at(pack, jst(2026, 12, 1))["season_active"])

    def test_priority_resolves_overlapping_gacha_slot(self):
        pack = sample_pack()
        preview = active_at(pack, jst(2026, 10, 10, 12))
        active_gacha_candidates = [x for x in preview["blocked"] if x["kind"] == "gacha"]
        self.assertEqual(len(active_gacha_candidates), 1)
        self.assertEqual(active_gacha_candidates[0]["content_id"],
                         "kneekura:gacha:local-rotation-b")

    def test_overnight_recurring_weekly_uses_previous_day(self):
        pack = sample_pack()
        row = next(x for x in pack["schedule"] if x["kind"] == "stage")
        row["rule"]["from_time"] = "22:00"
        row["rule"]["to_time"] = "02:00"
        saturday = active_at(pack, jst(2026, 10, 10, 1))
        self.assertTrue(any(x["kind"] == "stage" for x in saturday["blocked"]))
        finished = active_at(pack, jst(2026, 10, 10, 2))
        self.assertFalse(any(x["kind"] == "stage" for x in finished["blocked"]))

    def test_monthly_recurring_day_rules(self):
        pack = sample_pack()
        notice = next(x for x in pack["schedule"] if x["kind"] == "notice")
        notice["rule"] = {
            "mode": "monthly", "valid_from": "2026-10-01",
            "valid_until": "2026-12-01", "monthdays": [9],
            "from_time": "09:00", "to_time": "10:00",
        }
        def first_notice_at(when):
            return "kneekura:notice:prototype" in {
                row["content_id"] for row in active_at(pack, when)["preview"]["notice"]
            }
        self.assertTrue(first_notice_at(jst(2026, 10, 9, 9, 30)))
        self.assertTrue(first_notice_at(jst(2026, 11, 9, 9, 30)))
        self.assertFalse(first_notice_at(jst(2026, 10, 10, 9, 30)))

    def test_same_priority_collisions_rejected(self):
        pack = sample_pack()
        overlapping = deepcopy(pack["schedule"][0])
        overlapping["id"] = "kneekura:schedule:gacha-conflict"
        overlapping["content_id"] = "kneekura:gacha:local-rotation-b"
        pack["schedule"].append(overlapping)
        with self.assertRaisesRegex(LiveOpsError, "overlapping"):
            validate_pack(pack)

    def test_external_link_or_wrong_reference_rejected(self):
        for bad_key, value in [("channel", "official-server"),
                               ("timezone", "UTC"),
                               ("status", "RELEASED")]:
            bad = sample_pack()
            bad[bad_key] = value
            with self.assertRaises(LiveOpsError):
                validate_pack(bad)
        bad = sample_pack()
        bad["catalog"]["notice"][0]["url"] = "https://example.com"
        with self.assertRaisesRegex(LiveOpsError, "external URLs"):
            validate_pack(bad)
        bad = sample_pack()
        bad["schedule"][0]["content_id"] = "kneekura:stage:weekly-test-map"
        with self.assertRaisesRegex(LiveOpsError, "reference"):
            validate_pack(bad)
        bad = sample_pack()
        bad["policy"]["network"] = "allowed"
        with self.assertRaises(LiveOpsError):
            validate_pack(bad)

    def test_local_preview_windows_no_remote_update(self):
        windows = windows_in_range(sample_pack(), "2026-10-09", 3)
        self.assertTrue(any(x["kind"] == "stage" for x in windows))
        self.assertTrue(all(x["not_original_ponos_schedule"] for x in windows))
        self.assertTrue(any(x["kind"] == "gacha" and not x["content_ready"] for x in windows))
        with self.assertRaises(LiveOpsError):
            windows_in_range(sample_pack(), "2026-10-09", 91)

    def test_utc_instant_evaluated_in_jst_correctly(self):
        at_utc = datetime(2026, 10, 9, 10, tzinfo=timezone.utc)
        self.assertEqual(active_at(sample_pack(), at_utc)["local_time"],
                         jst(2026, 10, 9, 19).isoformat())
        with self.assertRaises(LiveOpsError):
            active_at(sample_pack(), datetime(2026, 10, 9, 19))


if __name__ == "__main__":
    unittest.main()
