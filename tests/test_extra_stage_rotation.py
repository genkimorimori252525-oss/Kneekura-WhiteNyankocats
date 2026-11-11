import unittest
from datetime import date, timedelta
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from tools.liveops.extra_stage_rotation import POOLS, choose_extra, choose_weekly


class ExtraStageRotationTests(unittest.TestCase):
    def test_actual_java_cache_period_changes_at_every_hour(self):
        javac = shutil.which('javac')
        if javac is None and os.name == 'nt':
            candidate = Path(r'C:\Program Files\Java\jdk-17\bin\javac.exe')
            if candidate.exists():
                javac = str(candidate)
        if javac is None:
            self.skipTest('Java compiler unavailable')
        java = str(Path(javac).with_name('java.exe' if os.name == 'nt' else 'java'))
        source = (Path(__file__).resolve().parents[1] / 'bridge/java/KneekuraOriginalOps.java.in').read_text(encoding='utf-8')
        start = source.index('    static long hourlyCachePeriod(')
        end = source.index('\n    }', start) + len('\n    }')
        method = source[start:end]
        harness = '''public class CacheBoundary {
%s
  public static void main(String[] args) {
    long base = hourlyCachePeriod(0L);
    if (hourlyCachePeriod(3599999L) != base || hourlyCachePeriod(3600000L) != base + 1
        || hourlyCachePeriod(-1L) != base - 1) throw new AssertionError();
  }
}''' % method
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'CacheBoundary.java'
            path.write_text(harness, encoding='utf-8')
            subprocess.run([javac, str(path)], check=True, capture_output=True)
            subprocess.run([java, '-cp', folder, 'CacheBoundary'], check=True, capture_output=True)

    def test_limits_deduplication_and_reproducibility(self):
        day = date(2026, 11, 11)
        existing = {POOLS['experience'][1][0], POOLS['event'][1][0]}
        first = choose_extra(day, 0, existing)
        self.assertLessEqual(len(first), 10)
        self.assertEqual(len(first), len(set(first)))
        self.assertFalse(set(first) & existing)
        self.assertEqual(first, choose_extra(day, 0, existing))
        self.assertNotEqual(first, choose_extra(day, 1, existing))

    def test_fully_scheduled_pools_never_overflow(self):
        existing = {identifier for _, pool in POOLS.values() for identifier in pool}
        self.assertEqual([], choose_extra(date(2026, 11, 11), 0, existing))
        with self.assertRaises(ValueError):
            choose_extra(date(2026, 11, 11), 24, set())

    def test_each_hour_offers_two_per_category_and_all_nine_cycle(self):
        day = date(2026, 11, 11)
        seen = set()
        for hour in range(9):
            chosen = choose_extra(day, hour, set())
            self.assertEqual(10, len(chosen))
            for name, (count, pool) in POOLS.items():
                self.assertEqual(count, len(set(chosen) & set(pool)))
            seen.update(chosen)
        self.assertTrue(set(POOLS['manic'][1]).issubset(seen))
        self.assertTrue(set(POOLS['little'][1]).issubset(seen))

    def test_collaboration_is_fixed_for_the_week(self):
        monday = date(2026, 11, 9)
        weekly = choose_weekly(monday)
        for day in range(7):
            self.assertEqual(weekly, choose_weekly(monday + timedelta(days=day)))
        self.assertNotEqual(weekly, choose_weekly(monday + timedelta(days=7)))
