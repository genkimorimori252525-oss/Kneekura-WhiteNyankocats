"""Baseline split-APK repack/sign pipeline with content-invariance checks.

This tool deliberately does *not* patch Battle Cats data or scenes.  It prepares a
re-signed split set and records a machine-readable ledger proving that non-signature
ZIP payloads are byte-identical before and after the baseline pipeline.

The real Android signing tools are external inputs; no private signing key belongs
in this repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import uuid
import zipfile


JP_15_7_1_SPLITS = (
    "base.apk",
    "split_config.arm64_v8a.apk",
    "split_config.en.apk",
    "split_config.ja.apk",
    "split_config.xxhdpi.apk",
    "split_InstallPack.apk",
)

_SIGNATURE_RE = re.compile(
    r"certificate SHA-256 digest:\s*([0-9a-fA-F:]+)", re.IGNORECASE
)

# These root ZIP entries are generated/consumed by Android's signing/layout
# machinery rather than by the game payload itself.  Modern apksigner removes
# an existing source-stamp hash when resigning with a different certificate,
# and may regenerate pinlist metadata from APK pin hints.
_SIGNING_METADATA_ENTRIES = {
    "stamp-cert-sha256",
    "pinlist.meta",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_signature_entry(name: str) -> bool:
    if name in _SIGNING_METADATA_ENTRIES:
        return True

    upper = name.upper()
    if not upper.startswith("META-INF/"):
        return False
    leaf = upper.rsplit("/", 1)[-1]
    return (
        leaf == "MANIFEST.MF"
        or leaf.endswith(".SF")
        or leaf.endswith(".RSA")
        or leaf.endswith(".DSA")
        or leaf.endswith(".EC")
    )


def payload_fingerprint(path: Path) -> str:
    """Hash game payload entries while ignoring Android signing/layout metadata."""

    digest = hashlib.sha256()
    with zipfile.ZipFile(path, "r") as archive:
        entries = [
            info
            for info in archive.infolist()
            if not info.is_dir() and not _is_signature_entry(info.filename)
        ]
        entries.sort(key=lambda item: (item.filename, item.header_offset))
        for info in entries:
            name = info.filename.encode("utf-8")
            payload = archive.read(info)
            digest.update(len(name).to_bytes(4, "little"))
            digest.update(name)
            digest.update(len(payload).to_bytes(8, "little"))
            digest.update(payload)
    return digest.hexdigest()


def find_android_tool(name: str, explicit: str | None = None) -> str:
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            raise FileNotFoundError(path)
        return str(path)

    found = shutil.which(name)
    if found:
        return found

    roots = [
        os.environ.get("ANDROID_HOME"),
        os.environ.get("ANDROID_SDK_ROOT"),
    ]
    candidates: list[Path] = []
    for root in roots:
        if not root:
            continue
        build_tools = Path(root) / "build-tools"
        if not build_tools.is_dir():
            continue
        for version in build_tools.iterdir():
            candidate = version / name
            if candidate.is_file():
                candidates.append(candidate)

    if not candidates:
        raise FileNotFoundError(
            f"{name!r} not found in PATH or Android SDK build-tools"
        )
    return str(sorted(candidates)[-1])


def _run(
    command: list[str], *, environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Launch child tools without recording secrets in the argv/exception."""
    return subprocess.run(
        command,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=environment,
    )


def _classify_signer_failure(raw_tool_output: str | None) -> str:
    """Map raw (possibly identifying) Java/apksigner errors to fixed codes.

    Never propagate the original exception, tool stdout/stderr, alias,
    keystore path, password or certificate fingerprint into public receipts
    or the owner's shareable console transcript.
    """
    message = (raw_tool_output or "").lower()
    if ("alias" in message or "key entry" in message) and (
        "does not exist" in message or "not found" in message
        or "not contain" in message or "no key" in message
    ):
        return "EXISTING_RESEARCH_KEY_ALIAS_NOT_FOUND"
    if "password" in message and (
        "keystore" in message or "store" in message
    ) and any(token in message for token in (
        "incorrect", "invalid", "failed", "wrong", "tampered",
    )):
        return "EXISTING_RESEARCH_KEYSTORE_PASSWORD_REJECTED"
    if any(token in message for token in (
        "unrecoverablekeyexception", "cannot recover key",
        "failed to load private key", "key password was incorrect",
    )):
        return "EXISTING_RESEARCH_PRIVATE_KEY_PASSWORD_OR_ENTRY_REJECTED"
    if "keystore" in message and (
        "not found" in message or "no such file" in message
        or "could not find" in message
    ):
        return "EXISTING_RESEARCH_KEYSTORE_FILE_NOT_FOUND"
    return "RESEARCH_APKSIGNER_FAILED_WITH_UNCLASSIFIED_TOOL_ERROR"


def _cert_digest(apksigner: str, apk: Path) -> str:
    result = _run([apksigner, "verify", "--verbose", "--print-certs", str(apk)])
    match = _SIGNATURE_RE.search(result.stdout)
    if not match:
        raise RuntimeError(
            f"apksigner did not report a certificate SHA-256 digest for {apk.name}"
        )
    return match.group(1).replace(":", "").lower()


def _required_splits(split_dir: Path) -> list[Path]:
    missing = [name for name in JP_15_7_1_SPLITS if not (split_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(
            "incomplete JP 15.7.1 split set; missing: " + ", ".join(missing)
        )
    return [split_dir / name for name in JP_15_7_1_SPLITS]


def baseline_resign(
    split_dir: Path,
    output_dir: Path,
    *,
    keystore: Path,
    alias: str,
    storepass: str,
    keypass: str | None = None,
    zipalign: str | None = None,
    apksigner: str | None = None,
    source_export_sha256: str | None = None,
) -> dict:
    """Re-align and re-sign an otherwise unchanged exact split set."""

    split_dir = split_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    sources = _required_splits(split_dir)

    keystore = keystore.resolve()
    if not keystore.is_file():
        raise FileNotFoundError(keystore)

    zipalign_bin = find_android_tool("zipalign", zipalign)
    apksigner_bin = find_android_tool("apksigner", apksigner)

    ledger_splits: list[dict] = []
    signer_digests: set[str] = set()

    # The Android SDK apksigner officially supports --ks-pass env:<VAR>.
    # Putting pass:<secret> in argv exposes the owner's key password in OS
    # process listings and Python CalledProcessError.cmd. Use private,
    # per-run child environment values instead. No password goes to Git/JSON.
    if not isinstance(storepass, str) or not storepass:
        raise ValueError("nonempty private signing password required")
    if keypass is not None and (not isinstance(keypass, str) or not keypass):
        raise ValueError("nonempty private signing key password required")
    env_store_name = "KNEEKURA_APKSIGN_STORE_" + uuid.uuid4().hex.upper()
    env_key_name = "KNEEKURA_APKSIGN_KEY_" + uuid.uuid4().hex.upper()
    signer_env = os.environ.copy()
    signer_env[env_store_name] = storepass
    if keypass is not None:
        signer_env[env_key_name] = keypass

    with tempfile.TemporaryDirectory(prefix="kneekura-baseline-") as temp_name:
        temp = Path(temp_name)
        for source in sources:
            aligned = temp / f"{source.stem}.aligned.apk"
            target = output_dir / source.name

            before_payload = payload_fingerprint(source)

            _run([zipalign_bin, "-p", "-f", "4", str(source), str(aligned)])

            sign_command = [
                apksigner_bin,
                "sign",
                "--ks",
                str(keystore),
                "--ks-key-alias",
                alias,
                "--ks-pass",
                f"env:{env_store_name}",
                "--v1-signing-enabled",
                "true",
                "--v2-signing-enabled",
                "true",
                "--v3-signing-enabled",
                "true",
                "--out",
                str(target),
            ]
            if keypass is not None:
                sign_command.extend(["--key-pass", f"env:{env_key_name}"])
            sign_command.append(str(aligned))
            try:
                _run(sign_command, environment=signer_env)
            except subprocess.CalledProcessError as exc:
                # CalledProcessError contains owner file paths and alias.
                # Never let its original __str__ escape into the console.
                failure = _classify_signer_failure(exc.stdout)
                raise RuntimeError(
                    "RESEARCH_SIGNING_BLOCKED: " + failure
                    + " (existing signer not changed; no device action)"
                ) from None

            _run([apksigner_bin, "verify", "--verbose", str(target)])
            signer = _cert_digest(apksigner_bin, target)
            signer_digests.add(signer)

            after_payload = payload_fingerprint(target)
            if before_payload != after_payload:
                raise RuntimeError(
                    f"payload changed during baseline pipeline for {source.name}: "
                    f"{before_payload} != {after_payload}"
                )

            ledger_splits.append(
                {
                    "name": source.name,
                    "input_size": source.stat().st_size,
                    "input_sha256": sha256_file(source),
                    "output_size": target.stat().st_size,
                    "output_sha256": sha256_file(target),
                    "payload_sha256_before": before_payload,
                    "payload_sha256_after": after_payload,
                    "content_invariant": True,
                }
            )

    if len(signer_digests) != 1:
        raise RuntimeError(
            "split signer mismatch: " + ", ".join(sorted(signer_digests))
        )

    ledger = {
        "schema_version": 1,
        "anchor": "jp-15.7.1",
        "mode": "baseline-resign",
        "source_export_sha256": source_export_sha256,
        "required_splits": list(JP_15_7_1_SPLITS),
        "signer_certificate_sha256": next(iter(signer_digests)),
        "content_invariant": True,
        "splits": ledger_splits,
    }

    ledger_path = output_dir / "patch-ledger.json"
    ledger_path.write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return ledger


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Re-align/re-sign an unchanged JP 15.7.1 Battle Cats split set and "
            "emit a content-invariance patch ledger."
        )
    )
    parser.add_argument("split_dir", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--keystore", required=True, type=Path)
    parser.add_argument("--alias", required=True)
    parser.add_argument("--storepass", required=True)
    parser.add_argument("--keypass")
    parser.add_argument("--zipalign")
    parser.add_argument("--apksigner")
    parser.add_argument("--source-export-sha256")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    ledger = baseline_resign(
        args.split_dir,
        args.output,
        keystore=args.keystore,
        alias=args.alias,
        storepass=args.storepass,
        keypass=args.keypass,
        zipalign=args.zipalign,
        apksigner=args.apksigner,
        source_export_sha256=args.source_export_sha256,
    )
    print(json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())