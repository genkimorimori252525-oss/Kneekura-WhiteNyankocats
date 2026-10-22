"""The stage programme must offer native families without manufacturing clears."""
import base64
from datetime import datetime, timedelta
import json
from pathlib import Path
import unittest

from tools.liveops.original_calendar import compile_calendar
from tools.liveops.original_ops_bundle import validate_bundle
from tools.liveops.stage_rotation import stage_rotation_pack
from tools.localcore.ops_calendar import active_at

ROOT=Path(__file__).resolve().parents[1]/'ops/seasons'


class StageProgramTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack=json.loads((ROOT/'2026-autumn-liveops.json').read_text(encoding='utf-8'))
        cls.selection=json.loads((ROOT/'2026-autumn-stage-selection.json').read_text(encoding='utf-8'))
        cls.records={r['id']:r for k in ('stage','event') for r in cls.pack['catalog'][k]}

    def snapshot(self,at):
        return active_at(self.pack,datetime.fromisoformat(at+'+09:00'))['active']

    def ids(self,at):
        rows=self.snapshot(at)
        return {n for k in ('stage','event') for r in rows[k]
                for n in self.records[r['content_id']]['original']['native_ids']}

    def rotation(self,at):
        row=next(r for r in self.snapshot(at)['stage'] if r['slot']=='rotation-20')
        return tuple(self.records[row['content_id']]['original']['native_ids'])

    def test_all_requested_programme_categories_have_source_ids(self):
        categories={r.get('program_category') for r in self.records.values()}
        self.assertTrue({'crazed','manic','cyclone','advent','behemoth','catfruit',
            'guerrilla','weekday','awakening','assault','weekend','enigma','monthly','event','catamin'}<=categories)
        self.assertLessEqual(len(self.pack['catalog']['stage']),400)
        self.assertLessEqual(len(self.pack['schedule']),1000)
        self.assertFalse(any(r.get('requires') for r in self.pack['schedule']))

    def test_crazed_manic_and_lil_maps_are_monthly_not_random(self):
        for i in range(9):
            for first,n in [(1,1017+i),(3,1102+i),(2,1130+i)]:
                day=first+3*i
                self.assertIn(n,self.ids(f'2026-11-{day:02}T12:00:00'))
                other=day+1
                self.assertNotIn(n,self.ids(f'2026-11-{other:02}T12:00:00'))
        self.assertIn(1137,self.ids('2026-10-23T12:00:00'))
        self.assertIn(1109,self.ids('2026-10-24T12:00:00'))

    def test_catamin_is_its_own_native_family_and_expiry_is_eight(self):
        before=self.ids('2026-10-23T07:59:59');after=self.ids('2026-10-23T08:00:00')
        self.assertEqual({n for n in before if n//1000==14},set(range(14005,14052)))
        self.assertFalse(any(n//1000==14 for n in after))
        self.assertFalse(any(14000<=n<=14004 for n in before))

    def test_current_catfruit_behemoth_weekend_and_enigma_windows(self):
        for day in range(23,30):
            self.assertIn(1422,self.ids(f'2026-10-{day}T15:00:00'))
        self.assertFalse(set(range(1097,1102))&self.ids('2026-10-23T15:00:00'))
        self.assertIn(31000,self.ids('2026-10-23T12:00:00'))
        self.assertNotIn(31000,self.ids('2026-10-23T16:00:00'))
        self.assertNotIn(1250,self.ids('2026-10-23T12:00:00'))
        self.assertIn(1250,self.ids('2026-10-24T12:00:00'))
        self.assertNotIn(1277,self.ids('2026-10-23T21:59:59'))
        self.assertIn(1277,self.ids('2026-10-23T22:00:00'))
        # Native Enigma ownership/identification remains a gameplay mechanism.
        self.assertFalse(any(n//1000==25 for n in self.ids('2026-10-23T22:00:00')))

    def test_monthly_assault_handoff_at_eleven_and_weekly_deck_variety(self):
        self.assertIn(24026,self.ids('2026-11-01T10:59:59'))
        self.assertNotIn(24026,self.ids('2026-11-01T11:00:00'))
        self.assertIn(24028,self.ids('2026-11-01T11:00:00'))
        self.assertNotIn(24028,self.ids('2026-11-16T11:00:00'))
        self.assertIn(24029,self.ids('2026-11-16T11:00:00'))
        current=self.rotation('2026-10-23T12:00:00')
        self.assertEqual(len(set(current)),20)
        self.assertNotEqual(set(current),set(self.rotation('2026-10-23T14:00:00')))
        self.assertNotEqual(set(current),set(self.rotation('2026-10-30T12:00:00')))
        self.assertTrue(self.selection['rotation_weekly_shuffle'])

    def test_native_sale_projection_keeps_distinct_catamin_and_monthly_maps(self):
        bindings={r['id']:dict(r['original'],kind=k) for k in ('gacha','stage','event','mission')
                  for r in self.pack['catalog'][k]}
        raw,_=compile_calendar(self.pack,bindings,start_date='2026-10-23',days=1)
        lines=base64.b64decode(validate_bundle(raw)['server_files']['sale.tsv']).decode().splitlines()[1:-1]
        observed=set()
        for line in lines:
            values=line.split('\t');observed.update(int(n) for n in values[9:])
        self.assertIn(1137,observed);self.assertNotIn(1136,observed)
        self.assertIn(1422,observed);self.assertIn(14040,observed)
        self.assertFalse(set(range(14000,14005))&observed)

    def test_reauthoring_does_not_duplicate_notice_or_touch_gacha(self):
        rebuilt=stage_rotation_pack(self.pack,self.selection)
        self.assertEqual(rebuilt['catalog']['gacha'],self.pack['catalog']['gacha'])
        self.assertEqual(sum(r['id']=='kneekura:notice:stage-rotation-20'
                             for r in rebuilt['catalog']['notice']),1)

    def test_placeholder_banners_cannot_be_reintroduced(self):
        from copy import deepcopy
        selection=deepcopy(self.selection)
        self.assertEqual(set(selection['excluded_native_ids']),{1144,1153,1310,1311})
        selection['regular_pools'][0]['native_ids'][0]=1310
        with self.assertRaisesRegex(ValueError,'UNPUBLISHED_BANNER'):
            stage_rotation_pack(self.pack,selection)


if __name__=='__main__':unittest.main()
