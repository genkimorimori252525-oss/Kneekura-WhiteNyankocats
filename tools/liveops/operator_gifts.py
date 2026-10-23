"""Author once-only Cat Food gifts for the original item.tsv claim handler.

The event ID and entire claim window are immutable across rebuilds. This tool
does not read or edit SAVE; original receipt persistence owns deduplication.
"""
from datetime import datetime

from tools.liveops.original_schedule import EventWindow, ProtocolError, item_row


def gift_rows(gifts):
    if not isinstance(gifts,list) or len(gifts)>32:
        raise ProtocolError('ORIGINAL_OPERATOR_GIFTS')
    rows=[];seen=set()
    for gift in gifts:
        if (not isinstance(gift,dict) or type(gift.get('event_id')) is not int
                or not 1<=gift['event_id']<=2**31-1 or gift['event_id'] in seen
                or type(gift.get('item_id')) is not int or gift['item_id']!=200
                or type(gift.get('amount')) is not int or not 1<=gift['amount']<=45000
                or gift.get('everyday') is not False):
            raise ProtocolError('ORIGINAL_OPERATOR_GIFT_ONCE_CONTRACT')
        try:
            window=EventWindow(datetime.fromisoformat(gift['start']),datetime.fromisoformat(gift['end']))
            row=item_row(window,gift['event_id'],200,gift['amount'],
                title=gift['title'],message=gift['message'],everyday=False)
        except (KeyError,TypeError,ValueError) as exc:
            raise ProtocolError('ORIGINAL_OPERATOR_GIFT_FIELDS') from exc
        seen.add(gift['event_id']);rows.append(row)
    return rows
