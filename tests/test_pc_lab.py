"""PC lab gates use synthetic inputs; never read owner data in CI."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
from unittest.mock import patch

from tools.base_mod.prepare_original_research_presign import (
    _source_receipt, UnsignedOriginalBuildBlocked,
)
from tools.pc_lab import (validate_identity, scope_research_log, capture_quality,
                          verify_installed_hashes, parse_installed_paths, has_log_loss,
                          summarize_java_crash, bound_to_barriers, Lab)


class FailedBuildEvidenceTests(unittest.TestCase):
    def test_stage_ownership_stops_before_root_on_wrong_avd_or_before_copy_on_bad_uid(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            lab = Lab(root / 'private/pc-lab', root / 'sdk', root / 'jdk')
            with patch.object(lab, 'identity', side_effect=ValueError('wrong avd')), \
                    patch.object(lab, 'adb') as adb:
                with self.assertRaisesRegex(ValueError, 'wrong avd'):
                    lab.stage_assets({})
                adb.assert_not_called()
            for uid in ('package:jp.co.ponos.battlecats uid:10209',
                        'package:jp.kn.local.battlecats uid:0',
                        'package:jp.kn.local.battlecats uid:10209\nextra',
                        'package:jp.kn.local.battlecats uid:10209;other'):
                def adb(*args, **kwargs):
                    return subprocess.CompletedProcess(args, 0,
                        '0\n' if args == ('shell', 'id', '-u') else uid, '')
                with self.subTest(uid=uid), patch.object(lab, 'identity'), \
                        patch.object(lab, 'adb', side_effect=adb) as calls:
                    with self.assertRaisesRegex(RuntimeError, 'UID_NOT_EXACT'):
                        lab.stage_assets({})
                    self.assertFalse(any(c.args[0] == 'push' for c in calls.call_args_list))

    def test_staged_assets_are_owned_by_target_app_in_dedicated_guest(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            lab = Lab(root / 'private/pc-lab', root / 'sdk', root / 'jdk')
            cache = lab.state.parent / 'original-jp1571-verified-server-cache'
            cache.mkdir()
            directory = root / 'build'; directory.mkdir()
            from zipfile import ZipFile
            with ZipFile(directory / 'split_InstallPack.apk', 'w'):
                pass
            digest = hashlib.md5(b'fixture').hexdigest()
            entries = [(f'asset_{i}.pack', 7, digest) for i in range(393)]
            for name, _, _ in entries:
                (cache / name).write_bytes(b'fixture')
            calls = []
            def adb(*args, **kwargs):
                calls.append(args)
                output = ''
                if args == ('shell', 'id', '-u'):
                    output = '0\n'
                elif args[:4] == ('shell', 'cmd', 'package', 'list'):
                    output = 'package:jp.kn.local.battlecats uid:10209\n'
                elif args[:2] == ('shell', 'md5sum'):
                    output = '\n'.join(f'{h}  /stage/{n}' for n, _, h in entries)
                elif args[:2] == ('shell', 'stat'):
                    output = '10209\n' * 393
                return subprocess.CompletedProcess(args, 0, output, '')
            with patch('tools.pc_lab.original_offline_asset_manifest', return_value=entries), \
                    patch.object(lab, 'identity'), patch.object(lab, 'adb', adb):
                lab.stage_assets({'directory': str(directory)})
            expected = ('shell', 'chown', '-R', '10209:1078',
                        '/data/media/0/Android/data/jp.kn.local.battlecats/files/'
                        'kneekura-original-jp1571-stage')
            self.assertIn(expected, calls)
            self.assertLess(next(i for i,c in enumerate(calls) if c[0]=='push'),
                            calls.index(expected))

    def test_failed_cmake_output_is_preserved_before_raising(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            lab = Lab(root / 'private/pc-lab', root / 'sdk', root / 'jdk')

            def failed_command(argv, **kwargs):
                if kwargs.get('check', True):
                    raise RuntimeError('synthetic configuration failure')
                return subprocess.CompletedProcess(argv, 1, 'synthetic compiler stdout',
                                                    'synthetic compiler stderr')

            with patch('tools.pc_lab.REPO', root), patch.object(lab, 'command', failed_command):
                with self.assertRaises(RuntimeError):
                    lab.build(root / 'not-owner.zip', root / 'not-official.aar')
            logs = list((root / 'private').glob('pc-native-*/compiler.log'))
            self.assertEqual(len(logs), 1)
            self.assertIn('synthetic compiler stderr', logs[0].read_text())


class CaptureGateTests(unittest.TestCase):
    def test_stale_buffer_entries_arriving_after_start_cannot_supply_evidence(self):
        source = ('10-11 17:00:10.000000 +0000 1 1 I KNEEKURA_PC_CAPTURE: run:START\n'
                  '10-11 16:59:59.000000 +0000 2 2 I KNEEKURA_STATIC_HTTP: stale\n'
                  '10-11 17:00:11.000000 +0000 2 2 I KNEEKURA_STATIC_HTTP: current\n'
                  '10-11 17:00:12.000000 +0000 1 1 I KNEEKURA_PC_CAPTURE: run:END\n')
        result = bound_to_barriers(source, 'run')
        self.assertIn('current', result)
        self.assertNotIn('stale', result)
        self.assertEqual(bound_to_barriers(source.replace('run:END', 'other:END'), 'run'), '')

    def test_java_crash_classes_are_reported_without_private_exception_message(self):
        source = ('10-11 17:10:52.000 123 123 E AndroidRuntime: FATAL EXCEPTION: main\n'
                  '10-11 17:10:52.000 123 123 E AndroidRuntime: '
                  'java.lang.RuntimeException: private-secret-owner-message\n'
                  '10-11 17:10:52.000 123 123 E AndroidRuntime: '
                  'Caused by: android.content.res.Resources$NotFoundException: String resource ID #0x0\n')
        report = summarize_java_crash(source)
        self.assertEqual(report['fatal_exception_events'], 1)
        self.assertIn('android.content.res.Resources$NotFoundException', report['exception_classes'])
        self.assertTrue(report['string_resource_id_zero_observed'])
        self.assertNotIn('private-secret', json.dumps(report))

    def test_utc_offset_is_normalized_only_for_existing_fixed_event_parsers(self):
        line = ('10-11 17:07:29.220995 +0000 4939 4939 I KNEEKURA_STATIC_HTTP: '
                'original-native-scene-hook-v1 hook-runtime-init-failed')
        scoped = scope_research_log(line, {4939})
        self.assertIn('hook-runtime-init-failed', scoped)
        self.assertNotIn('+0000', scoped)

    def test_binder_dropped_transaction_is_not_log_capture_loss(self):
        self.assertFalse(has_log_loss('I IPCThreadState: results will be dropped', ''))
        self.assertTrue(has_log_loss('I chatty: uid=1 identical 20 lines', ''))
        self.assertTrue(has_log_loss('', 'logcat: Unexpected EOF!'))

    def test_android_package_path_dots_are_valid_shell_metacharacters_are_not(self):
        path = '/data/app/~~nonce/jp.kn.local.battlecats-nonce==/base.apk'
        self.assertEqual(parse_installed_paths(['package:' + path]), [path])
        for bad in [path + ';other', '/sdcard/base.apk', path + '/extra']:
            with self.assertRaises(ValueError):
                parse_installed_paths(['package:' + bad])

    def test_device_payload_drift_or_missing_split_is_rejected(self):
        expected = {'base.apk': 'a' * 64, 'split_config.arm64_v8a.apk': 'b' * 64}
        actual = {'base.apk': 'a' * 64, 'split_config.arm64_v8a.apk': 'b' * 64}
        verify_installed_hashes(expected, actual)
        for bad in [dict(actual, **{'base.apk': 'c' * 64}), {'base.apk': 'a' * 64}]:
            with self.assertRaises(ValueError):
                verify_installed_hashes(expected, bad)

    def test_physical_wrong_and_unknown_emulators_cannot_be_operated(self):
        validate_identity('emulator-5580', 'kneekura-pc-api35\nOK\n')
        for serial, name in [('phone123', 'kneekura-pc-api35'),
                             ('emulator-5554', 'kneekura-pc-api35'),
                             ('emulator-5580', 'other-project\nOK')]:
            with self.assertRaises(ValueError):
                validate_identity(serial, name)

    def test_only_current_run_verified_package_pid_markers_are_summarized(self):
        lines = ('10-12 01:00:00.000 100 100 I ActivityManager: '
                 'Start proc 123:jp.kn.local.battlecats/u0a1 for activity\n'
                 '10-12 01:00:01.000 999 999 I KNEEKURA_STATIC_HTTP: '
                 'original-native-scene-v1 id=4\n'
                 '10-12 01:00:02.000 123 123 I KNEEKURA_STATIC_HTTP: '
                 'original-native-scene-v1 id=97\n')
        scoped = scope_research_log(lines, set())
        self.assertIn('id=97', scoped)
        self.assertNotIn('id=4', scoped)

    def test_capture_failure_and_missing_end_barrier_never_pass(self):
        good = dict(start_barrier=True, end_barrier=True, launch_ok=True,
                    collector_exit=0, screenshots=2, errors=[], log_loss=False)
        self.assertEqual(capture_quality(good), 'COMPLETE_BOUNDED_CAPTURE')
        for field, value in [('end_barrier', False), ('collector_exit', 1),
                             ('screenshots', 0), ('errors', ['denied']),
                             ('log_loss', True)]:
            with self.subTest(field=field):
                self.assertEqual(capture_quality(dict(good, **{field: value})),
                                 'INCOMPLETE_CAPTURE')


class LocalReceiptTests(unittest.TestCase):
    def test_local_receipt_requires_explicit_pc_opt_in_and_preserves_provenance(self):
        with tempfile.TemporaryDirectory() as folder:
            shim = Path(folder) / 'libkneekura.so'
            shim.write_bytes(b'passive-native-synthetic-' * 20)
            receipt = Path(folder) / 'receipt.json'
            proof = dict(schema='local-pc-research-passive-shim-v1',
                         elf_abi='arm64-v8a', original_save_writer_enabled=False,
                         fixed_error_markers_compiled=True, git_commit='a' * 40,
                         sha256=hashlib.sha256(shim.read_bytes()).hexdigest(),
                         source_tree_sha256='b' * 64, ndk_version='27.2.12479018')
            receipt.write_text(json.dumps(proof))
            with self.assertRaises(UnsignedOriginalBuildBlocked):
                _source_receipt(shim, receipt)
            self.assertEqual(_source_receipt(shim, receipt, allow_local_pc=True), proof)
            proof['original_save_writer_enabled'] = True
            receipt.write_text(json.dumps(proof))
            with self.assertRaises(UnsignedOriginalBuildBlocked):
                _source_receipt(shim, receipt, allow_local_pc=True)


if __name__ == '__main__':
    unittest.main()
