"""Minimal dependency-free DEX method-definition scanner.

Used to pin exact Java bridge signatures without decompiling or committing APK
payloads.  It reads method definitions (not merely method-id references) from
class_data_item records.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import zipfile


NO_INDEX = 0xFFFFFFFF


def _u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def _u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def _uleb128(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    shift = 0
    for _ in range(5):
        if offset >= len(data):
            raise ValueError("truncated uleb128")
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if byte < 0x80:
            return value, offset
        shift += 7
    raise ValueError("uleb128 exceeds 5 bytes")


def _strings(data: bytes) -> list[str]:
    size = _u32(data, 0x38)
    offset = _u32(data, 0x3C)
    result: list[str] = []
    for index in range(size):
        string_offset = _u32(data, offset + index * 4)
        _, cursor = _uleb128(data, string_offset)
        end = data.find(b"\0", cursor)
        if end < 0:
            raise ValueError("unterminated dex string")
        result.append(data[cursor:end].decode("utf-8", "replace"))
    return result


def defined_methods(data: bytes, class_descriptor: str) -> list[dict]:
    if data[:8] not in {
        b"dex\n035\0",
        b"dex\n036\0",
        b"dex\n037\0",
        b"dex\n038\0",
        b"dex\n039\0",
        b"dex\n040\0",
        b"dex\n041\0",
    }:
        raise ValueError("unsupported or invalid DEX magic")

    strings = _strings(data)

    type_size = _u32(data, 0x40)
    type_off = _u32(data, 0x44)
    types = [strings[_u32(data, type_off + index * 4)] for index in range(type_size)]

    proto_size = _u32(data, 0x48)
    proto_off = _u32(data, 0x4C)
    protos: list[dict] = []
    for index in range(proto_size):
        item = proto_off + index * 12
        shorty_idx = _u32(data, item)
        return_type_idx = _u32(data, item + 4)
        parameters_off = _u32(data, item + 8)
        parameters: list[str] = []
        if parameters_off:
            count = _u32(data, parameters_off)
            for param_index in range(count):
                type_idx = _u16(data, parameters_off + 4 + param_index * 2)
                parameters.append(types[type_idx])
        protos.append(
            {
                "shorty": strings[shorty_idx],
                "return": types[return_type_idx],
                "parameters": parameters,
            }
        )

    method_size = _u32(data, 0x58)
    method_off = _u32(data, 0x5C)
    methods: list[dict] = []
    for index in range(method_size):
        item = method_off + index * 8
        class_idx = _u16(data, item)
        proto_idx = _u16(data, item + 2)
        name_idx = _u32(data, item + 4)
        methods.append(
            {
                "method_idx": index,
                "class": types[class_idx],
                "name": strings[name_idx],
                "proto": protos[proto_idx],
            }
        )

    class_defs_size = _u32(data, 0x60)
    class_defs_off = _u32(data, 0x64)
    target_def = None
    for index in range(class_defs_size):
        item = class_defs_off + index * 32
        class_idx = _u32(data, item)
        if types[class_idx] == class_descriptor:
            target_def = {
                "class_idx": class_idx,
                "access_flags": _u32(data, item + 4),
                "class_data_off": _u32(data, item + 24),
            }
            break

    if target_def is None:
        return []
    class_data_off = target_def["class_data_off"]
    if class_data_off == 0:
        return []

    cursor = class_data_off
    static_fields_size, cursor = _uleb128(data, cursor)
    instance_fields_size, cursor = _uleb128(data, cursor)
    direct_methods_size, cursor = _uleb128(data, cursor)
    virtual_methods_size, cursor = _uleb128(data, cursor)

    for field_count in (static_fields_size, instance_fields_size):
        field_idx = 0
        for _ in range(field_count):
            diff, cursor = _uleb128(data, cursor)
            field_idx += diff
            _, cursor = _uleb128(data, cursor)

    result: list[dict] = []
    for kind, count in (
        ("direct", direct_methods_size),
        ("virtual", virtual_methods_size),
    ):
        method_idx = 0
        for _ in range(count):
            diff, cursor = _uleb128(data, cursor)
            method_idx += diff
            access_flags, cursor = _uleb128(data, cursor)
            code_off, cursor = _uleb128(data, cursor)

            if method_idx >= len(methods):
                raise ValueError("class_data method index out of bounds")
            row = methods[method_idx]
            if row["class"] != class_descriptor:
                raise ValueError("class_data references method from another class")
            result.append(
                {
                    **row,
                    "kind": kind,
                    "access_flags": access_flags,
                    "code_off": code_off,
                }
            )

    return result


def scan_apk(
    apk_path: Path,
    *,
    class_descriptor: str,
    names: set[str] | None = None,
) -> list[dict]:
    records: list[dict] = []
    with zipfile.ZipFile(apk_path, "r") as archive:
        dex_names = sorted(
            name
            for name in archive.namelist()
            if name.startswith("classes") and name.endswith(".dex")
        )
        for dex_name in dex_names:
            for row in defined_methods(archive.read(dex_name), class_descriptor):
                if names is not None and row["name"] not in names:
                    continue
                records.append({"dex": dex_name, **row})
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--class-descriptor", required=True)
    parser.add_argument("--name", action="append", dest="names")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = scan_apk(
        args.apk.resolve(),
        class_descriptor=args.class_descriptor,
        names=set(args.names) if args.names else None,
    )
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
