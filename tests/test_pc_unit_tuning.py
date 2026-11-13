"""Synthetic tests for the 2026-11-14 owner unit tuning (no original data needed)."""
import hashlib
import unittest
from unittest import mock

from tools.base_mod import pc_unit_tuning as T


def row(columns=117, **values):
    fields = [b'0'] * columns
    for column, value in values.items():
        fields[int(column[1:])] = str(value).encode()
    return fields


def csv(rows, ending=b'\n'):
    return b''.join(b','.join(r) + ending for r in rows)


def patched(name, original):
    return mock.patch.dict(T.ORIGINAL_SHA256, {name: hashlib.sha256(original).hexdigest()})


class UnitTuningTests(unittest.TestCase):
    def test_spec_never_targets_zombie_and_covers_every_other_trait(self):
        self.assertNotIn(T.ZOMBIE_COLUMN, T.NON_ZOMBIE_TARGET_COLUMNS)
        self.assertEqual(set(T.NON_ZOMBIE_TARGET_COLUMNS),
                         {10, 16, 17, 18, 19, 20, 21, 54, 76, 78, 96})
        for name in ('unit178.csv', 'unit135.csv'):
            edits = next(iter(T.EDITS[name].values()))
            self.assertEqual(edits[T.INSANE_TOUGH_COLUMN], 1)
            self.assertNotIn(T.ZOMBIE_COLUMN, edits)

    def test_diolamus_changes_only_form4(self):
        rows = [row(c0=5500 + i, c6=4400, c7=2480, c24=100, c27=100, c20=1, columns=110) for i in range(4)]
        rows[3][21] = b'1'
        original = csv(rows)
        with patched('unit178.csv', original):
            out = T.build_candidate('unit178.csv', original)
        before, after = original.splitlines(), out.splitlines()
        self.assertEqual(before[:3], after[:3])
        fields = after[3].split(b',')
        self.assertEqual(fields[6], b'5067')
        self.assertEqual(fields[7], b'4960')  # cooldown doubled
        self.assertEqual((fields[24], fields[27]), (b'100', b'100'))  # disruption unchanged
        self.assertEqual(fields[80], b'1')
        self.assertEqual(fields[22], b'0')
        for column in T.NON_ZOMBIE_TARGET_COLUMNS:
            self.assertEqual(fields[column], b'1')

    def test_gamereon_pads_old_70_column_rows_and_keeps_crlf_and_comment(self):
        rows = [row(columns=70, c0=770), row(columns=70, c0=11600), row(columns=70, c0=14500, c6=3250, c7=2600, c29=1)]
        rows[0][-1] = b'0 // legacy comment'
        original = csv(rows, b'\r\n')
        with patched('unit135.csv', original):
            out = T.build_candidate('unit135.csv', original)
        before, after = original.splitlines(keepends=True), out.splitlines(keepends=True)
        self.assertEqual(before[:2], after[:2])
        self.assertTrue(after[2].endswith(b'\r\n'))
        fields = after[2].rstrip(b'\r\n').split(b',')
        self.assertEqual(len(fields), 97)
        self.assertEqual((fields[80], fields[96], fields[22], fields[29]), (b'1', b'1', b'0', b'1'))
        self.assertEqual((fields[6], fields[7]), (b'3917', b'5200'))

    def test_madoka_layers_on_legacy_row_and_copies_without_animation_columns(self):
        rows = [row(c0=2550, c4=100, c13=44, c67=0, c23=1) for _ in range(2)]
        rows.append(row(c0=3250, c3=1850, c4=100, c13=72, c22=1, c30=1, c52=1, c67=19, c78=1, c79=1))
        original = csv(rows)
        legacy_rows = [list(r) for r in rows]
        legacy_rows[2][3] = b'1647'
        legacy = csv(legacy_rows)
        with patched('unit289.csv', original):
            out = T.build_candidate('unit289.csv', original, legacy_candidate=legacy)
        lines = [l.split(b',') for l in out.splitlines()]
        final = lines[2]
        self.assertEqual((final[35], final[36], final[94]), (b'100', b'3', b'1'))
        self.assertEqual(final[3], b'1647')
        for early in lines[:2]:
            for column in (0, 3, 22, 30, 35, 36, 52, 78, 79, 94):
                self.assertEqual(early[column], final[column], column)
            self.assertEqual((early[13], early[67]), (b'44', b'0'))  # animation-bound kept

    def test_homura_dead_zone_freeze_and_copy(self):
        rows = [row(c0=2830, c3=2030, c4=85, c13=30, c25=50, c26=120) for _ in range(2)]
        rows.append(row(c0=2830, c3=2470, c13=103, c25=50, c26=120, c44=205, c45=450, c10=1, c96=1))
        original = csv(rows)
        with patched('unit290.csv', original):
            out = T.build_candidate('unit290.csv', original)
        lines = [l.split(b',') for l in out.splitlines()]
        for index, line in enumerate(lines):
            self.assertEqual((line[25], line[44], line[45]), (b'100', b'100', b'555'))
            self.assertEqual(int(line[44]) + int(line[45]), 655)  # far end of the original reach
        self.assertEqual(lines[0][3], b'2470')
        self.assertEqual(lines[0][4], b'85')  # own attack cycle kept

    def test_crazed_form2_takes_form3_performance_with_requested_changes(self):
        legacy = [row(columns=53, c0=3600, c2=11, c3=1184, c13=47, c35=10, c36=10) for _ in range(2)]
        legacy.append(row(columns=53, c0=4400, c2=11, c3=1184, c13=47, c35=15, c36=10))
        for r in legacy:
            r[52] = b''  # legacy rows end in an empty field
        original = csv(legacy, b'\r\n')
        with patched('unit100.csv', original):
            out = T.build_candidate('unit100.csv', original)
        before, after = original.splitlines(keepends=True), out.splitlines(keepends=True)
        self.assertEqual((before[0], before[2]), (after[0], after[2]))
        fields = after[1].rstrip(b'\r\n').split(b',')
        self.assertEqual(len(fields), 116)
        self.assertNotIn(b'', fields)
        self.assertEqual((fields[0], fields[2], fields[3]), (b'17600', b'9', b'1776'))
        self.assertEqual((fields[35], fields[36]), (b'20', b'10'))
        self.assertEqual((fields[113], fields[114], fields[115]), (b'50', b'1800', b'0'))
        self.assertEqual(fields[13], b'47')
        # Widened columns keep modern-row defaults: no summon, unlimited attacks, normal spawn.
        for column in (55, 57, 66, 110):
            self.assertEqual(fields[column], b'-1', column)
        for column in (53, 54, 56, 58, 67, 109):
            self.assertEqual(fields[column], b'0', column)

    def test_fail_closed_on_changed_source_or_value(self):
        original = csv([row(columns=110, c6=4400, c7=2480, c24=100, c27=100)] * 4)
        with self.assertRaises(ValueError):
            T.build_candidate('unit178.csv', original)  # SHA not the pinned original
        bad = csv([row(columns=110, c6=4400, c7=2480, c24=50, c27=100)] * 4)
        with patched('unit178.csv', bad):
            with self.assertRaisesRegex(ValueError, 'UNEXPECTED_SOURCE_VALUE'):
                T.build_candidate('unit178.csv', bad)


if __name__ == '__main__':
    unittest.main()
