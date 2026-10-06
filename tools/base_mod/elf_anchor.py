"""Small ELF anchor helpers used before native mutation."""

from __future__ import annotations

import struct


PT_NOTE = 4
EM_AARCH64 = 183


def elf_machine(data: bytes) -> int:
    if len(data) < 64 or data[:4] != b"\x7fELF":
        raise ValueError("not an ELF file")
    if data[4] != 2 or data[5] != 1:
        raise ValueError("expected 64-bit little-endian ELF")
    return struct.unpack_from("<H", data, 18)[0]


def gnu_build_id(data: bytes) -> str | None:
    if elf_machine(data) < 0:
        return None

    phoff = struct.unpack_from("<Q", data, 32)[0]
    phentsize = struct.unpack_from("<H", data, 54)[0]
    phnum = struct.unpack_from("<H", data, 56)[0]

    for index in range(phnum):
        off = phoff + index * phentsize
        if off + 56 > len(data):
            raise ValueError("truncated ELF program header")
        p_type = struct.unpack_from("<I", data, off)[0]
        if p_type != PT_NOTE:
            continue
        p_offset = struct.unpack_from("<Q", data, off + 8)[0]
        p_filesz = struct.unpack_from("<Q", data, off + 32)[0]
        cursor = p_offset
        end = p_offset + p_filesz
        if end > len(data):
            raise ValueError("truncated ELF note segment")

        while cursor + 12 <= end:
            namesz, descsz, note_type = struct.unpack_from("<III", data, cursor)
            cursor += 12
            name_end = cursor + namesz
            if name_end > end:
                break
            name = data[cursor:name_end].rstrip(b"\x00")
            cursor = (name_end + 3) & ~3

            desc_end = cursor + descsz
            if desc_end > end:
                break
            desc = data[cursor:desc_end]
            cursor = (desc_end + 3) & ~3

            if note_type == 3 and name == b"GNU":
                return desc.hex()
    return None