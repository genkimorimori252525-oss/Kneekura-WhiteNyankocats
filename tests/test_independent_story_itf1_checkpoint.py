"""Source/behavior regression for additive independent Future-Chapter-1 seed.

This deliberately NEVER edits the original JP15.7.1 SAVE_DATA or the old
native cap updater, and never treats "available to play" as "cleared".
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from tools.localcore.kneekura_save_v1 import fresh_profile, validate
from tools.localcore.story_checkpoint import (
    CHAPTERS, ORIGINAL_INDICES, POLICY_VERSION, STAGES, SUPERIOR_RANK,
    StoryBootstrapError, apply_story_checkpoint, load_approved_policy,
)


ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "app/src/main/assets/kneekura-story-bootstrap-v2.json"
JAVA = ROOT / "app/src/main/java/jp/kneekura/whitenyankocats/StoryProgressStore.java"
MAIN = ROOT / "app/src/main/java/jp/kneekura/whitenyankocats/MainActivity.java"


class IndependentStoryInitialCheckpointTests(unittest.TestCase):
    def test_approved_chapters_and_true_jp_source_numbering(self):
        rules = load_approved_policy()
        self.assertEqual(tuple(item["id"] for item in rules["chapters"]), CHAPTERS)
        self.assertEqual(tuple(item["original_jp_chapter_index"]
                               for item in rules["chapters"]), ORIGINAL_INDICES)
        self.assertEqual(ORIGINAL_INDICES, (0, 1, 2, 4))
        self.assertEqual(STAGES, 48)
        self.assertEqual(SUPERIOR_RANK, 3)
        self.assertEqual(rules["other_story_chapters_initially_uncleared"],
                         ["itf2", "itf3", "cotc1", "cotc2", "cotc3", "sol"])

    def test_new_independent_save_all_four_chapters_48_superior(self):
        state = fresh_profile(12345)
        validate(state)
        self.assertEqual(state["story_policy_revision"], POLICY_VERSION)
        self.assertEqual(set(state["story_chapters"]), set(CHAPTERS))
        self.assertEqual(len(state["story_chapters"]), 4)
        for id_ in CHAPTERS:
            chapter = state["story_chapters"][id_]
            self.assertEqual(chapter["progress"], 48)
            self.assertEqual(chapter["clear_counts"], [1] * 48)
            self.assertEqual(chapter["treasure_ranks"], [3] * 48)
        for id_ in ["itf2", "itf3", "cotc1", "cotc2", "cotc3", "sol"]:
            self.assertNotIn(id_, state["story_chapters"])
        self.assertEqual(state["cleared_stages"], [])  # unrelated imported stage ledger
        self.assertEqual(state["unlocked_units"], [])  # no fake stage-reward grants

    def test_upgrade_existing_profile_only_once_and_preserve_all_else(self):
        original = {
            "schema": "KNEEKURA_SAVE_V1", "revision": 5,
            "story_policy_revision": 1,
            "story_chapters": {
                "eoc1": {"progress": 20, "clear_counts": [4, 0],
                         "treasure_ranks": [3, 1], "player_note": "mine"},
                "itf2": {"progress": 7, "clear_counts": [6, 1],
                         "treasure_ranks": [0, 2]},
                "sol": {"progress": 8, "clear_counts": [2], "treasure_ranks": [0]},
            },
            "currency": {"xp": 99123, "catfood": 300},
            "unlocked_units": [123, 288],
            "cleared_stages": ["kneekura:other:clear"],
            "local_gacha": {"campaign": "mine"},
        }
        original_copy = deepcopy(original)
        updated = apply_story_checkpoint(original)
        self.assertEqual(original, original_copy)
        self.assertEqual(updated["revision"], 5)
        self.assertEqual(updated["currency"], original["currency"])
        self.assertEqual(updated["unlocked_units"], original["unlocked_units"])
        self.assertEqual(updated["cleared_stages"], original["cleared_stages"])
        self.assertEqual(updated["local_gacha"], original["local_gacha"])
        self.assertEqual(updated["story_chapters"]["itf2"], original["story_chapters"]["itf2"])
        self.assertEqual(updated["story_chapters"]["sol"], original["story_chapters"]["sol"])
        self.assertEqual(updated["story_chapters"]["eoc1"]["clear_counts"][0], 4)
        self.assertEqual(updated["story_chapters"]["eoc1"]["treasure_ranks"][0:2], [3, 3])
        self.assertEqual(updated["story_chapters"]["eoc1"]["player_note"], "mine")
        self.assertEqual(apply_story_checkpoint(updated), updated)

    def test_stale_or_invalid_policy_is_rejected_without_mutation(self):
        original = {"schema": "KNEEKURA_SAVE_V1", "story_chapters": {},
                    "currency": {"catfood": 100}}
        with self.assertRaises(StoryBootstrapError):
            apply_story_checkpoint(original, policy={"schema_version": 2})
        self.assertEqual(original["story_chapters"], {})
        with self.assertRaises(StoryBootstrapError):
            apply_story_checkpoint({"schema": "PONOS_SAVE_DATA"})
        bad = deepcopy(original)
        bad["story_chapters"]["eoc1"] = {"progress": -10}
        with self.assertRaises(StoryBootstrapError):
            apply_story_checkpoint(bad)
        bad = deepcopy(original)
        bad["story_chapters"]["itf1"] = {"treasure_ranks": [4]}
        with self.assertRaises(StoryBootstrapError):
            apply_story_checkpoint(bad)

    def test_android_contract_real_bootstrap_not_settings_only(self):
        policy = json.loads(ASSET.read_text(encoding="utf-8"))
        code = JAVA.read_text(encoding="utf-8")
        main = MAIN.read_text(encoding="utf-8")
        self.assertEqual(policy["bootstrap_id"],
                         "kneekura:story:post-itf1-superior")
        self.assertIn("AtomicFile", code)
        self.assertIn("store.finishWrite(output)", code)
        self.assertIn("store.failWrite(output)", code)
        self.assertIn("if (revision >= POLICY_VERSION) return summary(root);", code)
        self.assertIn("for (String id : CHAPTERS) mergeChapter(chapters, id);", code)
        self.assertIn("new JSONArray()", code)
        self.assertIn("COMPLETE_STAGES = 48", code)
        self.assertIn("SUPERIOR = 3", code)
        self.assertIn("JP_INDICES = {0, 1, 2, 4}", code)
        self.assertIn("StoryProgressStore.ensureInitialCheckpoint(this)", main)
        self.assertIn("未来編1章クリア", main)
        self.assertNotIn("File(\"SAVE_DATA\")", code)
        self.assertFalse(policy["safety"]["modifies_original_ponos_save"])
        self.assertFalse(policy["safety"]["affects_gacha_ownership"])
        self.assertFalse(policy["safety"]["affects_stage_rewards"])


if __name__ == "__main__":
    unittest.main()
