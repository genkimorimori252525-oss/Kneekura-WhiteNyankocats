"""Deterministic Battle Cats local-pack rebuilder.

This writer is deliberately narrow:
- it consumes an existing .list/.pack pair;
- preserves entry ordering;
- copies unchanged encrypted entry bytes verbatim;
- encrypts only explicitly replaced payloads using the same family mode;
- rebuilds offsets and the encrypted manifest;
- emits a mutation ledger.

It does not know about APK signing or scene hooks.
"""

from __future__ import annotations

from dataclasses import asdict
import hashlib
from typing import Mapping

from Crypto.Cipher import AES

from tools.battlecats_pack import (
    BLOCK_SIZE,
    RAW_LOCAL_FAMILIES,
    REGION_KEYS,
    PackReader,
    _ascii_md5_prefix_key,
    parse_manifest,
)


def _pad_pkcs7(data: bytes) -> bytes:
    amount = BLOCK_SIZE - (len(data) % BLOCK_SIZE)
    return data + bytes([amount]) * amount


def encrypt_manifest_bytes(plain: bytes) -> bytes:
    cipher = AES.new(_ascii_md5_prefix_key("pack"), AES.MODE_ECB)
    return cipher.encrypt(_pad_pkcs7(plain))


def _encrypt_entry(
    family: str,
    payload: bytes,
    *,
    region: str,
) -> tuple[bytes, str]:
    lowered = family.lower()
    if lowered in RAW_LOCAL_FAMILIES:
        return payload, "raw"

    padded = _pad_pkcs7(payload)
    if "server" in lowered:
        cipher = AES.new(
            _ascii_md5_prefix_key("battlecats"),
            AES.MODE_ECB,
        )
        return cipher.encrypt(padded), "aes-128-ecb-server"

    try:
        key, iv = REGION_KEYS[region.lower()]
    except KeyError as exc:
        raise ValueError(f"unsupported region {region!r}") from exc
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(padded), f"aes-128-cbc-{region.lower()}"


def rebuild_pack(
    family: str,
    manifest_bytes: bytes,
    pack_bytes: bytes,
    replacements: Mapping[str, bytes],
    *,
    region: str = "jp",
) -> tuple[bytes, bytes, dict]:
    declared, entries = parse_manifest(manifest_bytes)
    known = {entry.name for entry in entries}
    unknown = sorted(set(replacements) - known)
    if unknown:
        raise KeyError(
            f"{family} replacement names are not present in source manifest: {unknown}"
        )

    source_reader = PackReader(
        family,
        manifest_bytes,
        pack_bytes,
        region=region,
    )

    rebuilt = bytearray()
    manifest_rows: list[str] = []
    ledger_rows: list[dict] = []

    for entry in entries:
        new_offset = len(rebuilt)
        original_chunk = pack_bytes[entry.offset : entry.offset + entry.size]

        if entry.name in replacements:
            original_payload, original_provenance = source_reader.read(entry.name)
            replacement_payload = bytes(replacements[entry.name])
            encrypted, mode = _encrypt_entry(
                family,
                replacement_payload,
                region=region,
            )
            rebuilt.extend(encrypted)
            ledger_rows.append(
                {
                    "name": entry.name,
                    "changed": True,
                    "mode": mode,
                    "old_offset": entry.offset,
                    "new_offset": new_offset,
                    "old_encrypted_size": entry.size,
                    "new_encrypted_size": len(encrypted),
                    "old_payload_sha256": original_provenance.payload_sha256,
                    "new_payload_sha256": hashlib.sha256(
                        replacement_payload
                    ).hexdigest(),
                    "old_payload_size": len(original_payload),
                    "new_payload_size": len(replacement_payload),
                }
            )
            size = len(encrypted)
        else:
            rebuilt.extend(original_chunk)
            ledger_rows.append(
                {
                    "name": entry.name,
                    "changed": False,
                    "old_offset": entry.offset,
                    "new_offset": new_offset,
                    "encrypted_size": entry.size,
                    "encrypted_sha256": hashlib.sha256(
                        original_chunk
                    ).hexdigest(),
                }
            )
            size = entry.size

        manifest_rows.append(f"{entry.name},{new_offset},{size}")

    if len(manifest_rows) != declared:
        raise RuntimeError("rebuilt manifest entry count drifted")

    manifest_plain = (
        str(declared) + "\n" + "\n".join(manifest_rows) + "\n"
    ).encode("utf-8")
    encrypted_manifest = encrypt_manifest_bytes(manifest_plain)
    rebuilt_pack = bytes(rebuilt)

    # Full postcondition: the rebuilt pair must parse and every untouched
    # payload must still decode to its original payload hash.
    rebuilt_reader = PackReader(
        family,
        encrypted_manifest,
        rebuilt_pack,
        region=region,
    )

    changed_names = sorted(replacements)
    for row in ledger_rows:
        payload, provenance = rebuilt_reader.read(row["name"])
        if row["changed"]:
            expected = row["new_payload_sha256"]
        else:
            original_payload, original_provenance = source_reader.read(row["name"])
            expected = original_provenance.payload_sha256
            if hashlib.sha256(payload).hexdigest() != hashlib.sha256(
                original_payload
            ).hexdigest():
                raise RuntimeError(
                    f"{family}/{row['name']} payload changed unexpectedly"
                )
        if provenance.payload_sha256 != expected:
            raise RuntimeError(
                f"{family}/{row['name']} rebuilt payload hash mismatch"
            )

    ledger = {
        "schema_version": 1,
        "family": family,
        "region": region.lower(),
        "entry_count": declared,
        "changed_entries": changed_names,
        "source_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "source_pack_sha256": hashlib.sha256(pack_bytes).hexdigest(),
        "rebuilt_manifest_sha256": hashlib.sha256(
            encrypted_manifest
        ).hexdigest(),
        "rebuilt_pack_sha256": hashlib.sha256(rebuilt_pack).hexdigest(),
        "source_pack_size": len(pack_bytes),
        "rebuilt_pack_size": len(rebuilt_pack),
        "entries": ledger_rows,
    }
    return encrypted_manifest, rebuilt_pack, ledger


def append_pack_entries(
    family: str,
    manifest_bytes: bytes,
    pack_bytes: bytes,
    additions: Mapping[str, bytes],
    *,
    region: str = "jp",
) -> tuple[bytes, bytes, dict]:
    """Append new encrypted entries while preserving every source entry byte-for-byte."""

    declared, entries = parse_manifest(manifest_bytes)
    if not additions:
        raise ValueError("at least one appended entry is required")

    known = {entry.name for entry in entries}
    duplicates = sorted(set(additions) & known)
    if duplicates:
        raise ValueError(
            f"{family} appended entry already exists in source manifest: {duplicates}"
        )

    source_reader = PackReader(
        family,
        manifest_bytes,
        pack_bytes,
        region=region,
    )

    rebuilt = bytearray()
    manifest_rows: list[str] = []
    ledger_rows: list[dict] = []

    for entry in entries:
        new_offset = len(rebuilt)
        original_chunk = pack_bytes[entry.offset : entry.offset + entry.size]
        rebuilt.extend(original_chunk)
        manifest_rows.append(f"{entry.name},{new_offset},{entry.size}")
        payload, provenance = source_reader.read(entry.name)
        ledger_rows.append(
            {
                "name": entry.name,
                "added": False,
                "old_offset": entry.offset,
                "new_offset": new_offset,
                "encrypted_size": entry.size,
                "encrypted_sha256": hashlib.sha256(original_chunk).hexdigest(),
                "payload_sha256": provenance.payload_sha256,
                "payload_size": len(payload),
            }
        )

    for name in sorted(additions):
        payload = bytes(additions[name])
        new_offset = len(rebuilt)
        encrypted, mode = _encrypt_entry(
            family,
            payload,
            region=region,
        )
        rebuilt.extend(encrypted)
        manifest_rows.append(f"{name},{new_offset},{len(encrypted)}")
        ledger_rows.append(
            {
                "name": name,
                "added": True,
                "mode": mode,
                "new_offset": new_offset,
                "encrypted_size": len(encrypted),
                "payload_sha256": hashlib.sha256(payload).hexdigest(),
                "payload_size": len(payload),
            }
        )

    new_count = declared + len(additions)
    manifest_plain = (
        str(new_count) + "\n" + "\n".join(manifest_rows) + "\n"
    ).encode("utf-8")
    encrypted_manifest = encrypt_manifest_bytes(manifest_plain)
    rebuilt_pack = bytes(rebuilt)

    rebuilt_reader = PackReader(
        family,
        encrypted_manifest,
        rebuilt_pack,
        region=region,
    )

    # Full postcondition: every original payload is unchanged and every
    # appended payload decodes exactly to the requested bytes.
    for entry in entries:
        before, _ = source_reader.read(entry.name)
        after, _ = rebuilt_reader.read(entry.name)
        if after != before:
            raise RuntimeError(
                f"{family}/{entry.name} changed during append-only rebuild"
            )

    for name, expected in additions.items():
        after, provenance = rebuilt_reader.read(name)
        if after != bytes(expected):
            raise RuntimeError(
                f"{family}/{name} appended payload verification failed"
            )
        if provenance.payload_sha256 != hashlib.sha256(bytes(expected)).hexdigest():
            raise RuntimeError(
                f"{family}/{name} appended payload hash verification failed"
            )

    return encrypted_manifest, rebuilt_pack, {
        "schema_version": 1,
        "family": family,
        "region": region.lower(),
        "source_entry_count": declared,
        "entry_count": new_count,
        "added_entries": sorted(additions),
        "original_entries_preserved": True,
        "source_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "source_pack_sha256": hashlib.sha256(pack_bytes).hexdigest(),
        "rebuilt_manifest_sha256": hashlib.sha256(encrypted_manifest).hexdigest(),
        "rebuilt_pack_sha256": hashlib.sha256(rebuilt_pack).hexdigest(),
        "source_pack_size": len(pack_bytes),
        "rebuilt_pack_size": len(rebuilt_pack),
        "entries": ledger_rows,
    }
