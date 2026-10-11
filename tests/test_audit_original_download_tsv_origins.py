"""Synthetic exact original TSV source-matrix adversarial tests.

All source files are disposable fake ZIP/list fixtures; no Battle Cats files,
Android app, network, key store or protected SAVE are accessed.
"""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from tools.battlecats_pack import PackEntry
from tools.base_mod import audit_original_download_tsv_origins as module
from tools.base_mod.recover_offline_original_server_cache import OfflineOwnerCacheBlocked


class OriginalSourceIndexPrecedenceTests(unittest.TestCase):
    def setUp(self):
        temporary=TemporaryDirectory(prefix="kn-scene97-origins-synthetic-")
        self.addCleanup(temporary.cleanup)
        self.repo=Path(temporary.name)
        self.private=self.repo/"private"
        self.private.mkdir()
        self.candidate=self.private/"candidate"
        self.candidate.mkdir()
        self.cache=self.private/"cache"
        self.cache.mkdir()
        self.index=self.candidate/"split_InstallPack.apk"
        self.packs={"AServer.list":(8,"0"*32),"AServer.pack":(7,"0"*32)}
        (self.cache/"AServer.list").write_bytes(b"SERVER")
        (self.cache/"AServer.pack").write_bytes(b"NOTREAL")

    def write_apk(self, missing=None):
        with ZipFile(self.index,"w") as z:
            for i in range(35):
                if i!=missing:
                    z.writestr(f"assets/download_{i}.tsv",b"dummy")
            z.writestr("assets/DataLocal.list",b"LOCAL")
            z.writestr("assets/DownloadLocal.list",b"LOCAL")

    def fake_index(self,payload):
        if payload == b"LOCAL":
            return 0,[]
        if payload == b"SERVER":
            return 0,[]
        raise ValueError("untrusted synthetic list")

    def inspect(self, *, index=None, verified=True):
        self.write_apk(missing=index)
        with patch.object(module,"audit_scene97",return_value={
            "all_original_extracted_members_verified":verified}), \
             patch.object(module,"owner_manifest",return_value=self.packs), \
             patch.object(module,"parse_manifest",side_effect=self.fake_index):
            return module.audit_original_download_tsv_origins(
                repo=self.repo,candidate=self.candidate,cache=self.cache)

    def test_plain_apk_direct_35_not_server_index(self):
        out=self.inspect()
        self.assertEqual(out["direct_InstallPack_asset_names"],35)
        self.assertEqual(out["encrypted_local_pack_TSV_name_count"],0)
        self.assertEqual(out["encrypted_server_pack_TSV_name_count"],0)
        self.assertFalse(out["original_runtime_named_source_index_initialized"])
        self.assertFalse(out["loose_app_private_TSV_can_satisfy_resolver"])
        self.assertFalse(out["original_game_cat_base_accepted"])
        self.assertFalse(out["Android_apk_or_SAVE_modified"])

    def test_declared_index_collision_recorded_without_precedence_claim(self):
        self.write_apk()
        def competing(payload):
            if payload == b"LOCAL":
                return 1,[PackEntry("download_1.tsv",0,0)]
            if payload == b"SERVER":
                return 1,[PackEntry("download_1.tsv",0,0)]
            raise ValueError("synthetic")
        with patch.object(module,"audit_scene97",return_value={
            "all_original_extracted_members_verified":True}), \
             patch.object(module,"owner_manifest",return_value=self.packs), \
             patch.object(module,"parse_manifest",side_effect=competing):
            result=module.audit_original_download_tsv_origins(
                repo=self.repo,candidate=self.candidate,cache=self.cache)
        self.assertEqual(result["encrypted_local_pack_TSV_name_count"],1)
        self.assertEqual(result["encrypted_server_pack_TSV_name_count"],1)
        self.assertFalse(result["loose_app_private_TSV_can_satisfy_resolver"])
        self.assertFalse(result["original_game_scene97_completed"])

    def test_missing_direct_tsv_rejected(self):
        with self.assertRaisesRegex(OfflineOwnerCacheBlocked,"direct TSV"):
            self.inspect(index=20)

    def test_incomplete_original_358_cache_blocks_source_claim(self):
        with self.assertRaisesRegex(OfflineOwnerCacheBlocked,"complete owner 358"):
            self.inspect(verified=False)


if __name__ == "__main__":
    unittest.main()
