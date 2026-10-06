"""Equal-length DEX string replacement with header repair."""

from __future__ import annotations

import hashlib
import struct
import zlib


DEX_HEADER_SIZE = 0x70


def _read_uleb128(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    shift = 0
    cursor = offset
    while True:
        byte = data[cursor]
        cursor += 1
        value |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return value, cursor
        shift += 7
        if shift > 35:
            raise ValueError("invalid ULEB128")


def patch_exact_dex_string(
    data: bytes,
    source: str,
    replacement: str,
    *,
    expected_count: int | None = None,
) -> tuple[bytes, int]:
    if not data.startswith(b"dex\n"):
        raise ValueError("not a DEX file")
    if len(data) < DEX_HEADER_SIZE:
        raise ValueError("truncated DEX file")

    source_bytes = source.encode("utf-8")
    replacement_bytes = replacement.encode("utf-8")
    if len(source_bytes) != len(replacement_bytes):
        raise ValueError("DEX replacement must preserve UTF-8 byte length")
    if len(source) != len(replacement):
        raise ValueError("DEX replacement must preserve UTF-16 character length")

    string_ids_size = struct.unpack_from("<I", data, 0x38)[0]
    string_ids_off = struct.unpack_from("<I", data, 0x3C)[0]

    mutable = bytearray(data)
    count = 0
    for index in range(string_ids_size):
        string_data_off = struct.unpack_from(
            "<I", data, string_ids_off + index * 4
        )[0]
        _, cursor = _read_uleb128(data, string_data_off)
        end = data.find(b"\x00", cursor)
        if end < 0:
            raise ValueError("unterminated DEX string")
        raw = data[cursor:end]
        if raw != source_bytes:
            continue
        mutable[cursor:end] = replacement_bytes
        count += 1

    if expected_count is not None and count != expected_count:
        raise ValueError(
            f"expected {expected_count} DEX string replacements, got {count}"
        )

    # DEX signature is SHA-1 over everything after the signature field.
    mutable[12:32] = hashlib.sha1(mutable[32:]).digest()
    checksum = zlib.adler32(mutable[12:]) & 0xFFFFFFFF
    struct.pack_into("<I", mutable, 8, checksum)
    return bytes(mutable), count