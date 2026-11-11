from __future__ import annotations

import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
import zlib
import zipfile

from tools.base_mod.binary_axml import (
    patch_boolean_attribute,
    patch_equal_length_strings,
    string_values,
)
from tools.base_mod.dex_strings import patch_exact_dex_string
from tools.base_mod.package_flavor import (
    FLAVOR_PACKAGES,
    ORIGINAL_PACKAGE,
    patch_split_set,
    patch_resource_package,
)
from tools.base_mod.verify_parity import _verify_resource_package


def _len8(value: int) -> bytes:
    if value < 0x80:
        return bytes([value])
    return bytes([0x80 | (value >> 8), value & 0xFF])


def _fake_axml(strings: list[str]) -> bytes:
    encoded_parts = []
    offsets = []
    cursor = 0
    for value in strings:
        payload = value.encode("utf-8")
        offsets.append(cursor)
        part = _len8(len(value)) + _len8(len(payload)) + payload + b"\x00"
        encoded_parts.append(part)
        cursor += len(part)

    pool_data = b"".join(encoded_parts)
    header_size = 28
    strings_start = header_size + 4 * len(strings)
    padding = (-len(pool_data)) % 4
    pool_size = strings_start + len(pool_data) + padding
    pool = bytearray()
    pool += struct.pack("<HHI", 0x0001, header_size, pool_size)
    pool += struct.pack(
        "<IIIII",
        len(strings),
        0,
        0x100,
        strings_start,
        0,
    )
    for offset in offsets:
        pool += struct.pack("<I", offset)
    pool += pool_data + b"\x00" * padding

    total = 8 + len(pool)
    return struct.pack("<HHI", 0x0003, 8, total) + bytes(pool)


def _fake_dex(value: str) -> bytes:
    payload = value.encode("utf-8")
    string_data_off = 0x74
    data = bytearray(string_data_off + 1 + len(payload) + 1)
    data[0:8] = b"dex\n035\x00"
    struct.pack_into("<I", data, 0x20, len(data))
    struct.pack_into("<I", data, 0x24, 0x70)
    struct.pack_into("<I", data, 0x28, 0x12345678)
    struct.pack_into("<I", data, 0x38, 1)
    struct.pack_into("<I", data, 0x3C, 0x70)
    struct.pack_into("<I", data, 0x70, string_data_off)
    data[string_data_off] = len(value)
    start = string_data_off + 1
    data[start : start + len(payload)] = payload
    data[start + len(payload)] = 0
    data[12:32] = hashlib.sha1(data[32:]).digest()
    struct.pack_into("<I", data, 8, zlib.adler32(data[12:]) & 0xFFFFFFFF)
    return bytes(data)


class PackageFlavorTests(unittest.TestCase):
    def test_resource_parser_rejects_drift_and_static_audit_rejects_other_changes(self):
        package = FLAVOR_PACKAGES["local-research"]
        header = bytearray(288)
        struct.pack_into("<HHII", header, 0, 0x0200, 288, 288, 0x7f)
        encoded = ORIGINAL_PACKAGE.encode("utf-16le")
        header[12:12 + len(encoded)] = encoded
        original = struct.pack("<HHII", 2, 12, 300, 1) + header
        patched = patch_resource_package(original, package, base=False)
        invalids = [original[:-1], original[:12], bytes(300)]
        drift = bytearray(original)
        drift[24] = ord("x")
        invalids.append(bytes(drift))
        drift = bytearray(original)
        struct.pack_into("<I", drift, 16, 1000)
        invalids.append(bytes(drift))
        invalids.append(struct.pack("<HHII", 2, 12, 588, 1) + header + header)
        for invalid in invalids:
            with self.subTest(size=len(invalid)), self.assertRaises(ValueError):
                patch_resource_package(invalid, package, base=False)
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / "source.apk", Path(tmp) / "final.apk"
            with zipfile.ZipFile(src, "w") as z:
                z.writestr("resources.arsc", original)
            for actual, passes in ((patched, True), (original, False),
                                   (patched[:-1] + b"x", False)):
                with zipfile.ZipFile(dst, "w") as z:
                    z.writestr("resources.arsc", actual)
                if passes:
                    _verify_resource_package(src, dst, "split_config.ja.apk", package)
                else:
                    with self.assertRaisesRegex(ValueError, "delta is not exact"):
                        _verify_resource_package(src, dst, "split_config.ja.apk", package)

    def test_all_resource_packages_match_isolated_manifest_without_other_changes(self):
        """Android resolves getIdentifier against ResTable_package.name, not UTF-8."""
        package = FLAVOR_PACKAGES["local-research"]
        resource_splits = ("base.apk", "split_config.en.apk",
                           "split_config.ja.apk", "split_config.xxhdpi.apk")
        header = bytearray(288)
        struct.pack_into("<HHII", header, 0, 0x0200, 288, 288, 0x7f)
        name = ORIGINAL_PACKAGE.encode("utf-16le")
        header[12:12 + len(name)] = name
        # Unrelated string-pool bytes containing the same UTF-16 text must stay.
        tail = b"unrelated:" + name
        tail += b"\0" * ((-len(tail)) % 4)
        pool = struct.pack("<HHI", 1, 8, 8 + len(tail)) + tail
        table = struct.pack("<HHII", 2, 12, 12 + len(header) + len(pool), 1)
        resources = table + header + pool
        base_tail = ORIGINAL_PACKAGE.encode() + b"\0"
        base_tail += b"\0" * ((-len(base_tail)) % 4)
        base_pool = struct.pack("<HHI", 1, 8, 8 + len(base_tail)) + base_tail
        base_resources = bytearray(resources + base_pool)
        struct.pack_into("<I", base_resources, 4, len(base_resources))
        suffixes = ("", ".DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION",
                    ".IronsourceLifecycleProvider", ".applovininitprovider",
                    ".androidx-startup", ".AudienceNetworkContentProvider",
                    ".mobileadsinitprovider", ".firebaseinitprovider",
                    ".adjust-lifecycle-provider", ".MyActivity")
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / "source", Path(tmp) / "output"
            src.mkdir()
            for split in (*resource_splits, "split_config.arm64_v8a.apk",
                          "split_InstallPack.apk"):
                with zipfile.ZipFile(src / split, "w") as z:
                    z.writestr("AndroidManifest.xml", _fake_axml(
                        [ORIGINAL_PACKAGE + s for s in suffixes]))
                    z.writestr("assets/unchanged.bin", b"original asset")
                    if split in resource_splits:
                        z.writestr("resources.arsc", base_resources if split == "base.apk"
                                   else resources)
                    if split == "base.apk":
                        z.writestr("classes.dex", _fake_dex(ORIGINAL_PACKAGE))
                        z.writestr("classes2.dex", _fake_dex(
                            ORIGINAL_PACKAGE + ".NotificationChannel."))
                    if split == "split_config.arm64_v8a.apk":
                        z.writestr("lib/arm64-v8a/libkneekura.so", b"inert")
                        z.writestr("lib/arm64-v8a/libnative-lib.so", ORIGINAL_PACKAGE.encode())
            patch_split_set(src, dst, flavor="local-research")
            for split in resource_splits:
                with zipfile.ZipFile(dst / split) as z:
                    actual = z.read("resources.arsc")
                    self.assertEqual(actual[24:280].decode("utf-16le").split("\0")[0], package)
                    expected = bytearray(base_resources if split == "base.apk" else resources)
                    expected[24:24 + len(name)] = package.encode("utf-16le")
                    if split == "base.apk":
                        expected = expected.replace(ORIGINAL_PACKAGE.encode(), package.encode())
                    self.assertEqual(actual, bytes(expected))
                    self.assertEqual(z.read("assets/unchanged.bin"), b"original asset")

    def test_approved_packages_preserve_original_length(self) -> None:
        for package in FLAVOR_PACKAGES.values():
            self.assertEqual(len(package), len(ORIGINAL_PACKAGE))
            self.assertEqual(
                len(package.encode("utf-8")),
                len(ORIGINAL_PACKAGE.encode("utf-8")),
            )

    def test_research_flavor_is_separate_and_equal_length(self) -> None:
        research = FLAVOR_PACKAGES["research"]
        self.assertEqual(research, "jp.kn.trace.battlecats")
        self.assertEqual(len(research), len(ORIGINAL_PACKAGE))
        self.assertNotIn(research, {
            FLAVOR_PACKAGES["personal"],
            FLAVOR_PACKAGES["practice"],
        })

    def test_axml_patch_does_not_rename_launcher_namespace(self) -> None:
        personal = FLAVOR_PACKAGES["personal"]
        source = _fake_axml(
            [
                ORIGINAL_PACKAGE,
                ORIGINAL_PACKAGE + ".DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION",
                ORIGINAL_PACKAGE + ".MyActivity",
            ]
        )
        patched, counts = patch_equal_length_strings(
            source,
            {
                ORIGINAL_PACKAGE: personal,
                ORIGINAL_PACKAGE + ".DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION":
                    personal + ".DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION",
            },
        )
        values = string_values(patched)
        self.assertEqual(counts[ORIGINAL_PACKAGE], 1)
        self.assertIn(personal, values)
        self.assertIn(ORIGINAL_PACKAGE + ".MyActivity", values)
        self.assertNotIn(personal + ".MyActivity", values)

    def test_boolean_attribute_patcher_rejects_missing_attribute(self) -> None:
        source = _fake_axml(["application", "extractNativeLibs"])
        with self.assertRaisesRegex(ValueError, "exactly one"):
            patch_boolean_attribute(
                source,
                element_name="application",
                attribute_name="extractNativeLibs",
                expected=False,
                replacement=True,
            )

    def test_research_manifest_code_requests_native_extraction(self) -> None:
        source = (
            Path(__file__).resolve().parents[1]
            / "tools/base_mod/package_flavor.py"
        ).read_text(encoding="utf-8")
        self.assertIn('flavor == "research"', source)
        self.assertIn('attribute_name="extractNativeLibs"', source)
        self.assertIn("replacement=extract_native_libs", source)

    def test_dex_equal_length_patch_repairs_header(self) -> None:
        practice = FLAVOR_PACKAGES["practice"]
        source = _fake_dex(ORIGINAL_PACKAGE)
        patched, count = patch_exact_dex_string(
            source,
            ORIGINAL_PACKAGE,
            practice,
            expected_count=1,
        )
        self.assertEqual(count, 1)
        self.assertIn(practice.encode(), patched)
        self.assertNotIn(ORIGINAL_PACKAGE.encode(), patched)
        self.assertEqual(
            patched[12:32],
            hashlib.sha1(patched[32:]).digest(),
        )
        self.assertEqual(
            struct.unpack_from("<I", patched, 8)[0],
            zlib.adler32(patched[12:]) & 0xFFFFFFFF,
        )


if __name__ == "__main__":
    unittest.main()
