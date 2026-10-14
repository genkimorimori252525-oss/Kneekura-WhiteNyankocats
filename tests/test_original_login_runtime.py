"""Execute actual Java assignment logic and ARM64 read-only map lookup."""
from pathlib import Path
import os
import shutil
import struct
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class OriginalLoginJavaTests(unittest.TestCase):
    def test_five_original_receipts_restart_refill_rollback_and_bad_snapshot(self):
        javac=shutil.which('javac')
        if javac is None:
            candidate=Path(r'C:\Program Files\Java\jdk-17\bin\javac.exe')
            if candidate.exists():javac=str(candidate)
        if javac is None:raise unittest.SkipTest('Java compiler unavailable')
        java=str(Path(javac).with_name('java.exe' if os.name=='nt' else 'java'))
        source=(ROOT/'bridge/java/KneekuraLoginRotation.java.in').read_text(encoding='utf-8')
        harness=r'''
package test.ops;
import java.util.HashMap;
public final class LoginAcceptance {
  static void check(boolean value) { if(!value)throw new AssertionError(); }
  public static void main(String[] args) {
    HashMap<Integer,Integer> pool=new HashMap<>();
    for(int id=949;id<=954;id++)pool.put(id,6);
    KneekuraLoginRotation r=new KneekuraLoginRotation(pool,new int[][]{
      {949,950,951,952,953,954},{954,953,952,951,950,949},{949,950,951,952,953,954}});
    KneekuraLoginRotation.State initial=r.initial(100);
    check(initial.active.size()==5 && initial.sequence==5);
    KneekuraLoginRotation.State offered=r.prepare(initial,100,new int[5]);
    check(initial.highDay==-1 && offered.highDay==100);
    check(r.offered(offered,offered.active.get(0),100));
    // HTTP offers do not advance stamp counts, complete or replace campaigns.
    KneekuraLoginRotation.State repeat=r.prepare(offered,100,new int[5]);
    check(repeat.active.get(0).observedCount==0 && repeat.sequence==5);
    // An actual original receipt updates observed counts; no synthetic grant.
    KneekuraLoginRotation.State received=r.prepare(repeat,100,new int[]{1,1,1,1,1});
    check(received.active.get(0).observedCount==1 && received.sequence==5);
    KneekuraLoginRotation.State back=r.prepare(received,99,new int[]{1,1,1,1,1});
    check(!r.offered(back,back.active.get(0),99) && back.highDay==100);
    KneekuraLoginRotation.State jump=r.prepare(back,110,new int[]{1,1,1,1,1});
    check(jump.active.get(0).observedCount==1 && jump.highDay==110);
    KneekuraLoginRotation.State complete=r.prepare(jump,110,new int[]{6,1,1,1,1});
    check(complete.sequence==5 && !r.offered(complete,complete.active.get(0),110));
    // Simulate cold reload of exactly the serialized state: identity/counters persist.
    KneekuraLoginRotation.State reloaded=complete.copy();
    KneekuraLoginRotation.State refill=r.prepare(reloaded,111,new int[]{6,1,1,1,1});
    check(refill.active.size()==5 && refill.sequence==6);
    check(refill.active.get(4).template==954 && refill.active.get(4).eventKey==700006);
    // Unflushed crash rollback restores observedCount to authoritative SAVE count
    KneekuraLoginRotation.State rolledBack=r.prepare(received,101,new int[5]);
    check(rolledBack.active.get(0).observedCount==0);
    // Query keys include active slots and bounded history slots
    int[] qKeys=r.queryKeys(refill);
    check(qKeys.length==6 && qKeys[0]==700001 && qKeys[5]==700006);
    // Unflushed crash resurrects retired slot if original count was less than days
    int[] rollCounts=new int[]{5,1,1,1,1,1};
    KneekuraLoginRotation.State resurrected=r.prepare(refill,112,rollCounts);
    check(resurrected.active.get(0).eventKey==700001 && resurrected.active.get(0).observedCount==5);
    // A rollback must preserve the descendant assignment, even if it already
    // has an original receipt. Restoring a predecessor must never discard it.
    boolean descendant=false;
    for(int key:r.queryKeys(resurrected)) if(key==700006)descendant=true;
    check(descendant);
    // Once the predecessor is completed and the day changes, reuse the exact
    // original descendant key and its existing receipt, never issue a new key.
    KneekuraLoginRotation.State oldDone=r.prepare(resurrected,112,new int[]{6,1,1,1,1,1});
    KneekuraLoginRotation.State descendantAgain=r.prepare(oldDone.copy(),113,new int[]{6,1,1,1,1,1});
    check(descendantAgain.sequence==6 && descendantAgain.active.get(4).eventKey==700006
        && descendantAgain.active.get(4).observedCount==1);
    boolean missingCounts=false;
    try {r.prepare(refill,112,new int[5]);} catch(IllegalArgumentException e){missingCounts=true;}
    check(missingCounts);
    // Cold reload can roll back farther than five historical assignments.
    KneekuraLoginRotation.State older=offered.copy();older.sequence=11;
    for(int key=700006;key<=700011;key++) {
      KneekuraLoginRotation.Slot h=new KneekuraLoginRotation.Slot(954,key,6,100);
      h.offeredDay=100;h.observedCount=6;older.history.add(h);
    }
    int[] full=new int[11];java.util.Arrays.fill(full,6);full[0]=2;
    KneekuraLoginRotation.State recovered=r.prepare(older.copy(),114,full);
    check(recovered.active.get(0).eventKey==700001 && r.queryKeys(recovered).length>=11);
    boolean rejected=false;
    try {r.prepare(offered,100,new int[]{-1,0,0,0,0});} catch(IllegalStateException e){rejected=true;}
    check(rejected);
    rejected=false;
    try {r.prepare(offered,100,new int[]{7,0,0,0,0});} catch(IllegalStateException e){rejected=true;}
    check(rejected);
    rejected=false;
    try {r.prepare(initial,100,new int[]{1,0,0,0,0});} catch(IllegalStateException e){rejected=true;}
    check(rejected);
    System.out.println("PASS_ORIGINAL_LOGIN_ASSIGNMENTS_ONLY_NOT_GAMEPLAY");
  }
}
'''
        with tempfile.TemporaryDirectory() as directory:
            temp=Path(directory);path=temp/'test/ops';path.mkdir(parents=True)
            (path/'KneekuraLoginRotation.java').write_text(source.replace('__KNEEKURA_PACKAGE__','test.ops'),encoding='utf-8')
            (path/'LoginAcceptance.java').write_text(harness,encoding='utf-8')
            subprocess.run([javac,'-encoding','UTF-8','-d',str(temp),
                str(path/'KneekuraLoginRotation.java'),str(path/'LoginAcceptance.java')],check=True,capture_output=True)
            result=subprocess.run([java,'-cp',str(temp),'test.ops.LoginAcceptance'],check=False,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('PASS_ORIGINAL_LOGIN_ASSIGNMENTS_ONLY_NOT_GAMEPLAY',result.stdout)


class OriginalLoginArm64Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import lief, unicorn
        except ImportError:raise unittest.SkipTest('Private native-test-venv with unicorn/lief required')
        cls.lief,cls.unicorn=lief,unicorn
        clang=Path(os.environ.get('LOCALAPPDATA',''))/'Android/Sdk/ndk/27.2.12479018/toolchains/llvm/prebuilt/windows-x86_64/bin/clang.exe'
        if not clang.exists():raise unittest.SkipTest('Pinned Android NDK unavailable')
        cls.temp=tempfile.TemporaryDirectory();temp=Path(cls.temp.name)
        source=temp/'probe.c';binary=temp/'probe.so'
        source.write_text(r'''
#include "kneekura_original_ops_login.h"
void *memcpy(void *out,const void *in,size_t n) {
  for(size_t i=0;i<n;i++)((unsigned char*)out)[i]=((const unsigned char*)in)[i];return out;
}
static int reader(uintptr_t address,void *out,size_t length) {
  if(address<0x4000000 || address>0x4004000-length)return 0;
  memcpy(out,(const void*)address,length);return 1;
}
__attribute__((visibility("default"))) int probe(uintptr_t root,uint64_t size,int32_t key,int32_t *out) {
  return kneekura_original_login_count(root,size,key,reader,out);
}
__attribute__((visibility("default"))) int probe_many(uintptr_t root,uint64_t size,int32_t mode,int32_t *out) {
  int32_t keys[5]={700001,700002,700003,700004,700006};
  if(mode==1)keys[1]=keys[0];
  if(mode==2)keys[4]=704097;
  return kneekura_original_login_counts(root,size,keys,5,reader,out);
}
__attribute__((visibility("default"))) int probe_gl(uintptr_t isolated,uint64_t hooks,int32_t mode,int32_t *out) {
  *out=kneekura_original_ops_gl_state((int)isolated,(mode&4)==0,(uint32_t)hooks,
      (mode&2)?2u:0u,(mode&8)?0:100,(mode&1)?101:100);
  return 1;
}
''',encoding='utf-8')
        subprocess.run([str(clang),'--target=aarch64-linux-android29','-shared','-nostdlib','-O2',
            '-ffreestanding','-fno-builtin','-fvisibility=hidden','-fno-stack-protector','-I',str(ROOT/'native/kneekura-shim/src'),
            str(source),'-o',str(binary)],check=True,capture_output=True)
        cls.elf=lief.parse(str(binary))

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls,'temp'):cls.temp.cleanup()

    def lookup(self,root,size,key,nodes,probe='probe'):
        from unicorn import arm64_const as a
        uc=self.unicorn.Uc(self.unicorn.UC_ARCH_ARM64,self.unicorn.UC_MODE_ARM)
        base=0x2000000
        for segment in self.elf.segments:
            if segment.type!=self.lief.ELF.Segment.TYPE.LOAD:continue
            begin=(base+segment.virtual_address)&~4095
            end=(base+segment.virtual_address+segment.virtual_size+4095)&~4095
            uc.mem_map(begin,end-begin);uc.mem_write(base+segment.virtual_address,bytes(segment.content))
        for address in (0x1000000,0x3000000,0x4000000):uc.mem_map(address,0x4000)
        for address,value in nodes.items():uc.mem_write(address,value)
        before=bytes(uc.mem_read(0x4000000,0x4000))
        uc.reg_write(a.UC_ARM64_REG_SP,0x3003000);uc.reg_write(a.UC_ARM64_REG_LR,0x1002000)
        for register,value in [(a.UC_ARM64_REG_X0,root),(a.UC_ARM64_REG_X1,size),
                (a.UC_ARM64_REG_X2,key),(a.UC_ARM64_REG_X3,0x1003000)]:uc.reg_write(register,value)
        uc.emu_start(base+self.elf.get_dynamic_symbol(probe).value,0x1002000,count=100000)
        self.assertEqual(bytes(uc.mem_read(0x4000000,0x4000)),before)
        count=5 if probe=='probe_many' else 1
        values=struct.unpack('<'+'i'*count,uc.mem_read(0x1003000,4*count))
        return uc.reg_read(a.UC_ARM64_REG_X0),values if count>1 else values[0]

    def test_one_snapshot_covers_all_history_and_rejects_partial_or_unordered_trees(self):
        nodes={0x4000000:self.node(700002,2,0x4000100,0x4000200),
               0x4000100:self.node(700001,6),0x4000200:self.node(700006,1)}
        self.assertEqual(self.lookup(0x4000000,3,0,nodes,'probe_many'),(1,(6,2,0,0,1)))
        self.assertEqual(self.lookup(0,0,0,{},'probe_many'),(1,(0,0,0,0,0)))
        for mode in (1,2):
            self.assertEqual(self.lookup(0x4000000,3,mode,nodes,'probe_many')[0],0)
        for size in (1,2,4):
            self.assertEqual(self.lookup(0x4000000,size,0,nodes,'probe_many')[0],0)
        bad={0x4000000:self.node(700002,2,0x4000100),0x4000100:self.node(700003,1)}
        self.assertEqual(self.lookup(0x4000000,2,0,bad,'probe_many')[0],0)

    @staticmethod
    def node(key,count,left=0,right=0):
        return struct.pack('<QQQiii4x',left,right,0,0,key,count)

    def test_reads_original_node_layout_without_mutation(self):
        nodes={0x4000000:self.node(700002,2,0x4000100,0x4000200),
               0x4000100:self.node(700001,6),0x4000200:self.node(700003,0)}
        for key,count in [(700001,6),(700002,2),(700003,0),(700004,0)]:
            with self.subTest(key=key):self.assertEqual(self.lookup(0x4000000,3,key,nodes),(1,count))

    def test_gl_readiness_accepts_complete_phone_hooks_and_pc_jni_only_on_attested_thread(self):
        cases=[(1,1,0,1),(1,1,1,0),(1,0,2,1),(1,0,3,0),
               (1,0,0,-1),(1,2,0,-1),(0,1,0,-1),(1,1,4,-1),(1,1,8,-1)]
        for isolated,hooks,mode,state in cases:
            with self.subTest(isolated=isolated,hooks=hooks,mode=mode):
                self.assertEqual(self.lookup(isolated,hooks,mode,{},'probe_gl'),(1,state))

    def test_corrupt_tree_count_pointer_cycle_and_foreign_key_fail_closed(self):
        cases=[(0x4000000,0,700001,{}),(0,1,700001,{}),(0,4097,700001,{}),
               (0x9000000,1,700001,{}),(0,0,42,{}),
               (0x4000000,1,700001,{0x4000000:self.node(700002,0,left=0x4000000)}),
               (0x4000000,1,700001,{0x4000000:self.node(700001,-1)})]
        for case in cases:
            with self.subTest(case=case[:3]):self.assertEqual(self.lookup(*case)[0],0)


if __name__=='__main__':unittest.main()
