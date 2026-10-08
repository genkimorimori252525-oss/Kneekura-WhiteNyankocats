"""Build the JP 15.7.1 Kneekura Post-EoC playable profile.

The mainline profile is deliberately different from the earlier all-units MAX
research profile:

- Empire of Cats chapters 1-3 are fully cleared with Superior treasures;
- Into the Future / Cats of the Cosmos remain untouched at zero progression;
- Stories of Legend starts normally from its first map;
- exact normal-event and collaboration maps are unlock-only, never pre-cleared;
- all exact guide-visible/playable non-stage-reward units are pre-owned;
- exact stage-reward units remain unowned for actual story/Tower/event play;
- economy/material values retain the low-friction MAX research values.

The resource layer reuses the independently verified MAX transformer. This file
then rewrites only progression/ownership/event-state fields that occur before
the variable Talent Orb insertion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
from typing import Any

from tools.battlecats_source import BattleCatsExport
from tools.base_mod.unit_identifiers import IMPORTANT_COLLAB_ASSET_IDS
from tools.base_mod.build_offline_profile_unit_manifest import build_manifest
from tools.base_mod.build_offline_max_save import (
    ARRAYS_I32,
    EXPORT_SHA256,
    _rewrite_hash,
    _verify_jp_hash,
    build_max_save,
)


EOC_CHAPTERS = (0, 1, 2)
EOC_STAGE_COUNT = 48
EOC_TREASURE_LEVEL = 3

STORY_PROGRESS_OFFSET = 1_145
STORY_CLEAR_TIMES_OFFSET = 1_185
STORY_CLEAR_SLOTS_PER_CHAPTER = 51
STORY_TREASURE_OFFSET = 3_225
STORY_TREASURE_SLOTS_PER_CHAPTER = 49
CLEARED_EOC_1_OFFSET = 120

# Ownership is derived from exact JP 15.7.1 acquisition data:
# all guide-visible/playable units are pre-owned EXCEPT characters whose exact
# drop_chara.csv has a non-negative stageDropCharaID. This preserves stage
# rewards (SoL/Tower/event/etc.) for actual play while retaining gacha/collab
# gacha/Legend Rare ownership. Valkyrie/Bahamut are not stage-drop rows and are
# therefore naturally retained by this rule.
EXPECTED_STAGE_REWARD_VISIBLE = 158
EXPECTED_PREOWNED_COUNT = 677
EXPECTED_LEGEND_RARE_COUNT = 18

EVENT_TYPE_COUNT = 5
EVENT_MAP_CAPACITY = 500
EVENT_STAR_CAPACITY = 4
EVENT_STAGE_CAPACITY = 12

# Exact JP 15.7.1 SAVE_DATA offsets proven one-field-at-a-time against the
# pinned research parser. For each map, star entries are adjacent bytes.
EVENT_SELECTED_STAGE_BASE = 24_450
EVENT_CLEAR_PROGRESS_BASE = 34_450
EVENT_STAGE_CLEAR_BASE = 68_450
EVENT_UNLOCK_STATE_BASE = 284_450

EVENT_TYPE_SOL = 0
EVENT_TYPE_NORMAL = 1
EVENT_TYPE_COLLAB = 2


def _write_i32(data: bytearray, offset: int, value: int) -> None:
    struct.pack_into("<i", data, offset, int(value))


def _event_type_block(base: int, event_type: int, bytes_per_map: int) -> int:
    return base + event_type * EVENT_MAP_CAPACITY * bytes_per_map


def _derive_ownership_contract(
    export_zip: Path,
) -> tuple[list[int], list[int], list[int], dict[str, Any]]:
    manifest = build_manifest(export_zip, expected_sha256=EXPORT_SHA256)
    eligible_units = manifest["eligible_units"]
    eligible_ids = {int(item["asset_id"]) for item in eligible_units}

    with BattleCatsExport(
        export_zip,
        region="jp",
        expected_sha256=EXPORT_SHA256,
    ) as source:
        data_local = source.pack("DataLocal")
        drop_payload, drop_provenance = data_local.read("drop_chara.csv")

    stage_reward_ids: set[int] = set()
    for row in drop_payload.decode("utf-8-sig", "replace").splitlines()[1:]:
        cols = [cell.strip() for cell in row.split(",")]
        if len(cols) < 3:
            continue
        try:
            stage_id = int(cols[0])
            chara_id = int(cols[2])
        except ValueError:
            continue
        if stage_id >= 0 and chara_id in eligible_ids:
            stage_reward_ids.add(chara_id)

    preowned_ids = sorted(eligible_ids - stage_reward_ids)
    stage_reward_ids_sorted = sorted(stage_reward_ids)
    legend_rare_ids = sorted(
        int(item["asset_id"])
        for item in eligible_units
        if int(item.get("rarity", -1)) == 5
    )

    if len(stage_reward_ids_sorted) != EXPECTED_STAGE_REWARD_VISIBLE:
        raise ValueError(
            "JP15.7.1 stage-reward unit count drifted: "
            f"{len(stage_reward_ids_sorted)} != {EXPECTED_STAGE_REWARD_VISIBLE}"
        )
    if len(preowned_ids) != EXPECTED_PREOWNED_COUNT:
        raise ValueError(
            f"JP15.7.1 preowned unit count drifted: "
            f"{len(preowned_ids)} != {EXPECTED_PREOWNED_COUNT}"
        )
    if len(legend_rare_ids) != EXPECTED_LEGEND_RARE_COUNT:
        raise ValueError(
            f"JP15.7.1 Legend Rare count drifted: "
            f"{len(legend_rare_ids)} != {EXPECTED_LEGEND_RARE_COUNT}"
        )
    if not set(legend_rare_ids).issubset(preowned_ids):
        raise ValueError("Legend Rare unit unexpectedly classified as stage reward")

    # Exact regression anchors for important collab/gacha units.
    for required_id in IMPORTANT_COLLAB_ASSET_IDS:
        if required_id not in preowned_ids:
            raise ValueError(f"required collab/gacha unit {required_id} not preowned")

    evidence = {
        "eligible_count": len(eligible_ids),
        "stage_reward_visible_count": len(stage_reward_ids_sorted),
        "preowned_count": len(preowned_ids),
        "stage_reward_ids_sha256": hashlib.sha256(
            ",".join(map(str, stage_reward_ids_sorted)).encode("ascii")
        ).hexdigest(),
        "preowned_ids_sha256": hashlib.sha256(
            ",".join(map(str, preowned_ids)).encode("ascii")
        ).hexdigest(),
        "legend_rare_count": len(legend_rare_ids),
        "legend_rare_ids": legend_rare_ids,
        "drop_chara_sha256": drop_provenance.payload_sha256,
        "required_collab_ids": list(IMPORTANT_COLLAB_ASSET_IDS),
    }
    return preowned_ids, stage_reward_ids_sorted, legend_rare_ids, evidence


def _derive_event_map_ids(export_zip: Path) -> tuple[dict[int, list[int]], dict[str, Any]]:
    with BattleCatsExport(
        export_zip,
        region="jp",
        expected_sha256=EXPORT_SHA256,
    ) as source:
        data_local = source.pack("DataLocal")
        ids: dict[int, list[int]] = {
            EVENT_TYPE_NORMAL: [],
            EVENT_TYPE_COLLAB: [],
        }
        name_lists: dict[int, list[str]] = {
            EVENT_TYPE_NORMAL: [],
            EVENT_TYPE_COLLAB: [],
        }

        patterns = {
            EVENT_TYPE_NORMAL: re.compile(r"^MapStageDataS_(\d{3})\.csv$"),
            EVENT_TYPE_COLLAB: re.compile(r"^MapStageDataC_(\d{3})\.csv$"),
        }

        for entry in data_local.entries:
            for event_type, pattern in patterns.items():
                match = pattern.match(entry.name)
                if match is None:
                    continue
                map_id = int(match.group(1))
                if not 0 <= map_id < EVENT_MAP_CAPACITY:
                    raise ValueError(f"event map id out of SAVE_DATA range: {entry.name}")
                ids[event_type].append(map_id)
                name_lists[event_type].append(entry.name)

    for event_type in ids:
        ids[event_type] = sorted(set(ids[event_type]))

    # Version-pinned guard. A later upstream version must deliberately revise
    # this evidence rather than silently changing the player's stage surface.
    expected_counts = {
        EVENT_TYPE_NORMAL: 436,
        EVENT_TYPE_COLLAB: 277,
    }
    for event_type, expected in expected_counts.items():
        if len(ids[event_type]) != expected:
            raise ValueError(
                f"JP15.7.1 event-map count changed for type {event_type}: "
                f"{len(ids[event_type])} != {expected}"
            )

    evidence = {
        "normal_event_map_count": len(ids[EVENT_TYPE_NORMAL]),
        "collab_event_map_count": len(ids[EVENT_TYPE_COLLAB]),
        "normal_event_ids_sha256": hashlib.sha256(
            ",".join(map(str, ids[EVENT_TYPE_NORMAL])).encode("ascii")
        ).hexdigest(),
        "collab_event_ids_sha256": hashlib.sha256(
            ",".join(map(str, ids[EVENT_TYPE_COLLAB])).encode("ascii")
        ).hexdigest(),
    }
    return ids, evidence


def _reset_event_family(data: bytearray, event_type: int) -> None:
    selected_base = _event_type_block(
        EVENT_SELECTED_STAGE_BASE, event_type, EVENT_STAR_CAPACITY
    )
    progress_base = _event_type_block(
        EVENT_CLEAR_PROGRESS_BASE, event_type, EVENT_STAR_CAPACITY
    )
    unlock_base = _event_type_block(
        EVENT_UNLOCK_STATE_BASE, event_type, EVENT_STAR_CAPACITY
    )
    stage_base = _event_type_block(
        EVENT_STAGE_CLEAR_BASE,
        event_type,
        EVENT_STAR_CAPACITY * EVENT_STAGE_CAPACITY,
    )

    data[selected_base : selected_base + EVENT_MAP_CAPACITY * EVENT_STAR_CAPACITY] = (
        b"\x00" * (EVENT_MAP_CAPACITY * EVENT_STAR_CAPACITY)
    )
    data[progress_base : progress_base + EVENT_MAP_CAPACITY * EVENT_STAR_CAPACITY] = (
        b"\x00" * (EVENT_MAP_CAPACITY * EVENT_STAR_CAPACITY)
    )
    data[unlock_base : unlock_base + EVENT_MAP_CAPACITY * EVENT_STAR_CAPACITY] = (
        b"\x00" * (EVENT_MAP_CAPACITY * EVENT_STAR_CAPACITY)
    )
    data[
        stage_base :
        stage_base
        + EVENT_MAP_CAPACITY * EVENT_STAR_CAPACITY * EVENT_STAGE_CAPACITY
    ] = b"\x00" * (
        EVENT_MAP_CAPACITY * EVENT_STAR_CAPACITY * EVENT_STAGE_CAPACITY
    )


def build_post_eoc_save(source: bytes, export_zip: Path) -> tuple[bytes, dict[str, Any]]:
    # Reuse the already verified low-friction economy layer, then explicitly
    # replace its all-unit ownership/progression policy.
    max_save, max_report = build_max_save(source, export_zip)
    out = bytearray(max_save)

    # Main story: exactly Post-EoC.
    for chapter in EOC_CHAPTERS:
        _write_i32(out, STORY_PROGRESS_OFFSET + chapter * 4, EOC_STAGE_COUNT)
        for stage in range(EOC_STAGE_COUNT):
            _write_i32(
                out,
                STORY_CLEAR_TIMES_OFFSET
                + (chapter * STORY_CLEAR_SLOTS_PER_CHAPTER + stage) * 4,
                1,
            )
            _write_i32(
                out,
                STORY_TREASURE_OFFSET
                + (chapter * STORY_TREASURE_SLOTS_PER_CHAPTER + stage) * 4,
                EOC_TREASURE_LEVEL,
            )

    # Future / Cosmos chapters are explicitly clean. Chapter index 3 is the
    # historical gap and remains untouched.
    for chapter in (4, 5, 6, 7, 8, 9):
        _write_i32(out, STORY_PROGRESS_OFFSET + chapter * 4, 0)
        for stage in range(STORY_CLEAR_SLOTS_PER_CHAPTER):
            _write_i32(
                out,
                STORY_CLEAR_TIMES_OFFSET
                + (chapter * STORY_CLEAR_SLOTS_PER_CHAPTER + stage) * 4,
                0,
            )
        for stage in range(STORY_TREASURE_SLOTS_PER_CHAPTER):
            _write_i32(
                out,
                STORY_TREASURE_OFFSET
                + (chapter * STORY_TREASURE_SLOTS_PER_CHAPTER + stage) * 4,
                0,
            )

    _write_i32(out, CLEARED_EOC_1_OFFSET, 1)

    # Acquisition truth: own every eligible non-stage-reward unit.
    preowned_ids, stage_reward_ids, legend_rare_ids, ownership_evidence = (
        _derive_ownership_contract(export_zip)
    )
    owned = set(preowned_ids)
    for cat_id in range(ARRAYS_I32["cat_unlocked"][1]):
        _write_i32(
            out,
            ARRAYS_I32["cat_unlocked"][0] + cat_id * 4,
            int(cat_id in owned),
        )
        _write_i32(
            out,
            ARRAYS_I32["cat_gatya_seen"][0] + cat_id * 4,
            int(cat_id in owned),
        )
        _write_i32(out, ARRAYS_I32["cat_current_form"][0] + cat_id * 4, 0)
        _write_i32(out, ARRAYS_I32["cat_unlocked_forms"][0] + cat_id * 4, 0)
        _write_i32(out, ARRAYS_I32["cat_fourth_form"][0] + cat_id * 4, 0)

    # Stage-drop ownership remains completely unclaimed. This covers SoL,
    # Tower/dojo-style and event-stage rewards and lets the original reward path
    # grant them through play.
    for save_id in range(ARRAYS_I32["unit_drops"][1]):
        _write_i32(out, ARRAYS_I32["unit_drops"][0] + save_id * 4, 0)

    event_ids, event_evidence = _derive_event_map_ids(export_zip)

    # SoL starts at its first map; no clear history.
    _reset_event_family(out, EVENT_TYPE_SOL)
    out[
        _event_type_block(
            EVENT_UNLOCK_STATE_BASE, EVENT_TYPE_SOL, EVENT_STAR_CAPACITY
        )
    ] = 1

    # Normal event + collab maps are available but never pre-cleared.
    for event_type in (EVENT_TYPE_NORMAL, EVENT_TYPE_COLLAB):
        _reset_event_family(out, event_type)
        unlock_base = _event_type_block(
            EVENT_UNLOCK_STATE_BASE, event_type, EVENT_STAR_CAPACITY
        )
        for map_id in event_ids[event_type]:
            out[unlock_base + map_id * EVENT_STAR_CAPACITY] = 1

    jp_md5 = _rewrite_hash(out)
    built = bytes(out)
    _verify_jp_hash(built)

    report = {
        "schema_version": 1,
        "mode": "kneekura-post-eoc-profile",
        "anchor": "jp-15.7.1",
        "source": max_report["source"],
        "output": {
            "size": len(built),
            "sha256": hashlib.sha256(built).hexdigest(),
            "jp_md5": jp_md5,
        },
        "economy_base": max_report["max_values"],
        "story": {
            "eoc_chapters": list(EOC_CHAPTERS),
            "eoc_progress_each": EOC_STAGE_COUNT,
            "eoc_clear_count_each": EOC_STAGE_COUNT,
            "eoc_treasure_level": EOC_TREASURE_LEVEL,
            "future_cotc_progress": 0,
        },
        "ownership": {
            **ownership_evidence,
            "preowned_ids": preowned_ids,
            "stage_reward_ids": stage_reward_ids,
            "legend_rare_ids": legend_rare_ids,
            "stage_drop_save_ids_enabled": 0,
            "policy": "all eligible non-stage-reward units owned",
        },
        "events": {
            **event_evidence,
            "sol_policy": "first-map-only / uncleared",
            "normal_event_policy": "unlock-only / uncleared",
            "collab_event_policy": "unlock-only / uncleared",
        },
        "login": {
            "runtime_scheduler": "separate sidecar/liveops layer",
            "save_login_progress_pregranted": False,
        },
        "integrity": {
            "jp_hash_valid": True,
            "source_untouched": True,
        },
    }
    return built, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("save_data", type=Path)
    parser.add_argument("owned_export", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        built, report = build_post_eoc_save(
            args.save_data.read_bytes(),
            args.owned_export,
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"Post-EoC build failed: {exc}", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(built)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"built Post-EoC SAVE_DATA: {report['output']['sha256']} "
        f"-> {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
