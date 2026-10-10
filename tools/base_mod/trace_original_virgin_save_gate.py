"""Pinned original JP15.7.1 virgin-SAVE failure path, read-only.

This is a NEGATIVE first-boot gate: the original AppLaunchLoad worker reads
SAVE_DATA and propagates missing/invalid SAVE failure. It does not prove
whether a separate legitimate first-run player-state generator exists, and
does not create or modify any game's or publisher's save/account.
"""
from __future__ import annotations

from hashlib import sha256
import struct
from typing import Any

NATIVE_SHA256 = "333d2974ab2ff881fd70087fd62dea7d12d82addbc55cab2f2a675ad67e3a7e2"

FIRST_BOOT_ANCHORS = {
    0x71C9B0: 0x97F1031C,  # original SAVE_DATA exists?
    0x71C9C8: 0x36004214,  # absent -> original AppLaunchLoad construction
    0x71D30C: 0x97F5D4FB,  # original AppLaunchLoad native constructor
    0x4926F8: 0xD10283FF,  # AppLaunchLoad constructor entry
    0x492730: 0xB00032E8,  # original class vtable target
    0x492738: 0xF9000008,  # stores AppLaunchLoad vtable
    0x4931FC: 0xF9403C00,  # worker takes original context
    0x493200: 0x97FFFE60,  # calls original worker
    0x492BD4: 0x9414A408,  # worker first initializes game tables
    0x492BE8: 0x9414A2DF,  # worker then tries saved game load
    0x492BEC: 0x360009E0,  # failed saved load -> worker failure branch
    0x492D28: 0x52800028,  # set failure state = 1
    0x492D2C: 0x39002668,  # worker state failure byte [x19 + 9]
    0x9BBD28: 0x97FFC6E4,  # first concrete table opened by initializer
    0x9BBEDC: 0x97FFC677,  # another concrete TSV opened by initializer
    0x9BB764: 0xD102C3FF,  # save-loading wrapper (not constructor)
    0x9BB78C: 0x97FBE306,  # original SAVE_DATA reader
    0x9BB794: 0x36001580,  # original SAVE read failed -> return false
    0x8B43A4: 0xD10443FF,  # SAVE_DATA reader entry
    0x8B4404: 0x97EAA487,  # SAVE_DATA reader file open
    0x8B441C: 0x36000774,  # missing file -> failed reader branch
    0x723448: 0x39402508,  # frame update observes failure flag
    0x72344C: 0x34FFAA88,  # no failure -> wait; failure -> scene4
    0x723458: 0x52800081,  # original scene4 number
    0x723460: 0x97FFE3EA,  # native scene transition
}
DIRECT_BL = {
    0x71C9B0: 0x35D620,
    0x71D30C: 0x4926F8,
    0x493200: 0x492B80,
    0x492BD4: 0x9BBBF4,
    0x492BE8: 0x9BB764,
    0x9BBD28: 0x9AD8B8,
    0x9BBEDC: 0x9AD8B8,
    0x9BB78C: 0x8B43A4,
    0x8B4404: 0x35D620,
    0x723460: 0x71C408,
}
CONDITIONAL_BRANCHES = {
    0x71C9C8: ("tbz", 0x71D208),
    0x492BEC: ("tbz", 0x492D28),
    0x9BB794: ("tbz", 0x9BBA44),
    0x8B441C: ("tbz", 0x8B4508),
    0x72344C: ("cbz", 0x72299C),
}
# Only check a *bounded* direct-call survey. Virtual / later calls and other
# code paths are explicitly NOT excluded by this negative local fact.
CONSTRUCTOR_DIRECT_BL_SURVEY = (0x4926F8, 0x492B80)
WORKER_DIRECT_BL_SURVEY = (0x492B80, 0x492D40)
WRITER_TARGET = 0x8B9FC8


class OriginalVirginSaveGateError(ValueError):
    """Exact original source differs from the independently observed flow."""


def _s(value: int, width: int) -> int:
    return value - (1 << width) if value & (1 << (width - 1)) else value


def _u32(elf: bytes, pc: int) -> int:
    if not 0 <= pc < len(elf) - 3:
        raise OriginalVirginSaveGateError("original native source truncated")
    return struct.unpack_from("<I", elf, pc)[0]


def _bl_target(elf: bytes, pc: int) -> int:
    w = _u32(elf, pc)
    if (w & 0xFC000000) != 0x94000000:
        raise OriginalVirginSaveGateError("expected ARM64 direct BL")
    return pc + _s(w & 0x03FFFFFF, 26) * 4


def _cond_target(elf: bytes, pc: int, mode: str) -> int:
    w = _u32(elf, pc)
    if mode == "tbz":
        if (w & 0x7F000000) != 0x36000000:
            raise OriginalVirginSaveGateError("expected ARM64 TBZ")
        offset, width = (w >> 5) & 0x3FFF, 14
    elif mode == "cbz":
        if (w & 0x7F000000) != 0x34000000:
            raise OriginalVirginSaveGateError("expected ARM64 CBZ")
        offset, width = (w >> 5) & 0x7FFFF, 19
    else:
        raise OriginalVirginSaveGateError("unsupported original branch")
    return pc + _s(offset, width) * 4


def _direct_bl_to(elf: bytes, region: tuple[int, int], target: int) -> list[str]:
    start, end = region
    if start < 0 or end > len(elf) or end <= start or (start | end) & 3:
        raise OriginalVirginSaveGateError("invalid original bounded code region")
    calls = []
    for pc in range(start, end, 4):
        w = _u32(elf, pc)
        if (w & 0xFC000000) == 0x94000000 and (
            pc + _s(w & 0x03FFFFFF, 26) * 4 == target
        ):
            calls.append(f"0x{pc:x}")
    return calls


def inspect_original_virgin_save_failure(elf: bytes) -> dict[str, Any]:
    """If this original worker attempts an absent save, it records failure.

    Does NOT claim AppLaunchLoad is the only valid original virgin route.
    """
    for pc, value in FIRST_BOOT_ANCHORS.items():
        if _u32(elf, pc) != value:
            raise OriginalVirginSaveGateError(f"original SAVE opcode changed 0x{pc:x}")
    for pc, dest in DIRECT_BL.items():
        if _bl_target(elf, pc) != dest:
            raise OriginalVirginSaveGateError(f"original SAVE BL target changed 0x{pc:x}")
    for pc, (kind, dest) in CONDITIONAL_BRANCHES.items():
        if _cond_target(elf, pc, kind) != dest:
            raise OriginalVirginSaveGateError(f"original SAVE branch changed 0x{pc:x}")
    if (elf[0x191955:0x19195F] != b"SAVE_DATA\x00"
        or elf[0x1A47F8:0x1A4805] != b"Map_Name.csv\x00"
        or elf[0x193AA0:0x193AAD] != b"Matatabi.tsv\x00"):
        raise OriginalVirginSaveGateError("original save/data-loader filename drift")
    constructor_writes = _direct_bl_to(elf, CONSTRUCTOR_DIRECT_BL_SURVEY, WRITER_TARGET)
    worker_writes = _direct_bl_to(elf, WORKER_DIRECT_BL_SURVEY, WRITER_TARGET)
    if constructor_writes or worker_writes:
        raise OriginalVirginSaveGateError(
            "original AppLaunchLoad constructor/worker new direct SAVE writer call"
        )
    return {
        "status": "ORIGINAL_APP_LAUNCH_WORKER_MISSING_SAVE_FAILURE_CHAIN_STATIC",
        "absent_save_scene101_branch": "0x71c9c8 TBZ -> 0x71d208; 0x71d30c -> 0x4926f8",
        "original_app_launch_constructor": "0x4926f8 AppLaunchLoad",
        "async_worker_call": "0x493200 -> 0x492b80",
        "initializer_before_save_read": "0x492bd4 -> 0x9bbbf4 (includes Map_Name.csv and Matatabi.tsv table readers)",
        "original_save_read": "0x492be8 -> 0x9bb764 -> 0x8b43a4",
        "save_absent_open_failure": "0x8b441c TBZ -> 0x8b4508",
        "failure_propagates_to_worker": "0x9bb794 TBZ -> 0x9bba44; 0x492bec TBZ -> 0x492d28",
        "worker_failure_field": "0x492d28 sets 1; 0x492d2c STRB worker+9",
        "observed_frame_failure_route": "0x723448 reads worker+9; 0x72344c CBZ waits if clear; else 0x723458 scene4",
        "bounded_constructor_direct_calls_to_original_save_writer": constructor_writes,
        "bounded_worker_direct_calls_to_original_save_writer": worker_writes,
        "this_worker_attempting_missing_SAVE_reports_error_static_proven": True,
        "all_original_virgin_initialization_paths_excluded": False,
        "fresh_local_original_native_profile_generator_identified": False,
        "any_sdk_ipc_zero_egress_hardware_run_verified": False,
        "original_player_save_or_apk_modified": False,
    }


def trace_exact_original_virgin_save_gate(elf: bytes) -> dict[str, Any]:
    if sha256(elf).hexdigest() != NATIVE_SHA256:
        raise OriginalVirginSaveGateError(
            "original virgin SAVE analysis only supports owner's exact JP15.7.1"
        )
    return inspect_original_virgin_save_failure(elf)
