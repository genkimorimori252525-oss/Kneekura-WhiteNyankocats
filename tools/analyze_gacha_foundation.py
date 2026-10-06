"""Read-only Super Kneekura Gacha foundation audit.

The audit proves what the exact JP InstallPack can tell us about gacha data and,
equally importantly, what it cannot prove.  It never mutates packs.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from tools.battlecats_source import BattleCatsExport


EXACT_JP_15_7_1_EXPORT_SHA256 = (
    "38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56"
)

RARITY_LABELS = {
    0: "normal",
    1: "special",
    2: "rare",
    3: "super_rare",
    4: "uber_rare",
    5: "legend_rare",
}

FOUNDATION_FILES = (
    "unitbuy.csv",
    "GatyaDataSetR1.csv",
    "GatyaDataSetR2.csv",
    "GatyaDataSetR3.csv",
    "GatyaData_Option_SetR.tsv",
    "EventGatya_Setting.csv",
    "GatyaData_Option_ChanceAnimation.tsv",
)


def _text(payload: bytes) -> str:
    return payload.decode("utf-8-sig", "replace")


def _nonempty_lines(payload: bytes) -> list[str]:
    return [line for line in _text(payload).splitlines() if line.strip()]


def parse_unit_rarity_counts(payload: bytes) -> dict[int, int]:
    counts: Counter[int] = Counter()
    for line in _text(payload).splitlines():
        body = line.split("//", 1)[0].strip()
        if not body:
            continue
        columns = [column.strip() for column in body.split(",")]
        if len(columns) <= 13:
            continue
        try:
            rarity = int(columns[13])
        except ValueError:
            continue
        counts[rarity] += 1
    return dict(sorted(counts.items()))


def parse_dataset_row_lengths(payload: bytes) -> list[int]:
    lengths: list[int] = []
    for line in _text(payload).splitlines():
        if not line.strip():
            continue
        count = 0
        for cell in line.split(","):
            cell = cell.strip()
            if not cell:
                continue
            try:
                value = int(cell)
            except ValueError:
                break
            if value == -1:
                break
            count += 1
        lengths.append(count)
    return lengths


def parse_event_gacha_setting(payload: bytes) -> list[dict]:
    rows: list[dict] = []
    for line in _text(payload).splitlines():
        if not line.strip():
            continue
        cells = [cell.strip() for cell in line.split(",")]
        try:
            values = [int(cell) for cell in cells]
        except ValueError:
            continue
        if not values:
            continue
        gacha_id = values[0]
        triples = []
        cursor = 1
        while cursor + 2 < len(values):
            triples.append(
                {
                    "group": values[cursor],
                    "unit": values[cursor + 1],
                    "value": values[cursor + 2],
                }
            )
            cursor += 3
        rows.append({"gacha_id": gacha_id, "entries": triples})
    return rows


def analyze_export(path: Path) -> dict:
    with BattleCatsExport(
        path,
        region="jp",
        expected_sha256=EXACT_JP_15_7_1_EXPORT_SHA256,
    ) as export:
        data_local = export.pack("DataLocal")
        files: dict[str, dict] = {}
        payloads: dict[str, bytes] = {}
        for name in FOUNDATION_FILES:
            payload, provenance = data_local.read(name)
            payloads[name] = payload
            files[name] = {
                "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "line_count": len(_text(payload).splitlines()),
                "provenance": {
                    "family": provenance.family,
                    "entry": provenance.entry,
                    "offset": provenance.offset,
                    "encrypted_size": provenance.encrypted_size,
                    "mode": provenance.mode,
                },
            }

        rarity_counts = parse_unit_rarity_counts(payloads["unitbuy.csv"])
        rarity_counts_labeled = {
            RARITY_LABELS.get(key, f"unknown_{key}"): value
            for key, value in rarity_counts.items()
        }

        r1_lengths = parse_dataset_row_lengths(payloads["GatyaDataSetR1.csv"])
        r2_lengths = parse_dataset_row_lengths(payloads["GatyaDataSetR2.csv"])
        r3_lengths = parse_dataset_row_lengths(payloads["GatyaDataSetR3.csv"])

        options = _nonempty_lines(payloads["GatyaData_Option_SetR.tsv"])
        chance_animation = _nonempty_lines(
            payloads["GatyaData_Option_ChanceAnimation.tsv"]
        )

        return {
            "schema_version": 1,
            "source": export.source_info.__dict__ if export.source_info else None,
            "files": files,
            "unit_rarity_counts": rarity_counts_labeled,
            "rare_dataset": {
                "set_count": len(r1_lengths),
                "r1_nonempty_sets": sum(1 for value in r1_lengths if value > 0),
                "r1_min_units": min(r1_lengths) if r1_lengths else 0,
                "r1_max_units": max(r1_lengths) if r1_lengths else 0,
                "r2_nonempty_sets": sum(1 for value in r2_lengths if value > 0),
                "r3_nonempty_sets": sum(1 for value in r3_lengths if value > 0),
                "option_rows_excluding_header": max(0, len(options) - 1),
            },
            "event_gacha_setting": parse_event_gacha_setting(
                payloads["EventGatya_Setting.csv"]
            ),
            "chance_animation": {
                "rows_excluding_header": max(0, len(chance_animation) - 1),
                "not_a_rarity_rate_source": True,
            },
            "rarity_rate_evidence": {
                "status": "unresolved_from_installpack_local_tables",
                "reason": (
                    "The local files prove unit rarity tiers, pool membership "
                    "sets, UI/options and chance-animation weights, but do not "
                    "by themselves prove the live Rare Capsule rarity-rate "
                    "vector. Phase C must capture one exact original JP banner "
                    "event/config or its runtime decision before Super Kneekura "
                    "rates are frozen."
                ),
            },
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export_zip", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = analyze_export(args.export_zip.resolve())
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
