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
# Original JP15.7.1 native ELF bounded source section hashes. Unlike
# rebuilt .dynstr / .dynamic, these must retain their exact bytes and their
# exact relative VMA spacing under any permitted uniform LIEF rebase.
ORIGINAL_PINNED_MAPPED_RANGES = {
    "gnu_note": (0x2D0, 0x24, "3514bdcd4f01ba1d879537a9c00a27e34b604118b470409588156f9c0e1116c1"),
    "rodata": (0x18F2C0, 0x6E784, "2e471f7dfcdfb9bb5e2bac68ab3d400ccc318aaab8daf0989a6526dc92126852"),
    "eh_frame": (0x22ABC0, 0xEC7B0, "0114d3eea2ed0315707957afa0016eb4f702e649558dd7097cc01deed7a92fec"),
    "lcxx_override": (0xAD751C, 0x10C, "a761a6710c195e92a9e8395970814288089fcedb11d2c2c78d156eacc7d28c62"),
    "plt": (0xAD7630, 0x7020, "2ed884a4ab2697036f71cd3255f000463cca6d80311faa7427cbf93ba0738050"),
}
ORIGINAL_MAX_ALLOWED_UNIFORM_VMA_REBASE = 0x10000
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
    native: bytes, loads: list[dict[str, int]], *, vma_shift: int = 0,
) -> str:
    """Hash the FULL original JP .text through unambiguous executable PT_LOAD.

    LIEF may legitimately change raw ELF file offsets when inserting a
    DT_NEEDED record, but the original mapped instruction bytes and VMAs
    must remain IDENTICAL. Fail closed on missing/overlapping/non-executable
    mappings or a single byte's drift. No original text is logged, returned
    or persisted; only its SHA256 appears in metadata.
    """
    start = ORIGINAL_NATIVE_TEXT_START + vma_shift
    end = ORIGINAL_NATIVE_TEXT_END + vma_shift
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


def _pinned_mapped_range_sha256(
    native: bytes, loads: list[dict[str, int]], *,
    vma: int, size: int, require_exec: bool | None = None,
) -> str:
    """Use ELF PT_LOAD mappings, never raw file offsets as shifted VMAs.

    Reject overlapping/unbacked mappings or unexpected permissions.
    No native source bytes are exported, only source SHA-256 receipts.
    """
    if (type(vma) is not int or type(size) is not int or size <= 0
        or vma < 0 or vma + size > (1 << 64)):
        raise OriginalSceneNativeImageError("native source mapped range invalid")
    matched = [
        seg for seg in loads
        if seg["vaddr"] <= vma
        and vma + size <= seg["vaddr"] + seg["filesz"]
    ]
    if len(matched) != 1:
        raise OriginalSceneNativeImageError("original native source range unmapped")
    seg = matched[0]
    for other in loads:
        if (other is not seg and other["vaddr"] < vma + size
            and vma < other["vaddr"] + other["filesz"]):
            raise OriginalSceneNativeImageError("original native source mappings overlap")
    if require_exec is not None and bool(seg["flags"] & 1) != require_exec:
        raise OriginalSceneNativeImageError("original native source mapping permissions drift")
    offset = seg["offset"] + (vma - seg["vaddr"])
    if not _bounded_offset(len(native), offset, size):
        raise OriginalSceneNativeImageError("original native source range outside ELF")
    return sha256(native[offset:offset + size]).hexdigest()


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
    installed_draw_vma = _dynsym_export_vma(native, ORIGINAL_DRAW_SYMBOL)
    vma_shift = installed_draw_vma - ORIGINAL_DRAW_VMA
    if (vma_shift < 0
        or vma_shift > ORIGINAL_MAX_ALLOWED_UNIFORM_VMA_REBASE
        or vma_shift % 0x1000 != 0):
        raise OriginalSceneNativeImageError(
            "original JNI draw export has unsupported nonuniform VMA shift"
        )
    for vma, expected in ORIGINAL_SCENE_ANCHORS.items():
        relocated_pc = vma + vma_shift
        actual = _mapped_opcode(native, loads, relocated_pc)
        if actual != expected:
            raise OriginalSceneNativeImageError(
                f"original mapped ARM64 instruction drift at 0x{relocated_pc:x}"
            )
    full_text_digest = _original_executable_text_sha256(
        native, loads, vma_shift=vma_shift
    )
    if full_text_digest != ORIGINAL_NATIVE_TEXT_SHA256:
        raise OriginalSceneNativeImageError(
            "complete original JP15.7.1 executable .text SHA256 drift"
        )
    verified_nontext = {}
    for label, (vma, size, original_sha) in ORIGINAL_PINNED_MAPPED_RANGES.items():
        actual = _pinned_mapped_range_sha256(
            native, loads, vma=vma + vma_shift, size=size,
            require_exec=True,
        )
        if actual != original_sha:
            raise OriginalSceneNativeImageError(
                "original JP15.7.1 mapped source section SHA256 drift: " + label
            )
        verified_nontext[label] = actual
    return {
        "status": "PINNED_REPACKAGED_JP1571_ORIGINAL_SCENE_VMA_AND_EXPORT_VERIFIED",
        "mapped_source_native_sha256": sha256(native).hexdigest(),
        "pinned_original_build_id": build_id,
        "original_JNI_draw_export_vma": f"0x{installed_draw_vma:x}",
        "original_source_uniform_VMA_rebase_bytes": vma_shift,
        "uniform_rebase_runtime_supported_by_device": False,
        "verified_nontext_mapped_source_sections": verified_nontext,
        "verified_executable_instruction_anchors": len(ORIGINAL_SCENE_ANCHORS),
        "complete_original_text_bytes_verified":
            ORIGINAL_NATIVE_TEXT_END - ORIGINAL_NATIVE_TEXT_START,
        "complete_original_text_sha256": full_text_digest,
        "all_original_executable_text_bytes_unchanged_static": True,
        "original_JP_build_data_only_repacked_dynamic_sections_allowed": True,
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

# This tool intentionally never creates an APK, native ELF output, player
# SAVE, public artifact, signing key, or device-side installation. Only hashes.
ORIGINAL_OWNER_EXPORT_SHA256 = (
    "38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56"
)
ORIGINAL_OWNER_NATIVE_SHA256 = (
    "333d2974ab2ff881fd70087fd62dea7d12d82addbc55cab2f2a675ad67e3a7e2"
)


def probe_owner_original_lief_roundtrip(
    owner_export: "Path", *, baseline_only: bool = False,
    native_rewriter=None,
) -> dict[str, Any]:
    """Exercise the real owned original native bytes and optional LIEF rewrite.

    This is deliberately NOT an installer. The only original asset read from
    the archive is the ARM64 native image; neither SAVE nor InstallPack data
    are read. The modified native stays in memory, is verified and destroyed.
    An injected test rewriter is supported only for synthetic unit tests.
    """
    from hashlib import sha256 as digest
    from io import BytesIO
    from pathlib import Path
    from zipfile import ZipFile, BadZipFile

    if (not isinstance(owner_export, Path) or owner_export.is_symlink()
        or not owner_export.is_file() or owner_export.stat().st_size > 300_000_000):
        raise OriginalSceneNativeImageError("unsafe or missing owned original export")
    with owner_export.open("rb") as stream:
        hashed = digest()
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hashed.update(chunk)
    if hashed.hexdigest() != ORIGINAL_OWNER_EXPORT_SHA256:
        raise OriginalSceneNativeImageError("original JP15.7.1 ZIP SHA256 mismatch")
    split_entry = "apk/split_config.arm64_v8a.apk"
    native_entry = "lib/arm64-v8a/libnative-lib.so"
    try:
        with ZipFile(owner_export) as archive:
            matching_splits = [
                member for member in archive.infolist()
                if member.filename == split_entry
            ]
            if len(matching_splits) != 1 or not (
                100_000 <= matching_splits[0].file_size <= 80_000_000
            ):
                raise OriginalSceneNativeImageError(
                    "original owner ARM64 split missing/ambiguous or oversized"
                )
            split_bytes = archive.read(matching_splits[0])
        with ZipFile(BytesIO(split_bytes)) as split:
            matching_native = [
                member for member in split.infolist()
                if member.filename == native_entry
            ]
            if len(matching_native) != 1 or not (
                64 <= matching_native[0].file_size <= 24_000_000
            ):
                raise OriginalSceneNativeImageError(
                    "original owner ARM64 native missing/ambiguous or oversized"
                )
            original = split.read(matching_native[0])
    except (OSError, BadZipFile, RuntimeError, EOFError) as exc:
        raise OriginalSceneNativeImageError(
            "original ARM64 private source archive unreadable"
        ) from exc
    original_sha = digest(original).hexdigest()
    if original_sha != ORIGINAL_OWNER_NATIVE_SHA256:
        raise OriginalSceneNativeImageError("original JP15.7.1 native SHA256 drift")
    original_gate = verify_mapped_original_scene_image(original)
    receipt: dict[str, Any] = {
        "schema": "kneekura-original-level-native-lief-probe-v1",
        "status": "PASS_ORIGINAL_JP1571_NATIVE_SOURCE_BASELINE_ONLY",
        "source_export_sha256": ORIGINAL_OWNER_EXPORT_SHA256,
        "original_native_sha256": original_sha,
        "original_native_build_id": original_gate["pinned_original_build_id"],
        "original_instruction_anchor_count":
            original_gate["verified_executable_instruction_anchors"],
        "original_executable_text_sha256":
            original_gate["complete_original_text_sha256"],
        "original_executable_text_bytes":
            original_gate["complete_original_text_bytes_verified"],
        "original_library_LIEF_rewrite_executed": False,
        "original_text_preserved_after_LIEF_rewrite": False,
        "changed_native_candidate_sha256": None,
        "original_APK_or_SAVE_written": False,
        "original_restricted_account_or_PONOS_endpoint_contacted": False,
        "original_Android_runtime_played": False,
        "original_game_Lv60_and_offline_SAVE_verified": False,
        "ready_to_sign_or_install": False,
    }
    if baseline_only:
        return receipt
    try:
        if native_rewriter is None:
            from tools.base_mod.inject_shim import add_needed_dependency
            native_rewriter = add_needed_dependency
        rewritten, ledger = native_rewriter(original)
    except RuntimeError as exc:
        receipt["status"] = (
            "BLOCKED_LIEF_DEPENDENCY_UNAVAILABLE"
            if "LIEF is required" in str(exc)
            else "BLOCKED_LIEF_REWRITE_RUNTIME_FAILURE"
        )
        return receipt
    except (OSError, ValueError, TypeError):
        receipt["status"] = "BLOCKED_LIEF_REWRITE_FAILURE"
        return receipt
    if (type(rewritten) is not bytes
        or not isinstance(ledger, dict)
        or len(rewritten) < 64 or len(rewritten) > 32_000_000
        or "libkneekura.so" not in ledger.get("libraries_after", [])
        or "libkneekura.so" in ledger.get("libraries_before", [])
        or ledger.get("export_surface_preserved") is not True):
        receipt["status"] = "BLOCKED_LIEF_DEPENDENCY_OR_EXPORT_INVARIANT"
        return receipt
    receipt["original_library_LIEF_rewrite_executed"] = True
    receipt["changed_native_candidate_sha256"] = digest(rewritten).hexdigest()
    try:
        mapped = verify_mapped_original_scene_image(rewritten)
    except (OriginalSceneNativeImageError, ValueError):
        receipt["status"] = "BLOCKED_LIEF_ORIGINAL_GAME_NATIVE_CODE_LAYOUT_DRIFT"
        return receipt
    receipt["original_text_preserved_after_LIEF_rewrite"] = (
        mapped["complete_original_text_sha256"]
        == original_gate["complete_original_text_sha256"]
    )
    receipt["status"] = "PASS_PRIVATE_TEMP_NATIVE_LIEF_ROUNDTRIP_ONLY"
    return receipt


def main_owner_native_probe(argv: list[str] | None = None) -> int:
    """Read-only private owner command; optionally write small JSON metadata."""
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser(
        description="JP15.7.1 owner-private original ARM64 native source/LIEF check"
    )
    parser.add_argument("--owned-export", required=True, type=Path)
    parser.add_argument("--baseline-only", action="store_true")
    parser.add_argument("--metadata-output", type=Path)
    args = parser.parse_args(argv)
    try:
        receipt = probe_owner_original_lief_roundtrip(
            args.owned_export, baseline_only=args.baseline_only
        )
        if args.metadata_output is not None:
            target = args.metadata_output
            if (target.suffix.lower() != ".json" or target.is_symlink()
                or target.exists()):
                raise OriginalSceneNativeImageError(
                    "metadata output must be a NEW non-symlink JSON path"
                )
            encoded = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")
            if len(encoded) > 16_384:
                raise OriginalSceneNativeImageError("metadata receipt unexpectedly large")
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as out:
                out.write(encoded)
    except (OriginalSceneNativeImageError, OSError, ValueError):
        print("BLOCKED_UNSAFE_OR_MISMATCHED_OWNER_SOURCE_OR_METADATA_OUTPUT")
        return 3
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"].startswith("PASS_") else 3


if __name__ == "__main__":
    raise SystemExit(main_owner_native_probe())
