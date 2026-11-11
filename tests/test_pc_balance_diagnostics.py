import unittest
from tools.pc_lab_diagnostics import pc_balance_summary


class BalanceDiagnosticsTests(unittest.TestCase):
    def test_absent_evidence_is_unknown_not_zero(self):
        self.assertIsNone(pc_balance_summary('')['adapter_calls'])

    def test_counts_reset_and_out_of_range_are_explicit(self):
        def event(count):
            return ('KNEEKURA_STATIC_HTTP: pc-native-balance-v1 calls='+','.join([str(count)]*8)
                    +' castle_credit=1 castle_zero=2 delayed_rejected=0 query_capacity=0')
        result=pc_balance_summary(event(10)+'\n'+event(1))
        self.assertEqual(result['observations'],2)
        self.assertEqual(result['counter_resets_observed'],1)
        self.assertEqual(result['castle_credited_hits'],1)
        with self.assertRaisesRegex(ValueError,'COUNTER_OUT_OF_RANGE'):
            pc_balance_summary(event(1<<64))
        self.assertEqual(pc_balance_summary(event(10).replace('KNEEKURA_STATIC_HTTP','untrusted_tag'))['observations'],0)
