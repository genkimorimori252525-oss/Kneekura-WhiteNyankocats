"""Grouped original-format contracts: source-independent expected TSV bytes."""
from copy import deepcopy
from datetime import datetime, timezone
import unittest

from tests.test_offline_ops_calendar import sample_pack, jst
from tools.localcore.ops_calendar import validate_pack
from tools.liveops.original_schedule import (
    ORIGINAL_OWNER_SAVE, ProtocolError, EventWindow, gacha_row, stage_row,
    item_row, stream, prepare_login_day,
)
from tools.liveops.login_scheduler import Campaign, initialize


class OriginalOpsProtocolTests(unittest.TestCase):
    def setUp(self):
        self.window=EventWindow(jst(2026,10,13),jst(2026,10,20))

    def test_original_gacha_vector_and_guarantee_field_order(self):
        row=gacha_row(self.window,49,cost=150,chances=(0,7000,2500,500,0),
                      guaranteed=(0,0,0,1,0),message='にーくら開催')
        expected=('20261013\t0\t20261020\t0\t150701\t150701\t0\t0\t1\t1\t'
                  '49\t150\t0\t0\t0\t0\t7000\t0\t2500\t0\t500\t1\t0\t0\tにーくら開催')
        self.assertEqual(row,expected)
        self.assertEqual(stream([row]),('[start]\n'+expected+'\n[end]\n').encode('utf-8'))

    def test_stage_stream_contains_availability_ids_only(self):
        row=stage_row(self.window,(1006,4002))
        self.assertEqual(row,'20261013\t0\t20261020\t0\t150701\t150701\t0\t0\t2\t1006\t4002')
        self.assertNotIn('clear',row)
        with self.assertRaises(ProtocolError):stage_row(self.window,(0,))
        with self.assertRaises(ProtocolError):stage_row(self.window,(1006,1006))

    def test_item_row_keeps_original_item_namespace_and_once_flag(self):
        row=item_row(self.window,100001,21,1,title='レアチケット',message='ログイン特典')
        self.assertEqual(row.split('\t')[8:],['100001','21','1','レアチケット','ログイン特典','0','0','0'])

    def test_gacha_rejects_invalid_distribution_and_guarantee(self):
        for chances in [(0,1,2,3,4),(-1,7001,2500,500,0),(True,6999,2500,1000,0)]:
            with self.subTest(chances=chances),self.assertRaises(ProtocolError):
                gacha_row(self.window,49,cost=150,chances=chances)
        with self.assertRaises(ProtocolError):
            gacha_row(self.window,49,cost=150,chances=(0,7000,2500,500,0),guaranteed=(0,0,0,0,1))

    def test_protocol_rejects_control_characters_and_invalid_numbers(self):
        for message in ['x\ny','x\ty','x\0y']:
            with self.subTest(message=message),self.assertRaises(ProtocolError):
                item_row(self.window,10,6,100,title=message,message='safe')
        for amount in [0,-1,True,2**31]:
            with self.subTest(amount=amount),self.assertRaises(ProtocolError):
                item_row(self.window,10,6,amount,title='safe',message='safe')
        with self.assertRaises(ProtocolError):stream(['[end]'])

    def test_window_is_aware_minute_aligned_and_half_open(self):
        with self.assertRaises(ProtocolError):EventWindow(datetime(2026,10,13),jst(2026,10,20))
        with self.assertRaises(ProtocolError):EventWindow(self.window.end,self.window.start)
        with self.assertRaises(ProtocolError):EventWindow(self.window.start.replace(second=1),self.window.end)
        utc=EventWindow(datetime(2026,10,12,15,tzinfo=timezone.utc),self.window.end)
        self.assertEqual(stage_row(utc,(1006,)),stage_row(self.window,(1006,)))

    def test_new_original_owner_mode_is_explicit_and_legacy_calendar_still_valid(self):
        old=sample_pack();validate_pack(old)
        new=deepcopy(old);new['policy']['owner_save']=ORIGINAL_OWNER_SAVE
        self.assertIs(validate_pack(new),new)
        bad=deepcopy(new);bad['policy']['owner_save']='official-user-save'
        with self.assertRaises(ValueError):validate_pack(bad)

    def test_login_day_is_proposed_without_mutating_original_state(self):
        campaigns=[Campaign(n,7) for n in range(10,18)]
        state=initialize(campaigns,seed='ops-contract',local_day=100)
        original=state.to_dict()
        candidate,report=prepare_login_day(original,campaigns,local_day=101)
        self.assertEqual(original,state.to_dict())
        self.assertEqual(len(report['claims']),5)
        self.assertEqual(candidate['last_observed_day'],101)
        same,same_report=prepare_login_day(candidate,campaigns,local_day=101)
        self.assertEqual(same_report['claims'],[])
        self.assertEqual(same,candidate)
        rollback,rollback_report=prepare_login_day(candidate,campaigns,local_day=90)
        self.assertEqual(rollback_report['claims'],[])
        self.assertEqual(rollback,candidate)

    def test_finished_login_slots_refill_for_the_next_day_only(self):
        campaigns=[Campaign(n,1) for n in range(10,21)]
        state=initialize(campaigns,seed='ops-contract',local_day=100)
        candidate,report=prepare_login_day(state.to_dict(),campaigns,local_day=101)
        self.assertEqual(len(report['claims']),5)
        self.assertTrue(all(slot['not_before_day']==102 for slot in candidate['active']))
        self.assertEqual(len(candidate['active']),5)


if __name__=='__main__':unittest.main()
