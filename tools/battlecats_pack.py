"""Read-only Battle Cats pack primitives.

This module only decodes data supplied by the caller. It never writes back to
an APK or pack and contains no code for re-signing or patching the Android app.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Iterable

from Crypto.Cipher import AES


BLOCK_SIZE = 16

# Verified against the user's JP 15.7.1 export. Keep region keys isolated so a
# future importer can select them by evidence instead of scattering constants.
REGION_KEYS: dict[str, tuple[bytes, bytes]] = {
    "jp": (
        bytes.fromhex("d754868de89d717fa9e7b06da45ae9e3"),
        bytes.fromhex("40b2131a9f388ad4e5002a98118f6128"),
    ),
}

# ImageDataLocal entries in the observed JP 15.7.1 InstallPack are directly
# readable text chunks and must not be AES-decoded.
RAW_LOCAL_FAMILIES = {"imagedatalocal"}


@dataclass(frozen=True)
class PackEntry:
    name: str
    offset: int
    size: int


@dataclass(frozen=True)
class EntryProvenance:
    family: str
    entry: str
    offset: int
    encrypted_size: int
    mode: str
    payload_sha256: str


def _ascii_md5_prefix_key(text: str) -> bytes:
    """Return the 16 ASCII bytes used by Battle Cats' manifest/server keys."""
    prefix = hashlib.md5(text.encode("utf-8")).digest()[:8]
    return prefix.hex().encode("ascii")


def _unpad_pkcs7(data: bytes) -> bytes:
    if not data:
        return data
    amount = data[-1]
    if amount < 1 or amount > BLOCK_SIZE:
        raise ValueError("invalid PKCS#7 padding length")
    if data[-amount:] != bytes([amount]) * amount:
        raise ValueError("invalid PKCS#7 padding bytes")
    return data[:-amount]


def _require_block_multiple(data: bytes, label: str) -> None:
    if len(data) % BLOCK_SIZE:
        raise ValueError(f"{label} length {len(data)} is not AES block-aligned")


def decrypt_manifest_bytes(raw: bytes) -> bytes:
    """Decrypt one .list manifest."""
    _require_block_multiple(raw, "manifest")
    cipher = AES.new(_ascii_md5_prefix_key("pack"), AES.MODE_ECB)
    return _unpad_pkcs7(cipher.decrypt(raw))


def parse_manifest(raw: bytes) -> tuple[int, list[PackEntry]]:
    """Decode a .list file and return declared count plus validated entries."""
    text = decrypt_manifest_bytes(raw).decode("utf-8-sig")
    lines = [line for line in text.splitlines() if line]
    if not lines:
        raise ValueError("empty manifest")

    try:
        declared_count = int(lines[0].strip())
    except ValueError as exc:
        raise ValueError("manifest first line is not an entry count") from exc

    entries: list[PackEntry] = []
    for line_no, line in enumerate(lines[1:], start=2):
        columns = [column.strip() for column in line.split(",")]
        if len(columns) < 3 or not columns[0]:
            raise ValueError(f"invalid manifest row at line {line_no}: {line!r}")
        try:
            offset = int(columns[1])
            size = int(columns[2])
        except ValueError as exc:
            raise ValueError(f"invalid offset/size at line {line_no}") from exc
        if offset < 0 or size < 0:
            raise ValueError(f"negative offset/size at line {line_no}")
        entries.append(PackEntry(columns[0], offset, size))

    if declared_count != len(entries):
        raise ValueError(
            f"manifest count mismatch: declared {declared_count}, parsed {len(entries)}"
        )
    return declared_count, entries


class PackReader:
    """Random-access, read-only view over one .list/.pack pair."""

    def __init__(
        self,
        family: str,
        manifest_bytes: bytes,
        pack_bytes: bytes,
        *,
        region: str = "jp",
    ) -> None:
        self.family = family
        self.region = region.lower()
        _, entries = parse_manifest(manifest_bytes)
        self._entries_in_order = tuple(entries)
        self._entries = {entry.name: entry for entry in entries}
        if len(self._entries) != len(self._entries_in_order):
            raise ValueError(f"duplicate entry name in {family} manifest")
        self._pack = pack_bytes

        for entry in self._entries_in_order:
            if entry.offset + entry.size > len(pack_bytes):
                raise ValueError(
                    f"{family}/{entry.name} exceeds pack bounds: "
                    f"{entry.offset}+{entry.size}>{len(pack_bytes)}"
                )

    @property
    def entries(self) -> tuple[PackEntry, ...]:
        return self._entries_in_order

    def has(self, name: str) -> bool:
        return name in self._entries

    def entry(self, name: str) -> PackEntry:
        try:
            return self._entries[name]
        except KeyError as exc:
            raise KeyError(f"{self.family} has no entry {name!r}") from exc

    def decryption_mode(self) -> str:
        lowered = self.family.lower()
        if lowered in RAW_LOCAL_FAMILIES:
            return "raw"
        if "server" in lowered:
            return "aes-128-ecb-server"
        return f"aes-128-cbc-{self.region}"

    def read(self, name: str) -> tuple[bytes, EntryProvenance]:
        entry = self.entry(name)
        chunk = self._pack[entry.offset : entry.offset + entry.size]
        mode = self.decryption_mode()

        if mode == "raw":
            payload = chunk
        elif mode == "aes-128-ecb-server":
            _require_block_multiple(chunk, f"{self.family}/{name}")
            cipher = AES.new(_ascii_md5_prefix_key("battlecats"), AES.MODE_ECB)
            payload = _unpad_pkcs7(cipher.decrypt(chunk))
        else:
            try:
                key, iv = REGION_KEYS[self.region]
            except KeyError as exc:
                raise ValueError(f"unsupported region {self.region!r}") from exc
            _require_block_multiple(chunk, f"{self.family}/{name}")
            cipher = AES.new(key, AES.MODE_CBC, iv)
            payload = _unpad_pkcs7(cipher.decrypt(chunk))

        provenance = EntryProvenance(
            family=self.family,
            entry=name,
            offset=entry.offset,
            encrypted_size=entry.size,
            mode=mode,
            payload_sha256=hashlib.sha256(payload).hexdigest(),
        )
        return payload, provenance
