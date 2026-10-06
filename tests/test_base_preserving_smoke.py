from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.base_mod.extract_owned_splits import EXPECTED_SPLITS
from tools.base_mod.verify_parity import _split_diff


ROOT = Path(__file__).resolve().parents[1]


class BootSmokeContractTests(unittest.TestCase):
    def test_exact_split_contract_contains_installpack(self) -> None:
        self.assertEqual(len(EXPECTED_SPLITS), 6)
        self.assertEqual(
            EXPECTED_SPLITS["split_InstallPack.apk"]["size"],
            132290560,
        )

    def test_diff_ignores_signatures_but_detects_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            before = root / "before.apk"
            signed = root / "signed.apk"

            with zipfile.ZipFile(before, "w") as z:
                z.writestr("AndroidManifest.xml", b"old")
                z.writestr("assets/game.csv", b"same")
                z.writestr("META-INF/OLD.RSA", b"old signature")

            with zipfile.ZipFile(signed, "w") as z:
                z.writestr("AndroidManifest.xml", b"new")
                z.writestr("assets/game.csv", b"same")
                z.writestr("META-INF/NEW.RSA", b"new signature")

            diff = _split_diff(before, signed)
            self.assertEqual(diff["changed"], ["AndroidManifest.xml"])
            self.assertEqual(diff["added"], [])
            self.assertEqual(diff["removed"], [])

    def test_product_workflow_does_not_reference_harness_activity(self) -> None:
        workflow = (
            ROOT / ".github/workflows/build-base-preserving-smoke.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("jp.co.ponos.battlecats.MyActivity", workflow)
        self.assertNotIn("jp.kneekura.whitenyankocats.MainActivity", workflow)


if __name__ == "__main__":
    unittest.main()