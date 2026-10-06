from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class AndroidStageContractTests(unittest.TestCase):
    def test_importer_reads_maplocal_and_major_stage_families(self) -> None:
        source = (
            ROOT / "app/src/main/java/jp/kneekura/whitenyankocats/BattleCatsImporter.java"
        ).read_text(encoding="utf-8")

        self.assertIn("assets/MapLocal.list", source)
        self.assertIn("StageName_RN_ja.csv", source)
        self.assertIn('case "RN"', source)
        self.assertIn('case "RS"', source)
        self.assertIn('case "RC"', source)
        self.assertIn('case "RNA"', source)
        self.assertIn('case "RND"', source)
        self.assertIn("spawnBasePercent", source)
        self.assertIn("magnification", source)

    def test_battle_core_uses_30fps_and_base_win_loss(self) -> None:
        source = (
            ROOT / "app/src/main/java/jp/kneekura/whitenyankocats/BattleActivity.java"
        ).read_text(encoding="utf-8")

        self.assertIn("FPS = 30", source)
        self.assertIn("enemyBaseHp <= 0", source)
        self.assertIn("playerBaseHp <= 0", source)
        self.assertIn("spawn.spawnBasePercent", source)
        self.assertIn("spawn.magnification", source)

    def test_manifest_remains_offline(self) -> None:
        manifest = (ROOT / "app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
        self.assertNotIn("android.permission.INTERNET", manifest)
        self.assertIn('android:name=".BattleActivity"', manifest)


if __name__ == "__main__":
    unittest.main()