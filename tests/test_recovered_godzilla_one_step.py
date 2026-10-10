"""Synthetic AES game-pack Godzilla handoff tests; no copyrighted assets."""
from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.base_mod import fetch_godzilla_server_assets as recovery
from tools.base_mod.battlecats_pack_writer import (
    _encrypt_entry, encrypt_manifest_bytes,
)
from tools.base_mod.extract_godzilla_owner_rig import PNG_FILE, ANIM_FILES


def fixture_pair(family: str, assets: dict[str, bytes]) -> tuple[bytes, bytes]:
    stream = bytearray()
    rows = []
    for filename, data in assets.items():
        ciphertext, mode = _encrypt_entry(family, data, region="jp")
        assert mode == "aes-128-ecb-server"
        rows.append(f"{filename},{len(stream)},{len(ciphertext)}")
        stream.extend(ciphertext)
    manifest = encrypt_manifest_bytes(
        (str(len(rows)) + "\n" + "\n".join(rows) + "\n").encode()
    )
    return manifest, bytes(stream)


class OwnerRecoveredGodzillaOneStepTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.owner = self.root / "recovered"
        self.cache = self.root / "private" / "godzilla"
        self.rig = self.root / "private" / "godzilla-550_e-original"
        self.owner.mkdir()
        self.actual = {}
        m_manifest, m_pack = fixture_pair(
            "MNumberServer", {
                PNG_FILE: b"\x89PNG\r\n\x1a\n" + b"synthetic-no-real-graphics",
            }
        )
        w_manifest, w_pack = fixture_pair(
            "WImageDataServer", {
                filename: (filename + ":fake-model-data").encode()
                for filename in ANIM_FILES
            },
        )
        self.actual = {
            "MNumberServer.list": m_manifest,
            "MNumberServer.pack": m_pack,
            "WImageDataServer.list": w_manifest,
            "WImageDataServer.pack": w_pack,
        }
        for name, data in self.actual.items():
            (self.owner / name).write_bytes(data)
        self.original = recovery.FILES
        recovery.FILES = {
            name: (len(data), hashlib.md5(data).hexdigest())
            for name, data in self.actual.items()
        }
        self.addCleanup(setattr, recovery, "FILES", self.original)

    def test_one_command_owner_import_then_exact_7_asset_private_stage(self):
        receipt = recovery.acquire("import", self.cache, self.owner)
        self.assertEqual(len(receipt["files"]), 4)
        out = recovery.extract_verified_local_godzilla_rig(
            self.cache, self.rig, private_root=self.root / "private",
        )
        self.assertEqual(out["status"], "EXTRACTED_OWNER_ONLY_NOT_MIRRORED_OR_INSTALLED")
        self.assertEqual(out["source_stem"], "550_e")
        self.assertEqual(out["target_stem"], "702_f")
        self.assertEqual(out["cat_form_index"], 0)
        self.assertFalse(out["ready_to_install"])
        self.assertFalse(out["has_runtime_sprite_override"])
        self.assertEqual(set(out["art"]), {PNG_FILE, *ANIM_FILES})
        self.assertEqual(
            {p.name for p in self.rig.iterdir()},
            {PNG_FILE, *ANIM_FILES, "rig-receipt.json"},
        )
        self.assertEqual(
            out["sources"]["MNumberServer.pack"],
            hashlib.sha256(self.actual["MNumberServer.pack"]).hexdigest(),
        )
        for n in self.actual:
            self.assertEqual((self.owner / n).read_bytes(), self.actual[n])

    def test_missing_7th_animation_refused_without_creating_rig(self):
        files = {
            n: (n + ":fake").encode()
            for n in ANIM_FILES if n != "550_e03.maanim"
        }
        manifest, pack = fixture_pair("WImageDataServer", files)
        self.cache.mkdir(parents=True)
        self.actual["WImageDataServer.list"] = manifest
        self.actual["WImageDataServer.pack"] = pack
        for name, data in self.actual.items():
            (self.cache / name).write_bytes(data)
        recovery.FILES = {
            name: (len(data), hashlib.md5(data).hexdigest())
            for name, data in self.actual.items()
        }
        with self.assertRaisesRegex(ValueError, "missing required original"):
            recovery.extract_verified_local_godzilla_rig(
                self.cache, self.rig, private_root=self.root / "private"
            )
        self.assertFalse(self.rig.exists())

    def test_invalid_md5_or_unsafe_rig_destination_never_overwrites(self):
        self.cache.mkdir(parents=True)
        for name, data in self.actual.items():
            (self.cache / name).write_bytes(data)
        invalid = self.cache / "WImageDataServer.pack"
        invalid.write_bytes(invalid.read_bytes() + b"!")  # original checksum fails
        with self.assertRaisesRegex(ValueError, "mismatch"):
            recovery.extract_verified_local_godzilla_rig(
                self.cache, self.rig, private_root=self.root / "private"
            )
        self.assertFalse(self.rig.exists())
        invalid.write_bytes(self.actual["WImageDataServer.pack"])
        with self.assertRaisesRegex(ValueError, "NEW under private"):
            recovery.extract_verified_local_godzilla_rig(
                self.cache, self.root / "outside",
                private_root=self.root / "private",
            )
        self.rig.mkdir()
        (self.rig / "user-data.txt").write_text("PROTECTED")
        with self.assertRaisesRegex(ValueError, "NEW under private"):
            recovery.extract_verified_local_godzilla_rig(
                self.cache, self.rig, private_root=self.root / "private",
            )
        self.assertEqual((self.rig / "user-data.txt").read_text(), "PROTECTED")

    def test_cli_explicit_one_step_from_existing_owner_cache(self):
        output = self.root / "private"
        with patch.object(recovery, "PRIVATE_ROOT", output):
            result = recovery.main([
                "--from-dir", str(self.owner),
                "--output", str(self.cache),
                "--extract-original-godzilla-rig",
                "--rig-output", str(self.rig),
            ])
        self.assertEqual(result, 0)
        self.assertTrue((self.rig / "rig-receipt.json").is_file())
        self.assertFalse((self.rig / "702_f.png").exists())  # conversion not done


if __name__ == "__main__":
    unittest.main()
