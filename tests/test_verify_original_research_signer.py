"""Synthetic private-keystore error diagnostics; never use owner signing keys."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.base_mod.verify_original_research_signer import (
    verify_before_sign, PrivateSignerPreflightBlocked,
)
from tools.base_mod.repack import _classify_signer_failure


class FakeKeyAndAPKVerifier:
    def __init__(self, *, password_valid=True, alias_present=True,
                 certificate_matches=True):
        self.password_valid = password_valid
        self.alias_present = alias_present
        self.certificate_matches = certificate_matches
        self.der = b"\x30" + b"synthetic-DER-not-an-owner-cert" * 14
        self.requests: list[list[str]] = []

    def __call__(self, argv, **options):
        self.requests.append(argv)
        if "-list" in argv:
            return subprocess.CompletedProcess(
                argv, 0 if self.password_valid else 1,
                "SYNTHETIC_ALIAS_NOT_SHARED" if self.password_valid else "",
                "BAD_PASSWORD" if not self.password_valid else "",
            )
        if "-exportcert" in argv:
            return subprocess.CompletedProcess(
                argv, 0 if self.alias_present else 1,
                self.der if self.alias_present else b"",
                b"wrong alias" if not self.alias_present else b"",
            )
        if "verify" in argv:
            fingerprint = (hashlib.sha256(self.der).hexdigest()
                           if self.certificate_matches else "f" * 64)
            return subprocess.CompletedProcess(
                argv, 0,
                "Signer #1 certificate SHA-256 digest: " + fingerprint,
                "",
            )
        raise AssertionError("unknown tool command")


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

    def check(self, fake):
        with patch.dict(os.environ, {
            "SYNTHETIC_PRIVATE_PASSWORD": "DO_NOT_PRINT_SYNTHETIC_SECRET",
        }):
            return verify_before_sign(**self.kwargs, runner=fake)

    def test_valid_existing_key_alias_password_and_cert_return_only_fixed_marker(self):
        fake = FakeKeyAndAPKVerifier()
        status = self.check(fake)
        self.assertEqual(
            status, "PASS_EXISTING_RESEARCH_KEYSTORE_ALIAS_PASSWORD_AND_CERT_MATCH")
        self.assertEqual(len(fake.requests), 3)
        self.assertTrue(any("-storepass:env" in x for x in fake.requests))
        for request in fake.requests:
            self.assertNotIn("DO_NOT_PRINT_SYNTHETIC_SECRET", str(request))
            self.assertNotIn("pass:", " ".join(request))

    def test_wrong_storepass_stops_before_touching_old_signed_cert(self):
        fake = FakeKeyAndAPKVerifier(password_valid=False)
        with self.assertRaisesRegex(
            PrivateSignerPreflightBlocked,
            "EXISTING_KEYSTORE_PASSWORD_OR_FORMAT_REJECTED",
        ):
            self.check(fake)
        self.assertEqual(len(fake.requests), 1)

    def test_wrong_alias_stops_after_valid_storepass(self):
        fake = FakeKeyAndAPKVerifier(alias_present=False)
        with self.assertRaisesRegex(
            PrivateSignerPreflightBlocked,
            "EXISTING_RESEARCH_KEY_ALIAS_NOT_FOUND_OR_NO_CERTIFICATE",
        ):
            self.check(fake)
        self.assertEqual(len(fake.requests), 2)

    def test_key_different_from_existing_signed_research_base_aborts(self):
        fake = FakeKeyAndAPKVerifier(certificate_matches=False)
        with self.assertRaisesRegex(
            PrivateSignerPreflightBlocked,
            "EXISTING_RESEARCH_SIGNING_CERTIFICATE_DIFFERS",
        ):
            self.check(fake)
        self.assertEqual(len(fake.requests), 3)

    def test_password_env_missing_blocks_without_tool_call(self):
        fake = FakeKeyAndAPKVerifier()
        with patch.dict(os.environ, {"SYNTHETIC_PRIVATE_PASSWORD": ""}):
            with self.assertRaisesRegex(
                PrivateSignerPreflightBlocked, "PRIVATE_PASSWORD_ENV_NOT_SET",
            ):
                verify_before_sign(**self.kwargs, runner=fake)
        self.assertFalse(fake.requests)

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
        self.assertEqual(
            _classify_signer_failure("something_else_with_PRIVATE_DETAILS"),
            "RESEARCH_APKSIGNER_FAILED_WITH_UNCLASSIFIED_TOOL_ERROR",
        )


if __name__ == "__main__":
    unittest.main()
