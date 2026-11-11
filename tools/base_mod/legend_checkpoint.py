"""Copy a research save and complete only the first-crown Legend checkpoint.

The pinned GPL parser remains an external development reference. No rewards,
characters, inventory or stage-reward claim flags are granted by this operation.
"""
from __future__ import annotations

import copy
import csv
import hashlib
import io
from pathlib import Path
import re

from tools.battlecats_source import BattleCatsExport
from tools.base_mod.build_offline_max_save import EXPORT_SHA256, _verify_jp_hash
from tools.base_mod.pc_initial_profile import PARSER_COMMIT

CHECKPOINT_MAP = 32
CHECKPOINT_NAME = '恐ろし連邦'


def derive_stage_counts(map_names: bytes, stage_names: bytes) -> tuple[int, ...]:
    """Read real stage counts, excluding the native sentinel and empty padding."""
    maps = list(csv.reader(io.StringIO(map_names.decode('utf-8-sig'))))
    stages = list(csv.reader(io.StringIO(stage_names.decode('utf-8-sig'))))
    if (len(maps) <= CHECKPOINT_MAP or len(stages) <= CHECKPOINT_MAP
            or maps[CHECKPOINT_MAP][:2] != [str(CHECKPOINT_MAP), CHECKPOINT_NAME]):
        raise ValueError('LEGEND_CHECKPOINT_SOURCE_IDENTITY_CHANGED')
    counts = []
    for index in range(CHECKPOINT_MAP + 1):
        row = stages[index]
        if len(maps[index]) < 2 or maps[index][0] != str(index) or row.count('＠') != 1:
            raise ValueError('LEGEND_CHECKPOINT_SOURCE_LAYOUT_CHANGED')
        count = row.index('＠')
        if (not 1 <= count <= 12 or any(not name.strip() for name in row[:count])
                or any(name.strip() for name in row[count + 1:])):
            raise ValueError('LEGEND_CHECKPOINT_SOURCE_LAYOUT_CHANGED')
        counts.append(count)
    return tuple(counts)


def _validate_counts(stage_counts):
    if (len(stage_counts) != CHECKPOINT_MAP + 1
            or any(type(count) is not int or not 1 <= count <= 12 for count in stage_counts)):
        raise ValueError('LEGEND_CHECKPOINT_INVALID_COUNTS')


def apply_checkpoint(save, stage_counts):
    """Return an independent copy; preserve existing counts and higher unlocks."""
    _validate_counts(stage_counts)
    result = copy.deepcopy(save)
    maps = result.event_stages.chapters[0].chapters
    if (len(maps) <= CHECKPOINT_MAP + 1
            or any(len(chapter.chapters) != 4 for chapter in maps[:CHECKPOINT_MAP + 2])
            or any(len(chapter.stages) != 12 for group in maps[:CHECKPOINT_MAP + 2]
                   for chapter in group.chapters)):
        raise ValueError('LEGEND_CHECKPOINT_SAVE_LAYOUT_CHANGED')
    for index, count in enumerate(stage_counts):
        first, second = maps[index].chapters[:2]
        first.clear_progress = max(first.clear_progress, count)
        first.chapter_unlock_state = max(first.chapter_unlock_state, 3)
        for stage in first.stages[:count]:
            stage.clear_amount = max(stage.clear_amount, 1)
        second.chapter_unlock_state = max(second.chapter_unlock_state, 1)
    next_chapter = maps[CHECKPOINT_MAP + 1].chapters[0]
    next_chapter.chapter_unlock_state = max(next_chapter.chapter_unlock_state, 1)
    return result


def verify_checkpoint(before, after, stage_counts):
    """Require the exact semantic result, including every unmodified field.

    Parser serialization represents EventStage.clear_amount as an integer. Error
    messages intentionally contain no private field values or identity data.
    """
    _validate_counts(stage_counts)
    expected = copy.deepcopy(before)
    maps = expected['event_stages']['chapters'][0]
    for index, count in enumerate(stage_counts):
        first, second = maps[index]['chapters'][:2]
        first['clear_progress'] = max(first['clear_progress'], count)
        first['chapter_unlock_state'] = max(first['chapter_unlock_state'], 3)
        for stage in range(count):
            first['stages'][stage] = max(first['stages'][stage], 1)
        second['chapter_unlock_state'] = max(second['chapter_unlock_state'], 1)
    next_chapter = maps[CHECKPOINT_MAP + 1]['chapters'][0]
    next_chapter['chapter_unlock_state'] = max(next_chapter['chapter_unlock_state'], 1)
    if after != expected:
        raise ValueError('LEGEND_CHECKPOINT_UNAPPROVED_SEMANTIC_CHANGE')


def build_checkpoint(source: bytes, owner_export: Path, core):
    """Build separate bytes without writing to the source or an attached device."""
    _verify_jp_hash(source)
    if int.from_bytes(source[:4], 'little') not in (150700, 150704):
        raise ValueError('LEGEND_CHECKPOINT_GAME_VERSION_CHANGED')
    save = core.SaveFile(core.Data(source), load=False)
    save.load()
    if save.to_data().get_bytes() != source:
        raise ValueError('LEGEND_CHECKPOINT_REFERENCE_ROUNDTRIP_CHANGED')
    if not re.fullmatch(r'kneekura-local-[0-9a-f]{32}', save.inquiry_code):
        raise ValueError('LEGEND_CHECKPOINT_FOREIGN_ACCOUNT_REFUSED')
    with BattleCatsExport(owner_export, region='jp', expected_sha256=EXPORT_SHA256) as export:
        names, names_provenance = export.pack('resLocal').read('Map_Name.csv')
        stages, stages_provenance = export.pack('resLocal').read('StageName_RN_ja.csv')
    counts = derive_stage_counts(names, stages)
    result_save = apply_checkpoint(save, counts)
    expected = result_save.to_dict()
    verify_checkpoint(save.to_dict(), expected, counts)
    result = result_save.to_data().get_bytes()
    _verify_jp_hash(result)
    reread = core.SaveFile(core.Data(result), load=False)
    reread.load()
    if reread.to_dict() != expected or reread.to_data().get_bytes() != result:
        raise ValueError('LEGEND_CHECKPOINT_OUTPUT_REREAD_CHANGED')
    report = dict(
        schema='kneekura-legend-checkpoint-v1',
        source_sha256=hashlib.sha256(source).hexdigest(),
        output_sha256=hashlib.sha256(result).hexdigest(),
        source_size=len(source), output_size=len(result), reference_commit=PARSER_COMMIT,
        reference_roundtrip_identical=True, output_roundtrip_identical=True,
        checkpoint_map=CHECKPOINT_MAP, checkpoint_name=CHECKPOINT_NAME, crown=1,
        stage_counts=list(counts), real_stage_count=sum(counts),
        map_names_sha256=names_provenance.payload_sha256,
        stage_names_sha256=stages_provenance.payload_sha256,
        unapproved_fields_unchanged=True, existing_clear_counts_preserved=True,
        existing_higher_unlock_states_preserved=True,
        later_chapter_clear_and_other_crowns_clear_unchanged=True,
        first_clear_reward_flags_and_unit_drops_unchanged=True,
        characters_levels_inventory_and_other_story_events_unchanged=True,
        reward_claim_runtime_consistency='unverified',
    )
    return result, report
