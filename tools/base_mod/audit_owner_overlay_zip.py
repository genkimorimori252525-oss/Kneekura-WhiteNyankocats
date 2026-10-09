"""Fail-closed audit of the EXACT ZIP delivered for the familiar owner update.

This is a read-only audit, not an installer. It verifies the *nested*
PowerShell installer as well as the wrapper and its third-party-independent
Java resolver. Windows CI must separately parse and run -CheckJava in a JDK
environment. A source-level test of only the outer wrapper is insufficient.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZipFile, BadZipFile

PREFIX = "tools/base_mod/"
NESTED = PREFIX + "independent_alpha_20261009/"
WRAPPER = PREFIX + "run_independent_alpha_update.ps1"
INSTALLER = NESTED + "INSTALL-ALPHA.ps1"
HELPER = PREFIX + "resolve_java_keytool.ps1"
APK = NESTED + "independent-alpha.apk"
INSTALL_MANIFEST = NESTED + "INSTALL-MANIFEST.json"
OVERLAY_MANIFEST = NESTED + "OVERLAY-MANIFEST.json"
REQUIRED = {WRAPPER, INSTALLER, HELPER, APK, INSTALL_MANIFEST, OVERLAY_MANIFEST}
BOM = bytes((0xEF, 0xBB, 0xBF))
HEX = re.compile(r"^[0-9a-f]{64}$")


class UnsafeRelease(ValueError):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def audit(path: Path) -> dict:
    with ZipFile(path) as zipfile:
        names = zipfile.namelist()
        if len(names) != len(set(names)) or any(
            name.startswith("/") or ".." in name.split("/") or
            "\\" in name or name.endswith("/") for name in names
        ):
            raise UnsafeRelease("unsafe/duplicate update ZIP entries")
        if not REQUIRED.issubset(names):
            raise UnsafeRelease("missing a required nested installer/helper/APK")
        if zipfile.testzip() is not None:
            raise UnsafeRelease("update ZIP CRC failed")
        if zipfile.getinfo(APK).file_size > 50 * 1024 * 1024:
            raise UnsafeRelease("unexpected APK file size")
        files = {name: zipfile.read(name) for name in names}
    for name in (WRAPPER, INSTALLER, HELPER):
        if not files[name].startswith(BOM):
            raise UnsafeRelease("Windows PowerShell 5.1 UTF8 BOM missing: " + name)
    outer = files[WRAPPER].decode("utf-8-sig")
    nested = files[INSTALLER].decode("utf-8-sig")
    helper = files[HELPER].decode("utf-8-sig")
    if ("[switch]$Apply" not in outer or
        "if (-not $Apply)" not in outer or
        "Resolve-JavaKeytool" not in nested or
        "-CheckJava" not in nested and "[switch]$CheckJava" not in nested or
        "function Resolve-JavaKeytool" not in helper):
        raise UnsafeRelease("missing one-command install or JDK runtime preflight")
    if "Join-Path $env:JAVA_HOME" in nested or "Join-Path $env:JAVA_HOME" in helper:
        raise UnsafeRelease("NULL JAVA_HOME regression is present")
    # Actual owner error 2026-10-09: PowerShell variable names are
    # case-insensitive; assigning $home collides with readonly $HOME.
    # This must be blocked in THE EXPORTED ZIP, not only repo helper source.
    reserved = ("home", "host", "pid", "pshome", "pwd", "profile")
    for label, ps_text in (("outer", outer), ("inner", nested), ("JDK helper", helper)):
        for name in reserved:
            if re.search(r"(?i)\\$" + name + r"\\b\\s*(?:=(?!=)|\\+=|-=)", ps_text):
                raise UnsafeRelease("PowerShell readonly reserved variable assignment in " + label + ": " + name)

    if any(s in nested.lower() for s in ("adb uninstall", "pm clear", "rm -rf")):
        raise UnsafeRelease("destructive command in signed installer")
    manifest = json.loads(files[INSTALL_MANIFEST])
    overlay = json.loads(files[OVERLAY_MANIFEST])
    if (manifest.get("app_id") != "jp.kneekura.whitenyankocats" or
        overlay.get("app_package") != manifest["app_id"]):
        raise UnsafeRelease("app identity mismatch")
    if overlay.get("privacy", {}).get("never_uninstalls_app") is not True:
        raise UnsafeRelease("no-uninstall safety contract missing")
    recorded = overlay.get("files", {})
    if not isinstance(recorded, dict) or not (REQUIRED - {OVERLAY_MANIFEST}).issubset(recorded):
        raise UnsafeRelease("incomplete overlay digest list")
    for name, expected in recorded.items():
        if name not in files or not isinstance(expected, str) or not HEX.fullmatch(expected):
            raise UnsafeRelease("invalid recorded ZIP entry or digest: " + name)
        if sha(files[name]) != expected:
            raise UnsafeRelease("overlay SHA256 mismatch: " + name)
    for basename, expected in manifest.get("files_sha256", {}).items():
        full_name = NESTED + basename
        if full_name in files and sha(files[full_name]) != expected:
            raise UnsafeRelease("inner installer manifest digest mismatch: " + full_name)
    if (sha(files[INSTALLER]) not in outer or sha(files[HELPER]) not in outer or
        sha(files[APK]) not in outer):
        raise UnsafeRelease("wrapper did not pin current shipped nested files")
    return {
        "status": "OWNER_BUNDLE_STATIC_VERIFIED_NO_DEVICE_INSTALL",
        "zip_sha256": sha(path.read_bytes()),
        "app_id": manifest["app_id"],
        "apk_sha256": sha(files[APK]),
        "installer_sha256": sha(files[INSTALLER]),
        "java_helper_sha256": sha(files[HELPER]),
        "powershell_bom": True,
        "java_home_optional": True,
        "device_installed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("update_zip", type=Path)
    args = parser.parse_args()
    try:
        result = audit(args.update_zip)
    except (OSError, ValueError, KeyError, BadZipFile) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
