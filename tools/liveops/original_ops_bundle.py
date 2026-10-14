"""Immutable original-reader assets. No player SAVE, initial grants or transport."""
import base64
from datetime import datetime
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

from tools.liveops.original_schedule import (
    GAME_VERSION, ORIGINAL_OWNER_SAVE, EventWindow, ProtocolError, stream,
    gacha_row, stage_row, item_row,
)
from tools.localcore.ops_calendar import JST

ASSET_ENTRY = 'assets/kneekura-original-ops-v1.json'
SOURCE_NATIVE_SHA256 = '333d2974ab2ff881fd70087fd62dea7d12d82addbc55cab2f2a675ad67e3a7e2'
FILES = frozenset(('sale.tsv', 'gatya.tsv', 'item.tsv'))
MAX_BUNDLE = 8*1024**2


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ProtocolError('ORIGINAL_OPS_DUPLICATE_KEY')
        result[key] = value
    return result


def _number(text):
    if not isinstance(text, str) or not text.isascii() or not text.isdecimal():
        raise ProtocolError('ORIGINAL_OPS_WIRE_NUMBER')
    return int(text)


def _timestamp(date, clock):
    if len(date) != 8 or len(clock) > 4:
        raise ProtocolError('ORIGINAL_OPS_WIRE_TIME')
    number = _number(clock)
    return datetime.strptime(date, '%Y%m%d').replace(
        hour=number//100, minute=number%100, tzinfo=JST)


def _validate_stream(name, payload):
    if not isinstance(payload, bytes) or len(payload) > 2*1024**2:
        raise ProtocolError('ORIGINAL_OPS_STREAM_TOO_LARGE')
    text = payload.decode('utf-8', errors='strict')
    if not text.startswith('[start]\n') or not text.endswith('[end]\n'):
        raise ProtocolError('ORIGINAL_OPS_STREAM_SENTINEL')
    rows = text[len('[start]\n'):-len('[end]\n')]
    lines = [] if not rows else rows[:-1].split('\n')
    if rows and not rows.endswith('\n'):
        raise ProtocolError('ORIGINAL_OPS_STREAM_LINE_END')
    for row in lines:
        fields = row.split('\t')
        if len(fields) < 10:
            raise ProtocolError('ORIGINAL_OPS_STREAM_ROW')
        window = EventWindow(_timestamp(fields[0],fields[1]), _timestamp(fields[2],fields[3]))
        if fields[4:8] != [str(GAME_VERSION),str(GAME_VERSION),'0','0']:
            raise ProtocolError('ORIGINAL_OPS_UNSUPPORTED_FILTER')
        values = fields[8:]
        if name == 'sale.tsv':
            count = _number(values[0])
            if count != len(values)-1:raise ProtocolError('ORIGINAL_OPS_MAP_COUNT')
            expected = stage_row(window, [_number(v) for v in values[1:]])
        elif name == 'gatya.tsv':
            if len(values) != 17 or values[:2] != ['1','1'] or values[4:6] != ['0','0']:
                raise ProtocolError('ORIGINAL_OPS_GACHA_SHAPE')
            expected = gacha_row(window, _number(values[2]), cost=_number(values[3]),
                chances=[_number(v) for v in values[6:16:2]],
                guaranteed=[_number(v) for v in values[7:16:2]], message=values[16])
        else:
            if len(values) != 8 or values[5:7] != ['0','0'] or values[7] not in ('0','1'):
                raise ProtocolError('ORIGINAL_OPS_ITEM_SHAPE')
            expected = item_row(window, *[_number(v) for v in values[:3]],
                title=values[3], message=values[4], everyday=values[7]=='1')
        if row != expected:raise ProtocolError('ORIGINAL_OPS_NONCANONICAL_ROW')
    if payload != stream(lines):raise ProtocolError('ORIGINAL_OPS_NONCANONICAL_STREAM')


def validate_bundle(data):
    if not isinstance(data, bytes) or not 0 < len(data) <= MAX_BUNDLE:
        raise ProtocolError('ORIGINAL_OPS_BUNDLE_SIZE')
    bundle = json.loads(data.decode('utf-8'), object_pairs_hook=_unique_object)
    if not isinstance(bundle, dict):raise ProtocolError('ORIGINAL_OPS_BUNDLE_OBJECT')
    contract = {'schema_version':1, 'game_version':GAME_VERSION,
                'owner_save':ORIGINAL_OWNER_SAVE, 'source_native_sha256':SOURCE_NATIVE_SHA256}
    for key, value in contract.items():
        if type(bundle.get(key)) is not type(value) or bundle[key] != value:
            raise ProtocolError('ORIGINAL_OPS_BUNDLE_CONTRACT')
    for key in ('revision','start_epoch_ms','end_epoch_ms'):
        if type(bundle.get(key)) is not int or not 0 < bundle[key] <= 2**63-1:
            raise ProtocolError('ORIGINAL_OPS_BUNDLE_INTEGER')
    if bundle['start_epoch_ms'] >= bundle['end_epoch_ms']:
        raise ProtocolError('ORIGINAL_OPS_BUNDLE_WINDOW')
    files = bundle.get('server_files')
    if not isinstance(files,dict) or set(files) != FILES:
        raise ProtocolError('ORIGINAL_OPS_STREAM_SET')
    for name, encoded in files.items():
        if not isinstance(encoded,str):raise ProtocolError('ORIGINAL_OPS_BASE64')
        _validate_stream(name, base64.b64decode(encoded, validate=True))
    if 'login_rotation' in bundle:
        validate_login_rotation(bundle['login_rotation'])
    if 'notices' in bundle:
        validate_notices(bundle['notices'])
    return bundle


def validate_login_rotation(configuration):
    if (not isinstance(configuration,dict)
            or configuration.get('rotation_id') != 'kneekura-original-login-v1'):
        raise ProtocolError('ORIGINAL_LOGIN_ROTATION_ID')
    pool = configuration.get('pool')
    if not isinstance(pool,list) or not 5 <= len(pool) <= 159:
        raise ProtocolError('ORIGINAL_LOGIN_POOL_SIZE')
    ids=set()
    for record in pool:
        if not isinstance(record,dict):raise ProtocolError('ORIGINAL_LOGIN_POOL_ENTRY')
        template,days=record.get('template_id'),record.get('days')
        if (type(template) is not int or not (900<=template<=999 or 35000<=template<=2**31-1)
                or template in ids or type(days) is not int or not 6<=days<=365):
            raise ProtocolError('ORIGINAL_LOGIN_POOL_ENTRY')
        ids.add(template)
    bags=configuration.get('shuffle_bags')
    if not isinstance(bags,list) or not 1<=len(bags)<=64:
        raise ProtocolError('ORIGINAL_LOGIN_BAG_SIZE')
    for bag in bags:
        if (not isinstance(bag,list) or len(bag)!=len(ids)
                or not all(type(v) is int for v in bag) or set(bag)!=ids):
            raise ProtocolError('ORIGINAL_LOGIN_BAG_ENTRY')
    return configuration


def build_login_rotation(pool, *, seed, cycles=32):
    from tools.liveops.login_scheduler import _new_bag
    if not isinstance(seed,str) or not 1<=len(seed)<=128 or type(cycles) is not int or not 1<=cycles<=64:
        raise ProtocolError('ORIGINAL_LOGIN_BAG_SEED')
    configuration=dict(rotation_id='kneekura-original-login-v1',pool=pool,
        shuffle_bags=[_new_bag(sorted(r['template_id'] for r in pool),seed=seed,
            cycle=cycle,excluded=set()) for cycle in range(cycles)])
    return validate_login_rotation(configuration)


def validate_notices(notices):
    if not isinstance(notices,list) or len(notices)>1000:
        raise ProtocolError('ORIGINAL_OPS_NOTICE_LIST')
    for record in notices:
        if not isinstance(record,dict):raise ProtocolError('ORIGINAL_OPS_NOTICE_ENTRY')
        for key in ('start_epoch_ms','end_epoch_ms'):
            if type(record.get(key)) is not int or not 0<record[key]<=2**63-1:
                raise ProtocolError('ORIGINAL_OPS_NOTICE_TIME')
        if record['start_epoch_ms']>=record['end_epoch_ms']:
            raise ProtocolError('ORIGINAL_OPS_NOTICE_WINDOW')
        for key,limit in [('title',1024),('body',12000)]:
            text=record.get(key)
            if not isinstance(text,str) or not 1<=len(text)<=limit or '\0' in text:
                raise ProtocolError('ORIGINAL_OPS_NOTICE_TEXT')
    return notices


def build_bundle(window, *, revision, files, login_rotation=None, notices=None):
    if not isinstance(window,EventWindow) or not isinstance(files,dict) or set(files) != FILES:
        raise ProtocolError('ORIGINAL_OPS_BUILD_CONTRACT')
    bundle = dict(schema_version=1, game_version=GAME_VERSION, owner_save=ORIGINAL_OWNER_SAVE,
        source_native_sha256=SOURCE_NATIVE_SHA256, revision=revision,
        start_epoch_ms=int(window.start.timestamp()*1000),
        end_epoch_ms=int(window.end.timestamp()*1000),
        server_files={name:base64.b64encode(files[name]).decode('ascii') for name in sorted(files)})
    if login_rotation is not None:bundle['login_rotation']=validate_login_rotation(login_rotation)
    if notices is not None:bundle['notices']=validate_notices(notices)
    data = (json.dumps(bundle,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode('utf-8')
    validate_bundle(data)
    return data


def add_bundle_asset(archive: Path, data: bytes):
    validate_bundle(data)
    temporary = archive.with_name(archive.name+'.original-ops.pending')
    if archive.is_symlink() or temporary.exists():
        raise ProtocolError('ORIGINAL_OPS_UNSAFE_STAGING')
    created=False
    try:
        with ZipFile(archive) as original:
            entries=original.infolist()
            if len({entry.filename for entry in entries}) != len(entries) or ASSET_ENTRY in original.namelist():
                raise ProtocolError('ORIGINAL_OPS_ASSET_ALREADY_PRESENT_OR_DUPLICATED')
            with temporary.open('xb') as pending:
                created=True
                with ZipFile(pending,'w') as output:
                    for entry in entries:output.writestr(entry,original.read(entry.filename))
                    output.writestr(ASSET_ENTRY,data)
        temporary.replace(archive)
    finally:
        if created and temporary.exists():temporary.unlink()
    return dict(schema='kneekura-original-ops-asset-v1', added_entry=ASSET_ENTRY,
                sha256=hashlib.sha256(data).hexdigest(), original_save_mutated=False,
                original_ui_accepted=False)
