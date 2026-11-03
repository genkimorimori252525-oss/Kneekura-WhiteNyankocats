"""Inventory availability separately from native eligibility and play evidence.

Inputs are metadata extracted from the owner's SHA-verified export and the
public index researched by Luna. Unknowns never become unlock instructions.
"""
import re


def audit_stage_policy(metadata,web_records,all_map_hashes,pack):
    web={int(r['nativeID'][1:]):r for r in web_records
         if re.fullmatch(r's\d{5}',r['nativeID'])}
    records={r['id']:r for k in ('stage','event') for r in pack['catalog'][k]}
    scheduled={n for r in records.values() for n in r['original']['native_ids']}
    known={r['native_id'] for r in metadata}
    if scheduled-known:raise ValueError('STAGE_POLICY_MAP_NOT_OWNED')
    if any(r['slot']=='rotation-20' for r in pack['schedule']):
        raise ValueError('STAGE_POLICY_UNRESTRICTED_ROTATION')
    categories={}
    for record in records.values():
        for n in record['original']['native_ids']:
            categories.setdefault(n,set()).add(record.get('program_category','UNKNOWN'))
    rows=[]
    for original in sorted(metadata,key=lambda r:r['native_id']):
        n=original['native_id'];w=web.get(n);family=n//1000
        handling=('native-owned-map-and-identification' if family==25 else
                  'native-ex-chain' if family==4 else
                  'native-catamin-cost-and-gates' if family==14 else
                  'collaboration-campaign' if family==2 else
                  'scheduled-native-gates' if n in scheduled else 'not-scheduled')
        rows.append(dict(native_id=n,title=original['title'],
            metadata_asset=original['metadata_asset'],metadata_sha256=original['source_sha256'],
            native_display_condition_code=original['header'][3] if len(original['header'])>3 else None,
            native_play_condition_code=original['header'][4] if len(original['header'])>4 else None,
            source_category=w['categories'] if w else ['UNKNOWN'],
            source_category_status='MATCHED_INDEX' if w else 'UNKNOWN',
            recurrence_status='INDEX_RULE_FOUND' if w and w.get('scheduleEvidence') else 'UNKNOWN',
            handling=handling,scheduled=n in scheduled,
            operator_categories=sorted(categories.get(n,[])),
            native_eligibility='PRESERVED_NOT_FULLY_DECODED',play_acceptance='NOT_ALL_PLAYED'))
    return dict(schema_version=1,stage_unlocks_modified=False,free_rotation_removed=True,
        schedulable_map_count=len(rows),public_index_matched=sum(r['source_category_status']=='MATCHED_INDEX' for r in rows),
        public_index_unknown=sum(r['source_category_status']=='UNKNOWN' for r in rows),
        all_original_map_metadata_count=len(all_map_hashes),all_original_map_hashes=all_map_hashes,
        scheduled_unique_maps=len(scheduled),maps=rows,
        limitation='Index coverage is not individual unlock verification; UNKNOWN entries are not newly scheduled.')
