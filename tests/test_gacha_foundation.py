import unittest

from tools.analyze_gacha_foundation import (
    parse_dataset_row_lengths,
    parse_dataset_rows,
    parse_unit_rarities,
    parse_event_gacha_setting,
    parse_unit_rarity_counts,
)


class GachaFoundationTests(unittest.TestCase):
    def test_unit_rarity_uses_unitbuy_column_13(self) -> None:
        payload = (
            b"0,0,0,0,0,0,0,0,0,0,0,0,0,2,0\n"
            b"0,0,0,0,0,0,0,0,0,0,0,0,0,4,0\n"
            b"0,0,0,0,0,0,0,0,0,0,0,0,0,4,0\n"
        )
        self.assertEqual(parse_unit_rarity_counts(payload), {2: 1, 4: 2})

    def test_unit_rarity_map_preserves_row_index(self) -> None:
        payload = (
            b"0,0,0,0,0,0,0,0,0,0,0,0,0,2,0\n"
            b"0,0,0,0,0,0,0,0,0,0,0,0,0,5,0\n"
        )
        self.assertEqual(parse_unit_rarities(payload), {0: 2, 1: 5})

    def test_dataset_lengths_stop_at_negative_one(self) -> None:
        payload = b"10,20,30,-1,999\n-1\n5,6\n"
        self.assertEqual(parse_dataset_row_lengths(payload), [3, 0, 2])

    def test_dataset_rows_preserve_unit_ids(self) -> None:
        payload = b"10,20,30,-1,999\n-1\n5,6\n"
        self.assertEqual(parse_dataset_rows(payload), [[10, 20, 30], [], [5, 6]])

    def test_event_setting_parses_group_unit_value_triples(self) -> None:
        payload = b"55,0,776,3,2,504,1\n"
        self.assertEqual(
            parse_event_gacha_setting(payload),
            [
                {
                    "gacha_id": 55,
                    "entries": [
                        {"group": 0, "unit": 776, "value": 3},
                        {"group": 2, "unit": 504, "value": 1},
                    ],
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
