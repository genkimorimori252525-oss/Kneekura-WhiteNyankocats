"""Version-pinned unit identifier namespaces for Battle Cats data.

Public unit/cat-guide numbers use 1-based numbering (e.g. Madoka No.289).
The SAVE_DATA cat arrays and unitbuy.csv rows use 0-based asset IDs (288).
The filename unit289.csv is in the 1-based namespace.

Never pass a public No.289 directly as a SAVE_DATA index.
"""

from __future__ import annotations


def asset_id_from_catalog_no(catalog_no: int) -> int:
    if catalog_no < 1:
        raise ValueError(f"invalid 1-based unit catalog number: {catalog_no}")
    return catalog_no - 1


def unit_csv_name_from_catalog_no(catalog_no: int) -> str:
    if catalog_no < 1:
        raise ValueError(f"invalid 1-based unit catalog number: {catalog_no}")
    return f"unit{catalog_no:03d}.csv"


IMPORTANT_COLLAB_CATALOG_NUMBERS: dict[str, int] = {
    "madoka": 289,
    "homura": 290,
    "saber": 363,
    "hatsune_miku": 536,
}

IMPORTANT_COLLAB_ASSET_IDS: tuple[int, ...] = tuple(
    asset_id_from_catalog_no(number)
    for number in IMPORTANT_COLLAB_CATALOG_NUMBERS.values()
)
