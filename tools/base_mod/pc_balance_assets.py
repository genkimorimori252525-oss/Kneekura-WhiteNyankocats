"""Exact private PC data overlay: two approved forms and seven Godzilla assets.

Pins were derived locally from the owned JP15.7.1 export and four verified
Server files. No original bytes are stored in this source file.
"""
import hashlib
from pathlib import Path
import tempfile
from zipfile import ZipFile

from tools.battlecats_pack import PackReader
from tools.base_mod.build_update_101_unsigned import validate_form_delta, SOURCE_UNIT_SHA

# Original enemy550's native timings, not guessed from animation key density.
PC_RIG_FIELDS = {4:120, 13:130, 61:170, 62:210}


def validate_pc_form_delta(original, candidate, *, file_name, original_sha):
    if file_name != 'unit703.csv':
        return validate_form_delta(original,candidate,file_name=file_name,original_sha=original_sha)
    before=original.splitlines(keepends=True)
    after=candidate.splitlines(keepends=True)
    fields=after[0].rstrip(b'\r\n').split(b',')
    old=before[0].rstrip(b'\r\n').split(b',')
    if len(fields)!=len(old): raise ValueError('PC_RIG_CSV_COLUMN_COUNT_CHANGED')
    ending=after[0][len(after[0].rstrip(b'\r\n')):]
    for col,value in PC_RIG_FIELDS.items():
        if fields[col]!=str(value).encode('ascii'): raise ValueError('PC_RIG_TIMING_CHANGED')
        fields[col]=b'180' if col==4 else old[col]
    after[0]=b','.join(fields)+ending
    proof=validate_form_delta(original,b''.join(after),file_name=file_name,original_sha=original_sha)
    proof['enemy550_hit_timings']=[130,170,210]
    proof['frequency_raw']=120
    return proof

PAYLOAD_SHA256 = {
    '702_f.imgcut':'6670e6c1104d420e7a519ed2aadfb58a559a113feb041ae1c22aeac3c617bf43',
    '702_f.mamodel':'c05d62c27930517a306545b92b042399bf73ae8188aff01132c10da393455554',
    '702_f.png':'f168a34a23d8097f6a8b6cd5f2eb6daab8135fad3009205880155a94df15526d',
    '702_f00.maanim':'d38726ad79a09a1baf5e64018b49bd9be6c47755f777fe9be8a607c4853a59ce',
    '702_f01.maanim':'dd295f3f53d086352e57b1293e42651912598addd9e0d377a71cf7819454ffed',
    '702_f02.maanim':'2bca2d1c9fd9dc88e64e39771514686dcc20141871201dfdb413e91c91e5e0d8',
    '702_f03.maanim':'b5afe2797db1b1547f0e3fbc3bc00ec79faf1d20963f6de823ed887bafa411f6',
    'unit289.csv':'e26afee204527508a0f8e06faa04a4431cf508ea30d251d2c3da917b70c6185a',
    'unit703.csv':'9fc373f2177dfe0017dc3c20d98c50603325aa7a740aee9d271c7f772af36e56',
}
PAIR = ('assets/DownloadLocal.list','assets/DownloadLocal.pack')


def reflect_godzilla_rotations(name: str, raw: bytes) -> bytes:
    """Complete the validated 702_f root reflection, including animated joints.

    The renderer inherits signed size separately from rotation. Negating root
    X alone leaves R(angle) M(x); negating every joint angle gives M(x) R(angle).
    Timing, easing, translations, texture, pivots and model footer stay intact.
    Input is the seven-file rig already validated by the conversion pipeline.
    """
    from tools.base_mod.prepare_godzilla_ally_preview import _newline_of
    if name not in ('702_f.mamodel', *(f'702_f0{i}.maanim' for i in range(4))):
        return raw
    lines=raw.splitlines(keepends=True)

    def negate(at, column):
        fields=lines[at].rstrip(b'\r\n').split(b',')
        value=int(fields[column])
        if value:
            fields[column]=str(-value).encode('ascii')
            lines[at]=b','.join(fields)+_newline_of(lines[at])

    count=int(lines[2])
    if name.endswith('.mamodel'):
        for at in range(3,3+count): negate(at,10)
    else:
        at=3
        for _ in range(count):
            kind=int(lines[at].split(b',')[1])
            keys=int(lines[at+1])
            if kind==11:
                for key in range(at+2,at+2+keys): negate(key,1)
            at+=2+keys
    return b''.join(lines)


def ensure_godzilla_ally_anchors(raw: bytes) -> bytes:
    """Keep the enemy's visual origin and add the original ally's neutral point.

    JP15.7.1's ally path selects configuration flags & 1. Enemy550 supplies
    only config0; original 702_f/702_c supply config1=(0,0,0,0,5,0).
    Without it, a later battle update reads past the configuration array.
    """
    from tools.base_mod.prepare_godzilla_ally_preview import _newline_of
    lines=raw.splitlines(keepends=True)
    at=4+int(lines[2])
    if len(lines)!=at+2 or int(lines[at])!=1:
        raise ValueError('PC_GODZILLA_ENEMY_ANCHOR_LAYOUT_CHANGED')
    anchor=lines[at+1].rstrip(b'\r\n').split(b',',6)
    if len(anchor)!=7 or [int(v) for v in anchor[:2]]!=[0,0]:
        raise ValueError('PC_GODZILLA_ROOT_ANCHOR_CHANGED')
    ending=_newline_of(lines[at]) or b'\n'
    lines[at]=b'2'+ending
    if not _newline_of(lines[-1]): lines[-1]+=ending
    lines.append(b'0,0,0,0,5,0,'+anchor[6]+ending)
    return b''.join(lines)


def load_pinned_assets(directory: Path):
    if directory.is_symlink() or not directory.is_dir() or {p.name for p in directory.iterdir()} != set(PAYLOAD_SHA256):
        raise ValueError('PC_BALANCE_ASSET_SET_CHANGED')
    out={}
    for name,digest in PAYLOAD_SHA256.items():
        path=directory/name
        if path.is_symlink() or not path.is_file() or not 0<path.stat().st_size<64*1024*1024:
            raise ValueError('PC_BALANCE_PAYLOAD_UNSAFE')
        data=path.read_bytes()
        if hashlib.sha256(data).hexdigest()!=digest:
            raise ValueError('PC_BALANCE_PAYLOAD_SHA_CHANGED')
        out[name]=data
    return out


def prepare_assets(owner_export: Path, server_source: Path, parent: Path):
    """Reproducibly derive private payloads; never fetch or alter original files."""
    from tools.battlecats_source import BattleCatsExport
    from tools.base_mod.build_offline_max_save import EXPORT_SHA256
    from tools.base_mod.build_update_101_unsigned import TARGET
    from tools.base_mod.fetch_godzilla_server_assets import complete_owner_private_godzilla_pipeline
    parent.mkdir(parents=True,exist_ok=True)
    if parent.is_symlink(): raise ValueError('PC_BALANCE_PRIVATE_CACHE_LINK_REFUSED')
    output=parent/'approved-v5'
    if output.exists():
        load_pinned_assets(output)
        return output
    with tempfile.TemporaryDirectory(prefix='.pc-balance-',dir=parent) as temporary:
        work=Path(temporary)
        complete_owner_private_godzilla_pipeline(server_source,server_output=work/'server',
            rig_output=work/'rig',ally_output=work/'ally',resource_output=work/'native-candidate',
            private_root=work)
        staged=work/'approved'
        staged.mkdir()
        for name in PAYLOAD_SHA256.keys()-SOURCE_UNIT_SHA.keys():
            payload=reflect_godzilla_rotations(name,(work/'ally'/name).read_bytes())
            if name=='702_f.mamodel': payload=ensure_godzilla_ally_anchors(payload)
            (staged/name).write_bytes(payload)
        with BattleCatsExport(owner_export,region='jp',expected_sha256=EXPORT_SHA256) as export:
            data=export.pack('DataLocal')
            for name,(form,values) in TARGET.items():
                if name=='unit703.csv': values={**values,**PC_RIG_FIELDS}
                original,_=data.read(name)
                rows=original.splitlines(keepends=True)
                row=rows[form]
                ending=row[len(row.rstrip(b'\r\n')):]
                fields=row.rstrip(b'\r\n').split(b',')
                for col,value in values.items(): fields[col]=str(value).encode('ascii')
                rows[form]=b','.join(fields)+ending
                candidate=b''.join(rows)
                validate_pc_form_delta(original,candidate,file_name=name,original_sha=SOURCE_UNIT_SHA[name])
                (staged/name).write_bytes(candidate)
        load_pinned_assets(staged)
        if output.exists(): raise ValueError('PC_BALANCE_CACHE_APPEARED_NO_OVERWRITE')
        staged.rename(output)
    return output


def verify_overlay(original_apk: Path, candidate_apk: Path):
    with ZipFile(original_apk) as before, ZipFile(candidate_apk) as after:
        original=PackReader('DownloadLocal',before.read(PAIR[0]),before.read(PAIR[1]),region='jp')
        candidate=PackReader('DownloadLocal',after.read(PAIR[0]),after.read(PAIR[1]),region='jp')
        data=PackReader('DataLocal',before.read('assets/DataLocal.list'),before.read('assets/DataLocal.pack'),region='jp')
        original_names={entry.name for entry in original.entries}
        candidate_names={entry.name for entry in candidate.entries}
        if original_names & PAYLOAD_SHA256.keys() or candidate_names != original_names|PAYLOAD_SHA256.keys():
            raise ValueError('PC_BALANCE_OVERLAY_KEY_SET_CHANGED')
        if len(candidate.entries)!=len(original.entries)+len(PAYLOAD_SHA256):
            raise ValueError('PC_BALANCE_OVERLAY_DUPLICATE_KEYS')
        for name in original_names:
            if candidate.read(name)[0]!=original.read(name)[0]:
                raise ValueError('PC_BALANCE_ORIGINAL_OVERLAY_ENTRY_CHANGED')
        for name,digest in PAYLOAD_SHA256.items():
            value=candidate.read(name)[0]
            if hashlib.sha256(value).hexdigest()!=digest:
                raise ValueError('PC_BALANCE_PAYLOAD_SHA_CHANGED')
            if name in SOURCE_UNIT_SHA:
                validate_pc_form_delta(data.read(name)[0],value,file_name=name,original_sha=SOURCE_UNIT_SHA[name])
        for entry in ('assets/DataLocal.list','assets/DataLocal.pack'):
            if before.read(entry)!=after.read(entry): raise ValueError('PC_BALANCE_DATALOCAL_CHANGED')
    return dict(schema='pc-pinned-balance-overlay-v1',payload_sha256=PAYLOAD_SHA256,
                original_overlay_entries_unchanged=len(original_names),datalocal_unchanged=True,
                original_form1_and_other_unit_rows_unchanged=True,
                actual_game_damage_and_castle_hook_proven=False)
