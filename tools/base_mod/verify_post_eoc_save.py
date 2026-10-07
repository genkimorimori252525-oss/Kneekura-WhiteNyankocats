"""Read-only semantic verifier for the JP 15.7.1 Kneekura Post-EoC profile."""

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
    I16,
    I32,
    MAX_VALUES,
    TALENT_ORB_COUNT,
    TALENT_ORB_COUNT_OFFSET,
    TALENT_ORB_DATA_OFFSET,
    TALENT_ORB_INSERT_BYTES,
    TALENT_ORB_VALUE,
    _verify_jp_hash,
)
from tools.base_mod.build_post_eoc_save import (
    CLEARED_EOC_1_OFFSET,
    EOC_CHAPTERS,
    EOC_STAGE_COUNT,
    EOC_TREASURE_LEVEL,
    EVENT_CLEAR_PROGRESS_BASE,
    EVENT_MAP_CAPACITY,
    EVENT_SELECTED_STAGE_BASE,
    EVENT_STAGE_CAPACITY,
    EVENT_STAGE_CLEAR_BASE,
    EVENT_STAR_CAPACITY,
    EVENT_TYPE_COLLAB,
    EVENT_TYPE_NORMAL,
    EVENT_TYPE_SOL,
    EVENT_UNLOCK_STATE_BASE,
    POST_EOC_OWNED_IDS,
    STORY_CLEAR_SLOTS_PER_CHAPTER,
    STORY_CLEAR_TIMES_OFFSET,
    STORY_PROGRESS_OFFSET,
    STORY_TREASURE_OFFSET,
    STORY_TREASURE_SLOTS_PER_CHAPTER,
    _derive_event_map_ids,
    _event_type_block,
)


EXPECTED_SIZE = 497_580
EXPECTED_GAME_VERSION = 150700


def _candidate_offset(offset: int) -> int:
    if offset >= TALENT_ORB_DATA_OFFSET:
        return offset + TALENT_ORB_INSERT_BYTES
    return offset


def _i32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<i", data, _candidate_offset(offset))[0]


def _i16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<h", data, _candidate_offset(offset))[0]


def _i32_array(data: bytes, name: str) -> list[int]:
    start, length, count_offset = ARRAYS_I32[name]
    if count_offset is not None and _i32(data, count_offset) != length:
        raise ValueError(
            f"{name} count mismatch: {_i32(data, count_offset)} != {length}"
        )
    return [_i32(data, start + index * 4) for index in range(length)]


def verify_post_eoc_save(data: bytes, export_zip: Path) -> dict[str, Any]:
    if len(data) != EXPECTED_SIZE:
        raise ValueError(f"unexpected Post-EoC SAVE_DATA size: {len(data)}")

    stored_hash, expected_hash = _verify_jp_hash(data)
    if struct.unpack_from("<i", data, 0)[0] != EXPECTED_GAME_VERSION:
        raise ValueError("unexpected game version")

    failures: list[str] = []

    story: dict[str, Any] = {
        "eoc": {},
        "future_cotc": {},
    }
    for chapter in EOC_CHAPTERS:
        progress = struct.unpack_from(
            "<i", data, STORY_PROGRESS_OFFSET + chapter * 4
        )[0]
        clears = [
            struct.unpack_from(
                "<i",
                data,
                STORY_CLEAR_TIMES_OFFSET
                + (chapter * STORY_CLEAR_SLOTS_PER_CHAPTER + stage) * 4,
            )[0]
            for stage in range(EOC_STAGE_COUNT)
        ]
        treasures = [
            struct.unpack_from(
                "<i",
                data,
                STORY_TREASURE_OFFSET
                + (chapter * STORY_TREASURE_SLOTS_PER_CHAPTER + stage) * 4,
            )[0]
            for stage in range(EOC_STAGE_COUNT)
        ]
        story["eoc"][str(chapter)] = {
            "progress": progress,
            "cleared_stages": sum(value > 0 for value in clears),
            "superior_treasures": sum(value == EOC_TREASURE_LEVEL for value in treasures),
        }
        if progress != EOC_STAGE_COUNT:
            failures.append(f"EoC chapter {chapter} progress={progress}")
        if any(value <= 0 for value in clears):
            failures.append(f"EoC chapter {chapter} has uncleared stage")
        if any(value != EOC_TREASURE_LEVEL for value in treasures):
            failures.append(f"EoC chapter {chapter} has non-Superior treasure")

    for chapter in (4, 5, 6, 7, 8, 9):
        progress = struct.unpack_from(
            "<i", data, STORY_PROGRESS_OFFSET + chapter * 4
        )[0]
        clear_nonzero = 0
        treasure_nonzero = 0
        for stage in range(STORY_CLEAR_SLOTS_PER_CHAPTER):
            value = struct.unpack_from(
                "<i",
                data,
                STORY_CLEAR_TIMES_OFFSET
                + (chapter * STORY_CLEAR_SLOTS_PER_CHAPTER + stage) * 4,
            )[0]
            clear_nonzero += value != 0
        for stage in range(STORY_TREASURE_SLOTS_PER_CHAPTER):
            value = struct.unpack_from(
                "<i",
                data,
                STORY_TREASURE_OFFSET
                + (chapter * STORY_TREASURE_SLOTS_PER_CHAPTER + stage) * 4,
            )[0]
            treasure_nonzero += value != 0

        story["future_cotc"][str(chapter)] = {
            "progress": progress,
            "clear_nonzero": clear_nonzero,
            "treasure_nonzero": treasure_nonzero,
        }
        if progress or clear_nonzero or treasure_nonzero:
            failures.append(f"story chapter {chapter} is not clean")

    cleared_eoc_1 = struct.unpack_from("<i", data, CLEARED_EOC_1_OFFSET)[0]
    if cleared_eoc_1 < 1:
        failures.append("cleared_eoc_1 flag is not set")

    # Acquisition contract.
    unlocked = _i32_array(data, "cat_unlocked")
    seen = _i32_array(data, "cat_gatya_seen")
    current_forms = _i32_array(data, "cat_current_form")
    unlocked_forms = _i32_array(data, "cat_unlocked_forms")
    fourth_forms = _i32_array(data, "cat_fourth_form")
    expected_owned = set(POST_EOC_OWNED_IDS)

    actual_owned = {index for index, value in enumerate(unlocked) if value != 0}
    actual_seen = {index for index, value in enumerate(seen) if value != 0}
    if actual_owned != expected_owned:
        failures.append(
            f"owned cat ids mismatch: actual={sorted(actual_owned)} "
            f"expected={sorted(expected_owned)}"
        )
    if actual_seen != expected_owned:
        failures.append("gacha-seen IDs do not match Post-EoC ownership")
    if any(current_forms) or any(unlocked_forms) or any(fourth_forms):
        failures.append("later cat forms were force-unlocked")

    unit_drops = _i32_array(data, "unit_drops")
    if any(unit_drops):
        failures.append("stage-drop reward ownership is pre-granted")

    # Event unlock-only contract.
    event_ids, event_evidence = _derive_event_map_ids(export_zip)
    event_summary: dict[str, Any] = {}

    expected_unlocks = {
        EVENT_TYPE_SOL: {0},
        EVENT_TYPE_NORMAL: set(event_ids[EVENT_TYPE_NORMAL]),
        EVENT_TYPE_COLLAB: set(event_ids[EVENT_TYPE_COLLAB]),
    }

    for event_type in (EVENT_TYPE_SOL, EVENT_TYPE_NORMAL, EVENT_TYPE_COLLAB):
        selected_base = _event_type_block(
            EVENT_SELECTED_STAGE_BASE, event_type, EVENT_STAR_CAPACITY
        )
        progress_base = _event_type_block(
            EVENT_CLEAR_PROGRESS_BASE, event_type, EVENT_STAR_CAPACITY
        )
        stage_base = _event_type_block(
            EVENT_STAGE_CLEAR_BASE,
            event_type,
            EVENT_STAR_CAPACITY * EVENT_STAGE_CAPACITY,
        )
        unlock_base = _event_type_block(
            EVENT_UNLOCK_STATE_BASE, event_type, EVENT_STAR_CAPACITY
        )

        selected_nonzero = sum(
            data[selected_base + index] != 0
            for index in range(EVENT_MAP_CAPACITY * EVENT_STAR_CAPACITY)
        )
        progress_nonzero = sum(
            data[progress_base + index] != 0
            for index in range(EVENT_MAP_CAPACITY * EVENT_STAR_CAPACITY)
        )
        stage_nonzero = sum(
            data[stage_base + index] != 0
            for index in range(
                EVENT_MAP_CAPACITY * EVENT_STAR_CAPACITY * EVENT_STAGE_CAPACITY
            )
        )
        actual_base_star_unlocks = {
            map_id
            for map_id in range(EVENT_MAP_CAPACITY)
            if data[unlock_base + map_id * EVENT_STAR_CAPACITY] != 0
        }
        later_star_unlocks = sum(
            data[
                unlock_base
                + map_id * EVENT_STAR_CAPACITY
                + star
            ]
            != 0
            for map_id in range(EVENT_MAP_CAPACITY)
            for star in range(1, EVENT_STAR_CAPACITY)
        )

        event_summary[str(event_type)] = {
            "base_star_unlocked_count": len(actual_base_star_unlocks),
            "selected_nonzero": selected_nonzero,
            "clear_progress_nonzero": progress_nonzero,
            "stage_clear_nonzero": stage_nonzero,
            "later_star_unlock_nonzero": later_star_unlocks,
        }

        if actual_base_star_unlocks != expected_unlocks[event_type]:
            failures.append(f"event type {event_type} unlock-only map set mismatch")
        if selected_nonzero or progress_nonzero or stage_nonzero or later_star_unlocks:
            failures.append(f"event type {event_type} contains pre-cleared/progress state")

    # Low-friction economy is inherited from the MAX research layer.
    scalar_values = {
        "catfood": _i32(data, I32["catfood"]),
        "xp": _i32(data, I32["xp"]),
        "normal_tickets": _i32(data, I32["normal_tickets"]),
        "rare_tickets": _i32(data, I32["rare_tickets"]),
        "platinum_tickets": _i32(data, I32["platinum_tickets"]),
        "legend_tickets": _i32(data, I32["legend_tickets"]),
        "platinum_shards": _i32(data, I32["platinum_shards"]),
        "np": _i32(data, I32["np"]),
        "leadership": _i16(data, I16["leadership"]),
        "hundred_million_ticket": _i32(data, I32["hundred_million_ticket"]),
        "engineers": _i32(data, I32["engineers"]),
    }
    for key, value in scalar_values.items():
        if value != MAX_VALUES[key]:
            failures.append(f"{key}={value} != {MAX_VALUES[key]}")

    arrays = {
        "battle_items": _i32_array(data, "battle_items"),
        "catfruit": _i32_array(data, "catfruit"),
        "catseyes": _i32_array(data, "catseyes"),
        "catamins": _i32_array(data, "catamins"),
        "base_materials": _i32_array(data, "base_materials"),
        "lucky_tickets": _i32_array(data, "lucky_tickets"),
        "treasure_chests": _i32_array(data, "treasure_chests"),
    }
    for name, values in arrays.items():
        if any(value != MAX_VALUES[name] for value in values):
            failures.append(f"{name} is not fully maxed")

    lab_start, lab_count, _ = ARRAYS_I16["labyrinth_medals"]
    labyrinth = [_i16(data, lab_start + index * 2) for index in range(lab_count)]
    if any(value != MAX_VALUES["labyrinth_medals"] for value in labyrinth):
        failures.append("labyrinth medals are not maxed")

    talent_count = struct.unpack_from("<h", data, TALENT_ORB_COUNT_OFFSET)[0]
    talent_ok = talent_count == TALENT_ORB_COUNT
    if talent_ok:
        for index in range(TALENT_ORB_COUNT):
            orb_id, count = struct.unpack_from(
                "<hh", data, TALENT_ORB_DATA_OFFSET + index * 4
            )
            if orb_id != index or count != TALENT_ORB_VALUE:
                talent_ok = False
                break
    if not talent_ok:
        failures.append("Talent Orb inventory does not match exact JP15.7.1 MAX set")

    return {
        "schema_version": 1,
        "mode": "kneekura-post-eoc-verification",
        "verification_level": "full-semantic",
        "save_size": len(data),
        "jp_salted_md5": stored_hash,
        "jp_hash_valid": stored_hash == expected_hash,
        "story": story,
        "cleared_eoc_1": cleared_eoc_1,
        "ownership": {
            "owned_ids": sorted(actual_owned),
            "owned_count": len(actual_owned),
            "required_ids": list(POST_EOC_OWNED_IDS),
            "unit_drop_nonzero": sum(value != 0 for value in unit_drops),
        },
        "events": {
            **event_evidence,
            "types": event_summary,
        },
        "economy": scalar_values,
        "talent_orbs": {
            "count": talent_count,
            "value_each_expected": TALENT_ORB_VALUE,
            "passed": talent_ok,
        },
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
        result = verify_post_eoc_save(
            args.save_data.read_bytes(),
            args.owned_export,
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"Post-EoC verification failed: {exc}", file=sys.stderr)
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
