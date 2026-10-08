"""Read-only Battle Cats SAVE_DATA envelope inspector.

This intentionally parses only the stable prefix corroborated by current
BCSFE-Python prior art and validates the JP salted-MD5 trailer. It performs no
mutation and is suitable for checking a pulled baseline before any bootstrap
work.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct


JP_SAVE_SALT = b"battlecats"
HASH_HEX_LEN = 32


def _read_i32(data: bytes, offset: int) -> tuple[int, int]:
    if offset + 4 > len(data):
        raise ValueError("truncated i32")
    return struct.unpack_from("<i", data, offset)[0], offset + 4


def _read_i8(data: bytes, offset: int) -> tuple[int, int]:
    if offset + 1 > len(data):
        raise ValueError("truncated i8")
    return struct.unpack_from("<b", data, offset)[0], offset + 1


def _read_f64(data: bytes, offset: int) -> tuple[float, int]:
    if offset + 8 > len(data):
        raise ValueError("truncated f64")
    return struct.unpack_from("<d", data, offset)[0], offset + 8


def inspect_save_bytes(data: bytes) -> dict:
    if len(data) < HASH_HEX_LEN + 4:
        raise ValueError("SAVE_DATA is too small")

    payload = data[:-HASH_HEX_LEN]
    trailer = data[-HASH_HEX_LEN:]
    try:
        trailer_text = trailer.decode("ascii")
    except UnicodeDecodeError:
        trailer_text = ""

    trailer_is_hex = (
        len(trailer_text) == HASH_HEX_LEN
        and all(ch in "0123456789abcdefABCDEF" for ch in trailer_text)
    )
    expected_hash = hashlib.md5(JP_SAVE_SALT + payload).hexdigest()
    hash_valid = trailer_is_hex and trailer_text.lower() == expected_hash

    offset = 0
    game_version, offset = _read_i32(payload, offset)

    # BCSFE-Python's modern JP parser reads a one-byte ub1 for gv >= 10,
    # followed by mute_bgm, mute_se, catfood and current energy.
    prefix = {"game_version": game_version}
    if game_version >= 10:
        ub1, offset = _read_i8(payload, offset)
        prefix["ub1"] = bool(ub1)

    mute_bgm, offset = _read_i8(payload, offset)
    mute_se, offset = _read_i8(payload, offset)
    catfood, offset = _read_i32(payload, offset)
    current_energy, offset = _read_i32(payload, offset)

    # Stable date/timestamp prefix up through tutorial-state fields.
    year_a, offset = _read_i32(payload, offset)
    year_b, offset = _read_i32(payload, offset)
    month_a, offset = _read_i32(payload, offset)
    month_b, offset = _read_i32(payload, offset)
    day_a, offset = _read_i32(payload, offset)
    day_b, offset = _read_i32(payload, offset)
    timestamp, offset = _read_f64(payload, offset)
    hour, offset = _read_i32(payload, offset)
    minute, offset = _read_i32(payload, offset)
    second, offset = _read_i32(payload, offset)

    # read_dst() is version/state dependent and not duplicated here. Stop the
    # semantic prefix at this safe boundary rather than guessing later offsets.
    prefix.update(
        {
            "mute_bgm": bool(mute_bgm),
            "mute_se": bool(mute_se),
            "catfood": catfood,
            "current_energy": current_energy,
            "date_prefix": {
                "year_primary": year_a,
                "year_secondary": year_b,
                "month_primary": month_a,
                "month_secondary": month_b,
                "day_primary": day_a,
                "day_secondary": day_b,
                "hour": hour,
                "minute": minute,
                "second": second,
                "timestamp": timestamp,
            },
            "parsed_prefix_bytes": offset,
        }
    )

    return {
        "schema_version": 1,
        "mode": "battlecats-save-readonly-envelope",
        "file_size": len(data),
        "payload_size": len(payload),
        "hash_trailer_ascii_hex": trailer_is_hex,
        "stored_hash": trailer_text.lower() if trailer_is_hex else None,
        "expected_jp_hash": expected_hash,
        "jp_hash_valid": hash_valid,
        "prefix": prefix,
        "mutation_attempted": False,
    }


def inspect_file(path: Path) -> dict:
    result = inspect_save_bytes(path.read_bytes())
    result["path"] = str(path.resolve())
    result["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("save_data", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = inspect_file(args.save_data)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result["jp_hash_valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
