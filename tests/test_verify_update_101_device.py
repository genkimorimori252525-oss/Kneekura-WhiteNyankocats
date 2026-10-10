"""No Android device required. Fail-closed backup/signature tests."""
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
from subprocess import CompletedProcess
from tools.base_mod import verify_update_101_device as u


def valid_save():
    payload = struct.pack("<i", 150700) + b"\0" * 190
    return payload + hashlib.md5(b"battlecats" + payload).hexdigest().encode()


class Update101DevicePreflightTests(unittest.TestCase):
    def test_save_validation(self):
        data = valid_save()
        self.assertTrue(u.save_integrity(data)["jp_md5_valid"])
        with self.assertRaises(u.Refused):
            u.save_integrity(data[:5] + b"\x01" + data[6:])
        with self.assertRaises(u.Refused):
            u.save_integrity(struct.pack("<i", 123) + data[4:])

    def test_installed_exact_six(self):
        lines = "\n".join("package:/data/app/~app/" + n for n in u.APK_NAMES)
        self.assertEqual(set(u.installed_paths(lines)), set(u.APK_NAMES))
        with self.assertRaises(u.Refused):
            u.installed_paths(lines + "\npackage:/data/app/~app/base.apk")
        with self.assertRaises(u.Refused):
            u.installed_paths(lines + "\npackage:/data/app/~app/evil.apk")
        with self.assertRaises(u.Refused):
            u.installed_paths(lines.replace("/data/app/", "/sdcard/"))

    def test_certificate_and_package(self):
        digest = "aB" * 32
        with patch.object(u, "call", return_value=CompletedProcess([], 0,
                  "Signer #1 certificate SHA-256 digest: " + digest, "")):
            self.assertEqual(u.signer("apksigner", Path("base.apk")), digest.lower())
        with patch.object(u, "call", return_value=CompletedProcess([], 0,
                  "package: name='jp.kn.white.battlecats' versionCode='1507010'", "")):
            self.assertEqual(u.package_version("aapt", Path("base.apk")),
                             ("jp.kn.white.battlecats", 1507010))

    def test_missing_signed_splits_refuses_before_apksigner(self):
        with tempfile.TemporaryDirectory() as path:
            with patch.object(u, "call") as execute:
                with self.assertRaises(u.Refused):
                    u.optional_signed(Path(path), "jp.kn.white.battlecats",
                                      "aapt", "apksigner", "a"*64)
                execute.assert_not_called()

    def test_refuse_existing_backup_without_accessing_device(self):
        with tempfile.TemporaryDirectory() as d, patch.object(u, "call") as execute:
            with self.assertRaises(u.Refused):
                u.snapshot("jp.kn.white.battlecats", Path(d), adb="adb",
                           aapt="aapt", apksigner="apksigner")
            execute.assert_not_called()

    def test_refuse_app_running_before_any_pull(self):
        def mocked(args, **opts):
            if args[-1] == "get-state":
                return CompletedProcess(args, 0, "device\n", "")
            if args[-2:] == ["pidof", "jp.kn.white.battlecats"]:
                return CompletedProcess(args, 0, "9999\n", "")
            raise AssertionError("unexpected ADB command")
        with tempfile.TemporaryDirectory() as d, patch.object(u, "call", side_effect=mocked):
            with self.assertRaisesRegex(u.Refused, "close the game"):
                u.snapshot("jp.kn.white.battlecats", Path(d)/"backup", device="serial",
                           adb="adb", aapt="aapt", apksigner="apksigner")

    def test_no_install_or_delete_capability(self):
        src=(Path(__file__).resolve().parents[1] /
             "tools/base_mod/verify_update_101_device.py").read_text(encoding="utf-8")
        for forbidden in ['"install-multiple"', '"uninstall"', '"pm clear"',
                          '"force-stop"', '"rm -rf"', '"--apply"']:
            self.assertNotIn(forbidden, src)
        self.assertIn("snapshot-receipt.json", src)


if __name__ == "__main__":
    unittest.main()