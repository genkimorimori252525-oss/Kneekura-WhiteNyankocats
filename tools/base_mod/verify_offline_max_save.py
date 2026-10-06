"""Verify that a JP 15.7.1 SAVE_DATA still carries the offline MAX profile.

Unlike the one-time builder, this verifier accepts post-launch/post-upgrade saves
whose timestamp/hash may have changed. It validates the exact save layout,
JP salted-MD5 integrity, eligible-unit ownership contract, tutorial gate and
resource values without modifying the file.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import sys
from typing import Any

from tools.base_mod.build_offline_max_save import (
    ARRAYS_I16,
    ARRAYS_I32,
    HASH_LEN,
    I16,
    I32,
    MAX_VALUES,
    _derive_unit_contract,
    _verify_jp_hash,
)


EXPECTED_SIZE = 496_340
EXPECTED_GAME_VERSION = 150700


def _read_i32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<i", data, offset)[0]


def _read_i16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<h", data, offset)[0]


def _read_i32_array(data: bytes, name: str) -> list[int]:
    start, length, count_offset = ARRAYS_I32[name]
    if count_offset is not None:
        actual = _read_i32(data, count_offset)
        if actual != length:
            raise ValueError(f"{name} count mismatch: {actual} != {length}")
    return [_read_i32(data, start + i * 4) for i in range(length)]


def verify_max_save(data: bytes, owned_export: Path) -> dict[str, Any]:
    if len(data) != EXPECTED_SIZE:
        raise ValueError(f"unexpected SAVE_DATA size: {len(data)}")

    stored_md5, expected_md5 = _verify_jp_hash(data)
    if _read_i32(data, 0) != EXPECTED_GAME_VERSION:
        raise ValueError("unexpected SAVE_DATA game version")

    eligible, drop_save_ids, contract = _derive_unit_contract(owned_export)
    if len(eligible) != 835:
        raise ValueError(f"unexpected eligible unit count: {len(eligible)}")
    if len(drop_save_ids) != 255:
        raise ValueError(f"unexpected unit-drop contract count: {len(drop_save_ids)}")

    unlocked = _read_i32_array(data, "cat_unlocked")
    gatya_seen = _read_i32_array(data, "cat_gatya_seen")
    current_form = _read_i32_array(data, "cat_current_form")
    unlocked_forms = _read_i32_array(data, "cat_unlocked_forms")
    fourth_form = _read_i32_array(data, "cat_fourth_form")
    unit_drops = _read_i32_array(data, "unit_drops")

    unit_checks = {
        "eligible_owned": sum(unlocked[i] != 0 for i in eligible),
        "eligible_gatya_seen": sum(gatya_seen[i] != 0 for i in eligible),
        "eligible_first_form": sum(current_form[i] == 0 for i in eligible),
        "eligible_unlocked_forms_zero": sum(unlocked_forms[i] == 0 for i in eligible),
        "eligible_fourth_form_zero": sum(fourth_form[i] == 0 for i in eligible),
        "required_drop_ids_enabled": sum(unit_drops[i] != 0 for i in drop_save_ids),
    }

    scalar_values = {
        "catfood": _read_i32(data, I32["catfood"]),
        "xp": _read_i32(data, I32["xp"]),
        "normal_tickets": _read_i32(data, I32["normal_tickets"]),
        "rare_tickets": _read_i32(data, I32["rare_tickets"]),
        "platinum_tickets": _read_i32(data, I32["platinum_tickets"]),
        "legend_tickets": _read_i32(data, I32["legend_tickets"]),
        "platinum_shards": _read_i32(data, I32["platinum_shards"]),
        "np": _read_i32(data, I32["np"]),
        "leadership": _read_i16(data, I16["leadership"]),
        "hundred_million_ticket": _read_i32(data, I32["hundred_million_ticket"]),
    }

    arrays = {
        "battle_items": _read_i32_array(data, "battle_items"),
        "catfruit": _read_i32_array(data, "catfruit"),
        "catseyes": _read_i32_array(data, "catseyes"),
        "catamins": _read_i32_array(data, "catamins"),
        "base_materials": _read_i32_array(data, "base_materials"),
        "lucky_tickets": _read_i32_array(data, "lucky_tickets"),
        "treasure_chests": _read_i32_array(data, "treasure_chests"),
    }
    if data[484927] != ARRAYS_I16["labyrinth_medals"][1]:
        raise ValueError("labyrinth medal count mismatch")
    if data[495796] != ARRAYS_I32["treasure_chests"][1]:
        raise ValueError("treasure chest count mismatch")
    lab_start, lab_len, _ = ARRAYS_I16["labyrinth_medals"]
    labyrinth_medals = [_read_i16(data, lab_start + i * 2) for i in range(lab_len)]

    tutorial = {
        "tutorial_state": _read_i32(data, I32["tutorial_state"]),
        "korea_superior_treasure_state": _read_i32(
            data, I32["korea_superior_treasure_state"]
        ),
        "ui6": _read_i32(data, I32["ui6"]),
        "chapter0_progress": _read_i32(data, I32["story_chapter0_progress"]),
        "chapter0_stage0_clear": _read_i32(data, I32["story_chapter0_stage0_clear"]),
        "equip_menu": _read_i32(data, I32["menu_unlock_equip"]),
        "dialog1": _read_i32(data, I32["new_dialog_1"]),
        "dialog5": _read_i32(data, I32["new_dialog_5"]),
    }

    failures: list[str] = []
    for key in (
        "eligible_owned",
        "eligible_gatya_seen",
        "eligible_first_form",
        "eligible_unlocked_forms_zero",
        "eligible_fourth_form_zero",
    ):
        if unit_checks[key] != 835:
            failures.append(f"{key}={unit_checks[key]} != 835")
    if unit_checks["required_drop_ids_enabled"] != 255:
        failures.append(
            f"required_drop_ids_enabled={unit_checks['required_drop_ids_enabled']} != 255"
        )

    for key, expected in (
        ("catfood", MAX_VALUES["catfood"]),
        ("xp", MAX_VALUES["xp"]),
        ("normal_tickets", MAX_VALUES["normal_tickets"]),
        ("rare_tickets", MAX_VALUES["rare_tickets"]),
        ("platinum_tickets", MAX_VALUES["platinum_tickets"]),
        ("legend_tickets", MAX_VALUES["legend_tickets"]),
        ("platinum_shards", MAX_VALUES["platinum_shards"]),
        ("np", MAX_VALUES["np"]),
        ("leadership", MAX_VALUES["leadership"]),
        ("hundred_million_ticket", MAX_VALUES["hundred_million_ticket"]),
    ):
        if scalar_values[key] != expected:
            failures.append(f"{key}={scalar_values[key]} != {expected}")

    for key in (
        "battle_items",
        "catfruit",
        "catseyes",
        "catamins",
        "base_materials",
        "lucky_tickets",
        "treasure_chests",
    ):
        expected = MAX_VALUES[key]
        if any(value != expected for value in arrays[key]):
            failures.append(f"{key} contains values other than {expected}")
    if any(value != MAX_VALUES["labyrinth_medals"] for value in labyrinth_medals):
        failures.append("labyrinth_medals not fully maxed")

    if tutorial["tutorial_state"] < 1:
        failures.append("tutorial_state < 1")
    if tutorial["korea_superior_treasure_state"] < 2:
        failures.append("korea_superior_treasure_state < 2")
    if tutorial["ui6"] < 1 or tutorial["equip_menu"] < 1:
        failures.append("tutorial/equip UI gate not unlocked")
    if tutorial["chapter0_progress"] < 1 or tutorial["chapter0_stage0_clear"] < 1:
        failures.append("first EoC stage/progress not minimally cleared")
    if tutorial["dialog1"] < 2 or tutorial["dialog5"] < 2:
        failures.append("tutorial dialog gate not cleared")

    return {
        "schema_version": 1,
        "mode": "offline-max-profile-verification",
        "save_size": len(data),
        "jp_salted_md5": stored_md5,
        "jp_hash_valid": stored_md5 == expected_md5,
        "unit_contract": contract,
        "unit_checks": unit_checks,
        "scalar_values": scalar_values,
        "array_lengths": {key: len(value) for key, value in arrays.items()},
        "labyrinth_medals_length": len(labyrinth_medals),
        "tutorial": tutorial,
        "failures": failures,
        "passed": not failures,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("save_data", type=Path)
    parser.add_argument("owned_export", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        result = verify_max_save(args.save_data.read_bytes(), args.owned_export)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"offline MAX verification failed: {exc}", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
