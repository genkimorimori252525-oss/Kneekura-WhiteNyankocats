import unittest

from tools.base_mod.dex_methods import _uleb128


class DexMethodScannerTests(unittest.TestCase):
    def test_uleb128_decodes_small_and_multibyte_values(self) -> None:
        self.assertEqual(_uleb128(bytes([0x00]), 0), (0, 1))
        self.assertEqual(_uleb128(bytes([0x7F]), 0), (127, 1))
        self.assertEqual(_uleb128(bytes([0x80, 0x01]), 0), (128, 2))
        self.assertEqual(_uleb128(bytes([0xE5, 0x8E, 0x26]), 0), (624485, 3))

    def test_uleb128_rejects_truncation(self) -> None:
        with self.assertRaisesRegex(ValueError, "truncated"):
            _uleb128(bytes([0x80]), 0)


if __name__ == "__main__":
    unittest.main()
