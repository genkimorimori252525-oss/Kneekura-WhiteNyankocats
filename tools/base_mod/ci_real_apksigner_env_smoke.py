"""Public synthetic Android 35 APK signing smoke with REAL apksigner.

No user APK, SAVE, key or device. The only keystore is ephemeral and CI-only.
Exercise baseline_resign with actual aapt2/zipalign/apksigner and ensure
owner-style passwords never occur in argv, errors, or generated ledgers.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from unittest import mock
from zipfile import ZipFile, ZIP_DEFLATED

from tools.base_mod import repack


SYNTHETIC_SECRET = "CI_ONLY_THROWAWAY_TEST_SECRET_2026"
SYNTHETIC_PACKAGE = "jp.kn.synthetic.signercheck"


def _tool(root: Path, basename: str) -> str:
    suffix = ".exe" if os.name == "nt" and basename in ("aapt2", "zipalign") else (
        ".bat" if os.name == "nt" and basename == "apksigner" else ""
    )
    candidate = root / (basename + suffix)
    if not candidate.is_file():
        raise AssertionError("required public Android build tool missing: " + basename)
    return str(candidate)


def _invoke(args: list[str], *, timeout=90) -> None:
    completed = subprocess.run(
        args, capture_output=True, check=False, text=True,
        errors="replace", timeout=timeout,
    )
    if completed.returncode:
        # Only public/synthetic APK input, never user secrets.
        raise AssertionError(
            "public Android SDK tool failed: " + Path(args[0]).name +
            " with status " + str(completed.returncode) +
            "; sanitized stderr length " + str(len(completed.stderr))
        )


def _run_smoke(sdk: Path, *, output: Path | None = None) -> dict:
    tools = sdk / "build-tools" / "35.0.0"
    aapt = _tool(tools, "aapt2")
    zipalign = _tool(tools, "zipalign")
    apksigner = _tool(tools, "apksigner")
    android_jar = sdk / "platforms" / "android-35" / "android.jar"
    if not android_jar.is_file():
        raise AssertionError("public Android API 35 android.jar unavailable")
    keytool = shutil.which("keytool") or shutil.which("keytool.exe")
    if keytool is None and os.name == "nt":
        # Owner Windows 11 often has Android Studio JBR but not keytool on
        # PATH. Run the *public synthetic* signer smoke using the existing
        # Android Studio JDK; never probe a research keystore/password.
        roots = [
            Path(os.environ["JAVA_HOME"]) if os.environ.get("JAVA_HOME") else None,
            (Path(os.environ.get("PROGRAMFILES", r"C:\\Program Files"))
             / "Android" / "Android Studio" / "jbr"),
        ]
        javac = shutil.which("javac.exe")
        if javac:
            roots.insert(0, Path(javac).resolve().parent.parent)
        for root in roots:
            if root is None:
                continue
            candidate = root / "bin" / "keytool.exe"
            if candidate.is_file():
                keytool = str(candidate)
                break
    if keytool is None:
        raise AssertionError("public synthetic Java JDK keytool unavailable")

    with tempfile.TemporaryDirectory(prefix="kn-real-apksigner-env-test-") as temp:
        root = Path(temp)
        manifest = root / "AndroidManifest.xml"
        manifest.write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<manifest xmlns:android="http://schemas.android.com/apk/res/android" '
            'package="' + SYNTHETIC_PACKAGE + '" '
            'android:versionCode="1" android:versionName="1.0">'
            '<uses-sdk android:minSdkVersion="23" android:targetSdkVersion="28"/>'
            '<application android:hasCode="false" android:label="Synthetic signing only"/>'
            '</manifest>\n',
            encoding="utf-8",
        )
        packed = root / "aapt2-output.apk"
        _invoke([aapt, "link", "--manifest", str(manifest),
                 "-I", str(android_jar), "-o", str(packed)])
        with ZipFile(packed) as archive:
            if not archive.read("AndroidManifest.xml").startswith(b"\x03\x00\x08\x00"):
                raise AssertionError("synthetic Android binary manifest missing")

        splits = root / "synthetic-six-inputs"
        signed = root / "synthetic-six-signed"
        splits.mkdir()
        for i, filename in enumerate(repack.JP_15_7_1_SPLITS):
            target = splits / filename
            shutil.copyfile(packed, target)
            with ZipFile(target, "a", compression=ZIP_DEFLATED) as archive:
                archive.writestr("assets/synthetic-ci-only.txt", f"NO_GAME_DATA_SPLIT_{i}")
        key = root / "THROWAWAY_CI_SIGNING_ONLY.p12"
        _invoke([keytool, "-genkeypair", "-storetype", "PKCS12",
                 "-keystore", str(key), "-alias", "synthetic",
                 "-storepass", SYNTHETIC_SECRET, "-keypass", SYNTHETIC_SECRET,
                 "-keyalg", "RSA", "-keysize", "2048", "-validity", "1",
                 "-dname", "CN=Public Test,OU=CI,O=Synthetic Only,C=JP"])
        recorded = []
        original = repack._run

        def check_argv(args, *, environment=None):
            serialized = " ".join(args)
            if SYNTHETIC_SECRET in serialized or "pass:" in serialized:
                raise AssertionError("signing password leaked to argv")
            if "sign" in args and "--ks-pass" in args:
                for flag in ("--ks-pass", "--key-pass"):
                    index = args.index(flag)
                    value = args[index + 1]
                    if not value.startswith("env:"):
                        raise AssertionError("signing password not sourced from environment")
                    if environment is None or environment.get(value[4:]) != SYNTHETIC_SECRET:
                        raise AssertionError("missing process-only test signing environment")
                recorded.append(True)
            return original(args, environment=environment)

        with mock.patch.object(repack, "_run", side_effect=check_argv):
            ledger = repack.baseline_resign(
                splits, signed, keystore=key, alias="synthetic",
                storepass=SYNTHETIC_SECRET, keypass=SYNTHETIC_SECRET,
                zipalign=zipalign, apksigner=apksigner,
                source_export_sha256="synthetic-do-not-mistake-for-owner",
            )
        if len(recorded) != 6 or not ledger["content_invariant"]:
            raise AssertionError("six real Android sign operations were not fully validated")
        # Exercise the real JDK17 keytool -storepass:env and APK verifier
        # with a TEST-ONLY ephemeral key. The real owner password never
        # appears in process argv or public build artifacts.
        from tools.base_mod.verify_original_research_signer import (
            verify_before_sign, PrivateSignerPreflightBlocked,
        )
        env_name = "KNEEKURA_PUBLIC_SYNTHETIC_KEY_PRECHECK"
        with mock.patch.dict(os.environ, {env_name: SYNTHETIC_SECRET}):
            signer_preflight = verify_before_sign(
                keystore=key, alias="synthetic", storepass_env=env_name,
                previously_signed_base=signed / "base.apk",
                keytool=Path(keytool), apksigner=Path(apksigner),
            )
            if signer_preflight != "PASS_EXISTING_RESEARCH_KEYSTORE_ALIAS_PASSWORD_AND_CERT_MATCH":
                raise AssertionError("real JDK synthetic signer preflight failed")
            # Wrong hint must discover the ONE real certificate-matching
            # private key, without showing its alias or any password.
            handoff = root / "synthetic-resolved-key-alias.txt"
            recovered = verify_before_sign(
                keystore=key, alias="missing_alias", storepass_env=env_name,
                previously_signed_base=signed / "base.apk",
                keytool=Path(keytool), apksigner=Path(apksigner),
                resolved_alias_file=handoff,
            )
            if recovered != "PASS_EXISTING_RESEARCH_SIGNING_CERT_MATCH_ALIAS_AUTO_RESOLVED":
                raise AssertionError("real JDK synthetic alias auto-discovery failed")
            if handoff.read_text(encoding="utf-8").strip() != "synthetic":
                raise AssertionError("resolved private alias did not match known synthetic key")
            handoff.unlink()
            # Even with a valid password, a certificate for a DIFFERENT
            # existing signer may never be silently selected.
            other_key = root / "separate-synthetic-key.p12"
            _invoke([keytool, "-genkeypair", "-storetype", "PKCS12",
                     "-keystore", str(other_key), "-alias", "other_key",
                     "-storepass", SYNTHETIC_SECRET, "-keypass", SYNTHETIC_SECRET,
                     "-keyalg", "RSA", "-keysize", "2048", "-validity", "1",
                     "-dname", "CN=Other Synthetic Key,OU=CI,O=No Original Game,C=JP"])
            try:
                verify_before_sign(
                    keystore=other_key, alias="other_key", storepass_env=env_name,
                    previously_signed_base=signed / "base.apk",
                    keytool=Path(keytool), apksigner=Path(apksigner),
                )
            except PrivateSignerPreflightBlocked as exc:
                if str(exc) != "EXISTING_RESEARCH_SIGNING_CERTIFICATE_NO_UNIQUE_PRIVATE_KEY_MATCH":
                    raise AssertionError("mismatched synthetic signer identity not blocked")
            else:
                raise AssertionError("wrong synthetic certificate was accepted")
        if len(ledger["splits"]) != 6:
            raise AssertionError("not six synthetic APKs")
        if SYNTHETIC_SECRET in (signed / "patch-ledger.json").read_text():
            raise AssertionError("secret leaked to synthetic signing ledger")
        if len(ledger["signer_certificate_sha256"]) != 64:
            raise AssertionError("apksigner did not produce a valid SHA256 certificate")
        for apk in repack.JP_15_7_1_SPLITS:
            with ZipFile(signed / apk) as archive:
                if "assets/synthetic-ci-only.txt" not in archive.namelist():
                    raise AssertionError("signed synthetic APK payload missing")

        report = {
            "schema": "kneekura-public-real-apksigner-env-only-v1",
            "real_android_sdk_tools_executed": True,
            "real_keytool_ephemeral_synthetic_only": True,
            "real_synthetic_apk_signatures_verified": 6,
            "real_keytool_existing_alias_certificate_preflight_verified": True,
            "wrong_alias_auto_resolved_only_by_cert": True,
            "different_signing_certificate_blocked": True,
            "signing_password_only_in_environment_not_argv": True,
            "all_six_signed_apk_payloads_preserved": True,
            "synthetic_keystore_removed_after_process": True,
            "owner_original_game_apk_or_SAVE_accessed": False,
            "device_or_publisher_account_touched": False,
            "genuine_original_game_first_boot_verified": False,
        }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    return report


def main() -> int:
    sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if not sdk:
        raise SystemExit("Android SDK root not configured on public CI")
    report = _run_smoke(Path(sdk), output=Path(
        ".agent-validation/reports/public-real-apksigner-environment-only.json"))
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
