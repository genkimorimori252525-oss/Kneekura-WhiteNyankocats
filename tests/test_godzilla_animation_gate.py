import unittest
from tools.base_mod.godzilla_animation_gate import inspect_index, required_names


def source_index(*stems):
    entries = []
    for stem in stems:
        for name in required_names(stem):
            entries.append({
                "name": name, "source": "private-owned-server-metadata",
                "family": "ImageServer" if name.endswith(".png") else "ImageDataServer",
            })
    return {"schema_version": 1, "entries": entries}


class GodzillaAnimationGateTests(unittest.TestCase):
    def test_exactly_one_valid_source_requires_real_conversion(self):
        report = inspect_index(source_index("550_e", "702_f", "702_c"))
        self.assertEqual(report["source_enemy_stem_evidenced"], "550_e")
        self.assertEqual(report["status"],
                         "SOURCE_RIG_METADATA_PRESENT_CONVERSION_AND_DEVICE_PROOF_REQUIRED")
        self.assertTrue(report["target_preexisting_rig_metadata_complete"])
        self.assertFalse(report["ready_to_install"])
        self.assertEqual(set(report["source_to_target_filenames_only_NOT_a_conversion"].values()),
                         set(required_names("702_f")))
        self.assertNotIn("702_c", str(report["source_to_target_filenames_only_NOT_a_conversion"]))

    def test_no_enemy_rig_does_not_guess(self):
        report = inspect_index(source_index("702_f", "702_c"))
        self.assertIsNone(report["source_enemy_stem_evidenced"])
        self.assertEqual(report["source_to_target_filenames_only_NOT_a_conversion"], {})

    def test_other_complete_candidates_do_not_override_exact_source_anchor(self):
        report = inspect_index(source_index("550_e", "551_e", "552_e"))
        self.assertEqual(report["source_enemy_stem_evidenced"], "550_e")
        self.assertTrue(report["source_to_target_filenames_only_NOT_a_conversion"])

    def test_invalid_index_and_pathlike_stem_rejected(self):
        with self.assertRaises(ValueError):
            inspect_index({"schema_version": 1})
        with self.assertRaises(ValueError):
            inspect_index(source_index("550_e"), enemy_stem="foo/../../bad")
        with self.assertRaises(ValueError):
            inspect_index({"schema_version": 1, "entries": [{"name": "550_e.png"}]})

    def test_alternate_enemy_stem_is_rejected(self):
        with self.assertRaises(ValueError):
            inspect_index(source_index("550_e"), enemy_stem="551_e")


if __name__ == "__main__":
    unittest.main()