"""Build the exact JP 15.7.1 one-time offline MAX research SAVE_DATA.

This tool is intentionally fail-closed:
- it accepts only the exact device baseline captured on 2026-10-07;
- it verifies the original JP salted-MD5 trailer;
- it derives eligible cats and drop-save IDs from the exact owned DataLocal;
- it patches only independently mapped SAVE_DATA fields;
- it writes a new file and never touches the source SAVE_DATA.

The field map was independently cross-checked against pinned BCSFE-Python
3.6.0 (commit 85fb94cbf00c6a74dbef58932610fb94ec8f7495) by a zero-diff
round-trip and one-field-at-a-time differential serialization. No BCSFE source
code is included or required at runtime.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
from typing import Any

from tools.battlecats_source import BattleCatsExport
from tools.base_mod.build_offline_profile_unit_manifest import build_manifest


BASELINE_SHA256 = "cad00e84f3d64910b623b8a89b57ae1a37e8947554f4b418f50efa1c6bdc1d3c"
BASELINE_SIZE = 496_340
JP_SALT = b"battlecats"
HASH_LEN = 32
EXPORT_SHA256 = "38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56"

TALENT_ORB_COUNT_OFFSET = 483_324
TALENT_ORB_DATA_OFFSET = 483_326
TALENT_ORB_COUNT = 310
TALENT_ORB_VALUE = 998
TALENT_ORB_RECORD_SIZE = 4
TALENT_ORB_INSERT_BYTES = TALENT_ORB_COUNT * TALENT_ORB_RECORD_SIZE

# Exact baseline field map, proven by differential serialization against the
# pinned parser and re-read from the real JP 15.7.1 research SAVE_DATA.
I32 = {
    "catfood": 7,
    "xp": 75,
    "tutorial_state": 79,
    "korea_superior_treasure_state": 87,
    "ui6": 111,
    "story_chapter0_progress": 1145,
    "story_chapter0_stage0_clear": 1185,
    "menu_unlock_equip": 19049,
    "new_dialog_1": 19145,
    "new_dialog_5": 19161,
    "normal_tickets": 19839,
    "rare_tickets": 19843,
    "platinum_tickets": 398140,
    "np": 451687,
    "legend_tickets": 483481,
    "platinum_shards": 483703,
    "hundred_million_ticket": 495780,
    "engineers": 399146,
}
I16 = {
    "leadership": 451697,
}

ARRAYS_I32 = {
    "cat_unlocked": (8401, 882, 8397),
    "cat_current_form": (15465, 882, 15461),
    "battle_items": (19113, 6, None),
    "cat_gatya_seen": (19851, 882, 19847),
    "unit_drops": (294606, 400, 294602),
    "cat_unlocked_forms": (310322, 882, 310318),
    "catfruit": (385884, 29, 385880),
    "cat_fourth_form": (386004, 882, 386000),
    "catseyes": (393068, 6, 393064),
    "catamins": (393096, 3, 393092),
    "base_materials": (399069, 16, 399065),
    "lucky_tickets": (439776, 55, 439772),
    "treasure_chests": (495797, 42, None),  # u8 count at 495796
}
ARRAYS_I16 = {
    "labyrinth_medals": (484928, 4, None),  # u8 count at 484927
}

MAX_VALUES = {
    # Exact-native-confirmed.
    "xp": 99_999_999,
    # Current BCSFE/community editor policy caps; kept explicit so they can be
    # revised independently if a stricter exact-native local cap is proven.
    "catfood": 45_000,
    "normal_tickets": 2_999,
    "rare_tickets": 299,
    "platinum_tickets": 9,
    "legend_tickets": 4,
    "platinum_shards": 9,
    "np": 9_999,
    "leadership": 9_999,
    "battle_items": 9_999,
    "catfruit": 998,
    "catseyes": 9_999,
    "catamins": 9_999,
    "base_materials": 9_999,
    "lucky_tickets": 9_999,
    "labyrinth_medals": 9_999,
    "hundred_million_ticket": 9_999,
    "treasure_chests": 9_999,
    "talent_orbs": TALENT_ORB_VALUE,
    "engineers": 5,
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_i32(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from("<i", data, offset)[0]


def _write_i32(data: bytearray, offset: int, value: int) -> None:
    struct.pack_into("<i", data, offset, int(value))


def _read_i16(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from("<h", data, offset)[0]


def _write_i16(data: bytearray, offset: int, value: int) -> None:
    struct.pack_into("<h", data, offset, int(value))


def _verify_jp_hash(data: bytes) -> tuple[str, str]:
    if len(data) < HASH_LEN:
        raise ValueError("SAVE_DATA is too small")
    try:
        stored = data[-HASH_LEN:].decode("ascii").lower()
    except UnicodeDecodeError as exc:
        raise ValueError("SAVE_DATA hash trailer is not ASCII") from exc
    if len(stored) != HASH_LEN or any(ch not in "0123456789abcdef" for ch in stored):
        raise ValueError("SAVE_DATA hash trailer is not 32 hex chars")
    expected = hashlib.md5(JP_SALT + data[:-HASH_LEN]).hexdigest()
    if stored != expected:
        raise ValueError(f"JP SAVE_DATA hash mismatch: {stored} != {expected}")
    return stored, expected


def _rewrite_hash(data: bytearray) -> str:
    digest = hashlib.md5(JP_SALT + bytes(data[:-HASH_LEN])).hexdigest()
    data[-HASH_LEN:] = digest.encode("ascii")
    return digest


def _assert_i32_count(data: bytes, name: str, expected: int) -> None:
    start, length, count_offset = ARRAYS_I32[name]
    if count_offset is None:
        return
    actual = _read_i32(data, count_offset)
    if actual != expected or length != expected:
        raise ValueError(f"{name} count mismatch: save={actual}, map={length}, expected={expected}")


def _derive_unit_contract(export: Path) -> tuple[list[int], list[int], dict[str, Any]]:
    manifest = build_manifest(export, expected_sha256=EXPORT_SHA256)
    eligible = [int(item["asset_id"]) for item in manifest["eligible_units"]]

    with BattleCatsExport(
        export,
        expected_sha256=EXPORT_SHA256,
        region="jp",
    ) as source:
        data_local = source.pack("DataLocal")
        drop_payload, drop_provenance = data_local.read("drop_chara.csv")
        equipment_payload, equipment_provenance = data_local.read("equipmentlist.json")
        castle_limit_payload, castle_limit_provenance = data_local.read("CastleCustomLimit.csv")

    drop_rows = list(csv.reader(io.StringIO(drop_payload.decode("utf-8-sig", "replace"))))
    drop_save_ids: set[int] = set()
    eligible_set = set(eligible)
    for row in drop_rows[1:]:
        if len(row) < 3:
            continue
        try:
            save_id = int(row[1])
            chara_id = int(row[2])
        except ValueError:
            continue
        if chara_id in eligible_set and 0 <= save_id < ARRAYS_I32["unit_drops"][1]:
            drop_save_ids.add(save_id)

    equipment_document = json.loads(equipment_payload.decode("utf-8-sig"))
    equipment_ids = equipment_document.get("ID")
    if not isinstance(equipment_ids, list) or len(equipment_ids) != TALENT_ORB_COUNT:
        raise ValueError(
            f"unexpected equipmentlist.json orb count: "
            f"{len(equipment_ids) if isinstance(equipment_ids, list) else 'invalid'}"
        )

    castle_limit_rows = list(
        csv.reader(io.StringIO(castle_limit_payload.decode("utf-8-sig", "replace")))
    )
    try:
        exact_engineer_max = int(castle_limit_rows[0][0])
    except (IndexError, ValueError) as exc:
        raise ValueError("invalid CastleCustomLimit.csv") from exc
    if exact_engineer_max != MAX_VALUES["engineers"]:
        raise ValueError(
            f"unexpected exact engineer max: {exact_engineer_max} != "
            f"{MAX_VALUES['engineers']}"
        )

    evidence = {
        "eligible_count": len(eligible),
        "eligible_ids_sha256": hashlib.sha256(
            ",".join(str(v) for v in eligible).encode("ascii")
        ).hexdigest(),
        "drop_save_id_count": len(drop_save_ids),
        "drop_chara_sha256": drop_provenance.payload_sha256,
        "talent_orb_count": len(equipment_ids),
        "equipmentlist_sha256": equipment_provenance.payload_sha256,
        "engineer_max": exact_engineer_max,
        "castle_custom_limit_sha256": castle_limit_provenance.payload_sha256,
    }
    return eligible, sorted(drop_save_ids), evidence


def build_max_save(source: bytes, export: Path) -> tuple[bytes, dict[str, Any]]:
    if len(source) != BASELINE_SIZE:
        raise ValueError(f"unexpected SAVE_DATA size: {len(source)} != {BASELINE_SIZE}")
    source_sha = _sha256(source)
    if source_sha != BASELINE_SHA256:
        raise ValueError(
            "input SAVE_DATA is not the exact captured bootstrap baseline; "
            f"sha256={source_sha}"
        )

    stored_md5, expected_md5 = _verify_jp_hash(source)
    if _read_i32(source, 0) != 150700:
        raise ValueError("unexpected SAVE_DATA game version")

    for name, expected in (
        ("cat_unlocked", 882),
        ("cat_current_form", 882),
        ("cat_gatya_seen", 882),
        ("unit_drops", 400),
        ("cat_unlocked_forms", 882),
        ("catfruit", 29),
        ("cat_fourth_form", 882),
        ("catseyes", 6),
        ("catamins", 3),
        ("base_materials", 16),
        ("lucky_tickets", 55),
    ):
        _assert_i32_count(source, name, expected)

    if source[484927] != 4:
        raise ValueError(f"labyrinth medal count mismatch: {source[484927]}")
    if source[495796] != 42:
        raise ValueError(f"treasure chest count mismatch: {source[495796]}")

    eligible, drop_save_ids, contract = _derive_unit_contract(export)
    if len(eligible) != 835:
        raise ValueError(f"unexpected eligible cat count: {len(eligible)}")

    out = bytearray(source)

    # Minimal tutorial escape as independently corroborated by the parser.
    _write_i32(out, I32["tutorial_state"], 1)
    _write_i32(out, I32["korea_superior_treasure_state"], 2)
    _write_i32(out, I32["ui6"], 1)
    _write_i32(out, I32["story_chapter0_progress"], 1)
    _write_i32(out, I32["story_chapter0_stage0_clear"], 1)
    _write_i32(out, I32["new_dialog_1"], 2)
    _write_i32(out, I32["new_dialog_5"], 2)
    _write_i32(out, I32["menu_unlock_equip"], 1)

    # First-form ownership. Hidden/internal/test/regional rows remain untouched.
    unlocked_base = ARRAYS_I32["cat_unlocked"][0]
    current_form_base = ARRAYS_I32["cat_current_form"][0]
    gacha_seen_base = ARRAYS_I32["cat_gatya_seen"][0]
    unlocked_forms_base = ARRAYS_I32["cat_unlocked_forms"][0]
    fourth_form_base = ARRAYS_I32["cat_fourth_form"][0]
    for cat_id in eligible:
        _write_i32(out, unlocked_base + cat_id * 4, 1)
        _write_i32(out, gacha_seen_base + cat_id * 4, 1)
        _write_i32(out, current_form_base + cat_id * 4, 0)
        _write_i32(out, unlocked_forms_base + cat_id * 4, 0)
        _write_i32(out, fourth_form_base + cat_id * 4, 0)

    unit_drop_base = ARRAYS_I32["unit_drops"][0]
    for save_id in drop_save_ids:
        _write_i32(out, unit_drop_base + save_id * 4, 1)

    # Scalar resources.
    for name in (
        "catfood",
        "xp",
        "normal_tickets",
        "rare_tickets",
        "platinum_tickets",
        "legend_tickets",
        "platinum_shards",
        "np",
        "hundred_million_ticket",
        "engineers",
    ):
        _write_i32(out, I32[name], MAX_VALUES[name])
    _write_i16(out, I16["leadership"], MAX_VALUES["leadership"])

    # Array resources.
    for name in (
        "battle_items",
        "catfruit",
        "catseyes",
        "catamins",
        "base_materials",
        "lucky_tickets",
        "treasure_chests",
    ):
        start, length, _ = ARRAYS_I32[name]
        value = MAX_VALUES[name]
        for i in range(length):
            _write_i32(out, start + i * 4, value)

    start, length, _ = ARRAYS_I16["labyrinth_medals"]
    for i in range(length):
        _write_i16(out, start + i * 2, MAX_VALUES["labyrinth_medals"])

    # Talent Orbs are a variable-length section. The exact baseline contains a
    # zero short count at 483,324 and no records. For JP 15.7.1 each record is
    # short id + short count. Insert all 310 exact equipmentlist.json IDs with
    # the storage-safe/current editor cap of 998.
    if _read_i16(out, TALENT_ORB_COUNT_OFFSET) != 0:
        raise ValueError("baseline talent orb section is not empty as expected")
    _write_i16(out, TALENT_ORB_COUNT_OFFSET, TALENT_ORB_COUNT)
    talent_payload = b"".join(
        struct.pack("<hh", orb_id, TALENT_ORB_VALUE)
        for orb_id in range(TALENT_ORB_COUNT)
    )
    if len(talent_payload) != TALENT_ORB_INSERT_BYTES:
        raise AssertionError("unexpected talent orb payload length")
    out[TALENT_ORB_DATA_OFFSET:TALENT_ORB_DATA_OFFSET] = talent_payload

    new_md5 = _rewrite_hash(out)
    built = bytes(out)
    _verify_jp_hash(built)

    report = {
        "schema_version": 1,
        "mode": "offline-max-profile-exact-baseline-transform",
        "anchor": "jp-15.7.1",
        "source": {
            "size": len(source),
            "sha256": source_sha,
            "jp_md5": stored_md5,
        },
        "output": {
            "size": len(built),
            "sha256": _sha256(built),
            "jp_md5": new_md5,
        },
        "unit_contract": contract,
        "first_form_contract": {
            "eligible_owned": 835,
            "current_form": 0,
            "unlocked_forms": 0,
            "fourth_form": 0,
            "drop_save_ids_enabled": len(drop_save_ids),
        },
        "talent_orbs": {
            "count": TALENT_ORB_COUNT,
            "value_each": TALENT_ORB_VALUE,
            "inserted_bytes": TALENT_ORB_INSERT_BYTES,
        },
        "tutorial": {
            "minimal_clear": True,
            "full_story_clear": False,
        },
        "max_values": MAX_VALUES,
        "integrity": {
            "input_jp_hash_valid": stored_md5 == expected_md5,
            "output_jp_hash_valid": True,
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
        source = args.save_data.read_bytes()
        built, report = build_max_save(source, args.owned_export)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"offline max save build failed: {exc}", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(built)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"built offline MAX SAVE_DATA: {report['output']['sha256']} -> {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
