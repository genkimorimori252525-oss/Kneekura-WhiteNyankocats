import unittest

from tools.base_mod.arm64_string_xrefs import (
    _decode_add_immediate,
    _decode_adrp,
)


class Arm64StringXrefTests(unittest.TestCase):
    def test_exact_daily_login_data_xref_pair_decodes(self) -> None:
        # JP 15.7.1 @ 0x9c3424:
        #   adrp x8, 0x1a2000
        #   add  x8, x8, #0x698
        page, register = _decode_adrp(0xF0FFBEE8, 0x9C3424)
        self.assertEqual(page, 0x1A2000)
        self.assertEqual(register, 8)

        rn, rd, immediate = _decode_add_immediate(0x911A6108)
        self.assertEqual((rn, rd, immediate), (8, 8, 0x698))
        self.assertEqual(page + immediate, 0x1A2698)

    def test_exact_login_background_xref_pair_decodes(self) -> None:
        # JP 15.7.1 @ 0x548190:
        #   adrp x9, 0x1ad000
        #   add  x9, x9, #0x6cd
        page, register = _decode_adrp(0xB0FFE329, 0x548190)
        self.assertEqual(page, 0x1AD000)
        self.assertEqual(register, 9)

        rn, rd, immediate = _decode_add_immediate(0x911B3529)
        self.assertEqual((rn, rd, immediate), (9, 9, 0x6CD))
        self.assertEqual(page + immediate, 0x1AD6CD)

    def test_non_matching_instructions_are_rejected(self) -> None:
        self.assertIsNone(_decode_adrp(0xD65F03C0, 0x1000))
        self.assertIsNone(_decode_add_immediate(0xD65F03C0))


if __name__ == "__main__":
    unittest.main()
