"""Build the exact JP 15.7.1 eligible login-campaign pool."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from tools.analyze_login_bonus_foundation import (
    EXACT_EXPORT_SHA256,
    _integer_rows,
    parse_login_groups,
)
from tools.battlecats_source import BattleCatsExport


MIN_CAMPAIGN_DAYS = 6


def build_pool(export_zip: Path) -> dict:
    with BattleCatsExport(
        export_zip,
        region="jp",
        expected_sha256=EXACT_EXPORT_SHA256,
    ) as export:
        data = export.pack("DataLocal")
        payload, provenance = data.read("DailyLoginEventData.csv")

    rows = _integer_rows(payload)
    eligible: list[dict] = []
    excluded: list[dict] = []

    for row in rows:
        event_id = row[0]
        groups = parse_login_groups(row)[1]
        kinds: set[int] = set()
        item_counts: list[int] = []
        for group in groups:
            item_count = group[0]
            item_counts.append(item_count)
            for index in range(item_count):
                kinds.add(group[2 + index * 3])

        reasons: list[str] = []
        if len(groups) < MIN_CAMPAIGN_DAYS:
            reasons.append(f"shorter-than-{MIN_CAMPAIGN_DAYS}-days")
        if any(count <= 0 for count in item_counts):
            reasons.append("empty-reward-day")
        if -1 in kinds:
            reasons.append("contains-system-negative-reward-kind")

        entry = {
            "event_id": event_id,
            "day_count": len(groups),
            "reward_kinds": sorted(kinds),
            "header": row[:7],
        }
        if reasons:
            excluded.append({**entry, "reasons": reasons})
        else:
            eligible.append(entry)

    ids = [entry["event_id"] for entry in eligible]
    if len(eligible) != 106:
        raise ValueError(
            f"JP15.7.1 eligible login pool drifted: {len(eligible)} != 106"
        )

    return {
        "schema_version": 1,
        "anchor": "jp-15.7.1",
        "source": {
            "file": "DailyLoginEventData.csv",
            "payload_sha256": provenance.payload_sha256,
            "row_count": len(rows),
        },
        "policy": {
            "min_campaign_days": MIN_CAMPAIGN_DAYS,
            "require_nonempty_reward_each_day": True,
            "exclude_negative_reward_kind": True,
            "purpose": (
                "player-facing campaign pool foundation; one-day/system definitions "
                "remain excluded until individually classified"
            ),
        },
        "eligible_count": len(eligible),
        "eligible_ids_sha256": hashlib.sha256(
            ",".join(map(str, ids)).encode("ascii")
        ).hexdigest(),
        "eligible": eligible,
        "excluded_count": len(excluded),
        "excluded": excluded,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("owned_export", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        result = build_pool(args.owned_export)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"login-pool build failed: {exc}", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"built login pool: {result['eligible_count']} campaigns "
        f"-> {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
