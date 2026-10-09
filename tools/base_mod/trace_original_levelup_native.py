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
    "unit_level_file": "unitlevel.csv",
    "unit_xp_file": "unitexp.csv",
    "catseye_screen_resource": "BcResCatsEyeLevelUp",
    "catseye_levelup_name": "CatsEyeLevelUp",
    "max_level_popup_first": "drop_popup_chara_levelmax1",
    "max_level_popup_second": "drop_popup_chara_levelmax2",
    "potential_skill_max": "potential_skill_MaxLevel",
    "recommended_levelup_table": "Recommended_levelup.csv",
}

# Proven direct ADRP+ADD disassembly sites from *this exact native SHA only*.
EXPECTED_ANCHORS = {
    "unit_data_file": {0x8A2C60},
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
        "evidence_type": "AARCH64_DIRECT_STRING_XREF_ONLY",
        "references": refs,
        "levelmax_popup_branch_candidate": _levelmax_popup_branch(elf),
        "levelmax_popup_value_call_chain": _popup_value_call_chain(elf),
        "original_unit_data_loader": _original_unit_data_loader(elf),
        "native_original_game_upgrader_getter_identified": False,
        "unit_cap_purchase_hook_attached": False,
        "scope": "READ_ONLY_EXACT_OWNER_SOURCE",
        "notes": [
            "unitbuy.csv column18 is XOR-decoded to the original 256-byte-per-unit native table; separate unitlevel.csv and unitexp.csv plain 80-byte rows must not be confused",
            "CatsEyeLevelUp and levelmax popups are original-game native code location leads",
            "Further control-flow and original-game UI behavior must be verified before patching",
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
