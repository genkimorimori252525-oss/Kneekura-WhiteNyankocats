import unittest

from tools.base_mod.dex_methods import _code_metadata, _uleb128


class DexMethodScannerTests(unittest.TestCase):
    def test_uleb128_decodes_small_and_multibyte_values(self) -> None:
        self.assertEqual(_uleb128(bytes([0x00]), 0), (0, 1))
        self.assertEqual(_uleb128(bytes([0x7F]), 0), (127, 1))
        self.assertEqual(_uleb128(bytes([0x80, 0x01]), 0), (128, 2))
        self.assertEqual(_uleb128(bytes([0xE5, 0x8E, 0x26]), 0), (624485, 3))

    def test_uleb128_rejects_truncation(self) -> None:
        with self.assertRaisesRegex(ValueError, "truncated"):
            _uleb128(bytes([0x80]), 0)

    def test_code_metadata_hashes_header_and_instruction_bytes(self) -> None:
        import hashlib
        import struct

        data = bytearray(64)
        code_off = 8
        struct.pack_into("<HHHHII", data, code_off, 4, 1, 2, 0, 0x1234, 3)
        instructions = bytes.fromhex("010203040506")
        data[code_off + 16:code_off + 22] = instructions

        meta = _code_metadata(bytes(data), code_off)
        self.assertEqual(meta["registers_size"], 4)
        self.assertEqual(meta["ins_size"], 1)
        self.assertEqual(meta["outs_size"], 2)
        self.assertEqual(meta["tries_size"], 0)
        self.assertEqual(meta["debug_info_off"], 0x1234)
        self.assertEqual(meta["insns_size"], 3)
        self.assertEqual(
            meta["insns_sha256"],
            hashlib.sha256(instructions).hexdigest(),
        )
        self.assertEqual(
            meta["code_header_insns_sha256"],
            hashlib.sha256(bytes(data[code_off:code_off + 22])).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()
