"""Synthetic tests for the unit name text overlay."""
import hashlib
import unittest
from unittest import mock

from tools.base_mod import unit_name_overlay as N

NAME = 'Unit_Explanation100_ja.csv'
EOL = '\r\n'
LINES = ['狂乱の巨神ネコ,a,b,c,キョウランノキョシンネコ,' + EOL,
         '狂乱のネコダラボッチ,a,b,c,キョウランノネコダラボッチ,' + EOL,
         '大狂乱のネコジャラミ,a,b,c,ダイキョウランノネコジャラミ,' + EOL]


class NameOverlayTests(unittest.TestCase):
    def test_renames_only_form2_name_and_reading(self):
        original = ''.join(LINES).encode('utf-8')
        with mock.patch.dict(N.ORIGINAL_SHA256, {NAME: hashlib.sha256(original).hexdigest()}):
            out = N.build_candidate(NAME, original).decode('utf-8').splitlines(keepends=True)
        self.assertEqual((out[0], out[2]), (LINES[0], LINES[2]))
        self.assertEqual(out[1], '狂乱のネコ親分,a,b,c,キョウランノネコオヤブン,' + EOL)

    def test_fail_closed(self):
        original = ''.join(LINES).encode('utf-8')
        with self.assertRaises(ValueError):
            N.build_candidate(NAME, original)  # not the pinned original
        bad = original.replace('ダラボッチ'.encode(), 'X'.encode())
        with mock.patch.dict(N.ORIGINAL_SHA256, {NAME: hashlib.sha256(bad).hexdigest()}):
            with self.assertRaises(ValueError):
                N.build_candidate(NAME, bad)


if __name__ == '__main__':
    unittest.main()
