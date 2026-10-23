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

    def test_catamin_all_47_maps_are_available_all_day_without_retired_maps(self):
        for at in ('2026-10-23T00:00:00','2026-10-23T07:59:59',
                   '2026-10-23T08:00:00','2026-10-23T17:18:00',
                   '2026-10-23T23:59:59','2026-10-24T00:00:00'):
            with self.subTest(at=at):
                self.assertEqual({n for n in self.ids(at) if n//1000==14},
                                 set(range(14005,14052)))

    def test_catamin_projection_keeps_separate_daily_windows_on_rebuild(self):
        from copy import deepcopy
        pack=deepcopy(self.pack)
        bindings={r['id']:dict(r['original'],kind=k) for k in ('gacha','stage','event','mission')
                  for r in pack['catalog'][k]}
        for entry in pack['schedule']:
            ids=bindings.get(entry['content_id'],{}).get('native_ids',[])
            if ids and all(n//1000==14 for n in ids):
                entry['rule']['to_time']='00:00'
        def rows(start,days):
            raw,_=compile_calendar(pack,bindings,start_date=start,days=days)
            lines=base64.b64decode(validate_bundle(raw)['server_files']['sale.tsv']).decode().splitlines()[1:-1]
            return [r for line in lines if (r:=line.split('\t'))
                    and any(14000<=int(n)<15000 for n in r[9:])]
        full=rows('2026-10-23',2)
        self.assertEqual([r[:4] for r in full],
                         [['20261023','0','20261024','0'],['20261024','0','20261025','0']])
        self.assertTrue(all({int(n) for n in r[9:]}==set(range(14005,14052)) for r in full))
        self.assertEqual(rows('2026-10-24',1),[full[1]])

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

    def test_monthly_assault_handoff_at_eleven_without_unrestricted_rotation(self):
        self.assertIn(24026,self.ids('2026-11-01T10:59:59'))
        self.assertNotIn(24026,self.ids('2026-11-01T11:00:00'))
        self.assertIn(24028,self.ids('2026-11-01T11:00:00'))
        self.assertNotIn(24028,self.ids('2026-11-16T11:00:00'))
        self.assertIn(24029,self.ids('2026-11-16T11:00:00'))
        self.assertIn(1161,self.ids('2026-11-28T12:00:00'))
        self.assertIn(1209,self.ids('2026-11-22T12:00:00'))
        self.assertNotIn(1161,self.ids('2026-11-27T12:00:00'))
        self.assertFalse(self.selection['rotation_enabled'])
        self.assertFalse(any(r['slot']=='rotation-20' for r in self.pack['schedule']))

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
        selection['timed'].append(dict(native_ids=[1310],title='bad',mode='monthly',
            monthdays=[1],from_time='00:00',to_time='00:00'))
        with self.assertRaisesRegex(ValueError,'UNPUBLISHED_BANNER'):
            stage_rotation_pack(self.pack,selection)

    def test_flower_exact_two_minute_window_and_no_off_season_awakening(self):
        for at,present in [('2026-11-02T14:21:59',False),('2026-11-02T14:22:00',True),
                ('2026-11-02T14:23:59',True),('2026-11-02T14:24:00',False),
                ('2026-11-03T14:22:00',False),('2026-11-22T14:22:00',True)]:
            self.assertEqual(1148 in self.ids(at),present)
        self.assertIn(1092,self.ids('2026-10-23T12:00:00'))
        self.assertNotIn(1092,self.ids('2026-11-01T11:00:00'))
        self.assertNotIn(1093,self.ids('2026-11-16T10:59:59'))
        self.assertIn(1093,self.ids('2026-11-16T11:00:00'))
        for n in [1337,1384,1349,1252,1253,1307,1310,1311]:
            self.assertNotIn(n,self.ids('2026-10-23T12:00:00'))

    def test_ex_awakening_fixed_dates_and_daily_local_xp(self):
        self.assertIn(1049,self.ids('2026-11-01T12:00:00'))
        self.assertNotIn(1049,self.ids('2026-11-03T12:00:00'))
        self.assertIn(1058,self.ids('2026-10-23T12:00:00'))
        self.assertNotIn(1058,self.ids('2026-10-25T12:00:00'))
        for d in range(23,30):
            for h in [9,15,21]:
                self.assertTrue({1028,1059,1124,1155,1319}<=self.ids(f'2026-10-{d}T{h:02}:00:00'))


if __name__=='__main__':unittest.main()
