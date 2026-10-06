from __future__ import annotations

import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from tools.base_mod.binary_axml import (
    patch_equal_length_strings,
    string_values,
)
from tools.base_mod.dex_strings import patch_exact_dex_string
from tools.base_mod.package_flavor import (
    FLAVOR_PACKAGES,
    ORIGINAL_PACKAGE,
)


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
    def test_approved_packages_preserve_original_length(self) -> None:
        for package in FLAVOR_PACKAGES.values():
            self.assertEqual(len(package), len(ORIGINAL_PACKAGE))
            self.assertEqual(
                len(package.encode("utf-8")),
                len(ORIGINAL_PACKAGE.encode("utf-8")),
            )

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