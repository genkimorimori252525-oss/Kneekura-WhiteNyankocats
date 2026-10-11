"""One-time profile for an independently created PC JP15.7.1 save.

The GPLv3 BCSFE reference stays an external, pinned development tool; its code,
dependencies and owner save are not included in this repository or the APK.
No fixed offset from the older 496340-byte save family is reused.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sys

from tools.battlecats_source import BattleCatsExport
from tools.base_mod.build_offline_max_save import EXPORT_SHA256, MAX_VALUES, _verify_jp_hash
from tools.base_mod.build_post_eoc_save import _derive_ownership_contract
from tools.base_mod.level_cap_unlock import _derive_targets

PARSER_COMMIT = '85fb94cbf00c6a74dbef58932610fb94ec8f7495'
PARSER_TREE_SHA256 = '5fb74c23f0c25466256eb2a8327a449db2e942f94e2f49fbb46dbfb124ea9c01'
STORY_CHAPTERS = (0, 1, 2, 4)  # index3 is the original historical gap.
ARRAY_LENGTHS = dict(catfruit=29, catseyes=6, catamins=3, lucky_tickets=55,
                     labyrinth_medals=4, treasure_chests=42)
SCALARS = ('catfood', 'xp', 'np', 'normal_tickets', 'rare_tickets',
           'platinum_tickets', 'legend_tickets', 'platinum_shards',
           'leadership', 'hundred_million_ticket')


def any_nonzero(value):
    if isinstance(value,list): return any(any_nonzero(v) for v in value)
    if isinstance(value,dict): return any(any_nonzero(v) for v in value.values())
    return bool(value)


def pristine_events(value):
    if isinstance(value,dict):
        return all(not (key in ('clear_progress','stages','chapter_completion_count','stages_reward_claimed')
                        and any_nonzero(v)) and pristine_events(v) for key,v in value.items())
    if isinstance(value,list): return all(pristine_events(v) for v in value)
    return True


def verify_unchanged(before, after, path=()):
    """Refuse any semantic change outside the explicitly requested fields.

    Never include actual field values in an exception or receipt.
    """
    if before == after:
        return
    if isinstance(before, dict) and isinstance(after, dict) and before.keys() == after.keys():
        for key in before:
            verify_unchanged(before[key], after[key], path+(key,))
        return
    if isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        for i, (left, right) in enumerate(zip(before, after)):
            verify_unchanged(left, right, path+(i,))
        return
    if path == ('talent_orbs',):
        return  # variable section, independently checked against equipmentlist.json.
    if len(path) == 1 and path[0] in SCALARS+('tutorial_state','koreaSuperiorTreasureState','ui6','cleared_eoc_1'):
        return
    if len(path) == 2 and path[0] in ARRAY_LENGTHS and isinstance(path[1], int):
        return
    if path in (('menu_unlocks',0), ('new_dialogs_2',1), ('new_dialogs_2',5), ('ototo','engineers')):
        return
    if len(path) == 3 and path[:2] == ('ototo','base_materials') and isinstance(path[2], int):
        return
    if len(path) == 4 and path[:2] == ('battle_items','items') and path[3] == 'amount':
        return
    if len(path) == 4 and path[:2] == ('cats','cats') and path[3] in ('unlocked','gatya_seen'):
        return
    if len(path) == 5 and path[:2] == ('cats','cats') and path[3:] == ('max_upgrade_level','base'):
        return
    if len(path) == 3 and path[0] == 'story' and path[1] in STORY_CHAPTERS and path[2] == 'progress':
        return
    if (len(path) == 5 and path[0] == 'story' and path[1] in STORY_CHAPTERS
            and path[2] == 'stages' and isinstance(path[3],int) and 0 <= path[3] < 48
            and path[4] in ('clear_times','treasure')):
        return
    raise ValueError('PC_PROFILE_UNAPPROVED_FIELD_CHANGE')


def apply_policy(save, owned, excluded, targets, orb_ids, orb_factory):
    if (len(save.cats.cats) != 882 or len(save.story.chapters) != 10
            or owned & excluded or not owned.issubset(range(882))
            or any(cat.unlocked for cat in save.cats.cats if cat.id in excluded)
            or any(c.progress or any(s.clear_times or s.treasure for s in c.stages)
                   for c in save.story.chapters)):
        raise ValueError('PC_PROFILE_NOT_PRISTINE')
    for name, length in ARRAY_LENGTHS.items():
        if len(getattr(save,name)) != length:
            raise ValueError('PC_PROFILE_RESOURCE_LAYOUT_CHANGED')
    if (len(save.ototo.base_materials.materials) != 16 or len(save.battle_items.items) != 6
            or len(save.menu_unlocks)<1 or len(save.new_dialogs_2)<6):
        raise ValueError('PC_PROFILE_RESOURCE_LAYOUT_CHANGED')
    for ci in STORY_CHAPTERS:
        chapter=save.story.chapters[ci]
        if len(chapter.stages) != 51:
            raise ValueError('PC_PROFILE_STORY_LAYOUT_CHANGED')
        chapter.progress=48
        for stage in chapter.stages[:48]:
            stage.clear_times=1
            stage.treasure=3
    for cat in save.cats.cats:
        if cat.id in owned:
            cat.unlocked=cat.gatya_seen=1
        if cat.id in targets:
            cat.max_upgrade_level.base=max(cat.max_upgrade_level.base, targets[cat.id]['required_increment'])
    for name in SCALARS:
        setattr(save,name,MAX_VALUES[name])
    for name, length in ARRAY_LENGTHS.items():
        setattr(save,name,[MAX_VALUES[name]]*length)
    for item in save.battle_items.items:
        item.amount=MAX_VALUES['battle_items']
    for material in save.ototo.base_materials.materials:
        material.amount=MAX_VALUES['base_materials']
    save.ototo.engineers=MAX_VALUES['engineers']
    save.talent_orbs.orbs={i:orb_factory(i,MAX_VALUES['talent_orbs']) for i in orb_ids}
    save.tutorial_state=max(save.tutorial_state,1)
    save.koreaSuperiorTreasureState=max(save.koreaSuperiorTreasureState,2)
    save.ui6=max(save.ui6,1)
    save.cleared_eoc_1=1
    save.menu_unlocks[0]=max(save.menu_unlocks[0],1)
    for i in (1,5): save.new_dialogs_2[i]=max(save.new_dialogs_2[i],2)


def load_reference(parser_source: Path, dependencies: Path, private_state: Path):
    digest=hashlib.sha256()
    for file in sorted(parser_source.rglob('*.py')):
        digest.update(file.relative_to(parser_source).as_posix().encode()+b'\0'+file.read_bytes())
    if digest.hexdigest() != PARSER_TREE_SHA256:
        raise ValueError('PC_PROFILE_REFERENCE_SOURCE_CHANGED')
    def forbid_network(event,args):
        if event.startswith('socket.'):
            raise RuntimeError('PC_PROFILE_REFERENCE_NETWORK_FORBIDDEN')
    sys.addaudithook(forbid_network)
    sys.path[:0]=[str(parser_source.resolve()),str(dependencies.resolve())]
    from bcsfe import core
    if not Path(core.__file__).resolve().is_relative_to(parser_source.resolve()):
        raise ValueError('PC_PROFILE_REFERENCE_IMPORT_OUTSIDE_PIN')
    core.set_data_dir_path(core.Path(str(private_state.resolve())))
    return core


def build_profile(source: bytes, owner_export: Path, core):
    _verify_jp_hash(source)
    if int.from_bytes(source[:4],'little') != 150700:
        raise ValueError('PC_PROFILE_GAME_VERSION_CHANGED')
    save=core.SaveFile(core.Data(source),load=False)
    save.load()
    if save.to_data().get_bytes() != source:
        raise ValueError('PC_PROFILE_REFERENCE_ROUNDTRIP_NOT_IDENTICAL')
    if not re.fullmatch(r'kneekura-local-[0-9a-f]{32}',save.inquiry_code):
        raise ValueError('PC_PROFILE_FOREIGN_ACCOUNT_REFUSED')
    # Event history and drop claims must be empty; preserve the complete objects.
    if not pristine_events(save.event_stages.serialize()) or any_nonzero(save.unit_drops):
        raise ValueError('PC_PROFILE_NOT_PRISTINE_EVENT_HISTORY')
    owned,excluded,legends,ownership=_derive_ownership_contract(owner_export)
    targets,caps=_derive_targets(owner_export)
    with BattleCatsExport(owner_export,region='jp',expected_sha256=EXPORT_SHA256) as export:
        orb_bytes,provenance=export.pack('DataLocal').read('equipmentlist.json')
    equipment=json.loads(orb_bytes.decode('utf-8-sig'))['ID']
    # Native equipment ID is the table index, not gradeID (which is shared).
    if not isinstance(equipment,list) or len(equipment) != 310 or any(
            not isinstance(row,dict) or set(row) not in (
                {'gradeID','content','value','attribute'}, {'gradeID','content','value'})
            for row in equipment):
        raise ValueError('PC_PROFILE_EQUIPMENT_CONTRACT_CHANGED')
    orb_ids=list(range(len(equipment)))
    before=copy.deepcopy(save.to_dict())
    apply_policy(save,set(owned),set(excluded),targets,orb_ids,core.TalentOrb)
    expected=copy.deepcopy(save.to_dict())
    verify_unchanged(before,expected)
    result=save.to_data().get_bytes()
    _verify_jp_hash(result)
    reread=core.SaveFile(core.Data(result),load=False)
    reread.load()
    if reread.to_dict() != expected or reread.to_data().get_bytes() != result:
        raise ValueError('PC_PROFILE_OUTPUT_REREAD_CHANGED')
    if any(min(targets[i]['original_max']+reread.cats.cats[i].max_upgrade_level.base,
               targets[i]['native_hard_max']) != 50 for i in legends):
        raise ValueError('PC_PROFILE_LEGEND_RARE_CAP_CHANGED')
    report=dict(schema='kneekura-pc-initial-profile-v1',source_sha256=hashlib.sha256(source).hexdigest(),
                output_sha256=hashlib.sha256(result).hexdigest(),source_size=len(source),output_size=len(result),
                reference_commit=PARSER_COMMIT,reference_roundtrip_identical=True,
                account_preserved=True,unapproved_fields_unchanged=True,
                story_chapter_indices=list(STORY_CHAPTERS),stages_per_chapter=48,treasure_grade=3,
                unlisted_story_and_event_history_unchanged=True,ownership=ownership,level_caps=caps,
                current_levels_plus_forms_unchanged=True,resource_policy=MAX_VALUES,
                resource_categories=len(MAX_VALUES),talent_orb_count=len(orb_ids),
                equipmentlist_sha256=provenance.payload_sha256,automatic_refill=False)
    return result,report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source','owner-export','parser-source','parser-dependencies','private-state','output','receipt'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args(argv)
    if args.output.exists() or args.receipt.exists() or args.source.resolve()==args.output.resolve():
        raise ValueError('PC_PROFILE_EXISTING_FILE_OVERWRITE_REFUSED')
    core=load_reference(args.parser_source,args.parser_dependencies,args.private_state)
    result,report=build_profile(args.source.read_bytes(),args.owner_export,core)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('xb') as out: out.write(result)
    with args.receipt.open('x',encoding='utf-8') as out: json.dump(report,out,ensure_ascii=False,indent=2)
    print(json.dumps(report,ensure_ascii=False))
    return 0


if __name__=='__main__': raise SystemExit(main())
