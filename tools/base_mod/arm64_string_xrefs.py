"""Find simple AArch64 ADRP+ADD references to exact ELF strings.

This is a dependency-free reconnaissance helper for the pinned JP 15.7.1
libnative binary. It deliberately recognizes only a narrow, auditable address
materialization pattern instead of pretending to be a general disassembler.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct

from tools.base_mod.elf_anchor import EM_AARCH64, elf_machine


def _section_table(data: bytes) -> dict[str, dict]:
    if elf_machine(data) != EM_AARCH64:
        raise ValueError("expected AArch64 ELF")

    shoff = struct.unpack_from("<Q", data, 40)[0]
    shentsize = struct.unpack_from("<H", data, 58)[0]
    shnum = struct.unpack_from("<H", data, 60)[0]
    shstrndx = struct.unpack_from("<H", data, 62)[0]
    if shentsize < 64:
        raise ValueError("ELF section header size is too small")
    if shoff + shentsize * shnum > len(data):
        raise ValueError("truncated ELF section table")
    if shstrndx >= shnum:
        raise ValueError("invalid section-name string table index")

    def raw_header(index: int) -> tuple[int, int, int, int, int]:
        off = shoff + index * shentsize
        name_index = struct.unpack_from("<I", data, off)[0]
        address = struct.unpack_from("<Q", data, off + 16)[0]
        file_offset = struct.unpack_from("<Q", data, off + 24)[0]
        size = struct.unpack_from("<Q", data, off + 32)[0]
        flags = struct.unpack_from("<Q", data, off + 8)[0]
        return name_index, address, file_offset, size, flags

    _, _, names_offset, names_size, _ = raw_header(shstrndx)
    if names_offset + names_size > len(data):
        raise ValueError("truncated ELF section-name string table")
    names = data[names_offset:names_offset + names_size]

    result: dict[str, dict] = {}
    for index in range(shnum):
        name_index, address, file_offset, size, flags = raw_header(index)
        if name_index >= len(names):
            raise ValueError("section name offset out of range")
        end = names.find(b"\0", name_index)
        if end < 0:
            raise ValueError("unterminated section name")
        name = names[name_index:end].decode("utf-8", "replace")
        result[name] = {
            "index": index,
            "address": address,
            "offset": file_offset,
            "size": size,
            "flags": flags,
        }
    return result


def _sign_extend(value: int, bits: int) -> int:
    sign = 1 << (bits - 1)
    return value - (1 << bits) if value & sign else value


def _decode_adrp(instruction: int, pc: int) -> tuple[int, int] | None:
    if instruction & 0x9F000000 != 0x90000000:
        return None
    immlo = (instruction >> 29) & 0x3
    immhi = (instruction >> 5) & 0x7FFFF
    immediate = _sign_extend((immhi << 2) | immlo, 21) << 12
    page = (pc & ~0xFFF) + immediate
    rd = instruction & 0x1F
    return page, rd


def _decode_add_immediate(
    instruction: int,
) -> tuple[int, int, int] | None:
    # ADD (immediate), 32/64 bit, excluding SUB and flag-setting variants.
    if instruction & 0x1F000000 != 0x11000000:
        return None
    if (instruction >> 30) & 0x1:
        return None
    if (instruction >> 29) & 0x1:
        return None

    rn = (instruction >> 5) & 0x1F
    rd = instruction & 0x1F
    immediate = (instruction >> 10) & 0xFFF
    if (instruction >> 22) & 0x1:
        immediate <<= 12
    return rn, rd, immediate


def string_addresses(data: bytes, value: bytes) -> list[int]:
    sections = _section_table(data)
    rodata = sections.get(".rodata")
    if rodata is None:
        raise ValueError("ELF has no .rodata section")

    start = rodata["offset"]
    size = rodata["size"]
    address = rodata["address"]
    if start + size > len(data):
        raise ValueError("truncated .rodata section")

    blob = data[start:start + size]
    result: list[int] = []
    cursor = 0
    while True:
        found = blob.find(value, cursor)
        if found < 0:
            break
        result.append(address + found)
        cursor = found + 1
    return result


def find_adrp_add_xrefs(
    data: bytes,
    target_address: int,
    *,
    max_following_instructions: int = 5,
) -> list[dict]:
    sections = _section_table(data)
    text = sections.get(".text")
    if text is None:
        raise ValueError("ELF has no .text section")

    start = text["offset"]
    size = text["size"]
    address = text["address"]
    if start + size > len(data):
        raise ValueError("truncated .text section")

    blob = data[start:start + size]
    result: list[dict] = []
    for offset in range(0, len(blob) - 4, 4):
        instruction = struct.unpack_from("<I", blob, offset)[0]
        pc = address + offset
        adrp = _decode_adrp(instruction, pc)
        if adrp is None:
            continue
        page, adrp_rd = adrp

        for step in range(1, max_following_instructions + 1):
            next_offset = offset + step * 4
            if next_offset + 4 > len(blob):
                break
            next_instruction = struct.unpack_from("<I", blob, next_offset)[0]
            add = _decode_add_immediate(next_instruction)
            if add is None:
                continue
            rn, add_rd, immediate = add
            if rn != adrp_rd:
                continue
            if page + immediate != target_address:
                continue
            result.append(
                {
                    "adrp_address": pc,
                    "add_address": address + next_offset,
                    "adrp_register": adrp_rd,
                    "add_destination_register": add_rd,
                    "distance_in_instructions": step,
                }
            )
    return result


def analyze_string(data: bytes, text: str) -> dict:
    encoded = text.encode("utf-8")
    addresses = string_addresses(data, encoded)
    return {
        "string": text,
        "occurrences": [
            {
                "address": address,
                "xrefs": find_adrp_add_xrefs(data, address),
            }
            for address in addresses
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("elf", type=Path)
    parser.add_argument("--string", action="append", dest="strings", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    data = args.elf.read_bytes()
    report = {
        "schema_version": 1,
        "elf": str(args.elf),
        "results": [analyze_string(data, value) for value in args.strings],
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
