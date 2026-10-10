"""Synthetic 550_e source files only: no original art/animation/game binaries."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from tools.base_mod import prepare_godzilla_ally_preview as preview


def png(width: int = 64, height: int = 48) -> bytes:
    def chunk(name: bytes, body: bytes) -> bytes:
        return (
            struct.pack(">I", len(body)) + name + body
            + struct.pack(">I", zlib.crc32(name + body) & 0xFFFFFFFF)
        )
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(b"\0" * (height * (width * 4 + 1))))
        + chunk(b"IEND", b"")
    )


def rig(*, bom: bool = True, eol: bytes = b"\r\n") -> dict[str, bytes]:
    b = b"\xef\xbb\xbf" if bom else b""
    cut = b + eol.join([
        b"[imgcut]", b"0", b"550_e.png", b"2",
        b"0,0,1,1,Null",
        b"1,1,5,7,Tail",
        b"",
    ])
    model = b + eol.join([
        b"[modelanim:model2]", b"4", b"3",
        b"-1,-1,0,0,0,0,0,0,-1000,1000,0,1000,0,Null",
        b"0,550,1,0,0,0,0,0,1000,1000,0,1000,0,Head",
        b"1,550,0,0,0,0,0,0,1000,1000,0,1000,0,Tail",
        b"1000,3600,1000,1", b"1",
        b"0,0,-48,350,10,0,collision",
        b"",
    ])
    anim = b + eol.join([
        b"[modelanim:animation2]", b"2", b"2",
        b"1,5,-1,0,0,Move", b"2",
        b"0,0,0,0", b"10,100,0,0",
        b"1,11,-1,0,0,Attack", b"1",
        b"0,0,0,0",
        b"",
    ])
    return {
        "550_e.png": png(),
        "550_e.imgcut": cut,
        "550_e.mamodel": model,
        **{f"550_e0{i}.maanim": anim for i in range(4)}
    }


def fake_receipt(data: dict[str, bytes]) -> dict:
    return {
        "status": "EXTRACTED_OWNER_ONLY_NOT_MIRRORED_OR_INSTALLED",
        "source_stem": "550_e",
        "target_stem": "702_f",
        "art": {
            name: {"sha256": sha256(payload).hexdigest(), "size": len(payload)}
            for name, payload in data.items()
        },
    }


class GodzillaNo703FirstFormCandidateTests(unittest.TestCase):
    def setUp(self):
        self.source = rig()

    def test_convert_enemy_into_only_first_form_without_modifying_original(self):
        original = deepcopy(self.source)
        outputs, record = preview.preview_converted_ally_rig(
            self.source, source_receipt=fake_receipt(self.source)
        )
        self.assertEqual(set(outputs), {
            "702_f.png", "702_f.imgcut", "702_f.mamodel",
            "702_f00.maanim", "702_f01.maanim",
            "702_f02.maanim", "702_f03.maanim",
        })
        self.assertEqual(outputs["702_f.png"], original["550_e.png"])
        self.assertEqual(self.source, original)
        self.assertIn(b"702_f.png\r\n", outputs["702_f.imgcut"])
        self.assertNotIn(b"550_e.png", outputs["702_f.imgcut"])
        self.assertIn(
            b"-1,-1,0,0,0,0,0,0,1000,1000,0,1000,0,Null",
            outputs["702_f.mamodel"],
        )
        self.assertIn(b"0,702,1,0,0,0,0,0,1000,1000", outputs["702_f.mamodel"])
        self.assertNotIn(b"0,550,1,0,0,0,0,0", outputs["702_f.mamodel"])
        self.assertTrue(outputs["702_f.mamodel"].endswith(
            b"0,0,-48,350,10,0,collision\r\n"
        ))
        for i in range(4):
            self.assertEqual(
                outputs[f"702_f0{i}.maanim"], original[f"550_e0{i}.maanim"]
            )
        self.assertTrue(record["mamodel_conversion"]["root_was_reoriented"])
        self.assertEqual(record["mamodel_conversion"]["atlas_rows_rebased"], 2)
        self.assertEqual(record["imgcut_conversion"]["sprite_part_count"], 2)
        self.assertFalse(record["ready_to_install"])
        self.assertEqual(record["preserved_second_form"], "702_c")
        self.assertFalse(record["second_form_bytes_changed"])
        self.assertFalse(record["animation_renderer_frame_sync_verified"])

    def test_already_correct_root_orientation_remains_unchanged(self):
        model = self.source["550_e.mamodel"].replace(
            b"-1000,1000,0,1000,0,Null", b"1000,1000,0,1000,0,Null"
        )
        self.source["550_e.mamodel"] = model
        targets, record = preview.preview_converted_ally_rig(self.source)
        self.assertFalse(record["mamodel_conversion"]["root_was_reoriented"])
        self.assertIn(b"1000,1000,0,1000,0,Null", targets["702_f.mamodel"])

    def test_utf8_bom_and_lf_variants_stay_parseable(self):
        inputs = rig(bom=False, eol=b"\n")
        out, receipt = preview.preview_converted_ally_rig(inputs)
        self.assertTrue(out["702_f.imgcut"].startswith(b"[imgcut]\n"))
        self.assertTrue(out["702_f.mamodel"].startswith(b"[modelanim:model2]\n"))
        self.assertEqual(receipt["atlas_geometry"], {"width": 64, "height": 48})

    def test_missing_source_or_wrong_receipt_hash_refuses_conversion(self):
        broken = dict(self.source)
        broken.pop("550_e02.maanim")
        with self.assertRaisesRegex(preview.OriginalGodzillaRigPreviewError,
                                     "exactly seven"):
            preview.preview_converted_ally_rig(broken)
        proof = fake_receipt(self.source)
        proof["art"]["550_e.mamodel"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(preview.OriginalGodzillaRigPreviewError,
                                     "art changed"):
            preview.preview_converted_ally_rig(self.source, source_receipt=proof)

    def test_original_model_unexpected_atlas_id_refused(self):
        bad = dict(self.source)
        bad["550_e.mamodel"] = bad["550_e.mamodel"].replace(
            b"0,550,1,", b"0,551,1,"
        )
        with self.assertRaisesRegex(preview.OriginalGodzillaRigPreviewError,
                                     "another atlas image ID"):
            preview.preview_converted_ally_rig(bad)

    def test_original_imgcut_missing_rows_bad_image_or_bounds_fail(self):
        cases = [
            ("550_e.png", b"not a png", "PNG"),
            ("550_e.imgcut", self.source["550_e.imgcut"].replace(
                b"550_e.png", b"702_f.png"), "header"),
            ("550_e.imgcut", self.source["550_e.imgcut"].replace(
                b"\r\n2\r\n", b"\r\n3\r\n"), "count"),
            ("550_e.imgcut", self.source["550_e.imgcut"].replace(
                b"1,1,5,7,Tail", b"60,1,5,7,Tail"), "outside"),
        ]
        for name, payload, reason in cases:
            with self.subTest(name=name,reason=reason):
                bad = dict(self.source)
                bad[name] = payload
                with self.assertRaises(preview.OriginalGodzillaRigPreviewError):
                    preview.preview_converted_ally_rig(bad)

    def test_truncated_model_and_animations_fail_before_output(self):
        one = dict(self.source)
        one["550_e.mamodel"] = one["550_e.mamodel"].replace(
            b"\r\n3\r\n", b"\r\n8\r\n"
        )
        with self.assertRaises(preview.OriginalGodzillaRigPreviewError):
            preview.preview_converted_ally_rig(one)
        two = dict(self.source)
        two["550_e02.maanim"] = two["550_e02.maanim"].replace(
            b"1,5,-1,0,0,Move\r\n2\r\n", b"1,5,-1,0,0,Move\r\n999\r\n"
        )
        with self.assertRaises(preview.OriginalGodzillaRigPreviewError):
            preview.preview_converted_ally_rig(two)

    def test_directory_staged_once_and_original_7_files_stay_identical(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "original-enemy"
            output = root / "ally-preview"
            source.mkdir()
            for filename, raw in self.source.items():
                (source / filename).write_bytes(raw)
            (source / "rig-receipt.json").write_text(
                __import__("json").dumps(fake_receipt(self.source)),
                encoding="utf-8",
            )
            receipt = preview.prepare_from_private_source(source, output)
            self.assertEqual(receipt["target_stem"], "702_f")
            self.assertTrue((output / "rig-conversion-preview-receipt.json").exists())
            self.assertFalse((output / "702_c.mamodel").exists())
            for name, blob in self.source.items():
                self.assertEqual((source / name).read_bytes(), blob)
            with self.assertRaisesRegex(preview.OriginalGodzillaRigPreviewError,
                                         "must not exist"):
                preview.prepare_from_private_source(source, output)

    def test_invalid_input_does_not_make_output_dir_or_write_half_a_rig(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "enemy"
            output = root / "target"
            source.mkdir()
            for name, blob in self.source.items():
                (source / name).write_bytes(blob)
            (source / "550_e03.maanim").write_bytes(b"broken")
            with self.assertRaises(preview.OriginalGodzillaRigPreviewError):
                preview.prepare_from_private_source(source, output)
            self.assertFalse(output.exists())
            self.assertFalse(list(root.glob(".kneekura-ally-rig-preview-*")))


if __name__ == "__main__":
    unittest.main()
