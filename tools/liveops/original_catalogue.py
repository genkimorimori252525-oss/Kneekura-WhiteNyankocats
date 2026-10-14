"""Bind operations to SHA-pinned owned JP15.7.1 source, never a player SAVE."""
import csv
import io
from pathlib import Path
from zipfile import ZipFile

from tools.battlecats_source import BattleCatsExport
from tools.battlecats_pack import PackReader
from tools.analyze_gacha_foundation import EXACT_JP_15_7_1_EXPORT_SHA256, parse_dataset_rows, parse_unit_rarities
from tools.analyze_login_bonus_foundation import _integer_rows, parse_login_groups
from tools.liveops.original_schedule import ProtocolError

# Known availability families; no story IDs, SoL/UL, TF/modifier pseudo-codes.
MAP_FAMILIES = {1:'S',2:'C',4:'RE',6:'T',7:'V',12:'M',13:'NA',14:'B',16:'D',
                24:'A',25:'H',27:'CA',30:'DM',31:'Q',33:'L',34:'ND',36:'SR',37:'G',39:'PR'}


def owned_catalogue(export_zip: Path, server_cache: Path):
    """Read source once; existing server mirror must match ORIGINAL member MD5s.

    Catalogue readiness concerns actual files. Original UI/battle acceptance is
    a separate PC gate; this function does not mark it completed.
    """
    import hashlib
    from tools.base_mod.recover_offline_original_server_cache import owner_manifest, verify
    import tempfile
    with BattleCatsExport(export_zip,expected_sha256=EXACT_JP_15_7_1_EXPORT_SHA256) as export:
        install=export._require_open()
        # owner_manifest consumes an APK path. Export the pinned private bytes
        # to a temporary file rather than inventing or trusting a local list.
        with tempfile.TemporaryDirectory(prefix='kneekura-ops-owned-') as directory:
            apk=Path(directory)/'split_InstallPack.apk';apk.write_bytes(export._install_bytes)
            expected=owner_manifest(apk)
        assets={}
        for name in install.namelist():
            if not name.startswith('assets/') or not name.endswith('.list'):continue
            family=Path(name).stem
            if f'assets/{family}.pack' not in install.namelist():continue
            pack=export.pack(family)
            for entry in pack.entries:assets[entry.name]=family
        for path in server_cache.glob('*.list'):
            packed=path.with_suffix('.pack')
            if not packed.is_file():continue
            for target in (path,packed):
                if target.is_symlink() or target.name not in expected:
                    raise ProtocolError('ORIGINAL_OPS_SERVER_SOURCE_UNPINNED')
                verify(target,expected[target.name])
            pack=PackReader(family=path.stem,manifest_bytes=path.read_bytes(),
                pack_bytes=packed.read_bytes(),region='jp')
            for entry in pack.entries:assets[entry.name]=path.stem
        data=export.pack('DataLocal')
        unitbuy,_=data.read('unitbuy.csv');rarities=parse_unit_rarities(unitbuy)
        # Original loader 0x5ed65c creates rows from R1 and enriches the SAME
        # row objects with R2/R3. They are not set-ID banks at +1000/+2000.
        # R1 proves a minimum roster for positive probability categories;
        # additional original draw/eligibility rules stay with the native loader.
        payload,_=data.read('GatyaDataSetR1.csv')
        sets={index:members for index,members in enumerate(parse_dataset_rows(payload))}
        options,_=data.read('GatyaData_Option_SetR.tsv')
        banners={}
        for row in csv.DictReader(io.StringIO(options.decode('utf-8-sig')),delimiter='\t'):
            try:
                identifier=int(row['GatyaSetID'])
                if int(row['BannerON_OFF'])!=1:continue
                members=sets.get(identifier,[])
                if not members:continue
                banners[identifier]=dict(members=members,
                    rarities=sorted({rarities[unit] for unit in members if unit in rarities}),
                    ticket=int(row['ItemID_Ticket']))
            except (ValueError,KeyError):continue
        payload,proof=data.read('DailyLoginEventData.csv');login=[]
        for row in _integer_rows(payload):
            identifier=row[0];groups=parse_login_groups(row)[1]
            # 900/system and 901/902 comeback use separate original flags.
            if identifier in (900,901,902) or len(groups)<6 or len(groups)>365:continue
            if any(g[0]<=0 or any(g[2+3*i]!=0 for i in range(g[0])) for g in groups):continue
            required=[f'DailyLoginEventText_{identifier:03d}_ja.tsv']
            if row[5]>=0:required.extend((f'loginbg_{row[5]:03d}.png','loginbg.imgcut'))
            if all(name in assets for name in required):
                login.append(dict(template_id=identifier,days=len(groups)))
        maps={}
        for category,code in MAP_FAMILIES.items():
            prefix=f'MapStageData{code}_'
            for entry in data.entries:
                if not entry.name.startswith(prefix) or not entry.name.endswith('.csv'):continue
                try:index=int(entry.name[len(prefix):-4])
                except ValueError:continue
                if not 0<=index<1000:continue
                # Map metadata alone is not sufficient: require a battle CSV.
                stage_prefixes=(f'stageR{code}{index:03d}_',f'stage{code}{index:03d}_')
                if any(name.startswith(stage_prefixes) and name.endswith('.csv') for name in assets):
                    maps[category*1000+index]=entry.name
        missions,_=data.read('Mission_Data.csv')
        mission_ids={int(row['mission_id']) for row in csv.DictReader(io.StringIO(missions.decode('utf-8-sig')))}
        monthly,_=data.read('Mission_Monthly.csv')
        monthly_ids={int(row['id']) for row in csv.DictReader(io.StringIO(monthly.decode('utf-8-sig')))}
        return dict(source_export_sha256=EXACT_JP_15_7_1_EXPORT_SHA256,
            asset_names=assets,gacha=banners,maps=maps,mission_ids=mission_ids,
            monthly_mission_ids=monthly_ids,login_pool=login,
            login_source_sha256=proof.payload_sha256,original_ui_accepted=False)


def bind_catalogue(pack, catalogue):
    if catalogue.get('source_export_sha256')!=EXACT_JP_15_7_1_EXPORT_SHA256:
        raise ProtocolError('ORIGINAL_OPS_SOURCE_EXPORT')
    bindings={}
    for kind in ('gacha','stage','event','mission'):
        for record in pack['catalog'][kind]:
            if not record['ready']:continue
            definition=record.get('original')
            if not isinstance(definition,dict):raise ProtocolError('ORIGINAL_OPS_NATIVE_BINDING')
            binding=dict(definition,kind=kind)
            if kind=='gacha':
                source=catalogue['gacha'].get(binding.get('set_id'))
                if source is None or source['ticket']!=21:raise ProtocolError('ORIGINAL_OPS_GACHA_SOURCE')
                rarity_index=(0,2,3,4,5)
                chances=binding.get('chances')
                if not isinstance(chances,list) or len(chances)!=5:
                    raise ProtocolError('ORIGINAL_OPS_GACHA_PROBABILITIES')
                if any(chance and rarity not in source['rarities'] for rarity,chance in zip(rarity_index,chances)):
                    raise ProtocolError('ORIGINAL_OPS_GACHA_EMPTY_RARITY')
            else:
                ids=binding.get('native_ids')
                if not isinstance(ids,list) or not ids:raise ProtocolError('ORIGINAL_OPS_NATIVE_IDS')
                known=catalogue['maps'] if kind!='mission' else (
                    catalogue['mission_ids'] | catalogue['monthly_mission_ids'])
                if any(type(identifier) is not int or identifier not in known for identifier in ids):
                    raise ProtocolError('ORIGINAL_OPS_MISSING_MAP_OR_MISSION')
            bindings[record['id']]=binding
    return bindings
