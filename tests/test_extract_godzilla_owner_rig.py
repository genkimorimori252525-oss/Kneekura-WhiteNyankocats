import hashlib
import tempfile
import unittest
from pathlib import Path
from tools.base_mod.extract_godzilla_owner_rig import (
    PNG_FILE, ANIM_FILES, stage_owner_rig, export_owner_rig,
)


class FakePack:
    def __init__(self, items): self.items = items
    def has(self, name): return name in self.items
    def read(self, name): return self.items[name], None


class OwnerGodzillaRigTests(unittest.TestCase):
    def setUp(self):
        self.image = b"\x89PNG\r\n\x1a\n" + b"dummy-owner-asset"
        self.png = FakePack({PNG_FILE: self.image})
        self.anim = FakePack({n: (n + "\n").encode() for n in ANIM_FILES})

    def test_exact_seven_owner_assets_and_receipt(self):
        assets = stage_owner_rig(self.png, self.anim)
        self.assertEqual(len(assets), 7)
        with tempfile.TemporaryDirectory() as t:
            dest = Path(t) / "owner-art"
            report = export_owner_rig(self.png, self.anim, dest, source_fingerprints={})
            self.assertEqual(report["target_stem"], "702_f")
            self.assertFalse(report["ready_to_install"])
            self.assertEqual(set(dest.iterdir()),
                             {dest/"rig-receipt.json", *(dest/n for n in assets)})
            self.assertEqual(report["art"][PNG_FILE]["sha256"],
                             hashlib.sha256(self.image).hexdigest())
            with self.assertRaises(ValueError):
                export_owner_rig(self.png, self.anim, dest, source_fingerprints={})

    def test_missing_and_invalid_png_fail_without_writing(self):
        with tempfile.TemporaryDirectory() as t:
            dest = Path(t) / "not-created"
            bad = FakePack({n: self.anim.items[n] for n in ANIM_FILES
                            if n != "550_e03.maanim"})
            with self.assertRaisesRegex(ValueError, "missing"):
                export_owner_rig(self.png, bad, dest, source_fingerprints={})
            self.assertFalse(dest.exists())
            with self.assertRaisesRegex(ValueError, "not PNG"):
                stage_owner_rig(FakePack({PNG_FILE: b"broken"}), self.anim)


if __name__ == "__main__":
    unittest.main()