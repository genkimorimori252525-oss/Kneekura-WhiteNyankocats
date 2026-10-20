"""Regression: no off-season banners or timed maps in the unrestricted pool."""
from copy import deepcopy
from datetime import datetime, timedelta
import json
from pathlib import Path
import unittest

from tools.liveops.gacha_rotation import validate_editorial_policy
from tools.liveops.stage_rotation import stage_rotation_pack
from tools.localcore.ops_calendar import active_at

ROOT=Path(__file__).resolve().parents[1]/'ops/seasons'


class EditorialPolicyTests(unittest.TestCase):
    def read(self,name):
        return json.loads((ROOT/('2026-autumn-'+name+'.json')).read_text(encoding='utf-8'))

    def test_gacha_policy_rejects_collaboration_rotation_and_wrong_season(self):
        selection=self.read('gacha-selection');validate_editorial_policy(selection)
        bad=deepcopy(selection);bad['rotating_set_ids'][0]=958
        with self.assertRaisesRegex(ValueError,'ORDINARY_POOL_CATEGORY'):validate_editorial_policy(bad)
        bad=deepcopy(selection);bad['set_policy']['922']['end']='2026-10-25'
        with self.assertRaisesRegex(ValueError,'SEASON_MISMATCH'):validate_editorial_policy(bad)
        bad=deepcopy(selection);bad['weekly'][3]['set_id']=958
        with self.assertRaisesRegex(ValueError,'COLLABORATION_FREQUENCY'):validate_editorial_policy(bad)

    def ids(self,pack,at):
        rows=active_at(pack,datetime.fromisoformat(at+'+09:00'))['active']
        records={v['id']:v for k in ('stage','event') for v in pack['catalog'][k]}
        return {n for k in ('stage','event') for row in rows[k]
                for n in records[row['content_id']]['original']['native_ids']}

    def test_weekday_and_guerrilla_boundaries_do_not_leak_through_other_slots(self):
        p=self.read('liveops')
        # Tuesday: Monday maps never appear, even at a rotation boundary.
        for hour in range(24):
            ids=self.ids(p,f'2026-10-20T{hour:02}:00:00')
            self.assertIn(1001,ids);self.assertNotIn(1000,ids);self.assertNotIn(1073,ids)
            self.assertNotIn(1027,ids)
            self.assertEqual(1074 in ids,hour in (8,12,19))
            self.assertEqual(1028 in ids,hour in (8,19))
        self.assertNotIn(1074,self.ids(p,'2026-10-20T07:59:59'))
        self.assertNotIn(1074,self.ids(p,'2026-10-20T09:00:00'))
        self.assertIn(1027,self.ids(p,'2026-10-24T00:00:00'))
        self.assertNotIn(1001,self.ids(p,'2026-10-24T00:00:00'))

    def test_month_dates_and_season_boundary_preserve_twenty_plus_specials(self):
        p=self.read('liveops')
        self.assertIn(1007,self.ids(p,'2026-10-22T19:00:00'))
        self.assertNotIn(1007,self.ids(p,'2026-10-22T20:00:00'))
        self.assertNotIn(1007,self.ids(p,'2026-10-23T19:00:00'))
        self.assertIn(1078,self.ids(p,'2026-10-20T11:59:59'))
        self.assertNotIn(1078,self.ids(p,'2026-10-20T12:00:00'))
        self.assertIn(1038,self.ids(p,'2026-10-31T23:59:59'))
        self.assertNotIn(1038,self.ids(p,'2026-11-01T00:00:00'))
        self.assertIn(1174,self.ids(p,'2026-11-01T00:00:00'))
        t=datetime.fromisoformat('2026-10-15T00:00:00')
        while t<datetime(2026,11,30):
            rows=active_at(p,datetime.fromisoformat(t.isoformat()+'+09:00'))['active']
            regular=[r for r in rows['stage'] if r['slot']=='rotation-20']
            self.assertEqual(len(regular),1)
            record=next(r for r in p['catalog']['stage'] if r['id']==regular[0]['content_id'])
            self.assertEqual(len(set(record['original']['native_ids'])),20)
            self.assertEqual(len(rows['gacha']),5)
            t+=timedelta(hours=3)

    def test_timed_map_cannot_be_reintroduced_in_random_pool(self):
        selection=self.read('stage-selection');selection['regular_pools'][0]['native_ids'][0]=1000
        with self.assertRaisesRegex(ValueError,'TIMED_POOL_LEAK'):
            stage_rotation_pack(self.read('liveops'),selection)


if __name__=='__main__':unittest.main()
