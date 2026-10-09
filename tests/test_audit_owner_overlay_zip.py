"""The full nested owner ZIP, not just repo wrapper, is the release unit."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.base_mod.audit_owner_overlay_zip import (
    APK, HELPER, INSTALLER, INSTALL_MANIFEST, OVERLAY_MANIFEST,
    REQUIRED, WRAPPER, UnsafeRelease, audit, sha,
)


def make_bundle(root: Path, *, mutation: str = "") -> Path:
    wrapper = "\ufeffparam([switch]$Apply)\nif (-not $Apply) { return }\n"
    installer = "\ufeffparam([switch]$CheckJava)\n. $javaResolver\n"
    installer += "$keytool = Resolve-JavaKeytool\n"
    helper = "\ufefffunction Resolve-JavaKeytool { return 'C:\\\\JDK\\\\bin\\\\keytool.exe' }\n"
    if mutation == "null_java_home":
        installer += "$keypath = Join-Path $env:JAVA_HOME 'bin\\\\keytool.exe'\n"
    if mutation == "destructive":
        installer += "adb uninstall jp.kneekura.whitenyankocats\n"
    if mutation == "no_bom":
        installer = installer.lstrip("\ufeff")
    inner = installer.encode("utf-8")
    ext = helper.encode("utf-8")
    apk = b"TEST_APK_ONLY_NOT_A_REAL_ANDROID_PACKAGE"
    wrapper += sha(inner) + "\n" + sha(ext) + "\n" + sha(apk)
    data = {
        WRAPPER: wrapper.encode("utf-8"),
        INSTALLER: inner, HELPER: ext, APK: apk,
    }
    data[INSTALL_MANIFEST] = json.dumps({
        "app_id": "jp.kneekura.whitenyankocats",
        "files_sha256": {
            "INSTALL-ALPHA.ps1": sha(inner),
            "independent-alpha.apk": sha(apk),
        },
    }).encode("utf-8")
    manifest = {
        "app_package": "jp.kneekura.whitenyankocats",
        "privacy": {"never_uninstalls_app": True},
        "files": {name: sha(blob) for name, blob in data.items()},
    }
    data[OVERLAY_MANIFEST] = json.dumps(manifest).encode("utf-8")
    # Wrap entrypoint in UTF8 BOM, just like the distributed Windows script.
    data[WRAPPER] = b"\xef\xbb\xbf" + data[WRAPPER]
    manifest["files"][WRAPPER] = sha(data[WRAPPER])
    data[OVERLAY_MANIFEST] = json.dumps(manifest).encode("utf-8")
    if mutation == "stale_checksum":
        data[APK] += b"tampered"
    if mutation == "missing_helper":
        del data[HELPER]
    bundle = root / "candidate.zip"
    with zipfile.ZipFile(bundle, "w") as z:
        for name, blob in data.items():
            z.writestr(name, blob)
    return bundle


class OwnerZipRegressionTests(unittest.TestCase):
    def test_valid_synthetic_archive_receipt(self):
        with tempfile.TemporaryDirectory() as root:
            result = audit(make_bundle(Path(root)))
            self.assertTrue(result["powershell_bom"])
            self.assertTrue(result["java_home_optional"])
            self.assertFalse(result["device_installed"])

    def test_known_user_failure_modes_rejected_before_distribution(self):
        for mode in ("null_java_home", "no_bom", "destructive",
                     "stale_checksum", "missing_helper"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as root:
                with self.assertRaises(UnsafeRelease):
                    audit(make_bundle(Path(root), mutation=mode))


if __name__ == "__main__":
    unittest.main()
