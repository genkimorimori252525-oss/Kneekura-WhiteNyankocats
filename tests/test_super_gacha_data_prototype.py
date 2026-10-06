import unittest

from tools.base_mod.super_gacha_data_prototype import (
    OPTION,
    R1,
    R2,
    R3,
    build_replacements,
    choose_safe_seed_units,
    choose_visible_clone_option_set,
)


class SuperGachaDataPrototypeTests(unittest.TestCase):
    def source_files(self):
        r1 = b"30,31,-1\n40,41,42,-1\n"
        r2 = b"-1\n-1\n"
        r3 = b"-1\n-1\n"
        option = (
            b"GatyaSetID\tBannerON_OFF\tItemID_Ticket\tanimeID\tbtnCutID\t"
            b"seriesID\tmenuCutID\tCharaID\twaitmaanimON_OFF\timgID\n"
            b"0\t0\t21\t0\t0\t0\t1\t-1\t0\t-1\n"
            b"1\t1\t21\t0\t0\t1\t1\t-1\t0\t-1\n"
        )
        return r1, r2, r3, option

    def test_auto_seed_pool_prefers_distinct_rare_tiers(self) -> None:
        r1 = b"30,31,40,41,50,60,-1\n"
        unit_rows = []
        for unit_id in range(61):
            rarity = 1
            if unit_id == 30:
                rarity = 2
            elif unit_id == 40:
                rarity = 3
            elif unit_id == 50:
                rarity = 4
            elif unit_id == 60:
                rarity = 5
            cells = ["0"] * 14
            cells[13] = str(rarity)
            unit_rows.append(",".join(cells))
        unitbuy = ("\n".join(unit_rows) + "\n").encode()

        self.assertEqual(
            choose_safe_seed_units(r1, unitbuy, count=3),
            [30, 40, 50],
        )

    def test_clone_selector_uses_existing_banner_on_row(self) -> None:
        option = (
            b"GatyaSetID\tBannerON_OFF\tItemID_Ticket\n"
            b"0\t0\t21\n"
            b"1\t1\t21\n"
            b"2\t1\t21\n"
        )
        self.assertEqual(choose_visible_clone_option_set(option), 1)

    def test_append_only_prototype_keeps_original_rows(self) -> None:
        r1, r2, r3, option = self.source_files()
        replacements, ledger = build_replacements(
            r1,
            r2,
            r3,
            option,
            clone_option_set=1,
            unit_ids=[30, 42],
            banner_on=1,
        )

        self.assertEqual(ledger["new_set_id"], 2)
        self.assertFalse(ledger["rarity_probability_vector_defined"])
        self.assertFalse(ledger["visibility_schedule_defined"])
        self.assertFalse(ledger["original_rows_replaced"])

        self.assertTrue(replacements[R1].startswith(r1))
        self.assertTrue(replacements[R2].startswith(r2))
        self.assertTrue(replacements[R3].startswith(r3))
        self.assertTrue(replacements[OPTION].startswith(option))
        self.assertTrue(replacements[R1].endswith(b"30,42,-1\n"))
        self.assertTrue(replacements[R2].endswith(b"-1\n"))
        self.assertIn(b"2\t1\t21\t0\t0\t1\t1\t-1\t0\t-1\n", replacements[OPTION])

    def test_unproven_unit_is_rejected(self) -> None:
        r1, r2, r3, option = self.source_files()
        with self.assertRaisesRegex(ValueError, "not present"):
            build_replacements(
                r1,
                r2,
                r3,
                option,
                clone_option_set=0,
                unit_ids=[999],
            )

    def test_explicit_cheater_id_is_rejected_even_if_present(self) -> None:
        r1 = b"673,30,-1\n"
        r2 = b"-1\n"
        r3 = b"-1\n"
        option = (
            b"GatyaSetID\tBannerON_OFF\n"
            b"0\t0\n"
        )
        with self.assertRaisesRegex(ValueError, "excluded"):
            build_replacements(
                r1,
                r2,
                r3,
                option,
                clone_option_set=0,
                unit_ids=[673],
            )

    def test_duplicate_weighting_is_not_silently_introduced(self) -> None:
        r1, r2, r3, option = self.source_files()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            build_replacements(
                r1,
                r2,
                r3,
                option,
                clone_option_set=0,
                unit_ids=[30, 30],
            )


if __name__ == "__main__":
    unittest.main()
