import base64
from datetime import datetime
import io
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from tools.base_mod.extract_owned_splits import extract_owned_splits
from tools.base_mod.inject_java_http_bridge import render_ops_profile
from tools.base_mod.source_export_jp1574 import SPLITS, verify_legacy_asset_equivalence
from tools.liveops.original_ops_bundle import build_bundle, retarget_bundle, validate_bundle
from tools.liveops.original_schedule import EventWindow, gacha_row, stage_row, item_row, stream


class Jp1574BuildProfileTests(unittest.TestCase):
    def bundle(self):
        window = EventWindow(datetime.fromisoformat('2026-11-04T00:00:00+09:00'),
                             datetime.fromisoformat('2026-11-05T00:00:00+09:00'))
        return build_bundle(window, revision=15, files={
            'sale.tsv': stream([stage_row(window, (14005, 14011))]),
            'gatya.tsv': stream([gacha_row(window, 49, cost=150, chances=(0, 7000, 2500, 500, 0))]),
            'item.tsv': stream([item_row(window, 100001, 21, 1, title='特典', message='ログイン特典')]),
        })

    def test_retarget_preserves_calendar_and_rewards_except_version_filters(self):
        raw = self.bundle()
        old = validate_bundle(raw)
        changed = retarget_bundle(raw, source_profile='jp1574')
        new = validate_bundle(changed)
        self.assertEqual(new['game_version'], 150704)
        self.assertEqual(new['revision'], old['revision'])
        for name, encoded in old['server_files'].items():
            before = base64.b64decode(encoded).decode().splitlines()[1:-1]
            after = base64.b64decode(new['server_files'][name]).decode().splitlines()[1:-1]
            for left, right in zip(before, after):
                fields = left.split('\t')
                fields[4:6] = ['150704', '150704']
                self.assertEqual(right.split('\t'), fields)
            self.assertEqual(len(before), len(after))
        self.assertEqual(retarget_bundle(changed, source_profile='jp1571'), raw)
        self.assertEqual(retarget_bundle(changed, source_profile='jp1574'), changed)

    def test_profile_mismatch_and_unknown_version_are_rejected(self):
        new = json.loads(retarget_bundle(self.bundle(), source_profile='jp1574'))
        for key, value in [('source_native_sha256', '0' * 64),
                           ('owner_save', 'ORIGINAL_JP1571_SAVE_DATA'), ('game_version', 150705)]:
            candidate = dict(new, **{key: value})
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_bundle(json.dumps(candidate).encode())
        mixed = dict(new, server_files=json.loads(self.bundle())['server_files'])
        with self.assertRaises(ValueError):validate_bundle(json.dumps(mixed).encode())

    def test_java_source_contract_is_exact_and_legacy_stays_unchanged(self):
        source = (Path(__file__).resolve().parents[1] / 'bridge/java/KneekuraOriginalOps.java.in').read_text()
        self.assertEqual(render_ops_profile(source), source)
        new = render_ops_profile(source, source_profile='jp1574')
        self.assertIn('!= 150704', new)
        self.assertIn('ORIGINAL_JP1574_SAVE_DATA', new)
        self.assertNotIn('ORIGINAL_JP1571_SAVE_DATA', new)
        with self.assertRaises(ValueError):render_ops_profile(source.replace('150701', '150702'), source_profile='jp1574')

    def test_source_profile_must_be_explicit_and_pinned(self):
        self.assertEqual(set(SPLITS), {'base.apk', 'split_config.arm64_v8a.apk',
            'split_config.en.apk', 'split_config.ja.apk', 'split_config.xxhdpi.apk', 'split_InstallPack.apk'})
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'untrusted.zip'
            source.write_bytes(b'not the approved source')
            for profile in ('jp1571', 'jp1574', 'unknown'):
                with self.subTest(profile=profile), self.assertRaises(ValueError):
                    extract_owned_splits(source, Path(folder) / profile, source_profile=profile)
                self.assertFalse((Path(folder) / profile).exists())

    def test_legacy_asset_conversion_requires_every_installpack_asset_identical(self):
        def export(path, payload, manifest):
            pack = io.BytesIO()
            with ZipFile(pack, 'w') as inner:
                inner.writestr('AndroidManifest.xml', manifest)
                inner.writestr('assets/DataLocal.pack', payload)
            with ZipFile(path, 'w') as outer:
                outer.writestr('apk/split_InstallPack.apk', pack.getvalue())
        with tempfile.TemporaryDirectory() as folder:
            old, new, bad = (Path(folder) / name for name in ('old.zip', 'new.zip', 'bad.zip'))
            export(old, b'original', b'legacy-manifest')
            export(new, b'original', b'new-manifest')
            export(bad, b'changed', b'new-manifest')
            self.assertTrue(verify_legacy_asset_equivalence(new, old)['all_installpack_assets_identical'])
            with self.assertRaises(ValueError):verify_legacy_asset_equivalence(bad, old)


if __name__ == '__main__':unittest.main()
