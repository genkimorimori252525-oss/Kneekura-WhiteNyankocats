"""Read-only JP15.7.1 native player defaults and reset-to-SAVE seams.

This proves original field initialization and identifies title/GameServices
reset flows. It NEVER constructs a player save, bypasses a publisher account,
or asserts a title reset is a legitimate account-free virgin start.
"""
from __future__ import annotations

from hashlib import sha256
import struct
from typing import Any

NATIVE_SHA256 = "333d2974ab2ff881fd70087fd62dea7d12d82addbc55cab2f2a675ad67e3a7e2"
RELA_START, RELA_END, RELA_SIZE = 0x9D2A8, 0x12F708, 24
# Selected four-byte AArch64 words, pinned to the user's original library.
ORIGINAL_ANCHORS = {
    0x719044: 0xD105C3FF,
    0x719434: 0x2A1F03E1, 0x71943C: 0x52987708,
    0x719440: 0x8B080360, 0x719444: 0x940AFCA8,
    0x71A1CC: 0x91411F6A, 0x71A1E0: 0x912E9157,
    0x71A204: 0xAA1703E0, 0x71A208: 0x2A1F03E1,
    0x71A214: 0x940AF934, 0x71A21C: 0x91001273,
    0x71A220: 0x910022F7, 0x71A224: 0xF137227F,
    0x71A228: 0x54FFFEC1,
    0x71A4E4: 0x914EB729, 0x71A4FC: 0x91203137,
    0x71A504: 0x52806E53, 0x71A508: 0xAA1703E0,
    0x71A50C: 0x2A1F03E1, 0x71A510: 0x940AF875,
    0x71A514: 0xF1000673, 0x71A518: 0x910022F7,
    0x71A51C: 0x54FFFF61,
    0x71F2D4: 0xD10203FF, 0x71F338: 0x97FFE743,
    0x89385C: 0xA9BE7BFD, 0x89386C: 0x97FA15F6,
    0x893878: 0x97F69E02, 0x893880: 0x97F69F0F,
    0x893888: 0x97F69FA5, 0x893890: 0x97F6A006,
    0x8938A4: 0x17F69C72,
    0x938C98: 0xD10283FF, 0x938CB8: 0xB9400049,
    0x938CBC: 0xB9400068, 0x938CC0: 0x7100153F,
    0x938CC4: 0x54000280,
    0x938D18: 0x7100051F, 0x938D1C: 0x540004C0,
    0x938D20: 0x350007C8, 0x938D24: 0xAA1303E0,
    0x938D28: 0x97FFECA8, 0x938D2C: 0xB0FFC2C9,
    0x938D30: 0x912E6929, 0x938DE0: 0x17FE047A,
    0x933FC8: 0xD104C3FF, 0x934024: 0xAA1303E0,
    0x934028: 0x97F79407, 0x9345A0: 0xAA1303E0,
    0x9345A4: 0x97FE1689,
    0x749DD0: 0xD101C3FF, 0x749E70: 0x7100251F,
    0x749E74: 0x54000A21, 0x749E78: 0x360006F4,
    0x749E80: 0x94052677, 0x749EAC: 0x97FF481E,
    0x749EB0: 0x9405C046,
}
BL_TARGETS = {
    0x719444: 0x9D86E4, 0x71A214: 0x9D86E4, 0x71A510: 0x9D86E4,
    0x71F338: 0x719044, 0x89386C: 0x719044,
    0x893878: 0x63B080, 0x893880: 0x63B4BC,
    0x893888: 0x63B71C, 0x893890: 0x63B8A8,
    0x938D28: 0x933FC8, 0x934028: 0x719044,
    0x9345A4: 0x8B9FC8, 0x749E80: 0x89385C,
    0x749EAC: 0x71BF24, 0x749EB0: 0x8B9FC8,
}
BRANCHES = {
    0x71A228: ("b.ne", 0x71A200),
    0x71A51C: ("b.ne", 0x71A508),
    0x8938A4: ("b", 0x63AA6C),
    0x938CC4: ("b.eq", 0x938D14),
    0x938D1C: ("b.eq", 0x938DB4),
    0x938D20: ("cbnz", 0x938E18),
    0x938DE0: ("b", 0x8B9FC8),
    0x749E74: ("b.ne", 0x749FB8),
    0x749E78: ("tbz", 0x749F54),
}
# These are ELF R_AARCH64_RELATIVE destinations, not copied vtables.
RELOCATIONS = {
    0xAFD4B8: 0x71F2D4, 0xAFD4E8: 0x1DA558,
    0xB096D8: 0x938C98, 0xB09690: 0x1F08B1,
    0xAFEA00: 0x749DD0, 0xAFEA80: 0x1DC78F,
}
ORIGINAL_LABELS = {
    0x1DA558: b"13MyApplication\x00",
    0x1F08B1: b"ZN13MyApplication11TitleUpdateEvE3$_1\x00",
    0x1DC78F: b"22MyGameServicesDelegate\x00",
    0x191B9A: b"restart_reflect\x00",
}


class OriginalPlayerInitSaveTraceError(ValueError):
    """Fail-closed pinned original instruction, branch or RTTI drift."""


def _sign(value: int, bits: int) -> int:
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def _u32(elf: bytes, pc: int) -> int:
    if pc < 0 or pc + 4 > len(elf):
        raise OriginalPlayerInitSaveTraceError("original native instruction truncated")
    return struct.unpack_from("<I", elf, pc)[0]


def _target(elf: bytes, pc: int, kind: str) -> int:
    w = _u32(elf, pc)
    if kind in ("bl", "b"):
        opcode = 0x94000000 if kind == "bl" else 0x14000000
        if w & 0xFC000000 != opcode:
            raise OriginalPlayerInitSaveTraceError("unexpected original direct branch")
        delta, width = w & 0x03FFFFFF, 26
    elif kind in ("b.ne", "b.eq"):
        condition = 1 if kind == "b.ne" else 0
        if w & 0xFF00001F != (0x54000000 | condition):
            raise OriginalPlayerInitSaveTraceError("wrong ARM64 branch condition")
        delta, width = (w >> 5) & 0x7FFFF, 19
    elif kind == "cbnz":
        if w & 0x7F000000 != 0x35000000:
            raise OriginalPlayerInitSaveTraceError("expected CBNZ")
        delta, width = (w >> 5) & 0x7FFFF, 19
    elif kind == "tbz":
        if w & 0x7F000000 != 0x36000000:
            raise OriginalPlayerInitSaveTraceError("expected TBZ")
        delta, width = (w >> 5) & 0x3FFF, 14
    else:
        raise OriginalPlayerInitSaveTraceError("unsupported original branch kind")
    return pc + _sign(delta, width) * 4


def _check_relatives(elf: bytes) -> None:
    if len(elf) < RELA_END or (RELA_END - RELA_START) % RELA_SIZE:
        raise OriginalPlayerInitSaveTraceError("original .rela.dyn invalid")
    seen: dict[int, int] = {}
    for at in range(RELA_START, RELA_END, RELA_SIZE):
        slot, kind, dest = struct.unpack_from("<QQq", elf, at)
        if slot not in RELOCATIONS:
            continue
        if slot in seen or kind != 0x403:
            raise OriginalPlayerInitSaveTraceError("original vtable relocation duplicated/drifted")
        seen[slot] = dest
    if seen != RELOCATIONS:
        raise OriginalPlayerInitSaveTraceError("original initializer/title/services RTTI drift")
    for pc, literal in ORIGINAL_LABELS.items():
        if elf[pc:pc+len(literal)] != literal:
            raise OriginalPlayerInitSaveTraceError("original title or service RTTI literal changed")


def inspect_original_player_init_save(elf: bytes) -> dict[str, Any]:
    """Source-only original initialization and SAVE callsites; not device success."""
    for pc, opcode in ORIGINAL_ANCHORS.items():
        if _u32(elf, pc) != opcode:
            raise OriginalPlayerInitSaveTraceError(
                f"original initializer instruction drift at 0x{pc:x}"
            )
    for pc, target in BL_TARGETS.items():
        if _target(elf, pc, "bl") != target:
            raise OriginalPlayerInitSaveTraceError(
                f"original initializer direct call changed at 0x{pc:x}"
            )
    for pc, (kind, target) in BRANCHES.items():
        if _target(elf, pc, kind) != target:
            raise OriginalPlayerInitSaveTraceError(
                f"original initializer branch changed at 0x{pc:x}"
            )
    _check_relatives(elf)
    if (_u32(elf, 0x71A504) >> 5) & 0xFFFF != 882 or 0xDC8 // 4 != 882:
        raise OriginalPlayerInitSaveTraceError("original 882-row level count drift")
    return {
        "status": "ORIGINAL_NATIVE_PLAYER_INITIALIZER_AND_TITLE_RESET_SAVER_STATIC",
        "source": "user-owned exact JP15.7.1 ARM64; never run the original functions",
        "default_native_state_initializer": "0x719044 (MyApplication vtable 0xafd4b8 -> 0x71f2d4 -> 0x71f338)",
        "xp_zero_writer": "0x719434 w1=0; 0x71943c/0x719440 context+0xc3b8; 0x719444 -> 0x9d86e4",
        "current_level_initialization": "0x71a1e0 context+0x47ba4; 882 records x8, write encoded 0 at 0x71a214",
        "cap_increment_initialization": "0x71a4fc context+0x3ad80c; 882 records x8, write encoded 0 at 0x71a510",
        "subsystem_reset": "0x89385c -> 0x719044, then 0x63b080/0x63b4bc/0x63b71c/0x63b8a8/0x63aa6c",
        "title_rtti": "ZN13MyApplication11TitleUpdateEvE3$_1",
        "title_dialog_name": "restart_reflect at 0x191b9a (0x938d2c/0x938d30)",
        "title_reset_call": "0x938cc0 event 5; 0x938d18 mode check; 0x938d28 -> 0x933fc8",
        "title_reset_writes_original_SAVE": "0x933fc8 -> 0x934028 -> 0x719044; 0x9345a4 -> 0x8b9fc8",
        "title_alternative_save": "0x938de0 tail B -> 0x8b9fc8",
        "game_services_rtti": "22MyGameServicesDelegate",
        "service_state9_reset_and_save": "0x749e70 CMP #9; 0x749e78 TBZ skip; 0x749e80 -> 0x89385c; 0x749eb0 -> 0x8b9fc8",
        "title_or_service_reset_accepted_for_legitimate_virgin_game": False,
        "original_title_reset_and_native_writer_connected": True,
        "normal_new_player_entry_identified": False,
        "original_android_fresh_local_SAVE_written": False,
        "original_lv60_xp_catseye_reboot_passed": False,
        "original_sdk_ipc_zero_egress_verified": False,
        "original_apk_SAVE_pack_modified": False,
    }


def trace_exact_original_player_init_save(elf: bytes) -> dict[str, Any]:
    if sha256(elf).hexdigest() != NATIVE_SHA256:
        raise OriginalPlayerInitSaveTraceError(
            "only user's exact original JP15.7.1 native source is supported"
        )
    return inspect_original_player_init_save(elf)
