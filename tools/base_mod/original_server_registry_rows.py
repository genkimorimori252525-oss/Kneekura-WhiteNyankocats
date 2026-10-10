"""Read-only reconstruction of JP15.7.1's 92 native Server registration rows.

Only emulate the pinned *straight-line* AArch64 .init_array constructor slice
that writes the 92 std::string short-string pairs into original .bss.
This does not execute Android native code, open .pack assets or author a SAVE.
"""
from __future__ import annotations

from hashlib import sha256
import re
import struct

NATIVE_SHA256 = "333d2974ab2ff881fd70087fd62dea7d12d82addbc55cab2f2a675ad67e3a7e2"
FIRST_OPCODE = 0x71599C
END_OPCODE = 0x716F24  # exclusive; original next instruction is __cxa_atexit BL
TABLE_BASE = 0xF98D38
TABLE_COUNT = 92
ROW_SIZE = 0x30
EXPECTED_CTOR_SLICE_SHA256 = "ea9dc2235a775d01758aa15b7a272fdfe0796e8bafd697dadb8fc4e18b0b9c95"
EXPECTED_RECONSTRUCTED_TABLE_SHA256 = "f686b3b0101417f6fdd92beab705892dc5bd33c37a72fd11613ac0cb243188a1"
SEED_OPCODES = {
    0x7157D4: (0x52800394, 20, 28),  # mov w20,#28
    0x7157E0: (0x528003D7, 23, 30),  # mov w23,#30
    0x7157F8: (0x52800415, 21, 32),  # mov w21,#32
}


class ServerRegistryTraceError(ValueError):
    """Exact-source drift or unmodelled AArch64 operation; fail closed."""


def _signed(number: int, bits: int) -> int:
    return number - (1 << bits) if number & (1 << (bits - 1)) else number


class _ConstructorSlice:
    """Minimal bounded ARM64 memory interpreter; no jump, syscall or side effect."""

    def __init__(self, elf: bytes):
        self.elf = elf
        self.gpr: list[int | None] = [None] * 32
        self.vector: list[bytes | None] = [None] * 32
        self.gpr[31] = 0x700000000  # fictive SP; no SP memory operations permitted
        self.written: dict[int, int] = {}  # virtual .bss, original bytes untouched
        self.pc = FIRST_OPCODE
        for pc, (opcode, reg, value) in SEED_OPCODES.items():
            if struct.unpack_from("<I", elf, pc)[0] != opcode:
                raise ServerRegistryTraceError(f"ARM64 constructor seed drift at 0x{pc:x}")
            self.gpr[reg] = value

    def _reg(self, n: int, *, sp: bool = False) -> int:
        value = self.gpr[n] if n != 31 or sp else 0
        if value is None:
            raise ServerRegistryTraceError(f"undefined constructor register at 0x{self.pc:x}")
        return value

    def _set(self, n: int, value: int) -> None:
        if n != 31:
            self.gpr[n] = value & ((1 << 64) - 1)

    def _load(self, address: int, size: int) -> bytes:
        if (address < 0 or size < 1
            or not ((size <= 16 and address + size <= len(self.elf))
                    or TABLE_BASE <= address < address + size <= TABLE_BASE + ROW_SIZE * TABLE_COUNT)):
            raise ServerRegistryTraceError(f"outside source or BSS read at 0x{self.pc:x}")
        return bytes(
            self.written.get(address + i, self.elf[address + i]
                             if address + i < len(self.elf) else 0)
            for i in range(size)
        )

    def _store(self, address: int, data: bytes | None) -> None:
        if (data is None or not data or not
            TABLE_BASE <= address < address + len(data) <= TABLE_BASE + ROW_SIZE * TABLE_COUNT):
            raise ServerRegistryTraceError(f"outside BSS write at 0x{self.pc:x}")
        self.written.update((address + i, char) for i, char in enumerate(data))

    def _scalar_mem(self, w: int, width: int, *, read: bool = False,
                    unscaled: bool = False, preindex: bool = False) -> None:
        rt, rn = w & 31, (w >> 5) & 31
        displacement = (_signed((w >> 12) & 0x1ff, 9)
                        if unscaled or preindex else ((w >> 10) & 0xfff) * width)
        address = self._reg(rn, sp=True) + displacement
        if preindex:
            self._set(rn, address)
        if read:
            self._set(rt, int.from_bytes(self._load(address, width), "little"))
        else:
            self._store(address, self._reg(rt).to_bytes(8, "little")[:width])

    def _q_mem(self, w: int, *, read: bool = False, unscaled: bool = False) -> None:
        rt, rn = w & 31, (w >> 5) & 31
        displacement = (_signed((w >> 12) & 0x1ff, 9)
                        if unscaled else ((w >> 10) & 0xfff) * 16)
        address = self._reg(rn, sp=True) + displacement
        if read:
            self.vector[rt] = self._load(address, 16)
        else:
            self._store(address, self.vector[rt])

    def _execute_one(self, pc: int) -> None:
        self.pc = pc
        w = struct.unpack_from("<I", self.elf, pc)[0]
        top = w & 0xff000000
        if (w & 0x9f000000) == 0x90000000:  # ADRP
            displacement = (((w >> 5) & 0x7ffff) << 2) | ((w >> 29) & 3)
            self._set(w & 31, (pc & ~0xfff) + (_signed(displacement, 21) << 12))
        elif top == 0x91000000:  # ADD Xd, Xn, #immediate
            immediate = ((w >> 10) & 0xfff) << (12 if ((w >> 22) & 1) else 0)
            self._set(w & 31, self._reg((w >> 5) & 31, sp=True) + immediate)
        elif (w & 0xffc00000) == 0x3dc00000: self._q_mem(w, read=True)
        elif (w & 0xffc00000) == 0x3d800000: self._q_mem(w)
        elif (w & 0xffc00000) == 0x3c800000: self._q_mem(w, unscaled=True)
        elif (w & 0xffc00000) == 0xf9400000: self._scalar_mem(w, 8, read=True)
        elif (w & 0xffc00000) == 0xf9000000: self._scalar_mem(w, 8)
        elif (w & 0xffe00c00) == 0xf8400000: self._scalar_mem(w, 8, read=True, unscaled=True)
        elif (w & 0xffe00c00) == 0xf8000000: self._scalar_mem(w, 8, unscaled=True)
        elif (w & 0xffc00000) == 0x39000000: self._scalar_mem(w, 1)
        elif (w & 0xffe00c00) == 0x38000000: self._scalar_mem(w, 1, unscaled=True)
        elif (w & 0xffe00c00) == 0x38000c00: self._scalar_mem(w, 1, preindex=True)
        elif (w & 0xffe00c00) == 0x78000000: self._scalar_mem(w, 2, unscaled=True)
        elif (w & 0x7f800000) == 0x52800000:  # MOVZ Wd,#imm16 (zero extends)
            self._set(w & 31, ((w >> 5) & 0xffff) << (16 * ((w >> 21) & 3)))
        elif (w & 0xffe0ffe0) == 0xaa0003e0:  # MOV Xd,Xm via ORR
            # A moved register may be unknown but is not dereferenced by this
            # pinned constructor slice; preserve unknown state safely.
            self.gpr[w & 31] = self.gpr[(w >> 16) & 31]
        else:
            raise ServerRegistryTraceError(f"unknown constructor instruction 0x{w:08x} at 0x{pc:x}")

    def replay(self) -> bytes:
        for pc in range(FIRST_OPCODE, END_OPCODE, 4):
            self._execute_one(pc)
        if len(self.written) != 3408:
            raise ServerRegistryTraceError("original constructor BSS write coverage drift")
        return self._load(TABLE_BASE, ROW_SIZE * TABLE_COUNT)


def _decode_registered_pair(table: bytes, index: int) -> tuple[str, str]:
    if len(table) != TABLE_COUNT * ROW_SIZE or not 0 <= index < TABLE_COUNT:
        raise ServerRegistryTraceError("original 92 x 48 BSS row bounds drift")
    def read_short_string(raw: bytes) -> str:
        length_tag = raw[0]
        length = length_tag // 2
        if (length_tag & 1 or not 1 <= length <= 22
            or raw[length + 1] != 0 or any(raw[length + 2:])):
            raise ServerRegistryTraceError("original Server std::string SSO layout drift")
        try:
            return raw[1:1 + length].decode("ascii")
        except UnicodeDecodeError as error:
            raise ServerRegistryTraceError("original Server string non-ASCII") from error
    start = index * ROW_SIZE
    return (read_short_string(table[start:start + 24]),
            read_short_string(table[start + 24:start + ROW_SIZE]))


def recover_original_92_server_rows(elf: bytes, *, original_catalog: set[str]) -> dict:
    """Original exact SHA only; report ordered names, never bytes from a .pack.

    Constructor writes 92 local source/pack *filename pairs*, NOT 35
    download_N.tsv contents. It does not prove Android runtime initialization.
    """
    if (sha256(elf).hexdigest() != NATIVE_SHA256 or len(elf) < END_OPCODE
        or sha256(elf[FIRST_OPCODE:END_OPCODE]).hexdigest() != EXPECTED_CTOR_SLICE_SHA256):
        raise ServerRegistryTraceError("wrong original JP native or constructor slice")
    table = _ConstructorSlice(elf).replay()
    if sha256(table).hexdigest() != EXPECTED_RECONSTRUCTED_TABLE_SHA256:
        raise ServerRegistryTraceError("recovered original Server row layout digest drift")
    rows = []
    for index in range(TABLE_COUNT):
        list_name, pack_name = _decode_registered_pair(table, index)
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*Server\.list", list_name):
            raise ServerRegistryTraceError(f"original registry list name invalid at {index}")
        stem = list_name[:-5]
        if pack_name != stem + ".pack":
            raise ServerRegistryTraceError(f"original registry list/pack mismatch at {index}")
        rows.append({"registration_index": index, "family": stem,
                     "list": list_name, "pack": pack_name})
    if len({row["family"] for row in rows}) != TABLE_COUNT or (
        {row["family"] for row in rows} != original_catalog):
        raise ServerRegistryTraceError("replayed 92 pairs disagree with immutable original catalog")
    return {
        "status": "PINNED_ORIGINAL_BSS_92_REGISTERED_FILENAME_ROWS_RECONSTRUCTED",
        "source": "original ARM64 .init_array straight-line constructor slice (no execution)",
        "constructor_slice": "0x71599c..0x716f24 (end exclusive)",
        "table_base": "0xf98d38",
        "row_size": ROW_SIZE,
        "registered_pair_count": len(rows),
        "constructor_slice_sha256": EXPECTED_CTOR_SLICE_SHA256,
        "reconstructed_bss_table_sha256": EXPECTED_RECONSTRUCTED_TABLE_SHA256,
        "registered_source_rows_in_original_loop_order": rows,
        "all_92_static_pairs_reconstructed": True,
        "all_92_names_match_original_rodata_catalog": True,
        "resource_registration_success_on_android_proven": False,
        "all_35_download_tsv_payloads_bound_proven": False,
        "original_pack_data_available_or_validated": False,
        "original_offline_save_first_boot_and_lv60_proven": False,
        "owner_apk_assets_or_save_modified": False,
    }
