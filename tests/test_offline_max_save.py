import hashlib
import json
from pathlib import Path
import struct
import unittest

from tools.base_mod import build_offline_max_save as maxsave


ROOT = Path(__file__).resolve().parents[1]


class OfflineMaxSaveLayoutTest(unittest.TestCase):
    def test_exact_layout_regressions(self):
        self.assertEqual(maxsave.ARRAYS_I32["cat_unlocked"], (8401, 882, 8397))
        self.assertEqual(maxsave.ARRAYS_I32["cat_gatya_seen"], (19851, 882, 19847))
        self.assertEqual(
            maxsave.ARRAYS_I32["cat_unlocked_forms"],
            (310322, 882, 310318),
        )
        self.assertEqual(maxsave.ARRAYS_I32["lucky_tickets"], (439776, 55, 439772))
        self.assertEqual(maxsave.ARRAYS_I32["catfruit"], (385884, 29, 385880))
        self.assertEqual(maxsave.ARRAYS_I16["labyrinth_medals"], (484928, 4, None))

    def test_talent_orb_and_engineer_contract(self):
        self.assertEqual(maxsave.TALENT_ORB_COUNT, 310)
        self.assertEqual(maxsave.TALENT_ORB_VALUE, 998)
        self.assertEqual(maxsave.TALENT_ORB_INSERT_BYTES, 1240)
        self.assertEqual(maxsave.I32["engineers"], 399146)
        self.assertEqual(maxsave.MAX_VALUES["engineers"], 5)
        self.assertEqual(maxsave.MAX_VALUES["platinum_shards"], 9)

    def test_scalar_width_contract(self):
        self.assertEqual(maxsave.I32["catfood"], 7)
        self.assertEqual(maxsave.I32["xp"], 75)
        self.assertEqual(maxsave.I32["np"], 451687)
        self.assertEqual(maxsave.I16["leadership"], 451697)
        self.assertEqual(maxsave.I32["hundred_million_ticket"], 495780)

    def test_hash_helpers_match_jp_envelope(self):
        payload = bytearray(b"\x00" * 128)
        struct.pack_into("<i", payload, 0, 150700)
        digest = hashlib.md5(maxsave.JP_SALT + payload).hexdigest().encode("ascii")
        save = bytes(payload) + digest

        stored, expected = maxsave._verify_jp_hash(save)
        self.assertEqual(stored, expected)

        mutable = bytearray(save)
        mutable[7] = 1
        rewritten = maxsave._rewrite_hash(mutable)
        self.assertEqual(rewritten.encode("ascii"), mutable[-32:])
        self.assertEqual(maxsave._verify_jp_hash(bytes(mutable))[0], rewritten)

    def test_evidence_matches_transformer_contract(self):
        evidence = json.loads(
            (
                ROOT
                / "docs/evidence/offline-profile-save-roundtrip-jp15.7.1.json"
            ).read_text(encoding="utf-8")
        )

        self.assertEqual(
            evidence["baseline"]["sha256"],
            maxsave.BASELINE_SHA256,
        )
        self.assertEqual(evidence["baseline"]["size"], maxsave.BASELINE_SIZE)
        self.assertEqual(
            evidence["candidate"]["sha256"],
            "0f5cbdadf2536f05af7748f7696ca93233dfb01d80dfe98a17da0fd5e6cf65e7",
        )
        self.assertTrue(
            evidence["candidate"]["raw_offset_transform_matches_parser_oracle_byte_for_byte"]
        )
        self.assertEqual(
            evidence["exact_field_map"]["arrays_i32"]["event_lucky_tickets"]["count"],
            55,
        )
        self.assertEqual(
            evidence["exact_field_map"]["arrays_i32"]["cat_unlocked_forms"][
                "data_offset"
            ],
            310322,
        )
        self.assertEqual(evidence["unit_bootstrap"]["eligible_unit_count"], 835)
        self.assertEqual(evidence["unit_bootstrap"]["unit_drop_save_ids_enabled"], 255)
        self.assertEqual(evidence["candidate"]["size"], 497580)
        self.assertEqual(evidence["candidate_values"]["talent_orb_types"], 310)
        self.assertEqual(evidence["candidate_values"]["talent_orbs_each"], 998)
        self.assertEqual(evidence["candidate_values"]["engineers"], 5)
        self.assertEqual(evidence["candidate_values"]["platinum_shards"], 9)

    def test_caps_fit_serialized_widths(self):
        self.assertLessEqual(maxsave.MAX_VALUES["leadership"], 0x7FFF)
        self.assertLessEqual(maxsave.MAX_VALUES["labyrinth_medals"], 0x7FFF)
        for name, value in maxsave.MAX_VALUES.items():
            if name in {"leadership", "labyrinth_medals"}:
                continue
            self.assertGreaterEqual(value, 0, name)
            self.assertLessEqual(value, 0x7FFFFFFF, name)


if __name__ == "__main__":
    unittest.main()
