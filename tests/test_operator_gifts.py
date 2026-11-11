"""A content rebuild must not turn a once-only gift into another reward."""
from copy import deepcopy
import unittest

from tools.liveops.operator_gifts import gift_rows
from tools.liveops.original_schedule import ProtocolError


class OperatorGiftTests(unittest.TestCase):
    def setUp(self):
        self.gift=dict(event_id=20261023,item_id=200,amount=4000,
            start='2026-10-23T00:00:00+09:00',end='2026-12-02T00:00:00+09:00',
            title='開催不具合のお詫び',message='ネコカン4000個をお受け取りください。',everyday=False)

    def test_original_item_namespace_and_once_flag(self):
        row=gift_rows([self.gift])[0].split('\t')
        self.assertEqual(row[8:11],['20261023','200','4000'])
        self.assertEqual(row[-3:],['0','0','0'])

    def test_rebuild_keeps_original_claim_identity_and_full_window(self):
        self.assertEqual(gift_rows([self.gift]),gift_rows(deepcopy([self.gift])))
        self.assertEqual(gift_rows([self.gift])[0].split('\t')[:4],['20261023','0','20261202','0'])

    def test_reject_duplicate_daily_or_other_reward(self):
        for patch in [dict(everyday=True),dict(item_id=21),dict(item_id=22),dict(amount=0),dict(event_id=True)]:
            with self.subTest(patch=patch),self.assertRaises(ProtocolError):
                gift_rows([dict(self.gift,**patch)])
        with self.assertRaises(ProtocolError):gift_rows([self.gift,self.gift])

    def test_real_calendar_compilation_keeps_once_claim_across_rebuild_dates(self):
        import base64,json
        from pathlib import Path
        from tools.liveops.original_calendar import compile_calendar
        p=json.loads((Path(__file__).resolve().parents[1]/'ops/seasons/2026-autumn-liveops.json').read_text(encoding='utf-8'))
        p['operator_gifts']=[self.gift]
        bindings={r['id']:dict(r['original'],kind=k) for k in ('gacha','stage','event','mission') for r in p['catalog'][k]}
        rows=[]
        for start in ['2026-10-23','2026-11-02']:
            bundle,_=compile_calendar(p,bindings,start_date=start,days=1)
            rows.append(base64.b64decode(json.loads(bundle)['server_files']['item.tsv']))
        self.assertEqual(rows[0],rows[1])
        self.assertEqual(rows[0].count(b'\t20261023\t200\t4000\t'),1)


if __name__=='__main__':unittest.main()
