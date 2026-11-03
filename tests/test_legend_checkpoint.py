"""Legend policy tests need neither private save data nor the external parser."""
import copy
import csv
import io
from types import SimpleNamespace as N
import unittest

from tools.base_mod.legend_checkpoint import (
    apply_checkpoint, derive_stage_counts, verify_checkpoint,
)


def fixture():
    groups = [N(chapters=[N(selected_stage=2, clear_progress=0,
                           chapter_unlock_state=0,
                           stages=[N(clear_amount=0) for _ in range(12)])
                          for _ in range(4)], legend_restriction=7) for _ in range(35)]
    return N(event_stages=N(chapters=[N(chapters=groups)],
                            stages_reward_claimed=[123], chapter_completion_count={8: 2}),
             inquiry_code='private-test-identity', cats=[{'level': 17}],
             inventory={'item': 19}, story=[3, 4], unit_drops=[1, 0])


def semantic(save):
    result = copy.deepcopy(vars(save))
    result['event_stages'] = dict(
        stages_reward_claimed=save.event_stages.stages_reward_claimed.copy(),
        chapter_completion_count=save.event_stages.chapter_completion_count.copy(),
        chapters=[[dict(legend_restriction=group.legend_restriction,
                        chapters=[dict(selected_stage=c.selected_stage,
                                       clear_progress=c.clear_progress,
                                       chapter_unlock_state=c.chapter_unlock_state,
                                       stages=[s.clear_amount for s in c.stages])
                                  for c in group.chapters])
                   for group in save.event_stages.chapters[0].chapters]])
    return result


def payload(rows):
    out = io.StringIO()
    csv.writer(out).writerows(rows)
    return out.getvalue().encode('utf-8-sig')


def source_rows():
    names = [[str(i), '恐ろし連邦' if i == 32 else 'chapter'] for i in range(34)]
    stages = [['stage'] * (8 if i < 2 else 6) + ['＠', '\u3000', ''] for i in range(34)]
    return names, stages


class LegendCheckpointTests(unittest.TestCase):
    def test_stage_counts_come_from_sentinel_not_twelve_save_slots(self):
        names, stages = source_rows()
        counts = derive_stage_counts(payload(names), payload(stages))
        self.assertEqual(counts, (8, 8) + (6,) * 31)

    def test_missing_sentinel_nonempty_padding_and_empty_stage_are_rejected(self):
        for change in ('sentinel', 'padding', 'stage', 'too_many'):
            names, stages = source_rows()
            if change == 'sentinel': stages[4].remove('＠')
            elif change == 'padding': stages[4][-1] = 'unexpected'
            elif change == 'stage': stages[4][2] = ' '
            else: stages[4] = ['stage'] * 13 + ['＠']
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'SOURCE_LAYOUT'):
                derive_stage_counts(payload(names), payload(stages))

    def test_checkpoint_name_and_map_order_are_checked(self):
        for index in (3, 32):
            names, stages = source_rows()
            names[index] = ['wrong', 'wrong']
            with self.subTest(index=index), self.assertRaises(ValueError):
                derive_stage_counts(payload(names), payload(stages))

    def test_copy_completes_only_real_first_crown_stages_and_unlocks_successors(self):
        save = fixture()
        before = semantic(save)
        result = apply_checkpoint(save, (6,) * 33)
        self.assertEqual(semantic(save), before)
        maps = result.event_stages.chapters[0].chapters
        for group in maps[:33]:
            self.assertEqual(group.chapters[0].clear_progress, 6)
            self.assertEqual([s.clear_amount for s in group.chapters[0].stages], [1]*6+[0]*6)
            self.assertEqual([c.chapter_unlock_state for c in group.chapters], [3, 1, 0, 0])
            self.assertTrue(all(s.clear_amount == 0 for c in group.chapters[1:] for s in c.stages))
        self.assertEqual([c.chapter_unlock_state for c in maps[33].chapters], [1, 0, 0, 0])
        self.assertTrue(all(c.clear_progress == 0 for g in maps[33:] for c in g.chapters))
        verify_checkpoint(before, semantic(result), (6,) * 33)

    def test_existing_counts_padding_high_unlocks_and_future_clear_are_preserved(self):
        save = fixture()
        maps = save.event_stages.chapters[0].chapters
        maps[2].chapters[0].stages[0].clear_amount = 23
        maps[2].chapters[0].stages[10].clear_amount = 5
        maps[2].chapters[0].clear_progress = 10
        maps[2].chapters[0].chapter_unlock_state = 7
        maps[2].chapters[1].chapter_unlock_state = 3
        maps[2].chapters[1].stages[2].clear_amount = 4
        maps[33].chapters[0].chapter_unlock_state = 3
        maps[34].chapters[0].clear_progress = 3
        maps[34].chapters[0].stages[2].clear_amount = 8
        before = semantic(save)
        result = apply_checkpoint(save, (6,) * 33)
        after = semantic(result)
        verify_checkpoint(before, after, (6,) * 33)
        group = after['event_stages']['chapters'][0][2]['chapters']
        self.assertEqual((group[0]['stages'][0], group[0]['stages'][10],
                          group[0]['clear_progress'], group[0]['chapter_unlock_state']), (23, 5, 10, 7))
        self.assertEqual(group[1], before['event_stages']['chapters'][0][2]['chapters'][1])
        self.assertEqual(after['event_stages']['chapters'][0][33:],
                         before['event_stages']['chapters'][0][33:])

    def test_idempotent_without_incrementing_clear_counts(self):
        once = apply_checkpoint(fixture(), (6,) * 33)
        twice = apply_checkpoint(once, (6,) * 33)
        self.assertEqual(semantic(once), semantic(twice))

    def test_every_unrelated_semantic_category_is_rejected_by_diff_gate(self):
        before = semantic(fixture())
        expected = semantic(apply_checkpoint(fixture(), (6,) * 33))
        for category in ('identity', 'cats', 'inventory', 'story', 'unit_drops', 'claims',
                         'completion', 'selected', 'restriction', 'other_crown', 'future', 'padding'):
            after = copy.deepcopy(expected)
            maps = after['event_stages']['chapters'][0]
            if category == 'identity': after['inquiry_code'] = 'changed'
            elif category in ('cats', 'inventory', 'story', 'unit_drops'): after[category] = []
            elif category == 'claims': after['event_stages']['stages_reward_claimed'] = []
            elif category == 'completion': after['event_stages']['chapter_completion_count'] = {}
            elif category == 'selected': maps[0]['chapters'][0]['selected_stage'] = 0
            elif category == 'restriction': maps[0]['legend_restriction'] = 0
            elif category == 'other_crown': maps[0]['chapters'][1]['stages'][0] = 1
            elif category == 'future': maps[33]['chapters'][0]['stages'][0] = 1
            else: maps[0]['chapters'][0]['stages'][6] = 1
            with self.subTest(category=category), self.assertRaisesRegex(ValueError, 'UNAPPROVED'):
                verify_checkpoint(before, after, (6,) * 33)

    def test_diff_gate_rejects_omission_and_overclearing(self):
        before = semantic(fixture())
        for count in (0, 2):
            after = semantic(apply_checkpoint(fixture(), (6,) * 33))
            after['event_stages']['chapters'][0][32]['chapters'][0]['stages'][5] = count
            with self.subTest(count=count), self.assertRaisesRegex(ValueError, 'UNAPPROVED'):
                verify_checkpoint(before, after, (6,) * 33)

    def test_invalid_counts_and_save_layout_are_refused(self):
        for counts in ((6,) * 32, (0,) * 33, (13,) * 33, (True,) * 33):
            with self.subTest(counts=counts[:1]), self.assertRaisesRegex(ValueError, 'INVALID_COUNTS'):
                apply_checkpoint(fixture(), counts)
        for shape in ('maps', 'crowns', 'stages'):
            save = fixture()
            maps = save.event_stages.chapters[0].chapters
            if shape == 'maps': del maps[33:]
            elif shape == 'crowns': maps[4].chapters.pop()
            else: maps[4].chapters[2].stages.pop()
            with self.subTest(shape=shape), self.assertRaisesRegex(ValueError, 'SAVE_LAYOUT'):
                apply_checkpoint(save, (6,) * 33)


if __name__ == '__main__':
    unittest.main()
