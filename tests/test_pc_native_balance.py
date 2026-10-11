"""Run the actual ARM64 dispatch and trampolines, without proprietary code."""
from pathlib import Path
import os
import struct
import subprocess
import tempfile
import unittest

from tools.base_mod.pc_native_balance import make_stub, SITES, DISPATCH_SYMBOL


class EncodingTests(unittest.TestCase):
    def test_rejects_unaligned_or_out_of_range_branch(self):
        from tools.base_mod.pc_native_balance import branch
        for target in (3, 1 << 28):
            with self.assertRaises(ValueError): branch(0, target)

    def test_all_adapters_fit_one_readonly_page(self):
        self.assertLess(sum(len(make_stub(0x1000000+i*512, 0x1002000, 0x1000, s))
                            for i,s in enumerate(SITES)),4096)


class Arm64ExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import unicorn
            import lief
        except ImportError:
            raise unittest.SkipTest('Private native-test-venv with unicorn/lief required')
        cls.ucmod=unicorn
        cls.lief=lief
        cls.temp=tempfile.TemporaryDirectory()
        cls.image=Path(cls.temp.name)/'balance.so'
        sdk=Path(os.environ.get('LOCALAPPDATA',''))/'Android/Sdk'
        clang=sdk/'ndk/27.2.12479018/toolchains/llvm/prebuilt/windows-x86_64/bin/clang.exe'
        if not clang.exists(): raise unittest.SkipTest('Pinned Android NDK compiler unavailable')
        root=Path(__file__).resolve().parents[1]
        actual=os.environ.get('PC_NATIVE_TEST_SHIM')
        if actual:
            cls.image=Path(actual)
        else:
            subprocess.run([str(clang),'--target=aarch64-linux-android29','-shared','-nostdlib',
                        '-O2','-fno-builtin','-ffreestanding','-fvisibility=hidden','-mno-outline-atomics',
                        '-I',str(root/'native/kneekura-shim/include'),
                        str(root/'native/kneekura-shim/src/kneekura_pc_balance.c'),
                            '-o',str(cls.image)],check=True,capture_output=True)
        cls.elf=lief.parse(str(cls.image))

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls,'temp'): cls.temp.cleanup()

    def setUp(self):
        from unicorn import arm64_const as a
        self.a=a
        self.uc=self.ucmod.Uc(self.ucmod.UC_ARCH_ARM64,self.ucmod.UC_MODE_ARM)
        self.base=0x2000000
        for seg in self.elf.segments:
            if seg.type != self.lief.ELF.Segment.TYPE.LOAD: continue
            start=(seg.virtual_address+self.base)&~4095
            end=(seg.virtual_address+self.base+seg.virtual_size+4095)&~4095
            self.uc.mem_map(start,end-start)
            self.uc.mem_write(self.base+seg.virtual_address,bytes(seg.content))
        self.entry=self.base+self.elf.get_dynamic_symbol(DISPATCH_SYMBOL).value
        for addr,size in ((0x1000000,0x4000),(0x3000000,0x4000),(0x4000000,0x400000)):
            self.uc.mem_map(addr,size)
        self.uc.reg_write(a.UC_ARM64_REG_SP,0x3003000)
        self.ctx=0x4000000

    def dispatch(self,op,values):
        regs=[0]*32
        for key,value in values.items(): regs[key]=value
        self.uc.mem_write(0x1003000,struct.pack('<32Q',*regs))
        self.uc.reg_write(self.a.UC_ARM64_REG_X0,0x1003000)
        self.uc.reg_write(self.a.UC_ARM64_REG_X1,op)
        self.uc.reg_write(self.a.UC_ARM64_REG_LR,0x1002000)
        self.uc.emu_start(self.entry,0x1002000,count=10000)
        return struct.unpack('<32Q',self.uc.mem_read(0x1003000,256))

    def spawn(self,slot=1,unit=702,form=0,side=1):
        self.dispatch(4,{20:side,19:slot,22:unit,25:form})
        at=self.ctx+0x84080+0xc804+slot*0x3ec+4
        self.uc.mem_write(at,struct.pack('<i',unit))

    def castle(self,slot=1,target=0,damage=50000):
        return self.dispatch(2,{20:self.ctx,22:slot,19:target,23:damage,2:damage})[2]

    def test_three_hits_repetition_first_miss_and_two_actors(self):
        self.spawn()
        self.spawn(2)
        self.assertEqual([self.castle() for _ in range(4)],[1,0,0,0])
        self.assertEqual(self.castle(2),1)
        self.dispatch(3,{21:1,20:1,19:0,0:self.ctx})
        self.assertEqual(self.castle(damage=0),0)
        self.assertEqual(self.castle(),1)
        self.assertEqual(self.castle(),0)

    def test_slot_reuse_enemy_and_other_forms_preserved(self):
        self.spawn(); self.assertEqual(self.castle(),1)
        self.spawn(form=1); self.assertEqual(self.castle(),50000)
        self.spawn(unit=288,form=2); self.assertEqual(self.castle(),50000)
        self.spawn(); self.assertEqual(self.castle(target=1),50000)
        self.assertEqual(self.castle(),1)
        self.dispatch(3,{21:0,20:1,19:0,0:self.ctx})
        self.assertEqual(self.castle(),0)

    def test_damage_growth_and_non_target_level_preserved(self):
        self.assertEqual(self.dispatch(1,{24:30,21:702,20:0,19:19999})[19],20000)
        for level,unit,form,value in ((31,702,0,20411),(30,702,1,1088),(30,288,2,11200)):
            self.assertEqual(self.dispatch(1,{24:level,21:unit,20:form,19:value})[19],value)

    def test_cost_frequency_and_native_research_delta(self):
        self.assertEqual(self.dispatch(5,{20:702,19:0,22:240})[22],241)
        self.assertEqual(210+241-1,450)
        self.assertEqual(self.dispatch(5,{20:702,19:1,22:92})[22],92)
        for chapter in (0,1,2):
            self.uc.mem_write(self.ctx+0x38fad8,struct.pack('<i',chapter))
            for unit,form,cost in ((288,2,454900),(702,0,979900),(702,1,66000)):
                expected=cost+100 if chapter==1 and (unit,form)!=(702,1) else cost
                self.assertEqual(self.dispatch(6,{0:self.ctx,19:unit,22:form,25:cost})[25],expected)
        for delta in (90,204,254):
            self.dispatch(8,{1:288,2:2,29:0x1111})
            self.dispatch(8,{1:702,2:1,29:0x2222})
            self.assertEqual(self.dispatch(7,{19:288,20:4904,8:delta,29:0x1111})[20]-delta,4650)
            self.assertEqual(self.dispatch(7,{19:702,20:540,8:delta,29:0x2222})[20],540)
            self.dispatch(8,{1:702,2:0,29:0x3333})
            self.assertEqual(self.dispatch(7,{19:702,20:15254,8:delta,29:0x3333})[20]-delta,15000)
        # Original talent reduction remains; missing/wrong query never changes a unit.
        self.dispatch(8,{1:288,2:2,29:0x1111})
        self.assertEqual(self.dispatch(7,{19:288,20:4884,8:90,29:0x1111})[20]-90,4630)
        self.assertEqual(self.dispatch(7,{19:288,20:4904,8:90,29:0x1111})[20],4904)

    def test_unexpected_delayed_generator_fails_closed(self):
        self.spawn()
        actor=self.ctx+0x84080+0xc804+0x3ec
        for field in (0x9c,0x2b8,0x380):
            self.uc.mem_write(actor+field,struct.pack('<i',1))
            self.assertEqual(self.castle(),0)
            self.uc.mem_write(actor+field,struct.pack('<i',0))
        self.assertEqual(self.castle(),1)

    def test_real_trampoline_preserves_registers_vectors_flags_and_stack(self):
        # Base-damage adapter alone requires no proprietary memory.
        site=SITES[0]
        code=make_stub(0x1000000,0x1002000,0x1000,site)
        self.uc.mem_write(0x1000000,code)
        self.uc.mem_write(0x1002000,struct.pack('<Q',self.entry))
        # Redirect the two original continuations to stop addresses in mapped test code.
        from tools.base_mod.pc_native_balance import branch
        end=0x1000000+len(code)-12
        self.uc.mem_write(end+4,struct.pack('<I',branch(end+4,0x1002100)))
        self.uc.mem_write(end+8,struct.pack('<I',branch(end+8,0x1002100)))
        initial={i:0x550000+i for i in range(31)}
        initial.update({24:30,21:702,20:0,19:19999})
        for i,v in initial.items(): self.uc.reg_write(getattr(self.a,'UC_ARM64_REG_X'+str(i)),v)
        for i in range(32): self.uc.reg_write(getattr(self.a,'UC_ARM64_REG_Q'+str(i)),(i+1)<<96|0xabcdef)
        self.uc.reg_write(self.a.UC_ARM64_REG_NZCV,0xa0000000)
        self.uc.emu_start(0x1000000,0x1002100,count=10000)
        for i,v in initial.items():
            self.assertEqual(self.uc.reg_read(getattr(self.a,'UC_ARM64_REG_X'+str(i))),20000 if i==19 else v)
        for i in range(32):
            self.assertEqual(self.uc.reg_read(getattr(self.a,'UC_ARM64_REG_Q'+str(i))),(i+1)<<96|0xabcdef)
        self.assertEqual(self.uc.reg_read(self.a.UC_ARM64_REG_NZCV),0xa0000000)
        self.assertEqual(self.uc.reg_read(self.a.UC_ARM64_REG_SP),0x3003000)

    def test_every_remaining_adapter_preserves_abi_and_displaced_instruction(self):
        from tools.base_mod.pc_native_balance import branch
        for site in SITES[1:]:
            op=site[0]
            with self.subTest(operation=op):
                self.spawn()
                initial={i:0x550000+i for i in range(31)}
                expected={}
                if op==2:
                    initial.update({0:0,1:0,2:50000,19:0,20:self.ctx,22:1,23:50000})
                    expected[2]=1
                elif op==3:
                    initial.update({0:self.ctx,8:self.ctx+0x200,9:8,19:0,20:1,21:1})
                    self.uc.mem_write(self.ctx+0x208,struct.pack('<I',123))
                elif op==4: initial.update({19:1,20:1,22:702,25:0})
                elif op==5:
                    initial.update({8:self.ctx+0x300,9:0,19:0,20:702})
                    self.uc.mem_write(self.ctx+0x300,struct.pack('<I',240))
                    expected[22]=241
                elif op==6:
                    initial.update({0:self.ctx,8:4549,9:100,19:288,22:2})
                    self.uc.mem_write(self.ctx+0x38fad8,struct.pack('<i',1))
                    expected[25]=455000
                elif op==7:
                    initial.update({19:288,20:4904,21:0,22:90,23:6,29:0x1111})
                    self.dispatch(8,{1:288,2:2,29:0x1111})
                    expected.update({8:90,20:4740})
                elif op==8: initial.update({1:702,2:0,29:0x2222})
                if op in (2,4,8): initial[30]=site[1]+0x1000+4
                code=make_stub(0x1000000,0x1002000,0x1000,site)
                self.uc.mem_write(0x1000000,code)
                self.uc.mem_write(0x1000000+len(code)-4,
                                  struct.pack('<I',branch(0x1000000+len(code)-4,0x1002100)))
                self.uc.mem_write(0x1002000,struct.pack('<Q',self.entry))
                for i,v in initial.items(): self.uc.reg_write(getattr(self.a,'UC_ARM64_REG_X'+str(i)),v)
                for i in range(32): self.uc.reg_write(getattr(self.a,'UC_ARM64_REG_Q'+str(i)),(i+1)<<96|0xabcdef)
                self.uc.reg_write(self.a.UC_ARM64_REG_NZCV,0xb0000000)
                self.uc.ctl_remove_cache(0x1000000,0x1001000)
                self.uc.emu_start(0x1000000,0x1002100,count=10000)
                for i,v in initial.items():
                    self.assertEqual(self.uc.reg_read(getattr(self.a,'UC_ARM64_REG_X'+str(i))),expected.get(i,v))
                for i in range(32):
                    self.assertEqual(self.uc.reg_read(getattr(self.a,'UC_ARM64_REG_Q'+str(i))),(i+1)<<96|0xabcdef)
                self.assertEqual(self.uc.reg_read(self.a.UC_ARM64_REG_NZCV),0xb0000000)
                self.assertEqual(self.uc.reg_read(self.a.UC_ARM64_REG_SP),0x3003000)
                if op==3: self.assertEqual(struct.unpack('<I',self.uc.mem_read(self.ctx+0x208,4))[0],0)


class PrivateElfGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture=os.environ.get('PC_NATIVE_TEST_IMAGE')
        if not fixture: raise unittest.SkipTest('Owner private native adapter fixture required')
        import lief
        cls.lief=lief
        cls.data=Path(fixture).read_bytes()
        cls.elf=lief.parse(list(cls.data))

    def test_loader_import_attributes_and_overlap_cannot_bypass_gate(self):
        from tools.base_mod.pc_native_balance import verify_and_restore,RW_MARKER
        verify_and_restore(self.data)
        symbols=list(self.elf.dynamic_symbols)
        index=next(i for i,s in enumerate(symbols) if s.name==DISPATCH_SYMBOL)
        at=self.elf.get_section('.dynsym').offset+index*24
        for offset,value in ((4,b'\x02'),(5,b'\x02'),(6,struct.pack('<H',1)),(8,struct.pack('<Q',0x31855c))):
            with self.subTest(offset=offset):
                candidate=bytearray(self.data); candidate[at+offset:at+offset+len(value)]=value
                with self.assertRaisesRegex(ValueError,'PC_BALANCE_DISPATCH_IMPORT_CHANGED'):
                    verify_and_restore(bytes(candidate))
        rw=next(s for s in self.elf.segments if bytes(s.content).startswith(RW_MARKER))
        got=rw.virtual_address+64
        rela=self.elf.get_section('.rela.dyn')
        candidate=bytearray(self.data)
        # Relocate a different existing record onto the second half of the GOT.
        for pos in range(rela.offset,rela.offset+rela.size,24):
            if struct.unpack_from('<Q',candidate,pos)[0]!=got:
                struct.pack_into('<Q',candidate,pos,got+4); break
        with self.assertRaisesRegex(ValueError,'PC_BALANCE_DISPATCH_RELOCATION_CHANGED'):
            verify_and_restore(bytes(candidate))

    def test_opt_in_and_any_unapproved_executable_change_are_rejected(self):
        from tools.base_mod.original_scene_native_image_gate import verify_mapped_original_scene_image
        from tools.base_mod.pc_native_balance import RX_MARKER
        arguments={'expected_research_native_package':'jp.kn.local.battlecats'}
        with self.assertRaisesRegex(ValueError,'executable .text SHA256 drift'):
            verify_mapped_original_scene_image(self.data,**arguments)
        proof=verify_mapped_original_scene_image(self.data,pc_balance_enabled=True,**arguments)
        self.assertFalse(proof['all_original_executable_text_bytes_unchanged_static'])
        rx=next(s for s in self.elf.segments if bytes(s.content).startswith(RX_MARKER))
        for at in (rx.file_offset+100,self.elf.virtual_address_to_offset(0x317600+0x2000)):
            candidate=bytearray(self.data); candidate[at]^=1
            with self.assertRaises(ValueError):
                verify_mapped_original_scene_image(bytes(candidate),pc_balance_enabled=True,**arguments)


if __name__=='__main__': unittest.main()
