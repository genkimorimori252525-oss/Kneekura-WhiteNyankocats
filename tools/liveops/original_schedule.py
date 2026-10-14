"""Original JP15.7.1 event wire format; pure authoring, no SAVE or network IO.

Field order is corroborated by the pinned BCSFE and PackPack readers. Their
code remains an external development reference, not an APK dependency.
"""
from dataclasses import dataclass
from datetime import datetime
import re

from tools.localcore.ops_calendar import JST, ORIGINAL_OWNER_SAVE
from tools.liveops.login_scheduler import SchedulerState, advance_local_day

GAME_VERSION = 150701  # original Android versionCode 1507010 / 10


class ProtocolError(ValueError):
    pass


def _integer(value, minimum=0, maximum=2**31-1):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ProtocolError('ORIGINAL_OPS_INTEGER_INVALID')
    return value


def _text(value):
    if not isinstance(value, str) or len(value)>1024 or any(ord(c)<32 for c in value):
        raise ProtocolError('ORIGINAL_OPS_TEXT_INVALID')
    return value


@dataclass(frozen=True)
class EventWindow:
    start: datetime
    end: datetime

    def __post_init__(self):
        for value in (self.start,self.end):
            if (not isinstance(value,datetime) or value.utcoffset() is None
                    or value.second or value.microsecond):
                raise ProtocolError('ORIGINAL_OPS_TIMESTAMP_INVALID')
        if self.start>=self.end:
            raise ProtocolError('ORIGINAL_OPS_EMPTY_WINDOW')
        if not (2000<=self.start.astimezone(JST).year<=2037
                and 2000<=self.end.astimezone(JST).year<=2037):
            raise ProtocolError('ORIGINAL_OPS_TIMESTAMP_RANGE')

    def header(self):
        start,end=self.start.astimezone(JST),self.end.astimezone(JST)
        return [int(start.strftime('%Y%m%d')),start.hour*100+start.minute,
                int(end.strftime('%Y%m%d')),end.hour*100+end.minute,
                GAME_VERSION,GAME_VERSION,0,0]


def _row(window, fields):
    if not isinstance(window,EventWindow):raise ProtocolError('ORIGINAL_OPS_WINDOW_INVALID')
    return '\t'.join(str(value) for value in window.header()+fields)


def gacha_row(window, set_id, *, cost=150, chances, guaranteed=(0,0,0,0,0), message=''):
    _integer(set_id,1,9999);_integer(cost,0,45000)
    if not isinstance(chances,(list,tuple)) or len(chances)!=5:
        raise ProtocolError('ORIGINAL_OPS_CHANCES_INVALID')
    if not isinstance(guaranteed,(list,tuple)) or len(guaranteed)!=5:
        raise ProtocolError('ORIGINAL_OPS_GUARANTEE_INVALID')
    for value in chances:_integer(value,0,10000)
    if sum(chances)!=10000:raise ProtocolError('ORIGINAL_OPS_CHANCES_INVALID')
    probability=[]
    for chance,guarantee in zip(chances,guaranteed):
        _integer(guarantee,0,1)
        if guarantee and not chance:raise ProtocolError('ORIGINAL_OPS_GUARANTEE_INVALID')
        probability.extend((chance,guarantee))
    # 1 = ordinary Rare Gacha. 2/3 are first-rare offers, not recurring events.
    return _row(window,[1,1,set_id,cost,0,0,*probability,_text(message)])


def stage_row(window, map_ids):
    if not isinstance(map_ids,(list,tuple)) or not 1<=len(map_ids)<=512:
        raise ProtocolError('ORIGINAL_OPS_STAGE_LIST_INVALID')
    for value in map_ids:_integer(value,1000,999999)
    if len(set(map_ids))!=len(map_ids):raise ProtocolError('ORIGINAL_OPS_STAGE_DUPLICATE')
    # Availability only; never emits a clear count, reward flag or unit grant.
    return _row(window,[len(map_ids),*map_ids])


def item_row(window, event_id, item_id, amount, *, title, message, everyday=False):
    _integer(event_id,1);_integer(item_id,0);_integer(amount,1)
    if type(everyday) is not bool:raise ProtocolError('ORIGINAL_OPS_ITEM_FLAG_INVALID')
    return _row(window,[event_id,item_id,amount,_text(title),_text(message),0,0,int(everyday)])


def stream(rows):
    if not isinstance(rows,(list,tuple)) or len(rows)>10000:
        raise ProtocolError('ORIGINAL_OPS_ROWS_INVALID')
    for row in rows:
        if (not isinstance(row,str) or not re.match(r'^\d{8}\t',row)
                or any(c in row for c in '\r\n\0')):
            raise ProtocolError('ORIGINAL_OPS_ROW_INVALID')
    payload=('[start]\n'+'\n'.join(rows)+('\n' if rows else '')+'[end]\n').encode('utf-8')
    if len(payload)>2*1024**2:raise ProtocolError('ORIGINAL_OPS_STREAM_TOO_LARGE')
    return payload


def prepare_login_day(state, campaigns, *, local_day):
    """Propose the existing state-machine transition; never commit or grant it."""
    _integer(local_day)
    candidate=SchedulerState.from_dict(state)
    report=advance_local_day(candidate,campaigns,local_day=local_day)
    return candidate.to_dict(),report
