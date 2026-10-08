"""Extract exact method/type/field/string references from standard DEX code items.

This is a narrow reconnaissance helper, not a general decompiler. It walks
standard Dalvik instructions, resolves reference-bearing instructions, and
fails closed on malformed code. It is used to pin the original JP 15.7.1
MyActivity HTTP transport chain without committing DEX bytes.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import zipfile

from tools.base_mod.dex_methods import (
    _strings,
    _u16,
    _u32,
    defined_methods,
)


def _dex_tables(data: bytes) -> tuple[list[str], list[str], list[tuple], list[tuple]]:
    strings = _strings(data)

    type_size = _u32(data, 0x40)
    type_off = _u32(data, 0x44)
    types = [
        strings[_u32(data, type_off + index * 4)]
        for index in range(type_size)
    ]

    proto_size = _u32(data, 0x48)
    proto_off = _u32(data, 0x4C)
    protos: list[tuple[str, list[str]]] = []
    for index in range(proto_size):
        item = proto_off + index * 12
        return_type_idx = _u32(data, item + 4)
        parameters_off = _u32(data, item + 8)
        parameters: list[str] = []
        if parameters_off:
            count = _u32(data, parameters_off)
            for param_index in range(count):
                type_idx = _u16(data, parameters_off + 4 + param_index * 2)
                parameters.append(types[type_idx])
        protos.append((types[return_type_idx], parameters))

    method_size = _u32(data, 0x58)
    method_off = _u32(data, 0x5C)
    methods: list[tuple[str, str, str, list[str]]] = []
    for index in range(method_size):
        item = method_off + index * 8
        class_idx = _u16(data, item)
        proto_idx = _u16(data, item + 2)
        name_idx = _u32(data, item + 4)
        return_type, parameters = protos[proto_idx]
        methods.append(
            (
                types[class_idx],
                strings[name_idx],
                return_type,
                parameters,
            )
        )

    field_size = _u32(data, 0x50)
    field_off = _u32(data, 0x54)
    fields: list[tuple[str, str, str]] = []
    for index in range(field_size):
        item = field_off + index * 8
        class_idx = _u16(data, item)
        type_idx = _u16(data, item + 2)
        name_idx = _u32(data, item + 4)
        fields.append(
            (
                types[class_idx],
                strings[name_idx],
                types[type_idx],
            )
        )

    return strings, types, methods, fields


def _payload_width(code_units: list[int], index: int) -> int | None:
    word = code_units[index]
    if word == 0x0100:  # packed-switch-payload
        if index + 2 > len(code_units):
            raise ValueError("truncated packed-switch payload")
        size = code_units[index + 1]
        return 4 + size * 2
    if word == 0x0200:  # sparse-switch-payload
        if index + 2 > len(code_units):
            raise ValueError("truncated sparse-switch payload")
        size = code_units[index + 1]
        return 2 + size * 4
    if word == 0x0300:  # fill-array-data-payload
        if index + 4 > len(code_units):
            raise ValueError("truncated fill-array payload")
        element_width = code_units[index + 1]
        size = code_units[index + 2] | (code_units[index + 3] << 16)
        byte_count = element_width * size
        return 4 + (byte_count + 1) // 2
    return None


def instruction_width(code_units: list[int], index: int) -> int:
    payload = _payload_width(code_units, index)
    if payload is not None:
        return payload

    opcode = code_units[index] & 0xFF

    width_1 = {
        0x00, 0x01, 0x04, 0x07, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E,
        0x0F, 0x10, 0x11, 0x12, 0x1D, 0x1E, 0x21, 0x27, 0x28,
    }
    if opcode in width_1 or 0x7B <= opcode <= 0x8F or 0xB0 <= opcode <= 0xCF:
        return 1

    width_2 = {
        0x02, 0x05, 0x08, 0x13, 0x15, 0x16, 0x19, 0x1A, 0x1C,
        0x1F, 0x20, 0x22, 0x23, 0x29,
    }
    if (
        opcode in width_2
        or 0x2D <= opcode <= 0x3D
        or 0x44 <= opcode <= 0x6D
        or 0x90 <= opcode <= 0xAF
        or 0xD0 <= opcode <= 0xE2
    ):
        return 2

    width_3 = {
        0x03, 0x06, 0x09, 0x14, 0x17, 0x1B, 0x24, 0x25, 0x26,
        0x2A, 0x2B, 0x2C,
    }
    if (
        opcode in width_3
        or 0x6E <= opcode <= 0x72
        or 0x74 <= opcode <= 0x78
        or opcode in {0xFA, 0xFB, 0xFC, 0xFD}
    ):
        return 3

    if opcode == 0x18:
        return 5
    if opcode in {0xFE, 0xFF}:
        return 2

    raise ValueError(f"unsupported DEX opcode 0x{opcode:02x} at code-unit {index}")


def _method_ref(methods: list[tuple], index: int) -> dict:
    owner, name, return_type, parameters = methods[index]
    return {
        "owner": owner,
        "name": name,
        "return": return_type,
        "parameters": parameters,
    }


def _field_ref(fields: list[tuple], index: int) -> dict:
    owner, name, field_type = fields[index]
    return {
        "owner": owner,
        "name": name,
        "type": field_type,
    }


def code_references(data: bytes, method: dict) -> list[dict]:
    code_off = int(method["code_off"])
    if code_off == 0:
        return []

    insns_size = _u32(data, code_off + 12)
    start = code_off + 16
    end = start + insns_size * 2
    if end > len(data):
        raise ValueError("DEX code item extends beyond file")
    code_units = list(
        struct.unpack_from(
            "<" + "H" * insns_size,
            data,
            start,
        )
    )

    strings, types, methods, fields = _dex_tables(data)
    result: list[dict] = []

    index = 0
    while index < len(code_units):
        word = code_units[index]
        opcode = word & 0xFF
        width = instruction_width(code_units, index)
        if index + width > len(code_units):
            raise ValueError("DEX instruction extends beyond code item")

        row: dict = {
            "code_unit": index,
            "file_offset": start + index * 2,
            "opcode": f"0x{opcode:02x}",
        }

        if opcode == 0x1A:  # const-string
            string_idx = code_units[index + 1]
            row["kind"] = "string"
            row["value"] = strings[string_idx]
        elif opcode == 0x1B:  # const-string/jumbo
            string_idx = code_units[index + 1] | (code_units[index + 2] << 16)
            row["kind"] = "string"
            row["value"] = strings[string_idx]
        elif opcode in {0x1C, 0x1F, 0x22}:  # const-class/check-cast/new-instance
            type_idx = code_units[index + 1]
            row["kind"] = "type"
            row["value"] = types[type_idx]
        elif 0x52 <= opcode <= 0x6D:
            field_idx = code_units[index + 1]
            row["kind"] = "field"
            row["value"] = _field_ref(fields, field_idx)
        elif (
            0x6E <= opcode <= 0x72
            or 0x74 <= opcode <= 0x78
        ):
            method_idx = code_units[index + 1]
            row["kind"] = "method"
            row["value"] = _method_ref(methods, method_idx)

        if "kind" in row:
            result.append(row)
        index += width

    return result


def scan_method(
    apk: Path,
    *,
    class_descriptor: str,
    method_name: str,
) -> list[dict]:
    matches: list[dict] = []
    with zipfile.ZipFile(apk, "r") as archive:
        dex_names = sorted(
            name
            for name in archive.namelist()
            if name.startswith("classes") and name.endswith(".dex")
        )
        for dex_name in dex_names:
            data = archive.read(dex_name)
            for method in defined_methods(data, class_descriptor):
                if method["name"] != method_name:
                    continue
                matches.append(
                    {
                        "dex": dex_name,
                        "class": class_descriptor,
                        "method": method,
                        "references": code_references(data, method),
                    }
                )
    return matches


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--class-descriptor", required=True)
    parser.add_argument("--method", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = scan_method(
        args.apk.resolve(),
        class_descriptor=args.class_descriptor,
        method_name=args.method,
    )
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
