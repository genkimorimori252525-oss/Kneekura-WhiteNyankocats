import unittest

from tools.liveops.login_scheduler import (
    ACTIVE_SLOT_COUNT,
    Campaign,
    advance_local_day,
    initialize,
)


class LoginSchedulerTest(unittest.TestCase):
    def campaigns(self):
        return [Campaign(event_id=1000 + i, day_count=2 + (i % 3)) for i in range(12)]

    def test_initializes_exactly_five_unique_slots(self):
        state = initialize(self.campaigns(), seed="profile-A", local_day=100)
        self.assertEqual(len(state.active), ACTIVE_SLOT_COUNT)
        self.assertEqual(len({slot.event_id for slot in state.active}), ACTIVE_SLOT_COUNT)

    def test_same_day_and_clock_rollback_do_not_claim_twice(self):
        state = initialize(self.campaigns(), seed="profile-A", local_day=100)
        first = advance_local_day(state, self.campaigns(), local_day=100)
        self.assertTrue(first["advanced"])
        self.assertEqual(len(first["claims"]), 5)

        same = advance_local_day(state, self.campaigns(), local_day=100)
        self.assertFalse(same["advanced"])
        self.assertEqual(same["claims"], [])

        back = advance_local_day(state, self.campaigns(), local_day=99)
        self.assertFalse(back["advanced"])
        self.assertEqual(back["claims"], [])

    def test_large_forward_jump_grants_one_stamp_only(self):
        state = initialize(self.campaigns(), seed="profile-A", local_day=100)
        advance_local_day(state, self.campaigns(), local_day=100)
        before = {slot.event_id: slot.progress for slot in state.active}
        result = advance_local_day(state, self.campaigns(), local_day=1000)
        self.assertTrue(result["advanced"])
        for slot in state.active:
            if slot.event_id in before:
                self.assertLessEqual(slot.progress - before[slot.event_id], 1)

    def test_completed_slot_refills_but_new_campaign_waits_until_next_day(self):
        campaigns = [Campaign(event_id=2000 + i, day_count=1 if i < 5 else 3) for i in range(12)]
        state = initialize(campaigns, seed="one-day", local_day=10)
        first_ids = {slot.event_id for slot in state.active}
        result = advance_local_day(state, campaigns, local_day=10)

        completed = set(result["completed"])
        self.assertTrue(completed)
        self.assertEqual(len(state.active), 5)
        replacement = [slot for slot in state.active if slot.event_id not in first_ids]
        self.assertTrue(replacement)
        self.assertTrue(all(slot.progress == 0 for slot in replacement))
        self.assertTrue(all(slot.not_before_day == 11 for slot in replacement))

        # Same day still does nothing.
        again = advance_local_day(state, campaigns, local_day=10)
        self.assertFalse(again["advanced"])
        self.assertTrue(all(slot.progress == 0 for slot in replacement))

    def test_deterministic_seed_is_reproducible(self):
        a = initialize(self.campaigns(), seed="same", local_day=1)
        b = initialize(self.campaigns(), seed="same", local_day=1)
        self.assertEqual(
            [slot.event_id for slot in a.active],
            [slot.event_id for slot in b.active],
        )


if __name__ == "__main__":
    unittest.main()
