from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class AndroidAlphaContractTests(unittest.TestCase):
    def test_manifest_is_offline_and_independent(self) -> None:
        manifest = (ROOT / "app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
        build = (ROOT / "app/build.gradle.kts").read_text(encoding="utf-8")

        self.assertNotIn("android.permission.INTERNET", manifest)
        self.assertIn('usesCleartextTraffic="false"', manifest)
        self.assertIn('applicationId = "jp.kneekura.whitenyankocats"', build)
        self.assertNotIn("jp.co.ponos.battlecats", build)

    def test_importer_is_local_export_only(self) -> None:
        source = (
            ROOT / "app/src/main/java/jp/kneekura/whitenyankocats/BattleCatsImporter.java"
        ).read_text(encoding="utf-8")

        self.assertIn("split_installpack.apk", source)
        self.assertIn("assets/DataLocal.list", source)
        self.assertIn("assets/resLocal.list", source)
        self.assertNotIn("http://", source)
        self.assertNotIn("https://", source)

    def test_max_profile_contract_is_explicit(self) -> None:
        source = (
            ROOT / "app/src/main/java/jp/kneekura/whitenyankocats/ProfileStore.java"
        ).read_text(encoding="utf-8")

        self.assertIn("MAX_VALUE = 999_999_999L", source)
        self.assertIn('"all_units_unlocked"', source)
        self.assertIn('"resource_mode_max"', source)
        self.assertIn('"cat_food"', source)
        self.assertIn('"xp"', source)
        self.assertIn('"np"', source)
        self.assertIn('"evolution_material"', source)


if __name__ == "__main__":
    unittest.main()