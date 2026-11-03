from pathlib import Path
import math
import subprocess
import sys
import tempfile
import unittest
from tools.base_mod.pc_balance_assets import load_pinned_assets
from tools.base_mod.verify_static_http_bridge import verify_static_http_bridge


class PcBalanceAssetTests(unittest.TestCase):
    def test_metadata_and_source_rejection_do_not_require_image_dependency(self):
        code='''
import builtins
from pathlib import Path
import tempfile
original_import=builtins.__import__
def without_pillow(name,*args,**kwargs):
    if name=='PIL' or name.startswith('PIL.'):
        raise ModuleNotFoundError('Pillow deliberately unavailable')
    return original_import(name,*args,**kwargs)
builtins.__import__=without_pillow
from tools.base_mod.pc_balance_assets import PAYLOAD_SHA256
from tools.base_mod.godzilla_portrait import prepare_portraits
assert 'uni702_f00.png' in PAYLOAD_SHA256
with tempfile.TemporaryDirectory() as folder:
    source=Path(folder)/'unapproved.png'
    source.write_bytes(b'unapproved')
    try:
        prepare_portraits(source,Path(folder)/'missing-packs')
    except ValueError as error:
        assert str(error)=='PC_GODZILLA_PORTRAIT_SOURCE_CHANGED'
    else:
        raise AssertionError('unapproved source accepted')
'''
        result=subprocess.run([sys.executable,'-B','-c',code],
                              cwd=Path(__file__).resolve().parents[1],
                              capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_portrait_import_rejects_unapproved_source_before_pack_access(self):
        from tools.base_mod.godzilla_portrait import prepare_portraits, PORTRAIT_SHA256
        self.assertEqual(set(PORTRAIT_SHA256), {
            'uni702_f00.png', 'udi702_f.png', 'gatyachara_702_f.png'})
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'owner-source.png'
            source.write_bytes(b'unapproved image')
            with self.assertRaisesRegex(ValueError,'PORTRAIT_SOURCE_CHANGED'):
                prepare_portraits(source,Path(folder)/'no-server-packs')

    def test_allied_hitpoint_selector_can_read_both_configurations(self):
        from tools.base_mod import pc_balance_assets as assets
        from tools.base_mod.prepare_godzilla_ally_preview import preview_converted_ally_rig
        from tests.test_prepare_godzilla_ally_preview import rig
        model=preview_converted_ally_rig(rig())[0]['702_f.mamodel']
        ensure=assets.ensure_godzilla_ally_anchors
        result=ensure(model).splitlines()
        nodes=int(result[2]);self.assertEqual(int(result[4+nodes]),2)
        # Native selector is flags & 1; the second configuration must exist.
        self.assertEqual(result[5+nodes],model.splitlines()[5+nodes])
        self.assertEqual(result[6+nodes].split(b',')[:6],[b'0',b'0',b'0',b'0',b'5',b'0'])
        self.assertEqual(result[:4+nodes],model.splitlines()[:4+nodes])
        with self.assertRaisesRegex(ValueError,'ANCHOR_LAYOUT_CHANGED'):
            ensure(ensure(model))
        with self.assertRaisesRegex(ValueError,'ROOT_ANCHOR_CHANGED'):
            ensure(model.replace(b'0,0,-48,350,10,0,collision',b'1,0,-48,350,10,0,collision'))

    def test_mirrored_rotated_sprite_matches_reflection_at_every_frame(self):
        from tools.base_mod import pc_balance_assets as assets
        from tools.base_mod.prepare_godzilla_ally_preview import preview_converted_ally_rig
        from tests.test_prepare_godzilla_ally_preview import rig
        source=rig()
        source['550_e.mamodel']=source['550_e.mamodel'].replace(
            b'-1000,1000,0,1000,0,Null',b'1000,1000,0,1000,0,Null').replace(
            b'1000,1000,0,1000,0,Head',b'1000,1000,450,1000,0,Head')
        source['550_e00.maanim']=source['550_e00.maanim'].replace(
            b'1,11,-1,0,0,Attack\r\n1\r\n0,0,0,0',
            b'1,11,-1,0,0,Attack\r\n2\r\n0,120,0,0\r\n10,-80,0,0')
        candidate,_=preview_converted_ally_rig(source)
        reflect=assets.reflect_godzilla_rotations
        model=reflect('702_f.mamodel',candidate['702_f.mamodel'])
        animation=reflect('702_f00.maanim',candidate['702_f00.maanim'])
        angle=int(model.splitlines()[4].split(b',')[10])
        self.assertIn(b'0,-120,0,0',animation)
        self.assertIn(b'10,80,0,0',animation)
        # The renderer inherits signed size separately from accumulated rotation.
        # A root-scale-only change produces R(a) M(x), rather than M(x) R(a).
        for frame in range(11):
            original_angle=450+120-20*frame
            mirrored_angle=angle-120+20*frame
            a=original_angle*math.tau/3600
            b=mirrored_angle*math.tau/3600
            x,y=7,3
            expected=(-(math.cos(a)*x-math.sin(a)*y),math.sin(a)*x+math.cos(a)*y)
            actual=(math.cos(b)*-x-math.sin(b)*y,math.sin(b)*-x+math.cos(b)*y)
            self.assertAlmostEqual(actual[0],expected[0],places=10)
            self.assertAlmostEqual(actual[1],expected[1],places=10)
        self.assertEqual(reflect('702_f.png',candidate['702_f.png']),candidate['702_f.png'])
        self.assertEqual(reflect('702_f.imgcut',candidate['702_f.imgcut']),candidate['702_f.imgcut'])
        self.assertIn(b'1,5,-1,0,0,Move\r\n2\r\n0,0,0,0\r\n10,100,0,0',animation)
        self.assertTrue(model.endswith(b'0,0,-48,350,10,0,collision\r\n'))

    def test_unknown_or_tampered_payload_cannot_be_installed(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'unit704.csv').write_bytes(b'forbidden second-form mutation')
            with self.assertRaisesRegex(ValueError,'PC_BALANCE_ASSET_SET_CHANGED'):
                load_pinned_assets(root)
            (root/'unit704.csv').unlink()
            from tools.base_mod.pc_balance_assets import PAYLOAD_SHA256
            for name in PAYLOAD_SHA256: (root/name).write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError,'PC_BALANCE_PAYLOAD_SHA_CHANGED'):
                load_pinned_assets(root)

    def test_balance_gate_requires_separate_pc_trust_opt_in(self):
        with self.assertRaisesRegex(ValueError,'PC_BALANCE_REQUIRES_INDEPENDENT_PC_TRUST'):
            verify_static_http_bridge(Path('unused'),Path('unused'),flavor='local-research',
                                      replay_enabled=False,research_deny_internet=True,
                                      pc_balance_assets_enabled=True)


if __name__=='__main__': unittest.main()
