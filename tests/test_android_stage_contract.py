from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class AndroidStageContractTests(unittest.TestCase):
    def test_importer_reads_stage_data_from_datalocal_and_major_families(self) -> None:
        importer = (
            ROOT / "app/src/main/java/jp/kneekura/whitenyankocats/BattleCatsImporter.java"
        ).read_text(encoding="utf-8")
        spawn = (
            ROOT / "app/src/main/java/jp/kneekura/whitenyankocats/EnemySpawn.java"
        ).read_text(encoding="utf-8")

        self.assertIn("assets/DataLocal.list", importer)
        self.assertIn("assets/MapLocal.list", importer)
        self.assertIn("for (String fileName : data.names())", importer)
        self.assertIn("enemyReleaseId < 2", importer)
        self.assertIn('data.has("Map_option.csv")', importer)
        self.assertIn('row.get(19)', importer)
        self.assertIn("Z_STAGE", importer)
        self.assertIn('return 1000 + address.mapIndex', importer)
        self.assertIn('return 2000 + address.mapIndex', importer)
        self.assertIn('"StageName_" + stageNameCode + "_ja.csv"', importer)
        self.assertIn('case "RN"', importer)
        self.assertIn('case "RS"', importer)
        self.assertIn('case "RC"', importer)
        self.assertIn('case "RNA"', importer)
        self.assertIn('case "RND"', importer)
        self.assertIn("intAt(row, 5, 100)", importer)
        self.assertIn("intAt(row, 9, 100)", importer)
        self.assertIn("spawnBasePercent", spawn)
        self.assertIn("magnification", spawn)

    def test_battle_core_uses_30fps_base_win_loss_and_zero_count_is_unlimited(self) -> None:
        source = (
            ROOT / "app/src/main/java/jp/kneekura/whitenyankocats/BattleActivity.java"
        ).read_text(encoding="utf-8")

        self.assertIn("FPS = 30", source)
        self.assertIn("enemyBaseHp <= 0", source)
        self.assertIn("playerBaseHp <= 0", source)
        self.assertIn("spawn.spawnBasePercent", source)
        self.assertIn("spawn.magnification", source)
        self.assertIn("spawn.maxEnemyCount <= 0", source)
        self.assertIn('allCats.setText("全キャラ")', source)

    def test_manifest_remains_offline(self) -> None:
        manifest = (ROOT / "app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
        self.assertNotIn("android.permission.INTERNET", manifest)
        self.assertIn('android:name=".BattleActivity"', manifest)


if __name__ == "__main__":
    unittest.main()