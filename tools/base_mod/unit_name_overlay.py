"""Owner-approved unit name text overlay (2026-11-14).

Pure byte transform over the original UTF-8 ``Unit_Explanation<N>_ja.csv`` text. The
original SHA-256 and the exact original name/reading are checked first (fail closed).
"""
from __future__ import annotations

import hashlib

ORIGINAL_SHA256 = {
    'Unit_Explanation100_ja.csv': 'd795e55758e5f3238d9972e0426a1ff0bd02f8117c621ddeacf8ca9d8814bca6',
}
# file -> (line index, {field index: (expected original, new value)})
RENAMES = {
    'Unit_Explanation100_ja.csv': (1, {0: ('狂乱のネコダラボッチ', '狂乱のネコ親分'),
                                       4: ('キョウランノネコダラボッチ', 'キョウランノネコオヤブン')}),
}


def build_candidate(name: str, original: bytes) -> bytes:
    if name not in ORIGINAL_SHA256:
        raise ValueError('UNIT_NAME_OVERLAY_UNKNOWN_FILE')
    if hashlib.sha256(original).hexdigest() != ORIGINAL_SHA256[name]:
        raise ValueError('UNIT_NAME_OVERLAY_SOURCE_CHANGED')
    text = original.decode('utf-8')
    lines = text.splitlines(keepends=True)
    index, fields_spec = RENAMES[name]
    body = lines[index].rstrip('\r\n')
    ending = lines[index][len(body):]
    fields = body.split(',')
    for column, (expected, new) in fields_spec.items():
        if fields[column] != expected:
            raise ValueError('UNIT_NAME_OVERLAY_UNEXPECTED_SOURCE_VALUE')
        fields[column] = new
    lines[index] = ','.join(fields) + ending
    return ''.join(lines).encode('utf-8')
