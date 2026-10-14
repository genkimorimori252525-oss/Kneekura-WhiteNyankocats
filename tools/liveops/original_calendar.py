"""Project the approved shared calendar into ORIGINAL reader windows.

Original native IDs must come from an independently verified owned catalogue.
No original clears, character grants, mission completions or SAVE writes.
"""
from datetime import datetime
from tools.localcore.ops_calendar import (
    KINDS, ORIGINAL_OWNER_SAVE, JST, _local_timestamp, _rule_intervals, active_at, validate_pack, canonical_hash,
)
from tools.localcore.opsctl import windows_in_range
from tools.localcore.notice_feed import notice_feed
from tools.liveops.original_schedule import EventWindow, ProtocolError, gacha_group_row, stage_row, stream
from tools.liveops.original_ops_bundle import build_bundle


def compile_calendar(pack, bindings, *, start_date, days, login_rotation=None):
    validate_pack(pack)
    if pack['status']!='published' or pack['policy']['owner_save']!=ORIGINAL_OWNER_SAVE:
        raise ProtocolError('ORIGINAL_OPS_REQUIRE_APPROVED_ORIGINAL_PACK')
    if not isinstance(bindings,dict):raise ProtocolError('ORIGINAL_OPS_BINDINGS')
    # Dynamic original prerequisites cannot be frozen into an APK schedule.
    # Keep them in original stage/mission eligibility, or explicitly implement
    # a runtime predicate before accepting an author-side additional gate.
    if any(entry.get('requires') for entry in pack['schedule']):
        raise ProtocolError('ORIGINAL_OPS_DYNAMIC_PREREQUISITE_UNSUPPORTED')
    windows=windows_in_range(pack,start_date,days)
    if not windows:raise ProtocolError('ORIGINAL_OPS_NO_WINDOWS')
    mission_occurrences={entry['id']:list(_rule_intervals(entry['rule'],
        _local_timestamp(pack['season']['start']),_local_timestamp(pack['season']['end'])))
        for entry in pack['schedule'] if entry['kind']=='mission'}
    points={_local_timestamp(row[key]) for row in windows for key in ('start','end')}
    first,last=min(points),max(points)
    for notice in pack['catalog']['notice']:
        publication=_local_timestamp(notice.get('published_at',pack['season']['start']))
        if first<publication<last:points.add(publication)
    boundaries=sorted(points)
    selected={}
    for begin,end in zip(boundaries,boundaries[1:]):
        snapshot=active_at(pack,begin)
        for kind in ('gacha','stage','event','mission'):
            for row in snapshot['active'][kind]:
                identifier=row['content_id'];binding=bindings.get(identifier)
                if kind!='notice' and (not isinstance(binding,dict) or binding.get('kind')!=kind):
                    raise ProtocolError('ORIGINAL_OPS_SOURCE_BINDING_MISSING')
                occurrence=None
                if kind=='mission':
                    matches=[span for span in mission_occurrences[row['schedule_id']]
                             if span[0]<=begin<span[1]]
                    if len(matches)!=1:raise ProtocolError('ORIGINAL_OPS_MISSION_OCCURRENCE')
                    occurrence=matches[0]
                key=(kind,row['slot'],identifier,occurrence)
                spans=selected.setdefault(key,[])
                if spans and spans[-1][1]==begin:spans[-1]=(spans[-1][0],end)
                else:spans.append((begin,end))
        for notice in notice_feed(pack,begin)['news']:
            spans=selected.setdefault(('notice',notice['schedule_id'],notice['id'],None),[])
            if spans and spans[-1][1]==begin:spans[-1]=(spans[-1][0],end)
            else:spans.append((begin,end))
    sale=[];gacha=[];gacha_windows=[];report=[];notices=[]
    catalog={kind:{record['id']:record for record in pack['catalog'][kind]} for kind in KINDS}
    schedules={entry['id']:entry for entry in pack['schedule']}
    for (kind,slot,identifier,occurrence),spans in sorted(selected.items()):
        binding=bindings.get(identifier)
        if kind=='mission':
            expected=(max(occurrence[0],boundaries[0]),min(occurrence[1],boundaries[-1]))
            if spans!=[expected]:
                raise ProtocolError('ORIGINAL_OPS_MISSION_PREEMPTION_UNSUPPORTED')
            # Original SAVE identifies a mission period by its original window.
            # A rebuild mid-week must not create a fresh start date or merge weeks.
            spans=[occurrence]
        for begin,end in spans:
            window=EventWindow(begin,end)
            if kind=='notice':
                record=catalog[kind][identifier]
                pub_time = _local_timestamp(record['published_at']) if record.get('published_at') else begin
                effective_begin = max(begin, pub_time)
                if effective_begin < end:
                    notices.append(dict(start_epoch_ms=int(effective_begin.timestamp()*1000),
                        end_epoch_ms=int(end.timestamp()*1000),title=record['title'],body=record['body'],
                        id=identifier,published_epoch_ms=int(pub_time.timestamp()*1000),
                        priority=schedules[slot]['priority'],pinned=record.get('pinned',False) is True))
            elif kind=='gacha':
                gacha_windows.append((begin,end,slot,identifier,binding))
            else:
                sale.append(stage_row(window,binding['native_ids']))
            report.append(dict(kind=kind,slot=slot,content_id=identifier,
                start=begin.isoformat(),end=end.isoformat()))
    # Serialize simultaneous banners using the original category-count row,
    # separately for ordinary rare and normal gacha.
    gacha_points=sorted({p for a,b,*_ in gacha_windows for p in (a,b)})
    grouped={}
    for begin,end in zip(gacha_points,gacha_points[1:]):
        active={}
        for a,b,slot,identifier,binding in gacha_windows:
            if a<=begin<b:
                active.setdefault(binding.get('gacha_type',1),[]).append((slot,identifier,binding))
        for category,items in sorted(active.items()):
            items.sort(key=lambda item:item[0])
            fingerprint=tuple((slot,identifier) for slot,identifier,_ in items)
            spans=grouped.setdefault(category,[])
            if spans and spans[-1][1]==begin and spans[-1][2]==fingerprint:
                spans[-1]=(spans[-1][0],end,fingerprint,items)
            else:spans.append((begin,end,fingerprint,items))
    has_permanent_normal=False
    for category,spans in sorted(grouped.items()):
        for begin,end,_,items in spans:
            permanent=category==0 and all(binding.get('permanent') is True for _,_,binding in items)
            if permanent:
                # Original reader's long availability horizon; no seasonal expiry.
                begin,end=datetime(2000,1,1,tzinfo=JST),datetime(2037,1,1,tzinfo=JST)
                has_permanent_normal=True
            entries=[dict(set_id=binding['set_id'],cost=binding.get('cost',150),
                chances=binding['chances'],guaranteed=binding.get('guaranteed',(0,0,0,0,0)),
                message='' if permanent else catalog['gacha'][identifier]['title']) for _,identifier,binding in items]
            gacha.append(gacha_group_row(EventWindow(begin,end),entries,gacha_type=category))
    notices.sort(key=lambda n: (not n['pinned'],-n['published_epoch_ms'],-n['priority'],n['id']))
    if not sale and not gacha:raise ProtocolError('ORIGINAL_OPS_NO_READY_ORIGINAL_CONTENT')
    window=EventWindow(boundaries[0],boundaries[-1])
    if has_permanent_normal:
        # Source lifetime covers the permanent normal rows. Seasonal sale/rare
        # rows keep their own original end dates; never extend their events.
        window=EventWindow(datetime(2000,1,1,tzinfo=JST),datetime(2037,1,1,tzinfo=JST))
    data=build_bundle(window,revision=pack['revision'],files={
        'sale.tsv':stream(sale),'gatya.tsv':stream(gacha),'item.tsv':stream([])},
        login_rotation=login_rotation,notices=notices)
    return data,dict(calendar_sha256=canonical_hash(pack),windows=report,
        original_save_mutated=False,original_ui_accepted=False)
