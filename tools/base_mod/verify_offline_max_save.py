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
    TALENT_ORB_COUNT,
    TALENT_ORB_COUNT_OFFSET,
    TALENT_ORB_DATA_OFFSET,
    TALENT_ORB_INSERT_BYTES,
    TALENT_ORB_VALUE,
    _derive_unit_contract,
    _verify_jp_hash,
)


CANDIDATE_SIZE = 497_580
RUNTIME_REWRITE_SIZE = 507_174
EXPECTED_GAME_VERSION = 150700

RUNTIME_SHIFT_BASE_MATERIALS = 6_725
RUNTIME_SHIFT_MID_RESOURCES = 9_485
RUNTIME_SHIFT_LATE_RESOURCES = 9_578


def verify_runtime_rewrite_prefix(data: bytes) -> dict[str, Any]:
    """Verify only fields that are before the first variable-length save region.

    The original game is allowed to reserialize/expand later sections after a
    successful launch. This mode is deliberately not a substitute for the full
    semantic verifier; it prevents a benign size drift from being mislabeled as
    save corruption while preserving fail-closed checks on the JP envelope,
    version, Cat Food, XP and tutorial gate.
    """
    stored_md5, expected_md5 = _verify_jp_hash(data)
    game_version = struct.unpack_from("<i", data, 0)[0]
    if game_version != EXPECTED_GAME_VERSION:
        raise ValueError(f"unexpected SAVE_DATA game version: {game_version}")

    stable = {
        "catfood": struct.unpack_from("<i", data, I32["catfood"])[0],
        "xp": struct.unpack_from("<i", data, I32["xp"])[0],
        "tutorial_state": struct.unpack_from("<i", data, I32["tutorial_state"])[0],
        "korea_superior_treasure_state": struct.unpack_from(
            "<i", data, I32["korea_superior_treasure_state"]
        )[0],
        "ui6": struct.unpack_from("<i", data, I32["ui6"])[0],
    }

    failures: list[str] = []
    if stable["catfood"] != MAX_VALUES["catfood"]:
        failures.append(f"catfood={stable['catfood']} != {MAX_VALUES['catfood']}")
    if stable["xp"] != MAX_VALUES["xp"]:
        failures.append(f"xp={stable['xp']} != {MAX_VALUES['xp']}")
    if stable["tutorial_state"] < 1:
        failures.append("tutorial_state < 1")
    if stable["korea_superior_treasure_state"] < 2:
        failures.append("korea_superior_treasure_state < 2")
    if stable["ui6"] < 1:
        failures.append("ui6 < 1")

    return {
        "schema_version": 1,
        "mode": "offline-max-runtime-rewrite-prefix-verification",
        "verification_level": "stable-prefix-only",
        "layout_profile": "runtime-rewrite-unmapped",
        "save_size": len(data),
        "candidate_size": CANDIDATE_SIZE,
        "size_delta_from_candidate": len(data) - CANDIDATE_SIZE,
        "jp_salted_md5": stored_md5,
        "jp_hash_valid": stored_md5 == expected_md5,
        "game_version": game_version,
        "stable_prefix": stable,
        "full_dynamic_semantic_verification": "pending-postrewrite-layout-map",
        "semantic_scope_complete": False,
        "failures": failures,
        "passed": not failures,
    }


def _profile_offset(offset: int, profile: str) -> int:
    """Map an original baseline field offset into a candidate/runtime profile.

    This helper is only for fields that already existed in the baseline. Talent
    Orb records themselves are inserted data and use _talent_data_offset().
    """
    mapped = offset
    if offset >= TALENT_ORB_DATA_OFFSET:
        mapped += TALENT_ORB_INSERT_BYTES

    if profile == "runtime-rewrite":
        if offset >= TALENT_ORB_COUNT_OFFSET:
            mapped += RUNTIME_SHIFT_LATE_RESOURCES
        elif offset >= ARRAYS_I32["lucky_tickets"][2]:
            mapped += RUNTIME_SHIFT_MID_RESOURCES
        elif offset >= ARRAYS_I32["base_materials"][2]:
            mapped += RUNTIME_SHIFT_BASE_MATERIALS
    elif profile != "candidate":
        raise ValueError(f"unknown SAVE_DATA profile: {profile}")

    return mapped


def _talent_count_offset(profile: str) -> int:
    if profile == "candidate":
        return TALENT_ORB_COUNT_OFFSET
    if profile == "runtime-rewrite":
        return TALENT_ORB_COUNT_OFFSET + RUNTIME_SHIFT_LATE_RESOURCES
    raise ValueError(f"unknown SAVE_DATA profile: {profile}")


def _talent_data_offset(profile: str) -> int:
    if profile == "candidate":
        return TALENT_ORB_DATA_OFFSET
    if profile == "runtime-rewrite":
        return TALENT_ORB_DATA_OFFSET + RUNTIME_SHIFT_LATE_RESOURCES
    raise ValueError(f"unknown SAVE_DATA profile: {profile}")


def _read_i32(data: bytes, offset: int, profile: str) -> int:
    return struct.unpack_from("<i", data, _profile_offset(offset, profile))[0]


def _read_i16(data: bytes, offset: int, profile: str) -> int:
    return struct.unpack_from("<h", data, _profile_offset(offset, profile))[0]


def _read_i32_array(data: bytes, name: str, profile: str) -> list[int]:
    start, length, count_offset = ARRAYS_I32[name]
    if count_offset is not None:
        actual = _read_i32(data, count_offset, profile)
        if actual != length:
            raise ValueError(f"{name} count mismatch: {actual} != {length}")
    return [_read_i32(data, start + i * 4, profile) for i in range(length)]


def verify_max_save(
    data: bytes,
    owned_export: Path,
    *,
    allow_runtime_rewrite: bool = False,
) -> dict[str, Any]:
    if len(data) == CANDIDATE_SIZE:
        profile = "candidate"
    elif allow_runtime_rewrite and len(data) == RUNTIME_REWRITE_SIZE:
        profile = "runtime-rewrite"
    elif allow_runtime_rewrite and len(data) > CANDIDATE_SIZE:
        return verify_runtime_rewrite_prefix(data)
    else:
        raise ValueError(f"unexpected SAVE_DATA size: {len(data)}")

    stored_md5, expected_md5 = _verify_jp_hash(data)
    if _read_i32(data, 0, profile) != EXPECTED_GAME_VERSION:
        raise ValueError("unexpected SAVE_DATA game version")

    eligible, drop_save_ids, contract = _derive_unit_contract(owned_export)
    if len(eligible) != 835:
        raise ValueError(f"unexpected eligible unit count: {len(eligible)}")
    if len(drop_save_ids) != 255:
        raise ValueError(f"unexpected unit-drop contract count: {len(drop_save_ids)}")

    unlocked = _read_i32_array(data, "cat_unlocked", profile)
    gatya_seen = _read_i32_array(data, "cat_gatya_seen", profile)
    current_form = _read_i32_array(data, "cat_current_form", profile)
    unlocked_forms = _read_i32_array(data, "cat_unlocked_forms", profile)
    fourth_form = _read_i32_array(data, "cat_fourth_form", profile)
    unit_drops = _read_i32_array(data, "unit_drops", profile)

    unit_checks = {
        "eligible_owned": sum(unlocked[i] != 0 for i in eligible),
        "eligible_gatya_seen": sum(gatya_seen[i] != 0 for i in eligible),
        "eligible_first_form": sum(current_form[i] == 0 for i in eligible),
        "eligible_unlocked_forms_zero": sum(unlocked_forms[i] == 0 for i in eligible),
        "eligible_fourth_form_zero": sum(fourth_form[i] == 0 for i in eligible),
        "required_drop_ids_enabled": sum(unit_drops[i] != 0 for i in drop_save_ids),
    }

    scalar_values = {
        "catfood": _read_i32(data, I32["catfood"], profile),
        "xp": _read_i32(data, I32["xp"], profile),
        "normal_tickets": _read_i32(data, I32["normal_tickets"], profile),
        "rare_tickets": _read_i32(data, I32["rare_tickets"], profile),
        "platinum_tickets": _read_i32(data, I32["platinum_tickets"], profile),
        "legend_tickets": _read_i32(data, I32["legend_tickets"], profile),
        "platinum_shards": _read_i32(data, I32["platinum_shards"], profile),
        "np": _read_i32(data, I32["np"], profile),
        "leadership": _read_i16(data, I16["leadership"], profile),
        "hundred_million_ticket": _read_i32(data, I32["hundred_million_ticket"], profile),
        "engineers": _read_i32(data, I32["engineers"], profile),
    }

    arrays = {
        "battle_items": _read_i32_array(data, "battle_items", profile),
        "catfruit": _read_i32_array(data, "catfruit", profile),
        "catseyes": _read_i32_array(data, "catseyes", profile),
        "catamins": _read_i32_array(data, "catamins", profile),
        "base_materials": _read_i32_array(data, "base_materials", profile),
        "lucky_tickets": _read_i32_array(data, "lucky_tickets", profile),
        "treasure_chests": _read_i32_array(data, "treasure_chests", profile),
    }
    if data[_profile_offset(484927, profile)] != ARRAYS_I16["labyrinth_medals"][1]:
        raise ValueError("labyrinth medal count mismatch")
    if data[_profile_offset(495796, profile)] != ARRAYS_I32["treasure_chests"][1]:
        raise ValueError("treasure chest count mismatch")
    lab_start, lab_len, _ = ARRAYS_I16["labyrinth_medals"]
    labyrinth_medals = [
        _read_i16(data, lab_start + i * 2, profile)
        for i in range(lab_len)
    ]

    talent_count = struct.unpack_from("<h", data, _talent_count_offset(profile))[0]
    talent_orbs: list[tuple[int, int]] = []
    if talent_count == TALENT_ORB_COUNT:
        for i in range(talent_count):
            offset = _talent_data_offset(profile) + i * 4
            talent_orbs.append(struct.unpack_from("<hh", data, offset))

    tutorial = {
        "tutorial_state": _read_i32(data, I32["tutorial_state"], profile),
        "korea_superior_treasure_state": _read_i32(
            data, I32["korea_superior_treasure_state"], profile
        ),
        "ui6": _read_i32(data, I32["ui6"], profile),
        "chapter0_progress": _read_i32(data, I32["story_chapter0_progress"], profile),
        "chapter0_stage0_clear": _read_i32(data, I32["story_chapter0_stage0_clear"], profile),
        "equip_menu": _read_i32(data, I32["menu_unlock_equip"], profile),
        "dialog1": _read_i32(data, I32["new_dialog_1"], profile),
        "dialog5": _read_i32(data, I32["new_dialog_5"], profile),
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
        ("engineers", MAX_VALUES["engineers"]),
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

    if talent_count != TALENT_ORB_COUNT:
        failures.append(f"talent_orb_count={talent_count} != {TALENT_ORB_COUNT}")
    elif any(
        orb_id != index or value != TALENT_ORB_VALUE
        for index, (orb_id, value) in enumerate(talent_orbs)
    ):
        failures.append("talent_orbs do not contain all exact IDs at max count")

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
        "verification_level": "full-semantic",
        "layout_profile": profile,
        "semantic_scope_complete": True,
        "save_size": len(data),
        "candidate_size": CANDIDATE_SIZE,
        "runtime_rewrite_size": RUNTIME_REWRITE_SIZE,
        "jp_salted_md5": stored_md5,
        "jp_hash_valid": stored_md5 == expected_md5,
        "unit_contract": contract,
        "unit_checks": unit_checks,
        "scalar_values": scalar_values,
        "array_lengths": {key: len(value) for key, value in arrays.items()},
        "labyrinth_medals_length": len(labyrinth_medals),
        "talent_orbs": {
            "count": talent_count,
            "value_each_expected": TALENT_ORB_VALUE,
        },
        "tutorial": tutorial,
        "failures": failures,
        "passed": not failures,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("save_data", type=Path)
    parser.add_argument("owned_export", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--allow-runtime-rewrite",
        action="store_true",
        help="allow an original-game rewritten save to grow and verify only stable prefix anchors",
    )
    args = parser.parse_args(argv)

    try:
        result = verify_max_save(
            args.save_data.read_bytes(),
            args.owned_export,
            allow_runtime_rewrite=args.allow_runtime_rewrite,
        )
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
