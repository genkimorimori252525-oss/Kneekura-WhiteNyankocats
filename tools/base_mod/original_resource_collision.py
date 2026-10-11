"""Read-only original JP15.7.1 resource-key collision control-flow witness.

Shows what happens when *successfully parsed* registered Server .list rows
contain the same inner-file key. Does NOT supply Server.pack, update original
SAVE or prove any Android device has loaded those files.
"""
from __future__ import annotations

from hashlib import sha256
import struct
from typing import Any

NATIVE_SHA256 = "333d2974ab2ff881fd70087fd62dea7d12d82addbc55cab2f2a675ad67e3a7e2"

# Exact original AArch64 opcode words at registry insert and comparison sites.
# The owner-proprietary native binary itself is never shipped or committed.
ORIGINAL_COLLISION_ANCHORS = {
    0x364980: 0x97FFA1A5,  # original named stream registry singleton
    0x364988: 0xAA1403E1,  # original resource key as lookup argument
    0x364990: 0x97FFA3D5,  # first registered-resource source lookup
    0x3649EC: 0xB40003D7,  # missing first stream -> fallback
    0x364A64: 0x97FFA16C,  # original registry singleton reused
    0x364A68: 0x910083E8,  # fallback output placement
    0x364A6C: 0xAA1403E1,  # SAME request key as first lookup
    0x364A70: 0x97FFA420,  # alternate registered-source lookup
    0x34D924: 0xAA1303E0,  # first lookup x0 registry
    0x34D928: 0xAA1403E1,  # first lookup x1 key
    0x34D92C: 0x940002FE,  # first lookup registry-map search
    0x34DB2C: 0xAA1303E0,  # alternate lookup x0 registry
    0x34DB30: 0xAA1503E1,  # alternate lookup x1 key
    0x34DB34: 0x9400027C,  # alternate lookup SAME registry-map search
    0x741B84: 0x97F02D5C,  # loop registers 92 .list/.pack mappings
    0x34D2EC: 0x54000D60,  # parsed .list entry loop termination
    0x34D304: 0x94005A48,  # parse inner resource key (column 0)
    0x34D308: 0xF940071C,  # load registered resource RB-tree root
    0x34D310: 0xB400057C,  # no node -> create new map entry
    0x34D334: 0xF940039C,  # seek the next RB-tree child
    0x34D33C: 0x39408388,  # read stored key SSO flag
    0x34D360: 0xEB1A02BF,  # stored length / candidate length
    0x34D36C: 0x941E2945,  # memcmp candidate vs stored key
    0x34D370: 0xEB15035F,
    0x34D374: 0x1A9F27E8,
    0x34D378: 0x7100001F,
    0x34D37C: 0x1A9FA7E9,
    0x34D380: 0x1A890108,
    0x34D384: 0x3707FD88,  # candidate < node -> traverse left
    0x34D394: 0x941E293B,  # memcmp stored vs candidate key
    0x34D398: 0xEB1A02BF,
    0x34D39C: 0x1A9F27E8,
    0x34D3A0: 0x7100001F,
    0x34D3A4: 0x1A9FA7E9,
    0x34D3A8: 0x1A890108,
    0x34D3AC: 0x7100051F,  # node < candidate?
    0x34D3B0: 0x540006A1,  # NO: equality -> skip new insertion
    0x34D3B4: 0x9100239C,  # YES: seek right child
    0x34D3B8: 0x17FFFFDF,  # repeat RB tree traversal
    0x34D3BC: 0x9104A3E0,  # only leaf/no-match path starts insertion
    0x34D440: 0x940002A7,  # insert into shared registered-resource tree
    0x34D47C: 0x35000093,  # SSO cleanup after newly inserted entry
    0x34D480: 0x17FFFF98,  # next parsed source-index row
    0x34D484: 0xAA1603F8,  # duplicate-key path starts; no write/insert
    0x34D488: 0x34FFF2D3,  # if SSO not heap-owned -> next row
    0x34D490: 0x941E2894,  # else free heap storage
    0x34D494: 0x17FFFF93,  # next parsed source-index row
}
# Pin linked callers too: generic cmp helpers and parse/open insertion paths.
DIRECT_BL_TARGETS = {
    0x364980: 0x34D014,
    0x364990: 0x34D8E4,
    0x364A64: 0x34D014,
    0x364A70: 0x34DAF0,
    0x34D92C: 0x34E524,
    0x34DB34: 0x34E524,
    0x741B84: 0x34D0F4,
    0x34D304: 0x363C24,
    0x34D36C: 0xAD7880,
    0x34D394: 0xAD7880,
    0x34D440: 0x34DEDC,
    0x34D490: 0xAD76E0,
}
# Deliberately bounded: no guessed links across virtual callbacks.
BRANCH_TARGETS = {
    0x3649EC: ("cbz", 0x364A64),
    0x34D2EC: ("b.cond", 0x34D498),
    0x34D310: ("cbz", 0x34D3BC),
    0x34D384: ("tbnz", 0x34D334),
    0x34D3B0: ("b.cond", 0x34D484),
    0x34D3B8: ("b", 0x34D334),
    0x34D47C: ("cbnz", 0x34D48C),
    0x34D480: ("b", 0x34D2E0),
    0x34D488: ("cbz", 0x34D2E0),
    0x34D494: ("b", 0x34D2E0),
}


class OriginalResourceCollisionError(ValueError):
    """Original native source changed or conditional duplicate proof broken."""


def _s(value: int, bits: int) -> int:
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def _u32(elf: bytes, at: int) -> int:
    if at < 0 or at + 4 > len(elf):
        raise OriginalResourceCollisionError("resource collision source truncated")
    return struct.unpack_from("<I", elf, at)[0]


def _direct_bl_target(elf: bytes, at: int) -> int:
    word = _u32(elf, at)
    if word & 0xFC000000 != 0x94000000:
        raise OriginalResourceCollisionError("expected direct original ARM64 BL")
    return at + _s(word & 0x03FFFFFF, 26) * 4


def _branch_target(elf: bytes, at: int, mode: str) -> int:
    word = _u32(elf, at)
    if mode == "b.cond":
        if word & 0xFF000010 != 0x54000000:
            raise OriginalResourceCollisionError("expected ARM64 B.cond")
        displacement = _s((word >> 5) & 0x7FFFF, 19)
    elif mode in {"cbz", "cbnz"}:
        if word & 0x7F000000 != (0x34000000 if mode == "cbz" else 0x35000000):
            raise OriginalResourceCollisionError("expected ARM64 CBZ/CBNZ")
        displacement = _s((word >> 5) & 0x7FFFF, 19)
    elif mode == "tbnz":
        if word & 0x7F000000 != 0x37000000:
            raise OriginalResourceCollisionError("expected ARM64 TBNZ")
        displacement = _s((word >> 5) & 0x3FFF, 14)
    elif mode == "b":
        if word & 0xFC000000 != 0x14000000:
            raise OriginalResourceCollisionError("expected direct ARM64 B")
        displacement = _s(word & 0x03FFFFFF, 26)
    else:
        raise OriginalResourceCollisionError("unrecognized collision source branch")
    return at + displacement * 4


def inspect_original_registration_collision_cfg(elf: bytes) -> dict[str, Any]:
    """Instruction-level proof; used with synthetic opcode fixtures in CI.

    Production wrapper always requires exact original-native full SHA-256.
    A duplicate key reaches 0x34d484, then (both SSO/heap paths) loops to
    0x34d2e0 without visiting the insert call at 0x34d440.
    """
    for pc, expected in ORIGINAL_COLLISION_ANCHORS.items():
        if _u32(elf, pc) != expected:
            raise OriginalResourceCollisionError(
                f"original registered resource opcode changed at 0x{pc:x}"
            )
    for pc, target in DIRECT_BL_TARGETS.items():
        if _direct_bl_target(elf, pc) != target:
            raise OriginalResourceCollisionError(
                f"original registered resource BL edge changed at 0x{pc:x}"
            )
    for pc, (kind, target) in BRANCH_TARGETS.items():
        if _branch_target(elf, pc, kind) != target:
            raise OriginalResourceCollisionError(
                f"original registered resource branch edge changed at 0x{pc:x}"
            )
    if (_u32(elf, 0x34D3B0) & 15) != 1:  # AArch64 B.NE specifically
        raise OriginalResourceCollisionError("duplicate-key skip is not B.NE")
    return {
        "status": "ORIGINAL_NATIVE_RESOURCE_DUPLICATE_KEY_SKIP_VERIFIED_STATIC",
        "original_registration_loop": "0x741b84 -> 0x34d0f4",
        "normal_stream_lookup": "0x364990 -> 0x34d8e4 -> 0x34e524",
        "fallback_stream_lookup": "0x3649ec CBZ -> 0x364a64; 0x364a70 -> 0x34daf0 -> 0x34e524",
        "primary_and_fallback_use_same_registry_singleton_and_key_tree": True,
        "source_list_inner_key_parser": "0x34d304 -> 0x363c24 (column 0)",
        "original_resource_tree_root": "0x34d308 (registry +0x8)",
        "lexicographic_key_compare": [
            "0x34d36c -> memcmp@plt",
            "0x34d394 -> memcmp@plt",
        ],
        "no_existing_key_to_new_insert_path": "0x34d310 -> 0x34d3bc -> 0x34d440",
        "new_entry_insert": "0x34d440 -> 0x34dedc",
        "existing_equal_key_skips_insert": "0x34d3b0 B.NE -> 0x34d484",
        "duplicate_ssostring_no_replacement": "0x34d488 -> 0x34d2e0",
        "duplicate_heap_string_no_replacement": "0x34d490 free; 0x34d494 -> 0x34d2e0",
        "same_key_registration_policy": "first successfully registered key is retained by this native path",
        "same_key_update_or_replace_in_this_function": False,
        "all_other_native_registry_mutation_sites_excluded": False,
        "all_92_owner_pack_files_locally_available": False,
        "real_original_runtime_registration_observed": False,
        "actual_download_tsv_source_winner_observed": False,
        "original_game_offline_first_boot_verified": False,
        "publisher_account_or_SAVE_data_modified": False,
    }


def trace_original_registration_collision(elf: bytes) -> dict[str, Any]:
    if sha256(elf).hexdigest() != NATIVE_SHA256:
        raise OriginalResourceCollisionError(
            "duplicate-key proof only applies to user's exact JP15.7.1 native"
        )
    return inspect_original_registration_collision_cfg(elf)
