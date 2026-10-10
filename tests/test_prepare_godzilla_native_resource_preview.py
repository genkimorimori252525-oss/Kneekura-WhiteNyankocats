"""Synthetic AES source-only native asset stream candidate for Godzilla 702_f.

No real Battle Cats art/list/pack, user SAVE, Android APK, or signing material.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

from tools.battlecats_pack import PackReader
from tools.base_mod.battlecats_pack_writer import _encrypt_entry, encrypt_manifest_bytes
from tools.base_mod import prepare_godzilla_native_resource_preview as native

SOURCE_PNG = b"\x89PNG\r\n\x1a\n" + b"SYNTHETIC_NON_DISPLAYABLE_IMAGE"


def _pair(family: str, contents: dict[str, bytes]) -> tuple[bytes, bytes]:
    packed = bytearray()
    rows = []
    for name, data in contents.items():
        ciphertext, mode = _encrypt_entry(family, data, region="jp")
        assert mode == "aes-128-ecb-server"
        rows.append(f"{name},{len(packed)},{len(ciphertext)}")
        packed.extend(ciphertext)
    manifest = encrypt_manifest_bytes(
        (str(len(rows)) + "\n" + "\n".join(rows) + "\n").encode()
    )
    return manifest, bytes(packed)


class GodzillaOriginalNativeResourceCandidateTests(unittest.TestCase):
    def setUp(self):
        self.source = {
            **{name: ("ORIGINAL_W_IMAGE_" + name).encode()
               for name in native.FIRST_FORM_DATA},
            "702_c.imgcut": b"UNMODIFIED_SECOND_FORM_CUT",
            "702_c.mamodel": b"UNMODIFIED_SECOND_FORM_MODEL",
            "100_e.mamodel": b"UNRELATED_ENEMY_MODEL",
        }
        self.preview = {name: b"CANDIDATE_" + name.encode()
                        for name in native.FIRST_FORM_DATA}
        self.preview[native.PNG_NAME] = SOURCE_PNG
        self.original_list, self.original_pack = _pair(native.FAMILY, self.source)

    def test_replace_only_6_existing_slots_plus_one_new_first_form_png(self):
        before_manifest, before_pack = self.original_list, self.original_pack
        manifest, pack, receipt = native.prepare_wimage_first_form_candidate(
            before_manifest, before_pack, self.preview
        )
        self.assertEqual((self.original_list, self.original_pack),
                         (before_manifest, before_pack))
        self.assertTrue(receipt["source_first_successful_name_registration_priority_static"])
        self.assertEqual(receipt["original_family_index_zero_based"], 4)
        self.assertEqual(receipt["existing_QNumberServer_family_index_zero_based"], 27)
        self.assertEqual(receipt["candidate_entry_count"],
                         receipt["original_source_entry_count"] + 1)
        self.assertEqual(set(receipt["changed_original_first_form_entries"]),
                         set(native.FIRST_FORM_DATA))
        self.assertFalse(receipt["original_second_form_bytes_changed"])
        self.assertFalse(receipt["unrelated_original_server_resource_bytes_changed"])
        self.assertFalse(receipt["candidate_original_download_table_MD5_still_valid"])
        self.assertFalse(receipt["original_game_running_or_battle_verified"])
        self.assertFalse(receipt["ready_to_install"])
        original = PackReader(native.FAMILY, before_manifest, before_pack)
        candidate = PackReader(native.FAMILY, manifest, pack)
        for name, value in self.preview.items():
            self.assertEqual(candidate.read(name)[0], value)
        for name in self.source:
            if name not in self.preview:
                self.assertEqual(candidate.read(name)[0], original.read(name)[0])
        self.assertFalse(original.has(native.PNG_NAME))
        self.assertTrue(candidate.has(native.PNG_NAME))

    def test_source_missing_original_form_slot_or_second_form_fails_closed(self):
        for missing in ("702_f02.maanim", "702_c.mamodel"):
            with self.subTest(missing=missing):
                contents = dict(self.source)
                contents.pop(missing)
                man, pack = _pair(native.FAMILY, contents)
                with self.assertRaisesRegex(native.OriginalGodzillaResourcePreviewError,
                                             "lacks necessary"):
                    native.prepare_wimage_first_form_candidate(
                        man, pack, self.preview
                    )

    def test_preexisting_same_key_702_f_png_refuses_ambiguous_registration(self):
        original = dict(self.source)
        original[native.PNG_NAME] = b"OLD_OTHER_OWNER_PNG"
        man, pack = _pair(native.FAMILY, original)
        with self.assertRaisesRegex(native.OriginalGodzillaResourcePreviewError,
                                     "already has 702_f.png"):
            native.prepare_wimage_first_form_candidate(man, pack, self.preview)

    def test_unapproved_first_form_payloads_and_bad_png_fail_closed(self):
        for change in ("missing", "extra", "badPNG", "empty", "nonbytes"):
            candidate = dict(self.preview)
            if change == "missing":
                del candidate["702_f03.maanim"]
            elif change == "extra":
                candidate["702_c.png"] = b"unsafe second form"
            elif change == "badPNG":
                candidate[native.PNG_NAME] = b"not a real PNG"
            elif change == "empty":
                candidate["702_f00.maanim"] = b""
            else:
                candidate["702_f00.maanim"] = "wrong type"
            with self.subTest(change=change), self.assertRaises(
                native.OriginalGodzillaResourcePreviewError
            ):
                native.prepare_wimage_first_form_candidate(
                    self.original_list, self.original_pack, candidate
                )

    def test_private_source_only_refuses_invalid_md5_and_output_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "private" / "source"
            art = root / "private" / "preview"
            output = root / "private" / "candidate"
            source.mkdir(parents=True)
            art.mkdir()
            (source / "WImageDataServer.list").write_bytes(self.original_list)
            (source / "WImageDataServer.pack").write_bytes(self.original_pack)
            for name, blob in self.preview.items():
                (art / name).write_bytes(blob)
            proof = {
                "status": "GODZILLA_FIRST_FORM_RIG_PREVIEW_ONLY_NOT_INSTALLABLE",
                "ready_to_install": False, "second_form_bytes_changed": False,
                "candidate_ally_art": {
                    name: {"bytes": len(blob), "sha256": sha256(blob).hexdigest()}
                    for name, blob in self.preview.items()
                },
            }
            (art / "rig-conversion-preview-receipt.json").write_text(json.dumps(proof))
            with self.assertRaises(ValueError):
                native.preview_private_candidate(source, art, output)
            self.assertFalse(output.exists())
            receipts = native.preview_private_candidate(
                source, art, output, enforce_owner_file_md5=False
            )
            self.assertFalse(receipts["ready_to_install"])
            self.assertEqual((output / "WImageDataServer.list").is_file(), True)
            self.assertEqual((output / "WImageDataServer.pack").is_file(), True)
            self.assertEqual((output / "candidate-research-receipt.json").is_file(), True)
            self.assertEqual((source / "WImageDataServer.pack").read_bytes(),
                             self.original_pack)
            with self.assertRaisesRegex(native.OriginalGodzillaResourcePreviewError,
                                         "output must be new"):
                native.preview_private_candidate(
                    source, art, output, enforce_owner_file_md5=False
                )
            self.assertFalse((output / "702_c.mamodel").exists())

    def test_wrong_candidate_provenance_refused_before_creating_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "s"
            art = root / "a"
            output = root / "target"
            source.mkdir()
            art.mkdir()
            (source / "WImageDataServer.list").write_bytes(self.original_list)
            (source / "WImageDataServer.pack").write_bytes(self.original_pack)
            for n, data in self.preview.items():
                (art / n).write_bytes(data)
            fake = {"status":"GODZILLA_FIRST_FORM_RIG_PREVIEW_ONLY_NOT_INSTALLABLE",
                    "ready_to_install":False,"second_form_bytes_changed":False,
                    "candidate_ally_art":{n: {"bytes":len(v),"sha256":sha256(v).hexdigest()}
                                         for n,v in self.preview.items()}}
            fake["candidate_ally_art"]["702_f02.maanim"]["sha256"] = "0"*64
            (art / "rig-conversion-preview-receipt.json").write_text(json.dumps(fake))
            with self.assertRaisesRegex(native.OriginalGodzillaResourcePreviewError,
                                         "hash changed"):
                native.preview_private_candidate(
                    source, art, output, enforce_owner_file_md5=False
                )
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
