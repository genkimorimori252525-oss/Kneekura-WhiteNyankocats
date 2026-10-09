"""Read-only native callsite locator for real JP15.7.1 Battle Cats level-up UI.

Find the exact binary's (ADRP page -> ADD register, within four instructions)
references to level-up/catseye resource names and unitbuy.csv. This reveals
real code locations for focused disassembly instead of coding a fake upgrade
screen. It does NOT assert those code locations are actual level-cap getters;
no patch, bypass, save access, APK signing, network or phone interaction.

Source: user's unmodified JP15.7.1 ARM64 split_config.arm64_v8a.apk.
Original ELF data/rodata and VMA are offset-identical for this PINNED build.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import struct
from typing import Any
from zipfile import ZipFile

SOURCE_EXPORT_SHA256 = (
    "38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56"
)
NATIVE_SHA256 = (
    "333d2974ab2ff881fd70087fd62dea7d12d82addbc55cab2f2a675ad67e3a7e2"
)
# Real ELF section addresses (validated solely by the pinned source hash).
TEXT_START = 0x317370
TEXT_END = 0xAD751C
SOURCE_APK_NAME = "apk/split_config.arm64_v8a.apk"
ELF_APK_NAME = "lib/arm64-v8a/libnative-lib.so"

# Only exact original text identifiers. No speculative native function names.
CUES = {
    "unit_data_file": "unitbuy.csv",
    "native_activity_files_dir": "getFilesDir",
    "unit_level_file": "unitlevel.csv",
    "unit_xp_file": "unitexp.csv",
    "catseye_screen_resource": "BcResCatsEyeLevelUp",
    "catseye_levelup_name": "CatsEyeLevelUp",
    "max_level_popup_first": "drop_popup_chara_levelmax1",
    "max_level_popup_second": "drop_popup_chara_levelmax2",
    "potential_skill_max": "potential_skill_MaxLevel",
    "recommended_levelup_table": "Recommended_levelup.csv",
    "original_save_file": "SAVE_DATA",
    "original_save4_file": "SAVE_DATA4",
    "original_save8_file": "SAVE_DATA8",
}

# Proven direct ADRP+ADD disassembly sites from *this exact native SHA only*.
EXPECTED_ANCHORS = {
    "unit_data_file": {0x8A2C60},
    "native_activity_files_dir": {0x45AA3C},
    # Direct filename xrefs do NOT identify the durable serializer/writer.
    "original_save_file": {0x71C984, 0x74B13C, 0x8B43D0, 0x8B9FDC, 0x8C5334},
    "original_save4_file": {0x7EDD54, 0x8BA0B0, 0x8C1D30},
    "original_save8_file": {0x748E00, 0x74AD74, 0x74AF48},
    "catseye_screen_resource": {0x942B64},
    "max_level_popup_first": {0x4E3070},
    "max_level_popup_second": {0x4E3238},
    "potential_skill_max": {0x4A1A9C},
    "recommended_levelup_table": {0x88A170},
}


class LevelUpNativeTraceError(ValueError):
    pass


def _hex(value: int) -> str:
    return f"0x{value:x}"


def _u32(elf: bytes, at: int) -> int:
    return struct.unpack_from("<I", elf, at)[0]


def _sign_extend(value: int, width: int) -> int:
    return value - (1 << width) if value & (1 << (width - 1)) else value


def direct_adrp_add_refs(
    elf: bytes, string_va: int, *, text_start: int, text_end: int
) -> list[dict[str, Any]]:
    """Decode two real AArch64 instructions; never guess indirect call flow.

    Matches ADRP Rd, page(text); ADD Xd, Xd, #low12 near the ADRP,
    without crossing the caller's requested .text bounds.
    """
    if (not isinstance(elf, bytes) or not isinstance(string_va, int)
        or not isinstance(text_start, int) or not isinstance(text_end, int)
        or text_start < 0 or text_start % 4 or text_end % 4
        or text_end > len(elf) or text_end < text_start + 8):
        raise LevelUpNativeTraceError("invalid AArch64 ELF text bounds")
    references = []
    page_target = string_va & ~0xFFF
    for pc in range(text_start, text_end - 4, 4):
        first = _u32(elf, pc)
        if first & 0x9F000000 != 0x90000000:  # ADRP
            continue
        distance = (((first >> 5) & 0x7FFFF) << 2) | ((first >> 29) & 3)
        page = (pc & ~0xFFF) + (_sign_extend(distance, 21) << 12)
        if page != page_target:
            continue
        rd = first & 31
        for advance in (4, 8, 12, 16):
            if pc + advance + 4 > text_end:
                continue
            second = _u32(elf, pc + advance)
            if (second & 0xFF000000 != 0x91000000   # ADD Xd,Xn,#imm
                or second & 31 != rd
                or (second >> 5) & 31 != rd):
                continue
            immediate = ((second >> 10) & 0xFFF) << (
                12 if ((second >> 22) & 1) else 0
            )
            if page + immediate == string_va:
                references.append({
                    "adrp_address": _hex(pc),
                    "add_address": _hex(pc + advance),
                    "register": f"x{rd}",
                    "adrp_opcode_le": _hex(first),
                    "add_opcode_le": _hex(second),
                })
    return references


def _decode_relative_bl(elf: bytes, address: int) -> int:
    instruction = _u32(elf, address)
    if instruction & 0xFC000000 != 0x94000000:
        raise LevelUpNativeTraceError("expected direct ARM64 BL, not a pointer guess")
    displacement = _sign_extend(instruction & 0x03FFFFFF, 26) * 4
    return address + displacement


def _popup_value_call_chain(elf: bytes) -> dict:
    """Confirm original level-max popup compares an OBFUSCATED count.

    Original 0x9cbf94 calls byte-wise XOR decoder 0x9d8718, masks the
    decoded integer's low 16 bits, clamps to 50,000, and returns the value.
    That is NOT proof it is a per-unit allowed level (60/50/20/1).
    """
    if _decode_relative_bl(elf, 0x4E3060) != 0x9CBF94:
        raise LevelUpNativeTraceError("levelmax popup value callee drifted")
    if _decode_relative_bl(elf, 0x9CBF9C) != 0x9D8718:
        raise LevelUpNativeTraceError("popup value decode callee drifted")
    expected = {
        0x9CBFA0: 0x52986A08,  # mov w8,#0xc350 (=50000)
        0x9CBFA4: 0x12003C09,  # and w9,w0,#0xffff
        0x9CBFA8: 0x6B08013F,  # cmp w9,w8
        0x9CBFAC: 0x1A883120,  # csel w0,w9,w8,lo
    }
    if any(_u32(elf, where) != word for where, word in expected.items()):
        raise LevelUpNativeTraceError("popup value clamp calculation drifted")
    return {
        "caller": "0x4e3060",
        "value_reader": "0x9cbf94",
        "decoder": "0x9d8718",
        "return_expression": "min((decoded_32bit & 0xffff), 50000)",
        "comparison_at": "0x4e3068",
        "compared_to": 1,
        "original_level_cap_getter_proven": False,
        "uncertainty": "Returned 0/1+ value selects popup variant, but meaning of decoded field remains unresolved",
    }


def _levelmax_popup_branch(elf: bytes) -> dict:
    """Exact JP UI branch between two original level-max popup strings.

    The condition's actual gameplay meaning is UNKNOWN. We validate control
    flow only; no assumption this computes a unit's native effective cap.
    """
    compare_addr = 0x4E3068
    branch_addr = 0x4E306C
    if _u32(elf, compare_addr) != 0x7100041F:
        raise LevelUpNativeTraceError("original max-level popup compare drifted")
    instruction = _u32(elf, branch_addr)
    if instruction != 0x54000E61:  # b.ne (condition=NE)
        raise LevelUpNativeTraceError("original max-level conditional branch drifted")
    distance = _sign_extend((instruction >> 5) & 0x7FFFF, 19) * 4
    target = branch_addr + distance
    if target != 0x4E3238:
        raise LevelUpNativeTraceError("level-max popup branch target drifted")
    return {
        "compare_address": _hex(compare_addr),
        "compare_instruction": "cmp w0, #1",
        "conditional_address": _hex(branch_addr),
        "conditional_branch": "b.ne",
        "branch_target": _hex(target),
        "fallthrough_label": "drop_popup_chara_levelmax1",
        "branch_label": "drop_popup_chara_levelmax2",
        "underlying_upgrade_limit_getter_identified": False,
    }



# Original-game asset loader evidence, pinned to JP15.7.1 exact native hash.
# Important: the three source files share this one function but target DIFFERENT
# in-memory arrays. NEVER confuse unitlevel.csv col18 with unitbuy.csv col18.
ORIGINAL_UNIT_DATA_ANCHORS = {
    0x8A2C30: 0xAA0003F3,  # game context x0 saved in x19
    0x8A2C60: 0xB0FFC848,  # unitbuy.csv ADRP
    0x8A2C64: 0x91268D08,  # unitbuy.csv ADD
    0x8A2C88: 0x94042B0C,  # open unitbuy.csv
    0x8A2CB8: 0x91018118,  # per-cat encoded unitbuy data (context+0x4b060)
    0x8A2CBC: 0x91018539,  # decoded destination (context+0x4b061)
    0x8A2CC8: 0x8B17231A,  # index*256
    0x8A2CD8: 0x2A1303E1,  # w1 = col number (0..62)
    0x8A2CDC: 0x97EB0388,  # read unitbuy col
    0x8A2CE0: 0x3943F348,  # load XOR key byte0 at record+0xfc
    0x8A2CEC: 0x4A000108,  # XOR parsed byte with key
    0x8A2CF0: 0x381FF368,  # write decoded byte0
    0x8A2D18: 0x9100137B,  # dest pointer += 4
    0x8A2D1C: 0x54FFFDC1,  # next col while index<63
    0x8A2D24: 0x91040339,  # next cat record +=256
    0x8A2D28: 0xF10DCAFF,  # 882 cat records
    0x8A2D2C: 0x54FFFCA1,  # next unitbuy cat record
    0x8A2D38: 0x90FFC789,  # unitlevel.csv ADRP
    0x8A2D3C: 0x91253929,  # unitlevel.csv ADD
    0x8A2D6C: 0x94042AD3,  # open unitlevel.csv
    0x8A2D80: 0x52806E53,  # 882 unitlevel rows
    0x8A2C94: 0x91513E6A,  # x10=context+0x44f000
    0x8A2C9C: 0x9133B156,  # x22=context+0x44fcec
    0x8A2EB0: 0x52800241,  # unitlevel col 18
    0x8A2EB4: 0x97EB0312,  # parse unitlevel col18
    0x8A2EB8: 0xB90022C0,  # store unitlevel col18 [x22,#0x20]
    0x8A2ED0: 0x910142D6,  # unitlevel row stride = 80
    0x8A2ED4: 0x54FFF581,  # loop unitlevel
    0x8A2EE0: 0xB0FFC7C9,  # unitexp.csv ADRP
    0x8A2EE4: 0x9116F929,  # unitexp.csv ADD
    0x8A2F18: 0x94042A68,  # open unitexp.csv
    0x8A2F2C: 0x52806E53,  # 882 unitexp rows
    0x8A305C: 0x52800241,  # unitexp col 18
    0x8A3060: 0x97EB02A7,  # parse unitexp col18
    0x8A3064: 0xB90022A0,  # store unitexp col18 [x21,#0x20]
    0x8A307C: 0x910142B5,  # unitexp row stride = 80
    0x8A3080: 0x54FFF581,  # loop unitexp
}

ORIGINAL_UNIT_DATA_BOOT_ANCHORS = {
    0x9C5988: 0xAA1303E0,  # x0 = game context
    0x9C598C: 0x97FB74A0,  # original loader
    0x9C5994: 0xAA1303E0,  # same game context
    0x9C5998: 0x2A1403E1,  # per-cat index
    0x9C599C: 0x97FB7605,  # follow-on per-cat initializer
    0x9C59A4: 0x710DCA9F,  # 882-count comparison
    0x9C59A8: 0x54FFFF61,  # loop
}
ORIGINAL_UNIT_SOURCE_STRINGS = {
    "unitbuy.csv": 0x1AB9A3,
    "unitlevel.csv": 0x19294E,
    "unitexp.csv": 0x19B5BE,
}


def _original_unit_data_loader(elf: bytes) -> dict[str, Any]:
    """Pin three original asset loads and their DIFFERENT per-cat RAM layouts.

    In unitbuy.csv the native code XOR-decodes 63 integer columns using the
    4-byte per-row key. For this pinned exact build, decoded column 18 lands at
    context+0x4b0a8+asset_index*0x100; the effective level-cap getter,
    clicked purchase and local save writer are still UNKNOWN.

    Meanwhile the 0x8a2eb4 plain parse/store belongs to **unitlevel.csv**,
    followed by a distinct **unitexp.csv** table. Those must not be mislabeled
    as the official base-level cap from unitbuy.csv.
    """
    if len(elf) < 0x9C59AC:
        raise LevelUpNativeTraceError("original unit-data loader bounds drifted")
    for name, where in ORIGINAL_UNIT_SOURCE_STRINGS.items():
        literal = name.encode("ascii") + b"\x00"
        if elf[where:where + len(literal)] != literal:
            raise LevelUpNativeTraceError(f"{name} original file string drifted")
    for at, expected in ORIGINAL_UNIT_DATA_ANCHORS.items():
        if _u32(elf, at) != expected:
            raise LevelUpNativeTraceError(
                f"original unit-data opcode drifted at {_hex(at)}"
            )
    for at, expected in ORIGINAL_UNIT_DATA_BOOT_ANCHORS.items():
        if _u32(elf, at) != expected:
            raise LevelUpNativeTraceError(
                f"original unit-data startup callsite drifted at {_hex(at)}"
            )
    for address in (0x8A2C88, 0x8A2D6C, 0x8A2F18):
        if _decode_relative_bl(elf, address) != 0x9AD8B8:
            raise LevelUpNativeTraceError("original file opener call target drifted")
    for address in (0x8A2CDC, 0x8A2EB4, 0x8A3060):
        if _decode_relative_bl(elf, address) != 0x363AFC:
            raise LevelUpNativeTraceError("original CSV parser target drifted")
    if (_decode_relative_bl(elf, 0x9C598C) != 0x8A2C0C
            or _decode_relative_bl(elf, 0x9C599C) != 0x8A31B0):
        raise LevelUpNativeTraceError("original unit initialization call targets drifted")
    for at, target in (
        (0x8A2D1C, 0x8A2CD4),
        (0x8A2D2C, 0x8A2CC0),
        (0x8A2ED4, 0x8A2D84),
        (0x8A3080, 0x8A2F30),
        (0x9C59A8, 0x9C5994),
    ):
        instruction = _u32(elf, at)
        displacement = _sign_extend((instruction >> 5) & 0x7FFFF, 19) * 4
        if at + displacement != target:
            raise LevelUpNativeTraceError(
                f"original unit-data loop target drifted at {_hex(at)}"
            )
    return {
        "original_startup_caller": "0x9c598c -> 0x8a2c0c",
        "loader_entry": "0x8a2c0c",
        "source_file_order": ["unitbuy.csv", "unitlevel.csv", "unitexp.csv"],
        "unitbuy": {
            "open_call": "0x8a2c88",
            "source_field_count_per_cat": 63,
            "row_count": 882,
            "row_stride_bytes": 256,
            "decoded_column18_ram_offset":
                "context+0x4b0a8+asset_index*0x100",
            "field_encoding": "bytewise XOR with each row's last four bytes",
            "actual_effective_cap_getter_confirmed": False,
        },
        "unitlevel": {
            "open_call": "0x8a2d6c",
            "column18_parser_call": "0x8a2eb4",
            "column18_store_callsite": "0x8a2eb8",
            "column18_ram_offset": "context+0x44fd0c+asset_index*0x50",
            "row_count": 882,
            "row_stride_bytes": 80,
        },
        "unitexp": {
            "open_call": "0x8a2f18",
            "column18_parser_call": "0x8a3060",
            "column18_store_callsite": "0x8a3064",
            "column18_ram_offset": "context+0x4610ac+asset_index*0x50",
            "row_count": 882,
            "row_stride_bytes": 80,
        },
        "follow_on_per_unit_initializer": "0x9c599c -> 0x8a31b0",
        "levelup_ui_getter_identified": False,
        "upgrade_purchase_or_xp_debit_identified": False,
        "offline_original_save_attached": False,
        "safe_original_game_patch_attached": False,
    }



# Native CAP GETTER with exact source column readers, save increment and min()
# verified from owner-owned exact JP15.7.1 AArch64 source.
ORIGINAL_EFFECTIVE_CAP_GETTER_ANCHORS = {
    0x53B2BC: 0xA9BB7BFD,  # getter entry
    0x53B2D4: 0x2A0003F3,  # asset index in w19
    0x53B2D8: 0x94078313,  # original game context getter
    0x53B2DC: 0x52960C15,  # base constant lower 16 bits = 0xb060
    0x53B2E0: 0x93787E74,  # index * 256
    0x53B2E4: 0x72A00095,  # context + 0x4b060
    0x53B2E8: 0x8B150008,
    0x53B2EC: 0x8B140108,
    0x53B2F0: 0x39412109,  # unitbuy decoded col18 byte at +0x48
    0x53B2F4: 0x3943F10A,  # XOR key at +0xfc
    0x53B2F8: 0x3941250B,  # col18 second byte
    0x53B300: 0x3941290D,  # col18 third byte
    0x53B308: 0x39412D0F,  # col18 fourth byte
    0x53B30C: 0x3943FD08,  # XOR key byte4
    0x53B310: 0x4A090156,  # XOR decoded low byte
    0x53B314: 0x4A0B0197,
    0x53B318: 0x4A0D01D8,
    0x53B31C: 0x4A0F0119,
    0x53B320: 0x94078301,  # context getter
    0x53B324: 0x8B33CC08,  # per-cat saved upgrade record index * 8
    0x53B328: 0x914EB508,  # + 0x3ad000
    0x53B32C: 0x91203100,  # + 0x80c
    0x53B330: 0x9412433D,  # original encoded high16 save increment
    0x53B334: 0x2A1722C8,  # assemble decoded unitbuy col18
    0x53B338: 0x2A184108,
    0x53B33C: 0x0B000108,  # base level + decoded saved increment
    0x53B340: 0x0B196113,
    0x53B344: 0x940782F8,  # context getter before native hard cap
    0x53B350: 0x8B150108,  # same unitbuy per-cat row
    0x53B354: 0x8B140108,
    0x53B358: 0x39432909,  # unitbuy col50 third byte (+0xca)
    0x53B380: 0x3943210A,  # unitbuy col50 first byte (+0xc8)
    0x53B394: 0x2A080121,  # col50 -> w1
    0x53B3AC: 0x17F83A3A,  # tail B original min(w0,w1)
    0x349C94: 0x6B01001F,  # cmp w0, w1
    0x349C98: 0x1A81B000,  # csel w0,w0,w1,lt
    0x349C9C: 0xD65F03C0,  # ret
    0x821904: 0x97F4666E,  # original UI-side cap getter caller
    0x82190C: 0x940AD79D,  # std::to_string(int) after cap getter
}
ORIGINAL_CAP_GETTER_LEVEL_LABEL = (0x193486, b"level\x00")


def _original_effective_level_cap_getter(elf: bytes) -> dict[str, Any]:
    """Original *cap computation* FOUND, purchase and local SAVE still unknown.

    The getter at 0x53b2bc returns min(unitbuy col18 + saved increment,
    unitbuy col50) through the exact original min-int function at 0x349c94.
    The only exact direct BL caller found so far is 0x821904; it then calls
    std::to_string(int) and has original 'level' string nearby. This is an
    exact source-level UI text lead, NOT proof the purchase button is hooked.
    """
    if len(elf) < 0x821918:
        raise LevelUpNativeTraceError("original cap getter/caller bounds drifted")
    where, label = ORIGINAL_CAP_GETTER_LEVEL_LABEL
    if elf[where:where + len(label)] != label:
        raise LevelUpNativeTraceError("original level UI label string drifted")
    for pc, opcode in ORIGINAL_EFFECTIVE_CAP_GETTER_ANCHORS.items():
        if _u32(elf, pc) != opcode:
            raise LevelUpNativeTraceError(
                f"original effective cap getter opcode drifted at {_hex(pc)}"
            )
    direct_calls = {
        0x53B2D8: 0x71BF24, 0x53B320: 0x71BF24,
        0x53B330: 0x9CC024, 0x53B344: 0x71BF24,
        0x821904: 0x53B2BC, 0x82190C: 0xAD7780,
    }
    for pc, target in direct_calls.items():
        if _decode_relative_bl(elf, pc) != target:
            raise LevelUpNativeTraceError(
                f"original cap getter/caller BL target drifted at {_hex(pc)}"
            )
    b_opcode = _u32(elf, 0x53B3AC)
    if b_opcode & 0xFC000000 != 0x14000000:
        raise LevelUpNativeTraceError("cap getter min tail is not a direct B")
    delta = _sign_extend(b_opcode & 0x03FFFFFF, 26) * 4
    if 0x53B3AC + delta != 0x349C94:
        raise LevelUpNativeTraceError("cap getter min-int target drifted")
    return {
        "status": "VERIFIED_ORIGINAL_NATIVE_PER_UNIT_CAP_COMPUTATION",
        "getter_entry": "0x53b2bc",
        "asset_index_input": "w0",
        "source_base_cap": "unitbuy.csv zero-based col18 (XOR decoded)",
        "base_cap_native_offset": "game_context+0x4b0a8+asset_index*0x100",
        "saved_increment_record": "game_context+0x3ad80c+asset_index*8",
        "saved_increment_read": "0x53b330 -> 0x9cc024 (decoded upper 16 bits)",
        "source_hard_cap": "unitbuy.csv zero-based col50 (XOR decoded)",
        "hard_cap_native_offset": "game_context+0x4b128+asset_index*0x100",
        "min_function": "0x53b3ac -> 0x349c94",
        "formula": "min(unitbuy_col18 + decoded_saved_base_increment, unitbuy_col50)",
        "verified_original_caller": "0x821904 -> 0x53b2bc",
        "caller_continuation": "0x82190c -> std::to_string(int), original 'level' text nearby",
        "upgrade_button_purchase_caller_identified": False,
        "xp_or_catseye_debit_identified": False,
        "original_game_zero_egress_local_save_attached": False,
    }



# Real original JP15.7.1 level purchase vertical slice. Both XP spending and
# native CURRENT level increment are in the 0x8581fc -> 0x8583b8 path.
# These are not a hook or proof of local persistence. In particular, the
# CURRENT level record (context+0x47ba4+cat*8) is distinct from the UNLOCK
# cap increment (context+0x3ad80c+cat*8) consumed at 0x53b2bc/0x53be0c.
ORIGINAL_UPGRADE_PURCHASE_ANCHORS = {
    0x53BE0C: 0xA9BA7BFD,  # cap-eligibility predicate entry
    0x53BE34: 0x91411C08,  # context + 0x47000
    0x53BE38: 0x93407E74,  # cat index
    0x53BE3C: 0x912E9108,  # +0xba4: CURRENT level stored (8 byte/cat)
    0x53BE40: 0x8B160100,  # current-level pointer
    0x53BE44: 0x94124078,  # read current base-level upper16
    0x53BE48: 0x11000415,  # next level
    0x53BE98: 0x914EB408,  # +0x3ad000 (MAX upgrade increment)
    0x53BE9C: 0x91203108,  # +0x80c (max upgrade increment record)
    0x53BEA0: 0x8B160100,  # saved increment pointer
    0x53BEA4: 0x94124060,  # read cap increment upper16
    0x53BEB0: 0x0B000108,  # base cap + saved increment
    0x53BF08: 0x97F83763,  # min(allowed, native hard cap)
    0x53BF0C: 0x6B0002BF,  # compare next level with effective cap
    0x53BF10: 0x540004EA,  # B.GE -> separate cap cases
    0x53C1C4: 0x52800020,  # eligibility predicate true
    0x53C1CC: 0x2A1F03E0,  # eligibility predicate false
    0x8581F8: 0x94004AEA,  # resolve selected cat
    0x8581FC: 0x97F38F04,  # predicate check
    0x858200: 0x36007260,  # TBZ fail => other UI path
    0x858208: 0x91411E6A,  # x10=context+0x47000
    0x858210: 0x912E9158,  # x24=context+0x47ba4
    0x858224: 0x8B20CF00,  # current-level record x0
    0x85822C: 0x9405CF7E,  # read upper16 current base level
    0x858364: 0x940014BD,  # XP price adjustment/calculation
    0x858368: 0x5298771A,  # w26 = 0xc3b8
    0x858370: 0x8B1A0260,  # XP wallet at context+0xc3b8
    0x858374: 0x940600E9,  # read encoded XP
    0x858378: 0x6B14001F,  # compare available XP and cost
    0x85837C: 0x54008A2B,  # B.LT -> cannot afford
    0x858384: 0x940600E5,  # read XP again for purchase
    0x858388: 0x4B140001,  # XP balance minus XP cost
    0x858390: 0x940600D5,  # write reduced encoded XP balance
    0x8583AC: 0xF94053F8,  # current-level array base from stack
    0x8583B0: 0x52800021,  # increment by 1
    0x8583B4: 0x8B20CF00,  # record at base+cat_index*8
    0x8583B8: 0x9405CF25,  # increment encoded CURRENT upper16
    0x8583D8: 0x97F130C5,  # post-purchase effect, not save proof
    0x8583E0: 0x97F1319C,  # post-purchase effect, not save proof
    0x85DB74: 0x914EB548,  # different max-cap-increment code path
    0x85DB78: 0x52800021,  # increment cap high16 by 1
    0x85DB7C: 0x91203100,  # x0 at context+0x3ad80c+cat*8
    0x85DB80: 0x9405B933,  # adds cap increment, NOT CURRENT level
}


def _original_upgrade_purchase_flow(elf: bytes) -> dict[str, Any]:
    """Prove original level-up predicate -> XP debit -> current level +1.

    This does NOT prove how the offline first-run player state is initialized,
    when/where native game state is durably saved, or whether the owned game
    can actually boot zero-egress. No account restrictions or saves are altered.
    """
    if len(elf) < 0x85DB84:
        raise LevelUpNativeTraceError("original level upgrade purchase code out of bounds")
    for pc, opcode in ORIGINAL_UPGRADE_PURCHASE_ANCHORS.items():
        if _u32(elf, pc) != opcode:
            raise LevelUpNativeTraceError(
                f"original level upgrade purchase opcode drifted at {_hex(pc)}"
            )
    for pc, target in {
        0x53BE44: 0x9CC024,  # current-level upper16
        0x53BEA4: 0x9CC024,  # max-upgrade increment upper16
        0x53BF08: 0x349C94,  # cap minimum
        0x8581F8: 0x86ADA0,  # selected cat resolver
        0x8581FC: 0x53BE0C,  # per-cat cap eligibility
        0x85822C: 0x9CC024,  # current-level read
        0x858364: 0x85D658,  # XP price multiplier
        0x858374: 0x9D8718,  # encoded XP read
        0x858384: 0x9D8718,  # encoded XP re-read
        0x858390: 0x9D86E4,  # XP debit write
        0x8583B8: 0x9CC04C,  # CURRENT level upper16 increment
        0x85DB80: 0x9CC04C,  # MAX upgrade cap increment elsewhere
    }.items():
        if _decode_relative_bl(elf, pc) != target:
            raise LevelUpNativeTraceError(
                f"original level upgrade purchase BL drifted at {_hex(pc)}"
            )
    # The TBZ and B.LT must still route *around* the XP and level writes.
    tbz_word = _u32(elf, 0x858200)
    if tbz_word & 0x7F000000 != 0x36000000 or (tbz_word >> 19) & 31 != 0:
        raise LevelUpNativeTraceError("original level cap predicate branch changed")
    tbz_imm14 = _sign_extend((tbz_word >> 5) & 0x3FFF, 14) * 4
    if 0x858200 + tbz_imm14 != 0x85904C:
        raise LevelUpNativeTraceError("original level cap-fail branch target changed")
    xp_branch = _u32(elf, 0x85837C)
    if xp_branch & 0xFF00001F != 0x5400000B:
        raise LevelUpNativeTraceError("original XP affordability branch changed")
    xp_displacement = _sign_extend((xp_branch >> 5) & 0x7FFFF, 19) * 4
    if 0x85837C + xp_displacement != 0x8594C0:
        raise LevelUpNativeTraceError("original XP insufficient branch target changed")
    return {
        "status": "VERIFIED_ORIGINAL_NATIVE_LEVEL_PURCHASE_PATH",
        "selected_unit_resolver": "0x8581f8 -> 0x86ada0",
        "cap_eligibility_predicate": "0x8581fc -> 0x53be0c",
        "eligibility_cap_math": "next_current_base_level compared with min(unitbuy_col18+max_upgrade_saved_increment, unitbuy_col50), plus original additional conditions",
        "cannot_upgrade_branch": "0x858200 TBZ -> 0x85904c",
        "max_cap_increment_record": "context+0x3ad80c+asset_index*8",
        "max_cap_increment_separate_write_lead": "0x85db80 -> 0x9cc04c; surrounding source/reward semantics NOT VERIFIED",
        "current_level_record": "context+0x47ba4+asset_index*8",
        "xp_wallet_record": "context+0xc3b8",
        "xp_cost_adjuster": "0x858364 -> 0x85d658",
        "xp_affordability_branch": "0x85837c B.LT -> 0x8594c0",
        "xp_debit": "0x858390 -> 0x9d86e4; new_xp=old_xp-cost",
        "current_level_increment": "0x8583b8 -> 0x9cc04c; upper16 current base+1",
        "post_purchase_effects": ["0x8583d8 -> 0x4a46ec", "0x8583e0 -> 0x4a4a50"],
        "save_writer_proven": False,
        "cats_eye_consume_proven": False,
        "offline_owned_game_boot_proven": False,
        "native_purchase_patch_attached": False,
        "original_device_upgrade_passed": False,
    }



# The actual ORIGINAL native SAVE_DATA serialization entry is reachable through
# the filename wrapper. It serializes XP and BOTH distinct per-cat tables.
# Bytes written to durable disk, reload, and separate local authority are still
# NOT PROVEN. No original code, app, or player SAVE is modified.
ORIGINAL_NATIVE_SAVE_SERIALIZATION_ANCHORS = {
    0x8B9FC8: 0xD10103FF,  # SAVE_DATA wrapper entry
    0x8B9FDC: 0x90FFC6C9,  # literal SAVE_DATA ADRP
    0x8B9FE0: 0x91255529,  # literal SAVE_DATA ADD
    0x8BA008: 0x97FFE9AA,  # wrapper calls serializer
    0x8B48C0: 0x52987708,  # XP balance address +0xc3b8
    0x8B48C4: 0x8B080260,
    0x8B48C8: 0x94048F94,  # decoded XP wallet
    0x8B48D4: 0x97EAA1C5,  # append XP to serialization stream
    0x8B4E20: 0x52806E41,  # 882 current level records
    0x8B4E24: 0x97EAA071,  # append count
    0x8B4E28: 0x91411F08,  # context+0x47000
    0x8B4E30: 0x912E9114,  # context+0x47ba4
    0x8B4E34: 0xAA1403E0,
    0x8B4E38: 0x94048E38,  # decode per-cat current level
    0x8B4E44: 0x97EAA069,  # append current level
    0x8B4E48: 0xF1000673,
    0x8B4E4C: 0x91002294,  # 8-byte stride
    0x8B4E50: 0x54FFFF21,  # next of 882
    0x8B62F4: 0x52806E41,  # 882 max upgrade records
    0x8B62F8: 0x97EA9B3C,  # append count
    0x8B62FC: 0x914EB708,  # context+0x3ad000
    0x8B6304: 0x91203114,  # context+0x3ad80c
    0x8B6308: 0xAA1403E0,
    0x8B630C: 0x94048903,  # decode saved cap increment
    0x8B6318: 0x97EA9B34,  # append cap increment
    0x8B631C: 0xF1000673,
    0x8B6320: 0x91002294,  # 8-byte stride
    0x8B6324: 0x54FFFF21,  # next of 882
    0x8593E0: 0x940182FA,  # UI-side trigger of SAVE_DATA wrapper
}


def _original_save_data_serialization(elf: bytes) -> dict[str, Any]:
    """Verifies original SAVE_DATA serialization includes purchase core fields.

    The exact 0x8b9fc8 SAVE_DATA wrapper calls 0x8b46b0, which decodes and
    appends XP, current level and max-upgrade increment separately. The IO
    completion/reload path and whether the UI calls it after a particular
    level-purchase branch are not yet proven. Never imply an offline save works.
    """
    if len(elf) < 0x8BA044 or elf[0x191955:0x19195F] != b"SAVE_DATA\x00":
        raise LevelUpNativeTraceError("original SAVE_DATA serialization bounds/name drifted")
    for pc, expected in ORIGINAL_NATIVE_SAVE_SERIALIZATION_ANCHORS.items():
        if _u32(elf, pc) != expected:
            raise LevelUpNativeTraceError(
                f"original SAVE_DATA serializer opcode drifted at {_hex(pc)}"
            )
    calls = {
        0x8BA008: 0x8B46B0,
        0x8B48C8: 0x9D8718,
        0x8B48D4: 0x35CFE8,
        0x8B4E24: 0x35CFE8,
        0x8B4E38: 0x9D8718,
        0x8B4E44: 0x35CFE8,
        0x8B62F8: 0x35CFE8,
        0x8B630C: 0x9D8718,
        0x8B6318: 0x35CFE8,
        0x8593E0: 0x8B9FC8,
    }
    for pc, expected in calls.items():
        if _decode_relative_bl(elf, pc) != expected:
            raise LevelUpNativeTraceError(
                f"original SAVE_DATA serialization target drifted at {_hex(pc)}"
            )
    for pc, target in (
        (0x8B4E50, 0x8B4E34),
        (0x8B6324, 0x8B6308),
    ):
        word = _u32(elf, pc)
        if word & 0xFF00001F != 0x54000001:
            raise LevelUpNativeTraceError(
                f"original SAVE_DATA row-loop branch changed at {_hex(pc)}"
            )
        displacement = _sign_extend((word >> 5) & 0x7FFFF, 19) * 4
        if pc + displacement != target:
            raise LevelUpNativeTraceError(
                f"original SAVE_DATA row-loop target drifted at {_hex(pc)}"
            )
    return {
        "status": "VERIFIED_ORIGINAL_SAVE_DATA_SERIALIZER_INCLUDE_UPGRADE_FIELDS",
        "original_filename": "SAVE_DATA",
        "native_save_wrapper": "0x8b9fc8 -> 0x8b46b0",
        "xp_wallet_decoded": "0x8b48c8: context+0xc3b8",
        "xp_wallet_serialized": "0x8b48d4 -> 0x35cfe8",
        "current_level_table": "0x8b4e30: context+0x47ba4; 882 records, 8-byte stride",
        "current_level_serializer": "0x8b4e38 decoded; 0x8b4e44 append",
        "max_upgrade_table": "0x8b6304: context+0x3ad80c; 882 records, 8-byte stride",
        "max_upgrade_serializer": "0x8b630c decoded; 0x8b6318 append",
        "ui_side_save_wrapper_caller": "0x8593e0 -> 0x8b9fc8",
        "ui_side_caller_directly_post_purchase_verified": False,
        "disk_save_flush_completed_verified": False,
        "save_reboot_reload_verified": False,
        "independent_offline_local_authority_integrated": False,
        "original_game_lv60_device_verified": False,
    }



# Original native serializer's close/commit status and paired SAVE_DATA reader.
# These source locations prove the XP/current-level/cap-increment deserializer
# uses exactly the same game-context fields as the purchase-side writer.
# The source still does NOT prove a durable fsync, new standalone offline
# profile compatibility, or safe original-device startup.
ORIGINAL_NATIVE_SAVE_RESTORE_ANCHORS = {
    0x8B43A4: 0xD10443FF,  # reader wrapper entry
    0x8B43D0: 0xB0FFC6E9,  # original SAVE_DATA string ADRP
    0x8B43D4: 0x91255529,  # original SAVE_DATA string ADD
    0x8B4404: 0x97EAA487,  # open input source
    0x8B441C: 0x36000774,  # failed-open branch
    0x8B4444: 0x97EAA8D7,  # reader ready/validation
    0x8B4448: 0x360006E0,  # failed-validation branch
    0x8B44AC: 0x97FFC87C,  # deserialize game context
    0x8A66E0: 0x97EAD7B4,  # deserialize source/version value
    0x8A69E8: 0x52987713,  # native XP record at context+0xc3b8
    0x8A69EC: 0x97EAD6F1,  # read XP from source
    0x8A69F4: 0x8B1302C0,  # XP destination context+0xc3b8
    0x8A69F8: 0x9404C73B,  # encode XP in native game context
    0x8A91E4: 0x97EACCF3,  # current levels recorded count
    0x8A91F4: 0x91411EC9,  # context + 0x47000
    0x8A9200: 0x912E9133,  # +0xba4: current-level array
    0x8A920C: 0x97EACCE9,  # read next current level
    0x8A921C: 0x9404BD32,  # encode current level
    0x8A9230: 0x54FFFEAB,  # current-level loop, input count
    0x8AD14C: 0x97EABD19,  # cap increments recorded count
    0x8AD15C: 0x914EB6C9,  # context +0x3ad000
    0x8AD168: 0x91203133,  # +0x80c: max-upgrade array
    0x8AD174: 0x97EABD0F,  # read next cap increment
    0x8AD180: 0x9404AD59,  # encode cap increment
    0x8AD194: 0x54FFFECB,  # cap-increment loop, input count
    0x8B46FC: 0x97EAA745,  # open original SAVE_DATA writer
    0x8B4700: 0x360063E0,  # write-open failed branch
    0x8B97DC: 0x940044EC,  # other game fields into source output
    0x8B97E8: 0x97EA9539,  # finalize underlying output stream
    0x8B97EC: 0x2A0003F3,  # save stream finalizer result
    0x8B9BD8: 0x12000260,  # return masked bool status
}


def _original_save_restore_flow(elf: bytes) -> dict[str, Any]:
    """Pin original WRITE stream finalization and READ state restoration.

    This source-derived path includes the level-purchase XP and level fields
    and their corresponding binary-deserialization stores. It does not prove
    independent local boot, storage durability, or runtime UI acceptance.
    """
    if len(elf) < 0x8BA010 or elf[0x191955:0x19195F] != b"SAVE_DATA\x00":
        raise LevelUpNativeTraceError("original save restore source bounds/name drifted")
    for at, word in ORIGINAL_NATIVE_SAVE_RESTORE_ANCHORS.items():
        if _u32(elf, at) != word:
            raise LevelUpNativeTraceError(
                f"original save restore native opcode drifted at {_hex(at)}"
            )
    calls = {
        0x8B4404: 0x35D620,  # reader open
        0x8B4444: 0x35E7A0,  # reader ready
        0x8B44AC: 0x8A669C,  # original deserializer
        0x8A66E0: 0x35C5B0,  # source version value
        0x8A69EC: 0x35C5B0,  # original XP
        0x8A69F8: 0x9D86E4,  # restored XP
        0x8A91E4: 0x35C5B0,  # current level count
        0x8A920C: 0x35C5B0,  # current level
        0x8A921C: 0x9D86E4,  # restored level
        0x8AD14C: 0x35C5B0,  # max increment count
        0x8AD174: 0x35C5B0,  # max increment
        0x8AD180: 0x9D86E4,  # restored max increment
        0x8B46FC: 0x35E410,  # original writer open
        0x8B97DC: 0x8CAB8C,  # extra original data serialization
        0x8B97E8: 0x35ECCC,  # stream finalization
    }
    for at, expected in calls.items():
        if _decode_relative_bl(elf, at) != expected:
            raise LevelUpNativeTraceError(
                f"original save restore BL target drifted at {_hex(at)}"
            )
    for at, target in (
        (0x8B441C, 0x8B4508),
        (0x8B4448, 0x8B4524),
        (0x8B4700, 0x8B537C),
    ):
        branch = _u32(elf, at)
        if branch & 0x7F000000 != 0x36000000:
            raise LevelUpNativeTraceError(
                f"original save open/validation TBZ drifted at {_hex(at)}"
            )
        displacement = _sign_extend((branch >> 5) & 0x3FFF, 14) * 4
        if at + displacement != target:
            raise LevelUpNativeTraceError(
                f"original save open/validation branch target drifted at {_hex(at)}"
            )
    for at, target in (
        (0x8A9230, 0x8A9204),
        (0x8AD194, 0x8AD16C),
    ):
        branch = _u32(elf, at)
        if branch & 0xFF00001F != 0x5400000B:
            raise LevelUpNativeTraceError(
                f"original saved unit-array loop drifted at {_hex(at)}"
            )
        displacement = _sign_extend((branch >> 5) & 0x7FFFF, 19) * 4
        if at + displacement != target:
            raise LevelUpNativeTraceError(
                f"original saved unit-array loop target drifted at {_hex(at)}"
            )
    return {
        "status": "VERIFIED_ORIGINAL_NATIVE_SAVE_READER_WRITER_STREAM_SEAMS",
        "save_filename": "SAVE_DATA",
        "read_entry": "0x8b43a4",
        "reader_open": "0x8b4404 -> 0x35d620",
        "reader_validity": "0x8b4444 -> 0x35e7a0",
        "deserialize_game_context": "0x8b44ac -> 0x8a669c",
        "restore_xp": "0x8a69ec read; 0x8a69f8 encode at context+0xc3b8",
        "restore_current_levels": "0x8a91e4 dynamic stored count, 0x8a920c read, 0x8a921c encode at context+0x47ba4+cat*8",
        "restore_max_cap_increments": "0x8ad14c dynamic stored count, 0x8ad174 read, 0x8ad180 encode at context+0x3ad80c+cat*8",
        "write_entry": "0x8b9fc8 -> 0x8b46b0",
        "writer_open": "0x8b46fc -> 0x35e410",
        "serializer_finished": "0x8b97e8 -> 0x35eccc; return status in w0",
        "storage_backend_identified": False,
        "durable_fsync_or_atomic_commit_proven": False,
        "successful_purchase_triggers_save_proven": False,
        "network_independent_fresh_game_profile_proven": False,
        "original_game_level60_restart_verified": False,
        "safe_original_native_game_patch_attached": False,
    }



# Original max-upgrade (+1) purchase path with item debit transaction.
# Catseye material category identity should still be audited from original
# resource catalog, so no fabricated material names/amounts are assumed.
# Unlike a generic SAVE_DATA filename xref, 0x85db88 is directly AFTER
# the original cap-increment write and explicitly calls the original serializer.
ORIGINAL_CAP_INCREMENT_ITEM_TRANSACTION_ANCHORS = {
    0x85D9F4: 0x71001ADF,  # six source material slots
    0x85D9F8: 0x54000A60,  # exit slot scan
    0x85DA04: 0x97F37827,  # resource quantity required for this unit/slot
    0x85DA0C: 0x7100041F,  # require >=1 before debit entry
    0x85DA10: 0x54FFFF0B,  # skip material if no requirement
    0x85DA14: 0x528000A0,  # item category = 5
    0x85DA18: 0x2A1603E1,  # slot index
    0x85DA1C: 0x97F64805,  # material type -> inventory ID
    0x85DABC: 0x4B1703E9,  # NEG required count => debit
    0x85DAC4: 0xB9002329,  # stage negative item delta
    0x85DB4C: 0xEB1402BF,  # compare pending item delta collection
    0x85DB50: 0x54000681,  # apply item deltas before cap increment
    0x85DB58: 0x914EBE68,  # per-cat upgrade history table
    0x85DB5C: 0x910FD115,
    0x85DB68: 0xB8696AA8,
    0x85DB6C: 0x11000508,
    0x85DB70: 0xB8296AA8,
    0x85DB74: 0x914EB548,  # max-increment base (+0x3ad000)
    0x85DB78: 0x52800021,  # +1 level-cap increment
    0x85DB7C: 0x91203100,  # max-increment record +0x80c
    0x85DB80: 0x9405B933,  # change encoded max cap increment
    0x85DB84: 0xAA1303E0,  # original game context
    0x85DB88: 0x94017110,  # immediate original SAVE_DATA serializer
    0x85DC1C: 0x54FFF9C0,  # after inventory drain, proceed to cap
    0x85DC20: 0x294386A0,  # inventory ID and signed negative delta
    0x85DC24: 0x2A1F03E2,
    0x85DC28: 0x97F6444C,  # apply inventory change
}


def _original_cap_increment_item_transaction(elf: bytes) -> dict[str, Any]:
    """Pin original item consumption before native max-cap +1 then SAVE_DATA.

    Distinct from the normal base-level upgrade flow at 0x8581fc.
    The inline SAVE_DATA call is proven, but POSIX flush, offline native host,
    and Catseye inventory item subtype mapping are still unverified.
    """
    if len(elf) < 0x85DC2C:
        raise LevelUpNativeTraceError("original cap increment transaction bounds drifted")
    for pc, expected in ORIGINAL_CAP_INCREMENT_ITEM_TRANSACTION_ANCHORS.items():
        if _u32(elf, pc) != expected:
            raise LevelUpNativeTraceError(
                f"original cap increment transaction opcode drifted at {_hex(pc)}"
            )
    for pc, expected in {
        0x85DA04: 0x53BAA0,
        0x85DA1C: 0x5EFA30,
        0x85DB80: 0x9CC04C,
        0x85DB88: 0x8B9FC8,
        0x85DC28: 0x5EED58,
    }.items():
        if _decode_relative_bl(elf, pc) != expected:
            raise LevelUpNativeTraceError(
                f"original cap increment transaction BL drifted at {_hex(pc)}"
            )
    for pc, target, cond in (
        (0x85D9F8, 0x85DB44, 0),  # EQ six-slot scan completed
        (0x85DA10, 0x85D9F0, 11),  # LT no material needed
        (0x85DB50, 0x85DC20, 1),  # NE item debit queue remains
        (0x85DC1C, 0x85DB54, 0),  # EQ inventory debit complete
    ):
        branch = _u32(elf, pc)
        if (branch & 0xFF00001F) != 0x54000000 | cond:
            raise LevelUpNativeTraceError(
                f"original cap increment branch type drifted at {_hex(pc)}"
            )
        disp = _sign_extend((branch >> 5) & 0x7FFFF, 19) * 4
        if pc + disp != target:
            raise LevelUpNativeTraceError(
                f"original cap increment branch target drifted at {_hex(pc)}"
            )
    return {
        "status": "VERIFIED_ORIGINAL_NATIVE_CAP_ITEM_DEBIT_INCREMENT_SAVE_CALL",
        "process_material_slots": "0x85d9f4: six candidate material slots",
        "required_material_count": "0x85da04 -> 0x53baa0",
        "material_inventory_id": "0x85da14 category5, 0x85da1c -> 0x5efa30",
        "negative_material_delta": "0x85dabc neg required, 0x85dac4 stages delta",
        "debit_loop": "0x85db50 -> 0x85dc20; 0x85dc28 -> 0x5eed58; 0x85dc1c -> 0x85db54",
        "max_upgrade_increment": "0x85db78 +1; 0x85db80 -> 0x9cc04c, per cat context+0x3ad80c+cat*8",
        "save_called_after_increment": "0x85db88 -> 0x8b9fc8",
        "original_catseye_material_subtypes_verified": False,
        "material_sufficiency_and_atomicity_proven": False,
        "original_save_file_fsync_and_restart_proven": False,
        "offline_independent_game_integrated": False,
        "android_lv60_ui_purchase_verified": False,
    }



# Original successful XP purchase is NOT an unrelated menu action: source CFG
# has TWO conditional witnesses from current-level +1 at 0x8583b8 to native
# SAVE_DATA wrapper 0x8b9fc8. This is source control-flow only; it does NOT
# establish all paths always save, filesystem fsync, or offline profile support.
ORIGINAL_XP_TO_SAVE_DISPATCH_ANCHORS = {
    0x858390: 0x940600D5,  # XP decrement recorded
    0x8583B8: 0x9405CF25,  # current base level +1
    0x858450: 0x54000480,  # b.eq split
    0x858484: 0x54009BC0,  # b.eq -> 0x8597fc
    0x858534: 0x540099E1,  # b.ne alternate route
    0x85853C: 0x140004F1,  # unconditional -> 0x859900
    0x859850: 0x1400007B,  # original path A -> 0x859a3c
    0x859900: 0xA94AA3E9,  # shared post-upgrade UI
    0x859994: 0x34006CE9,  # cbz -> 0x85a730
    0x8599C8: 0x540003A0,  # b.eq -> 0x859a3c
    0x859A38: 0x14000343,  # b -> 0x85a744
    0x859A3C: 0xAA1303E0,  # mov x0,x19 game context
    0x859A40: 0x94018162,  # BL original SAVE_DATA
    0x85A730: 0x52800149,  # original path B prelude
    0x85A744: 0xAA1303E0,  # mov x0,x19 game context
    0x85A748: 0x94017E20,  # BL original SAVE_DATA
}

def _original_arm64_cfg_successors(elf: bytes, pc: int) -> tuple[int, ...]:
    """Minimal direct AArch64 CFG edge decoder for pinned original .text.

    BL/BLR are modeled as return-to-next, not as proof that called functions
    terminate or always return. Unknown UDF, direct BR/RET and BRK are
    conservative terminal instructions. Never include outside .text as graph.
    """
    word = _u32(elf, pc)
    if word == 0 or word == 0xD4200000:
        return ()
    if word & 0xFFFFFC1F in (0xD65F0000, 0xD61F0000):
        return ()  # RET or indirect BR
    if word & 0xFC000000 == 0x14000000:  # B
        return (pc + _sign_extend(word & 0x03FFFFFF, 26) * 4,)
    if word & 0xFF000010 == 0x54000000:  # B.cond
        return (pc + _sign_extend((word >> 5) & 0x7FFFF, 19) * 4, pc + 4)
    if word & 0x7E000000 == 0x34000000:  # CBZ/CBNZ
        return (pc + _sign_extend((word >> 5) & 0x7FFFF, 19) * 4, pc + 4)
    if word & 0x7E000000 == 0x36000000:  # TBZ/TBNZ
        return (pc + _sign_extend((word >> 5) & 0x3FFF, 14) * 4, pc + 4)
    return (pc + 4,)


def _original_arm64_cfg_witness(
    elf: bytes,
    start: int,
    end: int,
    source: int,
    target: int,
    *,
    max_nodes: int = 20000,
) -> list[int]:
    """Return a bounded DIRECT control-flow witness or [].

    The path is syntactic and conditional; feasible runtime values, dynamic
    callbacks and persistent storage still need original-device verification.
    """
    from collections import deque
    if (not isinstance(elf, bytes) or any(type(n) is not int for n in
            (start, end, source, target, max_nodes))
        or any(n % 4 != 0 for n in (start, end, source, target))
        or not (0 <= start <= source < end <= len(elf))
        or not (start <= target < end)
        or not (0 < max_nodes <= 50000)):
        raise LevelUpNativeTraceError("invalid original native bounded control-flow range")
    parent: dict[int, int | None] = {source: None}
    todo = deque([source])
    examined = 0
    while todo:
        pc = todo.popleft()
        examined += 1
        if examined > max_nodes:
            raise LevelUpNativeTraceError("original native bounded CFG traversal limit exceeded")
        if pc == target:
            path = []
            at: int | None = pc
            while at is not None:
                path.append(at)
                at = parent[at]
            return list(reversed(path))
        for next_pc in _original_arm64_cfg_successors(elf, pc):
            if start <= next_pc < end and next_pc not in parent:
                parent[next_pc] = pc
                todo.append(next_pc)
    return []


def _original_normal_xp_purchase_save_routes(elf: bytes) -> dict[str, Any]:
    """Prove two CONDITIONAL original normal XP purchase -> SAVE_DATA paths.

    Not proof of saving on every purchase branch, successful file flush,
    game save acceptance, initial local profile or network isolation.
    """
    if len(elf) < 0x8B9FCC:
        raise LevelUpNativeTraceError("original purchase save-dispatch ELF bounds drifted")
    for at, word in ORIGINAL_XP_TO_SAVE_DISPATCH_ANCHORS.items():
        if _u32(elf, at) != word:
            raise LevelUpNativeTraceError(
                f"original XP purchase-to-save branch opcode drifted at {_hex(at)}"
            )
    for at, target in (
        (0x858390, 0x9D86E4),
        (0x8583B8, 0x9CC04C),
        (0x859A40, 0x8B9FC8),
        (0x85A748, 0x8B9FC8),
    ):
        if _decode_relative_bl(elf, at) != target:
            raise LevelUpNativeTraceError(
                f"original XP purchase-to-save direct BL target drifted at {_hex(at)}"
            )
    routes = {}
    source_region_start, source_region_end = 0x850000, 0x85B000
    prelude = _original_arm64_cfg_witness(
        elf, source_region_start, source_region_end, 0x858390, 0x8583B8
    )
    if not prelude:
        raise LevelUpNativeTraceError("original XP debit no longer reaches level increment")
    expected_branch_witnesses = {
        0x859A40: (
            (0x858450, 0x858454), (0x858484, 0x8597FC),
            (0x859850, 0x859A3C),
        ),
        0x85A748: (
            (0x858450, 0x8584E0), (0x858534, 0x858538),
            (0x85853C, 0x859900), (0x859994, 0x85A730),
        ),
    }
    for save_callsite, expected_decisions in expected_branch_witnesses.items():
        witness = _original_arm64_cfg_witness(
            elf, source_region_start, source_region_end, 0x8583B8, save_callsite
        )
        decisions = tuple((a, b) for a, b in zip(witness, witness[1:])
                          if len(_original_arm64_cfg_successors(elf, a)) > 1
                          or b != a + 4)
        if not witness or any(x not in decisions for x in expected_decisions):
            raise LevelUpNativeTraceError(
                f"original XP purchase-to-save conditional route drifted at {_hex(save_callsite)}"
            )
        routes[_hex(save_callsite)] = {
            "original_save_target": "0x8b9fc8",
            "witness_instruction_count": len(witness),
            "conditional_or_jump_edges": [
                {"from": _hex(a), "to": _hex(b)} for a, b in decisions
            ],
        }
    return {
        "status": "ORIGINAL_NATIVE_XP_PURCHASE_TO_SAVE_CONDITIONAL_CFG_PROVEN",
        "source_xp_debit": "0x858390 -> 0x9d86e4",
        "native_current_level_increment": "0x8583b8 -> 0x9cc04c",
        "xp_debit_reaches_level_increment": True,
        "conditional_save_routes": routes,
        "all_successful_upgrade_paths_save_proven": False,
        "runtime_branch_values_or_reachability_proven": False,
        "original_disk_durable_flush_proven": False,
        "fresh_independent_zero_network_save_connected": False,
        "original_game_lv60_screen_and_reboot_verified": False,
        "binary_mutated_or_user_save_modified": False,
    }



def _original_arm64_cfg_all_direct_paths_hit_save(
    elf: bytes,
    start: int,
    end: int,
    entry: int,
    save_calls: frozenset[int],
    *,
    max_nodes: int = 20000,
) -> dict[str, Any]:
    """Fail closed if ANY modeled direct CFG exit bypasses the save calls.

    This checks only finite DIRECT instruction-flow. Every BL/BLR is assumed
    to return; exceptions, longjmp, syscall termination, IO failures and
    game-side dynamically dispatched callbacks are unproven.
    """
    from collections import deque
    if (not isinstance(elf, bytes)
        or not isinstance(save_calls, frozenset) or not save_calls
        or any(type(n) is not int for n in (start, end, entry, max_nodes))
        or any(type(n) is not int for n in save_calls)
        or any(n % 4 for n in (start, end, entry, *save_calls))
        or not (0 <= start <= entry < end <= len(elf))
        or any(not (start <= n < end) for n in save_calls)
        or not 0 < max_nodes <= 50000):
        raise LevelUpNativeTraceError("invalid original save-gate CFG bounds")
    queue = deque([entry])
    seen: set[int] = set()
    seen_savers: set[int] = set()
    ordinary_edges: dict[int, tuple[int, ...]] = {}
    while queue:
        pc = queue.popleft()
        if pc in seen:
            continue
        seen.add(pc)
        if len(seen) > max_nodes:
            raise LevelUpNativeTraceError("original save-gate CFG exceeds node limit")
        if pc in save_calls:
            seen_savers.add(pc)
            continue
        successors = _original_arm64_cfg_successors(elf, pc)
        if not successors:
            raise LevelUpNativeTraceError(
                f"original upgrade path terminates before SAVE_DATA at {_hex(pc)}"
            )
        if any(next_pc < start or next_pc >= end for next_pc in successors):
            raise LevelUpNativeTraceError(
                f"original upgrade path escapes save-gate range at {_hex(pc)}"
            )
        ordinary_edges[pc] = tuple(next_pc for next_pc in successors
                                   if next_pc not in save_calls)
        queue.extend(next_pc for next_pc in successors if next_pc not in seen)
    if not seen_savers:
        raise LevelUpNativeTraceError("original upgrade path found no SAVE_DATA calls")
    # The preceding checks exclude direct exits. Also reject a reachable loop
    # that could run forever without hitting a saver (Kahn topological order).
    indegree = {pc: 0 for pc in ordinary_edges}
    for successors in ordinary_edges.values():
        for next_pc in successors:
            if next_pc in indegree:
                indegree[next_pc] += 1
    ready = deque(pc for pc, count in indegree.items() if count == 0)
    reduced = 0
    while ready:
        pc = ready.popleft()
        reduced += 1
        for next_pc in ordinary_edges[pc]:
            if next_pc in indegree:
                indegree[next_pc] -= 1
                if indegree[next_pc] == 0:
                    ready.append(next_pc)
    if reduced != len(ordinary_edges):
        raise LevelUpNativeTraceError(
            "original upgrade has reachable cycle before SAVE_DATA call"
        )
    return {
        "conditional_static_direct_paths_hit_a_saver": True,
        "code_range": [_hex(start), _hex(end)],
        "source_after_level_increment": _hex(entry),
        "save_calls": [_hex(pc) for pc in sorted(seen_savers)],
        "reachable_nodes": len(seen),
        "non_save_nodes": len(ordinary_edges),
        "early_direct_exits_found": 0,
        "nonterminating_direct_cycles_found": 0,
        "assumption": "BL/BLR returns normally; dynamic callbacks/exceptions and storage IO are out of scope",
        "real_runtime_guaranteed_save": False,
        "durable_disk_fsync_verified": False,
        "local_zero_egress_runtime_attached": False,
    }


def _original_xp_purchase_save_gate(elf: bytes) -> dict[str, Any]:
    """Check exact pinned native's post-Lv+1 direct CFG, not Android result."""
    result = _original_arm64_cfg_all_direct_paths_hit_save(
        elf, 0x850000, 0x85B000, 0x8583B8,
        frozenset((0x859A40, 0x85A748))
    )
    if (result["save_calls"] != ["0x859a40", "0x85a748"]
        or result["reachable_nodes"] != 244
        or result["non_save_nodes"] != 242):
        raise LevelUpNativeTraceError(
            "original JP native post-level CFG structural counts drifted"
        )
    return result


def trace_exact_native(elf: bytes, *, expected_sha: str = NATIVE_SHA256) -> dict:
    digest = sha256(elf).hexdigest()
    if digest != expected_sha or expected_sha != NATIVE_SHA256:
        raise LevelUpNativeTraceError("only user's exact JP15.7.1 native hash accepted")
    if elf[:4] != b"\x7fELF" or len(elf) < TEXT_END:
        raise LevelUpNativeTraceError("not expected pinned AArch64 ELF")
    refs: dict[str, Any] = {}
    for key, value in CUES.items():
        needle = value.encode("ascii")
        locations = []
        cursor = 0
        while True:
            position = elf.find(needle, cursor)
            if position < 0:
                break
            # A complete NUL-delimited original identifier, not a substring.
            if (position == 0 or elf[position - 1] == 0) and (
                position + len(needle) == len(elf)
                or elf[position + len(needle)] == 0
            ):
                locations.append(position)
            cursor = position + 1
        sites = []
        for address in locations:
            for match in direct_adrp_add_refs(
                elf, address, text_start=TEXT_START, text_end=TEXT_END
            ):
                sites.append({**match, "rodata_address": _hex(address)})
        refs[key] = {"identifier": value,
                     "string_addresses": [_hex(x) for x in locations],
                     "direct_adrp_add_sites": sites}
    for name, expected_sites in EXPECTED_ANCHORS.items():
        actual = {int(row["adrp_address"], 16)
                  for row in refs[name]["direct_adrp_add_sites"]}
        if actual != expected_sites:
            raise LevelUpNativeTraceError(
                f"{name}: pinned original code xrefs drifted: {actual}"
            )
    return {
        "schema_version": 1,
        "build": "jp-15.7.1-arm64",
        "native_sha256": digest,
        "evidence_type": "PINNED_AARCH64_CAP_PURCHASE_SAVE_RESTORE_AND_CONDITIONAL_DIRECT_CFG",
        "references": refs,
        "levelmax_popup_branch_candidate": _levelmax_popup_branch(elf),
        "levelmax_popup_value_call_chain": _popup_value_call_chain(elf),
        "original_unit_data_loader": _original_unit_data_loader(elf),
        "original_effective_level_cap_getter": _original_effective_level_cap_getter(elf),
        "original_upgrade_purchase_flow": _original_upgrade_purchase_flow(elf),
        "original_save_data_serialization": _original_save_data_serialization(elf),
        "original_save_restore_flow": _original_save_restore_flow(elf),
        "original_cap_increment_item_transaction": _original_cap_increment_item_transaction(elf),
        "original_normal_xp_purchase_save_routes": _original_normal_xp_purchase_save_routes(elf),
        "original_xp_purchase_save_gate": _original_xp_purchase_save_gate(elf),
        "native_original_game_upgrader_getter_identified": True,
        "native_original_game_upgrade_purchase_hook_verified": False,
        "original_native_conditional_xp_purchase_to_save_calls_proven": True,
        "original_offline_level60_purchase_reboot_proven": False,
        "unit_cap_purchase_hook_attached": False,
        "scope": "READ_ONLY_EXACT_OWNER_SOURCE",
        "notes": [
            "unitbuy.csv column18 is XOR-decoded to the original 256-byte-per-unit native table; separate unitlevel.csv and unitexp.csv plain 80-byte rows must not be confused",
            "CatsEyeLevelUp and levelmax popups are original-game native code location leads",
            "Original SAVE_DATA/SAVE_DATA4/SAVE_DATA8 filename xrefs and native getFilesDir JNI string xref (0x45aa3c) show potential file-root seams, NOT actual offline save redirection or persistence proof",
            "Bounded direct CFG reaches the original SAVE_DATA calls, but physical UI execution, file durability and zero-network local authority remain unproven",
        ],
        "original_assets_written_to_repo": False,
        "account_or_save_data_modified": False,
    }


def trace_from_owner_export(owner_zip: Path) -> dict:
    if sha256(owner_zip.read_bytes()).hexdigest() != SOURCE_EXPORT_SHA256:
        raise LevelUpNativeTraceError("owner export SHA256 differs from pinned JP15.7.1")
    with ZipFile(owner_zip) as z:
        with ZipFile(BytesIO(z.read(SOURCE_APK_NAME))) as split:
            elf = split.read(ELF_APK_NAME)
    report = trace_exact_native(elf)
    report["owner_export_sha256"] = SOURCE_EXPORT_SHA256
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owned-export", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.suffix.lower() != ".json":
        parser.error("--output must end in .json")
    try:
        receipt = trace_from_owner_export(args.owned_export)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8"
        )
    except (OSError, ValueError, KeyError, struct.error) as error:
        parser.error(str(error))
    print(f"exact owned game upgrade/native xref receipt -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
