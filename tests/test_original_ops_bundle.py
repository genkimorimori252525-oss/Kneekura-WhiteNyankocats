"""Owned original-runtime bundles: bounded bytes, archive parity and fail closed."""
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from tools.liveops.original_ops_bundle import (
    ASSET_ENTRY, build_bundle, validate_bundle, add_bundle_asset,
)
from tools.liveops.original_schedule import EventWindow, stream, stage_row


class OriginalOpsBundleTests(unittest.TestCase):
    def bundle(self):
        window = EventWindow(datetime(2026, 10, 13, tzinfo=timezone.utc),
                             datetime(2026, 10, 20, tzinfo=timezone.utc))
        return build_bundle(window, revision=1, files={
            'sale.tsv': stream([stage_row(window, [1006])]),
            'gatya.tsv': stream([]), 'item.tsv': stream([]),
        })

    def test_deterministic_original_contract_and_digest(self):
        data = self.bundle()
        self.assertEqual(data, self.bundle())
        metadata = validate_bundle(data)
        self.assertEqual(metadata['owner_save'], 'ORIGINAL_JP1571_SAVE_DATA')
        self.assertEqual(metadata['game_version'], 150701)
        self.assertEqual(set(metadata['server_files']), {'sale.tsv','gatya.tsv','item.tsv'})

    def test_rejects_untrusted_metadata_and_injected_streams(self):
        for key, value in [('schema_version', True), ('revision', 0),
                           ('game_version', 1), ('owner_save', 'KNEEKURA_SAVE_V1'),
                           ('source_native_sha256', '0'*64), ('end_epoch_ms', 0)]:
            candidate = json.loads(self.bundle()); candidate[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_bundle(json.dumps(candidate).encode())
        for data in [b'[start]\n[end]\nattack', b'[start]\n[end]\n[end]\n',
                     b'[start]\nnot-a-date\n[end]\n', b'[start]\n\xff\n[end]\n']:
            candidate=json.loads(self.bundle())
            candidate['server_files']['sale.tsv']=base64.b64encode(data).decode()
            with self.subTest(data=data), self.assertRaises(ValueError):
                validate_bundle(json.dumps(candidate).encode())

    def test_asset_addition_is_exact_and_original_entries_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'base.apk'
            with ZipFile(source,'w') as archive:
                archive.writestr('classes4.dex', b'original-native-ui')
            receipt=add_bundle_asset(source,self.bundle())
            self.assertEqual(receipt['sha256'],hashlib.sha256(self.bundle()).hexdigest())
            with ZipFile(source) as archive:
                self.assertEqual(set(archive.namelist()),{'classes4.dex', ASSET_ENTRY})
                self.assertEqual(archive.read('classes4.dex'),b'original-native-ui')
                self.assertEqual(archive.read(ASSET_ENTRY),self.bundle())
            before=source.read_bytes()
            with self.assertRaises(ValueError): add_bundle_asset(source,self.bundle())
            self.assertEqual(source.read_bytes(),before)

    def test_duplicate_json_keys_and_excessive_bundle_are_rejected(self):
        for data in [b'{"schema_version":1,"schema_version":1}', b' '* (8*1024**2+1)]:
            with self.assertRaises(ValueError):validate_bundle(data)


if __name__=='__main__':unittest.main()
