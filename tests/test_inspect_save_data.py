import hashlib
import struct

from tools.base_mod.inspect_save_data import inspect_save_bytes


def _build_prefix(*, gv=150700, catfood=1234, energy=100):
    out = bytearray()
    out += struct.pack("<i", gv)
    out += struct.pack("<b", 1)  # ub1 for modern JP
    out += struct.pack("<b", 0)  # mute_bgm
    out += struct.pack("<b", 1)  # mute_se
    out += struct.pack("<i", catfood)
    out += struct.pack("<i", energy)
    out += struct.pack("<i", 2026)
    out += struct.pack("<i", 2026)
    out += struct.pack("<i", 10)
    out += struct.pack("<i", 10)
    out += struct.pack("<i", 7)
    out += struct.pack("<i", 7)
    out += struct.pack("<d", 12345.5)
    out += struct.pack("<i", 19)
    out += struct.pack("<i", 30)
    out += struct.pack("<i", 0)
    out += b"\x00" * 64
    return bytes(out)


def _wrap(payload: bytes) -> bytes:
    digest = hashlib.md5(b"battlecats" + payload).hexdigest().encode("ascii")
    return payload + digest


def test_inspector_accepts_valid_jp_hash_and_reads_stable_prefix():
    data = _wrap(_build_prefix())
    result = inspect_save_bytes(data)

    assert result["jp_hash_valid"] is True
    assert result["prefix"]["game_version"] == 150700
    assert result["prefix"]["catfood"] == 1234
    assert result["prefix"]["current_energy"] == 100
    assert result["prefix"]["mute_bgm"] is False
    assert result["prefix"]["mute_se"] is True
    assert result["mutation_attempted"] is False


def test_inspector_rejects_tampered_payload():
    data = bytearray(_wrap(_build_prefix()))
    data[12] ^= 1
    result = inspect_save_bytes(bytes(data))
    assert result["jp_hash_valid"] is False


def test_inspector_rejects_non_hex_trailer():
    payload = _build_prefix()
    result = inspect_save_bytes(payload + b"z" * 32)
    assert result["hash_trailer_ascii_hex"] is False
    assert result["jp_hash_valid"] is False
