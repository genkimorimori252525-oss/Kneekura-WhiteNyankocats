"""Owner-approved unit CSV tuning layered on the pinned PC/phone overlay (2026-11-14).

Pure byte transforms over original DataLocal unit CSV files. No original bytes are
stored here; every transform first checks the pinned original SHA-256 and the
exact pre-edit field values, so a changed source fails closed.

Column meanings follow the public JP battle-data layout (0-based):
  6 EoC1 cost, 7 cooldown/2, 10 red, 16 floating, 17 black, 18 metal, 19 traitless,
  20 angel, 21 alien, 22 zombie, 24 knockback chance, 25 freeze chance, 27 slow chance,
  35 wave chance, 36 wave level, 44/45 long-distance anchor/span, 54 witch, 76 eva,
  78 relic, 80 insanely tough (超打たれ強い), 94 mini-wave flag, 96 aku.
"""
from __future__ import annotations

import hashlib

# Pinned originals (identical in the owner's JP15.7.1 export and the JP15.7.4 InstallPack).
ORIGINAL_SHA256 = {
    'unit135.csv': '70c8b86ac785e6861d5447f9af2f3e7a18193e85f548389ab168eeb9cc472c5a',
    'unit178.csv': '53bd36547683c432cd1881fa710300b8cf67b4493ae903649dfdebfc63b85c46',
    'unit289.csv': 'e48bc212537fe7949c74527f0a8212874e8595fd9414f6d9bc2b7a1e3aee1a82',
    'unit290.csv': '9d07caca85bdae775bdb94f6433413ee56032f357065230f75f952cff4ce8b53',
}

ZOMBIE_COLUMN = 22
INSANE_TOUGH_COLUMN = 80
# Every target-trait flag except zombie: 超打たれ強い applies to these targets.
NON_ZOMBIE_TARGET_COLUMNS = (10, 16, 17, 18, 19, 20, 21, 54, 76, 78, 96)
# Columns bound to one form's animation or attack sequence; never copied between forms.
ANIMATION_BOUND_COLUMNS = frozenset({4, 13, *range(59, 70)})

# Price: original 6,600 (EoC2 basis, CSV x1.5) + 1,000 = 7,600 -> CSV 5067 (x1.5 truncated = 7600).
# Cooldown and knockback/slow chances stay original (owner dropped the double-summon plan).
DIOLAMUS_FORM4_COST = 5067

TOUGH_ALL_BUT_ZOMBIE = {INSANE_TOUGH_COLUMN: 1, **{c: 1 for c in NON_ZOMBIE_TARGET_COLUMNS}}

# file -> row -> {column: value}
EDITS: dict[str, dict[int, dict[int, int]]] = {
    'unit178.csv': {3: {**TOUGH_ALL_BUT_ZOMBIE, 6: DIOLAMUS_FORM4_COST}},
    'unit135.csv': {2: dict(TOUGH_ALL_BUT_ZOMBIE)},
    # Madoka (No.289): small wave Lv5 on the third form, applied after the legacy approved row.
    'unit289.csv': {2: {35: 100, 36: 5, 94: 1}},
    # Homura (No.290): smaller dead zone (anchor 205 -> 100, far end 655 kept), certain freeze.
    'unit290.csv': {2: {25: 100, 44: 100, 45: 555}},
}
# Pre-edit values that must hold before an edit is applied (fail closed).
EXPECTED_BEFORE: dict[str, dict[int, dict[int, int]]] = {
    'unit178.csv': {3: {6: 4400, 7: 2480, 22: 0, 24: 100, 27: 100, 80: 0}},
    'unit135.csv': {2: {0: 14500, 22: 0, 29: 1}},
    'unit289.csv': {2: {35: 0, 36: 0, 94: 0}},
    'unit290.csv': {2: {25: 50, 44: 205, 45: 450}},
}
# Earlier forms take the final form's performance (animation-bound columns excluded).
COPY_FINAL_TO_EARLIER: dict[str, tuple[int, tuple[int, ...]]] = {
    'unit289.csv': (2, (0, 1)),
    'unit290.csv': (2, (0, 1)),
}
TUNED = frozenset(ORIGINAL_SHA256)
# Rows of each file that differ from the original after tuning (for the verifier).
CHANGED_ROWS = {
    'unit178.csv': frozenset({3}),
    'unit135.csv': frozenset({2}),
    'unit289.csv': frozenset({0, 1, 2}),
    'unit290.csv': frozenset({0, 1, 2}),
}


def _split(row: bytes) -> tuple[list[bytes], bytes]:
    body = row.rstrip(b'\r\n')
    return body.split(b','), row[len(body):]


def _set(fields: list[bytes], column: int, value: int) -> None:
    while len(fields) <= column:
        fields.append(b'0')
    fields[column] = str(value).encode('ascii')


def _get(fields: list[bytes], column: int) -> int:
    return int(fields[column]) if column < len(fields) else 0


def build_candidate(name: str, original: bytes, *, legacy_candidate: bytes | None = None) -> bytes:
    """Return the tuned file. ``legacy_candidate`` is the already approved
    single-row candidate (Madoka form 3) that tuning is layered on."""
    if name not in TUNED:
        raise ValueError('PC_UNIT_TUNING_UNKNOWN_FILE')
    if hashlib.sha256(original).hexdigest() != ORIGINAL_SHA256[name]:
        raise ValueError('PC_UNIT_TUNING_SOURCE_CHANGED')
    rows = (legacy_candidate if legacy_candidate is not None else original).splitlines(keepends=True)
    total = len(original.splitlines(keepends=True))
    if len(rows) != total:
        raise ValueError('PC_UNIT_TUNING_ROW_COUNT_CHANGED')
    for index, expectations in EXPECTED_BEFORE[name].items():
        fields, _ = _split(rows[index])
        for column, value in expectations.items():
            if _get(fields, column) != value:
                raise ValueError(f'PC_UNIT_TUNING_UNEXPECTED_SOURCE_VALUE:{name}:{index}:{column}')
    for index, edits in EDITS[name].items():
        fields, ending = _split(rows[index])
        for column, value in edits.items():
            _set(fields, column, value)
        rows[index] = b','.join(fields) + ending
    if name in COPY_FINAL_TO_EARLIER:
        source_index, targets = COPY_FINAL_TO_EARLIER[name]
        source, _ = _split(rows[source_index])
        for index in targets:
            fields, ending = _split(rows[index])
            for column, value in enumerate(source):
                if column not in ANIMATION_BOUND_COLUMNS:
                    while len(fields) <= column:
                        fields.append(b'0')
                    fields[column] = value
            rows[index] = b','.join(fields) + ending
    return b''.join(rows)
