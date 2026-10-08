from __future__ import annotations

import hashlib
import unittest

from Crypto.Cipher import AES

from tools.battlecats_pack import (
    BLOCK_SIZE,
    PackReader,
    decrypt_manifest_bytes,
    parse_manifest,
)


def pad(data: bytes) -> bytes:
    amount = BLOCK_SIZE - (len(data) % BLOCK_SIZE)
    return data + bytes([amount]) * amount


def list_key() -> bytes:
    prefix = hashlib.md5(b"pack").digest()[:8]
    return prefix.hex().encode("ascii")


def encrypt_manifest(text: str) -> bytes:
    return AES.new(list_key(), AES.MODE_ECB).encrypt(pad(text.encode("utf-8")))


def encrypt_local(payload: bytes) -> bytes:
    key = bytes.fromhex("d754868de89d717fa9e7b06da45ae9e3")
    iv = bytes.fromhex("40b2131a9f388ad4e5002a98118f6128")
    return AES.new(key, AES.MODE_CBC, iv).encrypt(pad(payload))


class BattleCatsPackTests(unittest.TestCase):
    def test_manifest_round_trip_and_local_entry(self) -> None:
        payload = b"100,3,10\n"
        encrypted_payload = encrypt_local(payload)
        manifest_text = f"1\nunit001.csv,0,{len(encrypted_payload)}\n"
        manifest = encrypt_manifest(manifest_text)

        declared, entries = parse_manifest(manifest)
        self.assertEqual(declared, 1)
        self.assertEqual(entries[0].name, "unit001.csv")

        reader = PackReader("DataLocal", manifest, encrypted_payload, region="jp")
        decoded, provenance = reader.read("unit001.csv")
        self.assertEqual(decoded, payload)
        self.assertEqual(provenance.mode, "aes-128-cbc-jp")
        self.assertEqual(
            provenance.payload_sha256,
            hashlib.sha256(payload).hexdigest(),
        )

    def test_image_data_is_raw(self) -> None:
        payload = b"[modelanim:model]\n3\n"
        manifest = encrypt_manifest(
            f"1\n001_f.mamodel,0,{len(payload)}\n"
        )
        reader = PackReader("ImageDataLocal", manifest, payload, region="jp")
        decoded, provenance = reader.read("001_f.mamodel")
        self.assertEqual(decoded, payload)
        self.assertEqual(provenance.mode, "raw")

    def test_manifest_count_is_validated(self) -> None:
        manifest = encrypt_manifest("2\na.csv,0,16\n")
        with self.assertRaises(ValueError):
            parse_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
