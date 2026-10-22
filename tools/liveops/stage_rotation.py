"""Author ordinary calendar rules for 20 rotating maps and weekly/monthly picks.

Only availability changes. Original clears, drops and player SAVE are untouched.
The output uses the existing pack schema and original sale.tsv reader.
"""
from copy import deepcopy
from datetime import date, datetime, timedelta
import hashlib
import math
import random

from tools.localcore.ops_calendar import JST, validate_pack


def stage_rotation_pack(pack, selection):
    """Expand an editorial selection into existing weekly/once schedule rules."""
    validate_pack(pack)
    if selection.get('schema_version') != 1:
        raise ValueError('ORIGINAL_STAGE_ROTATION_SCHEMA')
    enabled=selection.get('rotation_enabled',True)
    pools = selection.get('regular_pools', [])
    if (type(enabled) is not bool or not isinstance(pools, list) or (enabled and not pools)
            or (not enabled and pools)
            or any(not isinstance(pool, dict) for pool in pools)):
        raise ValueError('ORIGINAL_STAGE_ROTATION_POOLS')
    if selection.get('preserve_native_stage_rules') and enabled:
        raise ValueError('ORIGINAL_STAGE_UNRESTRICTED_ROTATION_FORBIDDEN')
    seen = set()
    for pool in pools:
        ids, count = pool.get('native_ids'), pool.get('slots')
        if (not isinstance(ids, list) or type(count) is not int or count < 1
                or len(ids) < count * 2 + 1 or len(set(ids)) != len(ids)
                or any(type(n) is not int or not 1000 <= n < 1000000 for n in ids)
                or seen.intersection(ids)):
            raise ValueError('ORIGINAL_STAGE_ROTATION_POOL')
        seen.update(ids)
    if sum(pool['slots'] for pool in pools) != (20 if enabled else 0):
        raise ValueError('ORIGINAL_STAGE_ROTATION_REQUIRES_TWENTY')
    first, stop = (date.fromisoformat(selection[key]) for key in ('start_date', 'end_date'))
    if not first < stop:
        raise ValueError('ORIGINAL_STAGE_ROTATION_DATES')
    for kind, lo, hi in (('weekly', 3, 5), ('monthly', 1, 3)):
        periods = selection.get(kind)
        if not isinstance(periods, list) or not periods:
            raise ValueError('ORIGINAL_STAGE_ROTATION_PERIODS')
        cursor = first
        for period in periods:
            start, end = (date.fromisoformat(period[key]) for key in ('start', 'end'))
            ids = period['native_ids']
            if (start > cursor or not start < end or end <= cursor
                    or not isinstance(ids, list) or not lo <= len(ids) <= hi
                    or any(type(n) is not int or not 1000 <= n < 1000000 for n in ids)
                    or len(set(ids)) != len(ids) or seen.intersection(ids)):
                raise ValueError('ORIGINAL_STAGE_ROTATION_FIXED_SELECTION')
            if kind == 'weekly' and (start.weekday() != 0 or end - start != timedelta(days=7)):
                raise ValueError('ORIGINAL_STAGE_ROTATION_WEEK')
            if kind == 'monthly' and (start.day != 1 or end.day != 1
                    or (end.year * 12 + end.month) - (start.year * 12 + start.month) != 1):
                raise ValueError('ORIGINAL_STAGE_ROTATION_MONTH')
            cursor = end
        if cursor < stop:
            raise ValueError('ORIGINAL_STAGE_ROTATION_GAP')
    # Reserve every special pick, so all regular windows remain twenty distinct
    # maps plus the additional long-lived events, including at period boundaries.
    for week in selection['weekly']:
        for month in selection['monthly']:
            if (week['start'] < month['end'] and month['start'] < week['end']
                    and set(week['native_ids']).intersection(month['native_ids'])):
                raise ValueError('ORIGINAL_STAGE_ROTATION_SPECIAL_DUPLICATE')
    timed=selection.get('timed',[])
    reserved={n for kind in ('weekly','monthly') for p in selection[kind] for n in p['native_ids']}
    for entry in timed:
        ids=entry['native_ids']
        if (not ids or len(set(ids))!=len(ids) or seen.intersection(ids) or reserved.intersection(ids)
                or any(type(n) is not int or not 1000<=n<1000000 for n in ids)
                or entry['mode'] not in ('weekly','monthly','once')):
            raise ValueError('ORIGINAL_STAGE_TIMED_POOL_LEAK')
    excluded=set(selection.get('excluded_native_ids',[]))
    if excluded.intersection(seen|reserved|{n for entry in timed for n in entry['native_ids']}):
        raise ValueError('ORIGINAL_STAGE_UNPUBLISHED_BANNER')
    result = deepcopy(pack)
    result['revision'] += 1
    result['catalog']['stage'] = []
    result['catalog']['event'] = []
    result['schedule'] = [entry for entry in result['schedule']
                          if entry['kind'] not in ('stage', 'event')]
    notice_id = 'kneekura:notice:stage-rotation-20'
    result['catalog']['notice']=[v for v in result['catalog']['notice'] if v['id']!=notice_id]
    result['schedule']=[v for v in result['schedule'] if v['content_id']!=notice_id]

    catalogue_records={}

    def add(suffix, kind, title, ids, slot, rule, category=None):
        identifier = 'kneekura:' + kind + ':' + suffix
        key=(kind,title,tuple(ids),category)
        if key in catalogue_records:
            identifier=catalogue_records[key]
        else:
            record=dict(id=identifier,title=title,source='kneekura-local',ready=True,original=dict(native_ids=ids))
            if category:record['program_category']=category
            result['catalog'][kind].append(record)
            catalogue_records[key]=identifier
        result['schedule'].append(dict(id='kneekura:schedule:' + suffix,
            kind=kind, slot=slot, priority=1, content_id=identifier, rule=rule))

    # A full seven-day grid avoids every day's lineup being identical. Each
    # two-hour group uses one original row containing 20 distinct native map IDs.
    # The extra step avoids reducing the pool to three repeated daily lineups.
    for weekday in range(7) if enabled and not selection.get('rotation_weekly_shuffle') else []:
        for block in range(12):
            index = weekday * 12 + block
            ids = []
            for pool in pools:
                members, count = pool['native_ids'], pool['slots']
                offset = index * (count + 1) % len(members)
                ids.extend(members[(offset + i) % len(members)] for i in range(count))
            add('rotation-%d-%02d' % (weekday, block), 'stage',
                '2時間交代イベント20枠', ids, 'rotation-20',
                dict(mode='weekly', valid_from=first.isoformat(), valid_until=stop.isoformat(),
                     weekdays=[weekday], from_time='%02d:00' % (block * 2),
                     to_time='%02d:00' % ((block * 2 + 2) % 24)))
    if enabled and selection.get('rotation_weekly_shuffle'):
        # Reproducible weekly deck, with an independent calendar-day offset.
        # Deduplicate catalogue records so a longer horizon stays within bounds.
        decks={};records={};cursor=first
        while cursor<stop:
            monday=cursor-timedelta(days=cursor.weekday())
            if monday not in decks:
                decks[monday]=[]
                for pool in pools:
                    members=list(pool['native_ids'])
                    seed=hashlib.sha256((str(monday)+':'+pool['title']).encode()).digest()
                    random.Random(int.from_bytes(seed,'big')).shuffle(members)
                    stride=pool['slots']+1
                    while math.gcd(stride,len(members))!=1:stride+=1
                    decks[monday].append((members,pool['slots'],stride))
            for block in range(12):
                ids=[]
                for members,count,stride in decks[monday]:
                    offset=((cursor-first).days*12+block)*stride%len(members)
                    ids.extend(members[(offset+i)%len(members)] for i in range(count))
                key=tuple(ids)
                begin=datetime.combine(cursor,datetime.min.time(),JST)+timedelta(hours=block*2)
                rule=dict(mode='once',start=begin.isoformat(),end=(begin+timedelta(hours=2)).isoformat())
                suffix='rotation-'+cursor.isoformat()+'-%02d'%block
                if key not in records:
                    add(suffix,'stage','2時間交代チャレンジ20枠',ids,'rotation-20',rule,'rotation')
                    records[key]=result['catalog']['stage'][-1]['id']
                else:
                    result['schedule'].append(dict(id='kneekura:schedule:'+suffix,kind='stage',
                        slot='rotation-20',priority=1,content_id=records[key],rule=rule))
            cursor+=timedelta(days=1)
    for kind in ('weekly', 'monthly'):
        for index, period in enumerate(selection[kind]):
            clock=datetime.strptime(period.get('time','00:00'),'%H:%M').time()
            start = datetime.combine(date.fromisoformat(period['start']), clock, JST)
            end = datetime.combine(date.fromisoformat(period['end']), clock, JST)
            add('%s-picks-%02d' % (kind, index), 'event', period['title'],
                period['native_ids'], kind + '-picks',
                dict(mode='once', start=start.isoformat(), end=end.isoformat()),
                'monthly' if kind=='monthly' else 'event')
    for index,entry in enumerate(timed):
        mode=entry['mode'];days='weekdays' if mode=='weekly' else 'monthdays'
        rule=(dict(mode='once',start=entry['start'],end=entry['end']) if mode=='once' else
              dict(mode=mode,valid_from=first.isoformat(),valid_until=stop.isoformat(),
                   **{days:entry[days]},from_time=entry['from_time'],to_time=entry['to_time']))
        add('timed-%03d'%index,'stage',entry['title'],entry['native_ids'],'timed-%03d'%index,
            rule,entry.get('category'))
    notice_id = 'kneekura:notice:stage-rotation-20'
    result['catalog']['notice'].append(dict(id=notice_id,
        title='イベント20枠が2時間ごとに交代！', category='イベント',
        body='通常イベント20枠が、日本時間の0・2・4・6・8・10・12・14・16・18・20・22時に交代します。'
             '\nさらに週替わりの特選イベント4枠と、月替わり2枠を追加！'
             '\n開催中のバトルはそのままお楽しみください。開催切替は原作のメニュー更新時に反映されます。',
        source='kneekura-local', ready=True, pinned=True,
        published_at=first.isoformat() + 'T00:00:00+09:00'))
    result['schedule'].append(dict(id='kneekura:schedule:notice-stage-rotation-20',
        kind='notice', slot='notice-rotation', priority=20, content_id=notice_id,
        rule=dict(mode='once', start=first.isoformat() + 'T00:00:00+09:00',
                  end=stop.isoformat() + 'T00:00:00+09:00')))
    if timed:
        result['catalog']['notice'][-1]['body']+='\n曜日・ゲリラ・月例攻略は各開催日時に出現。カテゴリ別開催枠を20枠とは別に追加します。解放条件・消費・報酬は原作どおりです。'
    if not enabled:
        result['catalog']['notice'][-1].update(title='原作区分に沿ったステージ開催へ',
            body='自由交代20枠を廃止し、月例・曜日・季節・進行解放の各区分に沿って開催します。'
                 '\nネコフラワーは毎月2日・22日14:22〜14:24。未来編3章クリアが必要です。'
                 '\n経験値シリーズは原作定期枠に、にーくら独自の毎日追加開催を用意します。'
                 '\n解放条件・出撃制限・消費・報酬・一度きりのクリアは原作どおりです。')
    return validate_pack(result)


def main():
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-pack', type=Path, required=True)
    parser.add_argument('--selection', type=Path, required=True)
    parser.add_argument('--out-pack', type=Path, required=True)
    args = parser.parse_args()
    if args.out_pack.exists() or args.out_pack.is_symlink():
        parser.error('ORIGINAL_STAGE_ROTATION_OUTPUT_EXISTS')
    result = stage_rotation_pack(json.loads(args.base_pack.read_text(encoding='utf-8')),
                                 json.loads(args.selection.read_text(encoding='utf-8')))
    with args.out_pack.open('x', encoding='utf-8', newline='\n') as output:
        output.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print('Authored revision %d: 20 regular maps plus weekly/monthly picks; no SAVE writes.'
          % result['revision'])


if __name__ == '__main__':
    main()
