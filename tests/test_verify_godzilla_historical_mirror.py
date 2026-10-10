"""Test only sanitized ephemeral mirror receipts; no actual remote network calls."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.base_mod import verify_godzilla_historical_mirror as mirror
from tools.base_mod import fetch_godzilla_server_assets as owner


class EphemeralRealGodzillaMirrorTests(unittest.TestCase):
    def test_public_network_requires_explicit_opt_in(self):
        with patch.object(owner, "acquire") as dangerous_download:
            report = mirror.verify_public_mirror_volatile(
                allow_mirror_download=False
            )
            dangerous_download.assert_not_called()
        self.assertEqual(report["status"],
                         "BLOCKED_EXPLICIT_NETWORK_OPT_IN_REQUIRED")
        self.assertFalse(report["ready_to_install_or_ship"])

    def test_success_receipt_has_only_metadata_not_original_asset_bytes(self):
        source = [
            {
                "name": name, "size": size, "md5": md5,
                "sha256": ("0" if i == 0 else "1") * 64,
            }
            for i, (name, (size, md5)) in enumerate(owner.FILES.items())
        ]
        art_names = (
            "550_e.png", "550_e.imgcut", "550_e.mamodel",
            "550_e00.maanim", "550_e01.maanim",
            "550_e02.maanim", "550_e03.maanim",
        )
        preview_names = {
            n.replace("550_e", "702_f") for n in art_names
        }
        expected = {
            "godzilla_original_rig": {
                "ready_to_install": False,
                "art": {n: {"size": 15, "sha256": "a" * 64} for n in art_names},
            },
            "godzilla_ally_preview": {
                "ready_to_install": False,
                "candidate_ally_art": {
                    n: {
                        "bytes": 15,
                        "sha256": ("b" if n.endswith(
                            (".imgcut", ".mamodel")
                        ) else "a") * 64,
                    }
                    for n in preview_names
                },
                "atlas_geometry": {"width": 1024, "height": 1000},
                "imgcut_conversion": {"sprite_part_count": 28},
                "mamodel_conversion": {
                    "declared_model_nodes": 45,
                    "atlas_rows_rebased": 44,
                    "root_was_reoriented": False,
                    "extra_collision_and_model_footer_bytes_preserved": True,
                },
                "animations_untouched": {
                    f"550_e0{i}.maanim": {
                        "track_count": 1, "keyframe_count": 4,
                        "negative_frame_key_count": 1,
                        "special_minus_two_node_track_count": 0,
                        "largest_frame_number": 80,
                        "zero_keyframe_track_count": 0,
                    } for i in range(4)
                },
            },
            "godzilla_WImageDataServer_research_candidate": {
                "ready_to_install": False,
                "original_source_entry_count": 300,
                "candidate_entry_count": 301,
                "original_second_form_bytes_changed": False,
                "unrelated_original_server_resource_bytes_changed": False,
                "changed_original_first_form_entries": [
                    "702_f.imgcut", "702_f.mamodel",
                    "702_f00.maanim", "702_f01.maanim",
                    "702_f02.maanim", "702_f03.maanim",
                ],
                "candidate_extra_PNG_in_earlier_WImageDataServer":
                    "702_f.png",
                "candidate_manifest_sha256": "c" * 64,
                "candidate_pack_sha256": "d" * 64,
            },
        }
        original_secret = b"NEVER_EXPOSE_ORIGINAL_PNG_BYTES_88"
        model = (
            b"[modelanim:model2]\n4\n1\n"
            b"-1,-1,0,0,0,0,0,0,1000,1000,0,1000,0,Control\n"
        )
        called = []
        def fake_download(mode, directory, *args, **kwargs):
            called.append(("download", mode, directory))
            self.assertEqual(mode, "download")
            self.assertTrue(directory.is_relative_to(Path(directory.parents[1])))
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "WImageDataServer.list").write_bytes(b"MOCKED_TEST_MANIFEST")
            (directory / "WImageDataServer.pack").write_bytes(b"MOCKED_TEST_PACK")
            return {"files": source}
        def fake_private_pipeline(source_dir, **kwargs):
            called.append(("private", source_dir, kwargs["private_root"]))
            self.assertTrue(source_dir.is_dir() or not source_dir.exists())
            self.assertEqual(source_dir.name, "mirror")
            target = kwargs["ally_output"] if "ally_output" in kwargs else kwargs.get("ally_output", kwargs.get("ally_output"))
            # Pipeline accepts ally_output as a keyword, and keeps this
            # fixture entirely under TemporaryDirectory for deletion.
            target.mkdir(parents=True, exist_ok=True)
            (target / "702_f.mamodel").write_bytes(model)
            return expected

        class MockPackReader:
            def __init__(self, *args, **kwargs):
                pass
            def read(self, name):
                self.last_name = name
                return model, None
        with patch.object(owner, "acquire", side_effect=fake_download), \
             patch.object(owner, "complete_owner_private_godzilla_pipeline",
                          side_effect=fake_private_pipeline), \
             patch.object(mirror, "PackReader", MockPackReader):
            report = mirror.verify_public_mirror_volatile(
                allow_mirror_download=True
            )
        self.assertEqual(report["status"],
                         "PASS_ORIGINAL_PUBLIC_ARCHIVE_MATCHED_AND_PRIVATE_PREVIEW_BUILT")
        self.assertEqual(len(called), 2)
        self.assertEqual(set(report["source_original_archives"]), set(owner.FILES))
        self.assertEqual(len(report["original_enemy_art_550e"]), 7)
        self.assertEqual(len(report["candidate_first_form_702f"]), 7)
        self.assertTrue(report["PNG_and_four_maanim_SHA256_all_unchanged"])
        self.assertTrue(
            report["original_allied_model_comparison"]
                ["candidate_matches_original_friendly_root_scale_sign"]
        )
        self.assertEqual(report["real_model_conversion"]["atlas_550_to_702_rows"], 44)
        self.assertFalse(report["ready_to_install_or_ship"])
        self.assertFalse(report["actual_original_Android_renderer_accepted"])
        self.assertNotIn(original_secret.decode(), json.dumps(report))
        self.assertNotIn("source_dir", json.dumps(report))

    def test_unrecognized_pipeline_exception_is_never_returned_raw(self):
        secret = "player_token=UNSAFE_PRIVATE_ACCOUNT"
        with patch.object(owner, "acquire", side_effect=RuntimeError(secret)):
            report = mirror.verify_public_mirror_volatile(
                allow_mirror_download=True
            )
        self.assertEqual(report["status"], "BLOCKED_ORIGINAL_MIRROR_SOURCE_OR_FORMAT")
        self.assertNotIn(secret, repr(report))
        self.assertEqual(report["failure_type"], "RuntimeError")
        self.assertFalse(report["ready_to_install_or_ship"])
        self.assertEqual(report["last_stage"], "historical-source-download")

    def test_metadata_only_file_is_exclusive_and_tiny(self):
        with tempfile.TemporaryDirectory() as root:
            receipt_path = Path(root) / "proof" / "original-mirror.json"
            receipt = mirror._base_receipt()
            mirror.write_metadata_receipt(receipt_path, receipt)
            self.assertEqual(json.loads(receipt_path.read_text()), receipt)
            with self.assertRaisesRegex(ValueError, "new JSON file"):
                mirror.write_metadata_receipt(receipt_path, receipt)
            self.assertFalse((Path(root) / "private").exists())

    def test_arbitrary_file_or_non_json_output_refused(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError, "new JSON file"):
                mirror.write_metadata_receipt(
                    Path(root) / "godzilla-original.pack", mirror._base_receipt()
                )
            very_large = mirror._base_receipt()
            very_large["asset_content"] = "x" * (mirror.RESULT_LIMIT + 1)
            with self.assertRaisesRegex(ValueError, "oversized"):
                mirror.write_metadata_receipt(
                    Path(root) / "bad.json", very_large
                )

    def test_failure_codes_are_bounded_and_do_not_retain_paths_or_urls(self):
        cases = [
            ("JP15.7.1 size/MD5 mismatch: MNumberServer.list",
             "ORIGINAL_SOURCE_SIZE_OR_MD5_MISMATCH"),
            ("Connection timeout", "PUBLIC_ARCHIVE_NETWORK_UNAVAILABLE"),
            ("invalid animation node", "ORIGINAL_RIG_FORMAT_NOT_SUPPORTED"),
            ("unknown WImageDataServer manifest format",
             "ORIGINAL_PACK_FORMAT_NOT_SUPPORTED"),
        ]
        for original, expected in cases:
            with self.subTest(original=original):
                self.assertEqual(mirror._error_code(original), expected)


if __name__ == "__main__":
    unittest.main()
