"""The five-slot campaign rotation has no server, banned-state or item grants."""
from datetime import datetime
import json
from pathlib import Path
import unittest

from tools.localcore.login_rotation import (
    SLOTS, initial_rotation, claim_stamp, local_day,
    eligible_login_templates,
)
from tools.localcore.ops_calendar import JST, LiveOpsError


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "ops/seasons/2026-autumn-prototype.json"


class LocalLoginRotationTests(unittest.TestCase):
    def test_starts_exactly_five_when_content_sufficient_and_is_repeatable(self):
        pools = {f"kneekura:login:campaign-{i}": 3 for i in range(9)}
        a = initial_rotation(pools, seed=31415, today=20735)
        b = initial_rotation(pools, seed=31415, today=20735)
        self.assertEqual(a, b)
        self.assertEqual(len(a["active"]), SLOTS)
        self.assertEqual(len({s["id"] for s in a["active"]}), SLOTS)
        self.assertEqual(set(s["slot"] for s in a["active"]), {1, 2, 3, 4, 5})

    def test_one_stamp_per_day_and_explicit_pending_reward_intent(self):
        pools = {"kneekura:login:alpha": 3, "kneekura:login:bravo": 3,
                 "kneekura:login:charlie": 3, "kneekura:login:delta": 3,
                 "kneekura:login:echo": 3, "kneekura:login:foxtrot": 3}
        state = initial_rotation(pools, seed=1, today=100)
        cid = state["active"][0]["id"]
        state, out = claim_stamp(state, cid, 100)
        self.assertEqual(out["status"], "STAMP_RECORDED_NO_REWARD_GRANTED")
        self.assertTrue(out["reward_pending_host_idempotency"])
        self.assertEqual(out["stamp"], 1)
        again, rejected = claim_stamp(state, cid, 100)
        self.assertEqual(rejected["status"], "ALREADY_CLAIMED_TODAY")
        self.assertEqual(again, state)
        after, rejected = claim_stamp(state, cid, 99)
        self.assertEqual(rejected["status"], "CLOCK_ROLLBACK_NO_CLAIM")
        self.assertEqual(after, state)
        next_day, out = claim_stamp(state, cid, 101)
        self.assertEqual(out["stamp"], 2)
        self.assertEqual(next_day["completed_count"], 0)

    def test_finished_campaign_swaps_one_slot_no_same_day_chain_claim(self):
        pools = {f"kneekura:login:series-{i}": 1 for i in range(7)}
        state = initial_rotation(pools, seed=7, today=200)
        before = {r["id"] for r in state["active"]}
        first_id = state["active"][0]["id"]
        state, out = claim_stamp(state, first_id, 200)
        self.assertEqual(out["stamp"], 1)
        self.assertEqual(state["completed_count"], 1)
        self.assertEqual(len(state["active"]), 5)
        replacements = {r["id"] for r in state["active"]} - before
        self.assertEqual(len(replacements), 1)
        replacement_id = next(iter(replacements))
        immediate, status = claim_stamp(state, replacement_id, 200)
        self.assertEqual(status["status"], "REPLACEMENT_WAIT_UNTIL_NEXT_DAY")
        self.assertEqual(immediate, state)
        next_day, granted = claim_stamp(state, replacement_id, 201)
        self.assertEqual(granted["status"], "STAMP_RECORDED_NO_REWARD_GRANTED")
        self.assertEqual(next_day["completed_count"], 2)

    def test_recycle_bag_and_never_duplicate_active_campaign(self):
        pool = {f"kneekura:login:short-{i}": 1 for i in range(5)}
        state = initial_rotation(pool, seed=123, today=250)
        selected = state["active"][0]["id"]
        for day in (250, 251, 252):
            state, grant = claim_stamp(state, selected, day)
            self.assertEqual(grant["status"], "STAMP_RECORDED_NO_REWARD_GRANTED")
            self.assertEqual(len(state["active"]), 5)
            self.assertEqual(len({r["id"] for r in state["active"]}), 5)
        self.assertEqual(state["completed_count"], 3)

    def test_jst_calendar_day_conversion(self):
        observed = local_day(datetime(2026, 10, 9, 23, tzinfo=JST))
        later = local_day(datetime(2026, 10, 10, 0, tzinfo=JST))
        self.assertEqual(later, observed + 1)
        with self.assertRaises(LiveOpsError):
            local_day(datetime(2026, 10, 9, 23))

    def test_prototype_login_definitions_not_pretend_ready(self):
        pack = json.loads(PACK.read_text(encoding="utf-8"))
        self.assertEqual(eligible_login_templates(pack), {})
        pack["catalog"]["login"][0]["ready"] = True
        with self.assertRaises(LiveOpsError):
            eligible_login_templates(pack)
        pack["catalog"]["login"][0]["max_stamps"] = 7
        self.assertEqual(len(eligible_login_templates(pack)), 1)

    def test_invalid_or_official_account_like_ids_rejected(self):
        with self.assertRaises(LiveOpsError):
            initial_rotation({"official:login:token": 7}, seed=1, today=1)
        with self.assertRaises(LiveOpsError):
            initial_rotation({"kneekura:login:a": 0}, seed=1, today=1)
        with self.assertRaises(LiveOpsError):
            initial_rotation({}, seed=-1, today=1)


if __name__ == "__main__":
    unittest.main()
