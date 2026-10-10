"""Synthetic privacy/source checks for the owner-private unsigned JP15.7.1 builder.

The actual owner original ZIP is deliberately NEVER in repository/CI tests.
Public Android SDK/owner-export parity is run only in the owner's private PC.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.base_mod import prepare_original_research_presign as presign


class UnsignedOriginalResearchBuilderTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="kn-presign-synthetic-")
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        (self.repo / "private").mkdir()
        self.shim = self.repo / "private" / "synthetic-passive.so"
        self.shim.write_bytes(
            b"NO_GAME_NATIVE_DATA_" * 32
            + b"original-native-scene-hook-v1 hook-runtime-init-failed"
        )
        self.proof = self.repo / "private" / "source-receipt.json"
        self.metadata = {
            "schema": "public-original-research-passive-shim-v1",
            "git_commit": "a" * 40,
            "sha256": hashlib.sha256(self.shim.read_bytes()).hexdigest(),
            "elf_abi": "arm64-v8a",
            "original_save_writer_enabled": False,
            "fixed_error_markers_compiled": True,
        }
        self.proof.write_text(json.dumps(self.metadata))

    def test_only_valid_passive_CI_source_sha_and_no_save_writer_accepted(self):
        p = presign._source_receipt(self.shim, self.proof)
        self.assertEqual(p["sha256"], hashlib.sha256(self.shim.read_bytes()).hexdigest())
        for key, value in (
            ("sha256", "f" * 64),
            ("git_commit", "../bad source"),
            ("original_save_writer_enabled", True),
            ("fixed_error_markers_compiled", False),
        ):
            with self.subTest(key=key):
                malformed = dict(self.metadata, **{key: value})
                self.proof.write_text(json.dumps(malformed))
                with self.assertRaises(presign.UnsignedOriginalBuildBlocked):
                    presign._source_receipt(self.shim, self.proof)
        self.proof.write_text(json.dumps(self.metadata))
        self.shim.write_bytes(self.shim.read_bytes() + b"kneekura-original-virgin-save-trial-v1")
        self.metadata["sha256"] = hashlib.sha256(self.shim.read_bytes()).hexdigest()
        self.proof.write_text(json.dumps(self.metadata))
        with self.assertRaises(presign.UnsignedOriginalBuildBlocked):
            presign._source_receipt(self.shim, self.proof)

    def test_only_private_inputs_accepted(self):
        self.assertEqual(presign._inside_private(self.repo, self.proof), self.proof)
        outside = self.repo / "public-so"
        outside.write_bytes(b"synthetic")
        with self.assertRaises(presign.UnsignedOriginalBuildBlocked):
            presign._inside_private(self.repo, outside)

    def test_unsafe_source_receipt_rejected_without_touching_export(self):
        owner_zip = self.repo / "synthetic-not-an-original.zip"
        owner_zip.write_bytes(b"NO_OWNER_APK")
        aar = self.repo / "private" / "synthetic.aar"
        aar.write_bytes(b"FAKE_NOT_OFFICIAL")
        with patch.object(presign, "extract_owned_splits") as read_owner:
            with self.assertRaises(presign.UnsignedOriginalBuildBlocked):
                presign.prepare_unsigned_research(
                    repo=self.repo, owner_export=owner_zip,
                    passive_shim=self.shim, passive_receipt=self.proof,
                    official_aar=aar, javac=None, d8=None, android_jar=None,
                )
            read_owner.assert_not_called()

    def test_no_signing_apksigner_or_device_access_in_builder_contract(self):
        code = (Path(__file__).resolve().parents[1] /
                "tools/base_mod/prepare_original_research_presign.py").read_text()
        self.assertIn("verify_staged_original_scene_before_signing(", code)
        self.assertIn("verify_static_http_bridge(", code)
        self.assertIn("original-JP1571-unsigned-six", code)
        self.assertIn('"Android_APK_signed": False', code)
        self.assertIn('"Android_game_installed_or_launched": False', code)
        self.assertIn('"unsigned_original_splits_sha256": signed_bytes', code)
        for forbidden in ("baseline_resign(", "install-multiple", "pm clear",
                          "adb shell", "subprocess.run(", "keytool"):
            self.assertNotIn(forbidden, code)


if __name__ == "__main__":
    unittest.main()
