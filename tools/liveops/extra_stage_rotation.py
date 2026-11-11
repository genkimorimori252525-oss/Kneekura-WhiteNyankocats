"""Add a bounded, reproducible local stage rotation to an existing bundle.

Only availability rows change. Original eligibility, clears and rewards are
left to the game, and existing scheduled occurrences are never replaced.
"""
import base64
from datetime import date, datetime, timedelta
import hashlib
import json
import math
import random

from tools.liveops.original_ops_bundle import _timestamp, validate_bundle
from tools.liveops.original_schedule import EventWindow, stage_row, stream
from tools.localcore.ops_calendar import JST
from tools.base_mod.build_offline_max_save import EXPORT_SHA256

POOLS = {
    'experience': (3, (1028, 1059, 1124, 1155, 1319)),
    'manic': (3, tuple(range(1102, 1111))),
    'little': (2, tuple(range(1130, 1139))),
    'event': (2, (1069, 1120, 1190, 1111, 1114, 1116, 1065, 1206)),
}
COLLABORATIONS = {
    '魔法少女まどか☆マギカコラボステージ': 13,
    'エヴァンゲリオンコラボステージ': 9,
    'メルクストーリアコラボステージ': 8,
    'ケリ姫スイーツコラボステージ': 6,
    '城とドラゴンコラボステージ': 5,
    '生きろ！マンボウ！コラボステージ': 3,
    'ゴジラコラボステージ': 2,
}


def verify_catalogue(audit):
    if audit.get('source_export_sha256') != EXPORT_SHA256:
        raise ValueError('EXTRA_STAGE_SOURCE_EXPORT_CHANGED')
    maps = {record['native_id']: record for record in audit['maps']}
    for kind, (_, members) in POOLS.items():
        for identifier in members:
            record = maps[identifier]
            if record['source_category_status'] != 'MATCHED_INDEX' or '(旧)' in record['title']:
                raise ValueError('EXTRA_STAGE_UNCONFIRMED_SOURCE')
            categories = record['source_category']
            if (kind == 'event' and categories != ['イベントステージ'] or
                kind == 'experience' and 'ゲリラステージ' not in categories or
                kind == 'manic' and '大狂乱ステージ' not in categories or
                kind == 'little' and 'ちび開眼ステージ' not in categories):
                raise ValueError('EXTRA_STAGE_CATEGORY_MISMATCH')
    for category, count in COLLABORATIONS.items():
        selected = [r for r in maps.values() if category in r['source_category']
                    and '(旧)' not in r['title']]
        if len(selected) != count or any(r['source_category_status'] != 'MATCHED_INDEX' for r in selected):
            raise ValueError('EXTRA_STAGE_COLLABORATION_CATALOGUE_CHANGED')


def collaboration_stages(audit, category):
    if category not in COLLABORATIONS:
        raise ValueError('EXTRA_STAGE_UNKNOWN_COLLABORATION')
    return sorted(r['native_id'] for r in audit['maps']
                  if category in r['source_category'] and '(旧)' not in r['title'])


def choose_extra(day, hour, existing):
    """Pick up to ten hourly maps without duplicating an active map."""
    if not 0 <= hour < 24:
        raise ValueError('EXTRA_STAGE_BLOCK')
    selected = []
    seen = set(existing)
    for name, (count, pool) in POOLS.items():
        members = list(pool)
        seed = hashlib.sha256((day.isoformat() + ':' + name).encode()).digest()
        random.Random(int.from_bytes(seed, 'big')).shuffle(members)
        stride = count + 1
        while math.gcd(stride, len(members)) != 1:
            stride += 1
        offset = hour * stride % len(members)
        taken = 0
        for i in range(len(members)):
            value = members[(offset + i) % len(members)]
            if value not in seen:
                selected.append(value)
                seen.add(value)
                taken += 1
                if taken == count:
                    break
    return selected


def choose_weekly(day):
    """Select one collaboration for a whole JST week, without adjacent repeats."""
    monday = day - timedelta(days=day.weekday())
    members = list(COLLABORATIONS)
    seed = hashlib.sha256(b'kneekura-autumn-2026-collaboration').digest()
    random.Random(int.from_bytes(seed, 'big')).shuffle(members)
    index = (monday - date(2026, 11, 9)).days // 7
    return members[index % len(members)]


def extend_bundle(raw, audit, start, end):
    """Preserve every old stream/row, adding per-hour availability only."""
    bundle = validate_bundle(raw)
    verify_catalogue(audit)
    if (bundle['game_version'] != 150704 or bundle['revision'] != 16 or
            start.tzinfo != JST or end.tzinfo != JST or start >= end or
            start.hour or end.hour or start.minute or start.second or end.minute or end.second):
        raise ValueError('EXTRA_STAGE_SOURCE_OR_WINDOW')
    original = base64.b64decode(bundle['server_files']['sale.tsv']).decode('utf-8')
    old_rows = original[len('[start]\n'):-len('[end]\n')].splitlines()
    old_windows = []
    for row in old_rows:
        fields = row.split('\t')
        old_windows.append((_timestamp(fields[0], fields[1]), _timestamp(fields[2], fields[3]),
                            set(map(int, fields[9:]))))
    added = []
    weekly_rows = []
    weeks = {}
    day = start.date()
    while day <= (end - timedelta(microseconds=1)).date():
        monday = day - timedelta(days=day.weekday())
        if monday not in weeks:
            first = max(start, datetime.combine(monday, datetime.min.time(), JST))
            last = min(end, datetime.combine(monday + timedelta(days=7), datetime.min.time(), JST))
            active = set().union(*(ids for a, b, ids in old_windows if a < last and first < b))
            category = choose_weekly(day)
            ids = collaboration_stages(audit, category)
            if active.intersection(ids):
                raise ValueError('EXTRA_STAGE_COLLABORATION_OVERLAPS_BASE')
            weeks[monday] = (category, ids)
            fields = stage_row(EventWindow(first, last), ids).split('\t')
            fields[4:6] = ['150704', '150704']
            weekly_rows.append('\t'.join(fields))
        day += timedelta(days=1)
    intervals = []
    now = start
    while now < end:
        stop = min(now + timedelta(hours=1), end)
        active = set().union(*(ids for first, last, ids in old_windows if first < stop and now < last))
        monday = now.date() - timedelta(days=now.weekday())
        category, weekly = weeks[monday]
        chosen = choose_extra(now.date(), now.hour, active | set(weekly))
        if chosen:
            fields = stage_row(EventWindow(now, stop), chosen).split('\t')
            fields[4:6] = ['150704', '150704']
            added.append('\t'.join(fields))
        intervals.append(dict(start=now.isoformat(), ids=chosen,
                              collaboration=category, collaboration_ids=weekly))
        now = stop
    bundle['server_files']['sale.tsv'] = base64.b64encode(stream(old_rows + added + weekly_rows)).decode('ascii')
    titles = {record['native_id']: record['title'] for record in audit['maps']}
    notices = []
    day = start
    while day < end:
        following = day + timedelta(days=1)
        today = [entry for entry in intervals if entry['start'][:10] == day.date().isoformat()]
        if len(today) != 24:
            raise ValueError('EXTRA_STAGE_NOTICE_DAY_INCOMPLETE')
        collaboration = today[0]['collaboration'].replace('コラボステージ', '')
        lines = ['追加イベントは毎時0分に交代。既存の開催はこの一覧以外にもあります。',
                 '開催期間中のコラボ：' + collaboration,
                 'ステージごとの解放・挑戦条件は原作どおりです。', '']
        for hour, entry in enumerate(today):
            names = '、'.join(titles[identifier] for identifier in entry['ids'])
            lines.append(f'{hour:02d}:00〜{(hour + 1) % 24:02d}:00　{names}')
        timestamp = int(day.timestamp() * 1000)
        notices.append(dict(id='kneekura:notice:extra-stages-' + day.strftime('%Y%m%d'),
                            title=day.strftime('%m月%d日') + 'の追加イベント予定',
                            body='\n'.join(lines), start_epoch_ms=timestamp,
                            end_epoch_ms=int(following.timestamp() * 1000),
                            published_epoch_ms=timestamp, priority=50, pinned=True))
        day = following
    bundle['notices'] = notices + bundle.get('notices', [])
    bundle['revision'] = 20
    output = (json.dumps(bundle, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode()
    validate_bundle(output)
    return output, intervals
