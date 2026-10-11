"""No official save, network, or Android needed to test Kneekura local core."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from tools.localcore.kneekura_save_v1 import (
    BACKUP_NAME, SAVE_NAME, LocalSaveError, fresh_profile,
    advance_energy, weekly_event_active, load_local, write_local,
)


class KneekuraIndependentCoreTests(unittest.TestCase):
    def test_local_60s_regen_retains_partial_progress(self):
        s = fresh_profile(1_000_000)
        s["energy"]["amount"] = 2
        result, code = advance_energy(s, 1_095_000)
        self.assertEqual(code, "LOCAL_REGENERATED")
        self.assertEqual(result["energy"]["amount"], 3)
        self.assertEqual(result["energy"]["remainder_ms"], 35000)
        later, _ = advance_energy(result, 1_120_000)
        self.assertEqual(later["energy"]["amount"], 4)
        self.assertEqual(later["energy"]["remainder_ms"], 0)
        self.assertEqual(s["energy"]["amount"], 2)

    def test_no_server_time_penalty_for_clock_rollback(self):
        s = fresh_profile(500_000)
        s["energy"]["amount"] = 7
        updated, code = advance_energy(s, 100)
        self.assertEqual(code, "CLOCK_WENT_BACK_IGNORED_NO_BAN")
        self.assertEqual(updated, s)

    def test_unlimited_energy_can_be_user_selected(self):
        s = fresh_profile(100, cap=800, energy_mode="unlimited")
        s["energy"]["amount"] = 0
        got, code = advance_energy(s, 100)
        self.assertEqual(code, "LOCAL_UNLIMITED")
        self.assertEqual(got["energy"]["amount"], 800)

    def test_weekly_event_uses_only_supplied_jst_clock(self):
        friday = int(datetime(2026, 10, 9, 3, tzinfo=timezone.utc).timestamp()*1000)
        self.assertTrue(weekly_event_active(utc_ms=friday, weekday=4,
                                            from_hour=11, to_hour=14))
        self.assertFalse(weekly_event_active(utc_ms=friday, weekday=5,
                                             from_hour=11, to_hour=14))

    def test_atomic_save_recovers_previous_good_state(self):
        with tempfile.TemporaryDirectory() as t:
            folder = Path(t)
            s = fresh_profile(0)
            write_local(folder, s)
            changed = deepcopy(s)
            changed["currency"]["xp"] = 5000
            write_local(folder, changed)
            self.assertEqual(load_local(folder)[0]["currency"]["xp"], 5000)
            (folder / SAVE_NAME).write_text("corrupt")
            recovered, source = load_local(folder)
            self.assertEqual(source, "BACKUP_RECOVERABLE")
            self.assertEqual(recovered["currency"]["xp"], 99_999_999)
            self.assertTrue((folder / BACKUP_NAME).exists())

    def test_corruption_has_no_account_ban_or_data_import(self):
        s = fresh_profile(0)
        s["inquiry_code"] = "do-not-import"
        with tempfile.TemporaryDirectory() as t:
            folder = Path(t)
            with self.assertRaises(LocalSaveError):
                write_local(folder, s)
            self.assertFalse((folder / SAVE_NAME).exists())
            (folder / SAVE_NAME).write_text("broken")
            with self.assertRaises(LocalSaveError):
                load_local(folder)

    def test_inputs_are_validated_without_network(self):
        with self.assertRaises(LocalSaveError):
            fresh_profile(0, cap=-10)
        with self.assertRaises(LocalSaveError):
            fresh_profile(0, seconds_per_point=0)
        with self.assertRaises(LocalSaveError):
            weekly_event_active(utc_ms=0, weekday=7, from_hour=9, to_hour=17)


if __name__ == "__main__":
    unittest.main()
