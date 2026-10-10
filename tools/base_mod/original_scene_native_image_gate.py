"""Read-only exact JP15.7.1 ARM64 scene-witness native-image preflight.

Applied to the *repacked* original native library AFTER adding DT_NEEDED via
LIEF and BEFORE anyone signs/installs an isolated no-INTERNET research build.

An ELF may preserve exported symbol names yet alter original function VMAs,
the game-context getter, or the ELF note. Reject that mismatch early instead
of enabling a hook which can address the wrong in-memory native function.

No original executable, SAVE, protected pack, account or device is modified.
"""
from __future__ import annotations

from hashlib import sha256
import struct
from typing import Any

from tools.base_mod.elf_anchor import EM_AARCH64, elf_machine, gnu_build_id

ORIGINAL_JP1571_BUILD_ID = "8cb3815648eb9642da10bfb039d71bff7a3519bd"
ORIGINAL_DRAW_SYMBOL = "Java_jp_co_ponos_battlecats_MyActivity_appUpdateDraw"
ORIGINAL_DRAW_VMA = 0x31755C
# Exact user-owned JP15.7.1 `.text` VMA bounds and SHA256 verified
# READ ONLY from ZIP 38c3bbb8...fd61a0ef56 and native 333d2974...a7e2.
# This is the entire native executable instruction section, not merely the
# 17 safety anchors; any unapproved instruction rewrite must abort signing.
ORIGINAL_NATIVE_TEXT_START = 0x317370
ORIGINAL_NATIVE_TEXT_END = 0xAD751C
ORIGINAL_NATIVE_TEXT_SHA256 = (
    "c696e73028669cfeed82ab3c4ceb216eff5dddd919101c3b4ec488580ecb6b15"
)
# Exactly the source words also pinned by the optional research hook.
ORIGINAL_SCENE_ANCHORS = {
    0x31755C: 0xD10143FF,  # static JNI MyActivity.appUpdateDraw()V
    0x71BF24: 0xB0002040,  # getter from original scene consumer context
    0x71BF28: 0x911CC000,
    0x71BF2C: 0xD65F03C0,
    0x71C408: 0xA9BB7BFD,  # original scene dispatcher
    0x71C458: 0xB9348001,  # STR W1,[X0,#0x3480]
    # Passive LEVEL original JNI research witness; fail closed if LIEF moved
    # any exact original function before owner-private APK signing.
    0x53B2BC: 0xA9BB7BFD,  # original unit effective-cap getter(int)
    0x53BE0C: 0xA9BA7BFD,  # original upgrade-allowed predicate(int)
    0x8B9FC8: 0xD10103FF,  # original SAVE_DATA serializer wrapper(void*)
    # Exact original caller edges. Getter's only direct caller builds a level
    # text; eligibility has five callers, including actual upgrade 0x8581FC.
    0x821904: 0x97F4666E,  # BL -> 0x53B2BC (label-related caller)
    0x8581FC: 0x97F38F04,  # BL -> 0x53BE0C (upgrade eligibility)
    0x85C734: 0x97F37DB6,
    0x860224: 0x97F36EFA,
    0x88CB00: 0x97F2BCC3,
    0x88E884: 0x97F2B562,
    0x858390: 0x940600D5,  # BL -> original XP encoded write
    0x8583B8: 0x9405CF25,  # BL -> CURRENT level upper16 +1
}
ELF64_LOAD = 1
ELF64_DYNSYM = 11
ELF64_SYM_ENTRY_SIZE = 24


class OriginalSceneNativeImageError(ValueError):
    """A non-exact mapped scene layout cannot safely be instrumented."""


def _bounded_offset(length: int, start: int, size: int) -> bool:
    return (
        type(start) is int and type(size) is int
        and 0 <= start <= length and 0 <= size <= length - start
    )


def _program_headers(native: bytes) -> list[dict[str, int]]:
    if len(native) < 64 or elf_machine(native) != EM_AARCH64:
        raise OriginalSceneNativeImageError("not an ELF64 AArch64 image")
    phoff = struct.unpack_from("<Q", native, 32)[0]
    size = struct.unpack_from("<H", native, 54)[0]
    count = struct.unpack_from("<H", native, 56)[0]
    if size < 56 or not 1 <= count <= 128 or not _bounded_offset(
        len(native), phoff, size * count
    ):
        raise OriginalSceneNativeImageError("ELF64 program-header extent invalid")
    items = []
    for i in range(count):
        at = phoff + i * size
        p_type, p_flags, p_offset, p_vaddr, _, p_filesz, p_memsz, _ = (
            struct.unpack_from("<IIQQQQQQ", native, at)
        )
        if p_type != ELF64_LOAD:
            continue
        if not _bounded_offset(len(native), p_offset, p_filesz):
            raise OriginalSceneNativeImageError("mapped original LOAD file span unsafe")
        if p_memsz < p_filesz or p_vaddr + p_memsz >= (1 << 64):
            raise OriginalSceneNativeImageError("original LOAD memory range unsafe")
        items.append({
            "flags": p_flags, "offset": p_offset,
            "vaddr": p_vaddr, "filesz": p_filesz,
        })
    if not items:
        raise OriginalSceneNativeImageError("ELF has no mapped text LOAD segment")
    return items


def _mapped_opcode(native: bytes, loads: list[dict[str, int]], vma: int) -> int:
    matching = [
        p for p in loads
        if p["vaddr"] <= vma and vma + 4 <= p["vaddr"] + p["filesz"]
    ]
    if len(matching) != 1 or matching[0]["flags"] & 1 == 0:
        raise OriginalSceneNativeImageError(
            f"original executable scene VMA 0x{vma:x} is not unique and mapped"
        )
    item = matching[0]
    return struct.unpack_from(
        "<I", native, item["offset"] + (vma - item["vaddr"])
    )[0]


def _original_executable_text_sha256(
    native: bytes, loads: list[dict[str, int]],
) -> str:
    """Hash the FULL original JP .text through unambiguous executable PT_LOAD.

    LIEF may legitimately change raw ELF file offsets when inserting a
    DT_NEEDED record, but the original mapped instruction bytes and VMAs
    must remain IDENTICAL. Fail closed on missing/overlapping/non-executable
    mappings or a single byte's drift. No original text is logged, returned
    or persisted; only its SHA256 appears in metadata.
    """
    start, end = ORIGINAL_NATIVE_TEXT_START, ORIGINAL_NATIVE_TEXT_END
    if start % 4 or end % 4 or start >= end:
        raise OriginalSceneNativeImageError("original .text VMA bounds invalid")
    mapped = [
        segment for segment in loads
        if (segment["flags"] & 1)
        and segment["vaddr"] <= start
        and end <= segment["vaddr"] + segment["filesz"]
    ]
    if len(mapped) != 1:
        raise OriginalSceneNativeImageError(
            "complete original executable .text mapping missing or ambiguous"
        )
    # Do not ignore overlapping auxiliary LOAD records even if non-executable.
    # A second mapping for any original .text VMA is not safe for hooking.
    overlapping = [
        segment for segment in loads
        if segment is not mapped[0]
        and segment["vaddr"] < end
        and start < segment["vaddr"] + segment["filesz"]
    ]
    if overlapping:
        raise OriginalSceneNativeImageError(
            "complete original executable .text has ambiguous LOAD overlap"
        )
    seg = mapped[0]
    at = seg["offset"] + (start - seg["vaddr"])
    size = end - start
    if not _bounded_offset(len(native), at, size):
        raise OriginalSceneNativeImageError("original executable .text extent unsafe")
    return sha256(native[at:at + size]).hexdigest()


def _dynsym_export_vma(native: bytes, symbol: str) -> int:
    """Read exactly one original JNI function dynamic symbol (no disassembler).

    Require section headers, as present in the pinned original JP15.7.1 and
    LIEF's normal output. Without them, do NOT gamble with a blind hook.
    """
    shoff = struct.unpack_from("<Q", native, 40)[0]
    shentsize = struct.unpack_from("<H", native, 58)[0]
    shnum = struct.unpack_from("<H", native, 60)[0]
    if shentsize < 64 or not 1 <= shnum <= 2048 or not _bounded_offset(
        len(native), shoff, shentsize * shnum
    ):
        raise OriginalSceneNativeImageError("ELF64 section headers unavailable")
    sections = []
    for i in range(shnum):
        at = shoff + i * shentsize
        fields = struct.unpack_from("<IIQQQQIIQQ", native, at)
        sections.append({
            "type": fields[1], "offset": fields[4], "size": fields[5],
            "link": fields[6], "entsize": fields[9],
        })
    located = []
    expected = symbol.encode("ascii")
    for sec in sections:
        if sec["type"] != ELF64_DYNSYM:
            continue
        if (sec["link"] >= len(sections)
            or sec["entsize"] != ELF64_SYM_ENTRY_SIZE
            or sec["size"] % ELF64_SYM_ENTRY_SIZE != 0
            or not _bounded_offset(len(native), sec["offset"], sec["size"])):
            raise OriginalSceneNativeImageError("native dynamic symbol table invalid")
        strings = sections[sec["link"]]
        if not _bounded_offset(len(native), strings["offset"], strings["size"]):
            raise OriginalSceneNativeImageError("dynamic symbol names outside ELF")
        names = native[strings["offset"]:strings["offset"]+strings["size"]]
        for i in range(0, sec["size"], ELF64_SYM_ENTRY_SIZE):
            at = sec["offset"] + i
            name_index, info, _, shndx, value, _ = struct.unpack_from(
                "<IBBHQQ", native, at
            )
            if name_index >= len(names):
                raise OriginalSceneNativeImageError("dynamic symbol name out of bounds")
            end = names.find(b"\x00", name_index)
            if end < 0:
                raise OriginalSceneNativeImageError("unterminated dynamic symbol")
            if names[name_index:end] == expected:
                if shndx == 0 or (info & 0xF) != 2:
                    raise OriginalSceneNativeImageError("original JNI export undefined/non-function")
                located.append(value)
    if len(located) != 1:
        raise OriginalSceneNativeImageError("exact original JNI draw export missing or duplicated")
    return located[0]


def verify_mapped_original_scene_image(native: bytes) -> dict[str, Any]:
    """Reject incorrect post-LIEF original VMAs BEFORE optional hook signing."""
    if type(native) is not bytes:
        raise OriginalSceneNativeImageError("expected bytes from private arm64 split")
    try:
        build_id = gnu_build_id(native)
    except (ValueError, IndexError, struct.error) as exc:
        raise OriginalSceneNativeImageError("invalid original native GNU note") from exc
    if build_id != ORIGINAL_JP1571_BUILD_ID:
        raise OriginalSceneNativeImageError("original JP15.7.1 ELF GNU Build ID drift")
    loads = _program_headers(native)
    for vma, expected in ORIGINAL_SCENE_ANCHORS.items():
        actual = _mapped_opcode(native, loads, vma)
        if actual != expected:
            raise OriginalSceneNativeImageError(
                f"original mapped ARM64 instruction drift at 0x{vma:x}"
            )
    if _dynsym_export_vma(native, ORIGINAL_DRAW_SYMBOL) != ORIGINAL_DRAW_VMA:
        raise OriginalSceneNativeImageError("original JNI draw export VMA changed")
    full_text_digest = _original_executable_text_sha256(native, loads)
    if full_text_digest != ORIGINAL_NATIVE_TEXT_SHA256:
        raise OriginalSceneNativeImageError(
            "complete original JP15.7.1 executable .text SHA256 drift"
        )
    return {
        "status": "PINNED_REPACKAGED_JP1571_ORIGINAL_SCENE_VMA_AND_EXPORT_VERIFIED",
        "mapped_source_native_sha256": sha256(native).hexdigest(),
        "pinned_original_build_id": build_id,
        "original_JNI_draw_export_vma": f"0x{ORIGINAL_DRAW_VMA:x}",
        "verified_executable_instruction_anchors": len(ORIGINAL_SCENE_ANCHORS),
        "complete_original_text_bytes_verified":
            ORIGINAL_NATIVE_TEXT_END - ORIGINAL_NATIVE_TEXT_START,
        "complete_original_text_sha256": full_text_digest,
        "all_original_executable_text_bytes_unchanged_static": True,
        "repacked_original_native_hook_layout_safe_static": True,
        "original_account_free_player_SAVE_generated": False,
        "actual_Android_inline_hook_attach_verified": False,
        "original_device_first_boot_or_zero_egress_verified": False,
        "user_original_APK_SAVE_or_asset_modified": False,
    }


def verify_staged_original_scene_before_signing(
    unsigned_splits: "Path", *, research_scene_witness: bool,
) -> dict[str, Any] | None:
    """Read the FINAL unsigned arm64 research split BEFORE any APK signing.

    The existing post-sign parity check remains independent defense in depth.
    Feature-OFF builds never need this expensive exact-original scene check.
    """
    from pathlib import Path
    from zipfile import BadZipFile, ZipFile

    if not research_scene_witness:
        return None
    if (not isinstance(unsigned_splits, Path)
        or unsigned_splits.is_symlink()
        or not unsigned_splits.is_dir()):
        raise OriginalSceneNativeImageError(
            "unsigned original research split directory missing or unsafe"
        )
    arm64 = unsigned_splits / "split_config.arm64_v8a.apk"
    if arm64.is_symlink() or not arm64.is_file():
        raise OriginalSceneNativeImageError(
            "no safe unsigned original ARM64 research split"
        )
    path = "lib/arm64-v8a/libnative-lib.so"
    try:
        with ZipFile(arm64, "r") as archive:
            members = archive.infolist()
            matching = [member for member in members if member.filename == path]
            if len(matching) != 1:
                raise OriginalSceneNativeImageError(
                    "unsigned original research split has missing or duplicate native entry"
                )
            member = matching[0]
            if member.file_size < 64 or member.file_size > 24 * 1024 * 1024:
                raise OriginalSceneNativeImageError(
                    "unsigned original research native entry size invalid"
                )
            original_repackaged = archive.read(member)
    except (OSError, BadZipFile, RuntimeError, EOFError, ValueError) as exc:
        if isinstance(exc, OriginalSceneNativeImageError):
            raise
        raise OriginalSceneNativeImageError(
            "unsigned original native split unreadable"
        ) from exc
    result = verify_mapped_original_scene_image(original_repackaged)
    result["research_pre_signature_gate_executed"] = True
    result["research_apk_signing_performed_by_this_gate"] = False
    result["original_owner_save_accessed_by_gate"] = False
    return result
