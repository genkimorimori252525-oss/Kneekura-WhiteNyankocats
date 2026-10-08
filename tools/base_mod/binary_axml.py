"""Minimal binary Android XML string-pool reader/patcher.

The base-preserving package patch intentionally uses equal-byte-length package
identifiers, so string indices, offsets and the XML tree do not need to move.
Only explicitly selected string-pool values are rewritten.
"""

from __future__ import annotations

from dataclasses import dataclass
import struct


RES_STRING_POOL_TYPE = 0x0001
UTF8_FLAG = 0x00000100


@dataclass(frozen=True)
class StringSlot:
    index: int
    value: str
    data_offset: int
    encoded_length: int
    utf8: bool


def _read_utf8_length(data: bytes | bytearray, offset: int) -> tuple[int, int]:
    first = data[offset]
    if first & 0x80:
        return ((first & 0x7F) << 8) | data[offset + 1], 2
    return first, 1


def _read_utf16_length(data: bytes | bytearray, offset: int) -> tuple[int, int]:
    first = struct.unpack_from("<H", data, offset)[0]
    if first & 0x8000:
        second = struct.unpack_from("<H", data, offset + 2)[0]
        return ((first & 0x7FFF) << 16) | second, 4
    return first, 2


def manifest_string_slots(data: bytes) -> list[StringSlot]:
    if len(data) < 36:
        raise ValueError("binary XML is too short")

    xml_type, xml_header_size, _ = struct.unpack_from("<HHI", data, 0)
    if xml_type != 0x0003 or xml_header_size != 8:
        raise ValueError("not an Android binary XML document")

    pool_offset = xml_header_size
    pool_type, pool_header_size, pool_size = struct.unpack_from(
        "<HHI", data, pool_offset
    )
    if pool_type != RES_STRING_POOL_TYPE:
        raise ValueError("binary XML does not begin with a string pool")
    if pool_offset + pool_size > len(data):
        raise ValueError("truncated Android string pool")

    string_count, _, flags, strings_start, _ = struct.unpack_from(
        "<IIIII", data, pool_offset + 8
    )
    utf8 = bool(flags & UTF8_FLAG)
    offsets_base = pool_offset + pool_header_size
    strings_base = pool_offset + strings_start

    slots: list[StringSlot] = []
    for index in range(string_count):
        relative = struct.unpack_from(
            "<I", data, offsets_base + index * 4
        )[0]
        cursor = strings_base + relative

        if utf8:
            _, consumed = _read_utf8_length(data, cursor)
            cursor += consumed
            byte_length, consumed = _read_utf8_length(data, cursor)
            cursor += consumed
            raw = data[cursor : cursor + byte_length]
            value = raw.decode("utf-8")
            slots.append(
                StringSlot(index, value, cursor, byte_length, True)
            )
        else:
            char_length, consumed = _read_utf16_length(data, cursor)
            cursor += consumed
            byte_length = char_length * 2
            raw = data[cursor : cursor + byte_length]
            value = raw.decode("utf-16le")
            slots.append(
                StringSlot(index, value, cursor, byte_length, False)
            )

    return slots


def string_values(data: bytes) -> list[str]:
    return [slot.value for slot in manifest_string_slots(data)]


def patch_equal_length_strings(
    data: bytes,
    replacements: dict[str, str],
    *,
    require_all: bool = True,
) -> tuple[bytes, dict[str, int]]:
    """Patch exact string-pool values without changing pool structure."""

    slots = manifest_string_slots(data)
    mutable = bytearray(data)
    counts = {source: 0 for source in replacements}

    for slot in slots:
        replacement = replacements.get(slot.value)
        if replacement is None:
            continue

        if slot.utf8:
            encoded = replacement.encode("utf-8")
        else:
            encoded = replacement.encode("utf-16le")

        if len(encoded) != slot.encoded_length:
            raise ValueError(
                "replacement must preserve encoded byte length: "
                f"{slot.value!r} -> {replacement!r}"
            )

        mutable[
            slot.data_offset : slot.data_offset + slot.encoded_length
        ] = encoded
        counts[slot.value] += 1

    if require_all:
        missing = [key for key, count in counts.items() if count == 0]
        if missing:
            raise ValueError(
                "expected manifest strings were not found: " + ", ".join(missing)
            )

    return bytes(mutable), counts

RES_XML_START_ELEMENT_TYPE = 0x0102
TYPE_INT_BOOLEAN = 0x12
NO_INDEX = 0xFFFFFFFF


def patch_boolean_attribute(
    data: bytes,
    *,
    element_name: str,
    attribute_name: str,
    expected: bool,
    replacement: bool,
) -> tuple[bytes, int]:
    """Patch one exact binary-AXML boolean attribute without moving chunks."""

    slots = manifest_string_slots(data)
    values = {slot.index: slot.value for slot in slots}
    mutable = bytearray(data)
    matches = 0

    _, xml_header_size, _ = struct.unpack_from("<HHI", data, 0)
    cursor = xml_header_size
    while cursor < len(data):
        chunk_type, _, chunk_size = struct.unpack_from("<HHI", data, cursor)
        if chunk_size < 8 or cursor + chunk_size > len(data):
            raise ValueError("malformed Android binary XML chunk")

        if chunk_type == RES_XML_START_ELEMENT_TYPE:
            # ResXMLTree_node is 16 bytes; ResXMLTree_attrExt follows it.
            ext = cursor + 16
            _, name_index = struct.unpack_from("<II", data, ext)
            tag_name = values.get(name_index)

            attribute_start, attribute_size, attribute_count = struct.unpack_from(
                "<HHH", data, ext + 8
            )
            if attribute_size < 20:
                raise ValueError("unexpected Android binary XML attribute size")

            base = ext + attribute_start
            for index in range(attribute_count):
                attribute = base + index * attribute_size
                _, attr_name_index, _ = struct.unpack_from("<III", data, attribute)
                attr_name = values.get(attr_name_index)
                if tag_name != element_name or attr_name != attribute_name:
                    continue

                value_size, _, data_type, value = struct.unpack_from(
                    "<HBBI", data, attribute + 12
                )
                if value_size != 8 or data_type != TYPE_INT_BOOLEAN:
                    raise ValueError(
                        f"{element_name}.{attribute_name} is not a boolean value"
                    )
                expected_value = 1 if expected else 0
                if value != expected_value:
                    raise ValueError(
                        f"{element_name}.{attribute_name} expected "
                        f"{expected_value}, got {value}"
                    )
                struct.pack_into(
                    "<I",
                    mutable,
                    attribute + 16,
                    1 if replacement else 0,
                )
                matches += 1

        cursor += chunk_size

    if matches != 1:
        raise ValueError(
            f"expected exactly one {element_name}.{attribute_name}, got {matches}"
        )
    return bytes(mutable), matches
