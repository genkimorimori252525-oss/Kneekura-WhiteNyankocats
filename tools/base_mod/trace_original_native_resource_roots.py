"""Exact JP15.7.1 native Server resource lookup / file-root fallback witness.

Read-only: instruction and CFG checks against the user's unmodified ARM64 ELF.
In particular, distinguish the registered-Server .list -> app files-directory
fallback from the FINAL unregistered direct-source fallback. A root/path
reference is NOT proof an offline original APK accepted a resource.
"""
from __future__ import annotations

from hashlib import sha256
import struct
from typing import Any

NATIVE_SHA256 = "333d2974ab2ff881fd70087fd62dea7d12d82addbc55cab2f2a675ad67e3a7e2"

# Instruction words read and checked from the pinned user-owned JP15.7.1 ELF.
FILE_SOURCE_ANCHORS = {
    0x42CDE4: 0x1400B62C,  # B -> 0x45a694 (empty string output)
    0x42CDE8: 0x1400B703,  # B -> 0x45a9f4 (JNI getFilesDir)
    0x45A694: 0x7900011F,  # STRH WZR,[X8] empty libc++ string
    0x45A698: 0xD65F03C0,  # RET
    0x45AA3C: 0xD0FFE9A8,  # getFilesDir JNI literal xref
    0x34D0F4: 0xA9BA7BFD,  # registered source list/pack setup entry
    0x34D148: 0x94037F27,  # first root, empty std::string
    0x34D158: 0x97FF33EB,  # join source root and .list name
    0x34D178: 0x940043F3,  # try to open .list file stream
    0x34D17C: 0x37000300,  # opened => skip fallback
    0x34D184: 0x94037F19,  # root fallback JNI getFilesDir
    0x34D194: 0x97FF33DC,  # join app root and .list name
    0x34D1D8: 0x940043DB,  # retry .list stream open
    0x34D228: 0x94005BFB,  # feed registered .list stream parser
    0x34D304: 0x94005A48,  # parse inner-file resource filename
    0x34D440: 0x940002A7,  # insert unique registered resource key
    0x34D92C: 0x940002FE,  # normal registry index search
    0x34D93C: 0x54000120,  # normal: missing key -> null
    0x34D97C: 0x9400032B,  # normal: find associated packed-source reader
    0x34DB34: 0x9400027C,  # alternate registry index search
    0x34DB44: 0x54000120,  # alternate: missing key -> null
    0x34DB84: 0x9400017C,  # alternate: find registered pack
    0x34DB94: 0x540002E0,  # pack absent: try other file root
    0x34DBF4: 0x94037C7D,  # registered source loose-file root getFilesDir
    0x34DC24: 0x94037C50,  # open registered item as local source
    0x3649EC: 0xB40003D7,  # no first registered stream -> alternate
    0x364BA4: 0x94032090,  # FINAL direct-name lookup empty root
    0x364BD0: 0x9403208A,  # FINAL direct-name stream open
    0x364C44: 0xB5000428,  # opened -> consume stream
    0x364C50: 0x9403206A,  # retry FINAL direct-name stream
    0x364CC4: 0xB4000248,  # no stream -> virtual failure
    0x364CD0: 0x97FFFD51,  # success-side stream consumer
}
DIRECT_BL = {
    0x34D148: 0x42CDE4,
    0x34D158: 0x31A104,
    0x34D178: 0x35E144,
    0x34D184: 0x42CDE8,
    0x34D194: 0x31A104,
    0x34D1D8: 0x35E144,
    0x34D228: 0x364214,
    0x34D304: 0x363C24,
    0x34D440: 0x34DEDC,
    0x34D92C: 0x34E524,
    0x34D97C: 0x34E628,
    0x34DB34: 0x34E524,
    0x34DB84: 0x34E174,
    0x34DBF4: 0x42CDE8,
    0x34DC24: 0x42CD64,
    0x364BA4: 0x42CDE4,
    0x364BD0: 0x42CDF8,
    0x364C50: 0x42CDF8,
    0x364CD0: 0x364214,
}
# (kind, target); branch-only claims rather than guessed data flow.
BRANCHES = {
    0x42CDE4: ("b", 0x45A694),
    0x42CDE8: ("b", 0x45A9F4),
    0x34D17C: ("tbnz", 0x34D1DC),
    0x34D93C: ("b.eq", 0x34D960),
    0x34DB44: ("b.eq", 0x34DB68),
    0x34DB94: ("b.eq", 0x34DBF0),
    0x3649EC: ("cbz", 0x364A64),
    0x364C44: ("cbnz", 0x364CC8),
    0x364CC4: ("cbz", 0x364D0C),
}


class OriginalNativeResourceSeamError(ValueError):
    """Version or source-CFG drift: do not infer local loader acceptance."""


def _signed(value: int, bits: int) -> int:
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def _opcode(elf: bytes, address: int) -> int:
    if address < 0 or address + 4 > len(elf):
        raise OriginalNativeResourceSeamError("original ELF instruction truncated")
    return struct.unpack_from("<I", elf, address)[0]


def _direct_target(elf: bytes, pc: int, kind: str) -> int:
    word = _opcode(elf, pc)
    if kind in ("b", "bl"):
        mask = 0xFC000000
        expected = 0x14000000 if kind == "b" else 0x94000000
        if (word & mask) != expected:
            raise OriginalNativeResourceSeamError("wrong ARM64 direct branch kind")
        immediate, width = word & 0x03FFFFFF, 26
    elif kind in ("cbz", "cbnz"):
        if (word & 0x7F000000) != (
            0x34000000 if kind == "cbz" else 0x35000000
        ):
            raise OriginalNativeResourceSeamError("wrong CBZ/CBNZ branch kind")
        immediate, width = (word >> 5) & 0x7FFFF, 19
    elif kind == "b.eq":
        if (word & 0xFF00001F) != 0x54000000:
            raise OriginalNativeResourceSeamError("wrong B.EQ branch condition")
        immediate, width = (word >> 5) & 0x7FFFF, 19
    elif kind == "tbnz":
        if (word & 0x7F000000) != 0x37000000:
            raise OriginalNativeResourceSeamError("wrong TBNZ branch kind")
        immediate, width = (word >> 5) & 0x3FFF, 14
    else:
        raise OriginalNativeResourceSeamError("unsupported native source edge")
    return pc + _signed(immediate, width) * 4


def inspect_source_file_roots(elf: bytes) -> dict[str, Any]:
    """Verify source-only original fallback sequence, including direct last resort.

    Synthetic exact-opcode fixtures can call this; use trace_exact_owner_source()
    for conclusions about the actual game build (whole-file SHA pinned).
    """
    for pc, expected in FILE_SOURCE_ANCHORS.items():
        if _opcode(elf, pc) != expected:
            raise OriginalNativeResourceSeamError(
                f"native source path opcode changed at 0x{pc:x}"
            )
    for pc, expected in DIRECT_BL.items():
        if _direct_target(elf, pc, "bl") != expected:
            raise OriginalNativeResourceSeamError(
                f"native source path call changed at 0x{pc:x}"
            )
    for pc, (kind, expected) in BRANCHES.items():
        if _direct_target(elf, pc, kind) != expected:
            raise OriginalNativeResourceSeamError(
                f"native source path branch changed at 0x{pc:x}"
            )
    if elf[0x1905A5:0x1905B1] != b"getFilesDir\x00":
        raise OriginalNativeResourceSeamError("native getFilesDir JNI literal drift")
    return {
        "status": "PINNED_ORIGINAL_NATIVE_RESOURCE_LIST_ROOTS_AND_THREE_STAGE_STREAM_LOOKUP",
        "list_first_root": "0x34d148 -> 0x42cde4 -> 0x45a694: empty string",
        "list_first_open": "0x34d178 -> 0x35e144",
        "list_first_open_success_skips_filesdir": "0x34d17c TBNZ -> 0x34d1dc",
        "list_filesdir_fallback": "0x34d184 -> 0x42cde8 -> 0x45a9f4 getFilesDir",
        "list_filesdir_retry": "0x34d1d8 -> 0x35e144",
        "list_entry_parser_and_register": "0x34d228 -> 0x364214; 0x34d304 -> 0x363c24; 0x34d440 -> 0x34dedc",
        "stream_normal_registered_key_lookup": "0x34d92c -> 0x34e524; missing key at 0x34d93c",
        "stream_alternative_registered_key_lookup": "0x34db34 -> 0x34e524; missing key at 0x34db44",
        "registered_key_pack_missing_filesdir_fallback": "0x34db94 -> 0x34dbf0; 0x34dbf4 getFilesDir; 0x34dc24 open",
        "outer_stream_fallback_from_registered_to_alternate": "0x3649ec -> 0x364a64",
        "final_unregistered_direct_name_source_attempt": "0x364ba4 empty root; 0x364bd0/0x364c50 -> 0x42cdf8",
        "final_direct_source_reader_or_fail": "0x364c44 stream-present; 0x364cc4 no-stream; 0x364cd0 -> 0x364214",
        "registered_server_list_searches_application_filesdir_static_proven": True,
        "normal_and_alternative_registered_key_source_differentiated": True,
        "final_direct_source_attempt_without_registry_static_proven": True,
        "registered_list_and_pair_loaded_on_android": False,
        "direct_source_35_tsv_success_or_acceptance_proven": False,
        "additional_owner_pack_payload_bytes_present_proven": False,
        "native_first_run_save_or_lv60_verified": False,
        "zero_network_sdk_ipc_egress_verified": False,
        "original_apk_save_or_pack_modified": False,
    }


def trace_exact_owner_source(elf: bytes) -> dict[str, Any]:
    if sha256(elf).hexdigest() != NATIVE_SHA256:
        raise OriginalNativeResourceSeamError(
            "only user's exact original JP15.7.1 ARM64 source is supported"
        )
    return inspect_source_file_roots(elf)
