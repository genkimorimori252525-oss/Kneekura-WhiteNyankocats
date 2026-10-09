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
        "native_original_game_upgrader_getter_identified": False,
        "unit_cap_purchase_hook_attached": False,
        "scope": "READ_ONLY_EXACT_OWNER_SOURCE",
        "notes": [
            "unitbuy.csv loader/string reference is not proof of the level cap calculation",
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
