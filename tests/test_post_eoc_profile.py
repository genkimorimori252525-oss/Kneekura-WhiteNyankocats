from pathlib import Path
import json
import unittest

from tools.base_mod import build_post_eoc_save as post


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/post-eoc-static-proof-jp15.7.1.json"


class PostEocProfileContractTest(unittest.TestCase):
    def test_story_checkpoint_contract(self):
        self.assertEqual(post.EOC_CHAPTERS, (0, 1, 2))
        self.assertEqual(post.EOC_STAGE_COUNT, 48)
        self.assertEqual(post.EOC_TREASURE_LEVEL, 3)
        self.assertEqual(post.STORY_PROGRESS_OFFSET, 1145)
        self.assertEqual(post.STORY_CLEAR_TIMES_OFFSET, 1185)
        self.assertEqual(post.STORY_TREASURE_OFFSET, 3225)
        self.assertEqual(post.CLEARED_EOC_1_OFFSET, 120)

    def test_acquisition_contract_is_not_all_units(self):
        self.assertEqual(post.POST_EOC_OWNED_IDS, tuple(range(9)) + (24, 25))
        self.assertEqual(len(post.POST_EOC_OWNED_IDS), 11)
        source = (ROOT / "tools/base_mod/build_post_eoc_save.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("for cat_id in range(ARRAYS_I32", source)
        self.assertIn("for save_id in range(ARRAYS_I32", source)
        self.assertNotIn("eligible_owned = 835", source)

    def test_event_unlock_only_layout_is_pinned(self):
        self.assertEqual(post.EVENT_TYPE_SOL, 0)
        self.assertEqual(post.EVENT_TYPE_NORMAL, 1)
        self.assertEqual(post.EVENT_TYPE_COLLAB, 2)
        self.assertEqual(post.EVENT_MAP_CAPACITY, 500)
        self.assertEqual(post.EVENT_STAR_CAPACITY, 4)
        self.assertEqual(post.EVENT_STAGE_CAPACITY, 12)
        self.assertEqual(post.EVENT_SELECTED_STAGE_BASE, 24450)
        self.assertEqual(post.EVENT_CLEAR_PROGRESS_BASE, 34450)
        self.assertEqual(post.EVENT_STAGE_CLEAR_BASE, 68450)
        self.assertEqual(post.EVENT_UNLOCK_STATE_BASE, 284450)

    def test_exact_static_evidence_matches_contract(self):
        evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        self.assertEqual(
            evidence["candidate"]["sha256"],
            "d13781c149a355618a26fc59ade91b0ca24b562370228f934282fae20308b641",
        )
        self.assertTrue(evidence["candidate"]["pinned_parser_roundtrip_byte_identical"])
        self.assertEqual(evidence["story"]["progress_each"], 48)
        self.assertEqual(evidence["story"]["superior_treasures_each"], 48)
        self.assertEqual(evidence["ownership"]["preowned_count"], 11)
        self.assertEqual(evidence["ownership"]["stage_drop_save_ids_nonzero"], 0)
        self.assertEqual(evidence["events"]["normal"]["map_count"], 436)
        self.assertEqual(evidence["events"]["collab"]["map_count"], 277)
        self.assertEqual(
            evidence["events"]["normal"]["ids_sha256"],
            "cbb9965e288efdc24096f5e771b3b55bfa8541b6a445db6fbe3bc120f4b41d82",
        )
        self.assertEqual(
            evidence["events"]["collab"]["ids_sha256"],
            "d8ec8f9a21131568ac97c12e3ea7ae67911d00c93d2f5b455ac53fbb249d968d",
        )


if __name__ == "__main__":
    unittest.main()
