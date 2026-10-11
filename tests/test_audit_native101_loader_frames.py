"""Synthetic unwind and AArch64 literal-address scanner fixtures."""
import struct
import unittest
from tools.base_mod.audit_native101_loader_frames import (
    frame_starts, function_bounds, find_references, audit_owner_binary
)


class Native101LoaderFrameTests(unittest.TestCase):
    def test_decode_sorted_pcrel_datarel_function_table(self):
        blob = bytearray(200)
        offset = 32
        blob[offset:offset+4] = b"\x01\x1b\x03\x3b"
        struct.pack_into("<I", blob, offset+8, 3)
        for i, start in enumerate([1000, 1024, 2048]):
            struct.pack_into("<ii", blob, offset+12+i*8, start-offset, 0)
        self.assertEqual(frame_starts(bytes(blob), offset), [1000, 1024, 2048])
        self.assertEqual(function_bounds(1026, [1000, 1024, 2048]), (1024, 2048))
        with self.assertRaises(ValueError):
            function_bounds(2048, [1000, 1024, 2048])
        blob[offset+1] = 0
        with self.assertRaises(ValueError):
            frame_starts(bytes(blob), offset)

    def test_adrp_add_literal_pair_exact(self):
        blob = bytearray(0x5000)
        pc = 0x1000
        page = 0x2000
        # ADRP x8, +0x1000 (imm=1), then ADD x8,x8,#0x123.
        word = 0x90000008 | (1 << 29)
        struct.pack_into("<I", blob, pc, word)
        add = 0x91000000 | (0x123 << 10) | (8 << 5) | 8
        struct.pack_into("<I", blob, pc+4, add)
        xrefs = find_references(bytes(blob), {"known": page+0x123, "other": page+0x124},
                                code_begin=pc, code_end=pc+64)
        self.assertEqual(xrefs, {"known": [pc], "other": []})

    def test_pin_blocks_unrecognized_binary(self):
        with self.assertRaises(ValueError):
            audit_owner_binary(b"not-an-exact-user-lib")


if __name__ == "__main__":
    unittest.main()