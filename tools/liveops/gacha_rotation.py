"""Author two three-hour rare slots, one weekly rare, and ordinary Cat Gacha."""
from copy import deepcopy
from datetime import date, timedelta

from tools.localcore.ops_calendar import validate_pack


def validate_editorial_policy(selection):
    """Keep collaborations out of the ordinary pool and seasons in date range."""
    policy=selection.get('set_policy')
    if policy is None:return  # Older authored packs remain readable.
    for identifier in selection['rotating_set_ids']:
        if policy.get(str(identifier),{}).get('category')!='standard':
            raise ValueError('ORIGINAL_GACHA_ORDINARY_POOL_CATEGORY')
    categories=[]
    for period in selection['weekly']:
        entry=policy.get(str(period['set_id']),{})
        category=entry.get('category')
        if category not in ('standard','festival','seasonal','collaboration'):
            raise ValueError('ORIGINAL_GACHA_WEEK_CATEGORY')
        if category=='seasonal' and not (entry['start']<=period['start']<period['end']<=entry['end']):
            raise ValueError('ORIGINAL_GACHA_SEASON_MISMATCH')
        categories.append(category)
    if any(categories[i:i+4].count('collaboration')>1 for i in range(len(categories))):
        raise ValueError('ORIGINAL_GACHA_COLLABORATION_FREQUENCY')


def gacha_rotation_pack(pack, selection):
    validate_pack(pack)
    if selection.get('schema_version')!=1:raise ValueError('ORIGINAL_GACHA_ROTATION_SCHEMA')
    first,stop=(date.fromisoformat(selection[key]) for key in ('start_date','end_date'))
    pool=selection.get('rotating_set_ids')
    if (not first<stop or not isinstance(pool,list) or len(pool)<4
            or any(type(n) is not int or not 1<=n<=9999 for n in pool)
            or len(set(pool))!=len(pool)):
        raise ValueError('ORIGINAL_GACHA_ROTATION_POOL')
    weekly=selection.get('weekly')
    if not isinstance(weekly,list) or not weekly:raise ValueError('ORIGINAL_GACHA_ROTATION_WEEKS')
    cursor=first
    for period in weekly:
        start,end=(date.fromisoformat(period[key]) for key in ('start','end'))
        identifier=period['set_id']
        if (type(identifier) is not int or not 1<=identifier<=9999 or identifier in pool
                or start>cursor or end<=cursor or start.weekday()!=0
                or end-start!=timedelta(days=7)):
            raise ValueError('ORIGINAL_GACHA_ROTATION_WEEK')
        cursor=end
    if cursor<stop:raise ValueError('ORIGINAL_GACHA_ROTATION_GAP')
    validate_editorial_policy(selection)
    normals=selection.get('normal')
    if (not isinstance(normals,list) or len(normals)!=2 or
            len({n.get('set_id') for n in normals if isinstance(n,dict)})!=2 or
            any(not isinstance(n,dict) or type(n.get('gacha_type')) is not int
                or n['gacha_type']!=0 or n.get('cost')!=0 or n.get('permanent') is not True for n in normals)):
        raise ValueError('ORIGINAL_GACHA_ROTATION_NORMAL')
    revision=selection.get('revision',pack['revision']+1)
    if type(revision) is not int or revision<=pack['revision']:
        raise ValueError('ORIGINAL_GACHA_ROTATION_REVISION')
    result=deepcopy(pack);result['revision']=revision
    result['catalog']['gacha']=[]
    result['schedule']=[entry for entry in result['schedule'] if entry['kind']!='gacha']
    for identifier in pool:
        result['catalog']['gacha'].append(dict(id='kneekura:gacha:rotation-r-'+str(identifier),
            title=selection.get('set_policy',{}).get(str(identifier),{}).get('title','3時間セレクション'),source='kneekura-local',ready=True,
            original=dict(set_id=identifier,gacha_type=1,cost=150,chances=selection['rare_chances'])))
    for weekday in range(7):
        for block in range(8):
            index=(weekday*8+block)*2
            for slot in range(2):
                identifier=pool[(index+slot)%len(pool)]
                result['schedule'].append(dict(id='kneekura:schedule:rare-%d-%d-%d'%(weekday,block,slot),
                    kind='gacha',slot='rare-rotating-'+str(slot+1),priority=1,
                    content_id='kneekura:gacha:rotation-r-'+str(identifier),rule=dict(mode='weekly',
                        valid_from=first.isoformat(),valid_until=stop.isoformat(),weekdays=[weekday],
                        from_time='%02d:00'%(block*3),to_time='%02d:00'%((block*3+3)%24))))
    for index,period in enumerate(weekly):
        identifier='kneekura:gacha:weekly-'+str(index)
        result['catalog']['gacha'].append(dict(id=identifier,title=period['title'],
            source='kneekura-local',ready=True,original=dict(set_id=period['set_id'],
                gacha_type=1,cost=150,chances=selection['rare_chances'])))
        result['schedule'].append(dict(id='kneekura:schedule:rare-weekly-'+str(index),kind='gacha',
            slot='rare-weekly',priority=1,content_id=identifier,rule=dict(mode='once',
                start=period['start']+'T00:00:00+09:00',end=period['end']+'T00:00:00+09:00')))
    rule=dict(mode='once',start=first.isoformat()+'T00:00:00+09:00',
              end=stop.isoformat()+'T00:00:00+09:00')
    for index,normal in enumerate(normals):
        identifier='kneekura:gacha:normal-'+str(index)
        result['catalog']['gacha'].append(dict(id=identifier,title=normal['title'],
            source='kneekura-local',ready=True,original={key:normal[key]
                for key in ('set_id','gacha_type','cost','chances','permanent')}))
        result['schedule'].append(dict(id='kneekura:schedule:normal-'+str(index),kind='gacha',
            slot='normal-'+str(index),priority=1,content_id=identifier,rule=rule))
    identifier='kneekura:notice:gacha-three-slots'
    result['catalog']['notice'].append(dict(id=identifier,title='レアガチャ3枠・にゃんこガチャ開催！',
        source='kneekura-local',ready=True,category='ガチャ',pinned=True,published_at=rule['start'],
        body='3時間ごとに交代するレアガチャ2枠と、週替わりの特選1枠を開催！'
             '\n日本時間の0・3・6・9・12・15・18・21時に交代します。週間特選は月曜0時に交代します。'
             '\n通常の「にゃんこガチャ」とマタタビ入りの「にゃんこガチャ」を常設します。'))
    result['schedule'].append(dict(id='kneekura:schedule:notice-gacha-three',kind='notice',
        slot='notice-gacha',priority=25,content_id=identifier,rule=rule))
    if selection.get('set_policy'):
        result['catalog']['notice'][-1]['body']+='\n通常シリーズを中心に開催し、コラボは特選の低頻度開催にします。季節ガチャは該当時期のみ開催します。'
    return validate_pack(result)


def main():
    import argparse
    import json
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-pack',type=Path,required=True)
    parser.add_argument('--selection',type=Path,required=True)
    parser.add_argument('--out-pack',type=Path,required=True)
    args=parser.parse_args()
    if args.out_pack.exists() or args.out_pack.is_symlink():parser.error('ORIGINAL_GACHA_OUTPUT_EXISTS')
    result=gacha_rotation_pack(json.loads(args.base_pack.read_text(encoding='utf-8')),
        json.loads(args.selection.read_text(encoding='utf-8')))
    with args.out_pack.open('x',encoding='utf-8',newline='\n') as output:
        output.write(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('Authored revision %d: two rotating rare slots, one weekly rare, two permanent normal.'%result['revision'])


if __name__=='__main__':main()
