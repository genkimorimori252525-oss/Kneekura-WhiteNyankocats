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


RES_XML_END_ELEMENT_TYPE = 0x0103
TYPE_STRING = 0x03


def remove_exact_uses_permission(
    data: bytes, permission: str,
) -> tuple[bytes, dict[str, int]]:
    """Remove ONE concrete <uses-permission> element from compiled AXML.

    Strictly intended for original-JP *research-only* app manifest quarantine.
    Preserves the entire string pool and all other chunks byte-for-byte.
    Aborts if the target is absent, duplicated, malformed, nested or not
    represented by a directly paired START/END element. This neither removes
    third-party SDK code nor certifies actual zero-egress.
    """
    if not isinstance(permission, str) or not permission:
        raise ValueError("permission must be a nonempty exact literal")
    if len(data) < 36 or struct.unpack_from("<HH", data, 0) != (3, 8):
        raise ValueError("not an Android AXML permission manifest")
    total_size = struct.unpack_from("<I", data, 4)[0]
    if total_size != len(data):
        raise ValueError("AXML declared size mismatch")
    values = {slot.index: slot.value for slot in manifest_string_slots(data)}
    cursor = 8
    ranges: list[tuple[int,int]] = []
    while cursor < len(data):
        if cursor + 8 > len(data):
            raise ValueError("truncated AXML chunk header")
        kind, header, size = struct.unpack_from("<HHI", data, cursor)
        if size < 8 or cursor + size > len(data):
            raise ValueError("invalid AXML chunk size")
        if kind == RES_XML_START_ELEMENT_TYPE:
            if header < 16 or size < 36:
                raise ValueError("invalid AXML start element")
            name_index = struct.unpack_from("<I", data, cursor + 20)[0]
            tag_name = values.get(name_index)
            if tag_name == "uses-permission":
                attr_start, attr_size, attr_count = struct.unpack_from(
                    "<HHH", data, cursor + 24
                )
                if attr_size < 20 or attr_count > 4096:
                    raise ValueError("invalid AXML permission attribute layout")
                attr_base = cursor + 16 + attr_start
                found_names: list[str] = []
                for idx in range(attr_count):
                    at = attr_base + idx * attr_size
                    if at < cursor + 16 or at + 20 > cursor + size:
                        raise ValueError("AXML permission attribute escaped chunk")
                    _, attr_id, raw_id = struct.unpack_from("<III", data, at)
                    if values.get(attr_id) != "name":
                        continue
                    data_type = data[at + 15]
                    value_id = struct.unpack_from("<I", data, at + 16)[0]
                    selected = raw_id if raw_id != NO_INDEX else (
                        value_id if data_type == TYPE_STRING else NO_INDEX
                    )
                    if selected != NO_INDEX and selected in values:
                        found_names.append(values[selected])
                if permission in found_names:
                    if found_names != [permission]:
                        raise ValueError("ambiguous original AXML permission attributes")
                    next_at = cursor + size
                    if next_at + 24 > len(data):
                        raise ValueError("permission element has no closing tag")
                    close_kind, close_header, close_size = struct.unpack_from(
                        "<HHI", data, next_at
                    )
                    close_name = struct.unpack_from("<I", data, next_at + 20)[0]
                    if (close_kind != RES_XML_END_ELEMENT_TYPE
                        or close_header != 16 or close_size != 24
                        or close_name != name_index):
                        raise ValueError("permission must have an immediate paired end tag")
                    ranges.append((cursor, next_at + close_size))
        cursor += size
    if len(ranges) != 1:
        raise ValueError(
            f"expected exactly one original <uses-permission {permission}>, got {len(ranges)}"
        )
    first, last = ranges[0]
    patched = bytearray(data[:first] + data[last:])
    struct.pack_into("<I", patched, 4, len(patched))
    if len(patched) != len(data) - (last - first):
        raise AssertionError("AXML permission-removal size drifted")
    return bytes(patched), {
        "removed_elements": 1,
        "removed_byte_count": last - first,
        "source_xml_size": len(data),
        "candidate_xml_size": len(patched),
    }


