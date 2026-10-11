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



def _private_key_aliases(verbose_listing: str) -> list[str]:
    """Parse JDK17 English keytool -list -v metadata, never expose its text.

    List only actual private-key entries, not trusted certificate entries.
    Enforce a small bounded distinct alias set and safe ASCII spelling.
    """
    if not isinstance(verbose_listing, str) or len(verbose_listing) > 200_000:
        raise PrivateSignerPreflightBlocked("EXISTING_KEYSTORE_ALIAS_LIST_UNAVAILABLE")
    found = []
    alias: str | None = None
    is_private = False

    def finish() -> None:
        if alias is not None and is_private:
            found.append(alias)

    for line in verbose_listing.splitlines():
        name = re.fullmatch(r"Alias name:\s*(.+)", line.strip())
        if name:
            finish()
            alias = name.group(1).strip()
            is_private = False
        elif alias is not None and line.strip() == "Entry type: PrivateKeyEntry":
            is_private = True
    finish()
    if not found or len(found) > 16 or len(set(found)) != len(found) or any(
        re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", candidate) is None
        for candidate in found
    ):
        raise PrivateSignerPreflightBlocked(
            "EXISTING_KEYSTORE_PRIVATE_KEY_ALIAS_LIST_UNAVAILABLE_OR_UNSAFE"
        )
    return found


def _write_private_alias(path: Path, keystore: Path, selected: str) -> None:
    """Ephemeral owner-private alias for the parent signer, exclusive creation.

    This alias is NOT a password or private key, but is still private
    metadata. Never put its actual value in stdout, Git, or receipts.
    The PowerShell wrapper removes it in the same process finally block.
    """
    if path.is_symlink() or path.exists() or path.parent.is_symlink():
        raise PrivateSignerPreflightBlocked("PRIVATE_RESOLVED_ALIAS_FILE_UNSAFE")
    if path.parent.resolve() != keystore.parent.resolve():
        raise PrivateSignerPreflightBlocked("PRIVATE_RESOLVED_ALIAS_OUTSIDE_KEY_DIRECTORY")
    try:
        descriptor = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as f:
            f.write(selected + "\n")
    except OSError:
        raise PrivateSignerPreflightBlocked("PRIVATE_RESOLVED_ALIAS_WRITE_BLOCKED") from None


def verify_before_sign(
    *, keystore: Path, alias: str, storepass_env: str,
    previously_signed_base: Path, keytool: Path, apksigner: Path,
    runner=subprocess.run, resolved_alias_file: Path | None = None,
) -> str:
    """Find exactly ONE key whose public cert matches prior research APK.

    The user's supplied alias is only a hint. The former alias '252525'
    was not a valid key entry on the owner system. Fail closed unless one
    PrivateKeyEntry matches the *already-signed isolated research APK*.
    Do not print any discovered private alias or read the private key.
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

    # Pin English *keytool output labels*, even on Japanese Windows.
    # The storepass is a variable NAME only, never pass:<secret> argv.
    base = [
        str(keytool), "-keystore", str(ks), "-storetype", "PKCS12",
        "-storepass:env", storepass_env,
    ]
    listed = _run([base[0], "-J-Duser.language=en", "-J-Duser.country=US",
                   "-list", "-v", *base[1:]], runner)
    if listed.returncode != 0:
        raise PrivateSignerPreflightBlocked(
            "EXISTING_KEYSTORE_PASSWORD_OR_FORMAT_REJECTED"
        )
    candidates = _private_key_aliases(listed.stdout)
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

    matches = []
    for entry in candidates:
        cert = _run(
            [base[0], "-exportcert", "-alias", entry, *base[1:]],
            runner, binary=True,
        )
        der = cert.stdout
        if (cert.returncode != 0 or not isinstance(der, bytes)
            or not 256 <= len(der) <= 64_000 or der[0] != 0x30):
            raise PrivateSignerPreflightBlocked(
                "EXISTING_KEYSTORE_PRIVATE_KEY_CERTIFICATE_EXPORT_FAILED"
            )
        if hashlib.sha256(der).hexdigest() == before:
            matches.append(entry)
    if len(matches) != 1:
        raise PrivateSignerPreflightBlocked(
            "EXISTING_RESEARCH_SIGNING_CERTIFICATE_NO_UNIQUE_PRIVATE_KEY_MATCH"
        )
    selected = matches[0]
    if resolved_alias_file is not None:
        _write_private_alias(resolved_alias_file, ks, selected)
    return (
        "PASS_EXISTING_RESEARCH_KEYSTORE_ALIAS_PASSWORD_AND_CERT_MATCH"
        if selected.casefold() == alias.casefold()
        else "PASS_EXISTING_RESEARCH_SIGNING_CERT_MATCH_ALIAS_AUTO_RESOLVED"
    )

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keystore", type=Path, required=True)
    parser.add_argument("--alias", required=True)
    parser.add_argument("--storepass-env", required=True)
    parser.add_argument("--previous-signed-base", required=True, type=Path)
    parser.add_argument("--keytool", required=True, type=Path)
    parser.add_argument("--apksigner", required=True, type=Path)
    parser.add_argument("--resolved-alias-file", type=Path,
                        help="owner-private exclusive temporary handoff; alias never printed")
    args = parser.parse_args()
    try:
        status = verify_before_sign(
            keystore=args.keystore, alias=args.alias,
            storepass_env=args.storepass_env,
            previously_signed_base=args.previous_signed_base,
            keytool=args.keytool, apksigner=args.apksigner,
            resolved_alias_file=args.resolved_alias_file,
        )
    except PrivateSignerPreflightBlocked as exc:
        parser.error(str(exc))
    print(status)
    print("Owner-private key and APK were READ ONLY; no secrets printed or stored.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
