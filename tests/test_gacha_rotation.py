"""Grouped original gacha categories and owner-requested calendar boundaries."""
import base64
from datetime import datetime
import json
from pathlib import Path
import unittest

from tools.liveops.gacha_rotation import gacha_rotation_pack
from tools.liveops.original_calendar import compile_calendar
from tools.liveops.original_catalogue import bind_catalogue
from tools.liveops.original_ops_bundle import build_bundle, validate_bundle
from tools.liveops.original_schedule import EventWindow, ProtocolError, gacha_group_row, stream
from tools.localcore.ops_calendar import active_at
from tools.analyze_gacha_foundation import EXACT_JP_15_7_1_EXPORT_SHA256

ROOT=Path(__file__).resolve().parents[1]


class GachaRotationTests(unittest.TestCase):
    def pack(self):
        base=json.loads((ROOT/'ops/seasons/2026-autumn-ops-rotation.json').read_text(encoding='utf-8'))
        selection=json.loads((ROOT/'ops/seasons/2026-autumn-gacha-selection.json').read_text(encoding='utf-8'))
        return gacha_rotation_pack(base,selection)

    def active(self,pack,at):
        snapshot=active_at(pack,datetime.fromisoformat(at+'+09:00'))
        records={v['id']:v['original'] for v in pack['catalog']['gacha']}
        return {row['slot']:records[row['content_id']]['set_id'] for row in snapshot['active']['gacha']}

    def test_three_distinct_rare_slots_rotate_at_three_hours_and_weekly_slot_is_stable(self):
        pack=self.pack()
        before=self.active(pack,'2026-10-15T02:59:00')
        after=self.active(pack,'2026-10-15T03:00:00')
        for selected in (before,after):
            self.assertEqual(len(selected),5)
            self.assertEqual(len({v for slot,v in selected.items() if slot.startswith('rare-')}),3)
            self.assertEqual(selected['normal-0'],0)
            self.assertEqual(selected['normal-1'],3)
        self.assertEqual(before['rare-weekly'],after['rare-weekly'])
        for slot in ('rare-rotating-1','rare-rotating-2'):
            self.assertNotEqual(before[slot],after[slot])
        self.assertNotEqual(self.active(pack,'2026-10-18T23:59:00')['rare-weekly'],
                            self.active(pack,'2026-10-19T00:00:00')['rare-weekly'])
        self.assertEqual(pack['catalog']['stage'],json.loads(
            (ROOT/'ops/seasons/2026-autumn-ops-rotation.json').read_text(encoding='utf-8'))['catalog']['stage'])

    def test_original_wire_groups_three_rare_sections_separately_from_normal_and_rejects_bad_counts(self):
        window=EventWindow(datetime.fromisoformat('2026-10-15T00:00:00+09:00'),
                           datetime.fromisoformat('2026-10-15T03:00:00+09:00'))
        entries=[dict(set_id=i,cost=150,chances=[0,7000,2500,500,0],message='local')
                 for i in (49,452,958)]
        rare=gacha_group_row(window,entries)
        normal=gacha_group_row(window,[dict(set_id=1,cost=0,chances=[10000,0,0,0,0])],gacha_type=0)
        self.assertEqual(rare.split('\t')[8:10],['1','3'])
        self.assertEqual(len(rare.split('\t')),8+2+3*15)
        self.assertEqual(normal.split('\t')[8:12],['0','1','1','0'])
        data=build_bundle(window,revision=1,files={'sale.tsv':stream([]),
             'gatya.tsv':stream([rare,normal]),'item.tsv':stream([])})
        self.assertEqual(base64.b64decode(validate_bundle(data)['server_files']['gatya.tsv']),stream([rare,normal]))
        broken=json.loads(data);parts=rare.split('\t');parts[9]='2'
        broken['server_files']['gatya.tsv']=base64.b64encode(stream(['\t'.join(parts)])).decode()
        with self.assertRaises(ProtocolError):validate_bundle(json.dumps(broken).encode())
        with self.assertRaises(ProtocolError):gacha_group_row(window,[entries[0],entries[0]])
        with self.assertRaises(ProtocolError):gacha_group_row(window,[dict(set_id=1,cost=150,chances=[10000,0,0,0,0])],gacha_type=0)

    def test_compiler_emits_one_three_section_rare_group_at_each_active_window(self):
        pack=self.pack()
        bindings={v['id']:dict(v['original'],kind='gacha') for v in pack['catalog']['gacha']}
        pack['catalog']={kind:values if kind=='gacha' else [] for kind,values in pack['catalog'].items()}
        pack['schedule']=[v for v in pack['schedule'] if v['kind']=='gacha']
        data,_=compile_calendar(pack,bindings,start_date='2026-10-15',days=1)
        rows=base64.b64decode(validate_bundle(data)['server_files']['gatya.tsv']).decode().splitlines()[1:-1]
        rare=[r.split('\t') for r in rows if r.split('\t')[8]=='1']
        normal=[r.split('\t') for r in rows if r.split('\t')[8]=='0']
        self.assertEqual(len(rare),8)
        self.assertTrue(all(row[9]=='3' for row in rare))
        self.assertEqual(len(normal),1)
        self.assertEqual(normal[0][:4],['20000101','0','20370101','0'])
        self.assertEqual(normal[0][9],'2')
        self.assertEqual([normal[0][10],normal[0][25]],['0','3'])
        self.assertEqual([normal[0][24],normal[0][39]],['',''])
        self.assertEqual([row[1] for row in rare],['0','300','600','900','1200','1500','1800','2100'])
        self.assertTrue(all(row[40]=='958' for row in rare))

    def test_normal_source_binding_uses_normal_table_and_standard_ticket(self):
        pack=self.pack();pack['catalog']['gacha']=[v for v in pack['catalog']['gacha']
            if v['original']['gacha_type']==0]
        for kind in ('stage','event','mission'):pack['catalog'][kind]=[]
        source=dict(source_export_sha256=EXACT_JP_15_7_1_EXPORT_SHA256,gacha={},
                    normal_gacha={0:dict(ticket=20,rarities=[0],source_group_sizes=[9,9,0]),
                                  3:dict(ticket=20,rarities=[],source_group_sizes=[0,0,24])})
        self.assertEqual(len(bind_catalogue(pack,source)),2)
        source['normal_gacha'][3]['ticket']=21
        with self.assertRaises(ProtocolError):bind_catalogue(pack,source)


if __name__=='__main__':unittest.main()
