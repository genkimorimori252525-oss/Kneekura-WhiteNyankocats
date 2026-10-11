"""Synthetic-only original JP15.7.1 35-lane / 348-file mirror audit.

No original APK, audio, graphics, Server .pack/.list or account data stored.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.base_mod import audit_original_server_mirror as subject


def md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def original_style_synthetic_lanes():
    families = [
        "XImageDataServer", "XImageServer", "XMapServer", "XNumberServer",
        "XUnitServer", "MNumberServer", "WImageDataServer",
    ] + [f"Z{i}Server" for i in range(86)]
    assert len(families) == 93
    names = [
        f"{family}.{extension}"
        for family in families for extension in ("list", "pack")
    ] + [f"{i:03d}.ogg" for i in range(172)]
    assert len(names) == 358
    contents = {lane: ["\t123\t" + md5(b"header")] for lane in range(35)}
    for i, name in enumerate(names):
        if name == "XImageDataServer.list":
            payload = subject.encrypt_manifest_bytes(b"0\n")
        elif name == "XImageDataServer.pack":
            payload = b""
        else:
            payload = name.encode("ascii")
        contents[i % 35].append(
            f"{name}\t{len(payload)}\t{md5(payload)}"
        )
    return {
        lane: ("\n".join(rows) + "\n").encode("utf-8")
        for lane, rows in contents.items()
    }


class OriginalMirrorAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.download = original_style_synthetic_lanes()
        cls.rows = subject.parse_owner_download_tables(cls.download)

    def test_exact_35_lanes_358_rows_93_pairs_and_172_audio(self):
        self.assertEqual(len(self.rows), 358)
        self.assertEqual(self.rows["XImageDataServer.list"].size, 16)
        self.assertEqual(
            self.rows["XImageDataServer.list"].md5,
            "8a3af3c681dea113c37d04f722d56db1"
        )
        self.assertEqual(self.rows["XImageDataServer.pack"].size, 0)
        self.assertEqual(
            self.rows["XImageDataServer.pack"].md5,
            "d41d8cd98f00b204e9800998ecf8427e"
        )
        self.assertTrue(all(0 <= row.download_lane < 35
                            for row in self.rows.values()))

    def test_88_complete_mirror_families_plus_172_sound_gives_348_of_358(self):
        tree = {
            "truncated": False,
            "tree": [
                {"path": "jp_server/" + name,
                 "type": "blob", "size": row.size,
                 "sha": "abcdef" * 7}
                for name, row in self.rows.items()
                if not name.startswith("X")
            ],
        }
        mirror = subject.parse_historical_mirror_index(tree)
        receipt = subject.compare_mirror_size_metadata(self.rows, mirror)
        self.assertEqual(receipt["original_manifest_entries"], 358)
        self.assertEqual(receipt["mirror_candidate_entries"], 348)
        self.assertEqual(receipt["matching_filename_and_size"], 348)
        self.assertEqual(receipt["matching_server_list_pack_files"], 176)
        self.assertEqual(receipt["matching_audio_files"], 172)
        self.assertEqual(len(receipt["missing_filenames"]), 10)
        self.assertEqual(receipt["missing_original_family_names"], [
            "XImageDataServer", "XImageServer", "XMapServer",
            "XNumberServer", "XUnitServer",
        ])
        self.assertEqual(receipt["mismatching_sizes"], {})
        self.assertFalse(receipt["MD5_for_any_mirror_candidate_proven_by_tree"])
        self.assertFalse(receipt["full_original_offline_gameplay_or_SAVE_verified"])

    def test_mirror_wrong_size_never_counts_as_md5_verified(self):
        mirror = {
            "MNumberServer.list": self.rows["MNumberServer.list"].size + 1,
            "WImageDataServer.list": self.rows["WImageDataServer.list"].size,
        }
        receipt = subject.compare_mirror_size_metadata(self.rows, mirror)
        self.assertEqual(receipt["matching_filename_and_size"], 1)
        self.assertIn("MNumberServer.list", receipt["mismatching_sizes"])
        self.assertFalse(receipt["MD5_for_any_mirror_candidate_proven_by_tree"])

    def test_empty_x_image_data_is_byte_exact_and_deterministic(self):
        pair = subject.make_exact_original_empty_ximagedata(self.rows)
        self.assertEqual(len(pair["XImageDataServer.list"]), 16)
        self.assertEqual(pair["XImageDataServer.pack"], b"")
        self.assertEqual(
            hashlib.sha256(pair["XImageDataServer.list"]).hexdigest(),
            "4c221cca50268038f2ccfb3503383e099372bc787d2fa951db51c26299e7655c",
        )
        modified = dict(self.rows)
        modified["XImageDataServer.list"] = subject.OwnerRow(
            16, "f" * 32, 34
        )
        with self.assertRaisesRegex(
            subject.OriginalServerMirrorAuditError, "does not hash-match"
        ):
            subject.make_exact_original_empty_ximagedata(modified)

    def test_explicit_private_empty_pair_writes_only_two_no_overwrite(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            private = root / "private"
            private.mkdir()
            output = private / "empty-x-data"
            with (patch.object(subject, "OWNER_ROOT", root),
                  patch.object(subject, "PRIVATE_ROOT", private)):
                receipt = subject.write_exact_empty_pair_privately(
                    self.rows, Path("private/empty-x-data")
                )
                self.assertEqual(
                    receipt["status"], "EXACT_JP1571_EMPTY_XIMAGEDATA_PAIR_PRIVATE_ONLY"
                )
                self.assertEqual(
                    sorted(p.name for p in output.iterdir()),
                    ["XImageDataServer.list", "XImageDataServer.pack"],
                )
                self.assertFalse(receipt["original_game_loaded_empty_pair"])
                with self.assertRaisesRegex(
                    subject.OriginalServerMirrorAuditError,
                    "new directory under private",
                ):
                    subject.write_exact_empty_pair_privately(
                        self.rows, Path("private/empty-x-data")
                    )
                with self.assertRaises(subject.OriginalServerMirrorAuditError):
                    subject.write_exact_empty_pair_privately(
                        self.rows, root / "outside"
                    )

    def test_previously_recovered_private_files_recheck_actual_md5_only(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            owned = ("MNumberServer.list", "MNumberServer.pack",
                     "WImageDataServer.list", "WImageDataServer.pack")
            for name in owned:
                (root / name).write_bytes(name.encode("ascii"))
            result = subject.check_local_exact_md5(self.rows, root)
            self.assertEqual(result["verified_count"], 4)
            self.assertFalse(result["all_358_original_files_MD5_verified"])
            self.assertEqual(
                {x["name"] for x in result["verified_files"]}, set(owned)
            )
            source = root / "MNumberServer.pack"
            source.write_bytes(b"not correct size")
            with self.assertRaises(subject.OriginalServerMirrorAuditError):
                subject.check_local_exact_md5(self.rows, root)

    def test_parse_refuses_missing_lanes_duplicate_or_bad_md5(self):
        missing = dict(self.download)
        missing.pop(34)
        with self.assertRaisesRegex(
            subject.OriginalServerMirrorAuditError, "35 original download lanes"
        ):
            subject.parse_owner_download_tables(missing)
        repeated = dict(self.download)
        repeated[0] += b"MNumberServer.list\t1\t" + b"0"*32 + b"\n"
        with self.assertRaisesRegex(
            subject.OriginalServerMirrorAuditError, "duplicated"
        ):
            subject.parse_owner_download_tables(repeated)
        malformed = dict(self.download)
        malformed[0] += b"../private/SAVE_DATA\t1\t" + b"0"*32 + b"\n"
        with self.assertRaises(subject.OriginalServerMirrorAuditError):
            subject.parse_owner_download_tables(malformed)

    def test_public_git_tree_rejects_incomplete_or_traversal_and_duplicates(self):
        with self.assertRaisesRegex(
            subject.OriginalServerMirrorAuditError, "incomplete or truncated"
        ):
            subject.parse_historical_mirror_index({"truncated": True, "tree": []})
        malicious = {
            "truncated": False,
            "tree": [
                {"path": "jp_server/../../SAVE_DATA", "type": "blob", "size": 123},
                {"path": "jp_server/MNumberServer.list",
                 "type": "blob", "size": 2832},
                {"path": "jp_server/MNumberServer.list",
                 "type": "blob", "size": 2832},
            ],
        }
        with self.assertRaisesRegex(
            subject.OriginalServerMirrorAuditError, "duplicated mirror filename"
        ):
            subject.parse_historical_mirror_index(malicious)

    def test_original_export_exact_sha_stops_fake_zip_before_reading(self):
        with tempfile.TemporaryDirectory() as scratch:
            path = Path(scratch) / "pretend-owner.zip"
            path.write_bytes(b"not original game")
            with self.assertRaisesRegex(
                subject.OriginalServerMirrorAuditError, "SHA256 mismatch"
            ):
                subject.read_exact_owner_export_tables(path)

    def test_public_metadata_network_is_explicit_and_content_is_bounded(self):
        payload = json.dumps({
            "truncated": False,
            "tree": [{"path": "jp_server/MNumberServer.list",
                      "type": "blob", "size": 2832}],
        }).encode()
        seen = []
        def opener(req, timeout):
            seen.append(req.full_url)
            return io.BytesIO(payload)
        result = subject.fetch_metadata_only_tree(opener=opener)
        self.assertEqual(result["truncated"], False)
        self.assertEqual(seen, [subject.MIRROR_TREE_URL])
        self.assertNotIn("nyanko-assets.ponosgames.com", seen[0])


if __name__ == "__main__":
    unittest.main()
