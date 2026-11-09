"""One-time repair for an undelivered owner-requested local gift."""
import copy
import hashlib
import re

from tools.base_mod.build_offline_max_save import _verify_jp_hash

GIFT_ID = 20261110
GIFT_AMOUNT = 40000


def build_gift_repair(source, core):
    _verify_jp_hash(source)
    if int.from_bytes(source[:4], 'little') not in (150700, 150704):
        raise ValueError('GIFT_REPAIR_UNSUPPORTED_SAVE')
    save = core.SaveFile(core.Data(source), load=False)
    save.load()
    if save.to_data().get_bytes() != source:
        raise ValueError('GIFT_REPAIR_SOURCE_ROUNDTRIP')
    if not re.fullmatch(r'kneekura-local-[0-9a-f]{32}', save.inquiry_code):
        raise ValueError('GIFT_REPAIR_FOREIGN_ACCOUNT')
    if GIFT_ID in save.mysale.dict_1 or GIFT_ID in save.mysale.dict_2:
        raise ValueError('GIFT_REPAIR_ALREADY_RECORDED')
    if not 0 <= save.catfood <= 2147483647 - GIFT_AMOUNT:
        raise ValueError('GIFT_REPAIR_CATFOOD_RANGE')
    expected = copy.deepcopy(save.to_dict())
    expected['catfood'] += GIFT_AMOUNT
    expected['mysale']['dict_1'][GIFT_ID] = 2
    expected['mysale']['dict_2'][GIFT_ID] = True
    save.catfood += GIFT_AMOUNT
    save.mysale.dict_1[GIFT_ID] = 2
    save.mysale.dict_2[GIFT_ID] = True
    if save.to_dict() != expected:
        raise ValueError('GIFT_REPAIR_UNAPPROVED_CHANGE')
    result = save.to_data().get_bytes()
    _verify_jp_hash(result)
    check = core.SaveFile(core.Data(result), load=False)
    check.load()
    if check.to_dict() != expected or check.to_data().get_bytes() != result:
        raise ValueError('GIFT_REPAIR_OUTPUT_ROUNDTRIP')
    return result, dict(source_sha256=hashlib.sha256(source).hexdigest(),
                        output_sha256=hashlib.sha256(result).hexdigest(),
                        added_catfood=GIFT_AMOUNT, original_claim_marked=True,
                        unrelated_fields_unchanged=True)
