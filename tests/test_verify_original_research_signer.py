"""Synthetic private-key signer matching; never access owner P12, device or SAVE."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.base_mod.verify_original_research_signer import (
    verify_before_sign, PrivateSignerPreflightBlocked, _private_key_aliases,
)
from tools.base_mod.repack import _classify_signer_failure


class FakeKeyAndAPKVerifier:
    def __init__(self, *, password_valid=True, aliases=("synthetic",),
                 certificate_matches=True, duplicate_matching=False):
        self.password_valid = password_valid
        self.aliases = aliases
        self.certificate_matches = certificate_matches
        self.duplicate_matching = duplicate_matching
        self.der = b"\x30" + b"synthetic-DER-not-an-owner-cert" * 14
        self.requests: list[list[str]] = []

    def __call__(self, argv, **options):
        self.requests.append(argv)
        if "-list" in argv:
            listing = ""
            for name in self.aliases:
                listing += (
                    "Alias name: " + name + "\n"
                    "Creation date: Oct 11, 2026\n"
                    "Entry type: PrivateKeyEntry\n"
                    "Certificate chain length: 1\n"
                )
            return subprocess.CompletedProcess(
                argv, 0 if self.password_valid else 1,
                listing if self.password_valid else "", "BAD_PASSWORD",
            )
        if "-exportcert" in argv:
            entry = argv[argv.index("-alias") + 1]
            valid = entry in self.aliases
            payload = self.der
            if entry != self.aliases[0] and not self.duplicate_matching:
                payload = b"\x30" + b"different-valid-synthetic-certificate" * 12
            return subprocess.CompletedProcess(
                argv, 0 if valid else 1, payload if valid else b"",
                b"" if valid else b"alias not found",
            )
        if "verify" in argv:
            fingerprint = (hashlib.sha256(self.der).hexdigest()
                           if self.certificate_matches else "f" * 64)
            return subprocess.CompletedProcess(
                argv, 0,
                "Signer #1 certificate SHA-256 digest: " + fingerprint, "",
            )
        raise AssertionError("unknown synthetic JDK or Android signer operation")


class OwnerSignerReadOnlyPreflightTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="kn-private-sign-synthetic-")
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        for name in ("research.p12", "baseline.apk", "keytool", "apksigner"):
            (self.base / name).write_bytes(b"SYNTHETIC_ONLY")
        self.kwargs = dict(
            keystore=self.base / "research.p12",
            alias="synthetic", storepass_env="SYNTHETIC_PRIVATE_PASSWORD",
            previously_signed_base=self.base / "baseline.apk",
            keytool=self.base / "keytool", apksigner=self.base / "apksigner",
        )

    def check(self, fake, **override):
        with patch.dict(os.environ, {
            "SYNTHETIC_PRIVATE_PASSWORD": "DO_NOT_PRINT_SYNTHETIC_SECRET",
        }):
            return verify_before_sign(**dict(self.kwargs, **override), runner=fake)

    def test_exact_existing_alias_password_and_cert(self):
        fake = FakeKeyAndAPKVerifier()
        self.assertEqual(
            self.check(fake),
            "PASS_EXISTING_RESEARCH_KEYSTORE_ALIAS_PASSWORD_AND_CERT_MATCH",
        )
        self.assertEqual(len(fake.requests), 3)
        self.assertTrue(any("-storepass:env" in x for x in fake.requests))
        self.assertTrue(any("-J-Duser.language=en" in x for x in fake.requests))
        for request in fake.requests:
            self.assertNotIn("DO_NOT_PRINT_SYNTHETIC_SECRET", str(request))
            self.assertFalse(any(token.startswith("pass:") for token in request))

    def test_wrong_password_blocks_before_any_certificate_query(self):
        fake = FakeKeyAndAPKVerifier(password_valid=False)
        with self.assertRaisesRegex(
            PrivateSignerPreflightBlocked,
            "EXISTING_KEYSTORE_PASSWORD_OR_FORMAT_REJECTED",
        ):
            self.check(fake)
        self.assertEqual(len(fake.requests), 1)

    def test_wrong_supplied_alias_auto_resolves_only_cert_matching_private_key(self):
        fake = FakeKeyAndAPKVerifier()
        private_path = self.base / "temporary-alias.txt"
        status = self.check(
            fake, alias="252525", resolved_alias_file=private_path,
        )
        self.assertEqual(
            status, "PASS_EXISTING_RESEARCH_SIGNING_CERT_MATCH_ALIAS_AUTO_RESOLVED"
        )
        self.assertEqual(private_path.read_text(encoding="utf-8"), "synthetic\n")
        self.assertNotIn("synthetic", status)
        self.assertEqual(len(fake.requests), 3)
        # No pre-existing file overwritten; caller deletes this private file.
        with self.assertRaisesRegex(
            PrivateSignerPreflightBlocked, "PRIVATE_RESOLVED_ALIAS_FILE_UNSAFE"
        ):
            self.check(fake, alias="252525", resolved_alias_file=private_path)

    def test_multiple_private_keys_only_matching_research_certificate_is_chosen(self):
        fake = FakeKeyAndAPKVerifier(aliases=("synthetic", "wrongcandidate"))
        private_path = self.base / "temp-match.txt"
        self.assertEqual(
            self.check(fake, alias="wrongcandidate",
                       resolved_alias_file=private_path),
            "PASS_EXISTING_RESEARCH_SIGNING_CERT_MATCH_ALIAS_AUTO_RESOLVED",
        )
        self.assertEqual(private_path.read_text(), "synthetic\n")
        self.assertEqual(len(fake.requests), 4)

    def test_ambiguous_matching_certificates_fail_without_alias_file(self):
        fake = FakeKeyAndAPKVerifier(
            aliases=("synthetic", "duplicate"), duplicate_matching=True,
        )
        target = self.base / "ambiguous.txt"
        with self.assertRaisesRegex(
            PrivateSignerPreflightBlocked,
            "EXISTING_RESEARCH_SIGNING_CERTIFICATE_NO_UNIQUE_PRIVATE_KEY_MATCH",
        ):
            self.check(fake, resolved_alias_file=target)
        self.assertFalse(target.exists())

    def test_different_research_signed_base_certificate_aborts(self):
        fake = FakeKeyAndAPKVerifier(certificate_matches=False)
        with self.assertRaisesRegex(
            PrivateSignerPreflightBlocked,
            "EXISTING_RESEARCH_SIGNING_CERTIFICATE_NO_UNIQUE_PRIVATE_KEY_MATCH",
        ):
            self.check(fake)
        self.assertEqual(len(fake.requests), 3)

    def test_keystore_without_privatekeyentry_rejected(self):
        self.assertRaises(
            PrivateSignerPreflightBlocked, _private_key_aliases,
            "Alias name: readonly\nEntry type: trustedCertEntry\n",
        )
        self.assertRaises(
            PrivateSignerPreflightBlocked, _private_key_aliases,
            "Alias name: unsafe/path\nEntry type: PrivateKeyEntry\n",
        )
        self.assertRaises(
            PrivateSignerPreflightBlocked, _private_key_aliases,
            "Alias name: same\nEntry type: PrivateKeyEntry\n"
            "Alias name: same\nEntry type: PrivateKeyEntry\n",
        )

    def test_secret_env_missing_blocks_without_tool_call(self):
        fake = FakeKeyAndAPKVerifier()
        with patch.dict(os.environ, {"SYNTHETIC_PRIVATE_PASSWORD": ""}):
            with self.assertRaisesRegex(
                PrivateSignerPreflightBlocked, "PRIVATE_PASSWORD_ENV_NOT_SET",
            ):
                verify_before_sign(**self.kwargs, runner=fake)
        self.assertFalse(fake.requests)

    def test_private_alias_handoff_must_stay_beside_research_keystore(self):
        fake = FakeKeyAndAPKVerifier()
        with tempfile.TemporaryDirectory() as other:
            with self.assertRaisesRegex(
                PrivateSignerPreflightBlocked,
                "PRIVATE_RESOLVED_ALIAS_OUTSIDE_KEY_DIRECTORY",
            ):
                self.check(fake, resolved_alias_file=Path(other) / "alias.txt")

    def test_secret_alias_path_does_not_escape_failure_classifiers(self):
        raw = (
            'Failed to load signer: no key with alias EXTRA_PRIVATE_ALIAS '
            'at C:\\Users\\PRIVATE\\research.p12'
        )
        result = _classify_signer_failure(raw)
        self.assertEqual(result, "EXISTING_RESEARCH_KEY_ALIAS_NOT_FOUND")
        for secret in ("EXTRA_PRIVATE_ALIAS", "PRIVATE", ".p12"):
            self.assertNotIn(secret, result)
        self.assertEqual(
            _classify_signer_failure(
                "java.security.UnrecoverableKeyException: failed to load private key"),
            "EXISTING_RESEARCH_PRIVATE_KEY_PASSWORD_OR_ENTRY_REJECTED",
        )


if __name__ == "__main__":
    unittest.main()
