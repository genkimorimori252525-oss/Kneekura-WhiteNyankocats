"""Tests on synthetic AArch64/SSO data; no original APK, packs or SAVE committed."""
import struct
import unittest

from tools.base_mod.original_server_registry_rows import (
    _ConstructorSlice, _decode_registered_pair, recover_original_92_server_rows,
    ServerRegistryTraceError, TABLE_BASE, TABLE_COUNT, ROW_SIZE, SEED_OPCODES,
)


class OriginalServerRegistrationTests(unittest.TestCase):
    @staticmethod
    def fixture():
        # Fake 7 MiB source for exact instruction operands, not private binary.
        blob = bytearray(0x716F24)
        for address, (word, _, _) in SEED_OPCODES.items():
            struct.pack_into("<I", blob, address, word)
        blob[0x1918D1:0x1918E3] = b"XImageServer.list\0"
        return blob

    @staticmethod
    def sso(name):
        encoded = name.encode("ascii")
        assert 1 <= len(encoded) <= 22
        return bytes((2 * len(encoded),)) + encoded + bytes(23 - len(encoded))

    def test_synthetic_adrp_load_and_bss_write_preserves_elf(self):
        blob = self.fixture()
        words = {
            0x71599C: 0x90FFD3E9, 0x7159A0: 0x91234529,
            0x7159A4: 0xF0004408, 0x7159A8: 0x9134E108,
            0x7159AC: 0x3DC00120, 0x7159C0: 0x3C801100,
        }
        for pc, word in words.items():
            struct.pack_into("<I", blob, pc, word)
        before = bytes(blob)
        replay = _ConstructorSlice(bytes(blob))
        for pc in words:
            replay._execute_one(pc)
        self.assertEqual(replay._load(TABLE_BASE + 1, 16), b"XImageServer.lis")
        self.assertEqual(bytes(blob), before)

    def test_exact_synthetic_short_string_pair(self):
        table = bytearray(TABLE_COUNT * ROW_SIZE)
        table[:24] = self.sso("XImageServer.list")
        table[24:48] = self.sso("XImageServer.pack")
        self.assertEqual(_decode_registered_pair(bytes(table), 0),
                         ("XImageServer.list", "XImageServer.pack"))
        self.assertRaises(ServerRegistryTraceError, _decode_registered_pair,
                          bytes(table), TABLE_COUNT)

    def test_short_string_malformed_tag_terminator_or_nonascii_refused(self):
        table = bytearray(TABLE_COUNT * ROW_SIZE)
        table[:24] = self.sso("XImageServer.list")
        table[24:48] = self.sso("XImageServer.pack")
        for position, wrong in ((0, 0x23), (18, 0x41), (2, 0xFF), (23, 0x42)):
            changed = bytearray(table)
            changed[position] = wrong
            with self.subTest(position=position), self.assertRaises(ServerRegistryTraceError):
                _decode_registered_pair(bytes(changed), 0)

    def test_synthetic_mutated_constructor_instruction_and_bss_escape_refused(self):
        blob = self.fixture()
        replay = _ConstructorSlice(bytes(blob))
        with self.assertRaises(ServerRegistryTraceError):
            replay._execute_one(0x71599C)  # unknown synthetic zero word
        blob = self.fixture()
        struct.pack_into("<I", blob, 0x7157F8, 0)
        with self.assertRaises(ServerRegistryTraceError):
            _ConstructorSlice(bytes(blob))
        replay = _ConstructorSlice(bytes(self.fixture()))
        with self.assertRaises(ServerRegistryTraceError):
            replay._store(TABLE_BASE + ROW_SIZE * TABLE_COUNT - 1, b"AB")

    def test_exact_original_hash_required_even_with_fake_catalog(self):
        with self.assertRaises(ServerRegistryTraceError):
            recover_original_92_server_rows(bytes(self.fixture()),
                                            original_catalog={"XImageServer"})


if __name__ == "__main__":
    unittest.main()
