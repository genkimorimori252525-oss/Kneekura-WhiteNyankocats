from pathlib import Path
import tempfile
import unittest
from tools.base_mod.pc_balance_assets import load_pinned_assets
from tools.base_mod.verify_static_http_bridge import verify_static_http_bridge


class PcBalanceAssetTests(unittest.TestCase):
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
