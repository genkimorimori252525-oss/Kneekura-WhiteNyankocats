"""Synthetic AArch64 regression for a version-pinned original resource key map.

No owner's proprietary native binary/pack/SAVE is stored in the tests.
"""
from __future__ import annotations
import struct
import unittest

from tools.base_mod.original_resource_collision import (
    ORIGINAL_COLLISION_ANCHORS, DIRECT_BL_TARGETS, BRANCH_TARGETS,
    OriginalResourceCollisionError, inspect_original_registration_collision_cfg,
    trace_original_registration_collision,
    _branch_target, _direct_bl_target,
)


def synthetic_resource_registration_code() -> bytearray:
    blob = bytearray(max(ORIGINAL_COLLISION_ANCHORS) + 4)
    for pc, opcode in ORIGINAL_COLLISION_ANCHORS.items():
        struct.pack_into("<I", blob, pc, opcode)
    return blob


class OriginalRegisteredResourceCollisionTests(unittest.TestCase):
    def test_exact_synthetic_original_duplicate_collision_cfg_has_no_overwrite(self):
        original = synthetic_resource_registration_code()
        immutable = bytes(original)
        found = inspect_original_registration_collision_cfg(immutable)
        self.assertEqual(
            found["status"], "ORIGINAL_NATIVE_RESOURCE_DUPLICATE_KEY_SKIP_VERIFIED_STATIC"
        )
        self.assertEqual(
            found["same_key_registration_policy"],
            "first successfully registered key is retained by this native path",
        )
        self.assertFalse(found["same_key_update_or_replace_in_this_function"])
        self.assertFalse(found["all_other_native_registry_mutation_sites_excluded"])
        self.assertFalse(found["actual_download_tsv_source_winner_observed"])
        self.assertEqual(bytes(original), immutable)

    def test_exact_bl_and_conditional_branch_targets(self):
        blob = bytes(synthetic_resource_registration_code())
        for pc, target in DIRECT_BL_TARGETS.items():
            with self.subTest(call=hex(pc)):
                self.assertEqual(_direct_bl_target(blob, pc), target)
        for pc, (kind, target) in BRANCH_TARGETS.items():
            with self.subTest(branch=hex(pc)):
                self.assertEqual(_branch_target(blob, pc, kind), target)

    def test_colliding_key_bypass_or_insert_jump_drift_is_refused(self):
        origin = synthetic_resource_registration_code()
        for pc in (0x34D310, 0x34D384, 0x34D3B0, 0x34D3B8,
                   0x34D440, 0x34D480, 0x34D488, 0x34D494):
            with self.subTest(pc=hex(pc)):
                mutated = bytearray(origin)
                struct.pack_into("<I", mutated, pc,
                                 struct.unpack_from("<I", mutated, pc)[0] ^ 0x20)
                with self.assertRaises(OriginalResourceCollisionError):
                    inspect_original_registration_collision_cfg(bytes(mutated))

    def test_non_original_native_cannot_claim_static_evidence(self):
        fake = bytes(synthetic_resource_registration_code())
        with self.assertRaisesRegex(
            OriginalResourceCollisionError, "exact JP15.7.1"
        ):
            trace_original_registration_collision(fake)

    def test_truncated_source_fails_closed(self):
        with self.assertRaises(OriginalResourceCollisionError):
            inspect_original_registration_collision_cfg(b"\x7fELF")
        with self.assertRaises(OriginalResourceCollisionError):
            _direct_bl_target(bytes(4), 0x34D440)


if __name__ == "__main__":
    unittest.main()
