"""PC-only opt-in and evidence attribution; no owner data in tests."""
from pathlib import Path
import hashlib
import json
import tempfile
import unittest

from tools.base_mod.inject_java_http_bridge import render_bridge_source

ROOT = Path(__file__).resolve().parents[1]


class PcSceneObserverTests(unittest.TestCase):
    def test_capture_verifier_recomputes_crashes_and_requires_actual_barriers_and_artifacts(self):
        from tools.pc_lab import (Lab, summarize_java_crash, summarize_crash,
                                  summarize_runtime_events, scope_research_log, bound_to_barriers)
        from tools.pc_lab_diagnostics import observer_summary
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'private/pc-lab'; folder = root / 'captures/run'; folder.mkdir(parents=True)
            source = ('10-11 18:00:00.000000 +0000 1 1 I KNEEKURA_PC_CAPTURE: run:START\n'
                      '10-11 18:00:01.000000 +0000 123 123 E AndroidRuntime: FATAL EXCEPTION: main\n'
                      '10-11 18:00:02.000000 +0000 1 1 I KNEEKURA_PC_CAPTURE: run:END\n')
            scoped = scope_research_log(bound_to_barriers(source, 'run'), {123})
            for name in ('source.diff', 'source-snapshot.zip', 'device-clock-before.txt',
                         'device-clock-after.txt', 'package.txt', 'properties.txt', 'buffers-before.txt',
                         'buffers-after.txt', 'exit-info.txt', 'logcat-stderr.log'):
                (folder / name).write_bytes(b'')
            (folder / 'logcat-threadtime.log').write_text(source)
            (folder / 'launch.txt').write_text('Status: ok\n')
            for name in ('launch.png', 'final.png'):
                (folder / name).write_bytes(b'\x89PNG\r\n\x1a\nsynthetic')
            proof = dict(schema='kneekura-pc-capture-v1', run_id='run', package='jp.kn.local.battlecats',
                         avd='kneekura-pc-api35', serial='emulator-5580',
                         pid_observations=[dict(pids=[123])], runtime_summary=summarize_runtime_events(scoped),
                         observer_summary=observer_summary(scoped), java_crash_summary=summarize_java_crash(scoped),
                         crash_summary=summarize_crash(scoped), status='COMPLETE_BOUNDED_CAPTURE',
                         start_barrier=True, end_barrier=True, launch_ok=True, collector_exit=0,
                         screenshots=2, screenshot_times=[{'file':n} for n in ('launch.png','final.png')],
                         errors=[], log_loss=False)
            def save(value):
                value['artifacts_sha256'] = {p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                            for p in folder.iterdir() if p.name != 'CAPTURE.json'}
                (folder / 'CAPTURE.json').write_text(json.dumps(value))
            lab = Lab(root, root/'sdk', root/'jdk'); save(proof)
            self.assertEqual(lab.verify_capture(folder)['capture_status'], 'COMPLETE_BOUNDED_CAPTURE')
            bad = dict(proof, java_crash_summary={'fatal_exception_events':0}); save(bad)
            with self.assertRaises(ValueError):
                lab.verify_capture(folder)
            save(proof)
            (folder / 'logcat-threadtime.log').write_text('')
            bad = dict(proof, runtime_summary=summarize_runtime_events(''),
                       observer_summary=observer_summary(''), java_crash_summary=summarize_java_crash(''),
                       crash_summary=summarize_crash('')); save(bad)
            with self.assertRaises(ValueError):
                lab.verify_capture(folder)
            (folder / 'logcat-threadtime.log').write_text(source); save(proof)
            bad = dict(proof, artifacts_sha256={'source.diff':hashlib.sha256(b'').hexdigest()})
            (folder / 'CAPTURE.json').write_text(json.dumps(bad))
            with self.assertRaises(ValueError):
                lab.verify_capture(folder)

    def test_anr_trace_selection_is_current_pid_and_fixed_private_path_only(self):
        from tools.pc_lab_diagnostics import anr_trace_paths
        def entry(pid=123, stamp='2026-10-11 18:00:01.123', path='/data/system/procexitstore/anr_2026-10-11-18-00-01-123.gz'):
            return (f'ApplicationExitInfo #0:\n timestamp={stamp} pid={pid} realUid=10209\n'
                    f' process=jp.kn.local.battlecats reason=6 (ANR) trace={path}\n')
        start, end = '2026-10-11T18:00:00+00:00', '2026-10-11T18:00:30+00:00'
        self.assertEqual(len(anr_trace_paths(entry(), {123}, start, end)), 1)
        for bad in (entry(pid=999), entry(stamp='2026-10-11 17:59:59.999'),
                    entry(path='/data/system/procexitstore/../other.gz'),
                    entry().replace('jp.kn.local.battlecats', 'jp.co.ponos.battlecats')):
            self.assertEqual(anr_trace_paths(bad, {123}, start, end), [])

    def test_saved_artifact_integrity_rejects_mutation_missing_and_path_escape(self):
        from tools.pc_lab_diagnostics import verify_artifacts
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'capture.log').write_bytes(b'synthetic log')
            manifest = {'capture.log': hashlib.sha256(b'synthetic log').hexdigest()}
            self.assertEqual(verify_artifacts(root, manifest), 1)
            (root / 'capture.log').write_bytes(b'changed')
            with self.assertRaises(ValueError):
                verify_artifacts(root, manifest)
            for bad in ({'missing': 'a'*64}, {'../escape': 'a'*64}, {'CAPTURE.json': 'a'*64}, {}):
                with self.assertRaises(ValueError):
                    verify_artifacts(root, bad)

    def test_pc_observer_is_explicit_and_rejects_shipping_or_save_trial(self):
        template = (ROOT / 'bridge/java/MyActivity.java.in').read_text(encoding='utf-8')
        default = render_bridge_source(template, flavor='local-research', enabled=False)
        self.assertIn('PC_JNI_SCENE_OBSERVER = false;', default)
        selected = render_bridge_source(template, flavor='local-research', enabled=False,
                                        pc_jni_scene_observer=True)
        self.assertIn('PC_JNI_SCENE_OBSERVER = true;', selected)
        for flavor in ('personal', 'practice', 'research'):
            with self.subTest(flavor=flavor), self.assertRaises(ValueError):
                render_bridge_source(template, flavor=flavor, enabled=False,
                                     pc_jni_scene_observer=True)
        with self.assertRaises(ValueError):
            render_bridge_source(template, flavor='local-research', enabled=False,
                                 pc_jni_scene_observer=True, virgin_save_trial=True)

    def test_jni_scene_attachment_does_not_claim_level_save_hooks(self):
        from tools.pc_lab_diagnostics import observer_summary
        def log(pid, tid, msg):
            return f'10-11 18:00:00.000 {pid} {tid} I KNEEKURA_STATIC_HTTP: {msg}\n'
        attachment = 'original-native-pc-jni-scene-v1 attached'
        forwarded = 'original-native-pc-jni-scene-v1 original-returned-same-gl-thread'
        result = observer_summary(log(123, 124, attachment) + log(123, 124, forwarded))
        self.assertEqual(result['backend'], 'pc-jni-scene-only')
        self.assertTrue(result['original_draw_returned_on_install_gl_thread'])
        self.assertFalse(result['level_save_hooks_installed'])
        for source in (log(123, 124, attachment),
                       log(123, 124, attachment) + log(123, 125, forwarded),
                       log(123, 124, attachment) + log(456, 124, forwarded),
                       log(123, 124, forwarded) + log(123, 124, attachment)):
            self.assertFalse(observer_summary(source)['original_draw_returned_on_install_gl_thread'])
        self.assertEqual(observer_summary(log(123, 124, attachment + ' private-secret'))['backend'],
                         'unavailable')


if __name__ == '__main__':
    unittest.main()
