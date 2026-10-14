"""Task evidence must distinguish masked slots from actual download state."""
import unittest

from tools.pc_lab_diagnostics import scene97_task_summary


class Scene97TaskStateTests(unittest.TestCase):
    def test_zero_slots_do_not_establish_active_sources_or_completion(self):
        line = ('10-12 01:00:00.000000 123 456 I KNEEKURA_STATIC_HTTP: '
                'original-native-scene97-task-v1 active=0 disabled=35 '
                'present=1 failed=0 needed=0 pending=0 completed=0')
        result = scene97_task_summary(line)
        self.assertEqual(result['observations'][0]['disabled'], 35)
        self.assertFalse(result['observations'][0]['completed'])
        self.assertFalse(result['resource_acceptance_proven'])

    def test_inconsistent_or_out_of_range_observation_is_rejected(self):
        prefix = 'I KNEEKURA_STATIC_HTTP: original-native-scene97-task-v1 '
        for fields in ('active=35 disabled=35 present=1 failed=0 needed=0 pending=0 completed=0',
                       'active=35 disabled=0 present=1 failed=2 needed=0 pending=0 completed=0',
                       'active=35 disabled=0 present=1 failed=0 needed=1 pending=36 completed=0'):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                scene97_task_summary(prefix + fields)

    def test_absent_event_is_unavailable_and_duplicates_are_bounded(self):
        self.assertEqual(scene97_task_summary('')['observations'], [])
        line = ('I KNEEKURA_STATIC_HTTP: original-native-scene97-task-v1 '
                'active=35 disabled=0 present=1 failed=0 needed=0 pending=0 completed=1')
        self.assertEqual(len(scene97_task_summary('\n'.join([line] * 9))['observations']), 1)

    def test_account_wait_is_distinct_from_download_completion(self):
        lines = '\n'.join([
            'I KNEEKURA_STATIC_HTTP: original-native-scene97-queue-v1 head=1 completed=0 phase=65 waiting=0',
            'I KNEEKURA_STATIC_HTTP: original-native-scene97-queue-v1 head=2 completed=0 phase=65 waiting=0',
        ])
        result = scene97_task_summary(lines)
        self.assertEqual(result['queue_observations'][-1]['head'], 'create-account')
        self.assertFalse(result['queue_observations'][-1]['completed'])
        self.assertIsNone(result['queue_observations'][0]['completed'])
        self.assertIsNone(result['queue_observations'][-1]['phase'])

    def test_unavailable_kernel_copy_is_reported_without_game_data(self):
        result = scene97_task_summary('I KNEEKURA_STATIC_HTTP: '
            'original-native-scene97-task-unavailable-v1 context-read')
        self.assertEqual(result['unavailable_categories'], ['task:context-read'])

    def test_revisited_states_keep_the_actual_last_observation(self):
        prefix = 'I KNEEKURA_STATIC_HTTP: original-native-scene97-'
        queue = [prefix + 'queue-v1 head=%s completed=0 phase=65 waiting=0' % head
                 for head in (1, 2, 1)]
        task = [prefix + 'task-v1 active=35 disabled=0 present=1 failed=0 '
                'needed=0 pending=0 completed=%s' % done for done in (0, 1, 0)]
        result = scene97_task_summary('\n'.join(queue + task))
        self.assertEqual([i['head'] for i in result['queue_observations']],
                         ['download', 'create-account', 'download'])
        self.assertEqual([i['completed'] for i in result['observations']], [False, True, False])
        old = scene97_task_summary('\n'.join(task), version=1)
        self.assertEqual([i['completed'] for i in old['observations']], [False, True])


if __name__ == '__main__':
    unittest.main()
