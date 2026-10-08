import unittest

from tools.base_mod.unit_identifiers import (
    IMPORTANT_COLLAB_ASSET_IDS,
    IMPORTANT_COLLAB_CATALOG_NUMBERS,
    asset_id_from_catalog_no,
    unit_csv_name_from_catalog_no,
)
from tools.base_mod import build_post_eoc_save, level_cap_unlock


class BattleCatsUnitIdentifierContractTest(unittest.TestCase):
    def test_public_catalog_numbers_differ_from_save_asset_ids(self):
        self.assertEqual(IMPORTANT_COLLAB_CATALOG_NUMBERS, {
            "madoka": 289,
            "homura": 290,
            "saber": 363,
            "hatsune_miku": 536,
        })
        self.assertEqual(IMPORTANT_COLLAB_ASSET_IDS, (288, 289, 362, 535))
        self.assertEqual(asset_id_from_catalog_no(289), 288)
        self.assertEqual(unit_csv_name_from_catalog_no(289), "unit289.csv")
        with self.assertRaises(ValueError):
            asset_id_from_catalog_no(0)
        with self.assertRaises(ValueError):
            unit_csv_name_from_catalog_no(-1)

    def test_ownership_and_level_cap_use_asset_id_namespace(self):
        self.assertEqual(
            build_post_eoc_save.IMPORTANT_COLLAB_ASSET_IDS,
            IMPORTANT_COLLAB_ASSET_IDS,
        )
        self.assertEqual(
            level_cap_unlock.IMPORTANT_COLLAB_ASSET_IDS,
            IMPORTANT_COLLAB_ASSET_IDS,
        )


if __name__ == "__main__":
    unittest.main()
