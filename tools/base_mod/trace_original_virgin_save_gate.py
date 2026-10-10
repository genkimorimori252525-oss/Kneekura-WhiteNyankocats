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


# Exact onCreate_loadSaveData-related libc++ aGameServices::Status lambda
# and real JNI update loop. These MAY participate in boot status progression,
# but DO NOT authorize faking an online success, new game SAVE or account.
ONCREATE_STATUS_ANCHORS = {
    0x31748C: 0xA9BD7BFD,  # real Android MyActivity_appInit JNI entry
    0x31753C: 0x141AC524,  # cold appInit -> 0x9c89cc
    0x9C89CC: 0xA9BD7BFD,  # original cold native initializer entry
    0x31755C: 0xD10143FF,  # real Android MyActivity_appUpdateDraw JNI entry
    0x3175EC: 0x941AC2B5,  # original per-frame update -> 0x9c80c0
    0x9C80C0: 0xD10203FF,  # native frame updater entry
    0x9C80E4: 0x97F54F90,  # get original application singleton
    0x9C8120: 0x36000F40,  # status check -> 0x9c8308
    0x9C8168: 0x540009A1,  # B.NE -> status callback installation
    0x9C82A0: 0xF0000A09,  # original registered lambda ADRP x9
    0x9C82A4: 0x9132A129,  # ADD x9,x9,#0xca8 -> 0xb0bca8
    0x9C82B4: 0xF9000BE9,  # store lambda vtable address
    0x9C82C4: 0xF9407508,  # game services virtual slot +0xe8
    0x9C82D0: 0xD63F0100,  # call service interface (not HTTP proof)
    0x9C9BB8: 0xA9BF7BFD,  # typed lambda invocation
    0x9C9BC0: 0x97F548D9,  # get original MyApplication
    0x9C9BC4: 0xF9400008,  # get MyApplication vtable
    0x9C9BC8: 0xF9401D01,  # vtable+0x38
    0x9C9BD0: 0xD61F0020,  # BR x1 into MyApplication virtual function
    0x724544: 0xD10303FF,  # resolved original app virtual method
    0x492B98: 0x940A192B,  # original worker resets STATE before save read
    0x492BE8: 0x9414A2DF,  # original worker THEN reads SAVE_DATA
    0x492BEC: 0x360009E0,  # SAVE load failure -> fail state
    0x492D2C: 0x39002668,  # worker failure flag
}

ONCREATE_DIRECT_CALLS = {
    0x3175EC: 0x9C80C0,
    0x9C80E4: 0x71BF24,
    0x9C9BC0: 0x71BF24,
    0x492B98: 0x719044,
    0x492BE8: 0x9BB764,
}

ONCREATE_RELOCATIONS = {
    0xB0BC78: 0x1F4B14,  # exact aGameServices::Status std::function type
    0xB0BC90: 0x1F4B92,  # exact lambda onCreate_loadSaveData name
    0xB0BCD8: 0x9C9BB8,  # lambda vtable invoked method
    0xAFD488: 0xAFD4E0,  # MyApplication vtable RTTI pointer
    0xAFD490: 0x71BF30,  # original MyApplication virtual initialization slot0
    0xAFD4C8: 0x724544,  # method +0x38 from address point 0xafd490
    0xAFD4E8: 0x1DA558,  # MyApplication type name
}

ONCREATE_RTTI = {
    0x1F4B14: b"NSt6__ndk110__function6__funcIZN13MyApplication21onCreate_loadSaveDataEvE3$_0NS_9allocatorIS3_EEFvN13aGameServices6StatusEEEE\x00",
    0x1F4B92: b"ZN13MyApplication21onCreate_loadSaveDataEvE3$_0\x00",
    0x1DA558: b"13MyApplication\x00",
}

ONCREATE_RELA_START = 0x9D2A8
ONCREATE_RELA_END = 0x12F708
ONCREATE_RELA_STEP = 24


def inspect_original_oncreate_save_status_callback(elf: bytes) -> dict[str, Any]:
    """Disambiguate original zero-initialized RAM from a valid virgin SAVE.

    The onCreate_loadSaveData-named lambda is installed on a services-status
    path inside the original native app's FRAME updater. When invoked it
    dispatches a MyApplication virtual method (+0x38). In this bounded lambda
    there is no SAVE writer call. The original loader worker seeds RAM first,
    but a missing SAVE still flows to its error flag. All claims are static.
    """
    for pc, expected in ONCREATE_STATUS_ANCHORS.items():
        if _u32(elf, pc) != expected:
            raise OriginalVirginSaveGateError(
                f"original onCreate status/worker opcode drift at 0x{pc:x}"
            )
    for pc, destination in ONCREATE_DIRECT_CALLS.items():
        if _bl_target(elf, pc) != destination:
            raise OriginalVirginSaveGateError(
                f"original onCreate call destination drift at 0x{pc:x}"
            )
    cold_start_branch = _u32(elf, 0x31753C)
    if (cold_start_branch & 0xFC000000) != 0x14000000:
        raise OriginalVirginSaveGateError("original JNI appInit direct B changed")
    cold_delta = _s(cold_start_branch & 0x03FFFFFF, 26) * 4
    if 0x31753C + cold_delta != 0x9C89CC:
        raise OriginalVirginSaveGateError("original JNI cold init target changed")
    if (_cond_target(elf, 0x492BEC, "tbz") != 0x492D28
        or _cond_target(elf, 0x9C8120, "tbz") != 0x9C8308):
        raise OriginalVirginSaveGateError("original frame/status or worker failure branch drift")
    original_branch = _u32(elf, 0x9C8168)
    if (original_branch & 0xFF00001F) != 0x54000001:
        raise OriginalVirginSaveGateError("original callback install must use B.NE")
    delta = _s((original_branch >> 5) & 0x7FFFF, 19)
    if 0x9C8168 + 4 * delta != 0x9C829C:
        raise OriginalVirginSaveGateError("original callback install branch target changed")
    for address, literal in ONCREATE_RTTI.items():
        if elf[address:address + len(literal)] != literal:
            raise OriginalVirginSaveGateError("original onCreate/MyApplication RTTI drift")
    observed: dict[int, int] = {}
    if len(elf) < ONCREATE_RELA_END:
        raise OriginalVirginSaveGateError("original native ELF relocation source truncated")
    for offset in range(ONCREATE_RELA_START, ONCREATE_RELA_END, ONCREATE_RELA_STEP):
        at, relocation_type, destination = struct.unpack_from("<QQq", elf, offset)
        if at not in ONCREATE_RELOCATIONS:
            continue
        if at in observed or relocation_type != 0x403:
            raise OriginalVirginSaveGateError("original onCreate RTTI/vtable relocation duplicate or drift")
        observed[at] = destination
    if observed != ONCREATE_RELOCATIONS:
        raise OriginalVirginSaveGateError("onCreate lambda or app vtable relocation mismatch")
    # Verify the ADRP/ADD pair rather than assuming the constructor's address.
    adrp = _u32(elf, 0x9C82A0)
    add = _u32(elf, 0x9C82A4)
    encoded_page = ((adrp >> 5) & 0x7FFFF) << 2 | ((adrp >> 29) & 3)
    if encoded_page & (1 << 20):
        encoded_page -= 1 << 21
    target_page = (0x9C82A0 & ~0xFFF) + (encoded_page << 12)
    if ((adrp & 31) != 9 or (add & 31) != 9
        or ((add >> 5) & 31) != 9
        or target_page + ((add >> 10) & 0xFFF) != 0xB0BCA8):
        raise OriginalVirginSaveGateError("original status lambda vtable address drift")
    bounded_lambda_writes = _direct_bl_to(elf, (0x9C9BB8, 0x9C9BD4), WRITER_TARGET)
    if bounded_lambda_writes:
        raise OriginalVirginSaveGateError("original lambda unexpectedly writes SAVE_DATA")
    return {
        "status": "ORIGINAL_ONCREATE_SAVEDATA_STATUS_LAMBDA_AND_PRELOAD_RAM_RESET_STATIC",
        "original_app_cold_init": "0x31748c JNI appInit; 0x31753c tail B -> 0x9c89cc",
        "original_app_update_draw": "0x31755c JNI appUpdateDraw; 0x3175ec -> 0x9c80c0",
        "cold_appInit_and_frame_GameServices_callback_are_distinct": True,
        "status_callback_name": "MyApplication::onCreate_loadSaveData()::$_0",
        "status_callback_type": "std::function<void(aGameServices::Status)>",
        "lambda_original_registration": "0x9c82a0 ADRP / 0x9c82a4 ADD -> 0xb0bca8",
        "services_status_callback_site": "0x9c82c4 virtual+0xe8; 0x9c82d0 BLR",
        "typed_lambda_entry": "0xb0bcd8 -> 0x9c9bb8",
        "typed_lambda_app_dispatch": "0x9c9bc0 singleton; 0x9c9bc8 app vtable+0x38; 0x9c9bd0 BR x1",
        "app_virtual_method_target": "0xafd490+0x38=0xafd4c8 -> 0x724544",
        "native_worker_initializes_RAM_first": "0x492b98 -> 0x719044",
        "native_worker_loads_existing_SAVE_second": "0x492be8 -> 0x9bb764",
        "native_worker_missing_save_still_fails": "0x492bec TBZ -> 0x492d28 -> 0x492d2c failure flag",
        "bounded_lambda_direct_SAVE_writer_calls": bounded_lambda_writes,
        "oncreate_status_callback_is_not_proven_native_new_player_writer": True,
        "state_zero_defaults_are_not_durable_new_profile": True,
        "actual_game_services_status_or_network_requirement_verified": False,
        "other_valid_original_virgin_creation_path_excluded": False,
        "original_native_game_local_first_boot_reboot_or_Lv60_passed": False,
        "user_owned_original_APK_or_SAVE_modified": False,
    }


# Original cold appInit (0x9c89cc) constructs the MyApplication virtual
# initialization path and dispatches scene102. Later update scene102 may
# dispatch the SAME application's vtable+0x38 and proceed to scene101.
# This is CONDITIONALLY reachable; not proof it happened on Android, and
# importantly does NOT establish an accepted missing-SAVE new player.
COLD_SCENE102_ANCHORS = {
    0x9C89CC: 0xA9BD7BFD,  # pinned original cold native entry
    0x9C8AFC: 0x97F54D0A,  # original application singleton
    0x9C8B00: 0xF9400008,  # load app vtable pointer
    0x9C8B04: 0xF9400108,  # load virtual slot 0
    0x9C8B08: 0xD63F0100,  # BLR x8 (vtable slot0)
    0x9C8B0C: 0x97F54D06,  # singleton again
    0x9C8B10: 0x97F54E10,  # original scene102 setup helper
    0x71BF30: 0xD10183FF,  # app initializer through vtable slot0
    0x71C350: 0xD10103FF,  # original scene setup helper
    0x71C3AC: 0xAA1303E0,  # x0 = original game app context
    0x71C3B0: 0x52800CC1,  # w1 = 102
    0x71C3B4: 0x94000015,  # dispatcher 0x71c408
    0x722CE8: 0x7101991F,  # update state == scene 102?
    0x722CEC: 0x54001A40,  # B.EQ -> scene102 frame handler
    0x723034: 0xB9403EA8,  # load scene102 state counter [x21,#0x3c]
    0x723044: 0x11000509,  # increment counter +1
    0x723048: 0xB9003EA9,  # store scene102 counter
    0x723058: 0x34000AAA,  # CBZ local flag -> 0x7231ac
    0x72305C: 0x71014D1F,  # cmp previous counter,#83
    0x723060: 0x54000A6C,  # B.GT -> 0x7231ac
    0x723064: 0x52800AA8,  # MOV 85 for counter reset on other side
    0x723068: 0xB9003EA8,  # store fallback counter
    0x72306C: 0x17FFFE48,  # back to per-frame return
    0x7231AC: 0x71018D1F,  # cmp previous counter,#99
    0x7231B0: 0x54FFBEEB,  # B.LT -> frame return, no scene101
    0x7231B4: 0xF9400268,  # load app vtable
    0x7231B8: 0xAA1303E0,  # x0 = app
    0x7231BC: 0xF9401D08,  # load virtual method vtable+0x38
    0x7231C0: 0xD63F0100,  # BLR x8
    0x7231C4: 0xAA1303E0,  # x0 = app
    0x7231C8: 0x52800CA1,  # w1 = scene101
    0x7231CC: 0x97FFE48F,  # dispatcher 0x71c408
    0x7231D0: 0x17FFFE41,  # frame return
    0x71C6E4: 0x7101951F,  # scene101 app scene-dispatch check
    0x71C6E8: 0x54007D41,  # if not scene101, skip
    0x71C9B0: 0x97F1031C,  # native SAVE_DATA existence probe
    0x71C9C8: 0x36004214,  # absence -> AppLaunchLoad creation route
}
COLD_SCENE102_DIRECT_CALLS = {
    0x9C8AFC: 0x71BF24,
    0x9C8B0C: 0x71BF24,
    0x9C8B10: 0x71C350,
    0x71C3B4: 0x71C408,
    0x7231CC: 0x71C408,
    0x71C9B0: 0x35D620,
}
COLD_SCENE102_CONDITIONAL_BRANCHES = {
    0x722CEC: ("b.eq", 0x723034),
    0x723058: ("cbz", 0x7231AC),
    0x723060: ("b.gt", 0x7231AC),
    0x72306C: ("b", 0x72298C),
    0x7231B0: ("b.lt", 0x72298C),
    0x7231D0: ("b", 0x722AD4),
}


def _cold_scene_branch_target(elf: bytes, pc: int, kind: str) -> int:
    word = _u32(elf, pc)
    if kind in ("b.eq", "b.gt", "b.lt"):
        condition = {"b.eq": 0, "b.gt": 12, "b.lt": 11}[kind]
        if word & 0xFF00001F != 0x54000000 | condition:
            raise OriginalVirginSaveGateError("original scene102 conditional branch kind drift")
        offset, bits = (word >> 5) & 0x7FFFF, 19
    elif kind == "cbz":
        if word & 0x7F000000 != 0x34000000:
            raise OriginalVirginSaveGateError("original scene102 CBZ changed")
        offset, bits = (word >> 5) & 0x7FFFF, 19
    elif kind == "b":
        if word & 0xFC000000 != 0x14000000:
            raise OriginalVirginSaveGateError("original scene102 direct branch changed")
        offset, bits = word & 0x03FFFFFF, 26
    else:
        raise OriginalVirginSaveGateError("unsupported original scene102 edge type")
    return pc + _s(offset, bits) * 4


def inspect_original_cold_scene102_to_101(elf: bytes) -> dict[str, Any]:
    """Exact source-only path: JNI cold start -> scene102 -> guarded scene101.

    The first MyApplication vtable entry and scene102 frame handler are
    source-pinned. The virtual method at +0x38 also appears in the typed
    onCreate_loadSaveData Status lambda, but calling it in one path is NOT
    proof the same callback or online status is needed in another path.
    No original new player save is synthesized and no server calls are made.
    """
    for pc, word in COLD_SCENE102_ANCHORS.items():
        if _u32(elf, pc) != word:
            raise OriginalVirginSaveGateError(
                f"original cold scene102 opcode changed at 0x{pc:x}"
            )
    for pc, expected in COLD_SCENE102_DIRECT_CALLS.items():
        if _bl_target(elf, pc) != expected:
            raise OriginalVirginSaveGateError(
                f"original cold scene102 direct call drift at 0x{pc:x}"
            )
    for pc, (kind, target) in COLD_SCENE102_CONDITIONAL_BRANCHES.items():
        if _cold_scene_branch_target(elf, pc, kind) != target:
            raise OriginalVirginSaveGateError(
                f"original cold scene102 branch destination drift at 0x{pc:x}"
            )
    # Original onCreate callback's relocation validator includes all
    # MyApplication vtable slots below; do not assume a literal pointer.
    _init_slot = ONCREATE_RELOCATIONS.get(0xAFD490)
    _status_slot = ONCREATE_RELOCATIONS.get(0xAFD4C8)
    if _init_slot != 0x71BF30 or _status_slot != 0x724544:
        raise OriginalVirginSaveGateError("original MyApplication vtable source changed")
    if ((_u32(elf, 0x71C3B0) >> 5) & 0xFFFF) != 102:
        raise OriginalVirginSaveGateError("original cold scene number no longer 102")
    if ((_u32(elf, 0x7231C8) >> 5) & 0xFFFF) != 101:
        raise OriginalVirginSaveGateError("original next scene number no longer 101")
    for at, expected in ((0x722CE8, 102), (0x72305C, 83), (0x7231AC, 99)):
        if ((_u32(elf, at) >> 10) & 0xFFF) != expected:
            raise OriginalVirginSaveGateError(
                f"original scene102 state/counter condition drift at 0x{at:x}"
            )
    for start, end in (
        (0x9C8AFC, 0x9C8B14),
        (0x71C3AC, 0x71C3B8),
        (0x723034, 0x723070),
        (0x7231AC, 0x7231D4),
    ):
        if _direct_bl_to(elf, (start, end), WRITER_TARGET):
            raise OriginalVirginSaveGateError(
                "unexpected original direct SAVE writer in guarded cold scene slice"
            )
    # Original ELF .eh_frame identifies the selected MyApplication virtual
    # routine's direct function body as 0x724544..0x725744. This bounded
    # direct-BL survey does NOT exclude indirect or transitive SAVE writes.
    virtual_direct_saves = _direct_bl_to(
        elf, (0x724544, 0x725744), WRITER_TARGET,
    )
    if virtual_direct_saves:
        raise OriginalVirginSaveGateError(
            "original scene102 app virtual now directly writes SAVE_DATA"
        )
    return {
        "status": "PINNED_ORIGINAL_COLD_SCENE102_GUARDED_SCENE101_TRANSITION",
        "original_cold_native_entry": "0x31753c -> 0x9c89cc",
        "original_cold_app_virtual_init": "0x9c8afc app singleton; 0x9c8b00/04/08 vtable+0 -> 0x71bf30",
        "initial_scene": "0x9c8b10 -> 0x71c350; 0x71c3b0 w1=102; 0x71c3b4 -> 0x71c408",
        "original_frame_scene102": "0x722ce8 CMP #102; 0x722cec BEQ -> 0x723034",
        "frame_counter": "0x723034 [x21+0x3c], 0x723044 +1, 0x723048 STR",
        "frame_local_state_gate": "0x723058 CBZ -> 0x7231ac, else 0x72305c CMP #83 and 0x723060 B.GT -> 0x7231ac; else 0x723064 resets counter to85",
        "guard_for_scene101": "0x7231ac CMP prior counter #99; 0x7231b0 B.LT -> 0x72298c",
        "application_virtual_before_scene101": "0x7231b4/1bc/1c0 vtable+0x38 -> 0x724544",
        "original_virtual_method_unwind_range": "0x724544..0x725744 (ELF .eh_frame)",
        "bounded_virtual_method_direct_SAVE_writer_calls": virtual_direct_saves,
        "transitive_or_indirect_SAVE_writer_calls_excluded": False,
        "conditional_next_scene": "0x7231c8 w1=101; 0x7231cc -> 0x71c408",
        "scene101_save_probe": "0x71c6e4 CMP #101; 0x71c9b0 -> 0x35d620; 0x71c9c8 absent SAVE -> AppLaunchLoad path",
        "conditional_source_control_flow_reaches_scene101": True,
        "frame_counter_gate_guaranteed_to_pass_in_real_offline_app": False,
        "original_virtual_status_check_guaranteed_success_offline": False,
        "native_missing_save_creates_valid_virgin_player": False,
        "real_original_scene102_or_101_seen_on_device": False,
        "real_native_game_first_run_or_SAVE_written": False,
        "original_APK_SAVE_or_owner_assets_modified": False,
    }


def trace_exact_original_virgin_save_gate(elf: bytes) -> dict[str, Any]:
    if sha256(elf).hexdigest() != NATIVE_SHA256:
        raise OriginalVirginSaveGateError(
            "original virgin SAVE analysis only supports owner's exact JP15.7.1"
        )
    report = inspect_original_virgin_save_failure(elf)
    report["original_oncreate_savedata_status_callback"] = (
        inspect_original_oncreate_save_status_callback(elf)
    )
    report["original_cold_scene102_guarded_scene101"] = (
        inspect_original_cold_scene102_to_101(elf)
    )
    return report
