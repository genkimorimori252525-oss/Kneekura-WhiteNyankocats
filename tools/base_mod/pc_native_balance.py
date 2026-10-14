"""PC-only exact ARM64 adapter injection, with independently reproducible gate.

No proprietary instruction bodies: only approved displaced instruction
words and tiny original-call adapters. Everything else in original .text must
still hash to the pinned JP15.7.1 source after restoring these ten words.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import struct
import tempfile
from zipfile import ZipFile

from tools.base_mod.inject_shim import (
    _import_lief, _export_names, _clone_info, _is_signature_entry, NATIVE_ENTRY,
    TARGET_NATIVE_BUILD_ID,
)
from tools.base_mod.elf_anchor import gnu_build_id

DISPATCH_SYMBOL = 'kneekura_pc_balance_dispatch'
# operation, source VMA, original opcode, original continuation/call target
SITES = (
    (1, 0x99c4e0, 0x36000097, 0),
    (2, 0x5e5178, 0x940ecc71, 0x99833c),
    (3, 0x990f54, 0xb8296913, 0x990f58),
    (4, 0x8ee878, 0x940289a9, 0x990f1c),
    (5, 0x99cb94, 0xb8696916, 0x99cb98),
    (6, 0x99ce18, 0x1b097d19, 0x99ce1c),
    (7, 0x488b78, 0x1b175aa8, 0x488b7c),
    (8, 0x488b30, 0x94145156, 0x99d088),
    (9, 0x5fa514, 0x1a9fd7e0, 0x5fa518),
    (10, 0x53b980, 0xb86a6929, 0x53b984),
)
RX_MARKER = b'KNEEKURA_PC_BALANCE_RX_V3\0'
RW_MARKER = b'KNEEKURA_PC_BALANCE_RW_V3\0'
STUB_START = 64
STUB_STRIDE = 320


def branch(pc: int, target: int, *, link: bool = False) -> int:
    delta=target-pc
    if delta % 4 or not -(1 << 27) <= delta < (1 << 27):
        raise ValueError('PC_BALANCE_BRANCH_RANGE')
    return (0x94000000 if link else 0x14000000) | ((delta//4)&0x3ffffff)


def make_stub(pc: int, got: int, shift: int, site: tuple[int,int,int,int]) -> bytes:
    op,_,word,target=site
    words=[]
    # Execute the displaced memory load/store or integer multiply exactly once.
    if op in (3,5,6,7,9,10): words.append(word)
    words.append(0xd10003ff | (768 << 10)) # sub sp,sp,#768
    for i in range(0,30,2):
        words.append(0xa9000000 | ((i*8//8)<<15) | ((i+1)<<10) | (31<<5) | i)
    words.extend((0xf90003fe | (30<<10), 0xd53b4210,
                  0xf90003f0 | (31<<10)))
    for i in range(0,32,2):
        words.append(0xad000000 | (((256+i*16)//16)<<15) | ((i+1)<<10) | (31<<5) | i)
    words.extend((0x910003e0,0x52800001 | (op<<5)))
    adrp_pc=pc+len(words)*4
    pages=((got&~4095)-(adrp_pc&~4095))//4096
    if not -(1<<20)<=pages<(1<<20) or got%8: raise ValueError('PC_BALANCE_GOT_RANGE')
    words.extend((0x90000010 | ((pages&3)<<29) | (((pages>>2)&0x7ffff)<<5),
                  0xf9400210 | ((got%4096//8)<<10),0xd63f0200))
    for i in range(0,32,2):
        words.append(0xad400000 | (((256+i*16)//16)<<15) | ((i+1)<<10) | (31<<5) | i)
    words.extend((0xf94003f0 | (31<<10),0xd51b4210))
    for i in range(0,30,2):
        words.append(0xa9400000 | (i<<15) | ((i+1)<<10) | (31<<5) | i)
    words.extend((0xf94003fe | (30<<10),0x910003ff | (768<<10)))
    if op==1:
        words.append(0x37000057) # tbnz w23,#0, +8; original TBZ's two edges
        words.append(branch(pc+len(words)*4,0x99c4f0+shift))
        words.append(branch(pc+len(words)*4,0x99c4e4+shift))
    else:
        words.append(branch(pc+len(words)*4,target+shift))
    data=struct.pack('<'+'I'*len(words),*words)
    if len(data)>STUB_STRIDE: raise ValueError('PC_BALANCE_STUB_TOO_LARGE')
    return data


def _marker_segment(binary, marker):
    matches=[s for s in binary.segments if bytes(s.content).startswith(marker)]
    if len(matches)!=1: raise ValueError('PC_BALANCE_SEGMENT_MISSING_OR_DUPLICATE')
    return matches[0]


def _shift(binary):
    symbol=binary.get_dynamic_symbol('Java_jp_co_ponos_battlecats_MyActivity_appUpdateDraw')
    if symbol is None: raise ValueError('PC_BALANCE_ORIGINAL_DRAW_MISSING')
    shift=symbol.value-0x31755c
    if shift<0 or shift>0x10000 or shift%4096: raise ValueError('PC_BALANCE_REBASE_UNSAFE')
    return shift


def _rx_content(rx,got,shift):
    out=bytearray(struct.pack('<I',0xd4200000)*1024)
    out[:64]=RX_MARKER.ljust(64,b'\0')
    for i,site in enumerate(SITES):
        offset=STUB_START+i*STUB_STRIDE
        stub=make_stub(rx+offset,got,shift,site)
        out[offset:offset+len(stub)]=stub
    return bytes(out)


def verify_and_restore(native: bytes):
    """Validate every adapter byte/relocation, then restore ONLY approved words."""
    lief=_import_lief()
    binary=lief.parse(list(native))
    if binary is None or gnu_build_id(native)!=TARGET_NATIVE_BUILD_ID:
        raise ValueError('PC_BALANCE_ORIGINAL_BUILD_ID_CHANGED')
    shift=_shift(binary)
    rx=_marker_segment(binary,RX_MARKER)
    rw=_marker_segment(binary,RW_MARKER)
    if (rx.type!=lief.ELF.Segment.TYPE.LOAD or int(rx.flags)!=5 or len(rx.content)!=4096
        or rx.virtual_size!=4096 or rw.type!=lief.ELF.Segment.TYPE.LOAD
        or int(rw.flags)!=6 or len(rw.content)!=4096 or rw.virtual_size!=4096):
        raise ValueError('PC_BALANCE_SEGMENT_PERMISSIONS_CHANGED')
    got=rw.virtual_address+64
    if bytes(rx.content)!=_rx_content(rx.virtual_address,got,shift):
        raise ValueError('PC_BALANCE_ADAPTER_BYTES_CHANGED')
    if bytes(rw.content)!=RW_MARKER.ljust(4096,b'\0'):
        raise ValueError('PC_BALANCE_GOT_INITIAL_BYTES_CHANGED')
    relocs=[r for r in binary.relocations if got-7 <= r.address < got+8]
    if (len(relocs)!=1 or relocs[0].type!=lief.ELF.Relocation.TYPE.AARCH64_GLOB_DAT
        or relocs[0].address!=got
        or relocs[0].symbol is None or relocs[0].symbol.name!=DISPATCH_SYMBOL
        or relocs[0].addend!=0): raise ValueError('PC_BALANCE_DISPATCH_RELOCATION_CHANGED')
    symbol=relocs[0].symbol
    if (symbol.shndx!=0 or symbol.value!=0 or symbol.size!=0
        or symbol.binding!=lief.ELF.Symbol.BINDING.GLOBAL
        or symbol.type!=lief.ELF.Symbol.TYPE.FUNC
        or symbol.visibility!=lief.ELF.Symbol.VISIBILITY.DEFAULT
        or sum(s.name==DISPATCH_SYMBOL for s in binary.dynamic_symbols)!=1
        or symbol.symbol_version is None or symbol.symbol_version.value not in (0,1)):
        raise ValueError('PC_BALANCE_DISPATCH_IMPORT_CHANGED')
    restored=bytearray(native)
    for i,(op,vma,word,_) in enumerate(SITES):
        address=vma+shift
        seg=binary.segment_from_virtual_address(address)
        if seg is None or int(seg.flags)!=5: raise ValueError('PC_BALANCE_SITE_UNMAPPED')
        offset=seg.file_offset+address-seg.virtual_address
        expected=branch(address,rx.virtual_address+STUB_START+i*STUB_STRIDE,link=op in (2,4,8))
        if struct.unpack_from('<I',native,offset)[0]!=expected:
            raise ValueError('PC_BALANCE_SITE_BRANCH_CHANGED')
        struct.pack_into('<I',restored,offset,word)
    return bytes(restored),dict(schema='pc-native-balance-v3',source_build_id=TARGET_NATIVE_BUILD_ID,
                              source_sites=[hex(s[1]) for s in SITES],uniform_vma_shift=shift,
                              adapter_sha256=hashlib.sha256(bytes(rx.content)).hexdigest(),
                              xp_only_level_policy=False,original_catseye_level_policy=True,
                              full_original_text_restore_gate_required=True)


def inject(native: bytes):
    from tools.base_mod.original_scene_native_image_gate import verify_mapped_original_scene_image
    # Full source executable validation before any permitted changes.
    verify_mapped_original_scene_image(native,expected_research_native_package='jp.kn.local.battlecats')
    lief=_import_lief()
    binary=lief.parse(list(native))
    before_exports=_export_names(binary)
    if binary.get_dynamic_symbol(DISPATCH_SYMBOL) is not None:
        raise ValueError('PC_BALANCE_ALREADY_INJECTED')
    for marker,flags in ((RX_MARKER,5),(RW_MARKER,6)):
        segment=lief.ELF.Segment()
        segment.type=lief.ELF.Segment.TYPE.LOAD
        segment.flags=lief.ELF.Segment.FLAGS(flags)
        segment.alignment=4096
        segment.content=list(marker.ljust(4096,b'\0'))
        binary.add(segment)
    rw=_marker_segment(binary,RW_MARKER)
    symbol=lief.ELF.Symbol()
    symbol.name=DISPATCH_SYMBOL
    symbol.type=lief.ELF.Symbol.TYPE.FUNC
    symbol.binding=lief.ELF.Symbol.BINDING.GLOBAL
    symbol=binary.add_dynamic_symbol(symbol)
    relocation=lief.ELF.Relocation(rw.virtual_address+64,
                                  lief.ELF.Relocation.TYPE.AARCH64_GLOB_DAT,
                                  lief.ELF.Relocation.ENCODING.RELA)
    relocation.symbol=symbol
    binary.add_dynamic_relocation(relocation)
    with tempfile.TemporaryDirectory(prefix='pc-native-adapter-') as temporary:
        path=Path(temporary)/'mapped.so'
        binary.write(str(path))
        staged=bytearray(path.read_bytes())
        binary=lief.parse(str(path))
        shift=_shift(binary)
        rx=_marker_segment(binary,RX_MARKER)
        rw=_marker_segment(binary,RW_MARKER)
        staged[rx.file_offset:rx.file_offset+4096]=_rx_content(rx.virtual_address,rw.virtual_address+64,shift)
        for i,(op,vma,word,_) in enumerate(SITES):
            address=vma+shift
            seg=binary.segment_from_virtual_address(address)
            offset=seg.file_offset+address-seg.virtual_address
            if struct.unpack_from('<I',staged,offset)[0]!=word: raise ValueError('PC_BALANCE_SITE_SOURCE_CHANGED')
            struct.pack_into('<I',staged,offset,branch(address,rx.virtual_address+STUB_START+i*STUB_STRIDE,link=op in (2,4,8)))
        result=bytes(staged)
        restored,receipt=verify_and_restore(result)
        verify_mapped_original_scene_image(restored,expected_research_native_package='jp.kn.local.battlecats')
        if _export_names(binary)!=before_exports: raise ValueError('PC_BALANCE_ORIGINAL_EXPORTS_CHANGED')
        return result,receipt


def patch_split(source: Path, output: Path):
    with ZipFile(source) as before, ZipFile(output,'w') as after:
        receipt=None
        if sum(i.filename==NATIVE_ENTRY for i in before.infolist())!=1:
            raise ValueError('PC_BALANCE_NATIVE_ENTRY_DUPLICATE')
        for member in before.infolist():
            if _is_signature_entry(member.filename): continue
            value=before.read(member)
            if member.filename==NATIVE_ENTRY: value,receipt=inject(value)
            after.writestr(_clone_info(member),value)
    return receipt
