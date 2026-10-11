"""Synthetic 35-lane source-only scene97 audit, no actual owner data/device."""
from __future__ import annotations

from hashlib import md5
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from tools.base_mod import audit_scene97_offline_readiness as audit
from tools.base_mod.recover_offline_original_server_cache import (
    OfflineOwnerCacheBlocked, ORIGINAL_DOWNLOAD_ARCHIVE_BYTES,
)


class OriginalScene97LaneReadinessTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="kn-scene97-synthetic-")
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name)
        (self.repo / "private").mkdir()
        self.candidate = self.repo / "private" / "unsigned-source-fixture"
        self.candidate.mkdir()
        self.cache = self.repo / "private" / "synthetic-cache"
        self.cache.mkdir()
        self.expected = {}
        self.lane_members = []
        with ZipFile(self.candidate / "split_InstallPack.apk", "w") as zipfile:
            for lane in range(35):
                count = 18 if lane == 0 else 10
                specs = []
                for j in range(count):
                    idx = len(self.expected)
                    name = f"A{idx:03d}.list"
                    raw = b"" if idx == 0 else ("SYNTHETIC-" + name).encode()
                    assert name not in self.expected
                    self.expected[name] = raw
                    specs.append(
                        f"{name}\t{len(raw)}\t{md5(raw).hexdigest()}\n"
                    )
                total = (ORIGINAL_DOWNLOAD_ARCHIVE_BYTES - 34
                         if lane == 0 else 1)
                tsv = f"\t{total}\t{'0'*32}\n" + "".join(specs)
                zipfile.writestr(f"assets/download_{lane}.tsv", tsv)
                self.lane_members.append([f"A{i:03d}.list"
                                          for i in range(len(self.expected)-count,
                                                         len(self.expected))])
        self.assertEqual(len(self.expected), 358)

    def perform(self):
        return audit.audit_scene97(
            repo=self.repo, candidate=self.candidate, cache=self.cache)

    def test_incomplete_files_report_exact_35_lane_counts_without_writes(self):
        for name in self.lane_members[0][:3]:
            (self.cache / name).write_bytes(self.expected[name])
        report = self.perform()
        self.assertEqual(report["status"], audit.STATUS_INCOMPLETE)
        self.assertEqual(report["expected_member_count"], 358)
        self.assertEqual(report["member_bytes_and_md5_verified_count"], 3)
        self.assertEqual(report["missing_member_count"], 355)
        self.assertEqual(report["expected_lane_count"], 35)
        self.assertEqual(report["lanes_all_member_bytes_verified"], 0)
        self.assertEqual(report["lanes"][0]["member_verified_by_size_md5"], 3)
        self.assertFalse(report["android_import_authorized"])
        self.assertFalse(report["original_native_source_index_population_proven"])
        self.assertFalse(report["original_scene97_loader_accepted_data_proven"])
        self.assertFalse(report["original_35_archive_zip_md5_verified"])
        self.assertFalse((self.repo / "private" / "readiness.json").exists())
        with self.assertRaisesRegex(OfflineOwnerCacheBlocked, "NOT_ALL_ORIGINAL"):
            audit.require_complete_source(report)

    def test_complete_original_member_bytes_still_not_native_or_zip_pass(self):
        for name, raw in self.expected.items():
            (self.cache / name).write_bytes(raw)
        report = self.perform()
        self.assertEqual(report["status"], audit.STATUS_FULL)
        self.assertEqual(report["member_bytes_and_md5_verified_count"], 358)
        self.assertEqual(report["missing_member_count"], 0)
        self.assertEqual(report["lanes_all_member_bytes_verified"], 35)
        self.assertEqual(report["original_35_archives_declared_bytes"],
                         ORIGINAL_DOWNLOAD_ARCHIVE_BYTES)
        audit.require_complete_source(report)
        self.assertFalse(report["original_35_archive_zip_md5_verified"])
        self.assertFalse(report["original_gameplay_offline_acceptance_proven"])
        self.assertFalse(report["android_import_authorized"])

    def test_wrong_md5_blocks_entire_audit_no_false_progress(self):
        first = self.lane_members[0][0]
        (self.cache / first).write_bytes(b"malformed")
        with self.assertRaisesRegex(OfflineOwnerCacheBlocked, "byte/MD5 drift"):
            self.perform()
        self.assertEqual((self.cache / first).read_bytes(), b"malformed")

    def test_symlink_and_foreign_cache_rejected(self):
        outside = self.repo / "outside"
        outside.mkdir()
        with self.assertRaisesRegex(OfflineOwnerCacheBlocked, "owner-private"):
            audit.audit_scene97(
                repo=self.repo, candidate=self.candidate, cache=outside)
        bad = self.cache / self.lane_members[0][0]
        try:
            bad.symlink_to(self.repo / "out-of-scope.txt")
        except (OSError, NotImplementedError):
            pass
        else:
            with self.assertRaisesRegex(OfflineOwnerCacheBlocked, "symlink"):
                self.perform()

    def test_private_metadata_write_exclusive_and_outside_rejected(self):
        receipt = self.perform()
        output = self.repo / "private" / "metadata-only.json"
        audit.save_private_metadata(
            repo=self.repo, destination=output, report=receipt)
        recorded = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(recorded["missing_member_count"], 358)
        with self.assertRaisesRegex(OfflineOwnerCacheBlocked, "already exists"):
            audit.save_private_metadata(
                repo=self.repo, destination=output, report=receipt)
        with self.assertRaisesRegex(OfflineOwnerCacheBlocked, "owner-private"):
            audit.save_private_metadata(
                repo=self.repo, destination=self.repo / "public.json",
                report=receipt)

    def test_manifest_mismatch_fails_before_report(self):
        with ZipFile(self.candidate / "split_InstallPack.apk", "a") as archive:
            archive.writestr("assets/download_0.tsv", b"wrong duplicate")
        with self.assertRaisesRegex(OfflineOwnerCacheBlocked, "duplicated"):
            self.perform()


if __name__ == "__main__":
    unittest.main()
