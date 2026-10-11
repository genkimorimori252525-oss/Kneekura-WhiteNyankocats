"""Pre-sign read-only PKCS#12 keystore/certificate check for isolated original game.

Only the owner-local EXISTING research keystore and previously signed
isolated JP15.7.1 base.apk are read. The password comes from a process-only
environment variable name, never argv, stdout, traceback, GitHub or a file.
No signing, password guessing, app/device/SAVE mutation or alias disclosure.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import subprocess

from tools.base_mod.preflight_original_device_update import _cert


class PrivateSignerPreflightBlocked(ValueError):
    """Fixed and nonsensitive failure classification."""


def _private_file(source: Path, label: str) -> Path:
    if source.is_symlink() or not source.is_file():
        raise PrivateSignerPreflightBlocked(label + "_MISSING_OR_UNSAFE")
    return source.resolve(strict=True)


def _run(command: list[str], runner, *, binary: bool = False):
    try:
        result = runner(
            command, check=False, capture_output=True,
            timeout=45, **({} if binary else {"text": True, "errors": "replace"}),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PrivateSignerPreflightBlocked(
            "LOCAL_SIGNER_TOOL_UNAVAILABLE_OR_TIMED_OUT"
        ) from None
    if not isinstance(result.returncode, int):
        raise PrivateSignerPreflightBlocked("LOCAL_SIGNER_TOOL_RESULT_INVALID")
    return result


def verify_before_sign(
    *, keystore: Path, alias: str, storepass_env: str,
    previously_signed_base: Path, keytool: Path, apksigner: Path,
    runner=subprocess.run,
) -> str:
    """Return fixed success text, or raise a fixed nonsensitive reason.

    Keytool -exportcert uses binary DER stdout; its certificate SHA256 must
    match apksigner's *already* signed isolated research base.apk fingerprint.
    This ensures a valid password and exact existing owner signing identity
    before the expensive native-research six-split rebuild.
    """
    if not re.fullmatch(r"[a-zA-Z0-9._-]{1,80}", alias or ""):
        raise PrivateSignerPreflightBlocked("INVALID_EXISTING_KEY_ALIAS_FORMAT")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", storepass_env or ""):
        raise PrivateSignerPreflightBlocked("INVALID_PRIVATE_PASSWORD_ENV_NAME")
    if not os.environ.get(storepass_env):
        raise PrivateSignerPreflightBlocked("PRIVATE_PASSWORD_ENV_NOT_SET")
    ks = _private_file(keystore, "OWNER_RESEARCH_KEYSTORE")
    original = _private_file(previously_signed_base, "PREVIOUS_RESEARCH_APK")
    keytool = _private_file(keytool, "JDK_KEYTOOL")
    apksigner = _private_file(apksigner, "ANDROID_APKSIGNER")

    # Storepass contents never enter the argv: JDK 17 keytool supports
    # -storepass:env VAR. Never report Java's raw diagnostics or aliases.
    base = [
        str(keytool), "-keystore", str(ks), "-storetype", "PKCS12",
        "-storepass:env", storepass_env,
    ]
    listed = _run([base[0], "-list", *base[1:]], runner)
    if listed.returncode != 0:
        raise PrivateSignerPreflightBlocked(
            "EXISTING_KEYSTORE_PASSWORD_OR_FORMAT_REJECTED"
        )
    cert = _run(
        [base[0], "-exportcert", "-alias", alias, *base[1:]],
        runner, binary=True,
    )
    if cert.returncode != 0:
        raise PrivateSignerPreflightBlocked(
            "EXISTING_RESEARCH_KEY_ALIAS_NOT_FOUND_OR_NO_CERTIFICATE"
        )
    der = cert.stdout
    if (not isinstance(der, bytes) or not 256 <= len(der) <= 64_000
        or der[0] != 0x30):
        raise PrivateSignerPreflightBlocked(
            "EXISTING_RESEARCH_CERTIFICATE_EXPORT_INVALID"
        )
    previous = _run(
        [str(apksigner), "verify", "--print-certs", str(original)], runner,
    )
    if previous.returncode != 0:
        raise PrivateSignerPreflightBlocked(
            "PREVIOUS_RESEARCH_APK_CERTIFICATE_VERIFICATION_FAILED"
        )
    try:
        before = _cert(previous.stdout)
    except ValueError:
        raise PrivateSignerPreflightBlocked(
            "PREVIOUS_RESEARCH_APK_CERTIFICATE_AMBIGUOUS"
        ) from None
    if hashlib.sha256(der).hexdigest() != before:
        raise PrivateSignerPreflightBlocked(
            "EXISTING_RESEARCH_SIGNING_CERTIFICATE_DIFFERS_FROM_INSTALLED_BASELINE"
        )
    return "PASS_EXISTING_RESEARCH_KEYSTORE_ALIAS_PASSWORD_AND_CERT_MATCH"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keystore", type=Path, required=True)
    parser.add_argument("--alias", required=True)
    parser.add_argument("--storepass-env", required=True)
    parser.add_argument("--previous-signed-base", required=True, type=Path)
    parser.add_argument("--keytool", required=True, type=Path)
    parser.add_argument("--apksigner", required=True, type=Path)
    args = parser.parse_args()
    try:
        status = verify_before_sign(
            keystore=args.keystore, alias=args.alias,
            storepass_env=args.storepass_env,
            previously_signed_base=args.previous_signed_base,
            keytool=args.keytool, apksigner=args.apksigner,
        )
    except PrivateSignerPreflightBlocked as exc:
        parser.error(str(exc))
    print(status)
    print("Owner-private key and APK were READ ONLY; no secrets printed or stored.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
