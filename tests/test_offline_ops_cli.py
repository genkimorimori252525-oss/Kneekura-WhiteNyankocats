"""Smoke the user-facing offline operations CLI exactly as an agent would."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "ops/seasons/2026-autumn-prototype.json"


def run(*arguments):
    return subprocess.run(
        [sys.executable, "-m", "tools.localcore.opsctl", *arguments],
        cwd=ROOT, capture_output=True, text=True, timeout=20, check=False,
    )


class OfflineOpsCliSmokeTests(unittest.TestCase):
    def test_validate_only_read_local_authoring_data(self):
        result = run("validate", "--pack", str(PACK))
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["pack_status"], "draft")
        self.assertEqual(report["catalog_entries"]["login"], 5)
        self.assertEqual(report["network_requests"], 0)
        self.assertEqual(report["save_mutations"], 0)
        self.assertTrue(report["not_an_android_game_update"])

    def test_preview_never_fabricates_active_gacha_or_stage(self):
        result = run("preview", "--pack", str(PACK),
                     "--at", "2026-10-09T19:00:00+09:00")
        self.assertEqual(result.returncode, 0, result.stderr)
        snapshot = json.loads(result.stdout)["snapshot"]
        self.assertEqual(snapshot["active"]["gacha"], [])
        self.assertEqual(snapshot["active"]["stage"], [])
        self.assertEqual(len(snapshot["preview"]["notice"]), 1)
        self.assertTrue(any(x["kind"] == "stage" for x in snapshot["blocked"]))

    def test_windows_outside_season_not_rendered(self):
        from tools.localcore.opsctl import windows_in_range
        from tools.localcore.ops_calendar import JST
        pack = json.loads(PACK.read_text(encoding="utf-8"))
        self.assertEqual(windows_in_range(pack, "2026-12-01", 14), [])
        clip = windows_in_range(pack, "2026-11-30", 4)
        self.assertTrue(all(w["end"] <= "2026-12-01T00:00:00+09:00" for w in clip))
        self.assertTrue(all(w["start"] < w["end"] for w in clip))

    def test_calendar_range_and_fail_closed_invalid_pack(self):
        result = run("calendar", "--pack", str(PACK),
                     "--from-date", "2026-10-09", "--days", "14")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(any(x["kind"] == "gacha" for x in report["windows"]))
        self.assertTrue(any(x["kind"] == "stage" for x in report["windows"]))
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory) / "unsafe.json"
            fake.write_text(json.dumps({"schema_version":1,"channel":"official-online"}),
                            encoding="utf-8")
            result = run("validate", "--pack", str(fake))
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("network_requests", result.stdout)

if __name__ == "__main__":
    unittest.main()
