"""A slow collector must not silently lose its start marker."""
from pathlib import Path
import tempfile
import unittest

from tools.pc_lab import confirm_log_barrier


class PcLogBarrierTests(unittest.TestCase):
    def test_initial_marker_lost_before_subscription_is_retransmitted(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'collector.log';path.write_text('',encoding='utf-8')
            emissions=[]
            def emit():
                emissions.append('run:START')
                if len(emissions)==2:path.write_text('run:START\n',encoding='utf-8')
            self.assertTrue(confirm_log_barrier(path,'run:START',emit,lambda:True,
                timeout=1,retry_interval=.02,poll_interval=.005))
            self.assertEqual(len(emissions),2)

    def test_dead_collector_and_missing_marker_remain_failures(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'collector.log';path.write_text('old-run:START',encoding='utf-8')
            self.assertFalse(confirm_log_barrier(path,'new-run:START',lambda:None,lambda:False))
            self.assertFalse(confirm_log_barrier(path,'new-run:START',lambda:None,lambda:True,
                timeout=.03,retry_interval=.01,poll_interval=.005))
