"""Exact owner JP15.7.1 native direct-call census for player state initialization.

Identify EVERY direct ARM64 BL into the original RAM initializer and the
multi-subsystem reset aggregator, then classify *observed caller context* by
source rodata references. Other indirect/virtual calls are NOT excluded.
No binary/SAVE mutation, device access or publisher network requests.
"""
from __future__ import annotations

from hashlib import sha256
import struct
from typing import Any

NATIVE_SHA256 = "333d2974ab2ff881fd70087fd62dea7d12d82addbc55cab2f2a675ad67e3a7e2"
TEXT_START = 0x317370
TEXT_END = 0xAD751C
STATE_DEFAULT_INITIALIZER = 0x719044
SUBSYSTEM_RESET = 0x89385C
ORIGINAL_SAVE_WRITER = 0x8B9FC8
ORIGINAL_SAVE_READER_WORKER = 0x9BB764
TARGETS = (
    STATE_DEFAULT_INITIALIZER, SUBSYSTEM_RESET,
    ORIGINAL_SAVE_WRITER, ORIGINAL_SAVE_READER_WORKER,
)
EXPECTED_DIRECT_INIT_CALLERS = (
    0x492B98,  # AppLaunchLoad: first initialize RAM before reading save
    0x71F338,  # normal MyApplication initialization
    0x89386C,  # common subsystem reset, called from transfer/reset contexts
    0x934028,  # title restart_reflect and selected reset path
)
EXPECTED_DIRECT_RESET_CALLERS = (
    0x748B38,  # kisyuhen_02_kisyuhen02, followed by native saver
    0x74906C,  # transfer_backup before original binary deserializer
    0x749444,  # data_download_error_could_not_load branch of restore
    0x74962C,  # companion failed source-restore callback branch
    0x749E80,  # MyGameServicesDelegate state 9 and native saver
    0x776584,  # AccountDelete callback reset and native saver
)
EXPECTED_DIRECT_SAVE_READER_CALLERS = (0x492BE8,)
EXPECTED_NATIVE_SAVE_WRITER_DIRECT_SITE_COUNT = 158
# Exactly pinned AArch64 adrps + adds and NUL-terminated original labels.
# These labels are source evidence only, not authorization to use the
# publisher's transfer/backup/delete flows to generate a new local SAVE.
ORIGINAL_CALLER_CONTEXT_LABELS = (
    (0x748AD8, 0x1A6756, "kisyuhen_02_kisyuhen02"),
    (0x74902C, 0x1AE9F9, "transfer_backup"),
    (0x749420, 0x191993, "data_download_error_could_not_load"),
    (0x749E28, 0x1AFB46, "kisyuhen_03_hikitugi02"),
    (0x7765D4, 0x1A82BD, "AccountDelete_error02"),
)


class OriginalInitCensusError(ValueError):
    """Only source-proven direct calls qualify; reject native version drift."""


def _signed(value: int, bits: int) -> int:
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def direct_call_census(
    native: bytes,
    targets: tuple[int, ...] = TARGETS,
    *,
    text_start: int = TEXT_START,
    text_end: int = TEXT_END,
) -> dict[int, list[int]]:
    """Decode all direct ARM64 BLs in caller-supplied .text bounds.

    This intentionally excludes BLR/BR (indirect), dynamic dispatch,
    post-load rewriting and other binaries. Scan once for all targets.
    """
    if (not isinstance(native, bytes) or not isinstance(targets, tuple)
        or not targets or any(type(v) is not int or v < 0 for v in targets)
        or len(targets) != len(set(targets))
        or any(type(v) is not int for v in (text_start, text_end))
        or text_start < 0 or text_start % 4 or text_end % 4
        or text_end > len(native) or text_end <= text_start):
        raise OriginalInitCensusError("invalid original code bounds or targets")
    found: dict[int, list[int]] = {target: [] for target in targets}
    for pc in range(text_start, text_end, 4):
        opcode = struct.unpack_from("<I", native, pc)[0]
        if opcode & 0xFC000000 != 0x94000000:
            continue
        destination = pc + _signed(opcode & 0x03FFFFFF, 26) * 4
        if destination in found:
            found[destination].append(pc)
    return found


def _verify_owner_context_labels(native: bytes) -> list[dict[str, Any]]:
    verified = []
    for pc, string_at, literal in ORIGINAL_CALLER_CONTEXT_LABELS:
        expected_bytes = literal.encode("ascii") + b"\x00"
        if native[string_at:string_at + len(expected_bytes)] != expected_bytes:
            raise OriginalInitCensusError(
                f"original transfer/account source label changed at 0x{string_at:x}"
            )
        adrp, add = struct.unpack_from("<II", native, pc)
        if (adrp & 0x9F000000 != 0x90000000
            or add & 0xFF000000 != 0x91000000):
            raise OriginalInitCensusError(
                f"original caller context ADRP/ADD drift at 0x{pc:x}"
            )
        rd = adrp & 31
        if add & 31 != rd or (add >> 5) & 31 != rd:
            raise OriginalInitCensusError(
                f"original caller context register mismatch at 0x{pc:x}"
            )
        page_displacement = ((adrp >> 5) & 0x7FFFF) << 2 | ((adrp >> 29) & 3)
        page = (pc & ~0xFFF) + (_signed(page_displacement, 21) << 12)
        immediate = ((add >> 10) & 0xFFF) << (12 if (add >> 22) & 1 else 0)
        if page + immediate != string_at:
            raise OriginalInitCensusError(
                f"original caller context rodata xref drift at 0x{pc:x}"
            )
        verified.append({
            "adrp_at": f"0x{pc:x}",
            "source_label": literal,
            "original_rodata_at": f"0x{string_at:x}",
        })
    return verified


def inspect_direct_original_player_init_callers(native: bytes) -> dict[str, Any]:
    """A static negative gate: four direct init callsites; six reset uses.

    This does not prove that a legitimate virgin profile constructor is
    absent; only that it is NOT evidenced by the surveyed direct calls.
    """
    results = direct_call_census(native)
    if tuple(results[STATE_DEFAULT_INITIALIZER]) != EXPECTED_DIRECT_INIT_CALLERS:
        raise OriginalInitCensusError("original RAM state initializer direct caller drift")
    if tuple(results[SUBSYSTEM_RESET]) != EXPECTED_DIRECT_RESET_CALLERS:
        raise OriginalInitCensusError("original subsystem reset direct caller drift")
    if tuple(results[ORIGINAL_SAVE_READER_WORKER]) != EXPECTED_DIRECT_SAVE_READER_CALLERS:
        raise OriginalInitCensusError("original save-loader wrapper caller drift")
    if len(results[ORIGINAL_SAVE_WRITER]) != EXPECTED_NATIVE_SAVE_WRITER_DIRECT_SITE_COUNT:
        raise OriginalInitCensusError("original SAVE writer direct BL count drift")
    labels = _verify_owner_context_labels(native)
    return {
        "status": "EXHAUSTIVE_ORIGINAL_AARCH64_DIRECT_INIT_AND_RESET_CALLER_CENSUS",
        "text_range": "0x317370..0xad751c (end exclusive)",
        "state_initializer": "0x719044",
        "state_initializer_direct_bl_sites": [
            f"0x{pc:x}" for pc in results[STATE_DEFAULT_INITIALIZER]
        ],
        "state_initializer_direct_site_count": len(results[STATE_DEFAULT_INITIALIZER]),
        "common_reset_aggregator": "0x89385c",
        "common_reset_direct_bl_sites": [
            f"0x{pc:x}" for pc in results[SUBSYSTEM_RESET]
        ],
        "common_reset_direct_site_count": len(results[SUBSYSTEM_RESET]),
        "original_SAVE_writer_direct_bl_site_count": len(results[ORIGINAL_SAVE_WRITER]),
        "original_SAVE_reader_worker_direct_bl_sites": [
            f"0x{pc:x}" for pc in results[ORIGINAL_SAVE_READER_WORKER]
        ],
        "transfer_and_account_context_source_labels": labels,
        "direct_init_categories": {
            "0x492b98": "AppLaunchLoad worker seeds RAM before existing SAVE read",
            "0x71f338": "MyApplication constructor/init vtable dispatch",
            "0x89386c": "subsystem reset aggregator",
            "0x934028": "TitleUpdate reset path",
        },
        "reset_caller_context": {
            "0x748b38": "kisyuhen_02 transfer screen, native SAVE follows",
            "0x74906c": "transfer_backup source, restore/deserializer follows",
            "0x749444": "restore failure-side source read after reset",
            "0x74962c": "same restore path later callback branch",
            "0x749e80": "GameServicesDelegate state 9 reset (kisyuhen context), native SAVE follows",
            "0x776584": "miniBrowser AccountDelete callback, native SAVE follows",
        },
        "direct_caller_survey_complete_for_exact_original_text": True,
        "indirect_BLR_or_virtual_reset_callers_excluded": False,
        "other_player_state_initializers_excluded": False,
        "transfer_restore_delete_flow_is_verified_virgin_profile": False,
        "legitimate_original_new_player_SAVE_constructor_identified": False,
        "native_original_game_offline_first_boot_verified": False,
        "user_private_original_APK_SAVE_or_assets_modified": False,
    }


def inspect_exact_owner_original_init_callers(native: bytes) -> dict[str, Any]:
    if sha256(native).hexdigest() != NATIVE_SHA256:
        raise OriginalInitCensusError("only user's exact original JP15.7.1 ELF is supported")
    return inspect_direct_original_player_init_callers(native)
