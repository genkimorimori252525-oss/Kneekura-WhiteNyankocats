from datetime import datetime
import unittest

from tools.localcore.mission_cycles import (
    mission_cycle, initial_mission_ledger, register_mission_claim,
)
from tools.localcore.ops_calendar import JST, LiveOpsError


def at(year, month, day, hour=0, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=JST)


class MissionCyclesLocalTests(unittest.TestCase):
    def test_jst_monday_weekly_reset_boundary(self):
        # 2026-10-12 is Monday.
        before = mission_cycle(at(2026, 10, 11, 23, 59), "weekly")
        after = mission_cycle(at(2026, 10, 12, 0, 0), "weekly")
        self.assertNotEqual(before, after)
        self.assertIn("weekly:", before)
        self.assertEqual(after, mission_cycle(at(2026, 10, 18, 23), "weekly"))

    def test_monthly_and_main_mission_epoch(self):
        sep = mission_cycle(at(2026, 9, 30, 23, 59), "monthly")
        octo = mission_cycle(at(2026, 10, 1, 0), "monthly")
        self.assertNotEqual(sep, octo)
        self.assertEqual(mission_cycle(at(2026, 10, 9), "main"), "forever")

    def test_special_mission_bound_to_a_specific_local_campaign(self):
        with self.assertRaises(LiveOpsError):
            mission_cycle(at(2026, 10, 9), "special")
        self.assertEqual(
            mission_cycle(at(2026, 10, 9), "special",
                          campaign_id="kneekura:event:autumn-campaign"),
            "special:kneekura:event:autumn-campaign",
        )

    def test_idempotent_claim_intent_requires_completion_and_availability(self):
        ledger = initial_mission_ledger()
        args = dict(mission_id="kneekura:mission:weekly-test", cadence="weekly",
                    at=at(2026, 10, 9), completion_evidenced=True, available=True)
        no = dict(args, available=False)
        state, outcome = register_mission_claim(ledger, **no)
        self.assertEqual(outcome["status"], "NOT_CURRENTLY_AVAILABLE")
        self.assertEqual(state, ledger)
        not_complete = dict(args, completion_evidenced=False)
        _, result = register_mission_claim(ledger, **not_complete)
        self.assertEqual(result["status"], "BATTLE_CONDITION_UNVERIFIED")
        state, record = register_mission_claim(ledger, **args)
        self.assertFalse(record["actual_item_granted"])
        self.assertEqual(record["status"], "CLAIM_INTENT_RESERVED_NOT_GRANTED")
        self.assertEqual(len(state["claim_keys"]), 1)
        state2, repeated = register_mission_claim(state, **args)
        self.assertEqual(repeated["status"], "ALREADY_RESERVED_NO_DUPLICATE")
        self.assertEqual(state2, state)
        self.assertEqual(ledger["claim_keys"], [])
        next_week = dict(args, at=at(2026, 10, 12))
        state3, next_result = register_mission_claim(state, **next_week)
        self.assertEqual(next_result["status"], "CLAIM_INTENT_RESERVED_NOT_GRANTED")
        self.assertEqual(len(state3["claim_keys"]), 2)

    def test_refuses_foreign_account_or_bad_ledger(self):
        with self.assertRaises(LiveOpsError):
            register_mission_claim(
                initial_mission_ledger(), mission_id="official:reward:cloud",
                cadence="main", at=at(2026, 10, 9),
                completion_evidenced=True, available=True,
            )
        with self.assertRaises(LiveOpsError):
            register_mission_claim(
                {"schema": "KNEEKURA_MISSION_LEDGER_V1", "claim_keys": ["same", "same"]},
                mission_id="kneekura:mission:weekly-test", cadence="weekly",
                at=at(2026, 10, 9), completion_evidenced=True, available=True,
            )


if __name__ == "__main__":
    unittest.main()
