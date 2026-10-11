"""Independent story initial checkpoint for KNEEKURA_SAVE_V1, NO original JP SAVE.

Uses the same bundled JSON specification as Android StoryProgressStore.
Only four chapters (EoC 1–3 and ItF 1) become cleared with all 48 Superior
treasures. Other future chapters, Cosmos, and SoL are untouched. This applies
a one-time additive minimum, not a repeated reset of earned player history.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

POLICY_FILE = (Path(__file__).resolve().parents[2] /
               "app/src/main/assets/kneekura-story-bootstrap-v2.json")
CHAPTERS = ("eoc1", "eoc2", "eoc3", "itf1")
ORIGINAL_INDICES = (0, 1, 2, 4)
STAGES = 48
SUPERIOR_RANK = 3
POLICY_VERSION = 2


class StoryBootstrapError(ValueError):
    pass


def load_approved_policy(path: Path = POLICY_FILE) -> dict:
    policy = json.loads(path.read_text(encoding="utf-8"))
    if (policy.get("schema_version") != 2 or
        policy.get("bootstrap_id") != "kneekura:story:post-itf1-superior" or
        policy.get("authority") != "kneekura-independent-local-only" or
        policy.get("stage_count_per_complete_chapter") != STAGES or
        policy.get("superior_treasure_rank") != SUPERIOR_RANK):
        raise StoryBootstrapError("unrecognized independent story policy")
    expected = list(zip(CHAPTERS, ORIGINAL_INDICES))
    rows = policy.get("chapters")
    if not isinstance(rows, list) or len(rows) != len(expected):
        raise StoryBootstrapError("wrong number of initially cleared chapters")
    for row, (chapter_id, index) in zip(rows, expected):
        if (row.get("id"), row.get("original_jp_chapter_index"),
            row.get("progress"), row.get("stage_clear_count_min"),
            row.get("treasure_rank_min")) != (
            chapter_id, index, STAGES, 1, SUPERIOR_RANK
        ):
            raise StoryBootstrapError("unexpected chapter, stage or treasure level")
    safety = policy.get("safety")
    if not isinstance(safety, dict) or any(safety.values()):
        raise StoryBootstrapError("this checkpoint may not touch original SAVE or rewards")
    if policy.get("other_story_chapters_initially_uncleared") != [
        "itf2", "itf3", "cotc1", "cotc2", "cotc3", "sol"
    ]:
        raise StoryBootstrapError("unexpected uncompleted story chapters")
    return policy


def apply_story_checkpoint(profile: dict, *, policy: dict | None = None) -> dict:
    if not isinstance(profile, dict) or profile.get("schema") != "KNEEKURA_SAVE_V1":
        raise StoryBootstrapError("only the independent Kneekura save is supported")
    policy = load_approved_policy() if policy is None else policy
    # For provided policy objects, never bypass the source-pinned constraints.
    if policy != load_approved_policy():
        raise StoryBootstrapError("an unapproved checkpoint manifest was supplied")
    result = deepcopy(profile)
    version = result.get("story_policy_revision", 0)
    if type(version) is not int or version < 0:
        raise StoryBootstrapError("invalid existing story policy revision")
    if version >= POLICY_VERSION:
        return result
    chapters = result.setdefault("story_chapters", {})
    if not isinstance(chapters, dict):
        raise StoryBootstrapError("invalid existing independent chapter ledger")
    for chapter_id in CHAPTERS:
        record = chapters.setdefault(chapter_id, {})
        if not isinstance(record, dict):
            raise StoryBootstrapError("invalid independent chapter state")
        prior_progress = record.get("progress", 0)
        if type(prior_progress) is not int or not 0 <= prior_progress <= STAGES:
            raise StoryBootstrapError("invalid preexisting chapter progress")
        record["progress"] = max(STAGES, prior_progress)
        for field, minimum, maximum in (("clear_counts", 1, 2**31-1),
                                        ("treasure_ranks", SUPERIOR_RANK, SUPERIOR_RANK)):
            existing = record.get(field, [])
            if not isinstance(existing, list) or len(existing) > STAGES:
                raise StoryBootstrapError("invalid stage progress/treasure array")
            if any(type(value) is not int or not 0 <= value <= maximum
                   for value in existing):
                raise StoryBootstrapError("invalid existing story rank/count")
            record[field] = [
                max(minimum, existing[i] if i < len(existing) else 0)
                for i in range(STAGES)
            ]
    result["story_policy_revision"] = POLICY_VERSION
    return result
