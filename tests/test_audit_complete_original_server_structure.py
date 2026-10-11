"""Synthetic safety checks for original 93-server index metadata audit.

No original Battle Cats game assets, private APK, Android device or SAVE.
The actual decryption parser is independently tested in battlecats_pack tests.
"""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.battlecats_pack import PackEntry
from tools.base_mod import audit_complete_original_server_structure as subject
from tools.base_mod.recover_offline_original_server_cache import OfflineOwnerCacheBlocked


class CompleteServerStructureAuditTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory(prefix="kn-full-server-index-synthetic-")
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name)
        self.root = self.repo / "private"
        self.root.mkdir()
        self.candidate = self.root / "candidate"
        self.cache = self.root / "cache"
        self.candidate.mkdir()
        self.cache.mkdir()
        self.families = [f"A{n:03d}Server" for n in range(93)]
        self.expected = {}
        for family in self.families:
            self.expected[family+".list"] = (len(family), "0"*32)
            self.expected[family+".pack"] = (4096, "0"*32)
            (self.cache / (family+".list")).write_text(family)
            (self.cache / (family+".pack")).write_bytes(b"\0" * 4096)
        self.expected.update({f"music{n:03d}.ogg": (0, "0"*32)
                              for n in range(172)})
        self.assertEqual(len(self.expected), 358)

    def parse(self, raw: bytes):
        name = raw.decode()
        count = 660 if name == self.families[0] else 360
        return count, [PackEntry(f"asset{n}.png", n, 1)
                       for n in range(count)]

    def run_audit(self, *, parse=None, complete=True):
        with patch.object(
            subject, "audit_scene97",
            return_value={"all_original_extracted_members_verified":complete,
                          "member_bytes_and_md5_verified_count":358},
        ), patch.object(subject, "owner_manifest", return_value=self.expected), \
             patch.object(subject, "parse_manifest",
                          side_effect=parse or self.parse):
            return subject.audit_pack_structure(
                repo=self.repo, candidate=self.candidate, cache=self.cache)

    def test_all_index_ranges_verified_but_native_not_approved(self):
        report = self.run_audit()
        self.assertEqual(report["exact_list_pack_pairs"], 93)
        self.assertEqual(report["declared_internal_resource_entries"], 33780)
        self.assertEqual(report["decrypted_original_list_indexes"], 93)
        self.assertEqual(report["internal_resource_type_counts"], {".png":33780})
        self.assertTrue(report["all_original_server_pack_offset_ranges_verified"])
        self.assertFalse(report["scene97_original_game_cache_accepted"])
        self.assertFalse(report["original_native_source_index_registered"])
        self.assertFalse(report["device_or_SAVE_written"])

    def test_missing_member_source_rejects_even_if_individual_pack_exists(self):
        with self.assertRaisesRegex(OfflineOwnerCacheBlocked, "INCOMPLETE_358"):
            self.run_audit(complete=False)

    def test_out_of_range_ciphertext_rejected(self):
        def malformed(raw: bytes):
            if raw.decode() == self.families[0]:
                return 1, [PackEntry("bad.png", 4095, 2)]
            return self.parse(raw)
        with self.assertRaisesRegex(OfflineOwnerCacheBlocked, "span overflow"):
            self.run_audit(parse=malformed)

    def test_duplicate_inner_names_rejected(self):
        def duplicate(raw: bytes):
            if raw.decode() == self.families[0]:
                return 2, [PackEntry("duplicate.png", 0, 1),
                           PackEntry("duplicate.png", 1, 1)]
            return self.parse(raw)
        with self.assertRaisesRegex(OfflineOwnerCacheBlocked, "duplicate"):
            self.run_audit(parse=duplicate)

    def test_missing_partner_pack_rejected(self):
        (self.cache / (self.families[0]+".pack")).unlink()
        with self.assertRaisesRegex(OfflineOwnerCacheBlocked, "pair missing"):
            self.run_audit()


if __name__=="__main__":
    unittest.main()
