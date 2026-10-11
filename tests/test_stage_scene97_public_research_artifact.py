"""Synthetic-only tests of public NDK scene97 research artifact verifier.

All binary fixtures are CREATED here; no original game, APK, SAVE, ADB,
research signer or real GitHub artifact downloaded or installed.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import struct
import tempfile
import unittest
from zipfile import ZipFile, ZipInfo
from unittest.mock import patch

from tools.base_mod import stage_scene97_public_research_artifact as subject


def mock_binary():
    result = bytearray(128)
    result[:4] = b"\x7fELF"
    result[4] = 2
    result[5] = 1
    struct.pack_into("<H", result, 18, 183)
    result.extend(b"|" + subject.MARKER + b"|source-only-passive")
    return bytes(result)


def mock_receipt(data: bytes):
    return json.dumps({
        "schema": "public-original-research-passive-shim-v1",
        "git_commit": subject.ARTIFACT_COMMIT,
        "sha256": sha256(data).hexdigest(),
        "elf_abi": "arm64-v8a",
        "fixed_error_markers_compiled": True,
        "scene97_resolver_histogram_compiled": True,
        "original_game_or_save_bundled": False,
        "original_save_writer_enabled": False,
    }).encode("utf-8")


def make_zip(target: Path, data: bytes, receipt: bytes,
             layout: str = "flat", extra: tuple[str, bytes] | None = None):
    prefix = "" if layout == "flat" else "build/kneekura-scene-research/"
    with ZipFile(target, "w") as handle:
        handle.writestr(prefix + subject.BINARY, data)
        handle.writestr(prefix + subject.RECEIPT, receipt)
        if extra is not None:
            handle.writestr(*extra)


class Scene97SourceOnlyArtifactTests(unittest.TestCase):
    def test_flat_and_nested_ci_layouts_verify_same_public_bytes(self):
        with tempfile.TemporaryDirectory(prefix="kn-pub-scene97-") as folder:
            root = Path(folder)
            data = mock_binary()
            receipt = mock_receipt(data)
            for layout in ("flat", "nested"):
                artifact = root / (layout + ".zip")
                make_zip(artifact, data, receipt, layout)
                payload = subject.inspect_artifact(
                    artifact, binary_sha256=sha256(data).hexdigest(),
                    commit=subject.ARTIFACT_COMMIT)
                self.assertEqual(payload[subject.BINARY], data)
                self.assertEqual(payload[subject.RECEIPT], receipt)

    def test_refuse_wrong_sha_owner_save_and_nonpassive_or_unsafe_archive(self):
        with tempfile.TemporaryDirectory(prefix="kn-pub-scene97-") as folder:
            root = Path(folder)
            data = mock_binary()
            receipt = mock_receipt(data)
            valid = root / "valid.zip"
            make_zip(valid, data, receipt)
            digest = sha256(data).hexdigest()
            with self.assertRaisesRegex(subject.Scene97PublicArtifactBlocked, "SHA256"):
                subject.inspect_artifact(valid, binary_sha256="0"*64)
            bad_metadata = json.loads(receipt)
            bad_metadata["original_save_writer_enabled"] = True
            changed = root / "writer.zip"
            make_zip(changed, data, json.dumps(bad_metadata).encode())
            with self.assertRaisesRegex(subject.Scene97PublicArtifactBlocked, "receipt"):
                subject.inspect_artifact(changed, binary_sha256=digest)
            bad_extra = root / "extra.zip"
            make_zip(bad_extra, data, receipt,
                     extra=("SAVE_DATA", b"FORBIDDEN_PRIVATE_PLACEHOLDER"))
            with self.assertRaisesRegex(subject.Scene97PublicArtifactBlocked, "member layout"):
                subject.inspect_artifact(bad_extra, binary_sha256=digest)
            bad_magic = bytearray(data)
            bad_magic[:4] = b"xxxx"
            bad = root / "bad-elf.zip"
            make_zip(bad, bytes(bad_magic), mock_receipt(bytes(bad_magic)))
            with self.assertRaisesRegex(subject.Scene97PublicArtifactBlocked, "ELF64"):
                subject.inspect_artifact(
                    bad, binary_sha256=sha256(bytes(bad_magic)).hexdigest())

    def test_create_only_private_staging_and_no_overwrite_on_mismatch(self):
        with tempfile.TemporaryDirectory(prefix="kn-pub-scene97-") as folder:
            repo = Path(folder)
            (repo / "private").mkdir()
            data = mock_binary()
            files = {subject.BINARY:data,subject.RECEIPT:mock_receipt(data)}
            status, target = subject.stage_artifact(repo, files)
            self.assertEqual(status, "STAGED_PUBLIC_RESEARCH_ONLY")
            self.assertEqual(target.parent,repo/"private")
            self.assertEqual(set(item.name for item in target.iterdir()),
                             {subject.BINARY,subject.RECEIPT})
            self.assertEqual(subject.stage_artifact(repo,files)[0],
                             "ALREADY_STAGED_IDENTICAL")
            (target / subject.RECEIPT).write_bytes(b"synthetic-mismatch")
            with self.assertRaises(subject.Scene97PublicArtifactBlocked):
                subject.stage_artifact(repo, files)
            self.assertEqual((target/subject.RECEIPT).read_bytes(),
                             b"synthetic-mismatch")

    def test_symlink_archive_fails_before_read(self):
        with tempfile.TemporaryDirectory(prefix="kn-pub-scene97-") as folder:
            root = Path(folder)
            data=mock_binary(); src=root/"source.zip"
            make_zip(src,data,mock_receipt(data))
            link=root/"link.zip"
            try:
                link.symlink_to(src)
            except (OSError, NotImplementedError):
                self.skipTest("current OS cannot create user symlinks")
            with self.assertRaisesRegex(subject.Scene97PublicArtifactBlocked, "unsafe"):
                subject.inspect_artifact(link)


if __name__ == "__main__":
    unittest.main()
