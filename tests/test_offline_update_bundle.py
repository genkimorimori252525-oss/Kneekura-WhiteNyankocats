"""Source-only signed operator ZIP test suite. No device/network/save involved."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from Crypto.PublicKey import ECC

from tools.localcore.offline_update_bundle import (
    BundleError, build_bundle, import_bundle, keygen, rollback_content,
    verify_bundle, _fingerprint,
)

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "ops/seasons/2026-autumn-prototype.json"


def published() -> dict:
    content = json.loads(DRAFT.read_text(encoding="utf-8"))
    content["status"] = "published"
    # Every not-ready game stage/gacha stays blocked by the resolver.
    return content


class SignedOfflineUpdateTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.root = Path(self.work.name)
        self.keys = keygen(self.root / "secrets")
        self.private = Path(self.keys["private_key"])
        self.public = Path(self.keys["public_key"])
        self.store = self.root / "installed-local-content"

    def _build(self, pack: dict, filename: str, *,
               previous_revision=None, previous_sha256=None) -> Path:
        dest = self.root / filename
        build_bundle(pack, self.private, dest,
                     previous_revision=previous_revision,
                     previous_sha256=previous_sha256)
        return dest

    def test_only_one_signed_zip_with_pinned_public_key(self):
        bundle = self._build(published(), "version1.kneekura.zip")
        self.assertLess(bundle.stat().st_size, 2 * 1024 * 1024)
        with zipfile.ZipFile(bundle) as z:
            self.assertEqual(set(z.namelist()), {
                "manifest.json", "ops.json", "signature.der",
            })
        manifest, data = verify_bundle(bundle, self.public)
        self.assertEqual(manifest["revision"], 1)
        self.assertFalse(manifest["requires_network"])
        self.assertFalse(manifest["contains_player_state"])
        self.assertEqual(data["channel"], "kneekura-main-offline")
        with self.assertRaises(BundleError):
            self._build(published(), "version1.kneekura.zip")

    def test_draft_never_becomes_installable(self):
        with self.assertRaisesRegex(BundleError, "published"):
            self._build(json.loads(DRAFT.read_text(encoding="utf-8")), "draft.zip")
        self.assertFalse((self.root / "draft.zip").exists())

    def test_verify_rejects_unknown_operator_key_and_modified_manifest(self):
        good = self._build(published(), "good.zip")
        stranger = keygen(self.root / "stranger")
        with self.assertRaisesRegex(BundleError, "pinned"):
            verify_bundle(good, Path(stranger["public_key"]))

        tampered = self.root / "tampered.zip"
        with zipfile.ZipFile(good) as src, zipfile.ZipFile(tampered, "w") as dst:
            for name in src.namelist():
                payload = src.read(name)
                if name == "manifest.json":
                    p = json.loads(payload.decode())
                    p["revision"] = 2
                    payload = json.dumps(p, sort_keys=True, ensure_ascii=False,
                                         separators=(",", ":")).encode()
                dst.writestr(name, payload)
        with self.assertRaisesRegex(BundleError, "signature"):
            verify_bundle(tampered, self.public)

    def test_zip_slip_extra_or_duplicate_entry_refused(self):
        good = self._build(published(), "good.zip")
        for name in ("../SAVE_DATA", "secret.txt", "ops.json"):
            bad = self.root / (name.replace("/", "x") + ".zip")
            with zipfile.ZipFile(good) as src, zipfile.ZipFile(bad, "w") as dst:
                for original in src.infolist():
                    dst.writestr(original.filename, src.read(original.filename))
                dst.writestr(name, b"bad")
            with self.assertRaises(BundleError):
                verify_bundle(bad, self.public)

    def test_import_idempotent_and_player_save_bytes_unchanged(self):
        original_save = self.root / "kneekura-local-v1.json"
        original_save.write_bytes(b'{"player_items":100}')
        before = hashlib.sha256(original_save.read_bytes()).hexdigest()
        bundle = self._build(published(), "initial.zip")
        receipt = import_bundle(bundle, self.public, self.store)
        self.assertEqual(receipt["status"], "CONTENT_IMPORTED_ONLY_NOT_ANDROID_ENGINE")
        self.assertFalse(receipt["player_save_changed"])
        self.assertEqual(import_bundle(bundle, self.public, self.store)["status"],
                         "ALREADY_INSTALLED_NO_WRITE")
        self.assertEqual(hashlib.sha256(original_save.read_bytes()).hexdigest(), before)
        self.assertEqual(len(list((self.store / "revisions").glob("*.json"))), 1)

    def test_new_revision_requires_exact_predecessor_and_supports_rollback(self):
        first_pack = published()
        first = self._build(first_pack, "v1.zip")
        v1 = import_bundle(first, self.public, self.store)
        self.assertEqual(v1["revision"], 1)
        successor = deepcopy(first_pack)
        successor["revision"] = 2
        successor["catalog"]["notice"][0]["title"] = "ローカル更新 v2"
        # wrong predecessor must be rejected before ANY current-pointer write
        bad = self._build(successor, "v2bad.zip", previous_revision=1,
                          previous_sha256="0"*64)
        current_before = (self.store / "current.json").read_bytes()
        with self.assertRaisesRegex(BundleError, "stale|chain"):
            import_bundle(bad, self.public, self.store)
        self.assertEqual((self.store / "current.json").read_bytes(), current_before)
        signed = self._build(successor, "v2good.zip", previous_revision=1,
                             previous_sha256=v1["content_sha256"])
        result = import_bundle(signed, self.public, self.store)
        self.assertEqual(result["revision"], 2)
        reverted = rollback_content(self.store)
        self.assertEqual(reverted["revision"], 1)
        with self.assertRaises(BundleError):
            rollback_content(self.store)

    def test_missing_or_corrupted_current_content_fails_closed(self):
        first = self._build(published(), "v1.zip")
        import_bundle(first, self.public, self.store)
        revision = next((self.store / "revisions").glob("*.json"))
        revision.write_bytes(b"corrupted")
        before = (self.store / "current.json").read_bytes()
        successor = deepcopy(published())
        successor["revision"] = 2
        new = self._build(successor, "v2.zip", previous_revision=1,
                          previous_sha256=json.loads(before)["content_sha256"])
        with self.assertRaises(BundleError):
            import_bundle(new, self.public, self.store)
        self.assertEqual((self.store / "current.json").read_bytes(), before)

    def test_no_network_tokens_and_owned_private_key_never_embedded(self):
        bundle = self._build(published(), "v1.zip")
        private_key_contents = self.private.read_bytes()
        with zipfile.ZipFile(bundle) as archive:
            for item in archive.namelist():
                self.assertNotIn(private_key_contents, archive.read(item))
        self.assertEqual(self.private.stat().st_size > 100, True)


if __name__ == "__main__":
    unittest.main()
