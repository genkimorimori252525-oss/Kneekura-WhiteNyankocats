"""Contract regression tests for the offline base's i-button news.

Real Android Java compilation and INTERNET-permission audit are separately
verified by GitHub Actions android-debug workflow. These tests only prove the
checked-in editorial/source contracts; they do not simulate a touch interaction.
"""
from datetime import datetime
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / "app/src/main/assets/kneekura-notices-bootstrap.json"
DRAFT = ROOT / "ops/seasons/2026-autumn-prototype.json"
MAIN = ROOT / "app/src/main/java/jp/kneekura/whitenyankocats/MainActivity.java"
NOTICE_UI = ROOT / "app/src/main/java/jp/kneekura/whitenyankocats/NoticeActivity.java"
REPO = ROOT / "app/src/main/java/jp/kneekura/whitenyankocats/LocalNoticeRepository.java"
STORE = ROOT / "app/src/main/java/jp/kneekura/whitenyankocats/LocalOpsStore.java"
MANIFEST = ROOT / "app/src/main/AndroidManifest.xml"


class OfflineBaseNoticeContracts(unittest.TestCase):
    def test_bootstrapped_news_three_articles_without_remote_urls(self):
        built_in = json.loads(BOOT.read_text(encoding="utf-8"))
        self.assertEqual(built_in["source"], "kneekura-bundled-local")
        self.assertEqual(built_in["schema_version"], 1)
        self.assertEqual(len(built_in["notices"]), 3)
        ids = {n["id"] for n in built_in["notices"]}
        self.assertEqual(len(ids), 3)
        for entry in built_in["notices"]:
            self.assertIn(entry["category"],
                          {"重要", "運営情報", "更新情報", "イベント", "ガチャ", "不具合"})
            self.assertTrue(entry["title"] and entry["body"])
            self.assertTrue(entry["id"].startswith("kneekura:notice:"))
            self.assertLess(datetime.fromisoformat(entry["published_at"]),
                            datetime.fromisoformat(entry["expires_at"]))
            self.assertNotIn("https://", json.dumps(entry))
            self.assertNotIn("http://", json.dumps(entry))
            self.assertFalse("PONOS" in entry["title"])

    def test_bootstrap_news_matches_operator_draft_without_pretending_release(self):
        built_in = json.loads(BOOT.read_text(encoding="utf-8"))
        season = json.loads(DRAFT.read_text(encoding="utf-8"))
        self.assertEqual(season["status"], "draft")
        catalog = {x["id"]: x for x in season["catalog"]["notice"]}
        self.assertEqual(len(season["catalog"]["notice"]), 3)
        self.assertEqual({x["id"] for x in built_in["notices"]}, set(catalog))
        for notice in built_in["notices"]:
            authored = catalog[notice["id"]]
            self.assertEqual(notice["title"], authored["title"])
            self.assertEqual(notice["body"], authored["body"])
            self.assertEqual(notice["published_at"], authored["published_at"])
            self.assertTrue(authored["ready"])

    def test_ui_entrypoint_is_in_base_and_offline_screen_is_private(self):
        main = MAIN.read_text(encoding="utf-8")
        ui = NOTICE_UI.read_text(encoding="utf-8")
        repository = REPO.read_text(encoding="utf-8")
        store = STORE.read_text(encoding="utf-8")
        manifest = MANIFEST.read_text(encoding="utf-8")
        self.assertIn('noticeButton.setText("i")', main)
        self.assertIn("NoticeActivity.class", main)
        self.assertIn(".NoticeActivity", manifest)
        self.assertIn('android:exported="false"', manifest)
        self.assertNotIn("<uses-permission", manifest)
        self.assertIn("LocalNoticeRepository.current(this)", ui)
        self.assertIn("LocalOpsStore.loadCurrentPack(context)", repository)
        self.assertIn("kneekura-notices-bootstrap.json", repository)
        self.assertIn("static JSONObject loadCurrentPack", store)
        for content in (ui, repository):
            self.assertNotIn("new URL(", content)
            self.assertNotIn("HttpURLConnection", content)
            self.assertNotIn("import android.webkit.WebView;", content)
            self.assertNotIn("new WebView(", content)

    def test_notice_schedule_does_not_grant_stage_clear_or_inventory(self):
        from tools.localcore.notice_feed import notice_feed
        from tools.localcore.ops_calendar import JST
        pack = json.loads(DRAFT.read_text(encoding="utf-8"))
        news = notice_feed(pack, datetime(2026, 10, 9, 11, tzinfo=JST),
                           allow_draft_preview=True)
        self.assertEqual(len(news["news"]), 3)
        self.assertFalse(news["player_save_changed"])
        self.assertEqual(news["network_requests"], 0)


if __name__ == "__main__":
    unittest.main()
