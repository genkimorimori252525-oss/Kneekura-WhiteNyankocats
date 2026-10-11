"""Synthetic no-network original JP15.7.1 download before/after diffs."""
from __future__ import annotations

from hashlib import md5
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import unittest

from tools.base_mod.compare_original_download_snapshots import (
    compare_download_snapshots, PRIVATE_SNAPSHOT_STATUS,
)
from tools.base_mod.recover_offline_original_server_cache import (
    OfflineOwnerCacheBlocked, ORIGINAL_DOWNLOAD_ARCHIVE_BYTES,
)


class Original615MBPrivateDownloadDiffTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(prefix="kn-download-diff-synthetic-")
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        self.private = self.repo / "private"
        self.private.mkdir()
        self.candidate = self.private / "original-signed-six"
        self.candidate.mkdir()
        self.before = self.private / "before"
        self.after = self.private / "after"
        self.before.mkdir()
        self.after.mkdir()
        self.content = {}
        with ZipFile(self.candidate / "split_InstallPack.apk", "w") as archive:
            index = 0
            for lane in range(35):
                count = 18 if lane == 0 else 10
                entries = []
                for _ in range(count):
                    filename = f"S{index:03d}Server.list"
                    value = b"" if index == 0 else (f"synthetic:{index}").encode()
                    self.content[filename] = value
                    entries.append(
                        f"{filename}\t{len(value)}\t{md5(value).hexdigest()}\n")
                    index += 1
                archive_bytes = (
                    ORIGINAL_DOWNLOAD_ARCHIVE_BYTES - 34 if lane == 0 else 1)
                header = f"\t{archive_bytes}\t{'0'*32}\n"
                archive.writestr(f"assets/download_{lane}.tsv",
                                 header + "".join(entries))
        self.assertEqual(len(self.content), 358)

    def diff(self, **kwargs):
        return compare_download_snapshots(
            repo=self.repo, candidate=self.candidate,
            before=kwargs.get("before", self.before),
            after=kwargs.get("after", self.after),
        )

    def test_absent_before_and_after_never_implies_download_success(self):
        report = self.diff()
        self.assertEqual(report["status"], PRIVATE_SNAPSHOT_STATUS)
        self.assertEqual(report["changes"]["absent_both"], 358)
        self.assertEqual(report["after_missing_original_members"], 358)
        self.assertFalse(report["all_original_member_bytes_verified_after"])
        self.assertFalse(report["android_import_authorized"])

    def test_exact_original_member_addition_and_change(self):
        names = list(self.content)
        one, two = names[0], names[1]
        (self.before / two).write_bytes(b"previous-version")
        (self.after / one).write_bytes(self.content[one])
        (self.after / two).write_bytes(self.content[two])
        report = self.diff()
        self.assertEqual(report["changes"]["added"], 1)
        self.assertEqual(report["changes"]["changed"], 1)
        self.assertEqual(report["after_exact_size_and_md5_verified_members"], 2)
        self.assertEqual(report["after_missing_original_members"], 356)
        self.assertFalse(report["native_source_index_and_scene97_accepted"])

    def test_mismatched_after_bytes_not_counted_and_no_save_read(self):
        filename = next(name for name, data in self.content.items() if data)
        (self.after / filename).write_bytes(b"wrong-data")
        (self.before / "SAVE_DATA").write_bytes(b"SECRET_PLAYER_SAVE_BEFORE")
        (self.after / "SAVE_DATA").write_bytes(b"SECRET_PLAYER_SAVE_AFTER")
        report = self.diff()
        self.assertEqual(report["after_present_but_mismatched_original_members"], 1)
        self.assertEqual(report["after_exact_size_and_md5_verified_members"], 0)
        self.assertFalse(report["SAVE_DATA_or_account_content_read"])
        self.assertFalse(report["other_unlisted_APP_files_read"])
        self.assertFalse(any(
            item["member"] == "SAVE_DATA"
            for item in report["changed_original_member_metadata"]
        ))

    def test_full_358_members_verified_still_not_zip_or_game_boot(self):
        for name, value in self.content.items():
            (self.after / name).write_bytes(value)
        report = self.diff()
        self.assertEqual(report["after_exact_size_and_md5_verified_members"], 358)
        self.assertEqual(report["changes"]["added"], 358)
        self.assertTrue(report["all_original_member_bytes_verified_after"])
        self.assertFalse(report["original_download_35_zip_archives_verified"])
        self.assertFalse(report["native_source_index_and_scene97_accepted"])
        self.assertFalse(report["android_import_authorized"])

    def test_foreign_and_nested_snapshot_roots_fail_closed(self):
        outside = self.repo / "foreign"
        outside.mkdir()
        with self.assertRaisesRegex(OfflineOwnerCacheBlocked, "owner-private"):
            self.diff(after=outside)
        nested = self.after / "nested"
        nested.mkdir()
        with self.assertRaisesRegex(OfflineOwnerCacheBlocked, "nested"):
            self.diff(before=nested)

    def test_source_member_symlink_refused_even_if_target_expected(self):
        name = next(iter(self.content))
        foreign = self.repo / "external-file"
        foreign.write_bytes(self.content[name])
        link = self.after / name
        try:
            link.symlink_to(foreign)
        except (NotImplementedError, OSError):
            self.skipTest("Windows native symlink privileges unavailable")
        with self.assertRaisesRegex(OfflineOwnerCacheBlocked, "symlink"):
            self.diff()


if __name__ == "__main__":
    unittest.main()
