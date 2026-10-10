"""Read-only exact JP15.7.1 native function-boundary / file-loader receipt.

Not a disassembler, native patch, combat hook locator or claim of battle parity.
Uses pinned owner ARM64 SHA, exact .eh_frame_hdr PC ranges, and ADRP+ADD literal
references to delimit *file-loading* functions for future device tracing.
"""
from __future__ import annotations
import argparse
from bisect import bisect_right
import hashlib
import json
from pathlib import Path
import struct

NATIVE_SHA256 = "333d2974ab2ff881fd70087fd62dea7d12d82addbc55cab2f2a675ad67e3a7e2"
HDR_OFFSET = 0x1FDA44
CODE_BEGIN = 0x317370
CODE_END = 0xAD751C
KNOWN = {
    "DataLocal.pack": (0x714AE8, 0x719044, 0x7157E8),
    "DownloadLocal.list": (0x71C408, 0x71DCF4, 0x71C6F8),
    "DownloadLocal.pack": (0x71C408, 0x71DCF4, 0x71C714),
    "t_unit.csv": (0x8A3624, 0x8A3900, 0x8A3678),
    "enemyCastleData0.csv": (0x553258, 0x55378C, 0x553348),
}


def frame_starts(blob: bytes, offset: int = HDR_OFFSET) -> list[int]:
    if len(blob) < offset + 12 or blob[offset:offset+4] != b"\x01\x1b\x03\x3b":
        raise ValueError("unexpected .eh_frame_hdr encoding")
    count = struct.unpack_from("<I", blob, offset+8)[0]
    if not 1 <= count <= 100000 or offset+12+8*count > len(blob):
        raise ValueError("unexpected frame table count/size")
    starts = [
        offset + struct.unpack_from("<i", blob, offset+12+8*i)[0]
        for i in range(count)
    ]
    if starts != sorted(set(starts)):
        raise ValueError("invalid or duplicated frame function starts")
    return starts


def function_bounds(pc: int, starts: list[int]) -> tuple[int, int]:
    idx = bisect_right(starts, pc) - 1
    if idx < 0 or idx + 1 >= len(starts):
        raise ValueError("instruction outside bounded frame table")
    return starts[idx], starts[idx+1]


def _page_target(pc: int, word: int) -> int:
    imm = (((word >> 5) & 0x7ffff) << 2) | ((word >> 29) & 3)
    if imm & 0x100000:
        imm -= 0x200000
    return (pc & ~0xfff) + (imm << 12)


def find_references(blob: bytes, targets: dict[str, int], *,
                    code_begin: int, code_end: int) -> dict[str, list[int]]:
    pages: dict[int, list[tuple[str, int]]] = {}
    for name, addr in targets.items():
        pages.setdefault(addr & ~0xfff, []).append((name, addr))
    refs = {name: [] for name in targets}
    for pc in range(code_begin, code_end - 24, 4):
        word = struct.unpack_from("<I", blob, pc)[0]
        if word & 0x9f000000 != 0x90000000:
            continue
        page = _page_target(pc, word)
        if page not in pages:
            continue
        rd = word & 31
        for steps in range(1, 7):
            add = struct.unpack_from("<I", blob, pc + 4*steps)[0]
            if (add & 0xffc00000) != 0x91000000 or ((add >> 5) & 31) != rd:
                continue
            referenced = page + ((add >> 10) & 4095)
            for name, addr in pages[page]:
                if referenced == addr:
                    refs[name].append(pc)
    return refs


def audit_owner_binary(blob: bytes) -> dict:
    if hashlib.sha256(blob).hexdigest() != NATIVE_SHA256:
        raise ValueError("not the pinned JP15.7.1 original native binary")
    starts = frame_starts(blob)
    if starts[0] != CODE_BEGIN or len(starts) != 23086:
        raise ValueError("unexpected original native unwind bounds")
    strings = {name: blob.find(name.encode()) for name in KNOWN}
    if any(pos < 0 for pos in strings.values()):
        raise ValueError("pinned loader strings missing")
    refs = find_references(blob, strings, code_begin=CODE_BEGIN, code_end=CODE_END)
    evidence = {}
    for name, (expected_start, expected_end, expected_pc) in KNOWN.items():
        if refs[name] != [expected_pc]:
            raise ValueError("literal reference drift: " + name)
        func_start, func_end = function_bounds(expected_pc, starts)
        if (func_start, func_end) != (expected_start, expected_end):
            raise ValueError("unwind function boundary drift: " + name)
        evidence[name] = {
            "string_offset": hex(strings[name]),
            "reference_instruction": hex(expected_pc),
            "unwind_function_range": [hex(func_start), hex(func_end)],
            "classification": "source-data-loader-only-not-a-proven-gameplay-hook",
        }
    return {
        "schema_version": 1,
        "anchor": "owner-JP15.7.1-ARM64",
        "native_sha256": NATIVE_SHA256,
        "frame_function_count": len(starts),
        "read_only": True,
        "device_traced": False,
        "combat_hit_function_identified": False,
        "castle_hp_debit_function_identified": False,
        "native_patch_permitted": False,
        "references": evidence,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit_owner_binary(args.native.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print("verified loader functions:", len(report["references"]), "; no combat hook proof")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())