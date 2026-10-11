"""Synthetic safety tests for historical owner-private original server data recovery.

No owner game assets, phone, SAVE, keystore, 615MiB download or public network.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from tools.base_mod import recover_offline_original_server_cache as cache


class OriginalOfflineMirrorVerifiedRecoveryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="kn-server-cache-synthetic-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root/"private").mkdir()
        self.candidate = self.root/"private/candidate"
        self.candidate.mkdir()
        with ZipFile(self.candidate/"split_InstallPack.apk","w") as z:
            for i in range(35):
                z.writestr(f"assets/download_{i}.tsv", "\t1\t"+"0"*32+"\n")
        self.out = self.root/"private/verified"
        self.one = b"the-original-file"
        self.two = b"another-original-file"
        self.expected = {
            "AUnitServer.list": (len(self.one),hashlib.md5(self.one).hexdigest()),
            "AUnitServer.pack": (len(self.two),hashlib.md5(self.two).hexdigest()),
        }

    def test_reject_unavailable_or_corrupt_exact_installpack_manifest(self):
        with self.assertRaisesRegex(cache.OfflineOwnerCacheBlocked, "shape/count drift"):
            cache.owner_manifest(self.candidate/"split_InstallPack.apk")
        with patch.object(cache, "owner_manifest", return_value=self.expected):
            with self.assertRaisesRegex(cache.OfflineOwnerCacheBlocked, "owner-private"):
                cache.recover(repo=self.root,candidate=self.candidate,
                              output=self.root/"public-output",mode="plan")

    def test_plan_no_mirror_network_and_no_write(self):
        with patch.object(cache,"owner_manifest",return_value=self.expected), \
             patch.object(cache,"public_mirror_inventory") as internet:
            result=cache.recover(repo=self.root,candidate=self.candidate,
                                 output=self.out,mode="plan")
        internet.assert_not_called()
        self.assertEqual(result["verified_original_members"],0)
        self.assertEqual(result["missing_original_members"],2)
        self.assertFalse(self.out.exists())

    def test_download_accepts_only_exact_original_size_and_md5(self):
        def write_verified(dest, expected, *, opener=None):
            payload = self.one if dest.name.endswith(".list") else self.two
            dest.write_bytes(payload)
            return cache.verify(dest, expected)
        with patch.object(cache,"owner_manifest",return_value=self.expected), \
             patch.object(cache,"public_mirror_inventory",
                          return_value={"AUnitServer.list":len(self.one),
                                        "AUnitServer.pack":len(self.two),
                                        "BogusServer.pack":1}), \
             patch.object(cache,"stage_verified",side_effect=write_verified):
            result=cache.recover(repo=self.root,candidate=self.candidate,
                                 output=self.out,mode="download",max_workers=1)
        self.assertEqual(result["verified_original_members"],2)
        self.assertEqual(result["missing_original_members"],0)
        self.assertTrue(result["all_original_member_MD5_proven"])
        self.assertFalse(result["original_game_boot_verified"])
        self.assertFalse(result["APK_installed_or_SAVE_modified"])
        self.assertNotIn("BogusServer.pack",list(p.name for p in self.out.iterdir()))
        self.assertTrue((self.out/"PRIVATE-METADATA-ONLY-RECEIPT.json").is_file())

    def test_wrong_checksum_blocks_existing_private_corrupt_asset(self):
        self.out.mkdir()
        (self.out/"AUnitServer.list").write_bytes(b"wrong")
        with patch.object(cache,"owner_manifest",return_value=self.expected):
            with self.assertRaisesRegex(cache.OfflineOwnerCacheBlocked,"mismatched"):
                cache.recover(repo=self.root,candidate=self.candidate,
                              output=self.out,mode="verify")

    def test_mirror_inventory_rejects_path_traversal_and_oversize(self):
        class Reply:
            status=200
            def __init__(self, payload): self.payload=payload
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self,n): return json.dumps(self.payload).encode()
        with self.assertRaisesRegex(cache.OfflineOwnerCacheBlocked,"mirror name/size"):
            cache.public_mirror_inventory(
                opener=lambda req,timeout:Reply([
                    {"type":"file","name":"../unsafe.pack","size":10}
                ]))

if __name__=="__main__":
    unittest.main()
