"""Network-free regression tests for the owner-only Godzilla Server source recovery."""
import hashlib
import io
from pathlib import Path
import tempfile
import unittest

from tools.base_mod import fetch_godzilla_server_assets as recovery


class Response(io.BytesIO):
    status = 200


class AcquireTest(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        self.payloads = {n: (n + ": owner bytes").encode() for n in recovery.FILES}
        self.original = recovery.FILES
        recovery.FILES = {n: (len(data), hashlib.md5(data).hexdigest())
                          for n, data in self.payloads.items()}

    def tearDown(self):
        recovery.FILES = self.original
        self.td.cleanup()

    def test_import_preverify_and_private_copy(self):
        src, dst = self.root / "source", self.root / "private"
        src.mkdir()
        for name, data in self.payloads.items():
            (src / name).write_bytes(data)
        proof = recovery.acquire("import", dst, src)
        self.assertEqual(len(proof["files"]), 4)
        self.assertTrue((dst / "godzilla-server-source-receipt.json").is_file())
        self.assertTrue(all((dst / name).read_bytes() == data for name, data in self.payloads.items()))

    def test_import_invalid_fails_before_any_copy(self):
        src, dst = self.root / "source", self.root / "private"
        src.mkdir()
        for name, data in self.payloads.items():
            (src / name).write_bytes(data)
        (src / "WImageDataServer.pack").write_bytes(b"bad")
        with self.assertRaisesRegex(ValueError, "mismatch"):
            recovery.acquire("import", dst, src)
        self.assertFalse(dst.exists())

    def test_download_mock_and_reuse_without_network(self):
        dst = self.root / "private"
        def opener(req, timeout=90):
            return Response(self.payloads[req.full_url.rsplit("/", 1)[-1]])
        receipt = recovery.acquire("download", dst, opener=opener)
        self.assertEqual(len(receipt["files"]), 4)
        def nope(*a, **k):
            raise AssertionError("must not open network for cached files")
        recovery.acquire("download", dst, opener=nope)
        self.assertFalse(list(dst.glob("*.part")))

    def test_failed_download_does_not_promote(self):
        dst = self.root / "private"
        name = "MNumberServer.list"
        with self.assertRaisesRegex(ValueError, "mismatch"):
            recovery.stage_verified(dst / name, recovery.FILES[name], opener=lambda *a, **k: Response(b"bad"))
        self.assertFalse((dst / name).exists())
        self.assertFalse(list(dst.glob("*.part")))

    def test_existing_conflict_preserved(self):
        dst = self.root / "private"
        dst.mkdir()
        name = "MNumberServer.list"
        (dst / name).write_bytes(b"invalid user data")
        with self.assertRaises(ValueError):
            recovery.stage_verified(dst / name, recovery.FILES[name])
        self.assertEqual((dst / name).read_bytes(), b"invalid user data")

    def test_verify_only_no_download(self):
        with self.assertRaisesRegex(ValueError, "missing file"):
            recovery.acquire("verify", self.root / "not-created")
        self.assertFalse((self.root / "not-created").exists())

    def test_pinned_original_metadata(self):
        self.assertEqual(self.original["WImageDataServer.pack"],
                         (79788272, "cebd0898a2c9d68fa3c7631afa9dd0d2"))
        self.assertEqual(sum(size for size, _ in self.original.values()), 90880336)


if __name__ == "__main__":
    unittest.main()
