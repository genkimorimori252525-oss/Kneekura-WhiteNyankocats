"""Shared calendar priorities/boundaries must survive original TSV projection."""
from copy import deepcopy
import base64
import unittest

from tests.test_offline_ops_calendar import sample_pack
from tools.liveops.original_calendar import compile_calendar
from tools.liveops.original_ops_bundle import validate_bundle, build_login_rotation
from tools.liveops.original_schedule import ORIGINAL_OWNER_SAVE, ProtocolError


class OriginalOpsCalendarTests(unittest.TestCase):
    def pack(self):
        pack=sample_pack();pack['status']='published';pack['policy']['owner_save']=ORIGINAL_OWNER_SAVE
        pack['catalog']={kind:[] for kind in pack['catalog']}
        pack['catalog']['stage']=[dict(id='kneekura:stage:base',title='にーくら開催',
            source='kneekura-local',ready=True),dict(id='kneekura:stage:special',
            title='にーくら期間イベント',source='kneekura-local',ready=True)]
        pack['schedule']=[dict(id='kneekura:schedule:base',kind='stage',slot='event-1',priority=1,
            content_id='kneekura:stage:base',rule=dict(mode='once',start='2026-10-13T00:00:00+09:00',
            end='2026-10-16T00:00:00+09:00')),
            dict(id='kneekura:schedule:special',kind='stage',slot='event-1',priority=2,
            content_id='kneekura:stage:special',rule=dict(mode='once',start='2026-10-14T00:00:00+09:00',
            end='2026-10-15T00:00:00+09:00'))]
        return pack

    def bindings(self):
        return {'kneekura:stage:base':dict(kind='stage',native_ids=[1006]),
                'kneekura:stage:special':dict(kind='stage',native_ids=[2002])}

    def test_priority_winner_splits_and_resumes_original_windows(self):
        data,report=compile_calendar(self.pack(),self.bindings(),start_date='2026-10-13',days=3)
        bundle=validate_bundle(data)
        rows=base64.b64decode(bundle['server_files']['sale.tsv']).decode().splitlines()[1:-1]
        parsed=[(r.split('\t')[0],r.split('\t')[2],r.split('\t')[-1]) for r in rows]
        self.assertEqual(parsed,[('20261013','20261014','1006'),('20261015','20261016','1006'),
                                 ('20261014','20261015','2002')])
        self.assertFalse(report['original_save_mutated'])
        self.assertFalse(report['original_ui_accepted'])

    def test_draft_unready_bindings_and_additional_dynamic_gates_fail_closed(self):
        pack=self.pack();pack['status']='draft'
        with self.assertRaises(ProtocolError):compile_calendar(pack,self.bindings(),start_date='2026-10-13',days=3)
        pack=self.pack();pack['schedule'][0]['requires']={'cleared_stages':['kneekura:stage:clear']}
        with self.assertRaises(ProtocolError):compile_calendar(pack,self.bindings(),start_date='2026-10-13',days=3)
        with self.assertRaises(ProtocolError):compile_calendar(self.pack(),{},start_date='2026-10-13',days=3)
        pack=self.pack()
        for row in pack['catalog']['stage']:row['ready']=False
        with self.assertRaises(ProtocolError):compile_calendar(pack,self.bindings(),start_date='2026-10-13',days=3)

    def test_compiled_login_bags_cover_source_pool_without_duplicate_ids(self):
        pool=[dict(template_id=id,days=7) for id in range(949,957)]
        configuration=build_login_rotation(pool,seed='kneekura-autumn',cycles=4)
        self.assertEqual(configuration,build_login_rotation(deepcopy(pool),seed='kneekura-autumn',cycles=4))
        for bag in configuration['shuffle_bags']:
            self.assertEqual(set(bag),set(range(949,957)))
            self.assertEqual(len(bag),8)
        bad=deepcopy(configuration);bad['pool'][0]['days']=True
        from tools.liveops.original_ops_bundle import validate_login_rotation
        with self.assertRaises(ProtocolError):validate_login_rotation(bad)

    def test_mission_periods_remain_separate_and_stable_on_mid_period_rebuild(self):
        pack=self.pack()
        pack['catalog']['mission']=[dict(id='kneekura:mission:weekly',title='週間',
            source='kneekura-local',ready=True)]
        pack['schedule']=[dict(id='kneekura:schedule:week-'+str(i),kind='mission',
            slot='weekly',priority=1,content_id='kneekura:mission:weekly',
            rule=dict(mode='once',start='2026-10-%02dT00:00:00+09:00'%day,
                      end='2026-10-%02dT00:00:00+09:00'%(day+1)))
            for i,day in enumerate([13,14])]
        bindings={'kneekura:mission:weekly':dict(kind='mission',native_ids=[8005])}
        full,_=compile_calendar(pack,bindings,start_date='2026-10-13',days=2)
        rows=base64.b64decode(validate_bundle(full)['server_files']['sale.tsv']).decode().splitlines()[1:-1]
        self.assertEqual(len(rows),2)
        partial,_=compile_calendar(pack,bindings,start_date='2026-10-14',days=1)
        again=base64.b64decode(validate_bundle(partial)['server_files']['sale.tsv']).decode().splitlines()[1:-1]
        self.assertEqual(again,[rows[1]])
        # A rolling bundle beginning inside a longer original period keeps its start/end.
        pack['schedule']=pack['schedule'][:1]
        pack['schedule'][0]['rule']['end']='2026-10-16T00:00:00+09:00'
        full,_=compile_calendar(pack,bindings,start_date='2026-10-13',days=3)
        partial,_=compile_calendar(pack,bindings,start_date='2026-10-14',days=1)
        self.assertEqual(validate_bundle(full)['server_files']['sale.tsv'],
                         validate_bundle(partial)['server_files']['sale.tsv'])

    def test_notices_share_publication_pinning_priority_and_deduplication(self):
        pack=self.pack()
        for suffix,pinned in [('pinned',True),('regular',False)]:
            identifier='kneekura:notice:'+suffix
            pack['catalog']['notice'].append(dict(id=identifier,title=suffix,body='local news',
                category='運営情報',source='kneekura-local',ready=True,pinned=pinned,
                published_at='2026-10-14T12:00:00+09:00'))
            pack['schedule'].append(dict(id='kneekura:schedule:notice-'+suffix,kind='notice',
                slot='notice-'+suffix,priority=1 if pinned else 99,content_id=identifier,
                rule=dict(mode='once',start='2026-10-13T00:00:00+09:00',
                          end='2026-10-16T00:00:00+09:00')))
        duplicate=deepcopy(pack['schedule'][-1]);duplicate['id']='kneekura:schedule:duplicate'
        duplicate['slot']='notice-duplicate';duplicate['priority']=2;pack['schedule'].append(duplicate)
        data,_=compile_calendar(pack,self.bindings(),start_date='2026-10-13',days=3)
        notices=validate_bundle(data)['notices']
        self.assertEqual([item['title'] for item in notices],['pinned','regular'])
        self.assertEqual([item['priority'] for item in notices],[1,99])
        self.assertEqual(notices[0]['start_epoch_ms'],notices[0]['published_epoch_ms'])
        self.assertEqual(notices[0]['start_epoch_ms'],notices[1]['start_epoch_ms'])


if __name__=='__main__':unittest.main()
