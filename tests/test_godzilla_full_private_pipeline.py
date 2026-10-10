"""One-command synthetic encrypted JP server -> Godzilla first form candidate.

This is a full in-memory SYNTHETIC fixture. No original pack, copyrighted art,
Android game, player SAVE or signing material is imported or committed.
"""
from __future__ import annotations

from hashlib import md5, sha256
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools.battlecats_pack import PackReader
from tools.base_mod import fetch_godzilla_server_assets as recovery
from tools.base_mod import prepare_godzilla_native_resource_preview as native_preview
from tools.base_mod.battlecats_pack_writer import (
    _encrypt_entry, encrypt_manifest_bytes,
)
from tools.base_mod.prepare_godzilla_native_resource_preview import (
    FIRST_FORM_DATA, PNG_NAME,
)


def _encrypted_pair(family: str, files: dict[str, bytes]) -> tuple[bytes, bytes]:
    body = bytearray()
    manifest_rows = []
    for name, raw in files.items():
        encoded, mode = _encrypt_entry(family, raw, region="jp")
        assert mode == "aes-128-ecb-server"
        manifest_rows.append(f"{name},{len(body)},{len(encoded)}")
        body.extend(encoded)
    text = f"{len(files)}\n" + "\n".join(manifest_rows) + "\n"
    return encrypt_manifest_bytes(text.encode()), bytes(body)


def _minimal_png() -> bytes:
    # Converter only checks PNG magic + IHDR geometry in this test;
    # the bytes are not a valid distributable sprite or copyrighted asset.
    return (
        b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR"
        + struct.pack(">IIBBBBB", 32, 32, 8, 6, 0, 0, 0)
        + b"\x00\x00\x00\x00"
    )


def _enemy_model() -> bytes:
    return (
        b"[modelanim:model2]\n4\n3\n"
        b"-1,-1,0,0,0,0,0,0,-1000,1000,0,1000,0,Null\n"
        b"0,550,1,0,0,0,0,0,1000,1000,0,1000,0,Head\n"
        b"1,-1,-1,0,0,0,0,0,1000,1000,0,1000,0,Invisible\n"
        b"1000,3600,1000,1\n"
    )


def _enemy_cut() -> bytes:
    return (
        b"[imgcut]\n0\n550_e.png\n2\n"
        b"0,0,1,1,Null\n1,1,5,7,Head\n"
    )


def _animation() -> bytes:
    return (
        b"[modelanim:animation2]\n2\n2\n"
        b"1,5,-1,0,0,Attack\n2\n"
        b"-10,0,0,0\n10,200,0,0\n"
        b"1,11,-1,0,0,Special\n0\n"
    )


class OriginalGodzillaFirstFormOneCommandIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.private = self.root / "private"
        self.owner = self.root / "owned"
        self.owner.mkdir()
        self.original_rig = {
            "550_e.imgcut": _enemy_cut(),
            "550_e.mamodel": _enemy_model(),
            **{f"550_e0{i}.maanim": _animation() for i in range(4)},
        }
        m = {"550_e.png": _minimal_png(), "unrelated.dat": b"OTHER_ORIGINAL"}
        w = {
            **self.original_rig,
            **{name: b"OLDER_ALLIED_FIRST_FORM_PLACEHOLDER"
               for name in FIRST_FORM_DATA},
            "702_c.imgcut": b"SECOND_FORM_ORIGINAL_CUT",
            "702_c.mamodel": b"SECOND_FORM_ORIGINAL_MODEL",
            "anything_else.dat": b"UNRELATED_ORIGINAL_BYTES",
        }
        m_list, m_pack = _encrypted_pair("MNumberServer", m)
        w_list, w_pack = _encrypted_pair("WImageDataServer", w)
        self.bodies = {
            "MNumberServer.list": m_list,
            "MNumberServer.pack": m_pack,
            "WImageDataServer.list": w_list,
            "WImageDataServer.pack": w_pack,
        }
        for name, body in self.bodies.items():
            (self.owner / name).write_bytes(body)
        self.expected = {
            name: (len(blob), md5(blob).hexdigest())
            for name, blob in self.bodies.items()
        }

    def _run(self, *, damage: str | None = None) -> tuple[int, Path, Path, Path]:
        imported = self.private / "godzilla-source"
        rig = self.private / "godzilla-enemy"
        ally = self.private / "godzilla-first-form"
        overlay = self.private / "godzilla-first-form-wimage"
        if damage:
            (self.owner / damage).write_bytes(b"wrong source data")
        args = [
            "--from-dir", str(self.owner),
            "--output", str(imported),
            "--extract-original-godzilla-rig",
            "--rig-output", str(rig),
            "--prepare-ally-preview",
            "--ally-preview-output", str(ally),
            "--prepare-native-resource-candidate",
            "--resource-preview-output", str(overlay),
        ]
        # The candidate also independently rechecks the owner's exact
        # MD5 metadata (immutable in production). Only synthetic tests
        # temporarily bind their own synthetic encrypted fixture hashes.
        with (patch.object(recovery, "FILES", self.expected),
              patch.object(native_preview, "EXACT_FILES", self.expected),
              patch.object(recovery, "PRIVATE_ROOT", self.private)):
            result = recovery.main(args)
        return result, rig, ally, overlay

    def test_full_encrypted_pipeline_preserves_owner_source_and_second_form(self):
        original_source = {
            name: (self.owner / name).read_bytes()
            for name in self.bodies
        }
        result, rig, ally, overlay = self._run()
        self.assertEqual(result, 0)
        self.assertEqual(
            {p.name for p in rig.iterdir()},
            {*self.original_rig, "550_e.png", "rig-receipt.json"},
        )
        first_art = {
            name: (ally / name).read_bytes()
            for name in [PNG_NAME, *FIRST_FORM_DATA]
        }
        self.assertTrue((ally / "rig-conversion-preview-receipt.json").is_file())
        self.assertTrue((overlay / "candidate-research-receipt.json").is_file())
        self.assertFalse((overlay / "702_c.mamodel").exists())
        woriginal = PackReader(
            "WImageDataServer", self.bodies["WImageDataServer.list"],
            self.bodies["WImageDataServer.pack"],
        )
        woverlay = PackReader(
            "WImageDataServer",
            (overlay / "WImageDataServer.list").read_bytes(),
            (overlay / "WImageDataServer.pack").read_bytes(),
        )
        self.assertFalse(woriginal.has(PNG_NAME))
        self.assertTrue(woverlay.has(PNG_NAME))
        for name, body in first_art.items():
            self.assertEqual(woverlay.read(name)[0], body)
        for name in ["702_c.imgcut", "702_c.mamodel", "anything_else.dat"]:
            self.assertEqual(woverlay.read(name)[0], woriginal.read(name)[0])
        for name, body in self.original_rig.items():
            self.assertEqual((rig / name).read_bytes(), body)
        for name, body in original_source.items():
            self.assertEqual((self.owner / name).read_bytes(), body)
        self.assertEqual((ally / "702_f.png").read_bytes(), _minimal_png())
        self.assertEqual((ally / "702_f01.maanim").read_bytes(), _animation())

    def test_late_resource_format_failure_cleans_all_invisible_stages(self):
        """Even AFTER real encrypted original rig and art have been built,
        failing the final native resource candidate must publish NOTHING.
        """
        rig_was_created_inside_private_stage = []
        def last_stage_drift(source, ally, output, *, private_root=None):
            rig_was_created_inside_private_stage.append(
                (source / "WImageDataServer.pack").is_file()
                and (ally / "702_f.mamodel").is_file()
            )
            raise ValueError("original real Server manifest contains unknown columns")
        with patch.object(
            recovery, "prepare_private_native_resource_candidate",
            side_effect=last_stage_drift,
        ):
            result, rig, ally, overlay = self._run()
        self.assertEqual(result, 2)
        self.assertEqual(rig_was_created_inside_private_stage, [True])
        self.assertFalse(rig.exists())
        self.assertFalse(ally.exists())
        self.assertFalse(overlay.exists())
        self.assertFalse((self.private / "godzilla-source").exists())
        self.assertFalse(list(self.private.glob(".kneekura-godzilla-4stage-*")))

    def test_one_filesystem_commit_error_rolls_back_own_directories(self):
        """If final candidate promotion fails, earlier output dirs created
        by the same invocation are removed; owner source files are untouched.
        """
        owner_before = {
            name: (self.owner / name).read_bytes()
            for name in self.bodies
        }
        original_rename = Path.rename
        def fail_last_publish(item, destination):
            if (item.name == "candidate"
                and item.parent.name.startswith(".kneekura-godzilla-4stage-")):
                raise OSError("synthetic late directory publication failure")
            return original_rename(item, destination)
        with patch.object(Path, "rename", fail_last_publish):
            result, rig, ally, overlay = self._run()
        self.assertEqual(result, 2)
        self.assertFalse(rig.exists())
        self.assertFalse(ally.exists())
        self.assertFalse(overlay.exists())
        self.assertFalse((self.private / "godzilla-source").exists())
        for name, prior in owner_before.items():
            self.assertEqual((self.owner / name).read_bytes(), prior)
        self.assertFalse(list(self.private.glob(".kneekura-godzilla-4stage-*")))

    def test_existing_user_private_output_is_never_overwritten(self):
        previous_art = self.private / "godzilla-enemy"
        previous_art.mkdir(parents=True)
        (previous_art / "important-user-output.txt").write_text(
            "do-not-delete-owner-data", encoding="utf-8"
        )
        result, rig, ally, overlay = self._run()
        self.assertEqual(result, 2)
        self.assertEqual(
            (rig / "important-user-output.txt").read_text(encoding="utf-8"),
            "do-not-delete-owner-data",
        )
        self.assertFalse(ally.exists())
        self.assertFalse(overlay.exists())
        self.assertFalse((self.private / "godzilla-source").exists())

    def test_real_md5_mismatch_fails_before_any_private_output(self):
        result, rig, ally, overlay = self._run(damage="WImageDataServer.pack")
        self.assertEqual(result, 2)
        self.assertFalse(rig.exists())
        self.assertFalse(ally.exists())
        self.assertFalse(overlay.exists())
        self.assertFalse((self.private / "godzilla-source").exists())

    def test_full_pipeline_requires_local_original_sources_not_partial_network_mode(self):
        """A full build never downloads half the sources before a late failure."""
        for mode in (["--download"], ["--verify-only"]):
            with self.subTest(mode=mode):
                with patch.object(recovery, "PRIVATE_ROOT", self.private):
                    with self.assertRaises(SystemExit):
                        recovery.main([
                            *mode,
                            "--extract-original-godzilla-rig",
                            "--prepare-ally-preview",
                            "--prepare-native-resource-candidate",
                            "--output", str(self.private / "godzilla-source"),
                        ])
                self.assertFalse(self.private.exists())

    def test_resource_candidate_requires_explicit_preceding_two_flags(self):
        with patch.object(recovery, "PRIVATE_ROOT", self.private):
            with self.assertRaises(SystemExit):
                recovery.main([
                    "--from-dir", str(self.owner),
                    "--prepare-native-resource-candidate",
                ])
        self.assertFalse(self.private.exists())


if __name__ == "__main__":
    unittest.main()
