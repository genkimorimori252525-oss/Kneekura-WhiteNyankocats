import unittest

from tools.base_mod.dex_code_refs import instruction_width


class DexCodeReferenceTests(unittest.TestCase):
    def test_standard_reference_instruction_widths(self) -> None:
        self.assertEqual(instruction_width([0x0322, 0x1234], 0), 2)  # new-instance
        self.assertEqual(
            instruction_width([0x2070, 0x1234, 0x0003], 0),
            3,
        )  # invoke-direct
        self.assertEqual(
            instruction_width([0x1076, 0x1234, 0x0000], 0),
            3,
        )  # invoke-direct/range
        self.assertEqual(instruction_width([0x011A, 0x1234], 0), 2)  # const-string

    def test_switch_payload_widths(self) -> None:
        # packed-switch payload: ident, size=2, first_key(2 units), targets(4 units)
        self.assertEqual(
            instruction_width(
                [0x0100, 0x0002, 0, 0, 0, 0, 0, 0],
                0,
            ),
            8,
        )
        # sparse-switch payload: ident, size=2, keys(4 units), targets(4 units)
        self.assertEqual(
            instruction_width(
                [0x0200, 0x0002, 0, 0, 0, 0, 0, 0, 0, 0],
                0,
            ),
            10,
        )

    def test_fill_array_payload_rounds_to_code_units(self) -> None:
        # element width=1, size=3 -> 3 payload bytes -> 2 code units
        self.assertEqual(
            instruction_width([0x0300, 0x0001, 0x0003, 0x0000, 0, 0], 0),
            6,
        )

    def test_unknown_opcode_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported DEX opcode"):
            instruction_width([0x00E9], 0)


if __name__ == "__main__":
    unittest.main()
