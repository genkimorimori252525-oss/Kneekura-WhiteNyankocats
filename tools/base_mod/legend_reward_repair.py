"""Repair rewards omitted by the earlier bounded Legend checkpoint.

This operates on a separate owner-controlled local SAVE copy. It never grants
the cat-food gift: the original once-only item delivery handles that.
"""
from __future__ import annotations

import copy
import csv
import hashlib
import io
import re
from pathlib import Path

from tools.battlecats_source import BattleCatsExport
from tools.base_mod.build_offline_max_save import EXPORT_SHA256, _verify_jp_hash
from tools.base_mod.legend_checkpoint import derive_stage_counts

EXPECTED = ((17, 5, 1113, 39, 130), (22, 5, 1118, 59, 172),
            (27, 5, 1131, 88, 268))


def derive_targets(export_path: Path):
    with BattleCatsExport(export_path, region='jp', expected_sha256=EXPORT_SHA256) as export:
        data, names = export.pack('DataLocal'), export.pack('resLocal')
        counts = derive_stage_counts(names.read('Map_Name.csv')[0], names.read('StageName_RN_ja.csv')[0])
        drops = {}
        for row in csv.reader(io.StringIO(data.read('drop_chara.csv')[0].decode('utf-8-sig'))):
            try:
                item, index, cat = map(int, row[:3])
            except (ValueError, TypeError):
                continue
            if item >= 0:
                if item in drops:
                    raise ValueError('LEGEND_REWARD_DUPLICATE_DROP')
                drops[item] = index, cat
        found = []
        for chapter, count in enumerate(counts):
            payload = data.read(f'MapStageDataN_{chapter:03}.csv')[0].decode('utf-8-sig')
            lines = [line.split('//')[0].strip() for line in payload.splitlines()
                     if line.split('//')[0].strip()]
            if len(lines) < count + 2:
                raise ValueError('LEGEND_REWARD_STAGE_LAYOUT_CHANGED')
            for stage, line in enumerate(lines[2:count + 2]):
                fields = [int(value.strip()) for value in line.split(',') if value.strip()]
                for position in range(5, len(fields) - 2, 3):
                    item = fields[position + 1]
                    if item in drops:
                        found.append((chapter, stage, item, *drops[item]))
    if tuple(found) != EXPECTED:
        raise ValueError('LEGEND_REWARD_SOURCE_TARGETS_CHANGED')
    return tuple(found)


def build_repair(source: bytes, owner_export: Path, core):
    _verify_jp_hash(source)
    if int.from_bytes(source[:4], 'little') not in (150700, 150704):
        raise ValueError('LEGEND_REWARD_UNSUPPORTED_SAVE')
    save = core.SaveFile(core.Data(source), load=False)
    save.load()
    if save.to_data().get_bytes() != source:
        raise ValueError('LEGEND_REWARD_SOURCE_ROUNDTRIP')
    if not re.fullmatch(r'kneekura-local-[0-9a-f]{32}', save.inquiry_code):
        raise ValueError('LEGEND_REWARD_FOREIGN_ACCOUNT')
    targets = derive_targets(owner_export)
    expected = copy.deepcopy(save.to_dict())
    repaired = []
    for chapter, stage, item, drop_index, cat_id in targets:
        if save.event_stages.chapters[0].chapters[chapter].chapters[0].stages[stage].clear_amount < 1:
            continue
        cat = save.cats.cats[cat_id]
        cat.unlocked = max(cat.unlocked, 1)
        cat.gatya_seen = max(cat.gatya_seen, 1)
        save.unit_drops[drop_index] = max(save.unit_drops[drop_index], 1)
        target = expected['cats']['cats'][cat_id]
        target['unlocked'] = max(target['unlocked'], 1)
        target['gatya_seen'] = max(target['gatya_seen'], 1)
        expected['unit_drops'][drop_index] = max(expected['unit_drops'][drop_index], 1)
        repaired.append(cat_id)
    save.xp = max(save.xp, 99_999_999)
    save.np = max(save.np, 9_999)
    expected['xp'] = max(expected['xp'], 99_999_999)
    expected['np'] = max(expected['np'], 9_999)
    if save.to_dict() != expected:
        raise ValueError('LEGEND_REWARD_UNAPPROVED_CHANGE')
    result = save.to_data().get_bytes()
    _verify_jp_hash(result)
    reread = core.SaveFile(core.Data(result), load=False)
    reread.load()
    if reread.to_dict() != expected or reread.to_data().get_bytes() != result:
        raise ValueError('LEGEND_REWARD_OUTPUT_ROUNDTRIP')
    return result, dict(source_sha256=hashlib.sha256(source).hexdigest(),
                        output_sha256=hashlib.sha256(result).hexdigest(),
                        rewarded_cats=repaired, cleared_stage_required=True,
                        xp_limit=99_999_999, np_minimum=9_999,
                        other_fields_unchanged=True, original_catfood_gift_separate=True)
